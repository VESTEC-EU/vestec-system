import Database
from Database import db
from enum import Enum
import datetime
import pony.orm as pny


class LogType(Enum):
    Unknown=0
    Activity=1
    Job=2
    Query=3
    Website=4
    Logins=5
    Error=6


class DBLog(db.Entity):
    timestamp = pny.Required(datetime.datetime)
    user = pny.Required(str,default="system")
    type = pny.Required(LogType)
    comment = pny.Required(str)
    originator = pny.Required(str)




class VestecLogger():
    def __init__(self,originator):
        self.originator = originator

    @pny.db_session
    def Log(self,type,comment,user="system"):
        DBLog(timestamp=datetime.datetime.now(),type=type,comment=comment,originator=self.originator,user=user)




if __name__ == "__main__":
    Database.initialiseDatabase()
    l=VestecLogger("Log Test Script")

    l.Log(type=LogType.Unknown,comment="Test")

    with pny.db_session:
        logs=pny.select(a for a in DBLog)[:]
        for log in logs:
            print(log.timestamp, "|", log.originator, "|",log.user,"|", log.comment)
