import configuration
import pyodbc
import logging
import pymsteams
import re


class VeeamEvent(object):
    def __init__(self, target_notification_channel: str, event_info: list):
        self.raw_event_info = event_info
        self.target_notification_channel = target_notification_channel
        self.completed = False
        self.job_name = self.raw_event_info[0][0]
        self.job_type = int(self.raw_event_info[0][1])
        if self.job_type == 51:
            self.job_type_name = 'Backup copy job'
        elif self.job_type == 0:
            self.job_type_name = 'Backup job'
        elif self.job_type == 1:
            self.job_type_name = 'Replication job'
        elif self.job_type == 3:
            self.job_type_name = 'SureBackup job'
        elif self.job_type == 24:
            self.job_type_name = 'File to tape job'
        elif self.job_type == 28:
            self.job_type_name = 'Backup to tape job'
        elif self.job_type == 100:
            self.job_type_name = 'Configuration backup'
        else:
            self.job_type_name = None
        # if you need, contact @Dmitry Rozhdestvenskiy at Veeam Support to get more job types
        self.usn = self.raw_event_info[0][2]
        self.end_time = self.raw_event_info[0][3]
        self.result = self.raw_event_info[0][4]
        if self.result == 0:
            self.result_text = 'success'
        elif self.result == 1:
            self.result_text = 'warning'
        elif self.result == 2:
            self.result_text = 'failed'
        else:
            self.result_text = None
        self.reason = self.raw_event_info[0][5]


class SQLConnectorVeeamDB:
    def __init__(self, sql_config: configuration.SQLConfigVeeamDB):
        self.logging_inst = logging.getLogger()
        try:
            self.connection = pyodbc.connect(
                'DRIVER=' + sql_config.Driver + ';PORT=1433;SERVER=' + sql_config.Server + ';PORT=1443;DATABASE='
                + sql_config.Database + ';UID=' + sql_config.Username + ';PWD=' + sql_config.Password)
            self.cursor = self.connection.cursor()
            self.logging_inst.debug('Connected to SQL Server ' + sql_config.Server + ', DB name: ' + sql_config.Database)
        except Exception as error:
            self.logging_inst.debug(
                'Unable to connect to SQL Server ' + sql_config.Server + ', DB name: ' + sql_config.Database + ', with error: \n' + str(error))
            exit(1)

    def select_completed_job_sessions_during_latest_hour(self)->tuple:
        query = 'select job_name,job_type, usn, end_time, result, reason ' \
                'from [dbo].[Backup.Model.JobSessions] ' \
                'where state = -1 and result != -1 and datediff(HH,[end_time],GETDATE()) <= 1 ' \
                'order by usn'
        self.cursor.execute(query)
        rows = self.cursor.fetchall()
        latest_usn = None
        if rows:
            lines = []
            for row in rows:
                verified_row = [row]
                lines.append(verified_row)
                latest_usn = row.usn
            if latest_usn is not None:
                result = (latest_usn, lines)
                return result
            else:
                raise ResourceWarning
        else:
            self.logging_inst.debug('No events during last hour, selecting latest usn in the table to use it next time')
            query = 'select top 1 [usn] ' \
                    'from [dbo].[Backup.Model.JobSessions] ' \
                    'order by usn desc'
            self.cursor.execute(query)
            row = self.cursor.fetchone()
            if row:
                latest_usn = row.usn
            if latest_usn is not None:
                result = (latest_usn, [])
                return result
            else:
                raise ResourceWarning

    def select_completed_job_sessions_after_usn(self, usn: int)->tuple:
        query = 'select job_name,job_type, usn, end_time, result, reason ' \
                'from [dbo].[Backup.Model.JobSessions] ' \
                'where state = -1 and result != -1 and usn > ? ' \
                'order by usn'
        self.cursor.execute(query, usn)
        rows = self.cursor.fetchall()
        latest_usn = None
        if rows:
            lines = []
            for row in rows:
                verified_row = [row]
                lines.append(verified_row)
                latest_usn = row.usn
            if latest_usn is not None:
                result = (latest_usn, lines)
                return result
            else:
                raise ResourceWarning
        else:
            self.logging_inst.debug('No events since provided usn, selecting latest usn in the table to use it next time')
            query = 'select top 1 [usn] ' \
                    'from [dbo].[Backup.Model.JobSessions] ' \
                    'order by usn desc'
            self.cursor.execute(query)
            row = self.cursor.fetchone()
            if row:
                latest_usn = row.usn
            if latest_usn is not None:
                result = (latest_usn, [])
                return result
            else:
                raise ResourceWarning


def send_notification_to_web_hook(web_hook_url: str, event_object: VeeamEvent)->bool:
    logger_inst = logging.getLogger()
    logger_inst.debug('web_hook_url: ' + str(web_hook_url))
    logger_inst.debug('threat: ' + str(event_object))
    if uri_validator(web_hook_url) is not True:
        logger_inst.error('Malformed url: ' + str(web_hook_url))
        return False
    team_connection = pymsteams.connectorcard(web_hook_url)
    text = None
    if event_object.job_type_name is not None:
        if event_object.result_text == 'success':
            text = 'A Veeam ' + event_object.job_type_name + ' **"' + str(event_object.job_name) + '"** has finished **successfully** at ' + str(event_object.end_time)[:-7]
            team_connection.color('005f4b')  # it's a brand color named "Veeam Sapphire", btw
        elif event_object.result_text == 'warning':
            text = 'A Veeam ' + event_object.job_type_name + ' **"' + str(event_object.job_name) + '"** has finished with **warning** and result: \n\n"' + str(event_object.reason) + '" at ' + str(event_object.end_time)[:-7]
            team_connection.color('ffff00')  # just Yellow
        elif event_object.result_text == 'failed':
            text = 'A Veeam ' + event_object.job_type_name + ' **"' + str(event_object.job_name) + '"** has **failed** with a result: \n\n"' + str(event_object.reason) + '" at ' + str(event_object.end_time)[:-7]
            team_connection.color('ba0200')  # "Veeam Accent Red"
    else:
        if event_object.result_text == 'success':
            # There is no need to notify about system events when everything is good
            return True
        elif event_object.result_text == 'warning':
            text = 'A Veeam Task **"' + event_object.job_name + '"** has finished with **warning** and result: \n\n"' + str(event_object.reason).replace('\n\n', ' ') + '" at ' + str(event_object.end_time)[:-7]
            team_connection.color('ffff00')  # just Yellow
        elif event_object.result_text == 'failed':
            text = 'A Veeam Task **"' + event_object.job_name + '"** has **failed** with a result: \n\n"' + str(event_object.reason).replace('\n\n', ' ') + '" at ' + str(event_object.end_time)[:-7]
            team_connection.color('ba0200')  # "Veeam Accent Red"
    if text is None:
        return False
    team_connection.text(text)
    try:
        result = team_connection.send()
    except Exception as error:
        logger_inst.error('Unable to send notification to MS Teams due to the following error: \n' + str(error))
        return False
    return result


def uri_validator(ulr) -> bool:
    regex = re.compile(
        r'^(?:http|ftp)s?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}|'  # ...or ipv4
        r'\[?[A-F0-9]*:[A-F0-9:]+\]?)'  # ...or ipv6
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    try:
        result = regex.match(ulr)
        if result is not None:
            return True
        else:
            return False
    except:
        return False
