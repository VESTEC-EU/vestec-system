import pony.orm as pny
from Database import db
from enum import Enum
import datetime

class LogType(Enum):
    Info=0
    Warning=1
    Error=2    


class DBLog(db.Entity):
    timestamp = pny.Required(datetime.datetime)
    user = pny.Required(str,default="system")
    type = pny.Required(LogType)
    comment = pny.Required(str)
    originator = pny.Required(str)
    incidentId = pny.Optional(str)