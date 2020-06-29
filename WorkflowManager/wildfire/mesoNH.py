import sys
sys.path.append("../")
import os
import requests
import pony.orm as pny


import workflow
from .weatherdata import getLatestURL

from Database import Incident


if "VESTEC_SM_URI" in os.environ:
    SM_URL= os.environ["VESTEC_SM_URI"]
else:
    SM_URL = 'http://localhost:5505/SM'

if "VESTEC_EDI_URI" in os.environ:
    EDI_URL = os.environ["VESTEC_EDI_URI"]
else:
    EDI_URL= 'http://localhost:5501/EDImanager'

if "VESTEC_DM_URI" in os.environ:
    DATA_MANAGER_URL = os.environ["VESTEC_DM_URI"]
else:
    DATA_MANAGER_URL = 'http://localhost:5000/DM'


#initialises the mesoNH part of the workflow
@workflow.handler
def wildfire_mesonh_init(msg):
    IncidentID = msg["IncidentID"]
    print("\nInitialising MesoNH sub-workflow")

    #register EDI to poll for GFS data
    myobj = {
        'queuename': 'wildfire_mesonh_getdata',
        'incidentid': IncidentID, 
        'endpoint': "https://www.ncei.noaa.gov/data/global-forecast-system/access/grid-003-1.0-degree/analysis",
        "pollperiod": 3600
            }
    x = requests.post(EDI_URL+"/register", json = myobj)
    if x.status_code != 200:
        raise Exception("Failed to register for GFS download")
    else:
        print("Registered EDI to poll for GFS data")
    
    workflow.send(msg,"wildfire_mesonh_physiographic")


#Sees if there is new GFS data available. If so, downloads it [not implemented yet] and sends this on to the simulation stage
@workflow.handler
def wildfire_mesonh_getdata(msg):
    IncidentID = msg["IncidentID"]
    print("\nGetting global forecast data...")
    url = getLatestURL()
    if url is not None:
        print("URL is %s"%url)

    
    logs=workflow.Persist.Get(IncidentID)
    for log in logs:
        if log["url"] == url:
            print("This data has already been fetched. Nothing to do")
            return

    print('This is new data!')
    workflow.Persist.Put(IncidentID,{"url": url})

    msg["url"] = url
    
    workflow.send(msg,"wildfire_mesonh_simulation")


#extracts [not implemented] physiographic data and passes this onto the simulation stage
@workflow.handler
def wildfire_mesonh_physiographic(msg):
    IncidentID = msg["IncidentID"]
    
    print("\nExtracting physiographic data from region for MesoNH")
    try:
        with pny.db_session:
            i = Incident[IncidentID]
            upperLeft = i.upper_left_latlong
            lowerRight = i.lower_right_latlong
            
            lonmin, latmax = upperLeft.split("/")
            lonmax, latmin = lowerRight.split("/")

            lonmin = float(lonmin)
            latmax = float(latmax)
            lonmax = float(lonmax)
            latmin = float(latmin)
    except Exception as e:
        raise ValueError("Unable to parse region coordinates") from e
    print("Latmin,latmax = %f, %f"%(latmin,latmax))
    print("Lonmin,Lonmax = %f, %f"%(lonmin,lonmax))

    #do something here to clip the physiographic data
    
    workflow.send(msg,"wildfire_mesonh_simulation")


#logs any new messages appropriately, then sees if the criteria are met to run a simulation. If so, it runs [not implemented] the simulation
@workflow.atomic
@workflow.handler
def wildfire_mesonh_simulation(msg):
    IncidentID = msg["IncidentID"]
    originator = msg["originator"]

    print("\nMesoNH simulation")

    if originator == "wildfire_mesonh_physiographic":
        workflow.Persist.Put(IncidentID,{"originator": originator, "Physiographic": True})
        print("Physiographic data received")
        

    elif originator == "wildfire_mesonh_getdata":
        workflow.Persist.Put(IncidentID,{"originator": originator, "url": msg["url"]})
        print('New weather forecast received')
    
    else:
        raise ValueError("Unexpected originator: %s"%originator)

    #now check if we need to do anything

    logs = workflow.Persist.Get(IncidentID)

    #check for physiographic data
    physiographic = False
    for log in logs:
        if log["originator"] == "wildfire_mesonh_physiographic":
            if log["Physiographic"]:
                physiographic = True
    
    latest = None
    
    #go through logs and get the latest url
    for log in logs:
        if log["originator"] == "wildfire_mesonh_getdata":
            latest = log["url"]
    
    if latest is None or physiographic == False:
        print("Nothing to be done yet. Missing dependencies")
        return
    
    print("Can now run a simulation!")

    #insert code to write a simulation here
    

    #this just forwards dummy stuff to the simulation results handler
    dummy, file = os.path.split(latest)
    workflow.send({"IncidentID": IncidentID, "file": file},"wildfire_mesonh_results")
    

#handles simulation results from a mesoNH simulation (at)
@workflow.handler
def wildfire_mesonh_results(msg):
    IncidentID = msg["IncidentID"]
    file = msg["file"]
    
    print('\nGot MesoNH results')
    print("File: %s"%file)

    workflow.send(msg,"wildfire_fire_simulation")






def RegisterHandlers():
    workflow.RegisterHandler(handler = wildfire_mesonh_getdata,queue="wildfire_mesonh_getdata")
    workflow.RegisterHandler(handler = wildfire_mesonh_init,queue="wildfire_mesonh_init")
    workflow.RegisterHandler(handler = wildfire_mesonh_physiographic,queue="wildfire_mesonh_physiographic")
    workflow.RegisterHandler(handler = wildfire_mesonh_simulation,queue="wildfire_mesonh_simulation")
    workflow.RegisterHandler(handler = wildfire_mesonh_results,queue="wildfire_mesonh_results")




