# Incident management

The incident management API allows callers to create incidents, track the state of existing incidents (if they have permission to do so) and manage a user's current incidents.

Note that all API calls require a logged in user and will return the 403 status code if either an access token is not provided, or the session that the access token references to is deemed expired.

The user's credentials are passed via the HTTP header, with the key _Authorization_ and value _Bearer <usertoken>_ where <usertoken> is returned by the system when you logged in. For instance, 'Authorization':'Bearer 123' if the token 123 was returned.

## Create incident
This call enables a user to create a new incident and will return the incident unique identifier. Note that incidents are created in a __pending__ state, and need to be explicitly activated by the corresponding API call. Incidents will be associated with the user who created them.

*Address:* /flask/createincident

*HTTP method:* POST

#### Input data
*Input data format:* JSON

Key | Value
------ | -----------
name | Name of the incident
kind | Kind of incident, corresponding to the registered workflow types 
upperLeftLatlong | Lat/Long of upper left corner of area of interest (optional)
lowerRightLatlong | Lat/Long of lower right corner of area of interest (optional)
duration | Duration of the incident (optional)

#### Output data on success
*Output data format:* JSON

Key | Value
------ | -----------
status | 201
msg | Incident successfully created
incidentid | Unique identifier of the incident

#### Output data on failure
*Output data format:* JSON

Failure is defined as the input data (incident name or type) is missing or malformed.

Key | Value
------ | -----------
status | 400
msg | Incident name or type is missing

## Get Incidents
Retrieves a summary list of incidents that the current user (provided as the web-token) has access to based upon some list of filters on the status of the incident.

*Address:* /flask/getincidents

*HTTP method:* GET

#### Input data
*Input data format:* Encoded as part of URI

Key | Value
------ | -----------
pending | String boolean whether to select incidents whose state is pending
active | String boolean whether to select incidents whose state is active
completed | String boolean whether to select incidents whose state is completed
cancelled | String boolean whether to select incidents whose state is cancelled
error | String boolean whether to select incidents whose state is error
archived | String boolean whether to select incidents whose state is archived

In the URI this is encoded as _?pending=true&active=true_ etc. Any missing keys are assumed to be false (e.g. filtered out) and the order does not matter.

#### Output data on success
*Output data format:* JSON

Key | Value
------ | -----------
status | 200
incidents | List of dictionaries, each of which is an incident and sorted by status and incident date

The incident dictionary format is 

Key | Value
------ | -----------
uuid | Incident unique identifier
kind | Incident type kind
name | This incident name
status | Status of the incident (e.g. pending, active, completed etc)
comment | Optional incident comment
creator | User who created the incident
date_started | Date that the incident was started if incident has started
date_completed | Date that the incident was completed if incident has completed *
upper_left_latlong | Lat/long of the upper left corner of the area of interest *
lower_right_latlong | Lat/long of the lower right corner of the area of interest *
duration | Duration of the simulation *
incident_date | Date incident was created

The status is one of PENDING, ACTIVE, COMPLETED, CANCELLED, ERROR, ARCHIVED

Note: A star next to the description means that this is an optional field, and will only be present if such information is recorded against the incident.

## Retrieve Incident
Retrieves detailed information about a specific incident that the current user (provided as the web-token) has access to.

*Address:* /flask/incident/<incident_uuid>

*HTTP method:* GET

#### Input data
N/A - the incident_uuid is used which is provided as part of the URL

#### Output data on success
*Output data format:* JSON

Key | Value
------ | -----------
status | 200
incident | Dictionary which is the incident in question

The incident dictionary format is 

Key | Value
------ | -----------
uuid | Incident unique identifier
kind | Incident type kind
name | This incident name
status | Status of the incident (e.g. pending, active, completed etc)
comment | Optional incident comment
creator | User who created the incident
date_started | Date that the incident was started if incident has started
date_completed | Date that the incident was completed if incident has completed
upper_right_latlong | Lat/long of the upper right corner of the area of interest
lower_left_latlong | Lat/long of the lower left corner of the area of interest
duration | Duration of the simulation
incident_date | Date incident was created
digraph | Digraph of workflow execution status
data_queue_name | The name of the EDI endpoint to use when adding data manually, empty means that the incident does not support this feature
data_sets | A list of data-sets associated with this incident
simulations | A list of simulations associated with this incident

