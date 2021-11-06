import sys
sys.path.append("../")
sys.path.append("../MachineInterface")
import flask
import uuid
import pony.orm as pny
from pony.orm.serialization import to_dict
from Database import db, initialiseDatabase, Data, DataTransfer, Machine
import datetime
from dateutil.parser import parse
import os
import json
import subprocess
from Database import LocalDataStorage
from mproxy.client import Client
import asyncio
import aio_pika
from WorkflowManager.manager import workflow
from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor
from apscheduler.schedulers.background import BackgroundScheduler

app = flask.Flask(__name__)

OK=0
FILE_ERROR=1
NOT_IMPLEMENTED = 2

useCaching = False
fileCache=[]
maxNumCacheEntries=10
maxCacheSize=1024*1024*100
minCacheSize=1024*1024

class cachedData:
    def __init__(self, machine, full_file, size, last_changed, byte_data):
        self.machine=machine
        self.full_file=full_file
        self.size=size
        self.last_changed=last_changed
        self.byte_data=byte_data

    def update(self, size, last_changed, byte_data):
        self.size=size
        self.last_changed=last_changed
        self.byte_data=byte_data

    def match(self, machine, full_file, size, last_changed):
        return self.machine==machine and self.full_file==full_file and self.size==size and self.last_changed==last_changed

    def getData(self):
        return self.byte_data

async_scheduler=BackgroundScheduler(executors={"default": ThreadPoolExecutor(1)})

@app.route("/DM/health", methods=["GET"])
def get_health():
    return flask.jsonify({"status": 200}), 200

#searches for data object with filename, machine and directory.
# at the moment can only return 1 result (changeme?)
@app.route("/DM/search",methods=["GET"])
@pny.db_session
def search():
    filename=flask.request.args.get("filename", None)
    path=flask.request.args.get("path", None)
    machine=flask.request.args.get("machine", None)
    print(filename,machine,path)
    if filename is None or machine is None:
        return "Need filename and machine", 501
    else:        
        try:
            if path is not None:
                data_obj=Data.get(filename=filename, machine=machine, path=path)
            else:
                data_obj=Data.get(filename=filename, machine=machine)
        except pny.core.MultipleObjectsFoundError:
            return "Multiple search results found", 400
        if data_obj is None:
            return "No such data object registered", 404
        else:
            return flask.jsonify(data_obj.to_dict()), 200

#Returns the information for all data entities, or for a specified entity
@app.route("/DM/info")
@app.route("/DM/info/<id>",methods=["GET"])
def info(id=None):
    with pny.db_session:
        #get list of all entries and turn them into a list of dictionaries
        if id == None:
            records = pny.select(d for d in Data)[:]
            data=[]
            for r in records:
                data_info=r.to_dict()                
                data_info["absolute_path"]=_retrieveAbsolutePath(data_info)
                data.append(data_info)

        #get a specific data item and turn it into a dictionary
        else:
            try:
                d = Data[id]
            except pny.ObjectNotFound:
                return "%s does not exist"%id, 404
            data = d.to_dict()
            data["absolute_path"]=_retrieveAbsolutePath(data)
    #return as a json
    return flask.jsonify(data), 200

@app.route("/DM/get/<id>",methods=["GET"])
@pny.db_session
def get_data(id):
    registeredData=Data[id]
    if registeredData is not None:
        if "gather_metrics" in flask.request.form:
            gather_metrics=flask.request.form["gather_metrics"].lower() == "true"            
        else:
            gather_metrics=False        
        return _get_data_from_location(registeredData, gather_metrics)
    else:
        return "Data not found", 400

# puts a stream of data to a location, avoids having to create a temporary file first and transfer it
@app.route("/DM/put",methods=["PUT"])
def put_data():    
    registered_status=_perform_registration(flask.request.form)
    if registered_status[1] == 201:
        if "gather_metrics" in flask.request.form:
            gather_metrics=flask.request.form["gather_metrics"].lower() == "true"            
        else:
            gather_metrics=False
        put_status= _put_data_to_location(flask.request.form["payload"], registered_status[0], gather_metrics)
        if put_status[1] == 201:
            return registered_status[0], 201
        else:
            return put_status
    else:
        return registered_status

