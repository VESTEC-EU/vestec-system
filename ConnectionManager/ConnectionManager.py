from __future__ import print_function
import os
import socket
import fabric
from . import machines


keydir = os.path.join(os.path.expanduser("~"),".ssh")

class RemoteConnection:
    def __init__(self,machine_name):
        if machine_name not in machines:
            print("Error: Unknown machine '%s'"%machine_name)
            return None

        machine = machines[machine_name]
        keyfile = os.path.join(keydir,machine["SSHkey"])
        #print("Key= %s"%keyfile)

        kwargs = {"key_filename": [keyfile],}

        self.host = machine["host"]
        self.user = machine["username"]

        print("Connecting to %s"%self.host)

        self.connection = fabric.Connection(
            host=self.host,
            user=self.user,
            connect_kwargs=kwargs)

        self.sftp = self.connection.sftp()

        print("Changing remote working directory to '%s'"%machine["basedir"])
        self.cd(machine["basedir"])

    def ExecuteCommand(self, command, env=None):
        if env is None:
            env = {}

        cwd = self.pwd()
        cmd = "cd %s ; %s " % (cwd, command)
        print("Sending command '%s'"%cmd)
        return self.connection.run(cmd, env=env, hide=True, warn=True)

    def CopyToMachine(self, src, dest):
        print("Copying %s to %s:%s/%s" % (src, self.host, self.pwd(), dest))
        self.sftp.put(src, dest)


    def CopyFromMachine(self, src, dest):
        print("Copying %s:%s/%s to %s" % (self.host, self.pwd(), src, dest))
        self.sftp.get(src, dest)

    def cd(self, dir):
        self.sftp.chdir(dir)

    def pwd(self):
        return self.sftp.getcwd()

    def ls(self, dir="."):
        return self.sftp.listdir(dir)

    def mkdir(self, dir):
        files = self.ls()
        if dir not in files:
            self.sftp.mkdir(dir)
        else:
            print("Directory '%s' already exists. Skipping" % dir)


    def rm(self, file):
        self.sftp.remove(file)

    def rmdir(self, dir):
        self.sftp.rmdir(dir)

    def mv(self, src, dest):
        self.sftp.move(src, dest)

    def OpenRemoteFile(self, file, mode):
        return self.sftp.open(file, mode)


if __name__ == "__main__":
    host = "CIRRUS"
    me = socket.gethostname()

    c = RemoteConnection(host)

    result = c.ExecuteCommand("whoami")
    print("Remote command 'whoami' output = ", result.stdout)

    print("Creating test file 'FabricTest.txt' with contents 'Hello to %s from %s'" % (host, me))
    f = open("FabricTest.txt", "w")
    f.write("Hello to %s from %s\n" % (host, me))
    f.close()


    c.CopyToMachine("FabricTest.txt", "FabricTest.txt")
    print("Instructing remote machine to append to this file")
    result = c.ExecuteCommand("echo 'And Hi from '$HOSTNAME >> FabricTest.txt")

    c.CopyFromMachine("FabricTest.txt", "FabricTest.txt")
    print("\nNew contents of file:")
    f = open("FabricTest.txt", "r")
    for line in f.readlines():
        print(line.strip())
    f.close()
    print(c.pwd())
