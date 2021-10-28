# Simulation Manager API

The Simulation Manager provides functionality to submit and control jobs on the HPC machines.

## CreateSimulation

`createSimulation(incident_id, num_nodes, requested_walltime, kind, executable, queuestate_callbacks={}, directory=None, template_dir=None, comment=None)`

Will create a simulation on a target HPC machine ready for it to be submitted. The arguments are as follows:

* _incident_id_: Unique identifier of the incident
* _num_nodes_: Number of nodes to run the simulation over
* _requested_walltime_: Amount of time requested for the job
* _kind_: Textual description of simulation for logging
* _executable_: Executable that will be run
* _queuestate_callbacks_: (Optional) dictionary of callbacks which will result in specific workflow stages being executed when the job reaches specific stages. These states are COMPLETED, QUEUED, RUNNING, ENDING, HELD.
