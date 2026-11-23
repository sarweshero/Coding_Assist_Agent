import asyncssh


class SSHManager:
    """Async SSH client with SFTP + exec + interactive shell support."""

    def __init__(self) -> None:
        self._conn = None
        self._sftp = None

    @property
    def is_connected(self) -> bool:
        return self._conn is not None and not self._conn.is_closed()

    async def connect(self, host: str, port: int, username: str, password: str = None, private_key: str = None, passphrase: str = None) -> bool:
        self._conn = await asyncssh.connect(
            host=host,
            port=port,
            username=username,
            password=password,
            private_key=private_key,
            passphrase=passphrase,
        )
        self._sftp = self._conn.open_sftp()
        return True

    async def disconnect(self) -> None:
        if self._conn is not None and not self._conn.is_closed():
            self._conn.close()
        self._conn = None
        self._sftp = None

    async def exec_command(self, command: str, timeout: int = 30) -> dict:
        if self._conn is None or self._conn.is_closed():
            raise ConnectionError("SSH connection is not established")
        result = await self._conn.run(command, timeout=timeout)
        return {
            "command": command,
            "stdout": result.stdout.decode(errors="replace") if result.stdout else "",
            "stderr": result.stderr.decode(errors="replace") if result.stderr else "",
            "exit_code": result.returncode,
        }

    async def read_file(self, path: str) -> str:
        if self._sftp is None:
            raise ConnectionError("SSH SFTP session is not open")
        data = await self._sftp.open(path, "r").read()
        return data.decode(errors="replace") if data else ""

    async def write_file(self, path: str, content: str) -> bool:
        if self._sftp is None:
            raise ConnectionError("SSH SFTP session is not open")
        await self._sftp.open(path, "w").write(content.encode())
        return True

    async def list_dir(self, path: str) -> list:
        if self._sftp is None:
            raise ConnectionError("SSH SFTP session is not open")
        return await self._sftp.listdir(path)

    def open_shell(self):
        if self._conn is None or self._conn.is_closed():
            raise ConnectionError("SSH connection is not established")
        return self._conn.create_command("bash")
