import json
import os
import socket
import sys
import time
from datetime import datetime
from threading import Thread

from win_proxy_setting import back_proxy_config, set_proxy_config


class ProxyClinet(object):
    def __init__(self):
        self.load_config()
        self.load_hosts()
        self.check_logdir()
        self.append_log('client start')

    def load_config(self):
        with open('client.config', 'r') as f:
            config = json.load(f)
        self.local_port = config['local_port']
        self.all_to_vps = config['all_to_vps']
        self.vpss = config['vpss']
        self.log_open = bool(config['log_open'])

    def load_hosts(self):
        self.proxy_hosts = []
        with open('proxy_hosts.txt') as f:
            for host in f:
                self.proxy_hosts.append(host.strip())

    def check_logdir(self):
        if not os.path.exists('log'):
            os.mkdir('log')

    def run(self):
        set_proxy_config(self.local_port)
        back_config = Thread(target=self.back_proxy_setting)
        back_config.setDaemon(True)
        back_config.start()

        run_thread = Thread(target=self.run_listen)
        run_thread.setDaemon(True)
        run_thread.start()

        hours = 1
        while True:
            time.sleep(3600)
            self.append_log('app run {0} hour(s)'.format(hours))
            hours += 1

    def back_proxy_setting(self):
        input('input any key to exit\n')
        back_proxy_config()
        self.append_log('client closed')
        import os
        os._exit(0)

    def run_listen(self):
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.bind(('localhost', self.local_port))
        listener.listen(20)

        while True:
            app = listener.accept()
            app_thread = Thread(target=self.app_run, args=[app[0]])
            app_thread.setDaemon(True)
            app_thread.start()

    def app_run(self, app):
        req = app.recv(4096)
        if len(req) == 0:
            app.close()
            return

        host_addr = self.parse_addr(req.decode())
        if not host_addr:
            app.close()
            return

        host = host_addr.split(':')[0]
        port = int(host_addr.split(':')[1])

        req_by_vps = bool(self.all_to_vps)
        if not req_by_vps:
            for ph in self.proxy_hosts:
                if host.find(ph) > -1:
                    req_by_vps = True
                    if self.log_open:
                        self.append_log('req {0} by vps'.format(host))
                    break

        if req_by_vps:
            proxy = self.connect_proxy(host_addr)
            if not proxy:
                self.append_log('connect proxy failed')
                return
            self.connect_bridge(app, proxy, port, req)
        else:
            try:
                local = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                if local.connect_ex((host, port)) == 0:
                    self.connect_bridge(app, local, port, req)
                else:
                    proxy = self.connect_proxy(host_addr)
                    if not proxy:
                        self.append_log('connect proxy failed')
                        return
                    self.connect_bridge(app, proxy, port, req)
                    self.append_proxy_hosts(host)
            except:
                self.append_log('get address failed => {0}'.format(host_addr))

    def parse_addr(self, req):
        try:
            req_items = req.split('\r\n')
            connect_index = req_items[0].find('CONNECT')
            if connect_index < 0:  # http proxy
                host_index = req.find('Host:')
                get_index = req.find('GET http')
                post_index = req.find('POST http')
                if host_index > -1:
                    rn_index = req.find('\r\n', host_index)
                    host = req[host_index+6:rn_index]
                elif get_index > -1 or post_index > -1:
                    host = req.split('/')[2]
                else:
                    self.append_log('host parsing failed => {0}'.format(req))
                    return

                host_items = host.split(':')
                host = host_items[0]
                if len(host_items) == 2:
                    port = host_items[1]
                else:
                    port = 80
            else:  # https proxy
                host = req_items[0][connect_index+8:].split(':')[0]
                port = 443

            host_addr = '{0}:{1}'.format(host, port)
            if self.log_open:
                self.append_log('{0} parsed'.format(host_addr))
            return host_addr
        except Exception as ex:
            self.append_log(ex, sys._getframe().f_code.co_name)

    def connect_proxy(self, host_addr):
        for vps in self.vpss:
            if bool(vps['used']):
                if len(vps['ipv4']) > 0:
                    socket_family = socket.AF_INET
                    vps_ip_port = (vps['ipv4'], vps['v4port'])
                else:
                    socket_family = socket.AF_INET6
                    vps_ip_port = (vps['ipv6'], vps['v6port'])
                proxy = socket.socket(socket_family, socket.SOCK_STREAM)
                if proxy.connect_ex(vps_ip_port) == 0:
                    proxy.sendall(vps['token'].encode())
                    if proxy.recv(1) == b'1':
                        proxy.sendall(host_addr.encode())
                        if proxy.recv(1) == b'1':
                            return proxy
                        else:
                            proxy.close()
                            self.append_log(
                                '{0} connect {1} failed'.format(vps_ip_port, host_addr))
                    else:
                        proxy.close()
                        self.append_log(
                            'auth {0} failed'.format(vps_ip_port))

    def connect_bridge(self, app, proxy, port, req):
        if port == 443:
            app.sendall(b'HTTP/1.0 200 Connection Established\r\n\r\n')
        else:
            proxy.sendall(req)

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

    def append_proxy_hosts(self, host):
        host_items = host.split('.')
        host = '.'.join(host_items[-2:])
        try:
            self.proxy_hosts.index(host)
        except:
            self.proxy_hosts.append(host)
            with open('proxy_hosts.txt', 'a') as f:
                f.write('\n{0}'.format(host))

    def append_log(self, msg, func_name=''):
        dt = str(datetime.now())
        with open('log/{0}_proxy.log'.format(dt[0:10]), 'a') as f:
            f.write('{0} | {1} | {2} \n'.format(dt, str(msg), func_name))


if __name__ == "__main__":
    ProxyClinet().run()
