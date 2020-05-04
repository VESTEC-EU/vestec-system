# Data Manager

This component keeps track of all the data being processed by the VESTEC system and associated HPC machines. The component is also responsible for moving data between machines. Each file is assicated with an identifier UUID. 

## How to run it

There are two components which must be run. These are `manager.py` which runs the RESTful interface, and `DMAsync.py` which is the backend for the asynchronous component. This also requires a RabbitMQ backend working (e.g. `docker run -p 5672:5672 rabbitmq`)
)


## API

The Data Manager consists of a RESTful interface with the following URIs:

- `/DM/info/[uuid]` (method = `GET`):
  Return information on the data object with UUID, id. This information is returned in json format. If no UUID is provided, the Data Manager returns information on all the data objects.

- `/DM/register` (method = `PUT`):
  Registers a file with the Data Manager. The request must contain the following information:
  - `filename`: The name of the file
  - `path`: The path of the file
  -  `machine`: the machine the file resides on
  -  `size`: THe size of the file in bytes
  -  `description`: A string describing the file
  -  `originator`: Where the file came from (e.g. the URL it was downloaded from, or the simulation that produced it)
  -  `group`: What the file belongs to, e.g. fire, disease, space weather
  
  This returns the UUID of the newly registered file

- `/DM/copy/[uuid]` (method=`POST`):
  Copies the file object `uuid` to a new location (creating a new data entity). The required fields in the request are:
  - `machine`: the machine the copy is to reside on
  - `dest`: the path (including filename) of the new file
  
  This returns a new UUID for the copy.

- `/DM/move/[uuid]` (method=`POST`):
  Moves the file object `uuid` to a new location (deleting the one at the original locaiton). The required fields in the request are:
  - `machine`: the machine the copy is to reside on
  - `dest`: the path (including filename) of the new file
  
  This returns status code 200 if successful.

- `/DM/delete/[uuid]` (method=`DELETE`):
  This deletes a file associated with `uuid`. This only deletes the file and changes its status in the Data Manager to be "DELETED". This does not remove the entry in the Data Manager's database.

- `/DM/getexternal` (method=`PUT`):
  This downloads a file from an external URI onto a machine. This will return a UUID for the new file. The request must contain:
  - `filename`: The name of the file
  - `path`: The path of the file
  - `machine`: the machine the file resides on
  - `size`: THe size of the file in bytes
  - `description`: A string describing the file
  - `originator`: Where the file came from (e.g. the URL it was downloaded from, or the simulation that produced it)
  - `group`: What the file belongs to, e.g. fire, disease, space weather
  - `url`: The URL of the remote resource to be downloaded
  - `protocol`: The protocol to use to get the file (Currently only `http` is supported)
  - `options`: A json dictionary of options (e.g. username and password). At present a non-empty dictionary is not supported

- `/DM/archive/[uuid]` (method=`POST`):
  This (tars? then) moves the file represented by `uuid` to a long-term storage facility. THIS IS NOT IMPLEMENTED YET

- `/DM/activate/[uuid]` (method=`POST`):
  This undoes the effects of `/archive`, by moving a file back onto a HPC machine. THIS IS NOT IMPLEMENTED YET

- `/DM/async/copy/[uuid]` (method=`POST`):
  Asynchronous copy. The request for this is identical to that of `/DM/copy`, however the copy is deferred to run in the background. The return for this is the UUID for the file transfer task, which can be queried using `/DM/async/status/[transfer uuid]`

- `/DM/async/move/[uuid]` (method=`POST`):
  Asynchronous move. The request for this is identical to that of `/DM/move`, however the move is deferred to run in the background. The return for this is the UUID for the file transfer task, which can be queried using `/DM/async/status/[transfer uuid]`

- `/DM/async/getexternal/` (method=`POST`):
  Asynchronous download of data from the interner. The request for this is identical to that of `/DM/getexternal`, however the download is deferred to run in the background. The return for this is the UUID for the download task, which can be queried using `/DM/async/status/[transfer uuid]`

- `/DM/async/status/` (method=`GET`):
  Get the status of an asynchronous task. This returns a json with the fields `status` and `result`. The status is one of `QUEUED`, `RUNNING`, `COMPLETE` or `ERROR`. The result is the output of the completed task (or the error message in case of an error). The output can be for example, the UUID of a new file object, or simply a message to say the operation has completed (in the case of a move).

## The Data Manager's Database
The Data Manager stores information on all the data objects with a database table with the following fields:

- `id`: The data object's UUID (Primary key)
- `machine`: The machine the data resides on
- `filename`: The name of the file
- `path`: The filepath of the file
- `description`: A string describing what the file is
- `size`: The size of the file in bytes
- `metadata`: Any metadata we wish to store about the file. This is stored as json
- `date_registered`: When this data was registered with the system
- `date_modified`: Time this data was last modified (e.g. copied, moved etc)
- `status`: The status of the file. Could be "ACTIVE", "ARCHIVED", "DELETED", "UNKNOWN"
- `originator`: Strong stating where this file came from, whether it be the URL of a remote data source, or the simulation that produced this file.
- `group`: What kind of incident does this belong to, e.g. Fire, Space Weather, Mosquito etc.

## TODO

- Implement `/archive` and `/activate`
- Add more functionality to `/getexternal`
- Create directories for a filepath if they do not exist?
- Implement an interface for the async operatons to the workflow system
