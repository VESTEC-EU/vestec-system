import datetime
import pony.orm as pny
from enum import Enum
from Database import db
from Database.workflow import Incident

class JobStatus(Enum):
    PENDING=0
    QUEUED=1
    RUNNING=2
    COMPLETED=3
    ERROR=4

class Job(db.Entity):
    job_id = pny.PrimaryKey(str)       
    num_nodes = pny.Required(int)    
    requested_walltime = pny.Required(int)
    executable = pny.Required(str)

    walltime = pny.Required(int)
    submit_time = pny.Required(datetime.datetime)
    run_time = pny.Optional(datetime.timedelta)
    end_time = pny.Optional(datetime.datetime) 
    status = pny.Required(str, default="PENDING")

    def setStatus(self, status):
        self.status = status

    def setRunTime(self, run_time):
        self.run_time = run_time

    def setEndTime(self, end_time):
        self.end_time = end_time


