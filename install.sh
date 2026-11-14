#!/bin/bash
set -euo pipefail

SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
DIR="$(cd "$(dirname "$SCRIPT_PATH")" && pwd -P)"

ln -sfn "$DIR/ssh-forward" /usr/local/bin/ssh-forward
ln -sfn "$DIR/ssh-forwarder.service" /etc/systemd/system/ssh-forwarder.service

systemctl daemon-reload
if [[ -f "$DIR/forwards.conf" ]]; then
    systemctl enable --now ssh-forwarder
else
    systemctl enable ssh-forwarder
    echo "提示：未检测到 $DIR/forwards.conf，已启用服务但暂未启动。"
    echo "请使用以下命令添加首条规则并启动服务："
    echo "  ssh-forward add --host user@host 本地端口 目标地址 目标端口 [备注]"
fi
