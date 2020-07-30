# Workflow Manager documentation

## Files
* `manager/`
   * `workflow.py` -  Contains the machinery of the workflow. Should be imported by anything that wants to use the workflow functionality
   * `lock.py` - Contains code around making specific handlers atomic. This is automatically imported by workflow.py
   * `persist.py` - Contains code for handlers to persist data. This is automatically imported by workflow.py
* `scripts/`
   * `graph.py` - Given an IncidentID, this will create an image visualising the workflow graph
   * `killIncidents.py` - kills all active incidents

* `run.py` - This executes the workflow manager
* `workflows/`
   * Contains workflows we have implemented so far
* `Dockerfile` - The dockerfile for the workflow manager
* `requirements.txt` - Python requirements
* `hotspots/`
   * This directory is for temporary data when the wildfire workflow is running. This shoud be removed at a later date


## Requirements
* The python module `pika` is required. It can be installed with `pip`. `requirements.txt` contains the full list of python dependencies.
* A RabbitMQ server must be installed. One can be started with docker using '`docker run -p 5672:5672 rabbitmq`'


## How it works
The workflow manager works via RabbitMQ. Every node of the workflow is represented by a AMQP queue whose entries are consumed by a 'handler' callback function. When a message is put into a node's queue, the handler function is called, inspects the message, then carries out some task appropriate for the message. The handler may then (based on the information it has processed) decide to send messages to one or more (or no) queues to trigger other nodes of the workflow. As such we can have a complicated workflow with conditional branching, parallel execution of nodes (assuming we have multiple worker processes) and loops if necessary. This is a push-based approach, where the workflow reacts to messages being pushed into it. 

## Writing handlers and constructing your workflow
Handler functions (which take the message as their input) are decorated with `@workflow.handler` and registered with RabbitMQ using `workflow.RegisterHandler(handler,queue)`. 

Messages are enqueued to be sent with `workflow.send(queue,message)`. The messages _must_ be sent as python dictionaries as these are converted to json when sent through RabbitMQ. The message _must_ contain a key `IncidentID` which is the UUID of the incident. This is to identify which incident the message belongs to so it may be approproately processed. Not including this key will throw and error when invoking `workflow.send`. As a handler exits, the enqueued messages are automatially sent. If sending a message from outside a handler (e.g. to start a workflow) use `workflow.FlushMessages()` to send the message(s).

Handlers are by default stateless, as the only information they have is that contained in the message that triggered them. Sometimes we need a handler to be able to persist some data so it can appropriately handle a new message based on something it has done previously. To this end the `workflow.Persist.Put(IncidentID,dict)` and `workflow.Persist.Get(IncidentID)` functions can be used. The first puts user-specified data in the form of a python dictionary into a database, labelled with the `IncidentID` and the name of the handler. The `Get` function returns the dictionarys from the previous calls to `Put` from that handler for the current incident. _This data is stored in json format, so any perisisted data must be jsonifyable._

To run a workflow, an incident (a specific incidence of a workflow) must first be declared, using the `workflow.CreateIncident(name,kind,incident_date)` function, where `name` is a name for the incident, `kind` is the kind of incident, and `incident_date` is the date the incident started at (defaults to `datetime.datetime.now()`). If an incident isn't declared (or an invalid IncidentID is passed to `workflow.send`) then an error will be thrown.

When a incident is finished, `workflow.Complete(IncidentID)` can be called to signal to the workflow engine that this workflow is finished. This sends a message to a special internal cleanup handler that marks the workflow as completed and removes temporary logs etc. There is a similar `workflow.Cancel(IncidentID)` function that is similar to complete but logs the workflow as cancelled. _*If you call these from outside of a handler you will need to call `workflow.FlushMessages` to ensure the cleanup message is sent!*_

## Workflow execution
We need to have a process running that act a consumer for the messages. This is the process that collects messages from the RabbitMQ server and handles them, thereby executing the workflow. To register as a consumer, `workflow.execute()` is called. This puts the consumer into an infinite loop waiting for messages. `manager.py` is the default consumer.

### Parallel workflow execution
It is possible to run several consumer processes. The messages are distributed between the different consumers and so they can be processed concurrently. To do this, simply run multiple incidences of `manager.py`. In some cases we may wish to ensure that only a single incidence of a handler (for a given incident) is run at one time to prevent race conditions. To do this we can decorate the handler with the `atomic` decorator:

```python
@workflow.atomic
@workflow.handler
def atomic_handler(msg):
    ...
```
This checks to see if the handler can be run. If not, the message is re-queued to rabbitMQ and will be scheduled to be processed again.

<!-- Or if we only wish to protect a certain part of the handler's execution, we can use the `GetLock` and `ReleaseLock` functions within the function:

```python
    label = "some label for this lock so it can be identified"
    workflow.GetLock(label,IncidentID)
    #Some code that can only be executed by one consumer at a time
    workflow.ReleaseLock(label,IncidentID)
```

If one consumer is executing code inside this region, another consumer will wait until the lock has been released before executing its code. -->

## Example Workflow
Consider we have two nodes connected together called A and B, whose workflow is `Start -> A -> B -> End`. An example code to define and execute the workflow is:
```python
from manager import workflow

#define the handlers for A and B
@workflow.handler
def A_handler(message):
    #do something with message
    print("Hello from A")
    #enqueue message to queue associated with B. 
    #This is automatically sent as this handler exits
    workflow.send(message=message,queue="B_queue")

@workflow.handler
def B_handler(message):
    #do something with message
    print("Hello from B")
    
    #Tell the workflow system that this incident is finished
    workflow.Complete(message["IncidentID"])
    
    
if __name__ == "__main__":
    #Open connection to RabbitMQ
    workflow.OpenConnection()

    #register these handlers to the queues
    workflow.RegisterHandler(handler=A_handler,queue="A_queue")
    workflow.RegisterHandler(handler=B_handler,queue="B_queue")

    #create an incident
    IncidentID = workflow.CreateIncident(name="some name",kind="DUMMY_INCIDENT")
    
    #create a dictionary for the message and include the IncidentID
    message={ "IncidentID" : IncidentID}

    #enqueue message to A to start workflow
    workflow.send(queue="A_queue",message=message)

    #send the enqueued message
    workflow.FlushMessages()

    #execute the workflow (this starts up an infinite loop)
    workflow.execute()
```

