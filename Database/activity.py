import pony.orm as pny
from Database import db
import datetime
from enum import Enum
from Database.users import User
from Database.job import Job


class ActivityStatus(Enum):
    PENDING=1
    ACTIVE=2
    COMPLETED=3
    ERROR=4

class Activity(db.Entity):
    activity_id = pny.PrimaryKey(str)
    activity_name = pny.Required(str)
    date_submitted = pny.Required(datetime.datetime)
    status = pny.Required(ActivityStatus, default=ActivityStatus.PENDING)
    activity_type = pny.Required(str)
    location = pny.Required(str)
    user_id = pny.Required(User)

    jobs = pny.Set("ActivityJobs")

    def setStatus(self, status):
        self.status = status

    def getJobs(self):
        job_ids = pny.select(link.job_id for link in ActivityJobs if link.activity_id == self.activity_id)[:]
        sub_jobs = pny.select(job for job in Jobs if job.job_id in job_ids)[:]

        return sub_jobs


class ActivityJobs(db.Entity):
    activity_id = pny.Required(Activity)
    job_id = pny.Required(Job)
    description = pny.Required(str)
    executable = pny.Required(str)

