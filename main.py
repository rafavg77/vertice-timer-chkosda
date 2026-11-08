import network
import time
import machine
import wifi_mgr
import web_app

print('=== VÉRTICE 24 — INICIO DE SISTEMA ===')

# Siempre inicializar interfaces
ap = network.WLAN(network.AP_IF)
sta = network.WLAN(network.STA_IF)

# Revisar si hay credenciales Wi-Fi guardadas
cfg = wifi_mgr.load_config()
connected = False

if cfg and 'ssid' in cfg and cfg['ssid']:
    print('Intentando conectar a red guardada:', cfg['ssid'])
    sta_ip = wifi_mgr.connect_sta(cfg['ssid'], cfg.get('password', ''), timeout=10)
    if sta_ip:
        connected = True
        web_app.current_mode = 'control'
        web_app.local_ip = sta_ip
        # Si conectó con éxito, APAGAR el AP para no saturar el Wi-Fi
        ap.active(False)
        print('CONEXIÓN EXITOSA! AP apagado.')
        print('Consola activa en red local: http://' + sta_ip)
    else:
        print('No se pudo conectar a la red guardada.')

if not connected:
    # Si no conectó, activar AP abierto (sin contraseña) para modo Setup
    ap.active(True)
    ap.config(essid='Vertice24-Timer', authmode=network.AUTH_OPEN)
    time.sleep(0.5)
    ap_ip = ap.ifconfig()[0]
    web_app.current_mode = 'setup'
    web_app.local_ip = ap_ip
    print('Punto de Acceso abierto emitido para Setup:')
    print('  Red: Vertice24-Timer (abierta, sin clave)')
    print('  IP: http://' + ap_ip)

# Arrancar Servidor Web
web_app.start_server(port=80)
