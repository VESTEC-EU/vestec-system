import manager.workflow as workflow
import ExternalDataInterface.client as client
import requests
import time
import os
import json

from .utils import logfile, logTest


@workflow.handler
def edi_tests_init(msg):
    incident = msg["IncidentID"]
    logdir = msg["logdir"]

    with logfile(logdir) as f:
        f.write("External Data Interface tests\n")
    
    workflow.send(msg,"edi_tests_register_push")


@workflow.handler
def edi_tests_complete(msg):
    incident = msg["IncidentID"]
    logdir = msg["logdir"]

    workflow.send(msg,"run_tests")

#registers a push endpoint, and pushes data to it. Once this is done, sends a message to the endpoint's handler to ask it if the data has come through
@workflow.handler
def edi_tests_register_push(msg):
    incident = msg["IncidentID"]
    logdir = msg["logdir"]

    
    endpoint =incident+"_test"

    #register the endpoint, catch any exceptions and treat these as fails
    try:
        client.registerEndpoint(incident,endpoint,"edi_tests_push_handler")
    except client.ExternalDataInterfaceException as e:
        msg["total_tests"]+=1
        msg["failed_tests"]+=1
        cleanup(msg)
        logTest("EDI_register_push","FAIL",logdir,"EDI raised exception: %s"%e.message)
        return
    except Exception as e:
        msg["total_tests"]+=1
        msg["failed_tests"]+=1
        cleanup(msg)
        logTest("EDI_register_push","FAIL",logdir,"Unknown exception: %s"%e.message)
        return
    msg["total_tests"]+=1
    msg["passed_tests"]+=1
    logTest("EDI_register_push","PASS", logdir)

    url = os.path.join(client._get_EDI_URL(),endpoint)
    data = json.dumps({"incident": incident}).encode("ascii")
    
    #push some made up data to the newly created endpoint
    try:
        r = requests.post(url,data=data)
    except Exception as e:
        msg["total_tests"]+=1
        msg["failed_tests"]+=1
        logTest("EDI_send_push","FAIL",logdir,"Requests module threw exception: %s"%e)
        cleanup(msg)
        return
    if r.status_code != 200:
        msg["total_tests"]+=1
        msg["failed_tests"]+=1
        logTest("EDI_send_push","FAIL",logdir,"Request returned code %d, response: %s"%(r.status_code,r.text))
        cleanup(msg)
        return

    msg["total_tests"]+=1
    msg["passed_tests"]+=1
    logTest("EDI_send_push","PASS",logdir)
    
    #sleep a bit to make sure the pushed data's workflow message gas been sent by the EDI
    time.sleep(1)
    
    #send message to the push handler. If all went well, this message would have come in after the pushed data has
    workflow.send(queue="edi_tests_push_handler",message=msg)
    


#Receives messages from the EDI (pushed data), and from the edi_tests_register_push handler
#The pushed data should come through first... it not, something has gone wrong and the test has failed
#handler must be atomic as the order that messages come in is important
@workflow.atomic
@workflow.handler
def edi_tests_push_handler(msg):
    incident = msg["IncidentID"]
    
    #see if this handler has been called before and get any persisted data from the previous calls
    past = workflow.Persist.Get(incident)
    
    #if ths hasn't been called before, message should be from the EDI
    #if so, persist the message payload
    if len(past) == 0 and msg["originator"] == "External Data Interface":
        data = msg["data"]["payload"]
        workflow.Persist.Put(incident,{"data": data})

    #if this has been called before, and the new message's originator is the previous workflow stage:
    elif len(past) == 1 and msg["originator"] == "edi_tests_register_push":
        data = past[0]["data"]
        testdata = json.dumps({"incident": incident})
        logdir = msg["logdir"]
        
        #see if the data pushed to this stage previously matches what it should be
        if data == testdata:
            msg["total_tests"]+=1
            msg["passed_tests"]+=1
            logTest("EDI_receive_push","PASS",logdir)
        else:
            msg["total_tests"]+=1
            msg["failed_tests"]+=1
            logTest("EDI_receive_push","FAIL",logdir,"Recieved data does not match what was sent")
            cleanup(msg)
        
        workflow.send(queue="edi_tests_deregister_push",message=msg)
    #something has gone wrong, test failed
    else:
        logdir = msg["logdir"]
        msg["total_tests"]+=1
        msg["failed_tests"]+=1
        logTest("EDI_receive_push","FAIL",logdir,"Pushed data not received")
        cleanup(msg)
        return


#deregister the push handler        
@workflow.handler
def edi_tests_deregister_push(msg):
    incident = msg["IncidentID"]
    logdir = msg["logdir"]

    endpoint = "%s_test"%incident

    try:
        client.removeEndpoint(incident,endpoint,"edi_tests_push_handler")
    except client.ExternalDataInterfaceException as e:
        msg["total_tests"]+=1
        msg["failed_tests"]+=1
        logTest("EDI_deregister_push","FAIL",logdir,"EDI raised exception: %s"%e.message)
        cleanup(msg)
        return
    
    # ensure it is de-registered by trying to push data to it again
    url = os.path.join(client._get_EDI_URL(),endpoint)
    data = json.dumps({"incident": incident}).encode("ascii")
    
    r = requests.post(url,data=data)

    if r.status_code != 404:
        msg["total_tests"]+=1
        msg["failed_tests"]+=1
        logTest("EDI_deregister_push","FAIL",logdir,"EDI accepted deregistered endpoint")
        cleanup(msg)
        return

    msg["total_tests"]+=1
    msg["passed_tests"]+=1
    logTest("EDI_deregister_push","PASS",logdir)

    workflow.send(queue="edi_tests_register_pull",message=msg)


