# vestec-wp5
VESTEC Project WP5

## Installation/basic running instructions
*It is strongly recommended to use Docker to run the server as there are many interrelated components that need to be run together and docker-compose streamlines this. See the Docker Instructions section below for instructions.*

You will need python 3 to run the existing framework with the following python packages (installed through pip or an equivalent):
- Flask
- Paramiko
- Fabric
- Pony
- Requests


Make sure that the root directory of this repository is included in the PYTHONPATH variable, e.g., by executing
```
$ export PYTHONPATH=$PYTHONPATH:/absolute/path/to/repository
```
before the execution of any of the commands below.


### Setting up the Database
There are two choices for the database. Either you can use a sqlite database file, or use a MySQL/MariaDB database. Which is being used, and the settings for each are controlled through environment variables (see `DockerFiles/environment_variables.env` for example values).

#### SQLite
Set the variables:
```
VESTEC_DB_TYPE="sqlite"
VESTEC_DB_PATH="/path/to/db.sqlite"
```

#### MySQL/MariaDB
Ensure you have a MySQL/MariaDB database server running. Then set the following variables:
```
VESTEC_DB_TYPE="mysql"
VESTEC_DB_USER=[sql username]
VESTEC_DB_PASSWD=[sql password]
VESTEC_DB_SERVER=[sql server hostname]
VESTEC_DB_PORT=[sql server port]
VESTEC_DB_NAME=[sql database name]
```

#### Creating the database
*NOTE: This need only be done once to set up the database*

*NOTE 2: If you are using MariaDB/MySQL remember to create the database first, e.g. `> CREATE DATABASE vestec;`*

Firstly you will need to initialise the database with the correct structures. To do this, change into the `Database` directory and run
```
$ python generate_db.py
```
Ensuring you have set the environment variables given above.



### Run the services

In order to run the services, two running processes are required: the simulation manager and the web interface. In one terminal run
```
$ cd website
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
Using Docker, the website is served using a NGINX image, and we have a separate MariaDB image to serve the database.

### NGINX setup Instructions
The NGINX image requires a certificate file `vestec.epcc.ed.ac.uk.crt` and key `vestec.epcc.ed.ac.uk.key`(to enable secure https), as well as a file `htpasswd` that contains login credentials to access the site. Instructions on how to create this file can be found [here](https://docs.nginx.com/nginx/admin-guide/security-controls/configuring-http-basic-authentication/). The image needs to be pointed to the directory these are stored in (`/var/vestec/certs` on `vestec.epcc.ed.ac.uk`). This is done in the `docker-compose.yml` script, though you may need to edit it to point to the correct location for your machine.

### MariaDB setup instructions
You will need to point the MariaDB image to the database directory on the host machine. On `vestec.epcc.ed.ac.uk` this is at `/var/vestec/db`. This is done in the `docker-compose.yml` script, though you may need to edit it to point to the correct location for your machine. You may also wish to change the `MYSQL_ROOT_PASSWORD` environment variable in the docker compose file.

*Remember to also follow the instructions in the above "Creating the Database" section to set up the database. For the environment variables, use `environment_variables.env`*

### Running the Services


To run all the services run
```
$ docker-compose build
$ docker-compose up -d
```
You should now be able to access the service at <https://vestec.epcc.ed.ac.uk>. You will need to enter a username and password as specified in the `htpasswd` file.

To bring the services down, use
```
$ docker-compose down
```

To build a single service (e.g. for testing) run
```
$ docker build -f [dockerfile] --tag=[image_name] ../
$ docker run [image_name]
```
