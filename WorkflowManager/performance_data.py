import sys

sys.path.append("../")
import workflow
import os
import pony.orm as pny
import datetime
import time
import requests
import json
from base64 import b64decode
from Database import LocalDataStorage
from Database.workflow import Incident, StoredDataset

if "VESTEC_EDI_URI" in os.environ:
    EDI_URL = os.environ["VESTEC_EDI_URI"]
    DATA_MANAGER_URI = os.environ["VESTEC_DM_URI"]
else:
    EDI_URL = "http://localhost:5501/EDImanager"
    DATA_MANAGER_URI = "http://localhost:5000/DM"

# we now want to define some handlers
@workflow.handler
@pny.db_session
def add_performance_data(message):
    """ add performance data to database
        expected fields in message["data"]:
            - ["JobID"]: id of the compute job in the VESTEC database
            - ["type"]: type of the performance data ("timings", "likwid", etc.)
            - ["raw_json"]: performance data in json format
    """
    new_db_entry = str()


@workflow.handler
def initialise_performance_data(message):
    print("Initialise simple workflow for " + message["IncidentID"])
    myobj = {
        "queuename": "add_performance_data",
        "incidentid": message["IncidentID"],
        "endpoint": "add_performance_data" + message["IncidentID"],
    }
    x = requests.post(EDI_URL + "/register", json=myobj)
    print("EDI response for manually add data" + x.text)
    workflow.setIncidentActive(message["IncidentID"])


# we have to register them with the workflow system
def RegisterHandlers():
    workflow.RegisterHandler(add_performance_data, "add_data_simple")
    workflow.RegisterHandler(initialise_performance_data, "initialise_simple")
