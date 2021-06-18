import sys
#sys.path.append("../")
from manager import workflow
import os
import pony.orm as pny
import datetime
import time
import json
import requests
from base64 import b64decode
from Database import LocalDataStorage, LogType
from Database.workflow import Simulation
from DataManager.client import getLocalFilePathPrepend, registerDataWithDM, putByteDataViaDM, downloadDataToTargetViaDM, DataManagerException
from SimulationManager.client import createSimulation, submitSimulation, SimulationManagerException
from ExternalDataInterface.client import registerEndpoint, ExternalDataInterfaceException, removeEndpoint
from time import sleep

from .utils import logfile
from Utils.log import VestecLogger

logger = VestecLogger("Testsuite")

#figure out how to import that later
def yyyymmdd(date):
    year = date.year
    month = date.month
    day = date.day

    return "%04d%02d%02d"%(year,month,day)

def yyyymm(date):
    year = date.year
    month = date.month

    return "%04d%02d"%(year,month)

def tryURL(url):
    try:
        r = requests.head(url,timeout = 5.0)
        #print(r.status_code)
        if r.status_code == 200:
            return True
    except requests.exceptions.Timeout:
        print("Warning, timeout on searching for new GFS data")
    return False

#returns the two latest GFS results
def getLatestURLs(verbose = False):


    baseURL = "https://www.ncei.noaa.gov/data/global-forecast-system/access/grid-003-1.0-degree/analysis"
    #baseURL = "https://www.ncei.noaa.gov/data/global-forecast-system/access/grid-003-1.0-degree/forecast"


    today = datetime.date.today()
    oneday = datetime.timedelta(days=1)

    urls = []

    if verbose: print("Checking for new weather data...")

    for i in range(10):
        day = today - i*oneday

        monthstr = yyyymm(day)
        daystr = yyyymmdd(day)

        dayURL = os.path.join(baseURL,monthstr,daystr)+"/"
        # print("")
        # print(daystr)

        if not tryURL(dayURL):
            # print("No data")
            continue

        if verbose: print("Page for %s exists! This is %d days old"%(day,i))

        for time in ["1800","1200","0600","0000"]:
            num = "000"
            base = "gfs_3_%s_%s_%s.grb2"%(daystr,time,num)
            fileURL = os.path.join(dayURL,base)
            # print("    %s"%fileURL)
            if tryURL(fileURL):
                if verbose: print('Timestamp is %s'%time)
                urls.append(fileURL)
                #if we have 2 urls, we are done and can return this
                if len(urls) == 2:
                    #reverse the order so the oldest is first
                    urls.reverse()
                    return urls
            else:
                continue
                # print("Does not exist")

    if verbose: print("Only %s url found"%len(urls))
    return urls

# Get the URL of the newest weather-data and download ist
@workflow.handler
def data_transfer(message):
    IncidentID = message["IncidentID"]

    latestURL = getLatestURLs()

    if len(latestURL) == 0:
        print("No URLs found")
        return
    else:
        print(latestURL)
        weather_data_filenames=[]
        weather_data_uuids=[]
        for url in latestURL:
            filename=os.path.split(url)[1]
            weather_data_filenames.append(filename)
            try:
                weather_data_uuids.append(downloadDataToTargetViaDM(filename = filename, machine = "localhost" ,originator = "gfs Weather data",
                description = "weather data", type = "gfs", url = url, protocol = "https", path="data/" + IncidentID, associate_with_incident=True, incidentId=IncidentID))
                print("Downloaded Data to localhost")
            except DataManagerException as err:
                print("Error downloading GFS weather data to target machine " + err.message)
                return

    workflow.Complete(message["IncidentID"])

# Initalise all handlers and the logger. Create a directory to store the
# created data. Activate the data-transfer
@workflow.handler
def initialise_data_transfer(message):
    IncidentID = message["IncidentID"]
    print("Initialise handlers for " + IncidentID)

    #create a directory to store the data
    logdir = os.path.join(getLocalFilePathPrepend(), "data", IncidentID)
    logger.Log(type=LogType.Activity, comment="Started transfer-test",incidentId =IncidentID)
    os.makedirs(logdir)

    try:
        print("Register Endpoint for initialise data transfer " + message["IncidentID"])
        registerEndpoint(message["IncidentID"], "shutdown_data_transfer", "shutdown_data_transfer")
    except ExternalDataInterfaceException as err:
        print("Error from EDI on registration " + err.message)

    workflow.setIncidentActive(message["IncidentID"])
    workflow.send(queue = "data_transfer", message = message)

#remove endpoint and all remaining data
@workflow.handler
def shutdown_data_transfer(message):
    print("Shutdown data transfer workflow for " + message["IncidentID"])
    data_uuids = message["weather_data"]
    for uuid in data_uuids:
        try:
            client.deleteDataViaDM(uuid)
        except client.DataManagerException as err:
            print("Error deleting weather data: " + err.message)
    try:
        removeEndpoint(message["IncidentID"], "shutdown_data_transfer", "shutdown_data_transfer")
    except ExternalDataInterfaceException as err:
        print("Error from EDI on enpoint removal " + err.message)
    workflow.Cancel(message["IncidentID"])


def RegisterHandlers():
    workflow.RegisterHandler(initialise_data_transfer, "initialise_data_transfer")
    workflow.RegisterHandler(shutdown_data_transfer, "shutdown_data_transfer")
    workflow.RegisterHandler(data_transfer, "data_transfer")