The status is one of PENDING, ACTIVE, COMPLETED, CANCELLED, ERROR, ARCHIVED

Each listed data-set is comprised of the following fields

Key | Value
------ | -----------
uuid | UUID of the data-set
name | Name of this specific data-set
type | The type or kind of data-set (note this is NOT the file-type, but instead the provided type/kind of the data)
comments | Any comments associated with the data-set
date_created | Timestamp when the data-set was created

Each listed simulation is comprised of the following fields

Key | Value
------ | -----------
uuid | UUID of the data-set
jobID | Machine assigned job ID (e.g. from the queue system)
status | Status of the incident (PENDING, QUEUED, RUNNING, COMPLETED, CANCELLED, ERROR)
status_updated | Timestamp when the job status was last updated
status_message | Any message associated with the status (e.g. a failure message in the event of error)
created | Timestamp when the simulation was created
walltime | Execution walltime (either entire walltime if completed, or walltime to date if running)
kind | The kind of simulation (a brief description)
num_nodes | Number of nodes requested
requested_walltime | The requested walltime
machine | Name of the machine running this simulation

#### Output data on failure
*Output data format:* JSON

This is most likely because the user does not have permission to access this specific incident.

Key | Value
------ | -----------
status | 401
msg | Error retrieving incident

## Delete Incident
Deletes and incident and cancels execution of the workflow

*Address:* /flask/incident/<incident_uuid>

*HTTP method:* DELETE

#### Input data
N/A - the incident_uuid is used which is provided as part of the URL

#### Output data on success
*Output data format:* JSON

Key | Value
------ | -----------
status | 200
msg | Incident cancelled

## Archive Incident
Archives an incident, which currently updates the status but in the future will also archive associated data

*Address:* /flask/archiveincident/<incident_uuid>

*HTTP method:* GET

#### Input data
N/A - the incident_uuid is used which is provided as part of the URL

#### Output data on success
*Output data format:* JSON

Key | Value
------ | -----------
status | 200
msg | Incident archived

#### Output data on failure
*Output data format:* JSON

This is most likely because the user does not have permission to archive this specific incident.

Key | Value
------ | -----------
status | 401
msg | Error archiving incident

## Activating an Incident
Activates an incident, calling into the appropriate workflow initialisation stage which will set up things like listeners in the EDI

*Address:* /flask/activateincident/<incident_uuid>

*HTTP method:* GET

#### Input data
N/A - the incident_uuid is used which is provided as part of the URL

#### Output data on success
*Output data format:* JSON

Key | Value
------ | -----------
status | 200
msg | Incident activated

#### Output data on failure
*Output data format:* JSON

This is most likely because the user does not have permission to archive this specific incident.

Key | Value
------ | -----------
status | 401
msg | Error retrieving incident

## Retrieving meta-data for an incident based on matching type
This retrieves the meta-data of incident's data-sets which match a specific type

*Address:* /flask/datasets

*HTTP method:* GET

#### Input data
*Input data format:* URI encoded

The _type_ and _incident_uuid_ are encoded as URI argument parameters, e.g. _?type=Sensors&incident_uuid=B_

#### Output data on success
*Output data format:* JSON

A list of dictionaries is returned, each dictionary representing a unique data-set that meets the search criteria. Dictionaries contain the following keys:

Key | Value
------ | -----------
uuid | UUID of the data-set
name | Name of this specific data-set
type | The type or kind of data-set (note this is NOT the file-type, but instead the provided type/kind of the data)
comments | Any comments associated with the data-set
date_created | Timestamp when the data-set was created

#### Output data on failure
*Output data format:* JSON

This is most likely because the user does not have permission to access this specific data-set

Key | Value
------ | -----------
status | 401
msg | Error can not find matching incident dataset.

## Retrieving meta-data associated with an incident's data-set
Retrieves the meta-data associated with an incident data-set

*Address:* /flask/metadata

*HTTP method:* GET

#### Input data
*Input data format:* URI encoded

The _data_uuid_ and _incident_uuid_ are encoded as URI argument parameters, e.g. _?data_uuid=A&incident_uuid=B_

