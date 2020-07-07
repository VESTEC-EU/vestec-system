import sys

sys.path.append("../")
import workflow
import os
import pony.orm as pny
import requests
import json
from Database import PerformanceData, Simulation
from ExternalDataInterface.client import registerEndpoint, ExternalDataInterfaceException

# we now want to define some handlers
@workflow.handler
@pny.db_session
def add_performance_data(message):
    """ add performance data to database
        expected fields in message["data"]:
            - ["machine"]: name of the machine
            - ["jobID"]: job id on the HPC machine
            - ["type"]: type of the performance data ("timings", "likwid", etc.)
            - ["raw_json"]: performance data in json format
    """
    data_type = message["data"]["type"]
    machine = message["data"]["machine"]
    job_id = message["data"]["JobID"]
    # pipe this through the json module for consistent formatting
    # removing indentation to save space in the database
    raw_json = json.dumps(json.loads(message["data"]["raw_json"]), indent=0)
    new_db_entry = PerformanceData(
        simulation=Simulation.get(machine=machine, jobID=job_id),
        data_type=data_type,
        raw_json=raw_json,
    )
    print(
        "Performance data of job {} has been added to the database".format(
            new_db_entry.simulation.uuid
        )
    )


@workflow.handler
def initialise_performance_data(message):
    print("Initialise performance workflow for " + message["IncidentID"])

    try:
        registerEndpoint(message["IncidentID"], "add_performance_data", "add_performance_data")
    except ExternalDataInterfaceException as err:
        print("Error from EDI on registration for performance data "+err.message)

    workflow.setIncidentActive(message["IncidentID"])


# we have to register them with the workflow system
def RegisterHandlers():
    workflow.RegisterHandler(add_performance_data, "add_performance_data")
    workflow.RegisterHandler(initialise_performance_data, "initialise_performance_gathering")