#registers a data entity with the DataManager, and returns its uuid
@app.route("/DM/register",methods=["PUT"])
def register():
    #get the info from the request
    return _perform_registration(flask.request.form)

def _perform_registration(form_data):
    fname = form_data["filename"]
    if "path" in form_data:
        path = form_data["path"]
    else:
        path = ""
    machine = form_data["machine"]
    description = form_data["description"]
    type = form_data["type"]
    if "size" in form_data:
        size = form_data["size"]
    elif "payload" in form_data:
        size=len(form_data["payload"])
    else:
        return "No size provided", 400
    originator = form_data["originator"]
    group = form_data["group"]
    if "storage_technology" in form_data:
        storage_technology = form_data["storage_technology"]
    else:
        storage_technology = "FILESYSTEM"
    
    if _checkExists(machine,fname,path):
        return "File already exists", 406

    #register this with the database and return its UUID
    id=_register(fname,path,machine,description,type,size,originator,group,storage_technology)
    return id, 201      

#instructs the data manager to download data from the internet onto a specified machine. Returns a uuid for that data entity
@app.route("/DM/getexternal",methods=["PUT"])
def GetExternal():
    #get required fields from the header    
    fname = flask.request.form["filename"]    
    if "path" in flask.request.form:
        path = flask.request.form["path"]
    else:
        path = ""
    machine = flask.request.form["machine"]
    description = flask.request.form["description"]
    type = flask.request.form["type"]
    originator = flask.request.form["originator"]
    group = flask.request.form["group"]
    if "storage_technology" in flask.request.form:
        storage_technology = flask.request.form["storage_technology"]
    else:
        storage_technology = "FILESYSTEM"
    url = flask.request.form["url"]
    protocol = flask.request.form["protocol"]
    if "options" in flask.request.form:
        options = json.loads(flask.request.form["options"])
    else:
        options = None    

    if "callback" in flask.request.form and "incidentId" in flask.request.form:
        callback = flask.request.form["callback"]
        incidentId = flask.request.form["incidentId"]
    else:
        callback = None
        incidentId = None

    if _checkExists(machine,fname,path):
        return "File already exists", 406

    if callback is None or incidentId is None:
        #instruct the machine to download the file (passes the size of the file back in the "options" dict)
        try:
            status, message, date_started, date_completed = _download(fname, path, storage_technology, machine, url, protocol, options)
        except ConnectionManager.ConnectionError as e:
            return str(e), 500
            
        if status == OK:
            size=message
            #register this new file with the data manager
            id=_register(fname,path, machine, description, type, size, originator, group, storage_technology)
            with pny.db_session:
                transfer_id = str(uuid.uuid4())
                data_transfer = DataTransfer(id=transfer_id,
                                        src=Data[id],
                                        src_machine=protocol,
                                        dst_machine=machine,
                                        date_started=date_started,
                                        status = "COMPLETED",
                                        date_completed = date_completed,
                                        completion_time = (date_completed - date_started))
            return id, 201
        elif status == NOT_IMPLEMENTED:
            return message, 501
        elif status==FILE_ERROR:
            return message, 500
    else:
        async_scheduler.add_job(downloadDataAsync, 'interval', weeks=1000, next_run_time=datetime.datetime.now()+ datetime.timedelta(seconds=1), 
            end_date=datetime.datetime.now()+ datetime.timedelta(seconds=10),
            args=[fname, path, storage_technology, machine, url, protocol, description, type, originator, group, options, callback, incidentId])
        return "Scheduled", 201

#Moves a data entity from one location to another
@app.route("/DM/move/<id>",methods=["POST"])
def move(id):
    return _handle_copy_or_move(id, True)

#copies a data entity to a new location, returning the uuid of the copy
@app.route("/DM/copy/<id>",methods=["POST"])
def copy(id):    
    return _handle_copy_or_move(id, False)

