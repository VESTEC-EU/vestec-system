# Administration

The user's credentials are passed via the HTTP header, with the key _Authorization_ and value _Bearer <usertoken>_ where <usertoken> is returned by the system when you logged in. For instance, 'Authorization':'Bearer 123' if the token 123 was returned.

## Show Logs
This call retrieves all logs that have been stored by the VESTEC system. Note that currently it retrieves absolutely everything, with any filtering done by the caller although in the future this will probably be extended to add filtering on the server side too.  ***Requires a logged in user with administrator rights***

*Address:* /flask/logs

*HTTP method:* GET

#### Input data
HTTP header should contain access token

#### Output data on success
*Output data format:* JSON

The call returns a list of dictionary entries, each item in the dictionary is one logged information item.

Key | Value
------ | -----------
timestamp | Timestamp that item was logged
originator | Originating part of the VESTEC system
user | User who drove this action to be logged
type | Type of logged activity (from a number of predefined types)
comment | Free text comment around the logged activity

## Get system health
This call returns the health of the VESTEC system components ***Requires a logged in user with administrator rights***

*Address:* /flask/health

*HTTP method:* GET

#### Input data
HTTP header should contain access token

#### Output data on success
*Output data format:* JSON

The call returns a list of dictionary entries, each item in the dictionary is the health of one component.

Key | Value
------ | -----------
name | Name of component
status | Boolean indicating whether component is online or not

Currently the health reporting is fairly simple, whether a system component reports itself as healthy within the VESTEC system, but moving forwards this might be extended to provide addition diagnostic functionality.

## Get workflow information
This call returns all the workflows that have been registered with the VESTEC system. Note that this is separate from the workflows that are actually running, these are ones that have been manually registered by administrators. ***Requires a logged in user with administrator rights***

*Address:* /flask/workflowinfo

*HTTP method:* GET

#### Input data
HTTP header should contain access token

#### Output data on success
*Output data format:* JSON

The call returns a list of dictionary entries, each item in the dictionary is a registered workflow.

Key | Value
------ | -----------
kind | Incident kind
queuename | Name of incident initialisation queue name
dataqueuename | Name of the workflow queue that will receive data from the EDI

## Register workflow
This call registers a workflow such that users can then be added to this so that they can create incidents. ***Requires a logged in user with administrator rights***

*Address:* /flask/addworkflow

*HTTP method:* POST

#### Input data
*Input data format:* JSON

Key | Value
------ | -----------
kind | The incident kind
queuename | Name of incident initialisation queue name
dataqueuename | Name of the workflow queue that will receive data from the EDI

#### Output data on success
*Output data format:* JSON

The call returns status code 200 with a message of _Workflow added_ in the _msg_ key field. 

## Delete workflow
This call deletes a workflow that has been previously registered. ***Requires a logged in user with administrator rights***

*Address:* /flask/deleteworkflow

*HTTP method:* POST

#### Input data
*Input data format:* JSON

Key | Value
------ | -----------
kind | The incident kind

#### Output data on success
*Output data format:* JSON

The call returns status code 200 with a message of _Workflow deleted in the _msg_ key field. 

## Get all users
This call returns all the users that have registered with the VESTEC system. ***Requires a logged in user with administrator rights***

*Address:* /flask/getallusers

*HTTP method:* GET

#### Input data
HTTP header should contain access token

#### Output data on success
*Output data format:* JSON

The call returns a list of dictionary entries, each item in the dictionary is a registered user.

Key | Value
------ | -----------
username | Username
name | User's name
email | User's email address
access_rights | User's privilege (0 is user, 1 is administrator)
enabled | Boolean whether user is enabled or not
workflows | Array of registered workflows that the user has access to

## Get user
This call returns information about a specific user based on their username. ***Requires a logged in user with administrator rights***

*Address:* /flask/getuser

*HTTP method:* POST

#### Input data
*Input data format:* JSON

Key | Value
------ | -----------
username | The username

#### Output data on success
*Output data format:* JSON

