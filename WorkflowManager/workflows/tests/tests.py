from manager import workflow
from . import test_workflows
from . import test_edi
from . import test_dm
from . import test_sm
from .utils import logfile



from DataManager.client import getLocalFilePathPrepend

import os

testsdict = {
    "workflow":"workflow_tests_init",
    "EDI": "edi_tests_init",
    "DM": "dm_tests_init",
    "SM": "sm_tests_init"
}

default_tests = ["workflow", "EDI","DM","SM"]


@workflow.handler
def init_tests(msg):
    incident = msg["IncidentID"]

    logdir = os.path.join(getLocalFilePathPrepend(),"test_results",incident)

    os.makedirs(logdir)

    print("logdir= %s"%logdir)

    if "testlist" in msg:
        testlist = msg["testlist"]
    else:
        workflow.logger.warn("No testlist specified, running all tests")
        testlist = default_tests

    newlist=[]
    for item in testlist:
        if item in testsdict:
            newlist.append(item)
        else:
            workflow.logger.warn("Unknown test type '%s'. Skipping"%item)
    msg["testlist"] = newlist

    print("Scheduling tests: ",testlist)
    
    with logfile(logdir) as f:
        f.write("Scheduling tests: %s\n"%testlist)

   
        

    msg["logdir"]=logdir
    msg["total_tests"]=0
    msg["passed_tests"]=0
    msg["failed_tests"]=0

    workflow.send(queue="run_tests",message=msg)


@workflow.handler
def run_tests(msg):
    incident = msg["IncidentID"]

    tests_run = workflow.Persist.Get(incident)

    n = len(tests_run)

    if n != len(msg["testlist"]):
        next_test = msg["testlist"][n]
        queue = testsdict[next_test]
        workflow.Persist.Put(incident, {"scheduled":next_test})
        print("Running tests for '%s'"%next_test)
        workflow.send(queue=queue,message=msg)
    else:
        workflow.send(queue="complete_tests",message=msg)



@workflow.handler
def abort_tests(msg):
    incident = msg["IncidentID"]
    workflow.Cancel(incident)


@workflow.handler
def complete_tests(msg):
    incident = msg["IncidentID"]
    logdir = msg["logdir"]
    print("Tests Completed")
    print("  Passed = %d"%msg["passed_tests"])
    print("  Failed = %d"%msg["failed_tests"])
    print("  Total  = %d"%msg["total_tests"])
    with logfile(logdir) as f:
        f.write("Tests Completed\n")
        f.write("  Passed = %d\n"%msg["passed_tests"])
        f.write("  Failed = %d\n"%msg["failed_tests"])
        f.write("  Total  = %d\n"%msg["total_tests"])
    
    workflow.Complete(incident)


def summarise_tests(msg):
    pass


def RegisterHandlers():
    workflow.RegisterHandler(init_tests,"init_tests")
    workflow.RegisterHandler(abort_tests,"abort_tests")
    workflow.RegisterHandler(complete_tests,"complete_tests")
    workflow.RegisterHandler(run_tests,"run_tests")
    test_workflows.RegisterHandlers()
    test_edi.RegisterHandlers()
    test_dm.RegisterHandlers()
    test_sm.RegisterHandlers()

