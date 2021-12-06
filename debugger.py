from connection import Connection
from memory_info import MemoryInfo, MemoryType
from enum import Enum
from result import Result
from threading import Lock
from typing import List
import os


class Command:
    COMMAND_STATUS = 0x01
    COMMAND_POKE8 = 0x02
    COMMAND_POKE16 = 0x03
    COMMAND_POKE32 = 0x04
    COMMAND_POKE64 = 0x05
    COMMAND_READ = 0x06
    COMMAND_WRITE = 0x07
    COMMAND_CONTINUE = 0x08
    COMMAND_PAUSE = 0x09
    COMMAND_ATTACH = 0x0A
    COMMAND_DETACH = 0x0B
    COMMAND_QUERY_MEMORY = 0x0C
    COMMAND_QUERY_MEMORY_MULTI = 0x0D
    COMMAND_CURRENT_PID = 0x0E
    COMMAND_GET_ATTACHED_PID = 0x0F
    COMMAND_GET_PIDS = 0x10
    COMMAND_GET_TITLEID = 0x11
    COMMAND_DISCONNECT = 0x12
    COMMAND_READ_MULTI = 0x13
    COMMAND_SET_BREAKPOINT = 0x14


class DebuggerStatus(Enum):
    STOPPED = 0
    RUNNING = 1
    PAUSED = 2


