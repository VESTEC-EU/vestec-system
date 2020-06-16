import sys

sys.path.append("../")
import workflow
import os
import pony.orm as pny
import requests
import json
from Database import PerformanceData, Job

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
    job_id = message["data"]["JobID"]
    data_type = message["data"]["type"]
    # pipe this through the json module for consistent formatting
    # removing indentation to save space in the database
    raw_json = json.dumps(json.loads(message["data"]["raw_json"]))
    new_db_entry = PerformanceData(
        job=Job[job_id], data_type=data_type, raw_json=raw_json
    )
    print(
        "Performance data of job {} has been added to the database".format(
            new_db_entry.job.job_id
        )
    )


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
