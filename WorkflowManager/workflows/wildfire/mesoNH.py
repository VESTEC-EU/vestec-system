import sys
# sys.path.append("../")
# sys.path.append("../../")
import os
import requests
import pony.orm as pny
import yaml
import datetime
from manager import workflow
from .weatherdata import getLatestURLs

from Database import Incident
from Database.workflow import Simulation
from ExternalDataInterface.client import registerEndpoint, ExternalDataInterfaceException, removeEndpoint
from SimulationManager.client import createSimulation, submitSimulation, SimulationManagerException, cancelSimulation
from DataManager.client import putByteDataViaDM, DataManagerException, registerDataWithDM, downloadDataToTargetViaDM, getInfoForDataInDM

@workflow.handler
def wildfire_mesonh_init_standalone(msg):
    IncidentID = msg["IncidentID"]
    _handle_init(msg, "wildfire_mesonh_init_standalone")
    workflow.setIncidentActive(IncidentID)

#initialises the mesoNH part of the workflow
@workflow.handler
def wildfire_mesonh_init(msg):
    _handle_init(msg, "wildfire_mesonh_init")

def _handle_init(msg, providedCaller):
    IncidentID = msg["IncidentID"]
    print("\nInitialising MesoNH sub-workflow")

    try:
        registerEndpoint(IncidentID, "https://www.ncei.noaa.gov/data/global-forecast-system/access/grid-003-1.0-degree/analysis", "wildfire_mesonh_getdata", 3600)
        print("Registered EDI to poll for GFS data")
    except ExternalDataInterfaceException as err:
        print("Failed to register for GFS download "+err.message)
        return
        
    workflow.send(msg,"wildfire_mesonh_physiographic", providedCaller=providedCaller)


@workflow.handler
def wildfire_mesonh_shutdown_standalone(msg):
    IncidentID = msg["IncidentID"]
    _handle_shutdown(IncidentID)
    workflow.Cancel(IncidentID)

@workflow.handler
def wildfire_mesonh_shutdown(msg):
    IncidentID = msg["IncidentID"]
    _handle_shutdown(IncidentID)
    workflow.send(msg, "wildfire_shutdown_response")

def _handle_shutdown(IncidentID):
    try:
        removeEndpoint(IncidentID, "https://www.ncei.noaa.gov/data/global-forecast-system/access/grid-003-1.0-degree/analysis", "wildfire_mesonh_getdata", 3600)        
    except ExternalDataInterfaceException as err:
        print("Failed to remove MesoNH for GFS download "+err.message)

#Sees if there is new GFS data available. If so, downloads it [not implemented yet] and sends this on to the simulation stage
@workflow.handler
def wildfire_mesonh_getdata(msg):
    IncidentID = msg["IncidentID"]
    print("\nGetting global forecast data...")

    #return the two (at most) latest URLs, oldest first
    urls = getLatestURLs()
    
    if len(urls) == 0:
        print("No URLs found")
        return

    #get the list of URLs we already know about
    logs=workflow.Persist.Get(IncidentID)
    
    #flag to determine if any of the above fetched URLS are new
    anynew = False

    #for each url, see if it is already known. If not, download it
    for url in urls:
        exists = False
        for log in logs:
            if log["url"] == url:
                exists = True
    
        if not exists:
            anynew = True
            print("New URL: %s"%url)
            # Persist these, will DL onto target machine when we know what it is
            workflow.Persist.Put(IncidentID,{"url": url})
    
    #if there is new data, send it onto the MesoNH simulation step
    if anynew:
        #get the persisted logs again (this time with any new data added)
        logs = workflow.Persist.Get(IncidentID)
        
        #if we have at least 2 forecasts
        if len(logs) >= 2:
            logs = logs[-2:]
            
            #get the filenames THIS SHOULD BE THE UUID OF THE FILES IN THE DM
            urls=[]
            for log in logs:
                #dummy, file = os.path.split(log["url"])
                urls.append(log["url"])
            
            msg["urls"] = urls

            print("Sending latest 2 weather observations to wildfire_mesonh_simulation")
        
            workflow.send(msg,"wildfire_mesonh_simulation")
        else:
            print("New data, but insufficient observations for a MesoNH simulation")
    else:
        print("No new weather observations")

