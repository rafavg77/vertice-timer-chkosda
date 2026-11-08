import network
import time
import machine
import wifi_mgr
import web_app

print('=== VÉRTICE 24 — INICIO DE SISTEMA ===')

# LED integrado (GPIO 2) y botón BOOT (GPIO 0, activo en bajo)
led = machine.Pin(2, machine.Pin.OUT, value=0)
boot_btn = machine.Pin(0, machine.Pin.IN, machine.Pin.PULL_UP)

def blink_led(times=10, on_ms=100, off_ms=100):
    for _ in range(times):
        led.value(1)
        time.sleep_ms(on_ms)
        led.value(0)
        time.sleep_ms(off_ms)

# Verificar si el botón BOOT se mantiene presionado al arrancar para restaurar Wi-Fi
if boot_btn.value() == 0:
    print('Botón BOOT detectado en arranque. Mantén presionado 3 segundos para borrar Wi-Fi...')
    t_press = time.ticks_ms()
    reset_triggered = True
    while time.ticks_diff(time.ticks_ms(), t_press) < 3000:
        if boot_btn.value() != 0:
            reset_triggered = False
            break
        led.value(1)
        time.sleep_ms(50)
        led.value(0)
        time.sleep_ms(50)
    if reset_triggered:
        print('¡Restaurando configuración de fábrica y borrando Wi-Fi!')
        wifi_mgr.clear_config()
        blink_led(times=15, on_ms=60, off_ms=60)

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
        blink_led(times=3, on_ms=150, off_ms=150)
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
    blink_led(times=6, on_ms=80, off_ms=80)
    print('Punto de Acceso abierto emitido para Setup:')
    print('  Red: Vertice24-Timer (abierta, sin clave)')
    print('  IP: http://' + ap_ip)

# Arrancar Servidor Web
web_app.start_server(port=80)