The call returns a list of dictionary entries, each item in the dictionary is a registered user who matches the username. As these are unique then there should only ever be one entry here.

Key | Value
------ | -----------
username | Username
name | User's name
email | User's email address
access_rights | User's privilege (0 is user, 1 is administrator)
enabled | Boolean whether user is enabled or not
workflows | Array of registered workflows that the user has access to

## Edit user
This call enables the details of a user to be edited. ***Requires a logged in user with administrator rights***

*Address:* /flask/edituser

*HTTP method:* POST

#### Input data
*Input data format:* JSON

Key | Value
------ | -----------
username | Username
name | User's name
email | User's email address
access_rights | User's privilege (_user_, or _administrator_)
enabled | Boolean whether user is enabled or not

The call is keyed on the username, so this is the unique identifier used to look up the record.

#### Output data on success
*Output data format:* JSON

The call returns status code 200 and a message of _User edited_ in the _msg_ field if successful.

## Delete user
This call enables the details of a user to be edited. ***Requires a logged in user with administrator rights***

*Address:* /flask/deleteuser

*HTTP method:* POST

#### Input data
*Input data format:* JSON

Key | Value
------ | -----------
username | Username

The call is keyed on the username, so this is the unique identifier used to look up the record.

#### Output data on success
*Output data format:* JSON

The call returns status code 200 and a message of _User edited_ in the _msg_ field if successful. Otherwise status code of 401 and _User deletion failed_

## Change user password
Changes the password for any user ***Requires a logged in user with administrator rights***

*Address:* /flask/changepassword

*HTTP method:* POST

#### Input data
*Input data format:* JSON

Key | Value
------ | -----------
username | Username
password | New password to set

The call is keyed on the username, so this is the unique identifier used to look up the record.

#### Output data on success
*Output data format:* JSON

The call returns status code 200 and a message of _Password changed_ in the _msg_ field if successful. Otherwise status code of 400 and _Can not change password_

## Add user to workflow
This call enables the details of a user to be edited. ***Requires a logged in user with administrator rights***

*Address:* /flask/addusertoworkflow

*HTTP method:* POST

#### Input data
*Input data format:* JSON

Key | Value
------ | -----------
username | Username
workflow | Workflow to add

The call is keyed on the username, so this is the unique identifier used to look up the record.

#### Output data on success
*Output data format:* JSON

The call returns status code 200 and a message of _Workflow added_ in the _msg_ field if successful.

## Remove user from workflow
This call enables the details of a user to be edited. ***Requires a logged in user with administrator rights***

*Address:* /flask/removeuserfromworkflow

*HTTP method:* POST

#### Input data
*Input data format:* JSON

Key | Value
------ | -----------
username | Username
workflow | Workflow to remove from user's permissions

The call is keyed on the username, so this is the unique identifier used to look up the record.

#### Output data on success
*Output data format:* JSON

The call returns status code 200 and a message of _Workflow removed in the _msg_ field if successful.

## Get EDI handlers 
This call returns all the registered handlers with the EDI ***Requires a logged in user with administrator rights***

*Address:* /flask/getediinfo

*HTTP method:* GET

#### Input data
HTTP header should contain access token

#### Output data on success
*Output data format:* JSON

The call returns a list of dictionary entries, each item in the dictionary is an EDI handler.

Key | Value
------ | -----------
queuename | Name of workflow queue to put data/meta-data packet into upon arrival
endpoint | Name of URI endpoint that this handler relates to (e.g. what we are polling on or waiting for data on)
incidentid | Associated incident UUID
pollperiod | The period in seconds that polling for new data is carried out, or _null_ if it is in push mode

## Delete EDI handler
This call deletes a specific handler on the EDI ***Requires a logged in user with administrator rights***

*Address:* /flask/deleteedihandler

*HTTP method:* POST

#### Input data
*Input data format:* JSON

Key | Value
------ | -----------
queuename | Name of workflow queue to put data/meta-data packet into upon arrival
endpoint | Name of URI endpoint that this handler relates to (e.g. what we are polling on or waiting for data on)
incidentid | Associated incident UUID
pollperiod | The period in seconds that polling for new data is carried out, omitted if in push mode

