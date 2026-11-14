# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-11-14

### Added
- Dedicated per-rule SSH subprocess supervision in `ssh-forward` (disabling `ControlMaster` multiplexing and reconnecting failed tunnels independently without disrupting healthy rules).
- Client `LimitNOFILE=65535` in `ssh-forwarder.service` and server-side `sshd-limits.conf` drop-in documentation.
- Automated `unittest` suite (`tests/test_forwarding.py`), `forwards.conf.example`, MIT `LICENSE`, `SECURITY.md`, bilingual documentation (`README.md` / `README_EN.md`), GitHub Actions CI, and Dependabot configuration.
- `del` command alias alongside `remove` / `delete`.

### Changed
- Changed `ssh-forwarder.service` `Restart=always` to `Restart=on-failure` so clean exit `0` when `forwards.conf` is absent does not spin-loop systemd.
- Hardened `install.sh` and `uninstall.sh` with `set -euo pipefail`, quoted paths, and graceful handling when `forwards.conf` has not yet been created.

### Fixed
- Fixed `setup-key.sh` writing `Host $HOST_PART` instead of `Host $HOST_ALIAS` in SSH config and marked `setup-key.sh` executable.
- Fixed `ssh-forward` (`list`, `add`, `remove`/`del`, `run`) failing ungracefully when `forwards.conf` is absent or lacks `SSH_HOST=`; enforced `0600` on newly created `forwards.conf` and rejected `|` / whitespace in rule fields.

## [0.1.0] - 2025-10-27

### Added
- Initial release with `ssh-forward`, `install.sh`, `uninstall.sh`, `setup-key.sh`, and `ssh-forwarder.service`.
