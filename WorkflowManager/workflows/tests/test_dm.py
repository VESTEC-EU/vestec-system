import manager.workflow as workflow
import DataManager.client as client
import requests
import time
import os
import json

from .utils import logfile, logTest


@workflow.handler
def dm_tests_init(msg):
    incident = msg["IncidentID"]
    logdir = msg["logdir"]

    with logfile(logdir) as f:
        f.write("Data Manager tests\n")
    
    workflow.send(msg,"dm_tests_register")


@workflow.handler
def dm_tests_complete(msg):
    incident = msg["IncidentID"]
    logdir = msg["logdir"]

    workflow.send(msg,"run_tests")

#creates testfile1.txt
@workflow.handler
def dm_tests_register(msg):
    incident = msg["IncidentID"]
    logdir = msg["logdir"]

    msg["files"] = []

    #create file locally
    fname = os.path.join(logdir,"testfile1.txt")
    fname = os.path.abspath(fname)
    
    f=open(fname,"w")
    f.write(incident)
    f.close()

    path,fname = os.path.split(fname)

    size = os.path.getsize(fname)

    #register this file
    try:
        fileid=client.registerDataWithDM(fname,"localhost","test file","txt",size,originator="vestec_tests",associate_with_incident=True,incidentId=incident,path=path)
    except client.DataManagerException as e:
        print(e.message)
        logTest("dm_register","FAIL",logdir,e.message)
        msg["total_tests"]+=1
        msg["failed_tests"]+=1
        cleanup(msg)
        return
    logTest("dm_register","PASS",logdir)
    msg["total_tests"]+=1
    msg["passed_tests"]+=1

    msg["file1"]=fileid
    

    workflow.send(msg,"dm_tests_retreive")

@workflow.handler
def dm_tests_retreive(msg):
    incident = msg["IncidentID"]
    logdir = msg["logdir"]
    
    try:
        data=client.getByteDataViaDM(msg["file1"])
    except client.DataManagerException as e:
        print(e.message)
        logTest("dm_retreive","FAIL",logdir,e.message)
        msg["total_tests"]+=1
        msg["failed_tests"]+=1
        cleanup(msg)
        return
    text = data.decode("ascii")

    if text == incident:
        logTest("dm_retreive","PASS",logdir)
        msg["total_tests"]+=1
        msg["passed_tests"]+=1
        
    else:
        logTest("dm_retreive","FAIL",logdir,"Retreived file does not match the original file")
        msg["total_tests"]+=1
        msg["failed_tests"]+=1
    
   

    workflow.send(msg,"dm_tests_copy")

#copies testfile1.txt to testfile2.txt
@workflow.handler
def dm_tests_copy(msg):
    incident = msg["IncidentID"]
    logdir = msg["logdir"]

    fname = "testfile2.txt"
    dir = os.path.abspath(logdir)

    file1id = msg["file1"]

    try:
        file2id=client.copyDataViaDM(file1id,os.path.join(dir,fname),"localhost",associate_with_incident=True, incident=incident)
    except client.DataManagerException as e:
        print(e.message)
        logTest("dm_copy","FAIL",logdir,e.message)
        msg["total_tests"]+=1
        msg["failed_tests"]+=1
        cleanup(msg)
        return
    
    #check this new file exists
    if os.path.isfile(os.path.join(dir,fname)) is False:
        logTest("dm_copy","FAIL",logdir,"Copied file does not appear to be at its location")
        msg["total_tests"]+=1
        msg["failed_tests"]+=1
        cleanup(msg)
        return


    #check its contants are correct
    f=open(os.path.join(dir,fname),"r")
    text = f.read()
    if text != incident:
        logTest("dm_copy","FAIL",logdir,"Copied file has wrong contents")
        msg["total_tests"]+=1
        msg["failed_tests"]+=1
        cleanup(msg)
        return

    logTest("dm_copy","PASS",logdir)
    msg["total_tests"]+=1
    msg["passed_tests"]+=1

    msg["file2"] = file2id

    
    workflow.send(msg,"dm_tests_move")
    

