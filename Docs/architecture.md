# Architecture overview

The overall view of the VESTEC system is illustrated below, with the middle box representing the system itself. It can be seen that this is comprised of a set of _managers_, each of which accesses the shared database. Workflows are the underlying driver here, with use-cases represented inside the system as separate workflows which the _workflow manager_ marshals and controlls. The other managers can be thought of as providing a set of unified services that workflow stages can call into the undertake specific actions. Each of the managers and interfaces runs as a separate Docker container and provides it's services via webservices using a RESTful API.

![Architecture view](https://raw.githubusercontent.com/VESTEC-EU/vestec-system/main/Docs/architecture_view.png)

## System components 

### Managers

#### Workflow Manager
The workflow manager marhalls and controls the workflows that represent different urgent use-case scenarios. This manager provides a base set of abstractions via API calls and Python decorators that the use-case developer can use to build up their workflow stages and express the consituent logic. 

#### Data Manager

The data manager is responsible for tracking data sets which may be located on the VESTEC system but are more likely held on HPC machines. Through this manager a series of operations, such as moving, deleting, renaming, and fetching are provided which abstracts the low level operations of how these actions are performed and the data transfer mechanism used between source and target.

#### Simulation Manager

Is responsible for managing active simulations that are queued or running on HPC machines. A workflow will call appropriate API calls to submit and manage simulations, with the simulation manager then calling back to workflow stages when simulations reach a specific state (if such details have been provided when the simulation was submitted).

#### Machine Status Manager

Tracks the live status of all HPC machines and is responsible for making decisions around the most appropriate machine to run which workloads upon. 

### Interfaces

The VESTEC system interfaces with the outside world and this is done via the interfaces provided as part of the system. 

#### Machine Interface

Physically connects to the HPC machines and abstracts details of how this connection is undertaken and specifics of the machines such as the batch queue system used. Presenting a common API to higher levels of the VESTEC system, logical operations such as retrieving the state of the queue or cancelling a job are translated to the form required by specific HPC machine(s) and issued to them.

#### External Services

A set of predefined web-services (via RESTful API) for managing incidents, users, and the system. These API calls are documented in more detail under _Client developer_ and can be called from webpages or client GUIs. The VESTEC management web interface calls into these API calls, and they have also been integrated into a variety of technologies including ParaView and CosmoScoutVR for management of incidents via those more front-line targetted technologies to enable fusion of results with control.

#### External Data Interface

Interface that works in both push and pull mode enabling unstructured data to be pulled into the VESTEC system from some source. End points are registered in this interface via it's API and upon the arrival of data the corresponding workflow stage is activated to handle it. This can be used for listening to sensor data, but also enabling client GUIs to post data into the system (e.g. simulation specific parameters) and the flexibility provided here as it is backed by a bespoke workflow that will interpret the arrived data effectively means that this is an infintely flexible API that can be specialised on a use-case by use-case basis. 

## Stack of Functionality 
