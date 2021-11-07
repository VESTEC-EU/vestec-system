# Data Manager API
The data manager will track data sets and abstract the physical operations on these items irrespective of physical location

## registerDataWithDM

`registerDataWithDM(filename, machine, description, type, size, originator, group = "none", storage_technology=None, path=None, associate_with_incident=False, incidentId=None, kind="", comment=None)`

Registers data with the data manager, the arguments are:
 * _filename_: The name of the file to register
 * _machine_: Location of the file, this is either the name of a registered HPC machine or _localhost_ if stored locally by the VESTEC system
 * _description_: Textual description of the dataset being registered
 * _type_: Metadata type of the dataset
 * _size_: Size of the dataset in bytes
 * _originator_: Where the data originates from, such as an HPC simulation, sensor, processed data
 * _group_: (Optional) Group of the data for logically associating datasets together
 * _storage_technology_: (Optional) The storage technology to use, if omitted will default to the filesystem. Can currently be _FILESYSTEM_ or _VESTECDB_, the later will represent that the data is stored within the VESTEC database (only applicable if the data is held on the VESTEC system).
 * _path_: (Optional) Absolute path to the data
 * _associate_with_incident_: (Optional) Whether to associate the dataset with an explicit incident or not
 * _incidentId_: (Optional) The incident unique identifier that this data is associated with
 * _kind_: (Optional) The kind of the dataset
 * _comment_: (Optional) Free text field associating any miscellaneous comments with the data

Returns the unique DM identifier of this new dataset.

If the registration is unsuccessful then the _DataManagerException_ will be thrown with associated message describing the source of the error.

## searchForDataInDM

`searchForDataInDM(filename, machine, path=None)`

Will search the DM for a specific dataset, if it is found will return a description of the data.

 * _filename_: The name of the file to register
 * _machine_: Location of the file, this is either the name of a registered HPC machine or _localhost_ if stored locally by the VESTEC system
 * _path_: (Optional) Absolute path to the data

If searching is unsuccessful then will throw _DataManagerException_, there are two situations where this could be thrown - firstly if the dataset can not be found and secondly if there are multiple datasets found based on the search criteria. The message associated with the exception will provide further details as to the exact error.

## getInfoForDataInDM

`getInfoForDataInDM(data_uuid=None)`

Returns information for a specific dataset or all datasets/

* _data_uuid_: (Optional) Unique identifier of the dataset we are retrieving, if omitted with return information for all datasets

If unsuccessful then the _DataManagerException_ will be thrown with associated message describing the source of the error.

## getByteDataViaDM

`getByteDataViaDM(data_uuid, gather_metrics=False)`

Returns the byte (binary) data of a specific dataset. This will succeed irrespective of where the data is located and depending upon the location and storage technology will be undertaken by different approaches. 

* _data_uuid_: Unique identifier of the dataset we are retrieving
* _gather_metrics_: (Optional) If set will gather and store performance metrics for this retrieval

If unsuccessful then the _DataManagerException_ will be thrown with associated message describing the source of the error.

## putByteDataViaDM

`putByteDataViaDM(filename, machine, description, type, originator, payload, group = "none", storage_technology=None, path=None, associate_with_incident=False, incidentId=None, kind="", comment=None, gather_metrics=False)`

Puts binary data to some target location storing it as appropriate (depending on machine and storage technology) and registers this dataset with the DM. 
 * _filename_: The name of the file to register
 * _machine_: Location of the file, this is either the name of a registered HPC machine or _localhost_ if stored locally by the VESTEC system
 * _description_: Textual description of the dataset being registered
 * _type_: Metadata type of the dataset
 * _payload_: Binary data payload
 * _originator_: Where the data originates from, such as an HPC simulation, sensor, processed data
 * _group_: (Optional) Group of the data for logically associating datasets together
 * _storage_technology_: (Optional) The storage technology to use, if omitted will default to the filesystem. Can currently be _FILESYSTEM_ or _VESTECDB_, the later will represent that the data is stored within the VESTEC database (only applicable if the data is held on the VESTEC system).
 * _path_: (Optional) Absolute path to the data
 * _associate_with_incident_: (Optional) Whether to associate the dataset with an explicit incident or not
 * _incidentId_: (Optional) The incident unique identifier that this data is associated with
 * _kind_: (Optional) The kind of the dataset
 * _comment_: (Optional) Free text field associating any miscellaneous comments with the data
 * _gather_metrics_: (Optional) If set will gather and store performance metrics for this operation

Returns the unique DM identifier of this new dataset.

If unsuccessful then the _DataManagerException_ will be thrown with associated message describing the source of the error.

## downloadDataToTargetViaDM

`downloadDataToTargetViaDM(filename, machine, description, type, originator, url, protocol, group = "none", storage_technology=None, path=None, options=None, associate_with_incident=False, incidentId=None, kind="", comment=None, callback=None)`
        
