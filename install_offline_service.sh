#!/bin/sh

ufw allow 6866

mkdir -p /home/FreedomNet2/server
cd /home/FreedomNet2/server

cat >server.config<<EOF
{
  "service_port": 6866,
  "password": "password123"
}
EOF

cat >server.py<<EOF
import json
import os
import socket
import time
from datetime import datetime
from threading import Thread


class ProxyServer(object):
    def __init__(self):
        self.load_config()
        self.check_logdir()
        self.append_log('-------proxy start-------')

    def load_config(self):
        with open('server.config', 'r') as f:
            config = json.load(f)
        self.service_port = config['service_port']
        self.password = config['password'].encode()

    def check_logdir(self):
        if not os.path.exists('log'):
            os.mkdir('log')

    def run(self):
        app = Thread(target=self.proxy_listen)
        app.setDaemon(True)
        app.start()

        hours = 1
        while True:
            time.sleep(3600)
            self.append_log('proxy run {0} hour(s)'.format(hours))
            hours += 1

    def proxy_listen(self):
        proxy = socket.create_server(
            ('', self.service_port), family=socket.AF_INET6, backlog=128, dualstack_ipv6=True)
        while True:
            client, addr = proxy.accept()
            app_thread = Thread(target=self.app_run, args=[client, addr])
            app_thread.setDaemon(True)
            app_thread.start()

    def app_run(self, app, addr):
        if self.check_password(app, addr):
            host_addr = app.recv(4096).decode()
            host = host_addr.split(':')[0]
            port = int(host_addr.split(':')[1])
            proxy = None
            try:
                proxy = socket.create_connection((host, port))
                app.sendall(b'1')
                self.append_log('connect to ' + host)
                self.connect_bridge(app, proxy)
            except Exception as ex:
                app.sendall(b'0')
                app.close()
                if proxy:
                    proxy.close()
                self.append_log(
                    'connect to {0} failed - {1}'.format(host, str(ex)))

    def check_password(self, app, addr):
        if self.password == app.recv(1024):
            app.sendall(b'1')
            return True
        else:
            app.sendall(b'0')
            app.close()
            self.append_log('{0} auth failed'.format(addr))
            return False

    def connect_bridge(self, app, proxy):
        a2p = Thread(target=self.bridge, args=[app, proxy])
        p2a = Thread(target=self.bridge, args=[proxy, app])
        a2p.setDaemon(True)
        p2a.setDaemon(True)
        a2p.start()
        p2a.start()

    def bridge(self, recver, sender):
        try:
            while True:
                data = recver.recv(4096)
                if not data:
                    break
                sender.sendall(data)
        except:
            recver.close()
            sender.close()
        finally:
            recver.close()
            sender.close()

    def append_log(self, msg, func_name=''):
        dt = str(datetime.now())
        with open('log/{0}.log'.format(dt[0:10]), 'a') as f:
            f.write('{0} | {1} | {2} \n'.format(dt, str(msg), func_name))


if __name__ == "__main__":
    ProxyServer().run()
EOF

cat >run<<EOF
python3 server.py > log.txt 2>&1 &
EOF

cat >stop<<EOF
eval \$(ps -ef|grep "[0-9] python3 server.py"|awk '{print "kill "\$2}')
EOF

bash run