#moves testfile2.txt to testfile3.txt
@workflow.handler
def dm_tests_move(msg):
    incident = msg["IncidentID"]
    logdir = msg["logdir"]

    fname = "testfile3.txt"
    dir = os.path.abspath(logdir)

    file2id = msg["file2"]

    try:
        file3id=client.moveDataViaDM(file2id,os.path.join(dir,fname),"localhost")
    except client.DataManagerException as e:
        print(e.message)
        logTest("dm_move","FAIL",logdir,e.message)
        msg["total_tests"]+=1
        msg["failed_tests"]+=1
        cleanup(msg)
        return

    
    #check this new file exists
    if os.path.isfile(os.path.join(dir,fname)) is False:
        logTest("dm_move","FAIL",logdir,"Moved file does not appear to be at its location")
        msg["total_tests"]+=1
        msg["failed_tests"]+=1
        cleanup(msg)
        return

    #check this new file exists
    if os.path.isfile(os.path.join(dir,"testfile2.txt")) is True:
        logTest("dm_move","FAIL",logdir,"Moved file still exists at its old position")
        msg["total_tests"]+=1
        msg["failed_tests"]+=1
        cleanup(msg)
        return


    #check its contents are correct
    f=open(os.path.join(dir,fname),"r")
    text = f.read()
    if text != incident:
        logTest("dm_move","FAIL",logdir,"Moved file has wrong contents")
        msg["total_tests"]+=1
        msg["failed_tests"]+=1
        cleanup(msg)
        return

    logTest("dm_move","PASS",logdir)
    msg["total_tests"]+=1
    msg["passed_tests"]+=1

    
    workflow.send(msg,"dm_tests_search")



@workflow.handler
def dm_tests_search(msg):
    incident = msg["IncidentID"]
    logdir = msg["logdir"]
    dir = os.path.abspath(logdir)
    
    try:
        result = client.searchForDataInDM("testfile1.txt","localhost",dir)
    except client.DataManagerException as e:
        logTest("dm_search","FAIL",logdir,"Unable to locate file with search: %s"%e.message)
        msg["total_tests"]+=1
        msg["failed_tests"]+=1
    else:
        if result["id"] == msg["file1"]:
            logTest("dm_search","PASS",logdir)
            msg["total_tests"]+=1
            msg["passed_tests"]+=1
        else:
            logTest("dm_search","FAIL",logdir,"Wrong file id returned. Got %s. Should be %s"%(result["id"],msg["file1"]))
            msg["total_tests"]+=1
            msg["failed_tests"]+=1

    
    workflow.send(msg,"dm_tests_put")



@workflow.handler
def dm_tests_put(msg):
    incident = msg["IncidentID"]
    logdir = msg["logdir"]
    dir = os.path.abspath(logdir)

    contents = ("%s"%incident).encode("ascii")

    try:
        id = client.putByteDataViaDM(filename = "testfile4.txt",
                                machine = "localhost",
                                description = "File added by PUT",
                                type = "txt",
                                originator="dm_tests",
                                payload = contents,
                                path = dir)
    except client.DataManagerException as e:
        logTest("dm_put","FAIL",logdir,"Unable to put file")
        msg["total_tests"]+=1
        msg["failed_tests"]+=1
        cleanup(msg)

    msg["file4"] = id

    
    try:
        contents2 = client.getByteDataViaDM(id)
    except client.DataManagerException as e:
        logTest("dm_put","FAIL",logdir,"Unable to retrieve put file")
        msg["total_tests"]+=1
        msg["failed_tests"]+=1
        cleanup(msg)
    
    if contents2 == contents:
        logTest("dm_put","PASS",logdir)
        msg["total_tests"]+=1
        msg["passed_tests"]+=1
    else:
        print(contents,contents2)
        logTest("dm_put","FAIL",logdir,"Retrieved put data does not match original file")
        msg["total_tests"]+=1
        msg["passed_tests"]+=1
    
    workflow.send(msg,"dm_tests_download")



