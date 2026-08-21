#!/bin/bash
systemctl disable --now ssh-forwarder.service

rm /etc/systemd/system/ssh-forwarder.service
rm /usr/local/bin/ssh-forward

systemctl daemon-reload
systemctl reset-failed