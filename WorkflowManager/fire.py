import workflow
import pony.orm as pny
from db import Incident
import datetime
import time




# we now want to define some handlers
@workflow.handler
@workflow.atomic
def fire_terrain_handler(message):
    print("In Fire terrain handler")
    time.sleep(1)

    workflow.send(message=message, queue="fire_simulation")


@workflow.handler
def fire_hotspot_handler(message):
    print("In Fire hotspot handler")
    time.sleep(1)

    workflow.send(message=message, queue="fire_simulation")


@workflow.handler
def fire_simulation_handler(message):
    incident = message["IncidentID"]

    workflow.GetLock("some_label", incident)

    print("In fire simulation handler")

    workflow.Persist.Put(incident=incident, dict={"originator": message["originator"]})

    logs = workflow.Persist.Get(incident)
    # print("Logs =",logs)

    test = 0
    terrain = 1
    hotspot = 2
    weather = 4

    for log in logs:
        if log["originator"] == "weather_results_handler":
            test = test | weather
            print("   Weather data available")
        elif log["originator"] == "fire_terrain_handler":
            test = test | terrain
            print("   Terrain data available")
        elif log["originator"] == "fire_hotspot_handler":
            test = test | hotspot
            print("   Hotspot data available")
    # print(test)

    if test == terrain | hotspot | weather:
        print("Running Fire Simulation")
        time.sleep(1)

        id = message["IncidentID"]
        workflow.Complete(id)
        print("Done!")
    else:
        print("Will do nothing - waiting for data")

    workflow.ReleaseLock("some_label", incident)


# we have to register them with the workflow system
workflow.RegisterHandler(fire_terrain_handler, "fire_terrain")
workflow.RegisterHandler(fire_hotspot_handler, "fire_hotspot")
workflow.RegisterHandler(fire_simulation_handler, "fire_simulation")
