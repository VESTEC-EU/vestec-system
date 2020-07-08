import pony.orm as pny
from Database import db
from enum import Enum
import datetime

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
    incidentId = pny.Optional(str)