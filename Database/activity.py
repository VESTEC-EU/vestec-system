import pony.orm as pny
import datetime
from enum import Enum
from Database import db
from Database.users import User


class ActivityStatus(Enum):
    PENDING=1
    ACTIVE=2
    COMPLETED=3
    ERROR=4

class Activity(db.Entity):
    activity_id = pny.PrimaryKey(str)
    activity_name = pny.Required(str)
    date_submitted = pny.Required(datetime.datetime)
    status = pny.Required(str, default="PENDING")
    activity_type = pny.Required(str)
    location = pny.Required(str)
    user_id = pny.Required(User)

    jobs = pny.Set("Job", cascade_delete=True)

    def setStatus(self, status):
        self.status = status