#### Output data on success
*Output data format:* JSON

The call returns a list of dictionary entries, each item in the dictionary is an EDI handler.

Key | Value
------ | -----------
queuename | Name of workflow queue to put data/meta-data packet into upon arrival
endpoint | Name of URI endpoint that this handler relates to (e.g. what we are polling on or waiting for data on)
incidentid | Associated incident UUID
pollperiod | The period in seconds that polling for new data is carried out, or _null_ if it is in push mode

#### Output data on success
*Output data format:* JSON

Key | Value
------ | -----------
status | 200
msg | Handler removed

#### Output data on failure
*Output data format:* JSON

This is because a matching handler does not exist

Key | Value
------ | -----------
status | 400
msg | No existing handler registered

## Get statuses of connected HPC machines
This call returns the status of all connected HPC machines ***Requires a logged in user with administrator rights***

*Address:* /flask/getmachinestatuses

*HTTP method:* GET

#### Input data
HTTP header should contain access token

#### Output data on success
*Output data format:* JSON

The call returns a list of dictionary entries, each item in the dictionary is a machine.

Key | Value
------ | -----------
uuid | Machine UUID
name | Machine name
host_name | Hostname of the machine
scheduler | Scheduler that the HPC machine uses
connection_type | Type of connection (e.g. fabric SSH or OpenSSH)
nodes | Number of nodes that the machine contains
cores_per_node | Number of cores per node in the machine
enabled | Whether the machine is enabled or not
test_mode | Whether the machine is in test mode (use dummy interface) or not
status | Status of the machine
status_last_checked | Timestamp when the machine status was last updated

## Add machine
Adds a new machine to the VESTEC system ***Requires a logged in user with administrator rights***

*Address:* /flask/addmachine

*HTTP method:* POST

#### Input data
*Input data format:* JSON

Key | Value
------ | -----------
machine_name | Name of the machine
host_name | Hostname that one connects to for the machine
scheduler | Scheduler type on the machine (e.g. PBS/Slurm)
connection_type | Mechanism by which one connects to the machine (e.g. fabric SSH or OpenSSH)
num_nodes | Number of nodes in the machine
cores_per_node | Cores per node in the machine
base_work_dir | Base working directory, will CD into this automatically upon connection

#### Output data on success
*Output data format:* JSON

The call returns status code 200 if successful.

## Enable machine
Enables a machine for connection by the VESTEC system ***Requires a logged in user with administrator rights***

*Address:* /flask/enablemachine/<machine_id>

*HTTP method:* POST

#### Input data
Machine ID is provided as part of the URI

#### Output data on success
*Output data format:* JSON

The call returns status code 200 if successful.

## Disable machine
Disables a machine for connection by the VESTEC system ***Requires a logged in user with administrator rights***

*Address:* /flask/disablemachine/<machine_id>

*HTTP method:* POST

#### Input data
Machine ID is provided as part of the URI

#### Output data on success
*Output data format:* JSON

The call returns status code 200 if successful.

## Enable test-mode for machine
Enables test-mode for a specific machine, this will block connections to the actual physical machine and instead use the dummy connection mechanism for all communications. This is done at the lowest level (in the machine interface) so it should enable exercising of all other parts of the VESTEC system ***Requires a logged in user with administrator rights***

*Address:* /flask/enabletestmodemachine/<machine_id>

*HTTP method:* POST

#### Input data
Machine ID is provided as part of the URI

#### Output data on success
*Output data format:* JSON

The call returns status code 200 if successful.

## Disable test-mode for machine
Disables test-mode for a specific machine, connecting directly to the physical machine rather than the dummy interface ***Requires a logged in user with administrator rights***

*Address:* /flask/disabletestmodemachine/<machine_id>

*HTTP method:* POST

#### Input data
Machine ID is provided as part of the URI

#### Output data on success
*Output data format:* JSON

The call returns status code 200 if successful.
