import sys
sys.path.append("../")
import pony.orm as pny
from Database.workflow import Simulation, Incident
from SimulationManager.client import createSimulation, submitSimulation, SimulationManagerException, cancelSimulation
from DataManager.client import moveDataViaDM, DataManagerException, getInfoForDataInDM, putByteDataViaDM, registerDataWithDM
import workflow
import yaml

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
            weather_data_info=getInfoForDataInDM(weatherDataUUID)            
        except DataManagerException as err:
            print("Can not retrieve DM information for weather data "+err.message)
            return

        try:
            callbacks = {'COMPLETED': 'wildfire_fire_results'}
            sim_id=createSimulation(IncidentID, 1, "0:05:00", "Wildfire simulation", "wfa.sh", queuestate_callbacks=callbacks, template_dir="wildfire_template")
            with pny.db_session:
                simulation=Simulation[sim_id]    
                machine_name=simulation.machine.machine_name
                machine_basedir=simulation.machine.base_work_dir
                if machine_basedir[-1] != "/": machine_basedir+="/"

            moveDataViaDM(hotspotDataUUID, machine_basedir+simulation.directory+"/WFA_hotspots.json", machine_name)

            try:                
                putByteDataViaDM("wfa.yml", machine_name, "Wildfire configuration", "text/plain", "Wildfire workflow", _buildWFAYaml(IncidentID, weather_data_info), path=simulation.directory)                 
            except DataManagerException as err:
                print("Can not write wildfire configuration to simulation location"+err.message)
                return

            submitSimulation(sim_id)
        except SimulationManagerException as err:
            print("Error creating or submitting WFA simulation "+err.message)
            return

@pny.db_session
def _buildWFAYaml(incidentId, weather_datainfo):
    myincident = Incident[incidentId]
    upperLeft = myincident.upper_left_latlong
    lowerRight = myincident.lower_right_latlong
    duration = myincident.duration
            
    upperLeftLon, upperLeftLat = upperLeft.split("/")
    lowerRightLon, lowerRightLat = lowerRight.split("/")

    sample_configuration_file = open("wildfire/templates/wfa.yml")
    yaml_template = yaml.load(sample_configuration_file, Loader=yaml.FullLoader)    
    yaml_template["upperleft"]["lat"]=float(upperLeftLat)
    yaml_template["upperleft"]["lon"]=float(upperLeftLon)
    yaml_template["lowerright"]["lat"]=float(lowerRightLat)
    yaml_template["lowerright"]["lon"]=float(lowerRightLon)

    yaml_template["weather_data"]["path"]=weather_datainfo["absolute_path"]
    yaml_template["dynamic_config"]["path"]="WFA_hotspots.json"
    yaml_template["sim_duration"]=duration
        
    return yaml.dump(yaml_template)
        
@workflow.handler
def wildfire_fire_results(msg):
    IncidentID = msg["IncidentID"]
    simulationId = msg["simulationId"]
    print("\nResults available for wildfire analyst simulation!") 

    with pny.db_session:
        simulation=Simulation[simulationId]
        machine_name=simulation.machine.machine_name

    if simulation is not None:
        try:                
            data_uuid_test_fire_best=registerDataWithDM("test_Fire_Best.tif", machine_name, "WFA simulation", "application/octet-stream", 0, "Normal GTIF", 
                path=simulation.directory, associate_with_incident=True, incidentId=IncidentID, kind="WFA output file", 
                comment="Created by WFA on "+machine_name)
            data_uuid_test_fireshed_best=registerDataWithDM("test_FireShed_Best.tif", machine_name, "WFA simulation", "application/octet-stream", 0, "FireShed GTIF", 
                path=simulation.directory, associate_with_incident=True, incidentId=IncidentID, kind="WFA output file", 
                comment="Created by WFA on "+machine_name)
            data_uuid_test_variance=registerDataWithDM("test_Fire_Variance.tif", machine_name, "WFA simulation", "application/octet-stream", 0, "Variance GTIF", 
                path=simulation.directory, associate_with_incident=True, incidentId=IncidentID, kind="WFA output file", 
                comment="Created by WFA on "+machine_name)
            data_uuid_test_mean=registerDataWithDM("test_Fire_Mean.tif", machine_name, "WFA simulation", "application/octet-stream", 0, "Mean GTIF", 
                path=simulation.directory, associate_with_incident=True, incidentId=IncidentID, kind="WFA output file", 
                comment="Created by WFA on "+machine_name)
        except DataManagerException as err:
            print("Error registering WFA result data with data manager "+err.message)
            return   

def RegisterHandlers():
    workflow.RegisterHandler(wildfire_fire_simulation,"wildfire_fire_simulation")
    workflow.RegisterHandler(wildfire_fire_static,"wildfire_fire_static")
    workflow.RegisterHandler(wildfire_fire_results,"wildfire_fire_results")
