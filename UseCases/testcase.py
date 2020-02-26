from __future__ import print_function
import sys
sys.path.append("../")
import ConnectionManager
import Templating
import uuid
import os
import QueueParsing
import time


nodes = 1
walltime = "00:10:00"
jobname = "vestec_test"
budget = "z19-cse"

modules = """module use /work/z01/z01/shared/vestec/modules
module add vestec-base
module add jacobi"""

command = "aprun -n 4 jacobi"



class Jacobi():
    def __init__(self,name,machine):
        print("Creating job %s on machine %s"%(name,machine))
        self.connection = ConnectionManager.RemoteConnection(machine)
        #print(self.connection.pwd())
        self.connection.mkdir(name)
        self.connection.cd(name)
        print("Created Working directory: ",self.connection.pwd())

        self.wkdir = self.connection.pwd()

        print("\n")


    def create_batch_script(self):
        t=Templating.Templates()
        batchfile=t.render_template("pbs.j2",pbs={"nodes":nodes,"walltime":walltime,"jobname":jobname,"budget":budget},modules=modules,command=command,workdir=self.wkdir)
        print("Creating Batch File 'submit.pbs'")
        print("--------------------------------------------------------------------------------")
        print(batchfile)
        print("--------------------------------------------------------------------------------")
        f=self.connection.OpenRemoteFile("submit.pbs","w")
        f.write(batchfile)
        f.close()
        print("\n")

    def submit_job(self):
        print("Submitting Job:")
        batchfile = os.path.join(self.wkdir,"submit.pbs")
        command = "qsub -q short %s"%batchfile
        stdout,stderr,return_code=self.connection.ExecuteCommand(command)
        if return_code == 0:
            name = stdout.strip()
            print("Job submit successful. JobID = %s\n"%name)
            self.QueueID = name
            return name
        else:
            print("Job submit unsuccessful. Error message:")
            print(stderr)
            self.QueueID = None
            return None

    def QueueStatus(self):
        print("Querying status of job %s"%self.QueueID)
        command = "qstat -fx %s"%self.QueueID
        #print("Command = '%s'"%command)

        stdout,stderr,exit_code=self.connection.ExecuteCommand(command)

        #print r.stdout

        qdata = stdout.splitlines(True)

        jobs=QueueParsing.pbs.Parse(qdata)
        #print jobs

        job = jobs[0]

        if job["job_state"] == "Q":
            print("Job Queued\n")
            return "Q"
        if job["job_state"] == "R":
            print("Job Running\n")
            return "R"
        if job["job_state"] == "F":
            print("Job Finished\n")
            w = job["resources_used.walltime"]
            print("Walltime = %s"%w)
            return "F"
        if job["job_state"] == "E":
            print("Job Exiting\n")
            return "E"
        if job["job_state"] == "H":
            print("Job Held\n")
            return "F"





if __name__ == "__main__":
    name=str(uuid.uuid4())

    j=Jacobi(name,"ARCHER")

    j.create_batch_script()

    name=j.submit_job()

    if name == None:
        print("Job Submission fail. Exiting")
        sys.exit()
    print("'%s'"%name)


    time.sleep(10)

    while j.QueueStatus() != "F":
        time.sleep(30)

    print("Finished :)")
