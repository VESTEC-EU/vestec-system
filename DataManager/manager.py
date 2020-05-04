import sys
sys.path.append("../")
import flask
import uuid
import pony.orm as pny
from pony.orm.serialization import to_dict
from Database import db, initialiseDatabase, Data, DataTransfer, DMTasks
import datetime
import os
import ConnectionManager
import json
import subprocess
from DMAsync import SubmitTask

from operations import _register, _delete, _copy, _download, _checkExists

app = flask.Flask(__name__)

OK=0
FILE_ERROR=1
NOT_IMPLEMENTED = 2

#Returns the information for all data entities, or for a specified entity
@app.route("/DM/info")
@app.route("/DM/info/<id>")
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
@app.route("/DM/register",methods=["PUT"])
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
@app.route("/DM/getexternal",methods=["PUT"])
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
@app.route("/DM/move/<id>",methods=["POST"])
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
        status, message =_copy(src,src_machine,dest,dest_machine,id,move=True)
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

        return "Move successful", 200

#copies a data entity to a new location, returning the uuid of the copy
@app.route("/DM/copy/<id>",methods=["POST"])
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
        status, message =_copy(src,src_machine,dest,dest_machine,id)
      
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
            
        return new_id, 201



#deletes a data entity. This marks the entity as "DELETED" in the database and deletes the file
@app.route("/DM/delete/<id>",methods=["DELETE"])
def delete(id):
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
            return "%s:%s deleted"%(machine,file), 200


#moves the data entity to a long term file storage location and marks it as archived
@app.route("/DM/archive/<id>",methods=["PUT"])
def archive(id):
    return "Not Implemented", 501

#moves the data entity from long term storage onto a machine and marks it as active
@app.route("/DM/activate/<id>",methods=["PUT"])
def activate(id):
    return "Not Implemented", 501


@app.route("/DM/async/status/<id>",methods=["GET"])
def async_status(id):
    #returns the status of the requested task id
    with pny.db_session:
        try:
            task=DMTasks[id]
        except pny.core.ObjectNotFound as e:
            return "Async task not found", 404
        status = task.status
        result = task.result

        return json.dumps({"status": status, "result": result}), 200
        
    
    

@app.route("/DM/async/copy/<id>",methods=["POST"])
def async_copy(id):
    #requests an asynchronous copy. Returns the UUID of the task, which can be queried by DM/async/status
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

    #create dict for the message
    message={}
    message["src"] = src
    message["src_machine"] = src_machine
    message["dest"] = dest
    message["dest_machine"] = dest_machine
    message["description"] = description
    message["size"] = size
    message["originator"]= originator
    message["group"] = group
    message["operation"] = "COPY"
    message["fileID"] = id
    
    path,fname = os.path.split(dest)
    if _checkExists(dest_machine,fname,path):
        return "File already exists", 406
    
    try:
        id=SubmitTask(message)
    except Exception as e:
        print(e)
        return str(e), 500
    else:
        if id is None:
            return "Some weird failure", 500
        else:
            return id, 200



@app.route("/DM/async/move/<id>",methods=["POST"])
def async_move(id):
    #requests an async move. Returns the UUID of the task, which can be queried by DM/async/status
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

    #create dict for the message
    message={}
    message["src"] = src
    message["src_machine"] = src_machine
    message["dest"] = dest
    message["dest_machine"] = dest_machine
    message["description"] = description
    message["size"] = size
    message["originator"]= originator
    message["group"] = group
    message["operation"] = "MOVE"
    message["fileID"] = id
    
    path,fname = os.path.split(dest)
    if _checkExists(dest_machine,fname,path):
        return "File already exists", 406
    
    try:
        id=SubmitTask(message)
    except Exception as e:
        print(e)
        return str(e), 500
    else:
        if id is None:
            return "Some weird failure", 500
        else:
            return id, 200

@app.route("/DM/async/getexternal",methods=["PUT"])
def async_download():
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

    message={}
    message["fname"]= fname
    message["path"] = path
    message["machine"] = machine
    message["url"] = url
    message["protocol"] = protocol
    message["options"] = options
    message["description"] = description
    message["originator"] = originator
    message["group"] = group

    message["operation"] = "DOWNLOAD"

    #submit the async task
    try:
        id=SubmitTask(message)
    except Exception as e:
        print(e)
        return str(e), 500
    else:
        if id is None:
            return "Some weird failure", 500
        else:
            return id, 200
            


if __name__ == "__main__":
    initialiseDatabase()
    app.run(host='0.0.0.0', port=5000)
