# Building and running the system

At this point we assume you have installed the system as per the [instructions](https://github.com/VESTEC-EU/vestec-system/blob/main/Docs/install.md). 

## Building the system

Ensure you are in the _DockerFiles_ directory and issue `sudo docker-compose build` which will pull down, build, and install the appropriate containers. Depending upon the specification of your machine this will likely take a few minutes the first time you do it, but subsequently will be much faster to rebuild if required as unmodified items are cached.

>**NOTE:**  
> Every time you make a change to the VESTEC source or configuration files you will need to issue this command to rebuild the containers in order to make those changes visible