#deletes a data entity. This marks the entity as "DELETED" in the database and deletes the file
@app.route("/DM/remove/<id>",methods=["DELETE"])
def remove(id):
    #get info about the file, namely what machine it is on and its path
    with pny.db_session:
        try:
            d=Data[id]
        except pny.ObjectNotFound:
            return "Data object not found", 404
        machine=d.machine
        file = os.path.join(d.path,d.filename)

    #delete this file
    status, message =_delete(file, machine, d.storage_technology)    

    if status == FILE_ERROR:
        with pny.db_session:
            Data[id].status = "UNKNOWN"
        return message, 500
    elif status == NOT_IMPLEMENTED:
        return message, 501
    else:
        #set the status of this file to "DELETED" in the database
        with pny.db_session:
            Data[id].status="DELETED"
            Data[id].date_modified=datetime.datetime.now()
            return "%s deleted"%Data[id].filename, 200

@app.route("/DM/predict",methods=["POST"])
@pny.db_session
def predict():    
    if "uuid" in flask.request.form:
        uuid=flask.request.form["uuid"]
        try:
            d=Data[uuid]
        except pny.ObjectNotFound:            
            return "Data with uuid '"+uuid+"' not found", 404
        src_machine=d.machine
        data_size=d.size
    else:
        src_machine=flask.request.form["src_machine"]    
        data_size=float(flask.request.form["data_size"])    

    dest_machine=flask.request.form["dest_machine"]
    print("From to "+src_machine+" "+str(data_size) +" to " +dest_machine)
    matching_transfers=pny.select(dt for dt in DataTransfer if dt.src_machine == src_machine and dt.dst_machine == dest_machine)[:]
    if len(matching_transfers) == 0:
        return "No matching data transfers between machines", 400
    else:
        avg_speed_per_sec=0.0
        for transfer in matching_transfers:
            avg_speed_per_sec += (float(transfer.src.size)/transfer.completion_time.total_seconds())
        avg_speed_per_sec /= len(matching_transfers)
        return flask.jsonify({"prediction_time": data_size / avg_speed_per_sec}), 201

#moves the data entity to a long term file storage location and marks it as archived
@app.route("/DM/archive/<id>",methods=["PUT"])
def archive(id):
    return "Not Implemented", 501

#moves the data entity from long term storage onto a machine and marks it as active
@app.route("/DM/activate/<id>",methods=["PUT"])
def activate(id):
    return "Not Implemented", 501


#--------------------- helper functions --------------------------

def _issueWorkflowCallback(callback, incidentId, response, success):      
    workflow.OpenConnection()    
    msg={"IncidentID": incidentId, "response": response, "success": success}            
    workflow.send(message=msg, queue=callback, providedCaller="Data manager callback from non-blocking operation")
    workflow.FlushMessages()
    workflow.CloseConnection()

def _downloadDataAsync(fname, path, storage_technology, machine, url, protocol, description, type, originator, group, options, callback, incidentId):        
    try:
        status, message, date_started, date_completed = _download(fname, path, storage_technology, machine, url, protocol, options)
    except ConnectionManager.ConnectionError as e:
        issueWorkflowCallback(callback, incidentId, "Connection error", False)    
            
    if status == OK:
        size=message
        #register this new file with the data manager
        id=_register(fname,path, machine, description, type, size, originator, group, storage_technology)
        with pny.db_session:
            transfer_id = str(uuid.uuid4())
            data_transfer = DataTransfer(id=transfer_id, src=Data[id], src_machine=protocol, dst_machine=machine,
                                        date_started=date_started, status = "COMPLETED", date_completed = date_completed,
                                        completion_time = (date_completed - date_started))
            issueWorkflowCallback(callback, incidentId, id, True)            
    elif status == NOT_IMPLEMENTED:
        issueWorkflowCallback(callback, incidentId, message, False)            
    elif status==FILE_ERROR:
        issueWorkflowCallback(callback, incidentId, message, False) 

