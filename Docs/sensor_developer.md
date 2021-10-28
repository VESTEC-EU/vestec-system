# Sensor Developer

If you are providing a sensor to the VESTEC system then this will need to interact via the EDI. The design of the EDI is for it to be a simple postbox layer as illustrated below where each EDI endpoint will run in push or pull mode, either periodically polling for new data or waiting until data is pushed into the interface. It is common to have a mixture of settings across numerous endpoints. Depending upon the context, this is then routed to the appropriate workflow stage and a dictionary of the data sent into the workflow manager and appropriate queue (see [EDI API](https://github.com/VESTEC-EU/vestec-system/blob/main/Docs/external_data_interface.md) for more details). Crucially, the EDI itself undertakes no data analysis or transformation as that is all workflow specific. It doesn't even retrieve the data in pull mode (just the metadata). Instead it is up to the workflow provided by the user to undertake these higher level operations as appropriate.

![Sensor EDI](https://raw.githubusercontent.com/VESTEC-EU/vestec-system/main/Docs/sensor_data_edi.png)

## Pushing data into the EDI

When an endpoint is configured in push mode it will register itself as in HTTP(S) POST mode `EDI/endpoint' where _endpoint_ is the name of the endpoint. For instance, if your system URL is _mymachine.com_ then you will push the data to _https://mymachine.com/EDI/endpoint_. This will return status code 202 (data recieved) if successful or code 404 with error message if unsuccessful. 

The following code snippet provides an example of pushing some data from a file to the EDI (you will need to set your machine URL and endpoint name as required.) The script is run with two arguments, the first is the incident unique identifier and second is a data file to push to the endpoint. For debugging purposes the response from the endpoint (success or failure) will be displayed.

```
import sys
import requests
import json

# Set your own URL and endpoint name appropriately
url = 'http://mymachine.com/EDI/endpoint'

if len(sys.argv) < 3:
    print("Error, you must provide the incidentID and data file as a command line argument")
    sys.exit(-1)

data_file=open(sys.argv[2], "r")
read_bytes=data_file.read()
data_file.close()

msg = {"incidentID": sys.argv[1], "payload" : read_bytes}

x = requests.post(url, data = json.dumps(msg))
print("Response: "+x.text)
```

>**NOTE:**  
> If you are looking in-depth at the EDI then might be surprised to see that the EDI endpoint is actually listening on `EDImanager/endpoint` rather than `EDI/endpoint` that we mention above. However the documentation above is correct because the EDI is not physically exposed for public access on the HTTPS port. Instead only one service can utilise a port (e.g. the HTTPS port) and this is the External Services component. It is this component that listens for `EDI/*` and then forwards all data received on `EDI/*` to the EDI via internal `EDImanager/*` path.
