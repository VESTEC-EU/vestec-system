import manager.workflow as workflow
import os

from .utils import logfile, logTest

@workflow.handler
def workflow_tests_init(msg):
    incident = msg["IncidentID"]
    logdir = msg["logdir"]

    with logfile(logdir) as f:
        f.write("Workflow tests\n")
    
    workflow.send(msg,"workflow_tests_persist")


@workflow.handler
def workflow_tests_complete(msg):
    incident = msg["IncidentID"]
    logdir = msg["logdir"]

   

    workflow.send(msg,"complete_tests")


#calls itself repetedly until it has been called 10 times. Calculates the sum of the first 10 Fibonacci numbers
@workflow.handler
def workflow_tests_persist(msg):
    incident = msg["IncidentID"]
    logdir = msg["logdir"]

    previous = workflow.Persist.Get(incident)
    
    if len(previous) < 10:
        if len(previous) < 2:
            N=1
        else:
            N = previous[-1]["N"] + previous[-2]["N"]

        workflow.Persist.Put(incident,{"N":N})
        #print(N)

        workflow.send(msg,"workflow_tests_persist")
    else:
        S=0
        for item in previous:
            S+= item["N"]

        if S != (1+1+2+3+5+8+13+21+34+55):
            status = "FAIL"
            msg["failed_tests"]+=1
            message = "Result %d not equal to reference value %d"%(S,1+1+2+3+5+8+13+21+34+55)
        else:
            status = "PASS"
            msg["passed_tests"]+=1
            message=None
        msg["total_tests"]+=1

        logTest("workflow_tests_persist",status,logdir)

        workflow.send(msg,"run_tests")




def RegisterHandlers():
    workflow.RegisterHandler(workflow_tests_init,"workflow_tests_init")
    workflow.RegisterHandler(workflow_tests_persist,"workflow_tests_persist")
    workflow.RegisterHandler(workflow_tests_complete,"workflow_tests_complete")