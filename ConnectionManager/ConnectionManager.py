from __future__ import print_function
import fabric
import os
import socket
import uuid
import yaml

#load in the machines config file 

dir=os.path.dirname(__file__)
f=open(os.path.join(dir,"machines.yaml"),"r")
machines = yaml.safe_load(f)
f.close()

class ConnectionError(Exception):
    pass



keydir = os.path.join(os.path.expanduser("~"),".ssh")

class RemoteConnection:
    def __init__(self,machine_name):
        if machine_name not in machines:
            print("Error: Unknown machine '%s'"%machine_name)
            return None

        machine = machines[machine_name]
        keyfile = os.path.join(keydir,machine["SSHkey"])
        #print("Key= %s"%keyfile)

        kwargs = {"key_filename": [keyfile],"gss_auth": True,}

        self.host=machine["host"]
        self.user=machine["username"]
        self.port=machine["port"]

        print("Connecting to %s"%self.host)

        try:

            self.connection = fabric.Connection(host=self.host, user=self.user, port=self.port, connect_kwargs=kwargs)

            self.active = True

            self.sftp = self.connection.sftp()
        except socket.gaierror as e:
            print("Cannot establish connection to %s"%self.host)
            raise ConnectionError("Cannot establish connection to host '%s'"%self.host) from None

        #print("Changing remote working directory to '%s'"%machine["basedir"])
        self.cd(machine["basedir"])


    def _CheckActive(self):
        if self.active:
            return
        else:
            raise ConnectionError("Remote connection to '%s' no longer active"%self.host)



    def ExecuteCommand(self,command,env={}):
        self._CheckActive()
        cwd = self.pwd()
        #we want to cd into the working directory before we execute the command
        cmd = "cd %s ; %s"%(cwd,command)
        #print("Sending command '%s'"%command)
        try:
            result = self.connection.run(cmd,env=env,hide=True,warn=True)
        except socket.gaierror as e:
            #print("Cannot establish connection to %s"%self.host)
            raise ConnectionError("Cannot establish connection to host '%s', or connection lost"%self.host) from None
        return result.stdout, result.stderr, result.exited

    def CopyToMachine(self,src,dest):
        self._CheckActive()
        #print("Copying %s to %s:%s/%s"%(src,self.host,self.pwd(),dest))
        self.sftp.put(src,dest)


    def CopyFromMachine(self,src,dest):
        self._CheckActive()
        #print("Copying %s:%s/%s to %s"%(self.host,self.pwd(),src,dest))
        self.sftp.get(src,dest)

    def cd(self,dir):
        self._CheckActive()
        self.sftp.chdir(dir)

    def pwd(self):
        self._CheckActive()
        return self.sftp.getcwd()

    def ls(self,dir="."):
        self._CheckActive()
        return self.sftp.listdir(dir)

    def mkdir(self,dir):
        self._CheckActive()
        files = self.ls()
        if dir not in files:
            self.sftp.mkdir(dir)
        else:
            print("Directory '%s' already exists. Skipping"%dir)


    def rm(self,file):
        self._CheckActive()
        self.sftp.remove(file)

    def rmdir(self,dir):
        self._CheckActive()
        self.sftp.rmdir(dir)

    def mv(self,src,dest):
        self._CheckActive()
        self.sftp.move(src,dest)

    def OpenRemoteFile(self,file,mode):
        self._CheckActive()
        return self.sftp.open(file,mode)

    def size(self,file):
        self._CheckActive()
        result=self.sftp.stat(file)
        return result.st_size

    def CloseConnection(self):
        self._CheckActive()
        self.connection.close()
        self.active=False




#A test code. Connects to a remote machine and does some things
if __name__ == "__main__":
    host = "Blackdog"
    me = socket.gethostname()

    c=RemoteConnection(host)

    stdout,stderr,exit_code =c.ExecuteCommand("whoami")
    print("Remote command 'whoami' output = ",stdout)

    print("Creating test file 'FabricTest.txt' with contents 'Hello to %s from %s'"%(host,me))
    f=open("FabricTest.txt","w")
    f.write("Hello to %s from %s\n"%(host,me))
    f.close()


    c.CopyToMachine("FabricTest.txt","FabricTest.txt")
    print("Instructing remote machine to append to this file")
    stdout,stderr,exit_code=c.ExecuteCommand("echo 'And Hi from '$HOSTNAME >> FabricTest.txt")

    c.CopyFromMachine("FabricTest.txt","FabricTest.txt")
    print("\nNew contents of file:")
    f=open("FabricTest.txt","r")
    for line in f.readlines():
        print(line.strip())
    f.close()
    print(c.pwd())

    wkdir = str(uuid.uuid4())

    c.mkdir(wkdir)
    c.cd(wkdir)
    f=c.OpenRemoteFile("testfile.txt","w")
    f.write("Hello I am a test file\n")
    f.close()
    c.ExecuteCommand("touch ImATouchedFile.txt")



