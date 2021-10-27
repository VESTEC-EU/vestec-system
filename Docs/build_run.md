# Building and running the system

At this point we assume you have installed the system as per the [instructions](https://github.com/VESTEC-EU/vestec-system/blob/main/Docs/install.md). 

## Building the system

Ensure you are in the _DockerFiles_ directory and issue `sudo docker-compose build` which will pull down, build, and install the appropriate containers. Depending upon the specification of your machine this will likely take a few minutes the first time you do it, but subsequently will be much faster to rebuild if required as unmodified items are cached.

>**NOTE:**  
> Every time you make a change to the VESTEC source or configuration files you will need to issue this command to rebuild the containers in order to make those changes visible

### Pruning cached containers

Docker will cache containers and these are not automatically cleaned which will take up disk space. If you are rebuilding the docker containers frequently then to reclain disk space issue `sudo docker system prune -a` and `sudo docker volume prune`

## Running the system

Once the system is built you can then run it via `nohup sudo docker-compose up &> output &` which will start the Docker containers detached from the local bash session (i.e. the session can be terminated without terminating the Docker containers) and all stdio and stderr logging will be directed to the _output_ file. You can then view this via _tail -fn2000 output_ or your other favourite file display tool.

If you are using persistent Open SSH connections to HPC machines (which can be required if the systems require password access) then at this stage you can access the MachineInterface docker image via `sudo docker exec -it machineinterface /bin/bash` and inside the bash then ssh to the appropriate machines to create the persistent connection. Once made you can exit the container's bash session and the persistent connection without closing the persistent connection. 

## Stopping the system

To stop the VESTEC system issue `sudo docker-compose down`

>**NOTE:**  
> It is advised that you do not shutdown the containers via killing them or Ctrl-C as often this does not leave them in a consistent state. If you do this then issue the above docker-compose down command regardless

## Incrementing the build number

If you are changing the code and wish to increment the build number then the version number displayed is made up of two parts, a hard coded _x.x_ in _ExternalServices/managementAPI.py_ and the number of git commits. This last bit is especially useful to update and can be done by cding into _ExternalServices/misc_ and then executing the _./gitnumber.sh_ script.
