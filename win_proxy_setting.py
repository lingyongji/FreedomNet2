import ctypes
import winreg

INTERNET_OPTION_SETTINGS_CHANGED = 39
INTERNET_OPTION_REFRESH = 37


def set_proxy_config(port):
    host = 'localhost:{0}'.format(str(port))
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Internet Settings', 0, winreg.KEY_WRITE) as key:
            winreg.SetValueEx(key, 'ProxyEnable', 0, winreg.REG_DWORD, 1)
            winreg.SetValueEx(key, 'ProxyServer', 0, winreg.REG_SZ, host)
        refresh()
    except Exception as ex:
        print(ex)


def back_proxy_config():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Internet Settings', 0, winreg.KEY_WRITE) as key:
            winreg.SetValueEx(key, 'ProxyEnable', 0, winreg.REG_DWORD, 0)
            winreg.SetValueEx(key, 'ProxyServer', 0, winreg.REG_SZ, '')
        refresh()
    except Exception as ex:
        print(ex)


def refresh():
    internet_set_option = ctypes.windll.wininet.InternetSetOptionW
    internet_set_option(0, INTERNET_OPTION_SETTINGS_CHANGED, 0, 0)
    internet_set_option(0, INTERNET_OPTION_REFRESH, 0, 0)


if __name__ == '__main__':
    back_proxy_config()
