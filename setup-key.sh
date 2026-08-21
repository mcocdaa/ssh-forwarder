#!/bin/bash
set -euo pipefail

# 用法: setup-key [SSH_DIR]
#   SSH_DIR 默认 ~/.ssh（当前用户）；给 systemd 服务(root)配: sudo ./setup-key /root/.ssh
# 流程: 读 forwards.conf 的 SSH_HOST -> 生成 ed25519 key -> ssh-copy-id 部署公钥 -> 写 ssh config
# key 使用空 passphrase（适配后台服务）；如需 passphrase 把 -N '' 改为 -N '你的密码'

SSH_DIR="${1:-${SSH_DIR:-$HOME/.ssh}}"
DIR="$(dirname "$(readlink -e "${BASH_SOURCE[0]}")")"
CONF="$DIR/forwards.conf"

SSH_HOST=$(sed -n 's/^SSH_HOST=//p' "$CONF")
[[ -n "$SSH_HOST" ]] || { echo "错误：$CONF 缺少 SSH_HOST"; exit 1; }

if [[ "$SSH_HOST" == *@* ]]; then
    USER_PART="${SSH_HOST%@*}"
    HOST_PART="${SSH_HOST#*@}"
else
    USER_PART=""
    HOST_PART="$SSH_HOST"
fi

read -r -p "key 文件名（如 id_myhost，将生成于 $SSH_DIR/）: " KEYFILE
[[ -n "$KEYFILE" ]] || { echo "错误：文件名不能为空"; exit 1; }

KEY="$SSH_DIR/$KEYFILE"

mkdir -p "$SSH_DIR"
chmod 700 "$SSH_DIR"

[[ ! -e "$KEY" ]] || { echo "错误：$KEY 已存在"; exit 1; }

ssh-keygen -t ed25519 -N '' -C "$SSH_HOST" -f "$KEY"

if ! ssh-copy-id -i "$KEY.pub" "$SSH_HOST"; then
    echo "错误：公钥部署失败。key 已生成，可手动: ssh-copy-id -i '$KEY.pub' '$SSH_HOST'"
    exit 1
fi

if [[ "$KEYFILE" == id_* ]]; then
    HOST_ALIAS="${KEYFILE#id_}"
else
    HOST_ALIAS="$KEYFILE"
fi

SSH_CONFIG="$SSH_DIR/config"
touch "$SSH_CONFIG"
chmod 600 "$SSH_CONFIG"

if grep -qx "Host $HOST_ALIAS" "$SSH_CONFIG"; then
    echo "config 已存在 Host $HOST_ALIAS，跳过写入"
else
    {
        echo ""
        echo "Host $HOST_ALIAS"
        echo "    HostName $HOST_PART"
        [[ -n "$USER_PART" ]] && echo "    User $USER_PART"
        echo "    IdentityFile $KEY"
    } >> "$SSH_CONFIG"
    echo "已写入 $SSH_CONFIG"
fi

echo "完成：ssh $HOST_ALIAS"
