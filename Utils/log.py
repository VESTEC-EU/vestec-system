from Database import DBLog, LogType
import datetime
import pony.orm as pny

class VestecLogger():
    def __init__(self,originator):
        self.originator = originator

    @pny.db_session
    def Log(self,type,comment,user="system",incidentId=None):
        DBLog(timestamp=datetime.datetime.now(),type=type,comment=comment,originator=self.originator,user=user)
