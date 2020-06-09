Notes : These lines in the event my brain goes away... and to avoid net search.

# Trigger scripts

These scripts are on a server to trigger the check and the build of the DB for
Pytt project.
Travis CI do not have specific Cron job so this have to be done remotely.

## Installation

.service and .timer files are user scripts.

Put them in `~/.config/systemd/user/`

.sh where you want, i.e. `~/repositories`

```bash
chmod +x check_eve_res.sh
```

Change path in `check_eve_res.service` line `ExecStart=` to reflect the path.

## Enable

```bash
systemctl --user enable check_eve_res.timer
systemctl --user enable check_eve_res.service
```

## Check

```bash
systemctl --user status check_eve_res.timer
systemctl --user list-timers
```