#extracts [not implemented] physiographic data and passes this onto the simulation stage
@workflow.handler
def wildfire_mesonh_physiographic(msg):
    IncidentID = msg["IncidentID"]
    
    print("\nExtracting physiographic data from region for MesoNH")  
    with pny.db_session:      
        i = Incident[IncidentID]
    upperLeft = i.upper_left_latlong
    lowerRight = i.lower_right_latlong
            
    upperLeftLat, upperLeftLon = upperLeft.split("/")
    lowerRightLat, lowerRightLon = lowerRight.split("/")

    sample_configuration_file = open("workflows/wildfire/templates/prep_pgd.yml")
    yaml_template = yaml.load(sample_configuration_file, Loader=yaml.FullLoader)
    yaml_template["upperleft"]["lat"]=float(upperLeftLat)
    yaml_template["upperleft"]["lon"]=float(upperLeftLon)
    yaml_template["lowerright"]["lat"]=float(lowerRightLat)
    yaml_template["lowerright"]["lon"]=float(lowerRightLon)

    print ("Upper Left lat " + str(upperLeftLat))
    print ("Upper Left lon " + str(upperLeftLon))
    print ("Lower right lat " + str(lowerRightLat))
    print ("Lower right lon " + str(lowerRightLon))

    try:
        callbacks = {'COMPLETED': 'wildfire_mesonh_simulation'}   
        sim_id=createSimulation(IncidentID, 1, "00:10", "PGD pre-processing", "prep_pgd.sh", queuestate_callbacks=callbacks, template_dir="templates/prep_pgd_template")
 #       sim_id=createSimulation(IncidentID, 1, "00:10", "test run", "helloworld.srun", callbacks, template_dir="templates/prep_pgd_template")

        with pny.db_session:
            simulation=Simulation[sim_id]   
            machine_name=simulation.machine.machine_name   
        try:
            data_uuid=putByteDataViaDM("prep_pgd.yml", machine_name, "PGD pre-processing YAML configuration", "text/plain", "MesoNH workflow", yaml.dump(yaml_template), path=simulation.directory)        
        except DataManagerException as err:
            print("Error creating configuration file on machine"+err.message)
            return
        submitSimulation(sim_id)
    except SimulationManagerException as err:
        print("Error creating or submitting simulation "+err.message)
        return

def _doesSimulationDirectoryContainFile(directoryListing, filename):
    for entry in directoryListing:
        tokens=entry.split()
        if len(tokens) == 9:
            if tokens[8] == filename:
                return True, int(tokens[4])
    return False, None

