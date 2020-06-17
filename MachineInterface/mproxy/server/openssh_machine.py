import io
import os
import logging
import datetime
from .throttle import ThrottlableMixin, throttle
from .job_status import JobStatus
from subprocess import Popen, PIPE

log = logging.getLogger(__name__)

class OpenSSHMachineConnection(ThrottlableMixin):
    """Perform operations on a remote machine with openssh"""

    def __init__(
        self, queue_system, hostname, remote_base_dir, min_wait_ms=1, max_wait_ms=2 ** 15
    ):
        super().__init__(min_wait_ms, max_wait_ms)

        self.remote_base_dir = remote_base_dir        
        self.queue_system = queue_system        
        self.queue_info={}
        self.hostname=hostname
        self.summary_status={}
        self.queue_last_updated=datetime.datetime.now()

    def _execute_command(self, command):
        p = Popen("ssh -t " + self.hostname+" "+ command, stdout=PIPE, stderr=PIPE, universal_newlines=True, shell=True)
        output, errors = p.communicate()
        return output, errors

    def _checkForErrors(self, errorString, reportError=True):        
        if len(errorString.strip().split('\n')) == 1 and "Shared connection to" in errorString:
            return False
        else:
            if (reportError): print("Error: "+errorString.strip())
            return True

    @throttle
    def run(self, command, env=None):
        cmd = "\"cd "+self.remote_base_dir+" ; "+command+"\""        
        return self._execute_command(cmd)

    @throttle
    def put(self, src_bytes, dest):
        log.info("Copying to %s:%s", self.host, os.path.join(self.getcwd(), dest))
        with io.BytesIO(src_bytes) as src:
            pass #self.sftp.putfo(src, dest)

    @throttle
    def get(self, src):
        log.info("Copying from %s:%s", self.host, os.path.join(self.getcwd(), src))
        with io.BytesIO() as dest:
            #self.sftp.getfo(src, dest)
            return dest.getvalue()    

    def checkForUpdateToQueueData(self):
        elapsed=datetime.datetime.now() - self.queue_last_updated
        if not self.queue_info or elapsed.total_seconds() > 600:
            self.updateQueueInfo()

    def updateQueueInfo(self):
        status_command=self.queue_system.getQueueStatusSummaryCommand()
        output, errors=self.run(status_command)
        if not self._checkForErrors(errors):            
            self.queue_info=self.queue_system.parseQueueStatus(output)
            self.summary_status=self.queue_system.getSummaryOfMachineStatus(self.queue_info)
            self.queue_last_updated=datetime.datetime.now()
            print("Updated status information")

    @throttle
    def getstatus(self):
        self.checkForUpdateToQueueData()
        if (self.summary_status):
            return "Connected (Q="+str(self.summary_status["QUEUED"])+",R="+str(self.summary_status["RUNNING"])+")";
        else:
            return "Error, can not connect"

    @throttle
    def getJobStatus(self, queue_ids):        
        status_command=self.queue_system.getQueueStatusForSpecificJobsCommand(queue_ids)
        output, errors=self.run(status_command)
        to_return={}
        if not self._checkForErrors(errors):
            parsed_jobs=self.queue_system.parseQueueStatus(output)        
            for queue_id in queue_ids:
                if (queue_id in parsed_jobs):
                    status=parsed_jobs[queue_id]                
                    to_return[queue_id]=[status.getStatus(), status.getWalltime()]
                    self.queue_info[queue_id]=status    # Update general machine status information too with this                
        return to_return

    @throttle
    def cancelJob(self, queue_id):
        deletion_command=self.queue_system.getJobDeletionCommand(queue_id)
        output, errors=self.run(deletion_command)
        self._checkForErrors(errors)  

    @throttle
    def submitJob(self, num_nodes, requested_walltime, directory, executable):        
        command_to_run = ""
        if len(directory) > 0:
            command_to_run += "cd "+directory+" ; "
        command_to_run+=self.queue_system.getSubmissionCommand(executable)        
        output, errors=self.run(command_to_run)
        if not self._checkForErrors(errors):
            return [self.queue_system.isStringQueueId(output), output]
        else:
            return [False, errors]

    @throttle
    def cd(self, dir):
        pass #self.sftp.chdir(dir)

    @throttle
    def getcwd(self):
        return "" #self.sftp.getcwd()

    @throttle
    def ls(self, d="."):
        return "" #self.sftp.listdir(d)

    @throttle
    def mkdir(self, d):
        files = self.ls()
        if dir not in files:
            pass #self.sftp.mkdir(d)
        else:
            log.info("Directory '%s' already exists. Skipping", d)

    @throttle
    def rm(self, file):
        pass # self.sftp.remove(file)

    @throttle
    def rmdir(self, dir):
        pass #self.sftp.rmdir(dir)

    @throttle
    def mv(self, src, dest):
        pass #self.sftp.move(src, dest)

    pass
