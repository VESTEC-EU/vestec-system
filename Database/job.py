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
    walltime = pny.Required(int)
    submit_time = pny.Required(datetime.datetime)
    run_time = pny.Optional(datetime.datetime)
    end_time = pny.Optional(datetime.datetime)

    work_directory = pny.Required(str)
    executable = pny.Required(str)
    
    status = pny.Required(JobStatus, default=JobStatus.QUEUED)

    activities = pny.Set("ActivityJobs")

    def setStatus(self, status):
        self.status = status


