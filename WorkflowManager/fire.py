import workflow
import pony.orm as pny
from db import Incident
import datetime
import time

#we only need to import MesoNH because we use a persistence variable for this demo. 
import MesoNH

#dummy variables to persist whether a step in the workflow is done or not
terrain_done=False
hotspot_done=False



#we now want to define some handlers
@workflow.handler
def fire_terrain_handler(message):
    print("In Fire terrain handler")
    time.sleep(1)
    global terrain_done
    terrain_done=True
    

    workflow.send(message=message,queue="fire_simulation")
   

@workflow.handler
def fire_hotspot_handler(message):
    print("In Fire hotspot handler")
    time.sleep(1)

    global hotspot_done
    hotspot_done=True

    workflow.send(message=message,queue="fire_simulation")


@workflow.handler
def fire_simulation_handler(message):
    global terrain_done
    global hotspot_done
    print("In fire simulation handler")
    print("   Terrain data available? - ",terrain_done)
    print("   Hotspot data available? - ",hotspot_done)
    print("   Weather data available? - ",MesoNH.weather_done)

    if terrain_done and hotspot_done and MesoNH.weather_done:
        print("Running Fire Simulation")
        time.sleep(1)

        terrain_done=False
        hotspot_done=False
        MesoNH.weather_done=False

        with pny.db_session:
            id = message["IncidentID"]
            fire = Incident[id]
            fire.status = "COMPLETE"
            fire.date_completed = datetime.datetime.now()
        print("Done!")
    else:
        print("Will do nothing - waiting for data")



#and now we register them with the workflow system
workflow.RegisterHandler(fire_terrain_handler,"fire_terrain")
workflow.RegisterHandler(fire_hotspot_handler,"fire_hotspot")
workflow.RegisterHandler(fire_simulation_handler,"fire_simulation")

