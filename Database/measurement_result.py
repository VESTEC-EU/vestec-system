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


class MeasurementResult(db.Entity): # pylint: disable=too-few-public-methods
    """ base class to store results of performance measurements
    """
    timestamp = pny.Required(dt.datetime)
    uuid = pny.Required(str)
    duration = pny.Required(float)


class DataTransferMeasurement(MeasurementResult): # pylint: disable=too-few-public-methods
    """ class to store timings of data transfers
    """
    source = pny.Required("Machine")
    target = pny.Required("Machine")
    size = pny.Required(int)
