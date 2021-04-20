from Database import DBLog, LogType
import datetime
import pony.orm as pny

class VestecLogger():
    def __init__(self,originator):
        self.originator = originator

    @pny.db_session
    def Log(self,comment,user="system",incidentId=None, type=LogType.Info):
        if (incidentId is None):
            DBLog(timestamp=datetime.datetime.now(),type=type,comment=comment,originator=self.originator,user=user)
        else:
            DBLog(timestamp=datetime.datetime.now(),type=type,comment=comment,originator=self.originator,user=user, incidentId=incidentId)
