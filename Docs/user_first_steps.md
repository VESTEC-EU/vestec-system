# Using the VESTEC system: First steps

Once the system is [installed](https://github.com/VESTEC-EU/vestec-system/blob/main/Docs/install.md) and [running](https://github.com/VESTEC-EU/vestec-system/blob/main/Docs/build_run.md) you can now login and access it.

## Creating a user administrator account 

We will log into the VESTEC management web interface and to do this, and indeed interact with the system at all, we must have a user account in place. To do this visit the VESTEC system management interface (e.g. _https://mymachine.com_) and request an account via the _Sign Up_ button on the page. This will send you to an account creation page where you can fill in the details of your requested account. Once you click _Sign Up_ here then the account will be created, however it has not yet been activated (i.e. you can not log into the system with this).

As an administrator you will be able to use the web management interface to manage and approve accounts of your users as they sign up, however for the first account you will need to approve this (and upgrade to administrator status) via the command line tool. On the VESTEC system you should list the active containers:

```
 $ sudo docker container ls
CONTAINER ID        IMAGE                 COMMAND                  CREATED              STATUS              PORTS                                      NAMES
1eb9c7d5969    dockerfiles_nginx              "/docker-entrypoint.…"   6 minutes ago   Up 6 minutes   0.0.0.0:80->80/tcp, :::80->80/tcp, 0.0.0.0:443->443/tcp, :::443->443/tcp   nginx
9554bf51fdd0   dockerfiles_machineinterface   "/bin/sh -c 'python …"   6 minutes ago   Up 6 minutes                                                                              machineinterface
884571fe060a   dockerfiles_edi                "python interface.py"    6 minutes ago   Up 6 minutes   5501/tcp                                                                   edi
d56d0cfb943a   dockerfiles_workflow           "/bin/sh -c 'python …"   6 minutes ago   Up 6 minutes                                                                              workflowManager
aa577132ad22   dockerfiles_msm                "/bin/sh -c 'python …"   6 minutes ago   Up 6 minutes   5502/tcp                                                                   msm
a857e87615a0   dockerfiles_datamanager        "/bin/sh -c 'python …"   6 minutes ago   Up 6 minutes   5000/tcp                                                                   DataManager
d7f754408c43   dockerfiles_simmanager         "/bin/sh -c 'python …"   6 minutes ago   Up 6 minutes   5505/tcp                                                                   simmanager
f5d0ec3afa53   mariadb                        "docker-entrypoint.s…"   6 minutes ago   Up 6 minutes   3306/tcp                                                                   mariadb
6a87ab53563e   dockerfiles_externalservices   "/bin/sh -c 'gunicor…"   6 minutes ago   Up 6 minutes   0.0.0.0:8000->8000/tcp, :::8000->8000/tcp                                  externalservices
de07f18da522   rabbitmq                       "docker-entrypoint.s…"   6 minutes ago   Up 6 minutes   4369/tcp, 5671-5672/tcp, 15691-15692/tcp, 25672/tcp                        rabbitmq

```
From this list select one to connect to via bash (it doesn't really matter which one) e.g. `sudo docker exec -it machineinterface /bin/bash` . Once you are inside that container execute `python3 ../CommandLine/manage_users.py -display` which will display the list of users (i.e. the one you just created). To enable your user execute `python3 ../CommandLine/manage_users.py -e name` where _name_ is the name of your user, and `python3 ../CommandLine/manage_users.py -admin name` to upgrade your user to be administrator status.

Once done you can now exit out of the container's bash session and back on the VESTEC management website you should be able to log into the VESTEC system now using your user credentials.

Incidently there is also a `dump_users.py` script in the same `CommandLine` directory, running this without arguments will list out the options and this enables you to dump out a CSV file of all user accounts and then load it in at some later date. It is especially useful when you need to completely rebuild the database but don't want to loose the authenticated user list.

