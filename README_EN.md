English | [简体中文](README.md)

# ssh-forwarder

Lightweight, zero-dependency persistent multi-host SSH local port-forwarding daemon & CLI powered by `systemd`.
Each forwarding rule runs in its own dedicated `ssh` subprocess and reconnects independently, avoiding head-of-line blocking between large inference payloads and control traffic without multiplexing over `ControlMaster`.

## Installation

```bash
sudo ./install.sh
```

## File Descriptor Limits for High-Concurrency Forwarding

Each forwarded connection consumes file descriptors in both the client `ssh` process and the remote `sshd` daemon. The included `ssh-forwarder.service` sets `LimitNOFILE=65535` on the client side, while remote hosts default to `1024` unless configured by an administrator.

On Ubuntu target hosts running `ssh.service`:

```bash
sudo install -D -m 644 sshd-limits.conf \
  /etc/systemd/system/ssh.service.d/ssh-forwarder-limits.conf
forward_user=ubuntu
printf '%s soft nofile 65535\n%s hard nofile 1048576\n' \
  "$forward_user" "$forward_user" | \
  sudo tee /etc/security/limits.d/90-ssh-forwarder.conf >/dev/null
sudo systemctl daemon-reload
sshd_pid=$(systemctl show ssh.service -p MainPID --value)
sudo prlimit --pid "$sshd_pid" --nofile=65535:1048576
```

## Configuration

Copy [forwards.conf.example](forwards.conf.example) to `forwards.conf` (gitignored). Supports one or more `SSH_HOST=` sections (subsequent rules belong to the most recent `SSH_HOST`), with an optional bind address (`127.0.0.1` by default, or `0.0.0.0`):

```
SSH_HOST=user1@host1
local_port|remote_host|remote_port|description
local_port|remote_host|remote_port|description|0.0.0.0

SSH_HOST=user2@host2
local_port|remote_host|remote_port|description
```

## Usage

```bash
ssh-forward list                                         # List forwarding rules
ssh-forward add 8080 10.0.0.1 80 web                     # Append rule under last SSH_HOST
ssh-forward add --host user@host 8081 127.0.0.1 8000 llm # Add rule under a specific SSH_HOST (--host required if new)
ssh-forward remove 8080                                  # Remove rule (aliases: del, delete)
ssh-forward status                                       # Check systemd status
ssh-forward logs                                         # Follow service logs
```

## Passwordless Key Setup

```bash
./setup-key.sh ~/.ssh
```

## Uninstall

```bash
sudo ./uninstall.sh
```

## Verification

```bash
bash -n ssh-forward install.sh setup-key.sh uninstall.sh
python3 -B -m unittest discover -s tests -v
```

Tests run against local mocks without touching live SSH hosts and verify per-rule subprocess isolation, independent reconnection, clean shutdown without orphan processes, absent-config handling, and `setup-key.sh` alias generation.

## Security

See [SECURITY.md](SECURITY.md).

## License

[MIT](LICENSE)
