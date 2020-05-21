import workflow
import requests
import os
os.path.join("../")
import hashlib
import uuid
import datetime
import zipfile
import json
import pony.orm as pny

from Database import Incident

from christian import Get_Fire_Hotspots


######### ATTENTION #################
#For this to work, you need to have a subdirectory inside WorkflwoManager called `hotspots`
#This directory must contain a directory called `static` which contains the unsipped admin files from Christian
#For now, it must also contain the zipped "northern_italy.zip" area of interest file (Also from Christian)
#So the directory structure is...
#   hotspots
# ├──  northern_italy.zip
# └──  static
#    ├──   ne_10m_admin_1_states_provinces.cpg
#    ├──   ne_10m_admin_1_states_provinces.dbf
#    ├──   ne_10m_admin_1_states_provinces.prj
#    ├──   ne_10m_admin_1_states_provinces.README.html
#    ├──   ne_10m_admin_1_states_provinces.shp
#    ├──   ne_10m_admin_1_states_provinces.shx
#    └──   ne_10m_admin_1_states_provinces.VERSION.txt
#
# For each incident, we create a directory in hotspots. This directory will contain
# - a 'region' directory where the region zipfile will be placed and extracted
# - a MODIS directory for MODIS data
# - a VIIRS directory for VIIRS data
# Each sensor's directory will then contain subdirectories for each input data timestamp
# These subdirectories will contain an input and output directory with the shape files
# The directory structure for an incident is therefore:
#   .
# ├──   region
# │  ├──   northern_italy.cpg
# │  ├──   northern_italy.dbf
# │  ├──   northern_italy.prj
# │  ├──   northern_italy.shp
# │  ├──   northern_italy.shx
# │  └──   northern_italy.zip
# ├──   MODIS
# │  └──   2020-05-21_144339
# │     ├──   input
# │     │  ├──   MODIS_C6_Europe_48h.cpg
# │     │  ├──   MODIS_C6_Europe_48h.dbf
# │     │  ├──   MODIS_C6_Europe_48h.prj
# │     │  ├──   MODIS_C6_Europe_48h.shp
# │     │  ├──   MODIS_C6_Europe_48h.shx
# │     │  └──   MODIS_C6_Europe_48h.zip
# │     └──   output
# │        ├──   MODIS-FIRE.cpg
# │        ├──   MODIS-FIRE.dbf
# │        ├──   MODIS-FIRE.prj
# │        ├──   MODIS-FIRE.shp
# │        ├──   MODIS-FIRE.shx
# │        └──   MODIS-FIRE.zip
# └──   VIIRS
#    └──   2020-05-21_144900
#       ├──   input
#       │  ├──   VNP14IMGTDL_NRT_Europe_48h.cpg
#       │  ├──   VNP14IMGTDL_NRT_Europe_48h.dbf
#       │  ├──   VNP14IMGTDL_NRT_Europe_48h.prj
#       │  ├──   VNP14IMGTDL_NRT_Europe_48h.shp
#       │  ├──   VNP14IMGTDL_NRT_Europe_48h.shx
#       │  └──   VNP14IMGTDL_NRT_Europe_48h.zip
#       └──   output
#          ├──   VIIRS-FIRE.cpg
#          ├──   VIIRS-FIRE.dbf
#          ├──   VIIRS-FIRE.prj
#          ├──   VIIRS-FIRE.shp
#          ├──   VIIRS-FIRE.shx
#          └──   VIIRS-FIRE.zip
#
# Presently you run a workflow by executing this file. It will create a new incident, register pull handlers on the EDI and will generate hotspots for the region described in  "northern_italy.shp" for each new MODIS/VIIRs observation


if "VESTEC_EDI_URI" in os.environ:    
    EDI_URL= os.environ["VESTEC_EDI_URI"]
    DATA_MANAGER_URI = os.environ["VESTEC_DM_URI"]
else:    
    EDI_URL= 'http://localhost:5501/EDImanager'
    DATA_MANAGER_URI = 'http://localhost:5000/DM'

#URLS to download the data from
MODISurl = "https://firms.modaps.eosdis.nasa.gov/data/active_fire/c6/shapes/zips/MODIS_C6_Europe_48h.zip"

VIIRSurl = "https://firms.modaps.eosdis.nasa.gov/data/active_fire/viirs/shapes/zips/VNP14IMGTDL_NRT_Europe_48h.zip"


#set up the hotspots workdir
wkdir = os.path.abspath("hotspots")

#
admin_filepath = os.path.join(wkdir,"static","ne_10m_admin_1_states_provinces.shp")

