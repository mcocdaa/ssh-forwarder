#!/bin/bash
set -euo pipefail

systemctl disable --now ssh-forwarder.service || true

rm -f /etc/systemd/system/ssh-forwarder.service
rm -f /usr/local/bin/ssh-forward

systemctl daemon-reload
systemctl reset-failed || true
