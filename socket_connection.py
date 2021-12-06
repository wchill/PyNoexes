import socket
from connection import Connection


class SocketConnection(Connection):
    def __init__(self, ip_addr: str, port: int):
        self.sock = socket.create_connection((ip_addr, port), timeout=60)

    def write_byte(self, b: int) -> None:
        assert b == (b & 0xFF), f"Invalid byte {b}"
        self.sock.sendall(b.to_bytes(1, byteorder="little"))

    def write(self, data: bytes) -> None:
        self.sock.sendall(data)

    def read_byte(self) -> int:
        result = self.read(1)
        return int.from_bytes(result, byteorder="little")

    def read(self, length: int) -> bytearray:
        result = bytearray()
        received = 0
        while received < length:
            read = self.sock.recv(min(4096, length - received))
            received += len(read)
            result += read
            if received == 0:
                break

        return result