Downloads data from some external source (represented by _url_ and _protocol_) to a target and register this dataset with the DM. Note that the system will always gather performance metrics for this operation.
* _filename_: The name of the file to register
 * _machine_: Location of the file, this is either the name of a registered HPC machine or _localhost_ if stored locally by the VESTEC system
 * _description_: Textual description of the dataset being registered
 * _type_: Metadata type of the dataset
 * _originator_: Where the data originates from, such as an HPC simulation, sensor, processed data
 * _url_: Source location of data to download from
 * _protocol_: Protocol to use when downloading the data (currently http and https supported)
 * _group_: (Optional) Group of the data for logically associating datasets together
 * _storage_technology_: (Optional) The storage technology to use, if omitted will default to the filesystem. Can currently be _FILESYSTEM_ or _VESTECDB_, the later will represent that the data is stored within the VESTEC database (only applicable if the data is held on the VESTEC system).
 * _path_: (Optional) Absolute path to the data
 * _associate_with_incident_: (Optional) Whether to associate the dataset with an explicit incident or not
 * _incidentId_: (Optional) The incident unique identifier that this data is associated with
 * _kind_: (Optional) The kind of the dataset
 * _comment_: (Optional) Free text field associating any miscellaneous comments with the data
* _callback_: (Optional) If provided will operate in non-blocking mode and return immediately, then calling back to specified workflow state when data transfer is completed or error has occurred

Returns the unique DM identifier of this new dataset. It is possible for _filename_, _url_, and _path_ to be lists and in such cases then multiple downloads will be issued and a list of unique DM identifiers returned. An error (via the  _DataManagerException_ will be thrown) if a mixture of lists and scalars are provided as arguments to this call.

If unsuccessful then the _DataManagerException_ will be thrown with associated message describing the source of the error.

## moveDataViaDM

`moveDataViaDM(data_uuid, dest_name, dest_machine, dest_storage_technology=None, gather_metrics=True)`

Moves a dataset from one location to another. The source and target locations can be on separate machines as the DM will abstract these details.
* _data_uuid_: Unique identifier of the dataset we are moving
* _dest_name_: Full path filename of the destination file
* _dest_machine_: Location of the destination file, this is either the name of a registered HPC machine or _localhost_ if stored locally by the VESTEC system
* _dest_storage_technology_: (Optional) The storage technology to use for destination file, if omitted will default to the filesystem. Can currently be _FILESYSTEM_ or _VESTECDB_, the later will represent that the data is stored within the VESTEC database (only applicable if the data is held on the VESTEC system)
* _gather_metrics_: (Optional) If set will gather and store performance metrics for this operation

Returns the unique DM identifier of the new, moved, dataset.

If unsuccessful then the _DataManagerException_ will be thrown with associated message describing the source of the error.

## copyDataViaDM

`copyDataViaDM(data_uuid, dest_name, dest_machine, dest_storage_technology=None, gather_metrics=True,associate_with_incident=False, incident=None, kind="")`

Copies a dataset from one location to another. The source and target locations can be on separate machines as the DM will abstract these details.
* _data_uuid_: Unique identifier of the dataset we are copying
* _dest_name_: Full path filename of the destination file
* _dest_machine_: Location of the destination file, this is either the name of a registered HPC machine or _localhost_ if stored locally by the VESTEC system
* _dest_storage_technology_: (Optional) The storage technology to use for destination file, if omitted will default to the filesystem. Can currently be _FILESYSTEM_ or _VESTECDB_, the later will represent that the data is stored within the VESTEC database (only applicable if the data is held on the VESTEC system)
* _gather_metrics_: (Optional) If set will gather and store performance metrics for this operation
* _associate_with_incident_: (Optional) Whether to associate the new copied dataset with an explicit incident or not
* _incidentId_: (Optional) The incident unique identifier that this  new copied data is associated with
* _kind_: (Optional) The kind of the new copied dataset

Returns the unique DM identifier of the new, copied, dataset.

If unsuccessful then the _DataManagerException_ will be thrown with associated message describing the source of the error.

## deleteDataViaDM

`deleteDataViaDM(data_uuid)`

Will delete a dataset by removing it at the source and eliminating the entry in the DM.
* _data_uuid_: Unique identifier of the dataset we are removing

If unsuccessful then the _DataManagerException_ will be thrown with associated message describing the source of the error.

## predictDataTransferPerformance

`predictDataTransferPerformance(src_machine, dest_machine, data_size)`

Will predict (in seconds) the transfer performance of data from a source to destination machine based on data transfer metrics routinely collected
* _src_machine_: The machine to transfer the data from
* _dest_machine_: The machine to transfer the data to
* _data_size_: Size in bytes of the data

Will throw the _DataManagerException_ is unsuccessful, including if no prediction can be made due to a lack of performance data

## predictDatasetTransferPerformance

`predictDatasetTransferPerformance(data_uuid, dest_machine)`

Will predict (in seconds) the transfer performance of a dataset from its current location to destination machine based on data transfer metrics routinely collected
* _data_uuid_: The unique identifier of data that considering for transfer
* _dest_machine_: The machine to transfer the data to

Will throw the _DataManagerException_ is unsuccessful, including if no prediction can be made due to a lack of performance data
