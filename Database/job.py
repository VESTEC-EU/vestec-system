from Database import db
import pony.orm as pny
from enum import Enum
import datetime
from Database.queues import Queue


class JobStatus(Enum):
    QUEUED=1
    RUNNING=2
    COMPLETED=3
    ERROR=4


class Job(db.Entity):
    job_id = pny.PrimaryKey(str)
    queue_id = pny.Required(Queue)
    
    no_nodes = pny.Required(int)
    walltime = pny.Required(datetime.timedelta)
    
    submit_time = pny.Required(datetime.datetime)
    run_time = pny.Optional(datetime.datetime)
    end_time = pny.Optional(datetime.datetime)
    
    status = pny.Required(JobStatus)

    activities = pny.Set("ActivityJobs")

