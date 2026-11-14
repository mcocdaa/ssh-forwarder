[English](README_EN.md) | 简体中文

# ssh-forwarder

基于 SSH 的轻量级端口转发守护工具，用 systemd 服务常驻运行，把本地多个端口转发到内网目标。
每条端口规则使用独立 SSH 连接并独立重连，避免推理大包与控制请求共用一条
SSH 连接产生队头阻塞；不复用 SSH ControlMaster，端口配置格式保持不变。

## 安装

```bash
sudo ./install.sh
```

## 高并发转发的两端限额

每个转发连接会在客户端 `ssh` 和目标主机的 `sshd` 中占用文件句柄。
本项目的 systemd 服务将客户端上限设为 65535，但不能改变远端服务端限额。
若多路推理、训练上传共用一个 SSH 连接，服务端默认的 1024 上限可能耗尽，
出现 `socket: Too many open files`、`channel ... open failed`；此时服务仍可能
显示 active、监听端口也能连接，但请求收不到回复。

在每个需要高并发转发的目标主机上，由管理员安装本仓库的服务端配置。
以下适用于服务名为 `ssh.service` 的 Ubuntu 主机：

```bash
sudo install -D -m 644 sshd-limits.conf \
  /etc/systemd/system/ssh.service.d/ssh-forwarder-limits.conf
# 改成 SSH_HOST 实际使用的登录用户，下面以 ubuntu 为例。
forward_user=ubuntu
printf '%s soft nofile 65535\n%s hard nofile 1048576\n' \
  "$forward_user" "$forward_user" | \
  sudo tee /etc/security/limits.d/90-ssh-forwarder.conf >/dev/null
sudo systemctl daemon-reload
sshd_pid=$(systemctl show ssh.service -p MainPID --value)
sudo prlimit --pid "$sshd_pid" --nofile=65535:1048576
```

drop-in 保证 SSH 服务重启后的限额，PAM 用户配置防止会话初始化时恢复到 1024；
目标主机需已在 `/etc/pam.d/sshd` 中启用 `pam_limits.so`。
`prlimit` 使当前监听进程立即采用该限额，无需重启整个 SSH 服务。
已有转发会话不会继承更新，需要
在客户端重建对应的 `ssh` 子进程。本工具会在子进程退出后
等待 5 秒再重连；仅处理故障规则的子进程，避免中断其他规则的转发。
若目标系统使用 `sshd.service`，请相应替换服务名和 drop-in 目录。

验收时检查新服务端进程 `/proc/<pid>/limits`，并从实际调用方请求转发后的服务、
确认业务成功计数增长。大量网络重传和慢请求会扩大连接积压，提高句柄上限
不能替代对链路拥塞的诊断。不要用不断重启、重复添加端口的方式掩盖问题。

## 配置

参考 [forwards.conf.example](forwards.conf.example) 创建并编辑 `forwards.conf`（此文件已 gitignore，不入库）。支持配置单个或多个 `SSH_HOST` 分段（后续转发规则归属最近声明的 `SSH_HOST`），每条规则可选指定监听地址（默认 `127.0.0.1`，可设为 `0.0.0.0`）：

```
SSH_HOST=用户1@IP1
本地端口|目标地址|目标端口|备注
本地端口|目标地址|目标端口|备注|0.0.0.0

SSH_HOST=用户2@IP2
本地端口|目标地址|目标端口|备注
```

## 使用

```bash
ssh-forward list                                         # 查看转发规则
ssh-forward add 8080 10.0.0.1 80 web                     # 添加规则（追加到当前末尾 SSH_HOST）
ssh-forward add --host user@host 8081 127.0.0.1 8000 llm # 指定 SSH_HOST 添加规则（首次添加必填 --host）
ssh-forward remove 8080                                  # 删除规则（也支持 del / delete）
ssh-forward status                                       # 服务状态
ssh-forward logs                                         # 查看日志
```

## 配置免密登录

```bash
./setup-key.sh ~/.ssh
```

## 卸载

```bash
sudo ./uninstall.sh
```

## 验证

```bash
bash -n ssh-forward install.sh setup-key.sh uninstall.sh
python3 -B -m unittest discover -s tests -v
```

测试使用本地替身，不连接 SSH 主机；检查同主机规则的独立连接、单条连接失败
后的独立重连、停止监督进程后没有遗留子进程，以及无配置文件场景与密钥别名配置。

## 安全

请参阅 [SECURITY.md](SECURITY.md)。

## License

[MIT](LICENSE)
