import io
import logging
import fabric
from .throttle import ThrottableMixin, throttle

log = logging.getLogger(__name__)


class FabricMachineConnection(ThrottlableMixin):
    """Perform operations on a remote machine with fabric"""

    def __init__(
        self, fab_connection, remote_base_dir, min_wait_ms=1, max_wait_ms=2 ** 15
    ):
        super().__init__(min_wait_ms, max_wait_ms)

        self.remote_base_dir = remote_base_dir
        self.connection = fab_connection
        self.sftp = self.connection.sftp()

    @throttle
    def run(self, command, env=None):
        if env is None:
            env = {}

        cwd = self.getcwd()
        cmd = "cd {} && {}" % (cwd, command)
        log.info("Sending command '%s'", cmd)
        return self.connection.run(cmd, env=env, hide=True, warn=True)

    @throttle
    def put(self, src_bytes, dest):
        log.info("Copying to %s:%s", self.host, os.path.join(self.getcwd(), dest))
        with io.BytesIO(src_bytes) as src:
            self.sftp.putfo(src, dest)

    @throttle
    def get(self, src):
        log.info("Copying from %s:%s", self.host, os.path.join(self.getcwd(), src))
        with io.BytesIO() as dest:
            self.sftp.getfo(src, dest)
            return dest.getvalue()

    @throttle
    def submitJob(self, num_nodes, requested_walltime, executable):
        log.info("%s.getstatus()", self.name)
        return "Q123456"

    @throttle
    def cd(self, dir):
        self.sftp.chdir(dir)

    @throttle
    def getcwd(self):
        return self.sftp.getcwd()

    @throttle
    def ls(self, d="."):
        return self.sftp.listdir(d)

    @throttle
    def mkdir(self, d):
        files = self.ls()
        if dir not in files:
            self.sftp.mkdir(d)
        else:
            log.info("Directory '%s' already exists. Skipping", d)

    @throttle
    def rm(self, file):
        self.sftp.remove(file)

    @throttle
    def rmdir(self, dir):
        self.sftp.rmdir(dir)

    @throttle
    def mv(self, src, dest):
        self.sftp.move(src, dest)

    pass
