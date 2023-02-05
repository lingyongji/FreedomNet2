
# FreedomNet2

#### 介绍
FreedomNet2是一个基于python3开发的，简单的http/https的"上网"工具。
- 
#### Linux安装service(推荐 Debian 11)(default python 3.9)
在线(请确保已安装git)：
- ```wget https://github.com/lingyongji/FreedomNet2/blob/master/install_online_service.sh && bash install_online_service.sh```

离线：（某些vps无法访问git的情况下 ipv6 only）
- 下载 ```https://github.com/lingyongji/FreedomNet2/blob/master/install_offline_service.sh``` 脚本，上传至服务器
- 在脚本所在路径下执行 ```bash install_offline_service.sh``` 命令

#### win本地安装clinet(python 3.10+)
- 安装python3.10 此文档基于 https://www.python.org/ftp/python/3.10.0/python-3.10.0-amd64.exe
- 请确保本地win已安装git
- 安装：```git clone https://github.com/lingyongji/FreedomNet2.git```
- 更新：```git pull```

#### 使用说明
Linux server端 安装既运行
- 停止：```bash stop```
- 运行：```bash run```

Windows client端
- 运行：双击 ```clinet.py```
- 还原配置(若有异常退出的情况)：请双击 ```local/win_setting.py``` 还原系统proxy配置

#### 配置文件说明
代理列表 ```client/proxy_urls_default.txt```
- 运行工具前添加想要走代理的站点顶级域名

追加代理列表 ```client/proxy_urls_append.txt```
- 本文件会随着工具运行自动追加本地不能访问的站点顶级域名(可配置开关 ```client/client.config - auto_append_urls```)
- 这里因为有强迫症，所以追加列表单独记录

客户端配置 ```client/client.config```
```
{
  "local_port": 16866,           -- 本地监听端口
  "service_port": 6866,          -- 服务器端口
  "all_to_vps": false,           -- 是否所有流量走service服务
  "auto_append_urls": true,      -- 是否开启自动追加host（对应local/proxy_urls_append.txt文件）
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
  ]
}
```

服务器配置 ```server/server.config```
```
{
  "service_port": 6866,          -- 监听端口(ipv4)
  "password": "password123"      -- 密码
}
```
