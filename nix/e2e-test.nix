{ lib, ... }:
{
  perSystem =
    { pkgs, self', ... }:
    {
      checks.e2e-test = pkgs.testers.runNixOSTest {
        name = "e2e-test";
        nodes.machine = {
          environment.systemPackages = [
            self'.packages.default
          ];

          systemd.services."counter" = {
            wantedBy = [ "multi-user.target" ];
            serviceConfig = {
              StateDirectory = "counter";
              Type = "notify";
              ExecStart = lib.getExe (
                pkgs.writers.writePython3Bin "counter" { } /* python */ ''
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
                      addr = writer.get_extra_info('peername')
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
                      server = await asyncio.start_server(handle_connection, '127.0.0.1', 2000)

                      addrs = ', '.join(str(sock.getsockname()) for sock in server.sockets)
                      print(f'Serving on {addrs}')

                      notify("READY=1")

                      async with server:
                          await server.serve_forever()

                  asyncio.run(main())
                ''
              );
            };
          };
        };

        testScript = /* python */ ''
          import re

          machine.wait_for_unit("counter.service")

          msg = machine.succeed("nc localhost 2000 </dev/null")
          assert msg == "You are visitor number 1", f"Unexpected message: {msg}"

          msg = machine.succeed("nc localhost 2000 </dev/null")
          assert msg == "You are visitor number 2", f"Unexpected message: {msg}"

          # Backup counter.service's StateDirectory.
          machine.succeed("mkdir /tmp/backup")
          machine.succeed("cp -r /var/lib/counter /tmp/backup")

          # Make a couple more calls, increasing the visitor count to 4.
          msg = machine.succeed("nc localhost 2000 </dev/null")
          assert msg == "You are visitor number 3", f"Unexpected message: {msg}"
          msg = machine.succeed("nc localhost 2000 </dev/null")
          assert msg == "You are visitor number 4", f"Unexpected message: {msg}"

          output = machine.succeed("systemctl-restore /tmp/backup --yes --backup-dir /var/lib.bak-1")

          # Sanity check the output.
          assert re.search("To restore them: .*systemctl-restore /var/lib.bak", output, re.DOTALL), f"Missing restore command in: {output}"

          # The backup restored the count to 2, so we should see visitor number
          # 3 again.
          msg = machine.succeed("nc localhost 2000 </dev/null")
          assert msg == "You are visitor number 3", f"Unexpected message: {msg}"

          # Undo the restore, confirm the visitor count is back to 4 + 1 = 5.
          machine.succeed("systemctl-restore /var/lib.bak-1 --backup-dir /var/lib.bak-2 --yes")
          msg = machine.succeed("nc localhost 2000 </dev/null")
          assert msg == "You are visitor number 5", f"Unexpected message: {msg}"
        '';
      };
    };
}
