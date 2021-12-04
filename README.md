
# FreedomNet2

#### 介绍
FreedomNet2是一个基于python3开发的，简单的http/https的"上网"工具。
- 
#### Linux安装(推荐 Debian 11)(default python 3.9)
在线(请确保已安装git)：
- wget https://gitee.com/lingyongji/FreedomNet2/raw/master/install_online.sh && bash install_online.sh

离线：（某些vps无法访问git的情况下）
- 将install_offline_service.sh上传至服务器
- bash install_offline_service.sh

#### win本地安装clinet(python 3.10)
- 安装python3.10 编辑此文档时最新版本为 https://www.python.org/ftp/python/3.10.0/python-3.10.0-amd64.exe
- 请确保已安装git
- (第一次pull)  git clone https://gitee.com/lingyongji/FreedomNet2.git
- (已经pull过)  git pull

#### 使用说明
Linux server端 安装既运行
- 运行：bash run
- 停止：bash stop

win端
- 运行：双击 clinet.py
- 关闭：在控制台中按任意键退出，不要直接关闭
- 还原配置：若直接关闭控制台，请双击 local/win_setting.py 还原系统配置

#### 配置文件说明
站点列表 local/hosts.txt
- 运行工具前添加想要走服务的站点
- 本文件会随着工具运行自动追加本地不能"上网"的站点(可配置开关)

服务器配置 server/server.config

```
{
  "v4_port": 6866,               -- 监听端口(ipv4)
  "v6_port": 6868,               -- 监听端口(ipv6)
  "password": "password123",     -- 密码
  "log_open": true               -- 日志开关（true-全开，false-仅记录报错）
}
```

客户端配置 local/client.config
```
{
  "local_port": 11080,           -- 本地监听端口
  "all_to_vps": false,           -- 是否所有流量走service服务
  "log_open": true,              -- 日志开关（true-全开，false-仅记录报错）  
  "auto_append_hosts": false,    -- 是否开启自动追加host（对应local/hosts.txt文件）
  "hosts": [
    {
      "used": true,              -- 使用开关
      "password": "password123", -- vps密码
      "ip": "0.0.0.0",           -- vps的ip(v4)
    },
    {
      "used": false,
      "password": "password123",
      "ip": "::",                -- vps的ip(v6)
    }
  ],
  "service_port_v4": 6866,       -- ipv4端口
  "service_port_v6": 6866        -- ipv6端口
}
```