@pny.db_session
def _retrieveAbsolutePath(data_info):
    if data_info["machine"] == "localhost":
        if len(data_info["path"]) > 0: 
            absolute_path=data_info["path"]+"/"+data_info["filename"]
        else:
            absolute_path=data_info["filename"]
    else:
        machine=Machine.get(machine_name=data_info["machine"])
        absolute_path=machine.base_work_dir.strip()
        if absolute_path[-1] != "/": absolute_path+="/"
        if len(data_info["path"]) > 0: 
            absolute_path+=data_info["path"]+"/"                    
        absolute_path+=data_info["filename"]
    return absolute_path

def _handle_copy_or_move(id, move):
    #get details of the data object
    with pny.db_session:
        try:
            data=Data[id]
        except pny.ObjectNotFound:            
            return "Object %s does not exist"%id, 404
        src = os.path.join(data.path,data.filename)
        src_machine = data.machine
        description = data.description
        type=data.type
        size = data.size
        originator = data.originator
        group = data.group    

    #get the options from the header
    dest_machine = flask.request.form["machine"]
    dest = flask.request.form["dest"]

    if "gather_metrics" in flask.request.form:
        gather_metrics=flask.request.form["gather_metrics"].lower() == "true"
    else:
        gather_metrics=True

    if "storage_technology" in flask.request.form:
        dest_storage_technology = flask.request.form["storage_technology"]
    else:
        dest_storage_technology = "FILESYSTEM"

    if gather_metrics:
        with pny.db_session:
            transfer_id = str(uuid.uuid4())
            data_transfer = DataTransfer(id=transfer_id,
                                        src=Data[id],
                                        src_machine=src_machine,
                                        dst_machine=dest_machine,
                                        date_started=datetime.datetime.now(),
                                        status="STARTED")

    path,fname = os.path.split(dest)
    if _checkExists(dest_machine,fname,path):
        if gather_metrics:
            with pny.db_session:
                DataTransfer[transfer_id].status = "FAILED"
        return "File already exists", 406    

    # perform move or copy on the file
    status, message =_copy(src, src_machine, data.storage_technology, dest, dest_machine, dest_storage_technology, move=move)
    date_completed = datetime.datetime.now()

    if status == FILE_ERROR:
        if gather_metrics:
            with pny.db_session:
                DataTransfer[transfer_id].status = "FAILED"
        return message, 500
    if status == NOT_IMPLEMENTED:
        if gather_metrics:
            with pny.db_session:
                DataTransfer[transfer_id].status = "FAILED"
        return message, 501
    elif status == OK:
        with pny.db_session:
            if move:
                data=Data[id]
                data.machine = dest_machine
                data.path, data.filename = os.path.split(dest)
                data.date_modified=datetime.datetime.now()
                new_id=id
            else:
                path,fname = os.path.split(dest)
                new_id =_register(fname,path,dest_machine,description,type,size,originator,group,dest_storage_technology)
            if gather_metrics:
                data_transfer = DataTransfer[transfer_id]
                data_transfer.status = "COMPLETED"
                data_transfer.dst = Data[new_id]
                data_transfer.date_completed = date_completed
                data_transfer.completion_time = (data_transfer.date_completed -
                                                data_transfer.date_started)
        return new_id, 201

#Creates a new entry in the database
@pny.db_session
def _register(fname,path,machine,description,type,size,originator,group,storage_technology="FILESYSTEM"):
    id = str(uuid.uuid4())
    try:
        size = int(size)
    except ValueError:    
        size=0 
    d=Data(id=id,machine=machine,filename=fname,path=path,description=description,type=type,size=size,date_registered=datetime.datetime.now(),
        originator=originator,group=group,storage_technology=storage_technology)
    return id

#deletes a file, and marks its entry in the database as deleted
@pny.db_session
def _delete(file, machine, storage_technology):
    if machine == "localhost":  
        if storage_technology == "FILESYSTEM":
            try:
                os.remove(_getLocalPathPrepend()+file)
            except OSError as e:
                return FILE_ERROR, str(e)            
        elif storage_technology == "VESTECDB":            
            data_item=LocalDataStorage.get(filename=file)
            data_item.delete()
    else:
        asyncio.run(submit_remove_file_on_machine(machine, file))
    return OK, "Deleted"    