#logs any new messages appropriately, then sees if the criteria are met to run a simulation. If so, it runs [not implemented] the simulation
@workflow.atomic
@workflow.handler
def wildfire_mesonh_simulation(msg):
    IncidentID = msg["IncidentID"]
    originator = msg["originator"]
    if "simulationId" in msg:
        simulationId = msg["simulationId"]
    else:
        simulationId = None    

    if originator == "Simulation Completed":        
        pgdFileCreated, pgdFileSize=_doesSimulationDirectoryContainFile(msg["directoryListing"], "CFIRE02KM.nc")
        if not pgdFileCreated:
            with pny.db_session:
                simulation=Simulation[simulationId]
                simulation.status="ERROR"
                simulation.status_message="PGD output file not generated, this indicated there was an error running the simulation code"
                simulation.status_updated=datetime.datetime.now()
                pny.commit()
            return

        workflow.Persist.Put(IncidentID,{"originator": "wildfire_mesonh_physiographic", "Physiographic": True})
        print("Physiographic data received "+ simulationId)        
        with pny.db_session:
            simulation=Simulation[simulationId]
            machine_name=simulation.machine.machine_name

        if simulation is not None:
            try:
                print("Physiographic path is "+simulation.directory)
                registerDataWithDM("CFIRE02KM.nc", machine_name, "Physiographic data", "application/octet-stream", pgdFileSize, "MesoNH PGD pre-processing", 
                    path=simulation.directory, associate_with_incident=True, incidentId=IncidentID, kind="Physiographic data", 
                    comment="Created by MesoNH PGD pre-processing which was run on "+machine_name+" with simulation ID "+simulationId)
            except DataManagerException as err:
                print("Error registering data with data manager "+err.message)
                return
        else:
            print("No such simulation with ID "+simulationId)
            return

    elif originator == "wildfire_mesonh_getdata":
        workflow.Persist.Put(IncidentID,{"originator": originator, "urls": msg["urls"]})        
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
    
    urls = None
    
    #go through logs and get the latest url
    for log in logs:
        if log["originator"] == "wildfire_mesonh_getdata":            
            urls = log["urls"]    
    
    if urls is None or physiographic == False:
        print("Nothing to be done yet. Missing dependencies")
        return
    
    try:
        callbacks = {'COMPLETED': 'wildfire_mesonh_results'}   
        sim_id=createSimulation(IncidentID, 1, "0:10:00", "MesoNH weather simulation", "mesonh_composed.sh", queuestate_callbacks=callbacks, template_dir="templates/mesonh_template")
        with pny.db_session:
            simulation=Simulation[sim_id]    
            machine_name=simulation.machine.machine_name
            machine_basedir=simulation.machine.base_work_dir
            if machine_basedir[-1] != "/": machine_basedir+="/"
        
        gfs_data_uuids=[]
        gfs_data_filenames=[]
        for url in urls:
            filename=os.path.split(url)[1]
            gfs_data_filenames.append(filename)            
            try:
                gfs_data_uuids.append(downloadDataToTargetViaDM(filename, machine_name, "GFS global weather data", "application/octet-stream", "NASA website", url, "https", 
                    path=simulation.directory, associate_with_incident=True, incidentId=IncidentID, kind="GFS global weather data", comment="Downloaded from NASA website onto "+machine_name))
            except DataManagerException as err:
                print("Error downloading GFS weather data to target machine "+err.message)
                return

        mesoNHYaml=_buildMesoNHYaml(IncidentID, machine_basedir, simulation.directory, gfs_data_filenames[0],gfs_data_filenames[1], _retrievePGDDataLocation(IncidentID))

        try:
            data_uuid=putByteDataViaDM("mesonh_composed.yml", machine_name, "MesoNH YAML configuration", "text/plain", "MesoNH workflow", mesoNHYaml, path=simulation.directory)        
        except DataManagerException as err:
            print("Error creating configuration file on machine"+err.message)
            return
        submitSimulation(sim_id)
    except SimulationManagerException as err:
        print("Error creating or submitting MesoNH simulation "+err.message)
        return

@pny.db_session
def _retrievePGDDataLocation(incidentId):
    myincident = Incident[incidentId]
    for stored_ds in myincident.associated_datasets:
        if stored_ds.type.lower() == "physiographic data":
            try:
                data_info=getInfoForDataInDM(stored_ds.uuid)                
                return data_info["absolute_path"]
            except DataManagerException as err:
                print("Can not retrieve DM information for data "+err.message)
    print("No matching physiographic data")
    return None
    
