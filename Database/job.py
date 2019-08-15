import datetime
import pony.orm as pny
from enum import Enum
from Database import db
from Database.queues import Queue
from Database.activity import Activity


class JobStatus(Enum):
    QUEUED=1
    RUNNING=2
    COMPLETED=3
    ERROR=4


class Job(db.Entity):
    job_id = pny.PrimaryKey(str)
    activity_id = pny.Required(Activity)
    queue_id = pny.Required(Queue)
    no_nodes = pny.Required(int)
    work_directory = pny.Required(str)
    executable = pny.Required(str)

    walltime = pny.Required(int)
    submit_time = pny.Required(datetime.datetime)
    run_time = pny.Optional(datetime.datetime)
    end_time = pny.Optional(datetime.datetime) 
    status = pny.Required(JobStatus, default=JobStatus.QUEUED)

    def setStatus(self, status):
        self.status = status