#### Output data on success
*Output data format:* JSON

Key | Value
------ | -----------
uuid | UUID of the data-set
name | Name of this specific data-set
type | The type or kind of data-set (note this is NOT the file-type, but instead the provided type/kind of the data)
comments | Any comments associated with the data-set
date_created | Timestamp when the data-set was created

#### Output data on failure
*Output data format:* JSON

This is most likely because the user does not have permission to access this specific data-set

Key | Value
------ | -----------
status | 401
msg | Error can not find matching incident dataset.

## Updating meta-data associated with an incident's data-set
Updates the meta-data associated with an incident data-set

*Address:* /flask/metadata

*HTTP method:* POST

#### Input data
*Input data format:* JSON

Key | Value
------ | -----------
data_uuid | UUID of the data-set
incident_uuid | UUID of the incident that the data-set is associated with
type | User provided type/kind of the data-set
comments | Comments associated with the data-set

#### Output data on success
*Output data format:* JSON

Key | Value
------ | -----------
status | 200
msg | Metadata updated

#### Output data on failure
*Output data format:* JSON

This is most likely because the user does not have permission to update the data-set.

Key | Value
------ | -----------
status | 401
msg | Metadata update failed, no incident data-set that you can edit

## Deleting an incident data-set
Deletes the data-set associated with an incident, purging it from the incident, data-manager and possibly the physical copy too

*Address:* /flask/data

*HTTP method:* DELETE

#### Input data
*Input data format:* URI encoded

The _data_uuid_ and _incident_uuid_ are encoded as URI argument parameters, e.g. _?data_uuid=A&incident_uuid=B_

#### Output data on success
*Output data format:* JSON

Key | Value
------ | -----------
status | 200
msg | Data deleted

#### Output data on failure
*Output data format:* JSON

This is most likely because the user does not have permission to delete the data-set.

Key | Value
------ | -----------
status | 401
msg | Data deletion failed, no incident data set that you can edit

## Downloading a data-set
Downloads the data-set, with filename and filetype preserved accordingly to the underlying file representation

*Address:* /flask/data/<data_uuid>

*HTTP method:* GET

#### Input data
N/A - the data_uuid is used which is provided as part of the URI

#### Output data on success
*Output data format:* Binary

Uses the send_file mechanism to send the file to the caller, with filename and filetype provided

#### Output data on failure
*Output data format:* JSON

This is most likely because the user does not have permission to delete the data-set.

Key | Value
------ | -----------
status | 400
msg | Only datasets stored on VESTEC server currently supported

## Refreshing the state of a simulation
Refreshes the state of a simulation, by default all simulation statuses are refreshed around every 15 minutes. By calling this it will update the state of the simulation immediately.

*Address:* /flask/refreshsimulation

*HTTP method:* POST

#### Input data
*Input data format:* JSON

Key | Value
------ | -----------
sim_uuid | The UUID of the simulation to refresh

#### Output data on success
*Output data format:* JSON

(Note, there can be a delay in this call returning as it will actively poll the target machine for updated status which can take a few seconds)

Key | Value
------ | -----------
status | 200
simulation | Dictionary containing the refreshed status of the simulation

The simulation dictionary contains the following fields:

Key | Value
------ | -----------
uuid | UUID of the data-set
jobID | Machine assigned job ID (e.g. from the queue system)
status | Status of the incident (PENDING, QUEUED, RUNNING, COMPLETED, CANCELLED, ERROR)
status_updated | Timestamp when the job status was last updated
status_message | Any message associated with the status (e.g. a failure message in the event of error)
created | Timestamp when the simulation was created
walltime | Execution walltime (either entire walltime if completed, or walltime to date if running)
kind | The kind of simulation (a brief description)
num_nodes | Number of nodes requested
requested_walltime | The requested walltime
machine | Name of the machine running this simulation

## Deleting (cancelling) a simulation
Deletes/cancels a simulation

*Address:* /flask/simulation

*HTTP method:* DELETE

#### Input data
The _sim_uuid_ are encoded as URI argument parameters, e.g. _?sim_uuid=A_

#### Output data on success
*Output data format:* JSON

Key | Value
------ | -----------
status | 200
