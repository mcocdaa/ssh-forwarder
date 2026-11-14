# Security Policy

## Reporting a Vulnerability

Please report security vulnerabilities privately via GitHub Security Advisories or direct maintainer contact instead of opening a public issue.

## Security Practices

- **Configuration privacy**: `forwards.conf` is excluded in `.gitignore` and created with `0600` permissions when initialized via `ssh-forward add`.
- **Bind addresses**: Rules default to `127.0.0.1`; only specify `0.0.0.0` when external network exposure is intentional and protected by firewall rules.
- **Input validation**: `ssh-forward add` validates ports (`1-65535`), bind addresses (`127.0.0.1` / `0.0.0.0`), and rejects `|` delimiters and whitespace in host/target fields.
- **Non-interactive SSH**: Tunnels run with `-o BatchMode=yes` and `-o ExitOnForwardFailure=yes` to fail fast rather than silently listening without active forwarding or hanging on password prompts.
- **SSH key permissions**: `setup-key.sh` enforces `0700` on the SSH directory and `0600` on `~/.ssh/config`.
