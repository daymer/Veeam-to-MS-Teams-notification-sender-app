from configuration import SQLConfigVeeamDB, Integration, TeamsChannels
from custom_logic import SQLConnectorVeeamDB, VeeamEvent
import logging
from datetime import datetime
import sys
import time as other_time
from logger_init import logging_config


ConfigurationInstance = Integration()
SqlConfigInstanceVeeamDB = SQLConfigVeeamDB()
SqlConnectorInstanceVeeamDB = SQLConnectorVeeamDB(SqlConfigInstanceVeeamDB)
MainLogger = logging_config(integration_config=ConfigurationInstance, logging_mode='INFO', log_to_file=False, executable_path=__file__)
MainLogger.info('Main process has been initialized')


def main_execution(latest_usn_func: int = 0, query_delay: int = 60):
    # initialising target MS channels list
    ms_teams_inst = TeamsChannels()
    # loading latest events from Veeam DataBase
    if latest_usn_func == 0:
        latest_usn_func, raw_event_list = SqlConnectorInstanceVeeamDB.select_failed_job_sessions_during_latest_hour()
    else:
        latest_usn_func, raw_event_list = SqlConnectorInstanceVeeamDB.select_failed_job_sessions_after_usn(latest_usn_func)
    print(latest_usn_func, raw_event_list)
    # parsing them and posting to MS Teams
    if len(raw_event_list) > 0:
        events_to_process = []
        for each_raw_event in raw_event_list:
            verified_event = VeeamEvent(target_notification_channel=ms_teams_inst.webhooks_dict['default_channel'],
                                        event_info=each_raw_event)
            events_to_process.append(verified_event)
        for each_verified_event in events_to_process:
            if type(each_verified_event) == VeeamEvent:
                print(each_verified_event.completed)
            else:
                MainLogger.info('Such event type isn\'t supported by this tinny app, '
                                'what it is doing in events_to_process? :)')
            MainLogger.debug(str(type(each_verified_event)))
    

    # waiting query_delay, default: 60 sec
    other_time.sleep(query_delay)
    return latest_usn_func

try:
    latest_usn = 0
    while True:
        latest_usn = main_execution(latest_usn_func=latest_usn)

except Exception as any_error_which_could_occur:
    MainLogger.error('Main Execution was stopped due to the following error: \n'
                     + str(any_error_which_could_occur))
    exit(1)
except ResourceWarning as any_error_which_could_occur:
    MainLogger.error('Main Execution was stopped since latest selected usn from VeeamDB is NONE: \n'
                     + str(any_error_which_could_occur))
    exit(1)
