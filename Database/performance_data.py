import pony.orm as pny
from enum import Enum
from Database import db
from Database.workflow import Simulation


class PerformanceDataType(Enum):
    TIMINGS = 0
    LIKWID = 1
    CWL_TIMINGS = 2


class PerformanceData(db.Entity):
    simulation = pny.Required(Simulation)
    data_type = pny.Required(PerformanceDataType)
    raw_json = pny.Required(str)
