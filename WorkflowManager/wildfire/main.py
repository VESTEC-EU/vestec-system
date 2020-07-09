import sys
sys.path.append("../")

import workflow

from . import mesoNH
from . import hotspots
from . import wildfire

@workflow.handler
def wildfire_init(msg):
    IncidentID = msg["IncidentID"]

    print("\nSetting up wildfire incident %s"%IncidentID)
    workflow.setIncidentActive(IncidentID)

    workflow.send(queue="wildfire_mesonh_init", message=msg)
    workflow.send(queue="wildfire_hotspot_init", message=msg)
    #workflow.send(queue="wildfire_fire_static", message=msg)

@workflow.handler
def wildfire_shutdown(msg):    
    workflow.send(queue="wildfire_mesonh_shutdown", message=msg)
    workflow.send(queue="wildfire_hotspot_shutdown", message=msg)    

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
