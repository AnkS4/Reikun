# OCI A1 retry service: install, manage, remove

Files in this bundle:


| File                   | Purpose                                                                                                           |
| ---------------------- | ----------------------------------------------------------------------------------------------------------------- |
| `oci-a1-retry.sh`      | Retries `oci compute instance launch` for an Always Free `VM.Standard.A1.Flex` until capacity appears, then exits |
| `oci-a1-retry.service` | systemd **user** unit that runs the script at boot and restarts it after transient failures                       |


Exit codes of the script: `0` done (VM created or already exists), `1` transient failure (systemd restarts it), `2` fatal (no restart; read the log).

The unit expects the script at `~/REPO/Reikun/local/oci-a1-retry.sh` and logs to `~/logs/oci-a1-retry.log`. Change `ExecStart=` in the unit if you keep it elsewhere.

---



## 1. Prerequisites

- OCI CLI installed and configured with an **API key** (`oci setup config`). Session-token auth expires in about an hour and the script refuses it.
- An SSH public key file (for example `~/.ssh/oci_a1.pub`).
- Your tenancy OCID and the OCID of your **public** subnet.

Quick check that the CLI works:

```bash
oci iam region list --output table
```



## 2. Install

```bash
# 1. Put the script in place
mkdir -p ~/REPO/Reikun/local/oci ~/logs ~/.config/systemd/user
# cp oci-a1-retry.sh ~/REPO/Reikun/local/

# 2. Edit the settings block at the top of the script
nano ~/REPO/Reikun/local/oci-a1-retry.sh
#    COMPARTMENT_ID, SUBNET_ID, SSH_PUB_KEY_FILE, DISPLAY_NAME, OCPUS, MEMORY_GB

# 3. Dry run by hand. Expect "Image: ...", "Availability domains: ...", "attempt 1".
#    Once you see at least one "will retry" line, press Ctrl+C.
bash ~/REPO/Reikun/local/oci/oci-a1-retry.sh

# 4. Install and start the service
cp oci-a1-retry.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now oci-a1-retry.service

# 5. Start at boot even when you are not logged in (REQUIRED for "on boot")
loginctl enable-linger "$USER"
```



## 3. Check status and logs

```bash
systemctl --user status oci-a1-retry.service      # active (running) = still trying
tail -f ~/logs/oci-a1-retry.log                   # live log, Ctrl+C stops watching only
journalctl --user -u oci-a1-retry -f              # systemd's own messages (starts, failures)
loginctl show-user "$USER" -p Linger              # should print Linger=yes
systemctl --user is-enabled oci-a1-retry.service  # enabled = will start at boot
```

What the log lines mean:


| Log line                                                         | Meaning                                                            |
| ---------------------------------------------------------------- | ------------------------------------------------------------------ |
| `attempt N in <AD>` then `no capacity ... will retry`            | Normal: no free A1 host right now                                  |
| `SUCCESS:` plus instance JSON                                    | VM created; the service exits and shows `inactive (dead)`          |
| `SUCCESS: instance already present` / `Instance already present` | A VM named `DISPLAY_NAME` exists, so the script stopped            |
| `FATAL: ...`                                                     | Config or auth problem; the service stays stopped until you fix it |
| `unrecognised error (n/5)`                                       | Unknown error; after 5 in a row the script gives up                |




## 4. Stop, start, restart

```bash
systemctl --user stop oci-a1-retry.service       # stop now (starts again at next boot if enabled)
systemctl --user start oci-a1-retry.service      # start again
systemctl --user restart oci-a1-retry.service    # after editing the script
```

After editing the **unit file**, always run `systemctl --user daemon-reload` first.

## 5. Deactivate (keep files, no autostart)

```bash
systemctl --user disable --now oci-a1-retry.service   # stop and do not start at boot
```

Re-enable later with `systemctl --user enable --now oci-a1-retry.service`.

## 6. Delete everything

```bash
systemctl --user disable --now oci-a1-retry.service
rm -f ~/.config/systemd/user/oci-a1-retry.service
systemctl --user daemon-reload
systemctl --user reset-failed oci-a1-retry.service 2>/dev/null

rm -f ~/REPO/Reikun/local/oci-a1-retry.sh      # the script
rm -f ~/logs/oci-a1-retry.log                  # the log
rm -f ~/.cache/oci-a1-retry.lock               # the lock file

# Only if no other service of yours needs boot-time start without login:
loginctl disable-linger "$USER"
```



## 7. After the VM is created

1. Confirm the VM: OCI Console, Compute, Instances. Note its public IP.
2. Turn the service off so it never runs again:
  ```bash
   systemctl --user disable oci-a1-retry.service
  ```
3. Connect: `ssh -i ~/.ssh/oci_a1 ubuntu@<public_ip>`

**Warning:** if you later terminate or rename that VM while the service is still enabled, the next boot sees no VM named `DISPLAY_NAME` and starts trying to create a new one. Disable the service as soon as you have your VM.

## 8. Troubleshooting


| Problem                                   | Fix                                                                                                                                |
| ----------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| `Active: failed` with `FATAL` in the log  | Fix the cause (OCIDs, key path, auth), then `systemctl --user reset-failed oci-a1-retry` and `systemctl --user start oci-a1-retry` |
| `oci CLI not found in PATH`               | Find it with `which oci`; add its folder to the `Environment=PATH=` line in the unit, then `daemon-reload` and restart             |
| `OCI config uses session-token auth`      | Run `oci setup config` and use an API key profile                                                                                  |
| `no image matched ...`                    | The script prints a table of available Ubuntu images; copy one OCID into `IMAGE_ID` in the script                                  |
| Service not running after reboot          | Check `loginctl show-user "$USER" -p Linger` is `yes` and the unit is `enabled`                                                    |
| `already running (lock ...)`              | Another copy is running (a manual run or the service). Stop it with `pkill -f oci-a1-retry.sh`, then start the service             |
| Nothing happens while the computer sleeps | Suspend pauses the retries. Disable sleep, or run on an always-on machine                                                          |
| Log keeps growing                         | About a few KB per day; truncate with `: > ~/logs/oci-a1-retry.log` if you like                                                    |




## 9. Things to know

- Free A1 capacity in a small or new region (such as eu-madrid-3, which has one availability domain) can stay full for days.
- A smaller request (for example `OCPUS=1`, `MEMORY_GB=6`) may be easier to get; you can resize later, subject to capacity. This is not guaranteed.
- Upgrading to Pay As You Go is widely reported to improve A1 availability; Always Free resources stay free. I have not verified this.
- Always Free totals: 4 OCPU and 24 GB RAM across A1 instances, and 200 GB of block storage.