async def submit_remove_file_on_machine(machine_name, file):
    client = await Client.create(machine_name)    
    await client.rm(file)

#copies a file between two (possibly remote) locations. If move=true this acts like a move (deletes the source file)
@pny.db_session
def _copy(src, src_machine, src_storage_technology, dest, dest_machine, dest_storage_technology, move=False):    
    #copy within a machine
    if src_machine == dest_machine:        
        #local copy on the VESTEC server
        if src_machine == "localhost":   
            if src_storage_technology == "FILESYSTEM":
                if move:
                    command = "mv %s %s"%(_getLocalPathPrepend()+src, _getLocalPathPrepend()+dest)
                else:
                    command = "cp %s %s"%(_getLocalPathPrepend()+src, _getLocalPathPrepend()+dest)
                result = subprocess.run(command.split(" "),stdout=subprocess.PIPE, stderr=subprocess.PIPE,text=True)
                if result.returncode == 0:
                    return OK, "copied"
                else:
                    return FILE_ERROR, result.stderr
            elif src_storage_technology == "VESTECDB":
                data_item=LocalDataStorage.get(filename=src)
                if data_item is not None:
                    if move:
                        data_item.filename=dest
                    else:
                        new_data_item=LocalDataStorage(contents=data_item.contents, filename=dest, filetype=data_item.filetype)
                    return OK, "copied"
                else:
                    return FILE_ERROR, "No such source file"

        #local copy on a remote machine
        else:
            asyncio.run(submit_move_or_copy_file_on_machine(dest_machine, src, dest, move))            
            return OK, "copied"

    else:
        #copy from VESTEC server to remote machine
        if src_machine == "localhost":
            if src_storage_technology == "FILESYSTEM":
                asyncio.run(transfer_file_to_or_from_machine(dest_machine, _getLocalPathPrepend()+src, dest, download=False))
            elif src_storage_technology == "VESTECDB":
                data_item=LocalDataStorage.get(filename=src)
                asyncio.run(submit_copy_bytes_to_machine(dest_machine, data_item.contents, dest))
                if move:
                    data_item.delete()
                return OK, "copied"

        #copy from remote machine to VESTEC server
        elif dest_machine == "localhost":
            if dest_storage_technology == "FILESYSTEM":
                asyncio.run(transfer_file_to_or_from_machine(src_machine, src, _getLocalPathPrepend()+dest, download=True))
            elif dest_storage_technology == "VESTECDB":
                byte_contents=asyncio.run(submit_copy_bytes_from_machine(src_machine, src, move))
                new_file = LocalDataStorage(contents=byte_contents, filename=dest, filetype="")
                return OK, "copied"

        #copy between two remote machines
        else:
            dest_user = ConnectionManager.machines[dest_machine]["username"]
            machine = ConnectionManager.machines[dest_machine]["host"]
            asyncio.run(submit_remote_copy_betwee_machines(src_machine, src, dest_machine, dest_file, move))          
            return OK, "copied"

async def submit_remote_copy_betwee_machines(src_machine_name, src_file, dest_machine, dest_file, move):
    client = await Client.create(machine_name)              
    await client.remote_copy(src_file, dest_machine, dest_username, dest_file)
    if move:
        await client.rm(src_file)

async def transfer_file_to_or_from_machine(machine_name, src, dest, download):    
    client = await Client.create(machine_name)
    if download:          
        await client.download(src, dest)
    else:
        await client.upload(src, dest)

async def submit_move_or_copy_file_on_machine(machine_name, src, dest, move):    
    client = await Client.create(machine_name)
    if move:          
        await client.mv(src, dest)
    else:
        await client.cp(src, dest)

async def submit_copy_bytes_from_machine(machine_name, src_file, move=False):        
    client = await Client.create(machine_name)    
    byte_contents= await client.get(src_filest)                
    if move:
        await client.rm(src_file)
    return byte_contents

async def submit_copy_bytes_to_machine(machine_name, src_bytes, dest):        
    client = await Client.create(machine_name)
    await client.put(src_bytes, dest)

