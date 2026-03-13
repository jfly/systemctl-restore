# systemctl-restore

Systemd aware tool to restore backups.

You're doing everything right, you're doing 3-2-1 backups. You're replacing a
machine and you want to restore some service data from backups.

Enter `systemctl-restore`. It's sort of like the opposite of [`systemctl
clean`](https://www.freedesktop.org/software/systemd/man/latest/systemctl.html#clean%20PATTERN%E2%80%A6). Just point it at a backup of your `/var/lib` directory:

```console
systemctl-restore /backups/var/lib
```

It will compare the contents of this directory to the configured
`StateDirectory` of the systemd services on the machine. Each affected service
will be stopped, have its `StateDirectory` restored, and then the service will
be started back up.
