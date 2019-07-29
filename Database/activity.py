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
    status = pny.Required(ActivityStatus)
    activity_type = pny.Required(str)
    location = pny.Required(str)
    user = pny.Required(User)

    jobs = pny.Set("ActivityJobs")


class ActivityJobs(db.Entity):
    activity = pny.Required(Activity)
    job = pny.Required(Job)
    description = pny.Required(str)
    executable = pny.Required(str)
