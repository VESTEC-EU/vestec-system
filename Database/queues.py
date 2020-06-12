from Database import db
import pony.orm as pny
import datetime
from Database.machine import Machine


class Queue(db.Entity):
    queue_id = pny.PrimaryKey(str)
    queue_name = pny.Required(str)
    max_nodes = pny.Required(int)
    min_walltime = pny.Required(int)
    max_walltime = pny.Required(int)
    default = pny.Required(bool)

#    jobs = pny.Set("Job")
