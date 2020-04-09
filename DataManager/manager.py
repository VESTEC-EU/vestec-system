import sys
sys.path.append("../")
import flask
import uuid
import pony.orm as pny
from pony.orm.serialization import to_dict
from db import Data, initialise_database
import datetime
import os
import ConnectionManager

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
    
    #register this with the database and return its UUID
    id=_register(fname,path,machine,description,size,originator,group)
    return id, 201

#instructs the data manager to download data from the internet onto a specified machine. Returns a uuid for that data entity
@app.route("/getexternal",methods=["PUT"])
def GetExternal():
    return "Not Implemented", 501

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
    
    #move the file
    result =_copy(src,src_machine,dest,dest_machine,move=True)
    if result == FILE_ERROR:
        print("Move failed")
        return "Move failed", 500
    if result == NOT_IMPLEMENTED:
        return "Request not implemented on server", 501
    elif result == OK:
        with pny.db_session:
            data=Data[id]
            data.machine = dest_machine
            data.path, data.filename = os.path.split(dest)
            data.date_modified=datetime.datetime.now()
            print("Move successful")
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
    
    #copy the file
    result =_copy(src,src_machine,dest,dest_machine)
    if result == FILE_ERROR:
        return "Copy failed", 500
    if result == NOT_IMPLEMENTED:
        return "Request not implemented on server", 501
    elif result == OK:
        path,fname = os.path.split(dest)
        id =_register(fname,path,dest_machine,description,size,originator,group)
        return id, 201



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
    status=_delete(file,machine)

    if status == FILE_ERROR:
        with pny.db_session:
            Data[id].status = "UNKNOWN"
        return "Deletion failed - file not found?", 500
    elif status == NOT_IMPLEMENTED:
        return "Remote deletion not implemented", 501
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
        except OSError:
            return FILE_ERROR
        else:
            return OK
    else:
        connection = ConnectionManager.RemoteConnection(machine)
        try:
            connection.rm(file)
        except Exception as e:
            print("Deletion failed")
            print("%s"%e)
            connection.CloseConnection()
            return FILE_ERROR
        connection.CloseConnection()
        return OK

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
            err = os.system(command)
            if err == 0:
                return OK
            else:
                return FILE_ERROR
        
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
                return OK
            else:
                print("Error")
                print(stderr)
                return FILE_ERROR
            
    else:
        #copy from VESTEC server to remote machine
        if src_machine == "localhost":
            connection = ConnectionManager.RemoteConnection(dest_machine)
            try:
                connection.CopyToMachine(src,dest)
            except FileNotFoundError as e:
                print("Error: %s"%e)
                connection.CloseConnection()
                return FILE_ERROR
            else:
                connection.CloseConnection()
                if move:
                    result=os.system("rm %s"%src)
                    if result != 0:
                        print("Error - Unable to remove local file")
                        return FILE_ERROR
                return OK

        #copy from remote machine to VESTEC server
        elif dest_machine == "localhost":
            connection = ConnectionManager.RemoteConnection(src_machine)
            try:
                connection.CopyFromMachine(src,dest)
            except FileNotFoundError as e:
                print("Error: %s"%e)
                connection.CloseConnection()
                return FILE_ERROR
            else:
                if move:
                    try:
                        connection.rm(src)
                    except Exception as e:
                        connection.CloseConnection()
                        print('Error: Unable to remove file')
                        print("%s"%e)
                        return FILE_ERROR
                connection.CloseConnection()
                return OK
            
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
                return FILE_ERROR
            else:
                if move:
                    try:
                        connection.rm(src)
                    except Exception as e:
                        print("Error: unable to remove file")
                        print("%s"%e)
                        connection.CloseConnection()
                        return FILE_ERROR
                connection.CloseConnection()
                return OK
            


#downloads a file to a (possibly remote) locarion
def _download(uri,machine,dest):
    return

if __name__ == "__main__":
    initialise_database()
    app.run()
