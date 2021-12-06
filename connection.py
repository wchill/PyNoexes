from abc import ABC, abstractmethod
from typing import cast
import struct
from result import Result


class Connection(ABC):
    @abstractmethod
    def write_byte(self, b: int) -> None:
        raise NotImplementedError

    @abstractmethod
    def write(self, data: bytes) -> None:
        raise NotImplementedError

    @abstractmethod
    def read_byte(self) -> int:
        raise NotImplementedError

    @abstractmethod
    def read(self, length: int) -> bytearray:
        raise NotImplementedError

    def write_command(self, command: int) -> None:
        self.write_byte(command)

    def write_short(self, s: int) -> None:
        assert s == (s & 0xFFFF), f"Invalid short {s}"
        self.write(s.to_bytes(2, byteorder="little"))

    def write_int(self, i: int) -> None:
        assert i == (i & 0xFFFFFFFF), f"Invalid int {i}"
        self.write(i.to_bytes(4, byteorder="little"))

    def write_long(self, long: int) -> None:
        assert long == (long & 0xFFFFFFFFFFFFFFFF), f"Invalid long {long}"
        self.write(long.to_bytes(8, byteorder="little"))

    def _read_multibyte(self, length: int) -> bytes:
        res = self.read(length)
        assert len(res) == length, f"Expected {length} bytes but only read {len(res)}"
        return res

    def read_short(self) -> int:
        return cast(int, struct.unpack("h", self._read_multibyte(2))[0])

    def read_ushort(self) -> int:
        return cast(int, struct.unpack("H", self._read_multibyte(2))[0])

    def read_int(self) -> int:
        return cast(int, struct.unpack("i", self._read_multibyte(4))[0])

    def read_uint(self) -> int:
        return cast(int, struct.unpack("I", self._read_multibyte(4))[0])

    def read_long(self) -> int:
        return cast(int, struct.unpack("q", self._read_multibyte(8))[0])

    def read_result(self) -> Result:
        return Result.from_int(self.read_int())
