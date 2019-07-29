from Database import db
import pony.orm as pny
import datetime
from Database.machine import Machine


class Queue(db.Entity):
    queue_id = pny.Required(str)
    queue_name = pny.Required(str)
    machine_id = pny.Required(Machine)
    max_nodes = pny.Required(int)
    min_walltime = pny.Required(datetime.timedelta)
    max_walltime = pny.Required(datetime.timedelta)
    default = pny.Required(bool)

    jobs = pny.Set("Job")
