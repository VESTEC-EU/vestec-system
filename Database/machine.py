from Database import db
import pony.orm as pny
from enum import Enum


class Machine(db.Entity):
    machine_id = pny.PrimaryKey(str)
    machine_name = pny.Required(str)
    host_name = pny.Required(str)
    scheduler = pny.Required(str)
    num_nodes = pny.Required(int)
    cores_per_node = pny.Required(int)
    base_work_dir = pny.Required(str)

    queues = pny.Set("Queue")
