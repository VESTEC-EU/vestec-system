import sys
sys.path.append("../")
import pony.orm as pny
from Database.workflow import Simulation
from SimulationManager.client import createSimulation, submitSimulation, SimulationManagerException, cancelSimulation
from DataManager.client import moveDataViaDM, DataManagerException, getInfoForDataInDM, putByteDataViaDM
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
        
    #if originator == "wildfire_fire_static":
    #    print("Static data received")
    #    workflow.Persist.Put(IncidentID,{"originator": originator, "file": file})
    #el
    if originator == "wildfire_mesonh_results":
        print("MesoNH forecast data received")
        workflow.Persist.Put(IncidentID,{"originator": originator, "weather_data_uuid":  msg["weather_data_uuid"]})
    elif originator == "wildfire_tecnosylva_hotspots":
        print("Hotspots from Tecnosylva received")
        workflow.Persist.Put(IncidentID,{"originator": originator, "hotspot_data_uuid":  msg["hotspot_data_uuid"]})
    else:
        raise ValueError("Unexpected originator %s"%originator)

    logs = workflow.Persist.Get(IncidentID)

    #get the latest data for all 3 required data types
    #staticFile = None
    hotspotDataUUID = None
    weatherDataUUID = None
    for log in logs:
        if log["originator"] == "wildfire_fire_static":
            staticFile = log["file"]
        elif log["originator"] == "wildfire_tecnosylva_hotspots":
            hotspotDataUUID = log["hotspot_data_uuid"]
        elif log["originator"] == "wildfire_mesonh_results":
            weatherDataUUID = log["weather_data_uuid"]

    #if staticFile is not None and hotspotFile is not None and weatherFile is not None:
    if hotspotDataUUID and weatherDataUUID is not None:
        print("Dependencies met for WFA")

        try:
            callbacks = {'COMPLETED': 'wildfire_fire_results'}   
            sim_id=createSimulation(IncidentID, 1, "0:05:00", "Wildfire simulation", "run.sh", queuestate_callbacks=callbacks, template_dir="wildfire_template")
            with pny.db_session:
                simulation=Simulation[sim_id]    
                machine_name=simulation.machine.machine_name
                machine_basedir=simulation.machine.base_work_dir
                if machine_basedir[-1] != "/": machine_basedir+="/"

            moveDataViaDM(hotspotDataUUID, machine_basedir+simulation.directory+"/CONFIG_PROB_DYN.json", machine_name)

            try:
                data_info=getInfoForDataInDM(weatherDataUUID)
                weather_loc="Weather data is located at "+data_info["absolute_path"]
                putByteDataViaDM("weather_data.txt", machine_name, "WFA weather location", "Wildfire workflow", weather_loc, path=simulation.directory)                 
            except DataManagerException as err:
                print("Can not retrieve DM information for weather data or write this to simulation location"+err.message)
                return
            
            cancelSimulation(sim_id)

        except SimulationManagerException as err:
            print("Error creating or submitting WFA simulation "+err.message)
            return
        
@workflow.handler
def wildfire_fire_results(msg):
    print("\nResults available for wildfire analyst simulation!")
    print("Simulation 'id' is %s"%msg["file"])

def RegisterHandlers():
    workflow.RegisterHandler(wildfire_fire_simulation,"wildfire_fire_simulation")
    workflow.RegisterHandler(wildfire_fire_static,"wildfire_fire_static")
    workflow.RegisterHandler(wildfire_fire_results,"wildfire_fire_results")
