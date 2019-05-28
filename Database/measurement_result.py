#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Provide PonyORM entities for performance measurement results

Created on Mon May 27 15:42:20 2019

@author: Max Kontak, DLR German Aerospace Center
"""


import datetime as dt
import pony.orm as pny
from Database import db


class MeasurementResult(db.Entity):  # pylint: disable=too-few-public-methods
    """ base class to store results of performance measurements
    """
    timestamp = pny.Required(dt.datetime)
    uuid = pny.Required(str)
    duration = pny.Required(float)


class DataTransferMeasurement(MeasurementResult):  # pylint: disable=too-few-public-methods
    """ class to store timings of data transfers
    """
    source = pny.Required("Machine", reverse="data_transfer_source")
    target = pny.Required("Machine", reverse="data_transfer_target")
    size = pny.Required(int)


class ExecutionMeasurement(MeasurementResult):  # pylint: disable=too-few-public-methods
    """ class to store timings of application executions
    """
    machine = pny.Required("Machine")
    application = pny.Required(str)  # "Application" could also be a database entity
    version = pny.Required(str)  # "ApplicationVersion" could also be a database entity
    numNodes = pny.Required(int)
    numProcPerNode = pny.Required(int)
    numThreadsPerProc = pny.Required(int)
    parameters = pny.Required(pny.Json)
