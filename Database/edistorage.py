from Database import db
import pony.orm as pny
from enum import Enum

class EDIHandler(db.Entity):
    id = pny.PrimaryKey(int, auto=True)
    queuename = pny.Required(str)
    incidentid=pny.Required(str)
    endpoint=pny.Required(str)
    type=pny.Required(str)
    pollperiod=pny.Optional(str)    
    