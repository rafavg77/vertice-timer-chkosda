import network
import time
import json
import os

HOSTNAME = 'timer'

try:
    network.hostname(HOSTNAME)
except Exception:
    pass

CONFIG_FILE = '/wifi_config.json'

def unquote(s):
    res = ''
    i = 0
    s = s.replace('+', ' ')
    while i < len(s):
        if s[i] == '%' and i + 2 < len(s):
            try:
                res += chr(int(s[i+1:i+3], 16))
                i += 3
                continue
            except Exception:
                pass
        res += s[i]
        i += 1
    return res

def load_config():
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.loads(f.read())
    except Exception:
        return None

def save_config(ssid, password):
    clean_ssid = unquote(ssid)
    clean_pwd = unquote(password)
    data = {'ssid': clean_ssid, 'password': clean_pwd}
    with open(CONFIG_FILE, 'w') as f:
        f.write(json.dumps(data))
    print('Wi-Fi config guardada para:', clean_ssid)
    return clean_ssid, clean_pwd

def clear_config():
    try:
        os.remove(CONFIG_FILE)
        print('Wi-Fi config eliminada')
    except Exception:
        pass

def scan_networks():
    sta = network.WLAN(network.STA_IF)
    sta.active(True)
    try:
        sta.disconnect()
    except Exception:
        pass
    time.sleep(0.6)
    
    nets = []
    seen = set()
    try:
        raw_nets = sta.scan()
        for n in raw_nets:
            ssid = n[0].decode('utf-8', 'ignore').strip()
            rssi = n[3]
            if ssid and ssid not in seen:
                seen.add(ssid)
                nets.append({'ssid': ssid, 'rssi': rssi})
        nets.sort(key=lambda x: x['rssi'], reverse=True)
    except Exception as e:
        print('Error scan:', e)
    return nets

def connect_sta(ssid, password, timeout=12):
    try:
        network.hostname(HOSTNAME)
    except Exception:
        pass
    sta = network.WLAN(network.STA_IF)
    try:
        sta.config(dhcp_hostname=HOSTNAME)
    except Exception:
        pass
    sta.active(True)
    try:
        sta.disconnect()
        time.sleep(0.3)
    except Exception:
        pass
    
    clean_ssid = unquote(ssid)
    clean_pwd = unquote(password)
    print('Intentando conectar a:', clean_ssid)
    sta.connect(clean_ssid, clean_pwd)
    
    start = time.time()
    while not sta.isconnected() and time.time() - start < timeout:
        time.sleep(0.5)
    
    if sta.isconnected():
        ip = sta.ifconfig()[0]
        print('CONEXION EXITOSA! IP:', ip, '| mDNS: http://' + HOSTNAME + '.local')
        return ip
    else:
        print('TIMEOUT o fallo al conectar con:', clean_ssid)
        return None