#initialise the workflow
@workflow.handler
def init(msg):
    incident = msg["IncidentID"]
    
    #make the working directory for this incident
    os.mkdir(os.path.join(wkdir,incident))
    
    #get the region zip and move into its correct directory, register it with the DM, and unzip it
    #in reality this would be provided at startup of the incident, but for now we're just copying an existing one into place
    os.mkdir(os.path.join(wkdir,incident,"region"))
    os.system("cp %s %s"%(os.path.join(wkdir,"northern_italy.zip"),os.path.join(wkdir,incident,"region")))
    regionfile = os.path.join(wkdir,incident,"region","northern_italy.zip")
    dm_register(file=regionfile,
                machine="localhost",
                description = "Region",
                originator = "hotspot init",
                group = "hotspot",
                incident = incident)

    unzip(regionfile,os.path.join(wkdir,incident,"region"))


    workflow.setIncidentActive(incident)
    
    #register EDI to poll for MODIS data
    myobj = {
        'queuename': 'modis_newdata',
        'incidentid': incident, 
        'endpoint': MODISurl,
        "pollperiod": 300
            }
    x = requests.post(EDI_URL+"/register", json = myobj)
    print("EDI response for MODIS data arrival" + x.text)

    if x.status_code != 200:
        raise Exception("Failed to register for modis download")
    
    #register EDI to poll for VIIRS data
    myobj = {
        'queuename': 'viirs_newdata',
        'incidentid': incident, 
        'endpoint': VIIRSurl,
        "pollperiod": 300
            }
    x = requests.post(EDI_URL+"/register", json = myobj)
    print("EDI response for VIIRS data arrival" + x.text)

    if x.status_code != 200:
        raise Exception("Failed to register for modis download")
    
    print("Ready to go :)\n")



#called when there is new MODIS data
@workflow.handler
def newMODISdata(msg):

    incident = msg["IncidentID"]
    header = msg["data"]["headers"]
    modified = header["Last-Modified"]

    #get the things this handler has persisted (list of existing timestamps)  
    persisted = workflow.Persist.Get(incident)
    
    #if the timestamp of this incoming data is not in the persisted data, we download it
    if not check_exists(persisted,modified,type="MODIS"):
        print("\nnew data for MODIS! - %s"%modified)
        
        #create the needed directories
        datestr = parse_timestamp(modified)
        
        basedir = os.path.join(wkdir,incident,"MODIS",datestr)
        filedir = os.path.join(basedir,"input")

        os.makedirs(filedir,exist_ok=True)
        
        #select the filename (with full path) for the file to be downloaded
        filename = os.path.join(filedir,os.path.basename(MODISurl))
        
        #instruct its download
        dm_download(file = filename,
                    machine = "localhost",
                    description = "MODIS input datafile for %s"%modified,
                    originator = "hotspot MODIS hadler",
                    group = "hotspot",
                    url = MODISurl,
                    incident = incident)
        
        #unzip it
        unzip(filename,filedir)
                     
        
        #persist this new timestamp (and the file)
        d = {
            "modified": modified,
            "filename": filename,
            "type": "MODIS"
        }
        workflow.Persist.Put(incident,d)
        
        #send a message to "process_hotspots" to extract hotspots for the data
        msg = {
            "IncidentID": incident,
            "baseDir": basedir,
            "inputFile": filename,
            "sensor": "MODIS",
            "regionFile": os.path.join(wkdir,incident,"region","northern_italy.shp"),
            "date": modified
        }
        workflow.send(msg,"process_hotspots")
    
   

#called when there is new MODIS data
@workflow.handler
def newVIIRSdata(msg):

    incident = msg["IncidentID"]
    header = msg["data"]["headers"]
    modified = header["Last-Modified"]

    #get the things this handler has persisted (list of existing timestamps)  
    persisted = workflow.Persist.Get(incident)
    
    #if the timestamp of this incoming data is not in the persisted data, we download it
    if not check_exists(persisted,modified,type="VIIRS"):
        print("\nnew data for VIIRS! - %s"%modified)
        
        #create the needed directories
        datestr = parse_timestamp(modified)
        
        basedir = os.path.join(wkdir,incident,"VIIRS",datestr)
        filedir = os.path.join(basedir,"input")

        os.makedirs(filedir,exist_ok=True)
        
        #select the filename (with full path) for the file to be downloaded
        filename = os.path.join(filedir,os.path.basename(VIIRSurl))
        
        #instruct its download
        dm_download(file = filename,
                    machine = "localhost",
                    description = "VIIRS input datafile for %s"%modified,
                    originator = "hotspot VIIRS hadler",
                    group = "hotspot",
                    url = VIIRSurl,
                    incident = incident)
        
        #unzip it
        unzip(filename,filedir)
                     
        
        #persist this new timestamp (and the file)
        d = {
            "modified": modified,
            "filename": filename,
            "type": "VIIRS"
        }
        workflow.Persist.Put(incident,d)
        
        #send a message to "process_hotspots" to extract hotspots for the data
        msg = {
            "IncidentID": incident,
            "baseDir": basedir,
            "inputFile": filename,
            "sensor": "VIIRS",
            "regionFile": os.path.join(wkdir,incident,"region","northern_italy.shp"),
            "date": modified
        }
        workflow.send(msg,"process_hotspots")


