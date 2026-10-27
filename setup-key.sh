#!/bin/bash
set -euo pipefail

# 用法: setup-key [SSH_DIR] [SSH_HOST]
#   SSH_DIR 默认 ~/.ssh（当前用户）；给 systemd 服务(root)配: sudo ./setup-key /root/.ssh
#   SSH_HOST 可选；若 forwards.conf 存在多个 SSH_HOST 且未传参，会提示选择
# 流程: 读 forwards.conf 的 SSH_HOST -> 生成 ed25519 key -> ssh-copy-id 部署公钥 -> 写 ssh config
# key 使用空 passphrase（适配后台服务）；如需 passphrase 把 -N '' 改为 -N '你的密码'

SSH_DIR="${1:-${SSH_DIR:-$HOME/.ssh}}"
TARGET_HOST="${2:-}"
DIR="$(dirname "$(readlink -e "${BASH_SOURCE[0]}")")"
CONF="$DIR/forwards.conf"

if [[ -n "$TARGET_HOST" ]]; then
    SSH_HOST="$TARGET_HOST"
else
    mapfile -t SSH_HOSTS < <(sed -n 's/^SSH_HOST=//p' "$CONF" | awk '!seen[$0]++')
    [[ ${#SSH_HOSTS[@]} -gt 0 ]] || { echo "错误：$CONF 缺少 SSH_HOST"; exit 1; }
    if (( ${#SSH_HOSTS[@]} == 1 )); then
        SSH_HOST="${SSH_HOSTS[0]}"
    else
        echo "检测到多个 SSH_HOST："
        for i in "${!SSH_HOSTS[@]}"; do
            echo "  $((i + 1))) ${SSH_HOSTS[$i]}"
        done
        default_idx=${#SSH_HOSTS[@]}
        read -r -p "请选择 [1-$default_idx，默认 $default_idx (${SSH_HOSTS[$((default_idx - 1))]})]: " choice
        choice="${choice:-$default_idx}"
        if ! [[ "$choice" =~ ^[0-9]+$ ]] || (( choice < 1 || choice > default_idx )); then
            echo "错误：选择无效"
            exit 1
        fi
        SSH_HOST="${SSH_HOSTS[$((choice - 1))]}"
    fi
fi

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
        echo "Host $HOST_PART"
        echo "    HostName $HOST_PART"
        [[ -n "$USER_PART" ]] && echo "    User $USER_PART"
        echo "    IdentityFile $KEY"
    } >> "$SSH_CONFIG"
    echo "已写入 $SSH_CONFIG"
fi

echo "完成：ssh $HOST_ALIAS"
