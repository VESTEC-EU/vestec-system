import io
import logging
from mproxy.core.model import CmdResult
from .throttle import ThrottlableMixin, throttle
from random import randint

log = logging.getLogger(__name__)

dummy_jobs={}

class DummyMachineConnection(ThrottlableMixin):
    """Don't do anything except log operations and return dummy data"""

    def __init__(
        self,
        name,
        min_wait_ms=1,
        max_wait_ms=2 ** 15,
        get=b"Some data",
        cwd="/home/vestec",
        ls=["README.md"],
    ):
        self.name = name
        super().__init__(min_wait_ms, max_wait_ms)
        self._get = get
        self._cwd = cwd
        self._ls = ls

    @throttle
    def run(self, command, env=None):
        log.info("%s.run(%s)", self.name, command)
        return CmdResult(stdout="dummy execution", stderr="none")

    @throttle
    def put(self, src_bytes, dest):
        log.info("%s.put(%d B -> %s)", self.name, len(src_bytes), dest)

    @throttle
    def get(self, src):
        log.info("%s.get(%s)", self.name, src)
        return self._get

    @throttle
    def upload(src_file, dest_file):
        log.info("%s.upload(%s)", self.name, src_file)

    @throttle
    def download(src_file, dest_file):
        log.info("%s.download(%s)", self.name, src_file)

    @throttle
    def remote_copy(src_file, dest_machine, dest_file):
        log.info("%s.remote_copy(%s)", self.name, src_file)

    @throttle
    def cd(self, dirname):
        log.info("%s.cd(%s)", self.name, dirname)

    @throttle
    def getcwd(self):
        log.info("%s.getcwd()", self.name)
        return self._cwd

    @throttle
    def getstatus(self):
        log.info("%s.getstatus()", self.name)
        return "connected"

    @throttle
    def getDetailedStatus(self):
        str_to_return=""
        return str_to_return

    @throttle
    def submitJob(self, num_nodes, requested_walltime, directory, executable):
        log.info("%s.getstatus()", self.name)
        queueid="Q"+(''.join(["{}".format(randint(0, 5)) for num in range(0, 5)]))
        dummy_jobs[queueid]="QUEUED"
        return [True, queueid]

    @throttle
    def getJobStatus(self, queue_ids):
        to_return={}
        for queue_id in queue_ids:
            if (queue_id in dummy_jobs):
                status=dummy_jobs[queue_id]
                if (status == "QUEUED"):
                    dummy_jobs[queue_id]="RUNNING"
                elif (status == "RUNNING"):
                    dummy_jobs[queue_id]="COMPLETED"
                to_return[queue_id]=[dummy_jobs[queue_id], "0:0:1", "-", "-"]
            else:
                to_return[queue_id]=["UNKNOWN", "0:0:0", "-", "-"]
        return to_return

    @throttle
    def cancelJob(self, queue_id):
        if (queue_id in dummy_jobs):
            dummy_jobs[queue_id]="CANCELLED"

    @throttle
    def ls(self, dirname="."):
        log.info("%s.ls(%s)", self.name, dirname)
        return self._ls

    @throttle
    def mkdir(self, dirname, args=""):
        log.info("%s.mkdir(%s)", self.name, dirname)

    @throttle
    def rm(self, filename):
        log.info("%s.rm(%s)", self.name, filename)

    @throttle
    def rmdir(self, dirname):
        log.info("%s.rmdir(%s)", self.name, dirname)

    @throttle
    def mv(self, src, dest):
        log.info("%s.mv(%s -> %s)", self.name, src, dest)

    @throttle
    def cp(self, src, dest, args=""):
        log.info("%s.cp(%s -> %s)", self.name, src, dest)


def DummyMachineConnectionFactory(name):
    return DummyMachineConnection(name)
