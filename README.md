# vestec-wp5
VESTEC Project WP5

## Installation/basic running Instructions
You will need python 3 to run the existing framework with the following python packages (installed through pip or an equivalent)
- Flask
- Paramiko
- Fabric
- Pony
- Requests

Firstly you will need to initialise the database. To do this, change into the `Database` directory and run
```
$ python generate_db.py
```

*NOTE: This need only be done once to set up the database*

In order to run the services, two running processes are required: the simulation manager and the web interface. In one terminal run
```
$ cd Website
$ python app.py
```
and in another run
```
$ cd SimulationManager
$ python manager.py
```

You can reach the web interface at `http://0.0.0.0:5000/`

At present all you can do is 'submit' a job (which only causes the manager to simulate a job running, changing its status from QUEUED to RUNNING to COMPLETED), and query the status of jobs.

## Docker Instructions
To run all the services, change into the `DockerFiles` directory and run
```
$ docker-compose build
$ docker-compose up
```

To bring the services down, use
```
$ docker-compose down
```
(`CTRL-C` does not always work so this step is needed to ensure everything is cleaned up)

To build a single service (e.g. for testing) run
```
$ docker build -f [dockerfile] --tag=[image_name] ../
$ docker run [image_name]
```
