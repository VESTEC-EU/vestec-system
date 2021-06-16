import sys
#sys.path.append("../")
from manager import workflow
import os
import pony.orm as pny
import datetime
import time
import json
from base64 import b64decode
from Database import LocalDataStorage
from Database.workflow import Simulation
from DataManager.client import registerDataWithDM, putByteDataViaDM, DataManagerException
from SimulationManager.client import createSimulation, submitSimulation, SimulationManagerException
from ExternalDataInterface.client import registerEndpoint, ExternalDataInterfaceException, removeEndpoint
from time import sleep


@workflow.handler
def data_transfer(message):
    print("Hello")
    workflow.Complete(message["IncidentID"])


@workflow.handler
def initialise_data_transfer(message):
    print("Initialise handlers for " + message["IncidentID"])
    try:
        print("Register Endpoint for initialise data transfer " + message["IncidentID"])
        #registerEndpoint(message["IncidentID"], "shutdown_data_transfer", "shutdown_data_transfer")
    except: ExternalDataInterfaceException as err:
        print("Error from EDI on registration " + err.message)

    workflow.setIncidentActive(message["IncidentID"])
    workflow.send(queue = "data_transfer", message = message)

@workflow.handler
def shutdown_data_transfer(message):
    print("Shutdown data transfer workflow for " + message["IncidentID"])
    try:
        removeEndpoint(message["IncidentID"], "shutdown_data_transfer", "shutdown_data_transfer")
    except: ExternalDataInterfaceException as err:
        print("Error from EDI on enpoint removal " + err.message)
    workflow.Cancel(message["IncidentID"])



def RegisterHandlers():
    workflow.RegisterHandler(initialise_data_transfer, "initialise_data_transfer")
    workflow.RegisterHandler(shutdown_data_transfer, "shutdown_data_transfer")
    workflow.RegisterHandler(data_transfer, "data_transfer")
