import sys
# sys.path.append("../")
import pony.orm as pny
from Database.workflow import Simulation, Incident
from SimulationManager.client import createSimulation, submitSimulation, SimulationManagerException, cancelSimulation
from DataManager.client import moveDataViaDM, DataManagerException, getInfoForDataInDM, putByteDataViaDM, registerDataWithDM, copyDataViaDM
from manager import workflow
import yaml
import datetime

class WildfireDataAccessException(Exception):
    def __init__(self, msg):
        self.msg=msg

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
            sim_id=createSimulation(IncidentID, 1, "0:05:00", "Wildfire simulation", "wfa.sh", queuestate_callbacks=callbacks, template_dir="templates/wildfire_template")
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
    simulationIdPostfix=simulationId.split("-")[-1]
    directoryListing=msg["directoryListing"]
    print("\nResults available for wildfire analyst simulation!") 

    with pny.db_session:
        myincident = Incident[IncidentID]
        simulation=Simulation[simulationId]
        machine_name=simulation.machine.machine_name
        machine_basedir=simulation.machine.base_work_dir
        if machine_basedir[-1] != "/": machine_basedir+="/"

    if simulation is not None:
        result_files={}
        for entry in directoryListing:
            tokens=entry.split()
            if len(tokens) == 9 and ".tif" in tokens[8]:
                result_files[tokens[8]]=int(tokens[4])

        try:
            data_uuid_test_fire_best=_registerWFAResultFile("test_Fire_Best.tif", result_files, machine_name, simulation.directory, IncidentID)
            data_uuid_test_fireshed_best=_registerWFAResultFile("test_FireShed_Best.tif", result_files, machine_name, simulation.directory, IncidentID)
            data_uuid_test_variance=_registerWFAResultFile("test_Fire_Variance.tif", result_files, machine_name, simulation.directory, IncidentID)
            data_uuid_test_mean=_registerWFAResultFile("test_Fire_Mean.tif", result_files, machine_name, simulation.directory, IncidentID)
        except WildfireDataAccessException as err:
            with pny.db_session:
                simulation=Simulation[simulationId]
                simulation.status="ERROR"
                simulation.status_message=err.msg
                simulation.status_updated=datetime.datetime.now()
                pny.commit()
            return

        try:
            callbacks = {'COMPLETED': 'wildfire_post_results'}
            pp_sim_id=createSimulation(IncidentID, 1, "0:05:00", "Wildfire postprocessing", "wfapost.sh", queuestate_callbacks=callbacks, template_dir="templates/wildfire_post_template")
            with pny.db_session:
                post_proc_simulation=Simulation[pp_sim_id]
                post_proc_machine_name=post_proc_simulation.machine.machine_name                

            try:                 
                putByteDataViaDM("config.json", machine_name, "Wildfire post-processing configuration", "text/plain", "Wildfire workflow", 
                    "{\n  \"simDuration\": "+str(myincident.duration)+"\n}\n", path=post_proc_simulation.directory)

                putByteDataViaDM("sim_id", machine_name, "Wildfire post-processing simulation ID token", "text/plain", "Wildfire workflow", 
                    simulationIdPostfix, path=post_proc_simulation.directory)

                copyDataViaDM(data_uuid_test_fire_best, machine_basedir+post_proc_simulation.directory+"/input/normal/test_Fire_Best.tif", machine_name, gather_metrics=False)
                copyDataViaDM(data_uuid_test_fireshed_best, machine_basedir+post_proc_simulation.directory+"/input/fireshed/test_FireShed_Best.tif", machine_name, gather_metrics=False)
                copyDataViaDM(data_uuid_test_variance, machine_basedir+post_proc_simulation.directory+"/input/probabilistic/test_Fire_Variance.tif", machine_name, gather_metrics=False)
                copyDataViaDM(data_uuid_test_mean, machine_basedir+post_proc_simulation.directory+"/input/probabilistic/test_Fire_Mean.tif", machine_name, gather_metrics=False)
                
                #putByteDataViaDM("wfapost.yml", machine_name, "Wildfire post-processing configuration", "text/plain", "Wildfire workflow", 
                #    _buildWFAPostYaml(IncidentID, simulation.directory, machine_basedir), path=post_proc_simulation.directory)                    
            except DataManagerException as err:
                print("Can not write wildfire post processing configuration to simulation location"+err.message)
                return

            submitSimulation(pp_sim_id)
        except SimulationManagerException as err:
            print("Error creating or submitting WFA post-processing simulation "+err.message)
            return

def _registerWFAResultFile(filename, result_files, machine_name, directory, incidentId):
    if filename not in result_files:
        raise WildfireDataAccessException("Expected result file is not available from the simulation, this indicates the execution failed")
    try:                
        data_uuid=registerDataWithDM(filename, machine_name, "WFA simulation", "application/octet-stream", result_files[filename], 
            "GTIF", path=directory, associate_with_incident=True, incidentId=incidentId, kind="WFA output file", 
            comment="Created by WFA on "+machine_name)
        return data_uuid
    except DataManagerException as err:
        print("Error registering WFA result data with data manager, aborting "+err.message)
        raise WildfireDataAccessException("Error registering WFA result data with data manager on the VESTEC system")

@pny.db_session
def _buildWFAPostYaml(incidentId, simulation_directory, machine_basedir):
    myincident = Incident[incidentId]
    duration = myincident.duration

    if simulation_directory[-1] != "/": simulation_directory+="/"

    sample_configuration_file = open("wildfire/templates/wfapost.yml")
    yaml_template = yaml.load(sample_configuration_file, Loader=yaml.FullLoader)    
    yaml_template["normal_gtif"]["path"]=machine_basedir+simulation_directory+"test_Fire_Best.tif"
    yaml_template["fireshed_gtif"]["path"]=machine_basedir+simulation_directory+"test_FireShed_Best.tif"
    yaml_template["variance"]["path"]=machine_basedir+simulation_directory+"test_Fire_Variance.tif"
    yaml_template["mean"]["path"]=machine_basedir+simulation_directory+"test_Fire_Mean.tif"
    
    yaml_template["sim_duration"]=duration
        
    return yaml.dump(yaml_template)

@workflow.handler
def wildfire_post_results(msg):
    print("Post processing of WFA results completed")

    IncidentID = msg["IncidentID"]
    simulationId = msg["simulationId"]
    directoryListing=msg["directoryListing"]

    with pny.db_session:        
        simulation=Simulation[simulationId]
        machine_name=simulation.machine.machine_name        
    
    for entry in directoryListing:
        tokens=entry.split()
        if len(tokens) == 9 and ".png" in tokens[8]:            
            try:                
                registerDataWithDM(tokens[8], machine_name, "WFA post-processing", "image/png", int(tokens[4]), "WFA output PNG", 
                    path=simulation.directory, associate_with_incident=True, incidentId=IncidentID, kind="WFA image file", 
                    comment="Created by WFA post-processor on "+machine_name)
            except DataManagerException as err:
                print("Error registering WFA post-processed PNG '"+tokens[8]+"' with data manager, aborting "+err.message)            

def RegisterHandlers():
    workflow.RegisterHandler(wildfire_fire_simulation,"wildfire_fire_simulation")
    workflow.RegisterHandler(wildfire_fire_static,"wildfire_fire_static")
    workflow.RegisterHandler(wildfire_fire_results,"wildfire_fire_results")
    workflow.RegisterHandler(wildfire_post_results,"wildfire_post_results")
