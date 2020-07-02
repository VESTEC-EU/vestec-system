import sys
sys.path.append("../")
sys.path.append("../MachineInterface")
import flask
import uuid
import pony.orm as pny
from pony.orm.serialization import to_dict
from Database import db, initialiseDatabase, Data, DataTransfer
import datetime
import os
import ConnectionManager
import json
import subprocess
from Database import LocalDataStorage
from mproxy.client import Client
import asyncio
import aio_pika

app = flask.Flask(__name__)

OK=0
FILE_ERROR=1
NOT_IMPLEMENTED = 2

@app.route("/DM/health", methods=["GET"])
def get_health():
    return flask.jsonify({"status": 200})

@app.route("/DM/search",methods=["GET"])
@pny.db_session
def search():
    filename=flask.request.args.get("filename", None)
    path=flask.request.args.get("path", None)
    machine=flask.request.args.get("machine", None)
    if filename is None or machine is None:
        return "Need filename and machine", 501
    else:        
        if path is not None:
            data_obj=Data.get(filename=filename, machine=machine, path=path)
        else:
            data_obj=Data.get(filename=filename, machine=machine)
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
                print(r.to_dict())
                data.append(r.to_dict())
        #get a specific data item and turn it into a dictionary
        else:
            try:
                d = Data[id]
            except pny.ObjectNotFound:
                return "%s does not exist"%id, 404
            data = d.to_dict()
    #return as a json
    return flask.jsonify(data), 200

@app.route("/DM/get/<id>",methods=["GET"])
@pny.db_session
def get_data(id):
    registeredData=Data[id]
    if registeredData is not None:
        return _get_data_from_location(registeredData)
    else:
        return "Data not found", 400

# puts a stream of data to a location, avoids having to create a temporary file first and transfer it
@app.route("/DM/put",methods=["PUT"])
def put_data():    
    registered_status=_perform_registration(flask.request.form)
    if registered_status[1] == 201:
        return _put_data_to_location(flask.request.form["payload"], registered_status[0])        
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
    id=_register(fname,path,machine,description,size,originator,group,storage_technology)
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

    if _checkExists(machine,fname,path):
        return "File already exists", 406

    #instruct the machine to download the file (passes the size of the file back in the "options" dict)
    try:
        status, message = _download(fname, path, storage_technology, machine, url, protocol, options)
    except ConnectionManager.ConnectionError as e:
        return str(e), 500

    if status == OK:
        size=message
        #register this new file with the data manager
        id=_register(fname,path, machine, description,size, originator, group, storage_technology)
        return id, 201
    elif status == NOT_IMPLEMENTED:
        return message, 501
    elif status==FILE_ERROR:
        return message, 500

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
    status, message =_delete(file,machine, d.storage_technology)    

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


#moves the data entity to a long term file storage location and marks it as archived
@app.route("/DM/archive/<id>",methods=["PUT"])
def archive(id):
    return "Not Implemented", 501

#moves the data entity from long term storage onto a machine and marks it as active
@app.route("/DM/activate/<id>",methods=["PUT"])
def activate(id):
    return "Not Implemented", 501


#--------------------- helper functions --------------------------

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
        size = data.size
        originator = data.originator
        group = data.group    

    #get the options from the header
    dest_machine = flask.request.form["machine"]
    dest = flask.request.form["dest"]
    if "storage_technology" in flask.request.form:
        dest_storage_technology = flask.request.form["storage_technology"]
    else:
        dest_storage_technology = "FILESYSTEM"

    with pny.db_session:
        transfer_id = str(uuid.uuid4())
        data_transfer = DataTransfer(id=transfer_id,
                                     src_id=id,
                                     src_machine=src_machine,
                                     dst_machine=dest_machine,
                                     date_started=datetime.datetime.now(),
                                     status="STARTED")

    path,fname = os.path.split(dest)
    if _checkExists(dest_machine,fname,path):        
        with pny.db_session:
            DataTransfer[transfer_id].status = "FAILED"
        return "File already exists", 406    

    # perform move or copy on the file
    status, message =_copy(src, src_machine, data.storage_technology, dest, dest_machine, dest_storage_technology, move=move)
    date_completed = datetime.datetime.now()

    if status == FILE_ERROR:
        with pny.db_session:
            DataTransfer[transfer_id].status = "FAILED"
        return message, 500
    if status == NOT_IMPLEMENTED:
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
                new_id =_register(fname,path,dest_machine,description,size,originator,group,dest_storage_technology)
            data_transfer = DataTransfer[transfer_id]
            data_transfer.status = "COMPLETED"
            data_transfer.dst_id = new_id
            data_transfer.date_completed = date_completed
            data_transfer.completion_time = (data_transfer.date_completed -
                                             data_transfer.date_started)
        return new_id, 201

#Creates a new entry in the database
@pny.db_session
def _register(fname,path,machine,description,size,originator,group,storage_technology="FILESYSTEM"):
    id = str(uuid.uuid4())
    d=Data(id=id,machine=machine,filename=fname,path=path,description=description,size=size,date_registered=datetime.datetime.now(),originator=originator,group=group,storage_technology=storage_technology)
    return id

