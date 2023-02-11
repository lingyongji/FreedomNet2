# python 3.10+

import json
import os
import socket
import platform
import atexit
from datetime import datetime
from threading import Thread
from proxy_setting_win import back_config as win_back_config, set_config as win_set_config
from proxy_setting_linux import back_config as linux_back_config, set_config as linux_set_config

os_name = platform.system().lower()


class ProxyClinet(object):
    def __init__(self):
        self.load_config()
        self.load_proxy_urls()
        self.check_logdir()
        append_log('\n------ client start ------')

    def load_config(self):
        with open('client.config', 'r') as f:
            config = json.load(f)
        self.local_port = config['local_port']
        self.service_port = config['service_port']
        self.all_to_vps = config['all_to_vps']
        self.vpss = config['vpss']
        self.log_open = bool(config['log_open'])
        self.auto_append_urls = bool(config['auto_append_urls'])

    def load_proxy_urls(self):
        self.proxy_urls_default = []
        with open('proxy_urls_default.txt') as f:
            for url in f:
                self.proxy_urls_default.append(url.strip())
        with open('proxy_urls_append.txt') as f:
            for url in f:
                self.proxy_urls_default.append(url.strip())

    def check_logdir(self):
        if not os.path.exists('log'):
            os.mkdir('log')

    def run(self):
        set_proxy_config(self.local_port)

        run_thread = Thread(target=self.run_listen)
        run_thread.daemon = True
        run_thread.start()

        self.control_panel()

    def control_panel(self):
        print('------ FreeNet Client ------')
        print('1.Reload proxy urls')
        print('2.Reload config')
        print('------ Ctrl+C to exit ------')
        action = input('Action:')
        self.actions(action)

    def actions(self, action):
        match action:
            case '1':
                self.load_proxy_urls()
                print('proxy urls reloaded')
            case '2':
                self.load_config()
                print('config reloaded')
            case _:
                print('Unkown action, select again')
        self.control_panel()

    def run_listen(self):
        listener = socket.create_server(
            ('', self.local_port), family=socket.AF_INET6, backlog=128, dualstack_ipv6=True)
        while True:
            app, addr = listener.accept()
            app_thread = Thread(target=self.app_run, args=[app])
            app_thread.daemon = True
            app_thread.start()

    def app_run(self, app):
        try:
            req = app.recv(4096)
            if not req:
                app.close()
                return
        except Exception as ex:
            append_log('recv request failed - {0}'.format(ex))
            return

        website_addr = self.parse_addr(req.decode(errors='ignore'))
        if not website_addr:
            app.close()
            return

        domain = website_addr.split(':')[0]
        port = int(website_addr.split(':')[1])
        addr = (domain, port)

        req_by_vps = bool(self.all_to_vps)
        if not req_by_vps:
            for proxy_host in self.proxy_urls_default:
                if domain.find(proxy_host) > -1:
                    req_by_vps = True
                    if self.log_open:
                        append_log('request {0} by vps'.format(domain))
                    break

        if req_by_vps:
            proxy = self.connect_website_by_proxy(website_addr)
            if proxy:
                self.connect_bridge(app, proxy, port, req)
        else:
            connected = False
            proxy = None
            try:
                proxy = socket.create_connection(addr)
                connected = True
            except Exception as ex:
                append_log(
                    'local connection to {0} failed, try proxy'.format(domain))
            if not connected:
                proxy = self.connect_website_by_proxy(website_addr)
                if proxy:
                    connected = True
                    if self.auto_append_urls:
                        self.append_proxy_urls(domain)
            if connected:
                self.connect_bridge(app, proxy, port, req)
            else:
                app.close()
                if proxy:
                    proxy.close()

    def parse_addr(self, req):
        try:
            req_items = req.split('\r\n')
            connect_index = req_items[0].find('CONNECT')
            # http proxy
            if connect_index < 0:
                host_index = req.find('Host:')
                get_index = req.find('GET http')
                post_index = req.find('POST http')
                if host_index > -1:
                    rn_index = req.find('\r\n', host_index)
                    website_addr = req[host_index+6:rn_index]
                elif get_index > -1 or post_index > -1:
                    website_addr = req.split('/')[2]
                else:
                    append_log(
                        'website_addr parsing failed => {0}'.format(req))
                    return

                website_items = website_addr.split(':')
                domain = website_items[0]
                if len(website_items) == 2:
                    port = website_items[1]
                else:
                    port = 80
            # https proxy
            else:
                domain = req_items[0][connect_index+8:].split(':')[0]
                port = 443

            website_addr = '{0}:{1}'.format(domain, port)
            if self.log_open:
                append_log('{0} parsed'.format(website_addr))
            return website_addr
        except Exception as ex:
            append_log('parse addr failed - {0}'.format(ex))

    def connect_website_by_proxy(self, website_addr):
        host = website_addr.split(':')[0]
        for vps in self.vpss:
            if bool(vps['used']):
                try:
                    vps_addr = (vps['ip'], self.service_port)
                    proxy = socket.create_connection(vps_addr)
                    proxy.sendall(vps['password'].encode())
                    if proxy.recv(1) == b'1':
                        proxy.sendall(website_addr.encode())
                        if proxy.recv(1) == b'1':
                            return proxy
                        else:
                            proxy.close()
                            append_log('{0} connect {1} failed'.format(
                                vps['ip'], host))
                    else:
                        proxy.close()
                        append_log('auth {0} failed'.format(vps_addr))
                except Exception as ex:
                    append_log('connect {0} failed - {1}'.format(vps_addr, ex))
        append_log('connect {0} by all proxy failed'.format(host))

    def connect_bridge(self, app, proxy, port, req):
        try:
            if port == 443:
                app.sendall(b'HTTP/1.0 200 Connection Established\r\n\r\n')
            else:
                proxy.sendall(req)
        except Exception as ex:
            append_log(
                'create bridge failed - {0} | app => {1} | proxy => {2}'.format(ex, app, proxy))
            return

        a2p = Thread(target=self.bridge, args=[app, proxy])
        p2a = Thread(target=self.bridge, args=[proxy, app])
        a2p.daemon = True
        p2a.daemon = True
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

    def append_proxy_urls(self, domain):
        domian_items = domain.split('.')
        domain = '.'.join(domian_items[-2:])
        try:
            self.proxy_urls_default.index(domain)
        except:
            self.proxy_urls_default.append(domain)
            with open('proxy_urls_append.txt', 'a') as f:
                f.write('\n{0}'.format(domain))


def append_log(msg: str, func_name=''):
    dt = str(datetime.now())
    with open('log/{0}.log'.format(dt[0:10]), 'a') as f:
        f.write('{0} | {1} | {2} \n'.format(dt, msg, func_name))


def set_proxy_config(port):
    if os_name == 'windows':
        win_set_config(port)
    elif os_name == 'linux':
        linux_set_config(port)


def back_proxy_config():
    if os_name == 'windows':
        win_back_config()
    elif os_name == 'linux':
        linux_back_config()


if __name__ == "__main__":
    def before_exit():
        back_proxy_config()
        append_log('------ client closed ------')

    atexit.register(before_exit)
    ProxyClinet().run()
