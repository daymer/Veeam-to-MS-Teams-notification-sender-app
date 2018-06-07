from configuration import SQLConfigVeeamDB, Integration, TeamsChannels
from custom_logic import SQLConnectorVeeamDB, VeeamEvent
import custom_logic
import configparser
import time as other_time
from logger_init import logging_config

ConfigurationInstance = Integration()
MainLogger = logging_config(integration_config=ConfigurationInstance, logging_mode='DEBUG', log_to_file=False, executable_path=__file__)
SqlConfigInstanceVeeamDB = SQLConfigVeeamDB()
SqlConnectorInstanceVeeamDB = SQLConnectorVeeamDB(SqlConfigInstanceVeeamDB)
MainLogger.info('Main process has been initialized')
IniFile = configparser.ConfigParser()
IniFileName = 'configuration.ini'


def main_execution(latest_usn_func: int = 0, query_delay: int = 60):
    # initialising target MS channels list
    ms_teams_inst = TeamsChannels()
    # loading latest events from Veeam DataBase
    if latest_usn_func == 0:
        latest_usn_func, raw_event_list = SqlConnectorInstanceVeeamDB.select_completed_job_sessions_during_latest_hour()
    else:
        latest_usn_func, raw_event_list = SqlConnectorInstanceVeeamDB.select_completed_job_sessions_after_usn(latest_usn_func)
    # parsing them and posting to MS Teams
    if len(raw_event_list) > 0:
        events_to_process = []
        for each_raw_event in raw_event_list:
            verified_event = VeeamEvent(target_notification_channel=ms_teams_inst.webhooks_dict['default_channel'],
                                        event_info=each_raw_event)
            events_to_process.append(verified_event)
        for each_verified_event in events_to_process:
            if type(each_verified_event) == VeeamEvent:
                # here you can filter events by VeeamEvent.job_type or VeeamEvent.result to send (or not send)
                # more personalized notification into different channels, just add some additional logic here
                result = custom_logic.send_notification_to_web_hook(event_object=each_verified_event, web_hook_url=each_verified_event.target_notification_channel)
                if result is True:
                    MainLogger.info('Veeam event ' + str(each_verified_event.job_name) + ' created at ' + str(each_verified_event.end_time) + ' is processed')
                    # save its each_verified_event.usn to a text ini to use later

                    each_verified_event.completed = True

                else:
                    MainLogger.error('The event ' + str(each_verified_event.job_name) + ' created at' + str(
                        each_verified_event.end_time) + ' is NOT processed, some error occurred')
                    # here you can do smth with such events, but I don't care :)
                    pass
            else:
                MainLogger.info('Such event type isn\'t supported by this tinny app, '
                                'what it is doing in events_to_process? :)')
            MainLogger.debug(str(type(each_verified_event)))

    # waiting a query_delay, default: 60 sec
    other_time.sleep(query_delay)
    return latest_usn_func

try:
    IniFile.read(IniFileName)
    try:
        latest_usn = int(IniFile['DEFAULT']['latest_usn'])
    except KeyError:
        latest_usn = 0
        IniFile['DEFAULT']['latest_usn'] = str(0)
        with open(IniFileName, 'w') as configfile:
            IniFile.write(configfile)
    while True:
        latest_usn = main_execution(latest_usn_func=latest_usn)
        MainLogger.debug('main_execution is done, updating ini file with a new latest_usn:' + str(latest_usn))
        IniFile['DEFAULT']['latest_usn'] = str(latest_usn)
        with open(IniFileName, 'w') as configfile:
            IniFile.write(configfile)
            MainLogger.debug('USN updated')

except Exception as any_error_which_could_occur:
    MainLogger.error('Main Execution was stopped due to the following error: \n'
                     + str(any_error_which_could_occur))
    exit(1)
except ResourceWarning as any_error_which_could_occur:
    MainLogger.error('Main Execution was stopped since latest selected usn from VeeamDB is NONE: \n'
                     + str(any_error_which_could_occur))
    exit(1)
