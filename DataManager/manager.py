import sys
sys.path.append("../")
import flask
import uuid
import pony.orm as pny
from pony.orm.serialization import to_dict
from db import Data, DataTransfer, initialise_database
import datetime
import os
import ConnectionManager
import json
import subprocess

app = flask.Flask(__name__)

OK=0
FILE_ERROR=1
NOT_IMPLEMENTED = 2

#Returns the information for all data entities, or for a specified entity
@app.route("/info")
@app.route("/info/<id>")
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


#registers a data entity with the DataManager, and returns its uuid
@app.route("/register",methods=["PUT"])
def register():
    #get the info from the request
    fname = flask.request.form["filename"]
    path = flask.request.form["path"]
    machine = flask.request.form["machine"]
    description = flask.request.form["description"]
    size = flask.request.form["size"]
    originator = flask.request.form["originator"]
    group = flask.request.form["group"]

    if _checkExists(machine,fname,path):
        return "File already exists", 406
    
    #register this with the database and return its UUID
    id=_register(fname,path,machine,description,size,originator,group)
    return id, 201

#instructs the data manager to download data from the internet onto a specified machine. Returns a uuid for that data entity
@app.route("/getexternal",methods=["PUT"])
def GetExternal():
    #get required fields from the header
    fname = flask.request.form["filename"]
    path = flask.request.form["path"]
    machine = flask.request.form["machine"]
    description = flask.request.form["description"]
    originator = flask.request.form["originator"]
    group = flask.request.form["group"]
    url = flask.request.form["url"]
    protocol = flask.request.form["protocol"]
    options = json.loads(flask.request.form["options"])

    if _checkExists(machine,fname,path):
        return "File already exists", 406

    #instruct the machine to download the file (passes the size of the file back in the "options" dict)
    try:
        status, message = _download(fname,path,machine,url,protocol,options)
    except ConnectionManager.ConnectionError as e:
        return str(e), 500

    if status == OK:
        size=options["size"]
        #register this new file with the data manager
        id=_register(fname,path,machine,description,size,originator,group)
        return id, 201
    elif status == NOT_IMPLEMENTED:
        return message, 501
    elif status==FILE_ERROR:
        return message, 500
    

#Moves a data entity from one location to another
@app.route("/move/<id>",methods=["POST"])
def move(id):
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

    path,fname = os.path.split(dest)
    if _checkExists(dest_machine,fname,path):
        return "File already exists", 406
    
    #move the file
    try:
        date_started = datetime.datetime.now()
        status, message =_copy(src,src_machine,dest,dest_machine,move=True)
        date_completed = datetime.datetime.now()
        completion_time = date_completed - date_started
    except ConnectionManager.ConnectionError as e:
        return str(e), 500

    if status == FILE_ERROR:
        print("Move failed")
        return message, 500
    if status == NOT_IMPLEMENTED:
        return message, 501
    elif status == OK:
        with pny.db_session:
            data=Data[id]
            data.machine = dest_machine
            data.path, data.filename = os.path.split(dest)
            data.date_modified=datetime.datetime.now()
            print("Move successful")
            data_transfer = DataTransfer(id=str(uuid.uuid4()),
                                         src_id=id,
                                         dst_id=id,
                                         src_machine=src_machine,
                                         dst_machine=dest_machine,
                                         date_started=date_started,
                                         date_completed=date_completed,
                                         completion_time=completion_time)
        return "Move successful", 200

#copies a data entity to a new location, returning the uuid of the copy
@app.route("/copy/<id>",methods=["POST"])
def copy(id):
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

    path,fname = os.path.split(dest)
    if _checkExists(dest_machine,fname,path):
        return "File already exists", 406
    
    #copy the file
    try:
        date_started = datetime.datetime.now()
        status, message =_copy(src,src_machine,dest,dest_machine)
        date_completed = datetime.datetime.now()
        completion_time = date_completed - date_started
    except ConnectionManager.ConnectionError as e:
        return str(e), 500

    if status == FILE_ERROR:
        return message, 500
    if status == NOT_IMPLEMENTED:
        return message, 501
    elif status == OK:
        with pny.db_session:
            path,fname = os.path.split(dest)
            new_id =_register(fname,path,dest_machine,description,size,originator,group)
            data_transfer = DataTransfer(id=str(uuid.uuid4()),
                                         src_id=id,
                                         dst_id=id,
                                         src_machine=src_machine,
                                         dst_machine=dest_machine,
                                         date_started=date_started,
                                         date_completed=date_completed,
                                         completion_time=completion_time)
        return new_id, 201



#deletes a data entity. This marks the entity as "DELETED" in the database and deletes the file
@app.route("/remove/<id>",methods=["DELETE"])
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
    try:
        status, message =_delete(file,machine)
    except ConnectionManager.ConnectionError as e:
        return str(e), 500

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
@app.route("/archive/<id>",methods=["PUT"])
def archive(id):
    return "Not Implemented", 501

#moves the data entity from long term storage onto a machine and marks it as active
@app.route("/activate/<id>",methods=["PUT"])
def activate(id):
    return "Not Implemented", 501


#--------------------- helper functions --------------------------



#Creates a new entry in the database
@pny.db_session
def _register(fname,path,machine,description,size,originator,group):
    id = str(uuid.uuid4())
    d=Data(id=id,machine=machine,filename=fname,path=path,description=description,size=size,date_registered=datetime.datetime.now(),originator=originator,group=group)
    return id