@workflow.handler
def dm_tests_download(msg):
    incident = msg["IncidentID"]
    logdir = msg["logdir"]
    dir = os.path.abspath(logdir)

    comp = requests.get("https://www.google.com/images/branding/googleg/1x/googleg_standard_color_128dp.png").content
    #print(len(comp))

    try:
        id = client.downloadDataToTargetViaDM("testfile5.png",
        "localhost",
        "test downloaded data",
        "png",
        "test_dm",
        "https://www.google.com/images/branding/googleg/1x/googleg_standard_color_128dp.png",
        "http",
        path=dir)
    except client.DataManagerException as e:
        print(e)
        logTest("dm_download","FAIL",logdir,"Unable to download file")
        msg["total_tests"]+=1
        msg["failed_tests"]+=1
        cleanup(msg)
    

    try:
        content = client.getByteDataViaDM(id)
    except client.DataManagerException as e:
        logTest("dm_download","FAIL",logdir,"Unable to get downloaded file from DM")
        msg["total_tests"]+=1
        msg["failed_tests"]+=1
        cleanup(msg)
    
    #print(len(content))
    #content = content.decode("utf-8")
    
    if content != comp:
        print(content)
        print("")
        print(comp)
        logTest("dm_download","FAIL",logdir,"Downloaded data does not match what it should be")
        msg["total_tests"]+=1
        msg["failed_tests"]+=1
        cleanup(msg)
    else:
        logTest("dm_download","PASS",logdir)
        msg["total_tests"]+=1
        msg["passed_tests"]+=1

    msg["file5"]=id

    workflow.send(msg,"dm_tests_delete")




@workflow.handler
def dm_tests_delete(msg):
    incident = msg["IncidentID"]
    logdir = msg["logdir"]
    dir = os.path.abspath(logdir)

    file1 = msg["file1"]
    file2 = msg["file2"]
    file4 = msg["file4"]
    file5 = msg["file5"]
    try:
        client.deleteDataViaDM(file1)
        client.deleteDataViaDM(file2)
        client.deleteDataViaDM(file4)
        client.deleteDataViaDM(file5)
    except client.DataManagerException as e:
        print(e.message)
        logTest("dm_delete","FAIL",logdir,e.message)
        msg["total_tests"]+=1
        msg["failed_tests"]+=1
        cleanup(msg)
        return

    
    #check the files no longer exist
    if os.path.isfile(os.path.join(dir,"testfile1.txt")) is True:
        logTest("dm_move","FAIL",logdir,"Deleted file still exists")
        msg["total_tests"]+=1
        msg["failed_tests"]+=1
        cleanup(msg)
        return


     #check the files no longer exist
    if os.path.isfile(os.path.join(dir,"testfile3.txt")) is True:
        logTest("dm_move","FAIL",logdir,"Deleted file still exists")
        msg["total_tests"]+=1
        msg["failed_tests"]+=1
        cleanup(msg)
        return

     #check the files no longer exist
    if os.path.isfile(os.path.join(dir,"testfile4.txt")) is True:
        logTest("dm_move","FAIL",logdir,"Deleted file still exists")
        msg["total_tests"]+=1
        msg["failed_tests"]+=1
        cleanup(msg)
        return

     #check the files no longer exist
    if os.path.isfile(os.path.join(dir,"testfile5.png")) is True:
        logTest("dm_move","FAIL",logdir,"Deleted file still exists")
        msg["total_tests"]+=1
        msg["failed_tests"]+=1
        cleanup(msg)
        return


    logTest("dm_delete","PASS",logdir)
    msg["total_tests"]+=1
    msg["passed_tests"]+=1

    workflow.send(msg,"dm_tests_complete")

    

#attempts to deregister any endpoints associated with this incident and requests the tests are aborted
def cleanup(msg):
    incident = msg["IncidentID"]
    
    workflow.send(queue="abort_tests",message=msg)
    


def RegisterHandlers():
    workflow.RegisterHandler(handler=dm_tests_init,queue="dm_tests_init")
    workflow.RegisterHandler(handler=dm_tests_complete,queue="dm_tests_complete")
    workflow.RegisterHandler(handler=dm_tests_register,queue="dm_tests_register")
    workflow.RegisterHandler(handler=dm_tests_retreive,queue="dm_tests_retreive")
    workflow.RegisterHandler(handler=dm_tests_copy,queue="dm_tests_copy")
    workflow.RegisterHandler(handler=dm_tests_move,queue="dm_tests_move")
    workflow.RegisterHandler(handler=dm_tests_delete,queue="dm_tests_delete")
    workflow.RegisterHandler(handler=dm_tests_search,queue="dm_tests_search")
    workflow.RegisterHandler(handler=dm_tests_put,queue="dm_tests_put")
    workflow.RegisterHandler(handler=dm_tests_download,queue="dm_tests_download")
