# Connection Manager
This module contains functionality around connecting to remote machines via ssh and sftp

## Contents
- ConnectionManager.py
  * Contains the RemoteConnection class which allows for a variety of things to be done with a remote machine
- machines.yaml
  * a config file containing a list of machines and their connection options and properties (required by ConnectionManager.py)
- machines.py
  * Superseded by machines.yaml

## Usage
The `RemoteConnection` class can be instantiated within code to allow the code to interact with a remote machine via a variety of ssh and sftp functionalities. For example, if we want to connect to ARCHER, one would do:
```python
from ConnectionManager import RemoteConnection

c = RemoteConnection("ARCHER")
```

By default the connection is opened in the `basedir` directory for the machine as speficied in `machines.yaml`

The `RemoteConnection` class has the following methods that can be used:

### `ExecuteCommand(command,env={})`
Executes a command (with an optional set of environment variables) on the remote machine. Upon completion it returns the stdout, stderr and the exit code of the command. E.g.
``` python
stdout,stderr,exit_code = c.ExecuteCommand("whoami")
print(stdout)
print(stderr)
print(exit_code)
```

### `CopyToMachine(src,dest)`
Copies a local file from `src` to the remote destination, `dest`.

### `CopyFromMachine(src,dest)`
Copies a remote file `src` to a local destination, `dest`.

### `cd(dir)`
Changes directory to `dir`

### `pwd(dir)`
Returns working directory

### `ls(dir=".")`
Returns a list of files/directories in the remote directory, `dir`.

### `mkdir(dir)`
Creates a remote directory, `dir`

### `rm(file)`
Removes a remote file, `file`

### `rmdir(dir)`
Removes a remote directory, `dir`

### `mv(src,dest)`
Moves a remote file/directory from `src` to `dest` (moves within the machine, cannot be used to copy on/off the machine)

### `OpenRemoteFile(file,mode)`
Opens a file on the remote file to be read/written. The usage is similar to the regular python `open`. E.g.
``` python
f=c.OpenRemoteFile("hello.txt"."w")
f.write("Hello World!\n")
f.close()
```
will create the file `hello.txt` on the remote machine and write `Hello world!` to it.

### `CloseConnection()`
Closes the remote connection