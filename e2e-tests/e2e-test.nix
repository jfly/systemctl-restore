{
  self',
  lib,
  pkgs,
  ...
}:
let
  counter = pkgs.writers.writePython3Bin "counter" { } (builtins.readFile ./counter.py);
  port = 2000;
in
{
  nodes.machine = {
    environment.systemPackages = [
      self'.packages.default
    ];

    systemd.services."counter" = {
      wantedBy = [ "multi-user.target" ];
      environment.PORT = toString port;
      serviceConfig = {
        StateDirectory = "counter";
        Type = "notify";
        ExecStart = lib.getExe counter;
      };
    };
  };

  testScript =
    { nodes, ... }:
    /* python */ ''
      import re

      def assert_count(expected_count: int):
        port = ${toString port}
        msg = machine.succeed(f"nc localhost {port} </dev/null")
        assert msg == f"You are visitor number {expected_count}", f"{expected_count=} {msg=}"

      machine.wait_for_unit("counter.service")

      assert_count(1)
      assert_count(2)

      # Backup counter.service's StateDirectory.
      is_dynamic = ${
        if nodes.machine.systemd.services.counter.serviceConfig.DynamicUser or false then
          "True"
        else
          "False"
      }
      if is_dynamic:
          machine.succeed("mkdir -p /tmp/backup/private")
          machine.succeed("cp -r /var/lib/private/counter /tmp/backup/private/counter")
      else:
          machine.succeed("mkdir -p /tmp/backup")
          machine.succeed("cp -r /var/lib/counter /tmp/backup/counter")

      # Make a couple more calls, increasing the visitor count to 4.
      assert_count(3)
      assert_count(4)

      # Restore the backup.
      output = machine.succeed("systemctl-restore /tmp/backup --yes --backup-dir /var/lib.bak-1")
      assert re.search("To restore them: .*systemctl-restore /var/lib.bak", output, re.DOTALL), f"Missing restore command in: {output}"

      # The backup restored the count to 2, so we should see visitor number
      # 3 again.
      assert_count(3)

      # Undo the restore, confirm the visitor count is back to 4 + 1 = 5.
      machine.succeed("systemctl-restore /var/lib.bak-1 --backup-dir /var/lib.bak-2 --yes")
      assert_count(5)
    '';
}
