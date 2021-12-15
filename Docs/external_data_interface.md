# External Data Interface API

Workflows sometimes need to interact with the EDI, for instance registering and managing endpoints

## getAllEDIEndpoints

`getAllEDIEndpoints()`

Retrieves a list of all the endpoints that are currently registered with the EDI 

## getEndpointInformation

`getEndpointInformation(endpoint)`

Retrieves a dictionary of information about a specific endpoint based on the arguments:

* _endpoint*: The name of the endpoint that we are looking up.

If found, a dictionary is returned which contains the following information, otherwise the dictionary will be empty:

* _id_: Unique identifier of the endpoint
* _queuename_: Name of workflow queue that will be activated with data
* _endpoint_: Endpoint that we are working with, such as a URL for pull mode or URI name for push mode
* _type_: Whether the endpoint is running in push or pull mode
* _pollperiod_: The period in seconds that the data source will be polled (only applicable if pull mode).

## removeEndpoint

`removeEndpoint(incidentid, endpoint, queuename, pollperiod=None)`

Removes a specific endpoint based on the arguments:

* _incidentid_: Unique identifier of the incident
* _endpoint_: Endpoint that we are polling or making available for push
* _queuename_: Workflow queue name that will be activated with new data
* _pollperiod_: (Optional) Polling period, only relavent if running in pull mode

If no such endpoint can be found or there is an error then `ExternalDataInterfaceException` will be thrown

## registerEndpoint

`registerEndpoint(incidentid, endpoint, queuename, pollperiod=None)`

Registers an endpoint based on the arguments provided:
* _incidentid_: Unique identifier of the incident
* _endpoint_: Endpoint that we are polling or making available for push
* _queuename_: Workflow queue name that will be activated with new data
* _pollperiod_: (Optional) Polling period, if provided will run in pull mode, otherwise runs in push mode.

If this is in pull mode then it will periodically poll (based on _poll_period_ the endpoint). Whenever a poll occurs then the corresponding workflow stage will be activated based upon the metadata (the actual data payload is not downloaded). The message passed to that workflow stage is a dictionary containing:

* _source_: The endpoint name we were polling
* _timestamp_: Timestamp that the poll occurred
* _headers_: Metadata headers from the poll that the workflow stage can use to determine if this is a new dataset or not
* _type_: Pull as this was in pull mode
* _incidentid_: Unique ID of the associated incident

If this is in push mode then the EDI will register the endpoint _EDI/endpoint_ where endpoint is the name of the endpoint. Whenever a data payload is pushed to this then the workflow stage will be activated with the following dictionary of data:

* _source_: The endpoint name that was pushed to
* _timestamp_: Timestamp when the data push occurred
* _headers_: Data payload that was pushed to this endpoint
* _type_: Push as this is in push mode
* _incidentid_: Unique ID of the associated incident

If registration can not occur then `ExternalDataInterfaceException` will be thrown