#deletes a file, and marks its entry in the database as deleted
def _delete(file,machine):
    if machine == "localhost":
        print("Deleting %s"%file)
        try:
            os.remove(file)
        except OSError as e:
            return FILE_ERROR, str(e)
        else:
            return OK, "deleted"
    else:
        connection = ConnectionManager.RemoteConnection(machine)
        try:
            connection.rm(file)
        except Exception as e:
            print("Deletion failed")
            print("%s"%e)
            connection.CloseConnection()
            return FILE_ERROR, str(e)
        connection.CloseConnection()
        return OK, "Deleted"

        #return NOT_IMPLEMENTED


#copies a file between two (possibly remote) locations. If move=true this acts like a move (deletes the source file)
def _copy(src,src_machine,dest,dest_machine,move=False):
    print("Copying %s from %s to %s with new name %s"%(src,src_machine,dest_machine,dest))
    #copy within a machine
    if src_machine == dest_machine:
        if move:
            command = "mv %s %s"%(src,dest)
        else:
            command = "cp %s %s"%(src,dest)

        print(command)

        #local copy on the VESTEC server
        if src_machine == "localhost":
            result = subprocess.run(command.split(" "),stdout=subprocess.PIPE, stderr=subprocess.PIPE,text=True)
            if result.returncode == 0:
                return OK, "copied"
            else:
                return FILE_ERROR, result.stderr
        
        #local copy on a remote machine
        else:
            connection=ConnectionManager.RemoteConnection(src_machine)
            if move:
                cmd = "mv %s %s"%(src,dest)
            else:
                cmd = "cp %s %s"%(src,dest)
            stdout, stderr, code = connection.ExecuteCommand(cmd)
            connection.CloseConnection()
            if code == 0:    
                return OK, "copied"
            else:
                print("Error")
                print(stderr)
                return FILE_ERROR, stderr
            
    else:
        #copy from VESTEC server to remote machine
        if src_machine == "localhost":
            connection = ConnectionManager.RemoteConnection(dest_machine)
            try:
                connection.CopyToMachine(src,dest)
            except FileNotFoundError as e:
                print("Error: %s"%e)
                connection.CloseConnection()
                return FILE_ERROR, str(e)
            else:
                connection.CloseConnection()
                if move:
                    try:
                        result=os.remove(src)
                    except OSError as e:
                        print("Error - Unable to remove local file")
                        return FILE_ERROR, str(e)
                return OK, "copied"

        #copy from remote machine to VESTEC server
        elif dest_machine == "localhost":
            connection = ConnectionManager.RemoteConnection(src_machine)
            try:
                connection.CopyFromMachine(src,dest)
            except FileNotFoundError as e:
                print("Error: %s"%e)
                connection.CloseConnection()
                return FILE_ERROR, str(e)
            else:
                if move:
                    try:
                        connection.rm(src)
                    except Exception as e:
                        connection.CloseConnection()
                        print('Error: Unable to remove file')
                        print("%s"%e)
                        return FILE_ERROR, str(e)
                connection.CloseConnection()
                return OK, "copied"
            
        #copy between two remote machines
        else:
            connection = ConnectionManager.RemoteConnection(src_machine)
            user = ConnectionManager.machines[dest_machine]["username"]
            machine = ConnectionManager.machines[dest_machine]["host"]
            machinestr = user+"@"+machine+":"+dest
            cmd = "scp "+src+" "+machinestr
            print(cmd)
            stdout, stderr, code = connection.ExecuteCommand(cmd)
            if code != 0:
                print("Error")
                print(stderr)
                connection.CloseConnection()
                return FILE_ERROR, stderr
            else:
                if move:
                    try:
                        connection.rm(src)
                    except Exception as e:
                        print("Error: unable to remove file")
                        print("%s"%e)
                        connection.CloseConnection()
                        return FILE_ERROR, str(e)
                connection.CloseConnection()
                return OK, "copied"
            


#downloads a file to a (possibly remote) location
def _download(filename,path,machine,url,protocol,options):
    #get the filename (with path ) of the file we want created 
    dest = os.path.join(path,filename)
    
    #deterine the command we wish to run to download the file
    if protocol == "http":
        if options:
            print("Do not know how to deal with non-empty options")
            print(options)
            return NOT_IMPLEMENTED
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
            options["size"]=size
            return OK, "Downloaded"
    else:
        #run the command remotely
        c = ConnectionManager.RemoteConnection(machine)
        stdout,stderr,exit_code = c.ExecuteCommand(cmd)
        if exit_code != 0:
            print("Remote download encountered an error:")
            print(stderr)
            c.CloseConnection()
            return FILE_ERROR, stderr
        else:
            print("Remote download completed successfully")
            #get the size of the new file and put it in the options dict
            size = c.size(dest)
            options["size"]=size
            c.CloseConnection()
            return OK, "Downloaded"

@pny.db_session
def _checkExists(machine,filename,path):
    print("Checking for %s, %s, %s"%(machine,filename,path))
    entries = pny.select(d for d in Data if (d.status!="DELETED" and d.status!="UNKNOWN") and d.machine == machine and d.path==path and d.filename == filename)

    if len(entries)>0:
        return True
    else:
        return False
    



if __name__ == "__main__":
    initialise_database()
    app.run()
