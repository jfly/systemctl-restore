# systemctl-restore

Systemd aware tool to restore backups.

You're doing everything right, you're doing 3-2-1 backups. You're replacing a
machine and you want to restore some service data from backups.

Enter `systemctl-restore`. It's sort of like the opposite of [`systemctl
clean`](https://www.freedesktop.org/software/systemd/man/latest/systemctl.html#clean%20PATTERN%E2%80%A6).
Just point it at a backup of your machine (it will ask before doing anything
destructive):

```console
$ systemctl-restore /backups/yesterday
```

This compares the contents of this directory to the configured systemd
services on the current system. Using various heuristics (`StateDirectory`, user/group
ownership), it produces a plan to restore the backup (basically, stop affected
services, restore folder(s), start affected services). The plan is just a shell
script which you can read before executing.