#Extracts hotspots from the MODIS/VIIRS data
@workflow.handler
def process_hotspots(msg):
    incident = msg["IncidentID"]
    inputfile = os.path.splitext(msg["inputFile"])[0]+".shp"
    sensor = msg["sensor"]
    regionfile = msg["regionFile"]
    outputdir = os.path.join(msg["baseDir"],"output")
    date = msg["date"]
    
    #make the directry to place the hotspots files
    os.mkdir(outputdir)

    print("\n")
    outfile = Get_Fire_Hotspots(inputfile = inputfile, sensor = sensor, regionfile = regionfile, adminfile = admin_filepath, outputdir=outputdir)
    
    #This returns files without prepending path...
    files = os.listdir(outputdir)
    #create a new list with the apsolute filepaths
    absfiles = []
    for file in files:
        absfiles.append(os.path.join(outputdir,file))
    
    #zip the hotspot files
    zipped = os.path.splitext(outfile)[0]+".zip"

    zip(absfiles,zipped)

    dm_register(file=zipped,
                machine="localhost",
                description = "%s hotspots for region on %s"%(sensor,date),
                originator = "process hotspots handler",
                group = "hotspot",
                incident = incident)



def check_exists(persisted,modified,type):
    for p in persisted:
        if p["modified"] == modified and p["type"]==type:
            return True
    return False

def unzip(target,dir):
    print("Unzipping %s"%target)
    file = zipfile.ZipFile(target, 'r')
    file.extractall(dir)
    file.close()

def zip(files,target):
    print("Zipping %s"%target)
    file = zipfile.ZipFile(target, "w")
    for f in files:
        file.write(f)
    file.close()

#register a file with the DM
def dm_register(file,machine,description,originator,group, incident):
    print("Registering %s with DataManager"%file)
    path, filename = os.path.split(file)
    size = os.path.getsize(file)

    data = {
        "filename": filename,
        "path": path,
        "machine": machine,
        "size": size,
        "description": description,
        "originator": originator,
        "group": group
    }
    r = requests.put(os.path.join(DATA_MANAGER_URI,"register"),data=data)
    if r.status_code != 201:
        print("ERROR! %s"%r.text)
        raise Exception("DM could not register file")

    with pny.db_session:
        I = Incident[incident]
        I.associated_datasets.create(
            uuid=r.text,
            name=file, 
            type=group, 
            comment=description,         
            date_created=datetime.datetime.now()
        )
    return    

#download a file with the DM
def dm_download(file,machine,description,originator,group,url,incident):
    print("Asking dm to download %s"%url)
    path, filename = os.path.split(file)


    data ={
        "filename": filename,
        "path": path,
        "machine": machine,
        "description": description,
        "originator": originator,
        "group": group,
        "url": url,
        "protocol": "http",
        "options": json.dumps({})
    }

    r = requests.put(os.path.join(DATA_MANAGER_URI,"getexternal"),data=data)

    if r.status_code != 201:
        print("ERROR! %s"%r.text)
        raise Exception("DM could not download file")

    with pny.db_session:
        I = Incident[incident]
        I.associated_datasets.create(
            uuid=r.text,
            name=file, 
            type=group, 
            comment=description,         
            date_created=datetime.datetime.now()
        )
    return    

#from a MODIS/VIIRS "modified" timestamp, produce a more 'friendly' datestring
def parse_timestamp(datestr):
    date=datetime.datetime.strptime(datestr,"%a, %d %b %Y %H:%M:%S %Z")
    newstring = date.strftime("%Y-%m-%d_%H%M%S")
    return newstring


#register the handlers with the workflow system
def RegisterHandlers():
    workflow.RegisterHandler(init, "hotspot_init")
    workflow.RegisterHandler(newMODISdata, "modis_newdata")
    workflow.RegisterHandler(newVIIRSdata, "viirs_newdata")
    workflow.RegisterHandler(process_hotspots, "process_hotspots")



#kick off an incident for the hotspot workflow
if __name__ == "__main__":
    incident = workflow.CreateIncident("hotspot", "test_hotspot")

    workflow.OpenConnection()
    workflow.send({"IncidentID": incident},"hotspot_init")
    workflow.FlushMessages()
    workflow.CloseConnection()



    



