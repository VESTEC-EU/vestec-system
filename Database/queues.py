from Database import db
import pony.orm as pny
import datetime
from Database.machine import Machine



class Queue(db.Entity):
    uuid = pny.Required(str)
    name = pny.Required(str)
    machine = pny.Required(Machine)
    maxNodes = pny.Required(int)
    minWalltime = pny.Required(datetime.timedelta)
    maxWalltime = pny.Required(datetime.timedelta)
    default = pny.Required(bool)

    jobs = pny.Set("Job")
