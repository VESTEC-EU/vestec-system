import workflow
import pony.orm as pny
from db import Incident
import datetime
import time


# we now want to define some handlers
@workflow.handler
def fire_terrain_handler(message):
    print("In Fire terrain handler")
    time.sleep(1)

    workflow.send(message=message, queue="fire_simulation")


@workflow.handler
def fire_hotspot_handler(message):
    print("In Fire hotspot handler")
    time.sleep(1)

    workflow.send(message=message, queue="fire_simulation")


@workflow.atomic
@workflow.handler
def fire_simulation_handler(message):
    incident = message["IncidentID"]

    print("In fire simulation handler")

    workflow.Persist.Put(incident=incident, data={"originator": message["originator"]})

    records = workflow.Persist.Get(incident)

    test = 0
    terrain = 1
    hotspot = 2
    weather = 4

    for record in records:
        if record["originator"] == "weather_results_handler":
            test = test | weather
            print("   Weather data available")
        elif record["originator"] == "fire_terrain_handler":
            test = test | terrain
            print("   Terrain data available")
        elif record["originator"] == "fire_hotspot_handler":
            test = test | hotspot
            print("   Hotspot data available")

    if test == terrain | hotspot | weather:
        print("Running Fire Simulation")
        time.sleep(1)
        workflow.send(message=message, queue="fire_results")
    else:
        print("Will do nothing - waiting for data")

@workflow.handler
def fire_results_handler(msg):
    incident=msg["IncidentID"]

    print("Fire simulation results available")
    time.sleep(1)
    
    workflow.Complete(incident)

workflow.RegisterHandler(fire_results_handler,"fire_results")




# we have to register them with the workflow system
workflow.RegisterHandler(fire_terrain_handler, "fire_terrain")
workflow.RegisterHandler(fire_hotspot_handler, "fire_hotspot")
workflow.RegisterHandler(fire_simulation_handler, "fire_simulation")