#register a pull endpoint
@workflow.handler
def edi_tests_register_pull(msg):
    incident = msg["IncidentID"]
    logdir = msg["logdir"]

    endpoint = "https://www.vestec-project.eu"

    try:
        client.registerEndpoint(incident,endpoint,"edi_tests_pull_handler",pollperiod=3)
    except client.ExternalDataInterfaceException as e:
        msg["total_tests"]+=1
        msg["failed_tests"]+=1
        cleanup(msg)
        logTest("EDI_register_pull","FAIL",logdir,"EDI raised exception: %s"%e.message)
        return
    msg["total_tests"]+=1
    msg["passed_tests"]+=1
    logTest("EDI_register_pull","PASS",logdir)
    
    time.sleep(6)

    workflow.send(queue="edi_tests_pull_handler",message=msg)

#receies messages from the EDI for the pull endpoint, and from the register handler
@workflow.atomic
@workflow.handler
def edi_tests_pull_handler(msg):
    incident = msg["IncidentID"]

    past = workflow.Persist.Get(incident)
    
    #First message should be from the EDI. If so, record its contents
    if len(past) == 0 and msg["originator"] == "External Data Interface":
        #print(json.dumps(msg,indent=2))
        data = msg["data"]["source"]
        workflow.Persist.Put(incident,{"data": data})

    #a subsequent message should be from the pull register handler
    elif len(past) >= 1 and msg["originator"] == "edi_tests_register_pull":
        data = past[0]["data"]
        testdata = "https://www.vestec-project.eu"
        logdir = msg["logdir"]
        
        #check that the persisted data is what it should be
        if data == testdata:
            msg["total_tests"]+=1
            msg["passed_tests"]+=1
            logTest("EDI_receive_pull","PASS",logdir)
        else:
            msg["total_tests"]+=1
            msg["failed_tests"]+=1
            logTest("EDI_receive_pull","FAIL",logdir,"Recieved endpoint does not match what was requested")
            cleanup(msg)
        
        workflow.send(queue="edi_tests_deregister_pull",message=msg)
    #something has gone wrong. test failed
    else:
        logdir = msg["logdir"]
        msg["total_tests"]+=1
        msg["failed_tests"]+=1
        logTest("EDI_receive_pull","FAIL",logdir,"Pushed data not received")
        cleanup(msg)
        return


#deregister pull handler
@workflow.handler
def edi_tests_deregister_pull(msg):
    incident = msg["IncidentID"]
    logdir = msg["logdir"]

    endpoint = "https://www.vestec-project.eu"

    try:
        client.removeEndpoint(incident,endpoint,"edi_tests_pull_handler",pollperiod=3)
    except client.ExternalDataInterfaceException as e:
        msg["total_tests"]+=1
        msg["failed_tests"]+=1
        logTest("EDI_deregister_pull","FAIL",logdir,"EDI raised exception: %s"%e.message)
        cleanup(msg)
        return

   
    msg["total_tests"]+=1
    msg["passed_tests"]+=1
    logTest("EDI_deregister_pull","PASS",logdir)

    workflow.send(queue="edi_tests_complete",message=msg)





#attempts to deregister any endpoints associated with this incident and requests the tests are aborted
def cleanup(msg):
    incident = msg["IncidentID"]
    try:
        endpoints = client.getAllEDIEndpoints()
    except:
        print("Warning: unable to clean up EDI endpoints")
        return
    
    for EDI_endpoint in endpoints:
        if incident in EDI_endpoint["endpoint"]:
            endpoint = EDI_endpoint["endpoint"]
            queuename = EDI_endpoint["queuename"]
            if "pollperiod" in EDI_endpoint:
                pollperiod = EDI_endpoint["pollperiod"]
            else:
                pollperiod=None

            try:
                client.removeEndpoint(incident,endpoint,queuename,pollperiod)
                print("Deregistered endpoint %s"%endpoint)
            except:
                print("Unable to deregister endpoint %s"%endpoint) 
                pass
    
    workflow.send(queue="abort_tests",message=msg)
    

# put bin data

#download

# delete



def RegisterHandlers():
    workflow.RegisterHandler(handler=edi_tests_init,queue="edi_tests_init")
    workflow.RegisterHandler(handler=edi_tests_register_push,queue="edi_tests_register_push")
    workflow.RegisterHandler(handler=edi_tests_complete,queue="edi_tests_complete")
    workflow.RegisterHandler(handler=edi_tests_push_handler,queue="edi_tests_push_handler")
    workflow.RegisterHandler(handler=edi_tests_deregister_push,queue="edi_tests_deregister_push")
    workflow.RegisterHandler(handler=edi_tests_register_pull,queue="edi_tests_register_pull")
    workflow.RegisterHandler(handler=edi_tests_pull_handler,queue="edi_tests_pull_handler")
    workflow.RegisterHandler(handler=edi_tests_deregister_pull,queue="edi_tests_deregister_pull")