def _get_data_from_location(registered_data, gather_metrics):
    if gather_metrics:        
            transfer_id = str(uuid.uuid4())
            data_transfer = DataTransfer(id=transfer_id,
                                        src=registered_data,
                                        src_machine=registered_data.machine,
                                        dst_machine="external",
                                        date_started=datetime.datetime.now(),
                                        status="STARTED")
    if len(registered_data.path) > 0:
        target_src=registered_data.path+"/"+registered_data.filename
    else:
        target_src=registered_data.filename
    if registered_data.machine == "localhost":   
        if registered_data.storage_technology == "FILESYSTEM":
            readFile = open(_getLocalPathPrepend()+target_src, "rb")
            contents=readFile.read()
            readFile.close()            
        elif registered_data.storage_technology == "VESTECDB":
            localData=LocalDataStorage.get(filename=target_src)
            contents=localData.contents            
    else:
        if useCaching:
            details=asyncio.run(get_ls_on_data(registered_data.machine, target_src))
            tokens=details[0].split()
            file_size = tokens[4]
            filefound=False
            timestamp=parse(tokens[5]+" "+tokens[6]+" "+tokens[7]).timestamp()
            for entry in fileCache:
                if entry.match(registered_data.machine, target_src, file_size, timestamp):
                    contents=entry.getData()                    
                    filefound=True
                    break
            if not filefound:
                contents=asyncio.run(submit_remote_get_data(registered_data.machine, target_src))            
                if int(file_size) < maxCacheSize: #and int(file_size) > minCacheSize:                    
                    if len(fileCache) == maxNumCacheEntries: del fileCache[0]
                    fileCache.append(cachedData(registered_data.machine, target_src, file_size, timestamp, contents))
        else:
            contents=asyncio.run(submit_remote_get_data(registered_data.machine, target_src))

    if gather_metrics:
        data_transfer = DataTransfer[transfer_id]
        data_transfer.status = "COMPLETED"
        data_transfer.dst = registered_data
        data_transfer.date_completed = datetime.datetime.now()
        data_transfer.completion_time = (data_transfer.date_completed - data_transfer.date_started)
    return contents, 200

async def submit_remote_get_data(target_machine_name, src_file):
    client = await Client.create(target_machine_name)              
    return await client.get(src_file)

async def get_ls_on_data(target_machine_name, src_file):
    client = await Client.create(target_machine_name)
    return await client.ls(src_file)

@pny.db_session
def _put_data_to_location(data_payload, data_uuid, gather_metrics):
    registered_data=Data[data_uuid]    
    if registered_data is not None:
        if gather_metrics:        
            transfer_id = str(uuid.uuid4())
            data_transfer = DataTransfer(id=transfer_id,
                                        src=registered_data,
                                        src_machine="external",
                                        dst_machine=registered_data.machine,
                                        date_started=datetime.datetime.now(),
                                        status="STARTED")

        # If we are provided with a string then perform an implicit conversion to bytes
        if isinstance(data_payload, str): data_payload=bytes(data_payload, encoding='utf8')
        if len(registered_data.path) > 0:
            target_dest=registered_data.path+"/"+registered_data.filename
        else:
            target_dest=registered_data.filename
        if registered_data.machine == "localhost":   
            if registered_data.storage_technology == "FILESYSTEM":
                newFile = open(_getLocalPathPrepend()+target_dest, "wb")
                newFile.write(data_payload)
                newFile.close()
            elif registered_data.storage_technology == "VESTECDB":                
                new_data_item=LocalDataStorage(contents=data_payload, filename=target_dest, filetype=registered_data.type)            
        else:
            asyncio.run(submit_remote_put_data(registered_data.machine, data_payload, target_dest))
        if gather_metrics:
                data_transfer = DataTransfer[transfer_id]
                data_transfer.status = "COMPLETED"
                data_transfer.dst = registered_data
                data_transfer.date_completed = datetime.datetime.now()
                data_transfer.completion_time = (data_transfer.date_completed - data_transfer.date_started)
        return "Data put completed", 201
    else:
        if gather_metrics:            
            DataTransfer[transfer_id].status = "FAILED"
        return "Registration error", 500    

