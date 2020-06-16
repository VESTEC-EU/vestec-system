import datetime
import pony.orm as pny
from enum import Enum
from Database import db
from Database.job import Job


class PerformanceDataType(Enum):
    TIMINGS=0
    LIKWID=1


class PerformanceData(db.Entity):
    job = pny.Required(Job)
    data_type = pny.Required(PerformanceDataType)
    raw_json = pny.Required(str)
