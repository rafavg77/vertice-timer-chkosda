import serial
import time
import base64

PORT = '/dev/ttyUSB0'
BAUD = 115200

def upload_in_chunks(s, local_path, remote_path, chunk_size=512):
    print(f"Uploading {local_path} -> {remote_path} in {chunk_size}b chunks...")
    with open(local_path, 'rb') as f:
        data = f.read()
    
    init_code = f"with open('{remote_path}', 'wb') as f: pass\r\nimport gc; gc.collect()\r\n\x04"
    s.write(init_code.encode('utf-8'))
    time.sleep(0.3)
    s.read_all()

    for i in range(0, len(data), chunk_size):
        chunk = data[i:i+chunk_size]
        b64 = base64.b64encode(chunk).decode('ascii')
        append_code = f"""
import ubinascii, gc
d = ubinascii.a2b_base64('''{b64}''')
with open('{remote_path}', 'ab') as f:
    f.write(d)
gc.collect()
print('C_{i}')
\x04"""
        s.write(append_code.encode('utf-8'))
        
        start = time.time()
        ok = False
        while time.time() - start < 3:
            if s.in_waiting:
                out = s.read(s.in_waiting)
                if f"C_{i}".encode() in out:
                    ok = True
                    break
            time.sleep(0.02)
        if not ok:
            print(f"Error at chunk {i}")
            return False

    print(f"  SUCCESS: {remote_path} ({len(data)} bytes uploaded)")
    return True

s = serial.Serial(PORT, BAUD, timeout=1)
t0 = time.time()
while time.time() - t0 < 12:
    data = s.read(s.in_waiting or 1).decode('utf-8', 'ignore')
    if 'Servidor Web iniciado' in data:
        break
time.sleep(0.3)
s.write(b'\r\x03\x03\x01') # Raw REPL
time.sleep(0.5)
s.read_all()

# DO NOT delete wifi_config.json - keep saved network!
upload_in_chunks(s, 'mam_link.py', '/mam_link.py')
upload_in_chunks(s, 'ir_tx.py', '/ir_tx.py')
upload_in_chunks(s, 'web_app.py', '/web_app.py')
upload_in_chunks(s, 'main.py', '/main.py')

print("Soft rebooting ESP32...")
s.write(b'\r\x02\r\x04') # Soft reboot
t_boot = time.time()
out_boot = ""
while time.time() - t_boot < 12:
    chunk = s.read(s.in_waiting or 1).decode('utf-8', errors='ignore')
    out_boot += chunk
    if 'Servidor Web iniciado' in out_boot:
        break
print(out_boot)
s.close()
print("Deployment complete!")
