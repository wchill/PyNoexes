from debugger import Debugger
from socket_connection import SocketConnection
from memory_info import MemoryType


if __name__ == "__main__":
    print("Entering debugger")
    connection = SocketConnection('10.0.128.113', 7331)
    debugger = Debugger(connection)
    pid = debugger.get_current_pid()
    debugger.attach(pid)
    mis = debugger.query_multi(0, 10000)
    mis = [m for m in mis if m.memory_type not in [MemoryType.UNMAPPED, MemoryType.RESERVED] and m.readable]

    mis = [m for m in mis if m.memory_type != MemoryType.HEAP]

    candidates = []
    for mi in mis:
        mem = debugger.read_mem(mi.addr, mi.size)
        try:
            idx = mem.index(b'\x11\x36\x46\xf9')
            candidates.append(mi.addr + idx)
        except ValueError:
            continue

    addrs = [f"0x{x:08x}" for x in candidates]
    mis2 = [debugger.query(addr) for addr in candidates]

    debugger.dump_mem_regions(mis, ".")
    breakpoint()
    input()