#deletes a file, and marks its entry in the database as deleted
def _delete(file, machine, storage_technology):
    if machine == "localhost":  
        if storage_technology == "FILESYSTEM":
            try:
                os.remove(file)
            except OSError as e:
                return FILE_ERROR, str(e)            
        elif storage_technology == "VESTECDB":
            data_item=LocalDataStorage.get(filename=src)
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
    print("Copying %s from %s to %s with new name %s"%(src,src_machine,dest_machine,dest))
    #copy within a machine
    if src_machine == dest_machine:        
        #local copy on the VESTEC server
        if src_machine == "localhost":   
            if src_storage_technology == "FILESYSTEM":
                if move:
                    command = "mv %s %s"%(src,dest)
                else:
                    command = "cp %s %s"%(src,dest)
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
                asyncio.run(transfer_file_to_or_from_machine(dest_machine, src, dest, download=False))
            elif src_storage_technology == "VESTECDB":
                data_item=LocalDataStorage.get(filename=src)
                asyncio.run(submit_copy_bytes_to_machine(dest_machine, data_item.contents, dest))
                if move:
                    data_item.delete()
                return OK, "copied"

        #copy from remote machine to VESTEC server
        elif dest_machine == "localhost":
            if dest_storage_technology == "FILESYSTEM":
                asyncio.run(transfer_file_to_or_from_machine(src_machine, src, dest, download=True))
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

def _get_data_from_location(registered_data):
    if len(registered_data.path) > 0:
        target_src=registered_data.path+"/"+registered_data.filename
    else:
        target_src=registered_data.filename
    if registered_data.machine == "localhost":   
        if registered_data.storage_technology == "FILESYSTEM":
            readFile = open(target_src, "wb")
            data_payload=readFile.read()
            readFile.close()
            return data_payload, 201
        elif registered_data.storage_technology == "VESTECDB":
            localData=LocalDataStorage.get(filename=target_src)
            return localData.contents, 201
    else:
        contents=asyncio.run(submit_remote_get_data(registered_data.machine, target_src))
        return contents, 201

async def submit_remote_get_data(target_machine_name, src_file):
    client = await Client.create(target_machine_name)              
    return await client.get(src_file)     

@pny.db_session
def _put_data_to_location(data_payload, data_uuid):
    registered_data=Data[data_uuid]
    if registered_data is not None:
        # If we are provided with a string then perform an implicit conversion to bytes
        if isinstance(data_payload, str): data_payload=bytes(data_payload, encoding='utf8')
        if len(registered_data.path) > 0:
            target_dest=registered_data.path+"/"+registered_data.filename
        else:
            target_dest=registered_data.filename
        if registered_data.machine == "localhost":   
            if registered_data.storage_technology == "FILESYSTEM":
                newFile = open(target_dest, "wb")
                newFile.write(data_payload)
                newFile.close()
            elif registered_data.storage_technology == "VESTECDB":                
                new_data_item=LocalDataStorage(contents=data_payload, filename=target_dest, filetype="")            
        else:
            asyncio.run(submit_remote_put_data(registered_data.machine, data_payload, target_dest))
        return "Data put completed", 201
    else:
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
            return NOT_IMPLEMENTED
        if machine == "localhost" and storage_technology == "VESTECDB":
            # If its localhost and VESTECDB then use a temporary file
            temp = tempfile.NamedTemporaryFile()
            cmd = "curl -f -sS -o %s %s"%(temp.name,url)
        else:
            cmd = "curl -f -sS -o %s %s"%(dest,url)
    else:
        print("Do not know how to handle protocols that are not http")
        return NOT_IMPLEMENTED, "'%s' protocol not supported (yet?)"%protocol

    if machine == "localhost":
        #run the command locally        
        r=subprocess.run(cmd.split(" "),stdout=subprocess.PIPE,stderr = subprocess.PIPE,text=True)
        if r.returncode != 0:
            print("An error occurred in the local download")
            print(r.stderr)
            print(r.stdout)
            return FILE_ERROR, r.stderr
        else:
            #get size of the new file and put this in the options dict
            size=os.path.getsize(dest)            
            if storage_technology == "VESTECDB":
                # Transfer temporary file into the VESTECDB
                byte_contents=temp.read()
                temp.close()
                new_file = LocalDataStorage(contents=byte_contents, filename=dest, filetype="")
            return OK, size            

    else:        
        #run the command remotely
        success, size_or_error=asyncio.run(submit_run_command_on_machine(machine, cmd, dest))        
        if not success:
            print("Remote download encountered an error:")              
            return FILE_ERROR, size_or_error
        else:
            print("Remote download completed successfully")                                           
            return OK, size_or_error

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

if __name__ == "__main__":
    initialiseDatabase()
    app.run(host='0.0.0.0', port=5000)
