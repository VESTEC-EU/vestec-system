# Workflow Developer Overview

Adding support for a specific disaster use-case will likely involve the creation of a new workflow, integration with this into the system, and interaction with other VESTEC services. Whilst the services are called via RESTful API, each provide a client interface which presents a set of functions that other parts of the system can call, packaging the arguments into the format nescesary for the web-service and handling errors via throwing service specific exceptions.

Workflows should be created in the _WorkflowManager/workflows_ directory where it can be seen there are numerous existing example and use-case specific workflows already. Underneath the hood the workflow engine uses AMQP via RabbitMQ, however the specifics of these details are absracted from the developer. This is illustrated below, where messages are pushed into different named AMQP queues and each of these is registered with a specific consumer. The workflow system builds atop of this, adding structure to the message and representing these consumers as Python functions as well as providing a set of API calls to undertake the sending and management of messages.

![AMQP message](https://raw.githubusercontent.com/VESTEC-EU/vestec-system/main/Docs/images/amqp_message.png)

Code for a simple workflow is illustrated below, where two handlers are registered and when a message is sent to the _A_queue_ the _A_handler_ function is activated in a thread which will process the message as appropriate and then send this onto the _B_queue_ stage which will activate the _B_handler_ function. The RegisterHandlers call should be issued by the workflow manager on start to load in the appropriate stages.

```
import workflow

@workflow.handler
def A_handler(message):
  print("Stage A running")
  workflow.send(message=message, queue="B_queue")

@workflow.handler
def B_handler(message):
  print("Stage B running")
  workflow.Complete(message["id"])

def RegisterHandlers():
  workflow.RegisterHandler(handler=A_handler, queue="A_queue")
  workflow.RegisterHandler(handler=B_handler, queue="B_queue")    
```

## Workflow manager API calls
### RegisterHandler

`RegisterHandler(handler, queue)`

Registers a workflow stage handler with the workflow manager, where _handler_ is the decorated Python function that will handle the message and _queue_ the string queue name. Will throw an exception if registration is not possible.

### send
`send(message, queue, src_tag = "", dest_tag = "", providedCaller=None)`

Will enqueues a message to be sent to the specified queue, activating that workflow stage to handle it. It is possible to provide optional tags which will give context to the message and the provided caller which will be logged where the message originated from.

### FlushMessages
`FlushMessages()`

Loops through all enqueued messages and flushes them forcing a send
