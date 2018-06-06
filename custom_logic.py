import configuration
import pyodbc
import logging


class VeeamEvent(object):
    def __init__(self, target_notification_channel: str, event_info: list):
        self.raw_event_info = event_info
        self.target_notification_channel = target_notification_channel
        self.completed = False


class SQLConnectorVeeamDB:
    def __init__(self, sql_config: configuration.SQLConfigVeeamDB):
        self.connection = pyodbc.connect(
            'DRIVER=' + sql_config.Driver + ';PORT=1433;SERVER=' + sql_config.Server + ';PORT=1443;DATABASE='
            + sql_config.Database + ';UID=' + sql_config.Username + ';PWD=' + sql_config.Password)
        self.cursor = self.connection.cursor()
        self.logging_inst = logging.getLogger()
        self.logging_inst.debug('Connected to SQL Server ' + sql_config.Server + ', DB name: ' + sql_config.Database)

    def select_failed_job_sessions_during_latest_hour(self)->tuple:
        query = 'select job_name,job_type, usn, end_time, result, reason ' \
                'from [dbo].[Backup.Model.JobSessions] ' \
                'where state = -1 and result in (1,2) and datediff(HH,[end_time],GETDATE()) <= 1 ' \
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

    def select_failed_job_sessions_after_usn(self, usn: int)->tuple:
        query = 'select job_name,job_type, usn, end_time, result, reason ' \
                'from [dbo].[Backup.Model.JobSessions] ' \
                'where state = -1 and result in (1,2) and usn > ? ' \
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