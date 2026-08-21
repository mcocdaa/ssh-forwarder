# ssh-forwarder

基于 SSH 的端口转发工具，用 systemd 服务常驻运行，把本地多个端口转发到内网目标。

## 安装

```bash
sudo ./install.sh
```

## 配置

编辑 `forwards.conf`（此文件已 gitignore，不入库）：

```
SSH_HOST=用户@IP
本地端口|目标地址|目标端口|备注
```

## 使用

```bash
ssh-forward list                       # 查看转发规则
ssh-forward add 8080 10.0.0.1 80 web   # 添加规则
ssh-forward remove 8080                # 删除规则
ssh-forward status                     # 服务状态
ssh-forward logs                       # 查看日志
```

## 配置免密登录

```bash
./setup-key.sh ~/.ssh
```

## 卸载

```bash
sudo ./uninstall.sh
```
