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
    def cd(dirname: str) -> None:
        pass

    @rpcmethod
    def getcwd() -> str:
        pass

    @rpcmethod
    def ls(dirname: str = ".") -> list:
        pass

    @rpcmethod
    def mkdir(d: str) -> None:
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

    pass
