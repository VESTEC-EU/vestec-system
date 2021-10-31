# Simulation Manager API

The Simulation Manager provides functionality to submit and control jobs on the HPC machines.

## CreateSimulation

`createSimulation(incident_id, num_nodes, requested_walltime, kind, executable, queuestate_callbacks={}, directory=None, template_dir=None, comment=None)`

Will create a simulation on a target HPC machine ready for it to be submitted. The arguments are as follows:

* _incident_id_: Unique identifier of the incident
* _num_nodes_: Number of nodes to run the simulation over
* _requested_walltime_: Amount of time requested for the job
* _kind_: Textual description of kind of simulation running 
* _executable_: Executable that will be run
* _queuestate_callbacks_: (Optional) dictionary of callbacks which will result in specific workflow stages being executed when the job reaches specific stages. These states are COMPLETED, QUEUED, RUNNING, ENDING, HELD.
* _directory_: The directory to run in
* _template_dir_: Template directory to copy from when setting up the submission environment
* _comment_: Free text comments that are logged
* _number_instances_: (Optional) defaults to 1, the number of instances on separate machines that should be created

Returns a list of unique simulation identifiers, one per instance, that can be used to identify the created simulation(s).

If there is an error during creation this will throw a _SimulationManagerException_ with message containing the source of the error

## submitSimulation

`submitSimulation(sim_id)`

Submits the simulation on the HPC machine

* _sim_id_: Simulation identifier returned from the creation API call

If there is an error during submission this will throw a _SimulationManagerException_ with message containing the source of the error

## refreshSimilation

`refreshSimilation(sim_id)`

Refreshes internal system state of a specific simulation on an HPC machine. Simulation states are automatically refreshed periodically (typically every 60 seconds although this is configurable) but this will force an immediate refresh.

* _sim_id_: Simulation identifier returned from the creation API call

If there is an error this will throw a _SimulationManagerException_ with message containing the source of the error

## cancelSimulation

`cancelSimulation(sim_id)`

Cancels a simulation that has been submitted or created.

* _sim_id_: Simulation identifier returned from the creation API call

If there is an error this will throw a _SimulationManagerException_ with message containing the source of the error

## getSimulationInfo

`getSimulationInfo(sim_id)`

Retrieves information about a specific simulation based on it's state. Note that this will not explicitly fetch new information, rather it will return information that is cached based on the last state update (either automatic or manual via the _refresh_state_ call).

* _sim_id_: Simulation identifier returned from the creation API call

If there is an error this will throw a _SimulationManagerException_ with message containing the source of the error