@pny.db_session
def _buildMesoNHYaml(incidentId, machine_basedir, simulation_location, gfs_file1, gfs_file2, pdg_file):
    myincident = Incident[incidentId]
    upperLeft = myincident.upper_left_latlong
    lowerRight = myincident.lower_right_latlong
            
    upperLeftLat, upperLeftLon = upperLeft.split("/")
    lowerRightLat, lowerRightLon = lowerRight.split("/")

    sample_configuration_file = open("workflows/wildfire/templates/mesonh.yml")
    yaml_template = yaml.load(sample_configuration_file, Loader=yaml.FullLoader)    
    yaml_template["upperleft"]["lat"]=float(upperLeftLat)
    yaml_template["upperleft"]["lon"]=float(upperLeftLon)
    yaml_template["lowerright"]["lat"]=float(lowerRightLat)
    yaml_template["lowerright"]["lon"]=float(lowerRightLon)

    yaml_template["gfs_gribs"][0]["path"]=machine_basedir+simulation_location+"/"+gfs_file1
    yaml_template["gfs_gribs"][1]["path"]=machine_basedir+simulation_location+"/"+gfs_file2
    yaml_template["ini_nameroots"][0]="GFS"+gfs_file1.split("_")[-3]+"."+gfs_file1.split("_")[-2][0:2]
    yaml_template["ini_nameroots"][1]="GFS"+gfs_file2.split("_")[-3]+"."+gfs_file2.split("_")[-2][0:2]
    yaml_template["pgd"]["path"]=pdg_file

    print ("Upper Left lat " + str(upperLeftLat))
    print ("Upper Left lon " + str(upperLeftLon))
    print ("Lower right lat " + str(lowerRightLat))
    print ("Lower right lon " + str(lowerRightLon))
    return yaml.dump(yaml_template)
    
#handles simulation results from a mesoNH simulation (at)
@workflow.handler
def wildfire_mesonh_results(msg):
    IncidentID = msg["IncidentID"]
    simulationId = msg["simulationId"]

    weatherFileCreated, weatherFileSize=_doesSimulationDirectoryContainFile(msg["directoryListing"], "weather_output.nc")
    if not weatherFileCreated:
        with pny.db_session:
            simulation=Simulation[simulationId]
            simulation.status="ERROR"
            simulation.status_message="MesoNH output file not generated, this indicated there was an error running the simulation code"
            simulation.status_updated=datetime.datetime.now()
            pny.commit()
        return

    with pny.db_session:
        simulation=Simulation[simulationId]
        machine_name=simulation.machine.machine_name

    if simulation is not None:
        try:                
            data_uuid=registerDataWithDM("weather_output.nc", machine_name, "MesoNH weather forecast", "application/octet-stream", weatherFileSize, 
                "MesoNH simulation", path=simulation.directory, associate_with_incident=True, incidentId=IncidentID, kind="Weather forecast", 
                comment="Created by MesoNH on "+machine_name+" with simulation ID "+simulationId)
        except DataManagerException as err:
            print("Error registering MesoNH result data with data manager "+err.message)
            return            
    else:
        print("No such simulation with ID "+simulationId)
        return    

    fwdmsg={"IncidentID" : IncidentID, "weather_data_uuid" : data_uuid}
    workflow.send(fwdmsg,"wildfire_fire_simulation")

def RegisterHandlers():
    workflow.RegisterHandler(handler = wildfire_mesonh_getdata,queue="wildfire_mesonh_getdata")
    workflow.RegisterHandler(handler = wildfire_mesonh_init,queue="wildfire_mesonh_init")
    workflow.RegisterHandler(handler = wildfire_mesonh_shutdown,queue="wildfire_mesonh_shutdown")
    workflow.RegisterHandler(handler = wildfire_mesonh_shutdown_standalone,queue="wildfire_mesonh_shutdown_standalone")
    workflow.RegisterHandler(handler = wildfire_mesonh_init_standalone,queue="wildfire_mesonh_init_standalone")
    workflow.RegisterHandler(handler = wildfire_mesonh_physiographic,queue="wildfire_mesonh_physiographic")
    workflow.RegisterHandler(handler = wildfire_mesonh_simulation,queue="wildfire_mesonh_simulation")
    workflow.RegisterHandler(handler = wildfire_mesonh_results,queue="wildfire_mesonh_results")
