import json
import os
import socket
import sys
import time
from datetime import datetime
from threading import Thread


class ProxyServer(object):
    def __init__(self):
        self.load_config()
        self.check_logdir()
        self.append_log('proxy start')

    def load_config(self):
        with open('server.config', 'r') as f:
            config = json.load(f)
        self.v4_port = config['v4_port']
        self.v6_port = config['v6_port']
        self.password = config['password'].encode()
        self.log_open = bool(config['log_open'])

    def check_logdir(self):
        if not os.path.exists('log'):
            os.mkdir('log')

    def run(self):
        try:
            proxy_v4 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            proxy_v4.bind(('0.0.0.0', self.v4_port))
            v4_app = Thread(target=self.proxy_run, args=[proxy_v4])
            v4_app.setDaemon(True)
            v4_app.start()
        except Exception as ex:
            self.append_log(ex, sys._getframe().f_code.co_name)

        try:
            proxy_v6 = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
            proxy_v6.bind(('::', self.v6_port))
            v6_app = Thread(target=self.proxy_run, args=[proxy_v6])
            v6_app.setDaemon(True)
            v6_app.start()
        except Exception as ex:
            self.append_log(ex, sys._getframe().f_code.co_name)

        hours = 1
        while True:
            time.sleep(3600)
            self.append_log('proxy run {0} hour(s)'.format(hours))
            hours += 1

    def proxy_run(self, proxy):
        proxy.listen(20)
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
            try:
                local_v4 = socket.socket(
                    socket.AF_INET, socket.SOCK_STREAM)
                local_v6 = socket.socket(
                    socket.AF_INET6, socket.SOCK_STREAM)
                if local_v4.connect_ex((host, port)) == 0:
                    app.sendall(b'1')
                    self.connect_bridge(app, local_v4)
                    if self.log_open:
                        self.append_log(
                            'connect {0} by ipv4'.format(host_addr))
                elif local_v6.connect_ex((host, port)) == 0:
                    app.sendall(b'1')
                    self.connect_bridge(app, local_v6)
                    if self.log_open:
                        self.append_log(
                            'connect {0} by ipv6'.format(host_addr))
                else:
                    app.sendall(b'0')
                    app.close()
                    self.append_log('connect {0} failed'.format(host_addr))
            except Exception as ex:
                app.close()
                local_v4.close()
                local_v6.close()
                self.append_log(ex, sys._getframe().f_code.co_name)

    def check_password(self, app, addr):
        if self.password == app.recv(1024):
            app.sendall(b'1')
            return True
        else:
            app.sendall(b'0')
            app.close()
            self.append_log('{0}:{1} auth failed'.format(addr[0], addr[1]))
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
        with open('log/{0}_proxy.log'.format(dt[0:10]), 'a') as f:
            f.write('{0} | {1} | {2} \n'.format(dt, str(msg), func_name))


if __name__ == "__main__":
    ProxyServer().run()
