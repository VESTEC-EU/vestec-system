import sys
sys.path.append("../")

import workflow

@workflow.handler
def wildfire_fire_static(msg):
    print("\nPreparing static data for wildfire analyst")

    msg["file"] = "Static wildfire analyst file"

    workflow.send(msg,"wildfire_fire_simulation")

@workflow.atomic
@workflow.handler
def wildfire_fire_simulation(msg):
    print("\nWildfire fire simulation handler")
    IncidentID = msg["IncidentID"]
    originator = msg["originator"]
    
    file = msg["file"]
    if originator == "wildfire_fire_static":
        print("Static data received")
        workflow.Persist.Put(IncidentID,{"originator": originator, "file": file})
    elif originator == "wildfire_mesonh_results":
        print("MesoNH forecast data received")
        workflow.Persist.Put(IncidentID,{"originator": originator, "file": file})
    elif originator == "wildfire_tecnosylva_hotspots":
        print("Hotspots from Tecnosylva received")
        workflow.Persist.Put(IncidentID,{"originator": originator, "file": file})
    else:
        raise ValueError("Unexpected originator %s"%originator)

    logs = workflow.Persist.Get(IncidentID)

    #get the latest data for all 3 required data types
    staticFile = None
    hotspotFile = None
    weatherFile = None
    for log in logs:
        if log["originator"] == "wildfire_fire_static":
            staticFile = log["file"]
        elif log["originator"] == "wildfire_tecnosylva_hotspots":
            hotspotFile = log["file"]
        elif log["originator"] == "wildfire_mesonh_results":
            weatherFile = log["file"]

    if staticFile is not None and hotspotFile is not None and weatherFile is not None:
        print("Dependencies met! We can run a simulation!")
        print("Input files are:")
        print("    Static: %s"%staticFile)
        print("    hotspot: %s"%hotspotFile)
        print("    weather: %s"%weatherFile)

        message = {
            "IncidentID": IncidentID,
            "file": staticFile+hotspotFile+weatherFile
        }

        workflow.send(message,"wildfire_fire_results")
    else:
        print("Dependencies are not met yet. Nothing to do")
    

        
@workflow.handler
def wildfire_fire_results(msg):
    print("\nResults available for wildfire analyst simulation!")
    print("Simulation 'id' is %s"%msg["file"])

    
    




def RegisterHandlers():
    workflow.RegisterHandler(wildfire_fire_simulation,"wildfire_fire_simulation")
    workflow.RegisterHandler(wildfire_fire_static,"wildfire_fire_static")
    workflow.RegisterHandler(wildfire_fire_results,"wildfire_fire_results")

