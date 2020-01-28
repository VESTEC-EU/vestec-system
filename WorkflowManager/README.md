# Workflow Manager documentation

## Files
* `workflow.py` -  Contains the machinery of the workflow. Should be imported by anything that wants to use the workflow functionality
* `manager.py` - Run this to run a workflow
* `fire.py` - Contains example handlers for the forest fire workflow
* `MesoNH.py` - Contains example handlers for MesoNH workflows
* `example.py` - Sets off an example forest fire workflow 

## Requirements
* The python module `pika` is required. It can be installed with `pip`
* A RabbitMQ server must be installed. One can be started with docker using '`docker run -p 5672:5672 rabbitmq`'


## How it works
The workflow manager works via RabbitMQ. Every node of the workflow is represented by a AMQP queue whose entries are consumed by a 'handler' callback function. When a message is put into a node's queue, the handler function is called, inspects the message, then carries out some task appropriate for the message. The handler may then (based on the information it has processed) decide to send messages to one or more (or no) queues to trigger other nodes of the workflow. As such we can have a complicated workflow with conditional branching, parallel execution of nodes (assuming we have multiple worker processes) and loops if necessary.

## Writing handlers and constructing your workflow
Handler functions (which take the message as their input) are decorated with `@workflow.handler` and registered with RabbitMQ using `workflow.RegisterHandler(handler,queue)`. Messages are sent with `workflow.send(queue,message)`. The messages _must_ be sent as python dictionaries as these are converted to json when sent through RabbitMQ. 

## Workflow execution
We need to have a process (or group of processes/threads) running that act as consumers for the messages. These are the processes that execute the workflow. To register as a consumer `workflow.execute()` is called. This puts the consumer into an infinite loop waiting for messages. 


## Example Workflow
Consider we have two nodes connected together called A and B, whose workflow is `Start -> A -> B -> End`. An example code to define and execute the workflow is:
```python
import workflow

#define the handlers for A and B
@workflow.handler
def A_handler(message):
    #do something with message
    print("Hello from A")
    #send message to queue associated with B
    workflow.send(message=message,queue="B_queue")

@workflow.handler
def B_handler(message):
    #do something with message
    print("Hello from B")
    #nothing else to do because the workflow is finished

#register these handlers to the queues
workflow.RegisterHandler(handler=A_handler,queue="A_queue")
workflow.RegisterHandler(handler=B_handler,queue="B_queue")


if __name__ == "__main__":
    #send message to A to start workflow
    workflow.send(queue="A_queue",message="some messsge")

    #execute the workflow (this starts up an infinite loop)
    workflow.execute()
```

## The Fire and MesoNH workflows
At present the workflow defined in `MesoNH.py` and `fire.py` (and executed in `example.py`) is very simplified and only represents a skeleton workflow. The handlers only pass on messages to the appropriate parts of the workflow, and do not process anything. The workflow is as shown below:

![workflow](example.png)

In order for the fire simulation to be run it requires three dependencies: terrain data, hotspot data and post-processed output data from MesoNH. In order to obtain the MesoNH output data, we must first collect data from a weather forecast, feed this into MesoNH, then reduce the MesoNH data. The handlers for each of these dependencies send messages to the fire simulation queue to say they have completed their tasks. Each time a message comes into the queue, the fire simulation handler is called and it checks to see if all three dependencies are met. If they are, it runs the simulation, else it does nothing and waits for another message.

## Running the example workflow
The example contained in `example.py` runs the fire workflow (see above). To run this we first need
* A running RabbitMQ server (e.g. use a rabbitmq docker container exposing port 5672)
* `manager.py` to be running (this is the "workflow engine" that listens for messages and executes the handlers)

If we then run `example.py` it will send messages to the terrain, hotspot and weather data handlers to kickstart the workflow. The output from `example.py` should be:
```
$ python example.py 
 [*] Sent message 'Dummy Message' to queue 'fire_terrain'
 [*] Sent message 'Dummy Message' to queue 'fire_hotspot'
 [*] Sent message 'Dummy Message' to queue 'weather_data'
 [*] Closing connection to RabbitMQ server
```

Whilst the output from `manager.py` should be:
```
$ python manager.py 
 [*] 'weather_data_handler' registered to queue 'weather_data'
 [*] 'weather_simulation_handler' registered to queue 'weather_simulation'
 [*] 'weather_results_handler' registered to queue 'weather_results'
 [*] 'fire_terrain_handler' registered to queue 'fire_terrain'
 [*] 'fire_hotspot_handler' registered to queue 'fire_hotspot'
 [*] 'fire_simulation_handler' registered to queue 'fire_simulation'

 [*] Workflow Manager ready to accept messages. To exit press CTRL+C 


--------------------------------------------------------------------------------
In Fire terrain handler
 [*] Sent message '' to queue 'fire_simulation'
--------------------------------------------------------------------------------


--------------------------------------------------------------------------------
In Fire hotspot handler
 [*] Sent message '' to queue 'fire_simulation'
--------------------------------------------------------------------------------


--------------------------------------------------------------------------------
In weather data handler
 [*] Sent message '' to queue 'weather_simulation'
--------------------------------------------------------------------------------


--------------------------------------------------------------------------------
In fire simulation handler
   Terrain data available? -  True
   Hotspot data available? -  True
   Weather data available? -  False
Will do nothing - waiting for data
--------------------------------------------------------------------------------


--------------------------------------------------------------------------------
In fire simulation handler
   Terrain data available? -  True
   Hotspot data available? -  True
   Weather data available? -  False
Will do nothing - waiting for data
--------------------------------------------------------------------------------


--------------------------------------------------------------------------------
In weather simulation handler
 [*] Sent message '' to queue 'weather_results'
--------------------------------------------------------------------------------


--------------------------------------------------------------------------------
In weather results handler
 [*] Sent message '' to queue 'fire_simulation'
--------------------------------------------------------------------------------


--------------------------------------------------------------------------------
In fire simulation handler
   Terrain data available? -  True
   Hotspot data available? -  True
   Weather data available? -  True
Running Fire Simulation
--------------------------------------------------------------------------------

```