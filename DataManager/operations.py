import sys
sys.path.append("../")
import pony.orm as pny
import uuid
from Database import Data, DataTransfer
import datetime
import os
import ConnectionManager
import json
import subprocess


OK=0
FILE_ERROR=1
NOT_IMPLEMENTED = 2

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
def _copy(src,src_machine,dest,dest_machine,id,move=False):
    print("Copying %s from %s to %s with new name %s"%(src,src_machine,dest_machine,dest))

    connection = None

    with pny.db_session:
        transfer_id = str(uuid.uuid4())
        data_transfer = DataTransfer(id=transfer_id,
                                     src_id=id,
                                     src_machine=src_machine,
                                     dst_machine=dest_machine,
                                     date_started=datetime.datetime.now(),
                                     status="STARTED")
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
                status = OK
            else:
                status = FILE_ERROR
            message = result.stderr

        #local copy on a remote machine
        else:
            try:
                connection=ConnectionManager.RemoteConnection(src_machine)
                if move:
                    cmd = "mv %s %s"%(src,dest)
                else:
                    cmd = "cp %s %s"%(src,dest)
                stdout, stderr, code = connection.ExecuteCommand(cmd)
            
                if code == 0:
                    status=OK
                else:
                    status = FILE_ERROR
                message = stderr
            except Exception as e:
                status = FILE_ERROR
                message = str(e) 
            finally:
                if connection is not None:
                    connection.CloseConnection()

    else:
        #copy from VESTEC server to remote machine
        if src_machine == "localhost": 
            try:
                connection = ConnectionManager.RemoteConnection(dest_machine)
                connection.CopyToMachine(src,dest)
            except Exception as e:
                print("Error: %s"%e)
                status = FILE_ERROR
                message = str(e)
            else:
                status = OK
                if move:
                    try:
                        result=os.remove(src)
                    except OSError as e:
                        print("Error - Unable to remove local file")
                        status = FILE_ERROR
                        message = "Unable to delete local file"
            finally:
                if connection is not None:
                    connection.CloseConnection()
                    

        #copy from remote machine to VESTEC server
        elif dest_machine == "localhost":
            try:
                connection = ConnectionManager.RemoteConnection(src_machine)
                connection.CopyFromMachine(src,dest)
            except Exception as e:
                print("Error: %s"%e)
                message = str(e)
                status = FILE_ERROR
                
            else:
                status = OK
                if move:
                    try:
                        connection.rm(src)
                    except Exception as e:
                        print('Error: Unable to remove file')
                        print("%s"%e)
                        status = FILE_ERROR
                        message = str(e)
            finally:
                if connection is not None:
                    connection.CloseConnection()

        #copy between two remote machines
        else:
            try:
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
                    status = FILE_ERROR
                    message = stderr
                else:
                    if move:
                        try:
                            connection.rm(src)
                        except Exception as e:
                            print("Error: unable to remove file")
                            print("%s"%e)
                            status = FILE_ERROR
                            message = str(e)
                    status = OK
            except Exception as e:
                message = str(e)
                status = FILE_ERROR
            finally:
                if connection is not None:
                    connection.CloseConnection()

    #now record this in the data transfer table 
    with pny.db_session:
        transfer = DataTransfer[transfer_id]
        if status == OK:
            transfer.status = "COMPLETED"
            transfer.date_completed = datetime.datetime.now()
            transfer.completion_time = transfer.date_completed - transfer.date_started
        else:
            transfer.status = "ERROR"

    if status != OK:
        return status, message
    else:
        if move:
            return status, "Move completed"
        else:
            return status, "Copy completed"
    



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

#Checks to see if the file exists
@pny.db_session
def _checkExists(machine,filename,path):
    print("Checking for %s, %s, %s"%(machine,filename,path))
    entries = pny.select(d for d in Data if (d.status!="DELETED" and d.status!="UNKNOWN") and d.machine == machine and d.path==path and d.filename == filename)

    if len(entries)>0:
        return True
    else:
        return False