class Debugger:
    def __init__(self, conn: Connection):
        self.conn = conn
        self.lock = Lock()
        self.last_mem_info = None

    def get_status(self) -> DebuggerStatus:
        with self.lock:
            self.conn.write_command(Command.COMMAND_STATUS)
            status = self.conn.read_byte()
            major = self.conn.read_byte()
            minor = self.conn.read_byte()
            patch = self.conn.read_byte()
            protocol_version = (major << 16) | (minor << 8)
            self.conn.read_result()
            protocol_version |= patch

            return DebuggerStatus(status)

    def get_result(self, command: int) -> Result:
        with self.lock:
            self.conn.write_command(command)
            return self.conn.read_result()

    def read_mem(self, addr: int, size: int) -> bytearray:
        with self.lock:
            self.conn.write_command(Command.COMMAND_READ)
            self.conn.write_long(addr)
            self.conn.write_int(size)

            result = self.conn.read_result()
            if result.failed:
                self.conn.read_result()
                raise AssertionError(f"Failed: {result}")

            pos = 0
            buffer = bytearray()
            while pos < size:
                result = self.conn.read_result()
                if result.failed:
                    self.conn.read_result()
                    raise AssertionError(f"Failed: {result}")

                read = self.read_compressed()
                buffer += read
                pos += len(read)

            self.conn.read_result()
            return buffer

    def dump_mem(self, addr: int, size: int, path: str) -> None:
        mem = self.read_mem(addr, size)
        with open(path, "wb") as f:
            f.write(mem)

    def dump_mem_regions(self, memory_infos: List[MemoryInfo], path: str) -> None:
        for memory_info in memory_infos:
            mem = self.read_mem(memory_info.addr, memory_info.size)
            with open(os.path.join(path, f"{memory_info.addr:08x}.dmp"), "wb") as f:
                f.write(mem)

    def read_compressed(self) -> bytearray:
        compressed_flag = self.conn.read_byte()
        decompressed_len = self.conn.read_int()

        if not compressed_flag:
            return self.conn.read(decompressed_len)
        else:
            buf = bytearray()
            compressed_len = self.conn.read_int()
            compressed = self.conn.read(compressed_len)
            pos = 0
            for i in range(0, compressed_len, 2):
                val = compressed[i]
                count = compressed[i+1] & 0xFF
                buf += (val.to_bytes(1, byteorder="little")) * count
                pos += count
            return buf

    def write_mem(self, addr: int, data: bytes) -> Result:
        with self.lock:
            self.conn.write_command(Command.COMMAND_WRITE)
            self.conn.write_long(addr)
            self.conn.write_int(len(data))

            result = self.conn.read_result()
            if result.succeeded:
                self.conn.write(data)

            return self.conn.read_result()

    def read_info(self) -> MemoryInfo:
        addr = self.conn.read_long()
        size = self.conn.read_long()
        mem_type = self.conn.read_int()
        perm = self.conn.read_int()

        result = self.conn.read_result()
        assert result.succeeded, f"Failed: {result}"

        return MemoryInfo(addr, size, mem_type, perm)

    def resume(self) -> Result:
        return self.get_result(Command.COMMAND_CONTINUE)

    def pause(self) -> Result:
        return self.get_result(Command.COMMAND_PAUSE)

    def attach(self, pid: int) -> Result:
        with self.lock:
            self.conn.write_command(Command.COMMAND_ATTACH)
            self.conn.write_long(pid)
            return self.conn.read_result()

    def detach(self) -> Result:
        return self.get_result(Command.COMMAND_DETACH)

    def disconnect(self) -> Result:
        return self.get_result(Command.COMMAND_DISCONNECT)

    def query(self, addr: int) -> MemoryInfo:
        with self.lock:
            if not (self.last_mem_info is not None and addr in self.last_mem_info):
                self.conn.write_command(Command.COMMAND_QUERY_MEMORY)
                self.conn.write_long(addr)
                self.last_mem_info = self.read_info()

            return self.last_mem_info

    def query_multi(self, start: int, max_count: int) -> List[MemoryInfo]:
        with self.lock:
            self.conn.write_command(Command.COMMAND_QUERY_MEMORY_MULTI)
            self.conn.write_long(start)
            self.conn.write_int(max_count)

            result = []
            for i in range(max_count):
                info = self.read_info()
                result.append(info)
                if info.memory_type == MemoryType.RESERVED:
                    break

            self.conn.read_result()
            return result

    def get_current_pid(self) -> int:
        with self.lock:
            self.conn.write_command(Command.COMMAND_CURRENT_PID)
            pid = self.conn.read_long()
            result = self.conn.read_result()
            if result.failed:
                pid = 0
            return pid

    def get_attached_pid(self) -> int:
        with self.lock:
            self.conn.write_command(Command.COMMAND_GET_ATTACHED_PID)
            pid = self.conn.read_long()
            result = self.conn.read_result()
            assert result.succeeded, "Should never fail"
            return pid

    def get_pids(self) -> List[int]:
        with self.lock:
            self.conn.write_command(Command.COMMAND_GET_PIDS)
            count = self.conn.read_int()
            pids = [self.conn.read_long() for _ in range(count)]

            result = self.conn.read_result()
            assert result.succeeded, f"Failed: {result}"

            return pids

    def get_title_id(self, pid: int) -> int:
        with self.lock:
            self.conn.write_command(Command.COMMAND_GET_TITLEID)
            self.conn.write_long(pid)
            tid = self.conn.read_long()

            result = self.conn.read_result()
            assert result.succeeded, f"Failed: {result}"

            return tid

    def get_current_title_id(self) -> int:
        pid = self.get_current_pid()
        if pid == 0:
            return 0
        return self.get_title_id(pid)

    def poke8(self, addr: int, value: int) -> None:
        with self.lock:
            self.conn.write_command(Command.COMMAND_POKE8)
            self.conn.write_long(addr)
            self.conn.write_byte(value)

            result = self.conn.read_result()
            if result.failed:
                self.conn.read_result()
                raise AssertionError(f"Failed: {result}")

    def poke16(self, addr: int, value: int) -> None:
        with self.lock:
            self.conn.write_command(Command.COMMAND_POKE16)
            self.conn.write_long(addr)
            self.conn.write_short(value)

            result = self.conn.read_result()
            if result.failed:
                self.conn.read_result()
                raise AssertionError(f"Failed: {result}")

    def poke32(self, addr: int, value: int) -> None:
        with self.lock:
            self.conn.write_command(Command.COMMAND_POKE32)
            self.conn.write_long(addr)
            self.conn.write_int(value)

            result = self.conn.read_result()
            if result.failed:
                self.conn.read_result()
                raise AssertionError(f"Failed: {result}")

    def poke64(self, addr: int, value: int) -> None:
        with self.lock:
            self.conn.write_command(Command.COMMAND_POKE64)
            self.conn.write_long(addr)
            self.conn.write_long(value)

            result = self.conn.read_result()
            if result.failed:
                self.conn.read_result()
                raise AssertionError(f"Failed: {result}")

    def peek(self, addr: int, size: int) -> int:
        return int.from_bytes(self.read_mem(addr, size), byteorder="little")

    def peek8(self, addr: int) -> int:
        return self.peek(addr, 1)

    def peek16(self, addr: int) -> int:
        return self.peek(addr, 2)

    def peek32(self, addr: int) -> int:
        return self.peek(addr, 4)

    def peek64(self, addr: int) -> int:
        return self.peek(addr, 8)
