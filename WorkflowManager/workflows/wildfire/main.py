import sys
# sys.path.append("../")
# sys.path.append("../../")
from manager import workflow
import pony.orm as pny
from Database import Incident

from . import mesoNH
from . import hotspots
from . import wildfire

@workflow.handler
def wildfire_init(msg):
    IncidentID = msg["IncidentID"]

    with pny.db_session:
        myincident = Incident[IncidentID]
        upperLeft = myincident.upper_left_latlong
        lowerRight = myincident.lower_right_latlong
        duration = myincident.duration
        if upperLeft is None or lowerRight is None or duration is None:            
            raise Exception("Must include location extents and duration for wildfire simulation")

        if len(upperLeft.split("/")) != 2 or len(lowerRight.split("/")) != 2:
            raise Exception("Location extents must be of the form longitude/latitude")

        try:
            upperLeftLon, upperLeftLat = upperLeft.split("/")
            lowerRightLon, lowerRightLat = lowerRight.split("/")
    
            float(upperLeftLat)
            float(upperLeftLon)
            float(lowerRightLat)
            float(lowerRightLon)
        except ValueError:
            raise Exception("Longitudes and latitudes must be floating point numbers")    

    print("\nSetting up wildfire incident %s"%IncidentID)
    workflow.setIncidentActive(IncidentID)

    workflow.send(queue="wildfire_mesonh_init", message=msg)
    workflow.send(queue="wildfire_hotspot_init", message=msg)
    #workflow.send(queue="wildfire_fire_static", message=msg)

@workflow.handler
def wildfire_shutdown(msg):    
    workflow.send(queue="wildfire_mesonh_shutdown", message=msg)
    workflow.send(queue="wildfire_hotspot_shutdown", message=msg)    

@workflow.atomic
@workflow.handler
def wildfire_shutdown_response(msg):
    IncidentID = msg["IncidentID"]
    originator = msg["originator"]
    workflow.Persist.Put(IncidentID, {"type": "shutdown", "originator": originator})

    logs = workflow.Persist.Get(IncidentID)
    mesoNHFinished = False
    hotspotFinished = False
    for log in logs:
        if "type" in log and log["type"] == "shutdown":
            if log["originator"] == "wildfire_mesonh_shutdown": mesoNHFinished=True
            if log["originator"] == "wildfire_hotspot_shutdown": hotspotFinished=True            

    if (mesoNHFinished and hotspotFinished): workflow.Cancel(msg["IncidentID"])

def RegisterHandlers():
    workflow.RegisterHandler(handler = wildfire_init,queue="wildfire_init")
    workflow.RegisterHandler(handler = wildfire_shutdown,queue="wildfire_shutdown")
    workflow.RegisterHandler(handler = wildfire_shutdown_response,queue="wildfire_shutdown_response")
    hotspots.RegisterHandlers()
    mesoNH.RegisterHandlers()
    wildfire.RegisterHandlers()
