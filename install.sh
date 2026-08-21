#!/bin/bash
DIR="$(dirname "$(readlink -e "${BASH_SOURCE[0]}")")"

ln -sfn "$DIR/ssh-forward" /usr/local/bin/ssh-forward
ln -sfn "$DIR/ssh-forwarder.service" /etc/systemd/system/ssh-forwarder.service

systemctl daemon-reload
systemctl enable --now ssh-forwarder
