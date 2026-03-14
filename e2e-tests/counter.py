import asyncio
import os
import socket
from pathlib import Path

state_dir = Path(os.environ["STATE_DIRECTORY"])

counter_file = state_dir / "counter.txt"
if counter_file.exists():
    count = int(counter_file.read_text())
else:
    count = 0


# Copied from
# <https://gist.github.com/grawity/6e5980981dccf66f554bbebb8cd169fc>
def notify(arg):
    path = os.environ.get("NOTIFY_SOCKET")
    if path:
        if path[0] == "@":
            path = "\0" + path[1:]
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        sock.sendto(arg.encode("utf-8"), path)


async def handle_connection(reader, writer):
    addr = writer.get_extra_info("peername")
    print(f"Received connection from {addr!r}")

    global count
    count += 1
    counter_file.write_text(str(count))
    message = f"You are visitor number {count}"

    print(f"Send: {message!r}")
    writer.write(message.encode())
    await writer.drain()

    print("Close the connection")
    writer.close()
    await writer.wait_closed()


async def main():
    port = os.environ["PORT"]
    server = await asyncio.start_server(handle_connection, "127.0.0.1", port)

    addrs = ", ".join(str(sock.getsockname()) for sock in server.sockets)
    print(f"Serving on {addrs}")

    notify("READY=1")

    async with server:
        await server.serve_forever()


asyncio.run(main())
