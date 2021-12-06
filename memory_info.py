from enum import Enum


class MemoryType(Enum):
    UNMAPPED = 0x0
    IO = 0x01
    NORMAL = 0x02
    CODE_STATIC = 0x03
    CODE_MUTABLE = 0x04
    HEAP = 0x05
    SHARED = 0x06
    WEIRD_MAPPED = 0x07
    MODULE_CODE_STATIC = 0x08
    MODULE_CODE_MUTABLE = 0x09
    IPC_BUFFER_0 = 0x0A
    MAPPED = 0x0B
    THREAD_LOCAL = 0x0C
    ISOLATED_TRANSFER = 0x0D
    TRANSFER = 0x0E
    PROCESS = 0x0F
    RESERVED = 0x10
    IPC_BUFFER_1 = 0x11
    IPC_BUFFER_3 = 0x12
    KERNEL_STACH = 0x13
    CODE_READ_ONLY = 0x14
    CODE_WRITABLE = 0x15


class MemoryInfo:
    def __init__(self, addr: int, size: int, memory_type: int, permissions: int):
        self.addr = addr
        self.size = size
        self.memory_type = MemoryType(memory_type)
        self.permissions = permissions

    @property
    def next_address(self) -> int:
        return self.addr + self.size

    @property
    def readable(self) -> bool:
        return (self.permissions & 0x1) != 0

    @property
    def writable(self) -> bool:
        return (self.permissions & 0x2) != 0

    @property
    def executable(self) -> bool:
        return (self.permissions & 0x4) != 0

    @property
    def perm_str(self) -> str:
        return f"{'R' if self.readable else '-'}{'W' if self.writable else '-'}{'X' if self.executable else '-'}"

    def __contains__(self, item) -> bool:
        if not isinstance(item, int):
            raise ValueError("item must be an int")

        return self.addr <= item < self.next_address

    def __repr__(self) -> str:
        return f"MemoryInfo(addr=0x{self.addr:08x}, size=0x{self.size:04x}, type={self.memory_type.name}, perm={self.perm_str})"