async def submit_remote_put_data(target_machine_name, data, dest_file):
    client = await Client.create(target_machine_name)              
    await client.put(data, dest_file)     

#downloads a file to a (possibly remote) location
def _download(filename,  path, storage_technology, machine, url, protocol, options):
    #get the filename (with path ) of the file we want created
    dest = os.path.join(path,filename)

    #deterine the command we wish to run to download the file
    if protocol == "http" or protocol == "https":
        if options:
            print("Do not know how to deal with non-empty options")
            print(options)
            return NOT_IMPLEMENTED, "", 0, 0
        if machine == "localhost" and storage_technology == "VESTECDB":
            # If its localhost and VESTECDB then use a temporary file
            temp = tempfile.NamedTemporaryFile()
            cmd = "curl --insecure -f -sS -o %s %s"%(temp.name, url)
        elif machine == "localhost":
            cmd = "curl --insecure -f -sS -o %s %s"%(_getLocalPathPrepend()+dest, url)
        else:
            cmd = "curl -f -sS -o %s %s"%(dest, url)
    else:
        print("Do not know how to handle protocols that are not http")
        return NOT_IMPLEMENTED, "'%s' protocol not supported (yet?)"%protocol, 0, 0

    if machine == "localhost":
        #run the command locally
        date_started=datetime.datetime.now()
        r=subprocess.run(cmd.split(" "),stdout=subprocess.PIPE,stderr = subprocess.PIPE,text=True)
        date_completed=datetime.datetime.now()
        if r.returncode != 0:
            print("An error occurred in the local download")
            print(r.stderr)
            print(r.stdout)
            return FILE_ERROR, r.stderr, 0, 0
        else:
            #get size of the new file and put this in the options dict
            size=os.path.getsize(_getLocalPathPrepend()+dest)            
            if storage_technology == "VESTECDB":
                # Transfer temporary file into the VESTECDB
                byte_contents=temp.read()
                temp.close()
                new_file = LocalDataStorage(contents=byte_contents, filename=dest, filetype="")
            return OK, size, date_started, date_completed

    else:        
        #run the command remotely
        date_started=datetime.datetime.now()
        success, size_or_error=asyncio.run(submit_run_command_on_machine(machine, cmd, dest))        
        date_completed=datetime.datetime.now()
        if not success:
            print("Remote download encountered an error:")              
            return FILE_ERROR, size_or_error, 0, 0
        else:
            print("Remote download completed successfully")                                           
            return OK, size_or_error, date_started, date_completed

async def submit_run_command_on_machine(machine_name, command, listfile):
    client = await Client.create(machine_name)
    run_info= await client.run(command)
    if not run_info.error:
        list_info=await client.ls(listfile)
        if len(list_info) == 1:
            tokens=list_info[0].split()
            if len(tokens) >= 4:
                size=tokens[4]                
            else:
                print("Downloaded file OK, but can not retrieve size as file listing is malformed")
                size=0
            return True, size
        else:
            print("Downloaded file OK, but can not retrieve size as list command on '"+dest+"' resulted in "+str(len(list_info))+" entries")
            return True, 0
    else:
        return False, run_info.stderr

@pny.db_session
def _checkExists(machine,filename,path):    
    entries = pny.select(d for d in Data if (d.status!="DELETED" and d.status!="UNKNOWN") and d.machine == machine and d.path==path and d.filename == filename)

    if len(entries)>0:
        return True
    else:
        return False

def _getLocalPathPrepend():
    if "VESTEC_SHARED_FILE_LOCATION" in os.environ:
        shared_location= os.environ["VESTEC_SHARED_FILE_LOCATION"]
        if shared_location[-1] != "/": shared_location+="/"
        return shared_location
    else:
        return ""

if __name__ == "__main__":
    initialiseDatabase() 
    async_scheduler.start()   
    app.run(host='0.0.0.0', port=5503)
