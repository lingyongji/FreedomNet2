import json
import os
import socket
import sys
from datetime import datetime
from threading import Thread

from win_setting import back_proxy_config, set_proxy_config


class ProxyClinet(object):
    def __init__(self):
        self.load_config()
        self.load_urls()
        self.check_logdir()
        self.append_log('-------client start-------')

    def load_config(self):
        with open('client.config', 'r') as f:
            config = json.load(f)
        self.local_port = config['local_port']
        self.service_port_v4 = config['service_port_v4']
        self.service_port_v6 = config['service_port_v6']
        self.all_to_vps = config['all_to_vps']
        self.vpss = config['vpss']
        self.log_open = bool(config['log_open'])
        self.auto_append_urls = bool(config['auto_append_urls'])

    def load_urls(self):
        self.proxy_urls = []
        with open('urls.txt') as f:
            for url in f:
                self.proxy_urls.append(url.strip())

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
        print('-------FreeNet Client-------')
        print('1.Reload urls')
        print('2.Reload config')
        print('Press Enter to exit client.')
        action = input('Action:')
        self.actions(action)

    def actions(self, action):
        match action:
            case '1':
                self.load_config()
            case '2':
                self.load_urls()
            case '':
                self.stop()
            case _:
                print('Unkown action, select again')
                self.control_panel()

    def stop(self):
        back_proxy_config()
        self.append_log('-------client closed-------')
        import os
        os._exit(0)

    def run_listen(self):
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.bind(('localhost', self.local_port))
        listener.listen(20)

        while True:
            app = listener.accept()
            app_thread = Thread(target=self.app_run, args=[app[0]])
            app_thread.daemon = True
            app_thread.start()

    def app_run(self, app):
        try:
            req = app.recv(4096)
            if len(req) == 0:
                app.close()
                return
        except Exception as ex:
            self.append_log(ex, sys._getframe().f_code.co_name)

        website_addr = self.parse_addr(req.decode(errors='ignore'))
        if not website_addr:
            app.close()
            return

        domain = website_addr.split(':')[0]
        port = int(website_addr.split(':')[1])

        req_by_vps = bool(self.all_to_vps)
        if not req_by_vps:
            for ph in self.proxy_urls:
                if domain.find(ph) > -1:
                    req_by_vps = True
                    if self.log_open:
                        self.append_log('req {0} by vps'.format(domain))
                    break

        if req_by_vps:
            proxy = self.connect_website(website_addr)
            if not proxy:
                self.append_log('connect proxy failed')
                return
            self.connect_bridge(app, proxy, port, req)
        else:
            try:
                local = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                if local.connect_ex((domain, port)) == 0:
                    self.connect_bridge(app, local, port, req)
                else:
                    proxy = self.connect_website(website_addr)
                    if not proxy:
                        self.append_log('connect proxy failed')
                        return
                    self.connect_bridge(app, proxy, port, req)
                    self.append_proxy_urls(domain)
            except:
                self.append_log('get address failed => {0}'.format(website_addr))

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
                    self.append_log('website_addr parsing failed => {0}'.format(req))
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
                self.append_log('{0} parsed'.format(website_addr))
            return website_addr
        except Exception as ex:
            self.append_log(ex, sys._getframe().f_code.co_name)

    def connect_website(self, website_addr):
        for vps in self.vpss:
            if bool(vps['used']):
                isIpv6 = vps['ip'].find(':') != -1
                socket_family = socket.AF_INET6 if isIpv6 else socket.AF_INET
                service_port = self.service_port_v6 if isIpv6 else self.service_port_v4
                vps_ip_port = (vps['ip'], service_port)

                proxy = socket.socket(socket_family, socket.SOCK_STREAM)
                if proxy.connect_ex(vps_ip_port) == 0:
                    proxy.sendall(vps['password'].encode())
                    if proxy.recv(1) == b'1':
                        proxy.sendall(website_addr.encode())
                        if proxy.recv(1) == b'1':
                            return proxy
                        else:
                            proxy.close()
                            self.append_log(
                                '{0} connect {1} failed'.format(vps_ip_port, website_addr))
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
        if self.auto_append_urls:
            domian_items = domain.split('.')
            domain = '.'.join(domian_items[-2:])
            try:
                self.proxy_urls.index(domain)
            except:
                self.proxy_urls.append(domain)
                with open('urls.txt', 'a') as f:
                    f.write('\n{0}'.format(domain))

    def append_log(self, msg, func_name=''):
        dt = str(datetime.now())
        with open('log/{0}_proxy.log'.format(dt[0:10]), 'a') as f:
            f.write('{0} | {1} | {2} \n'.format(dt, str(msg), func_name))


if __name__ == "__main__":
    ProxyClinet().run()
