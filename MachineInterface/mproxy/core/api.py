from .rpc import rpcmethod
from .model import CmdResult

class API:
    DEFAULT_EXCHANGE = "mproxy"

    @rpcmethod
    def run(cmd: str, env: dict = None) -> CmdResult:
        """Run a command on the remote server"""
        return

    @rpcmethod
    def put(src_bytes: bytes, dest: str) -> None:
        return

    @rpcmethod
    def get(src: str) -> bytes:
        pass

    @rpcmethod
    def upload(src_file: str, dest_file: str) -> None:
        pass

    @rpcmethod
    def download(src_file: str, dest_file: str) -> None:
        pass

    @rpcmethod
    def remote_copy(src_file: str, dest_machine:str, dest_file: str) -> None:
        pass

    @rpcmethod
    def cd(dirname: str) -> None:
        pass

    @rpcmethod
    def getcwd() -> str:
        pass

    @rpcmethod
    def getstatus() -> str:
        pass

    @rpcmethod
    def submitJob(num_nodes: int, requested_walltime:str, directory:str, executable: str) -> list:
        pass
	
    @rpcmethod
    def getJobStatus(queue_id: list) -> dict:
        pass

    @rpcmethod
    def cancelJob(queue_id: str) -> None:
        pass

    @rpcmethod
    def ls(dirname: str = ".") -> list:
        pass

    @rpcmethod
    def mkdir(d: str, args: str = "") -> None:
        pass

    @rpcmethod
    def rm(filename: str) -> None:
        pass

    @rpcmethod
    def rmdir(dirname: str) -> None:
        pass

    @rpcmethod
    def mv(src: str, dest: str) -> None:
        pass

    @rpcmethod
    def cp(src: str, dest: str, args: str = "") -> None:
        pass

    pass
