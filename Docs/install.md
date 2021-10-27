# Installation

## Obtaining the VESTEC system code

Firstly select an appropriate machine, this should be running Linux and accessible via SSH with Docker and Git installed. You will also need to have sudo rights on this machine. To clone the system issue `git clone https://github.com/VESTEC-EU/vestec-system.git`

## Configuring the VESTEC system

Move into the newly created _vestec_system_ directory and from there into the _DockerFiles_ directory. There are a number of items that need to be configured for your system and exactly how you are going to be running the VESTEC system. 

### Production machine

In the _environment_variables.env_ file you need to set the following for your system:

```
VESTEC_DB_TYPE="mysql"
VESTEC_DB_USER=[sql username]
VESTEC_DB_PASSWD=[sql password]
VESTEC_DB_SERVER=[sql server hostname]
VESTEC_DB_PORT=[sql server port]
VESTEC_DB_NAME=[sql database name]
```

You should also change the _MYSQL_ROOT_PASSWORD_ in the _docker-compose.yml_ entry (this will be found under the maria entry). You now need to create the database which you will be using (i.e. the value provided to _VESTEC_DB_NAME_ in the above settings). 

``` 
 $ sudo docker-compose up maria
```

In a new shell on your machine you then need to connect to the mariadb image via `sudo docker exec mariadb /bin/bash` which will start a bash session in that container and login to the database.

``` 
 $ sudo docker exec mariadb /bin/bash
 # mysql -u root -p -h 0.0.0.0
```

At this point you will be prompted for the password for MariaDB (MYSQL_ROOT_PASSWORD) specified in docker-compose.yml. You should now be logged into mysql and you can create the database required where _name_ is the database name set for _VESTEC_DB_NAME_ in the _environment_variables.env_ file.

```
MariaDB [(none)]> create database name;
```

### Local development machine

The VESTEC system will also operate with sqlite and we suggest that this is used for a local development system as it's quicker to install and manage. You will need sqlite installed on your system already, and then in the _environment_variables.env_ file you need to set the following:

```
VESTEC_DB_TYPE="sqlite"
VESTEC_DB_PATH="/path/to/db.sqlite"
```


>**IMPORTANT:**  
> We strongly advise against using sqlite for running the VESTEC system on a production, publicly accessible, system

## Certificate set-up

By default the VESTEC system will use HTTPS for web-based communications and you need to set up the certificate for this. You require a certificate file `mymachine.com.crt` and key `mymachine.com.key`to enable secure https. Instructions on how to create this file can be found [here](https://docs.nginx.com/nginx/admin-guide/security-controls/configuring-http-basic-authentication/). 

The _nginx_ entry of _docker-compose.yml_ file should be updated to point to paths of these files such that these can be picked up. You can see that the configuration mounts the local directory _/var/vestec/certs_ into the container and this is where the files are located. This directory should be changed to suit the location that the files are held on your own system.

### Disabling HTTPS

For local development it might be preferable to disable HTTPS for easy deployment on a development machine. To do so you will need to edit the _default.conf_ file in the _Nginx_ directory to remove HTTPS:

```
server {
    listen 80 default_server;
    server_name vestec.epcc.ed.ac.uk;
    root /var/www/;
    index login.html;

    location / {
        try_files $uri /login.html;
    }

    location /signup {
        try_files $uri /signup.html;
    }

    location /flask {
        proxy_pass http://website:8000;
        proxy_redirect off;
    }

    location /home {
        try_files $uri /base.html;
    }
}
```

## Setting up HPC machine specific SSH configuration
SSH to different machines can require specific configurations, such as the appropriate keys, to be provided. The MachineInterface will set up the SSH configuration file, that will be used for OpenSSH connections to machines, when the container is built. You should specify this and the configuration can be found in `MachineInterface/Dockerfile` . By default it expects that you will create a _misc_ directory in _MachineInterface_ and _ssh_config_ file although this can be changed to suit what is required. Any SSH keys can be placed in the _misc_ directory as this will be visible to the Docker container.

## Running containers in debug mode

By default Docker does not flush stdio, but you can force this to display messages which can be very helpful for debugging as then print statement and other logging information will be sent out and can be viewed. Either in the Dockerfile of each service add `-u` as an argument or add _PYTHONUNBUFFERED: 1_ under the environment in _DockerFiles/docker-compose.xml_
