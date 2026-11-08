import socket
import network
import _thread
import time
import machine
import ir_tx
import wifi_mgr
import mam_link

is_transmitting = False
current_mode = 'control'
local_ip = '0.0.0.0'
boot_btn = machine.Pin(0, machine.Pin.IN, machine.Pin.PULL_UP)
status_led = machine.Pin(2, machine.Pin.OUT, value=0)

HTML_SETUP = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
<title>Vertice24 Timer | Configuración Wi-Fi</title>
<style>
  :root {
    --bg-dark: #000000;
    --glass-card: rgba(28, 28, 30, 0.75);
    --glass-border: rgba(255, 255, 255, 0.12);
    --text-primary: #FFFFFF;
    --text-secondary: rgba(235, 235, 245, 0.6);
    --apple-blue: #0A84FF;
    --apple-green: #30D158;
    --apple-red: #FF453A;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", sans-serif; -webkit-tap-highlight-color: transparent; }
  body {
    background-color: var(--bg-dark);
    color: var(--text-primary);
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 1.5rem 1rem;
    background-image: radial-gradient(circle at 50% 20%, rgba(10, 132, 255, 0.2) 0%, transparent 70%);
  }
  .card {
    background: var(--glass-card);
    backdrop-filter: blur(25px) saturate(180%);
    -webkit-backdrop-filter: blur(25px) saturate(180%);
    border: 1px solid var(--glass-border);
    border-radius: 22px;
    width: 100%;
    max-width: 380px;
    padding: 2rem 1.5rem;
    box-shadow: 0 16px 40px rgba(0, 0, 0, 0.6);
    text-align: center;
  }
  .icon-wrap {
    width: 56px;
    height: 56px;
    border-radius: 50%;
    background: rgba(10, 132, 255, 0.15);
    border: 1px solid rgba(10, 132, 255, 0.3);
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 1.8rem;
    margin-bottom: 1rem;
  }
  h1 { font-size: 1.45rem; font-weight: 700; letter-spacing: -0.02em; margin-bottom: 0.35rem; }
  p.desc { font-size: 0.85rem; color: var(--text-secondary); margin-bottom: 1.5rem; line-height: 1.4; }
  .field { text-align: left; margin-bottom: 1rem; }
  .field-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.4rem; }
  label { font-size: 0.8rem; font-weight: 600; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.04em; }
  .btn-rescan { background: none; border: none; color: var(--apple-blue); font-size: 0.75rem; font-weight: 600; cursor: pointer; }
  select, input[type="text"], input[type="password"] {
    width: 100%;
    height: 48px;
    background: rgba(0, 0, 0, 0.5);
    border: 1px solid var(--glass-border);
    border-radius: 12px;
    color: var(--text-primary);
    padding: 0 0.85rem;
    font-size: 1rem;
    outline: none;
  }
  select:focus, input:focus { border-color: var(--apple-blue); }
  .btn-submit {
    width: 100%;
    height: 52px;
    background: var(--apple-blue);
    border: none;
    border-radius: 14px;
    color: white;
    font-size: 1.05rem;
    font-weight: 600;
    cursor: pointer;
    margin-top: 0.75rem;
    transition: transform 0.1s ease;
    box-shadow: 0 4px 16px rgba(10, 132, 255, 0.35);
  }
  .btn-submit:active { transform: scale(0.97); }
  #status_setup { margin-top: 1rem; font-size: 0.9rem; min-height: 1.4rem; line-height: 1.4; }
  .success-box {
    margin-top: 1rem;
    padding: 1rem;
    background: rgba(48, 209, 88, 0.15);
    border: 1px solid rgba(48, 209, 88, 0.3);
    border-radius: 14px;
    text-align: center;
  }
  .btn-go {
    display: block;
    margin-top: 0.75rem;
    padding: 0.75rem;
    background: var(--apple-green);
    color: black;
    font-weight: 700;
    text-decoration: none;
    border-radius: 10px;
  }
</style>
</head>
<body>
<div class="card">
  <div class="icon-wrap">📶</div>
  <h1>Vertice24 Timer</h1>
  <p class="desc">Selecciona la red Wi-Fi para acceder a la consola del Vertice24 Timer.</p>

  <form id="wifi_form" onsubmit="connectWifi(event)">
    <div class="field">
      <div class="field-header">
        <label>Red Wi-Fi</label>
        <button type="button" class="btn-rescan" onclick="doScan()">🔄 Actualizar</button>
      </div>
      <select id="ssid_select" onchange="checkOther(this)">
        <option value="" disabled selected>Buscando redes...</option>
      </select>
      <input type="text" id="ssid_custom" placeholder="Nombre de red manual" style="display:none; margin-top: 0.5rem;">
    </div>

    <div class="field">
      <label>Contraseña</label>
      <input type="password" id="wifi_pass" placeholder="Ingresa la clave">
    </div>

    <button type="submit" class="btn-submit" id="btn_conn">Conectar</button>
  </form>

  <div id="status_setup"></div>
</div>

<script>
function doScan() {
  const sel = document.getElementById('ssid_select');
  sel.innerHTML = '<option value="" disabled selected>Escaneando redes...</option>';
  fetch('/scan')
    .then(r => r.json())
    .then(nets => {
      sel.innerHTML = '<option value="" disabled>Selecciona una red detectada</option>';
      nets.forEach(n => {
        const opt = document.createElement('option');
        opt.value = n.ssid;
        opt.innerText = n.ssid + ' (' + n.rssi + ' dBm)';
        sel.appendChild(opt);
      });
      if (nets.length > 0) {
        sel.selectedIndex = 1;
      }
      const customOpt = document.createElement('option');
      customOpt.value = '__custom__';
      customOpt.innerText = '➕ Otra red no listada...';
      sel.appendChild(customOpt);
    })
    .catch(e => {
      sel.innerHTML = '<option value="__custom__">Ingresar red manual</option>';
      document.getElementById('ssid_custom').style.display = 'block';
    });
}

doScan();

function checkOther(sel) {
  const cust = document.getElementById('ssid_custom');
  if (sel.value === '__custom__') {
    cust.style.display = 'block';
    cust.focus();
  } else {
    cust.style.display = 'none';
  }
}

function connectWifi(e) {
  e.preventDefault();
  const sel = document.getElementById('ssid_select');
  let ssid = sel.value;
  if (ssid === '__custom__') {
    ssid = document.getElementById('ssid_custom').value.trim();
  }
  const pwd = document.getElementById('wifi_pass').value;
  if (!ssid) {
    alert('Selecciona o ingresa una red');
    return;
  }

  const st = document.getElementById('status_setup');
  const btn = document.getElementById('btn_conn');
  st.innerHTML = '<span style="color:#FF9F0A;">Conectando a ' + ssid + '... Espera unos segundos.</span>';
  btn.disabled = true;

  fetch('/save-wifi?ssid=' + encodeURIComponent(ssid) + '&pwd=' + encodeURIComponent(pwd))
    .then(r => r.text())
    .then(resp => {
      if (resp.startsWith('OK:')) {
        const ip = resp.substring(3);
        st.innerHTML = '<div class="success-box"><div style="font-weight:700; color:#30D158;">¡Conectado exitosamente!</div><div style="font-size:0.85rem; color:#EBEBF5; margin-top:4px;">El punto de acceso se apagará. Conéctate a tu Wi-Fi y abre la consola:</div><a href="' + ip + '" class="btn-go">Abrir Consola (' + ip + ')</a></div>';
        document.getElementById('wifi_form').style.display = 'none';
      } else {
        st.innerHTML = '<span style="color:#FF453A;">' + resp + '</span>';
        btn.disabled = false;
      }
    })
    .catch(err => {
      st.innerHTML = '<span style="color:#FF9F0A;">Procesado. Conéctate a tu Wi-Fi habitual.</span>';
    });
}
</script>
</body>
</html>
"""

HTML_CONTROL = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
<title>Vertice24 Timer</title>
<style>
  :root {
    --bg-dark: #000000;
    --glass-card: rgba(28, 28, 30, 0.72);
    --glass-border: rgba(255, 255, 255, 0.12);
    --text-primary: #FFFFFF;
    --text-secondary: rgba(235, 235, 245, 0.6);
    --apple-blue: #0A84FF;
    --apple-indigo: #5E5CE6;
    --apple-orange: #FF9F0A;
    --apple-purple: #BF5AF2;
    --apple-teal: #64D2FF;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", sans-serif; -webkit-tap-highlight-color: transparent; }
  body {
    background-color: var(--bg-dark);
    color: var(--text-primary);
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: calc(env(safe-area-inset-top) + 1.25rem) 1rem calc(env(safe-area-inset-bottom) + 1.5rem);
    background-image: radial-gradient(circle at 50% 0%, rgba(10, 132, 255, 0.15) 0%, transparent 60%);
  }
  .app-container { width: 100%; max-width: 390px; display: flex; flex-direction: column; gap: 1rem; }
  .top-bar { display: flex; justify-content: space-between; align-items: center; padding: 0 4px; }
  .brand-badge {
    display: inline-flex; align-items: center; gap: 6px; padding: 4px 12px;
    border-radius: 999px; background: rgba(255, 255, 255, 0.08); border: 1px solid var(--glass-border);
    font-size: 0.75rem; font-weight: 600; color: var(--text-secondary); text-transform: uppercase;
  }
  .pulse-dot { width: 6px; height: 6px; border-radius: 50%; background: #30D158; box-shadow: 0 0 8px #30D158; }
  .btn-wifi-config {
    background: rgba(255, 255, 255, 0.08); border: 1px solid var(--glass-border); color: var(--text-secondary);
    padding: 4px 10px; border-radius: 999px; font-size: 0.75rem; text-decoration: none; font-weight: 500;
    cursor: pointer;
  }
  .top-actions { display: flex; align-items: center; gap: 6px; }

  /* Modal MAM */
  .modal-overlay {
    display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(0, 0, 0, 0.75); backdrop-filter: blur(15px); -webkit-backdrop-filter: blur(15px);
    z-index: 100; align-items: center; justify-content: center; padding: 1rem;
  }
  .modal-overlay.active { display: flex; }
  .modal-card {
    background: var(--glass-card); border: 1px solid var(--glass-border); border-radius: 20px;
    width: 100%; max-width: 360px; padding: 1.25rem; display: flex; flex-direction: column; gap: 0.8rem;
    box-shadow: 0 20px 40px rgba(0, 0, 0, 0.6);
  }
  .modal-header { display: flex; justify-content: space-between; align-items: center; }
  .modal-title { font-size: 0.95rem; font-weight: 700; color: #FFF; }
  .modal-close { background: none; border: none; color: var(--text-secondary); font-size: 1.2rem; cursor: pointer; padding: 0 4px; }
  .mam-chip { font-size: 0.7rem; font-weight: 600; padding: 2px 9px; border-radius: 999px; background: rgba(255,255,255,0.08); color: var(--text-secondary); }
  .mam-chip.ok { background: rgba(48,209,88,0.18); color: #30D158; }
  .mam-chip.err { background: rgba(255,69,58,0.18); color: #FF453A; }
  .mam-input {
    width: 100%; height: 42px; background: rgba(0,0,0,0.5); border: 1px solid var(--glass-border);
    border-radius: 12px; color: var(--text-primary); font-size: 0.85rem; padding: 0 0.75rem;
    font-family: ui-monospace, "SF Mono", monospace;
  }
  .mam-save {
    background: var(--apple-blue); border: none; color: #FFF; border-radius: 12px; height: 42px;
    font-size: 0.9rem; font-weight: 600; cursor: pointer; width: 100%;
  }
  .mam-toggle { font-size: 0.8rem; color: var(--text-secondary); display: flex; align-items: center; gap: 0.5rem; }
  .header { text-align: center; }
  h1 { font-size: 1.65rem; font-weight: 700; letter-spacing: -0.03em; }
  .subtitle { font-size: 0.85rem; color: var(--text-secondary); margin-top: 2px; }

  .display-card {
    background: var(--glass-card); backdrop-filter: blur(25px) saturate(180%); -webkit-backdrop-filter: blur(25px) saturate(180%);
    border: 1px solid var(--glass-border); border-radius: 20px; padding: 1.25rem; text-align: center;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
  }
  .timer-digits {
    font-size: 3.5rem; font-weight: 700; font-family: ui-monospace, "SF Mono", monospace;
    letter-spacing: -0.02em; font-variant-numeric: tabular-nums;
  }
  .status-text { font-size: 0.85rem; color: var(--text-secondary); margin-top: 0.25rem; min-height: 1.2rem; }

  .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; }
  .btn {
    border: none; border-radius: 16px; min-height: 58px; padding: 0.75rem; cursor: pointer;
    font-size: 1.05rem; font-weight: 600; display: flex; flex-direction: column; align-items: center;
    justify-content: center; user-select: none; transition: transform 0.12s ease, opacity 0.2s ease;
  }
  .btn:active:not(:disabled) { transform: scale(0.96); filter: brightness(0.85); }
  .btn:disabled { opacity: 0.45; cursor: not-allowed; }
  .btn-tag { font-size: 0.75rem; font-weight: 400; opacity: 0.8; margin-top: 2px; }

  .btn-1m { background: var(--apple-blue); color: #FFF; box-shadow: 0 4px 16px rgba(10, 132, 255, 0.3); }
  .btn-3m { background: var(--apple-indigo); color: #FFF; box-shadow: 0 4px 16px rgba(94, 92, 230, 0.3); }
  .btn-5m { background: var(--apple-orange); color: #FFF; box-shadow: 0 4px 16px rgba(255, 159, 10, 0.3); }
  .btn-10m { background: var(--apple-purple); color: #FFF; box-shadow: 0 4px 16px rgba(191, 90, 242, 0.3); }

  .btn-play { background: rgba(255, 255, 255, 0.12); border: 1px solid var(--glass-border); color: var(--apple-teal); }
  .btn-mute { background: rgba(255, 255, 255, 0.08); border: 1px solid var(--glass-border); color: var(--text-secondary); }
  .btn-ret {
    grid-column: span 2; background: rgba(255, 255, 255, 0.15); border: 1px solid rgba(255, 255, 255, 0.2);
    color: var(--text-primary); font-size: 1.05rem; min-height: 54px;
  }

  .custom-card {
    background: rgba(28, 28, 30, 0.5); border: 1px solid var(--glass-border); border-radius: 18px;
    padding: 0.9rem; display: flex; flex-direction: column; gap: 0.6rem;
  }
  .custom-title { font-size: 0.78rem; font-weight: 600; text-transform: uppercase; color: var(--text-secondary); text-align: center; }
  .custom-row { display: flex; align-items: center; justify-content: center; gap: 0.5rem; }
  .time-input {
    width: 70px; height: 44px; background: rgba(0, 0, 0, 0.5); border: 1px solid var(--glass-border);
    border-radius: 10px; color: var(--text-primary); font-size: 1.2rem; font-weight: 600; text-align: center;
    font-family: ui-monospace, "SF Mono", monospace;
  }
  .btn-start-custom {
    background: rgba(255, 255, 255, 0.12); border: 1px solid var(--glass-border); color: var(--text-primary);
    border-radius: 12px; min-height: 44px; font-size: 0.95rem; font-weight: 600; cursor: pointer;
  }
  .btn-start-custom:disabled { opacity: 0.45; cursor: not-allowed; }
</style>
</head>
<body>
<div class="app-container">
  <div class="top-bar">
    <div class="brand-badge"><span class="pulse-dot"></span> Vertice24 Timer</div>
    <div class="top-actions">
      <button onclick="openMamModal()" class="btn-wifi-config" id="top_mam_btn">☁️ MAM: ...</button>
      <a href="/setup" class="btn-wifi-config">⚙️ Wi-Fi</a>
    </div>
  </div>

  <div class="header">
    <h1>Vertice24 Timer</h1>
    <p class="subtitle">Control Infrarrojo de Temporizador</p>
  </div>

  <div class="display-card">
    <div class="timer-digits" id="live_timer">--:--</div>
    <div class="status-text" id="status_msg">Listo para programar</div>
  </div>

  <div class="grid">
    <button class="btn btn-1m" onclick="triggerTimer(1, 0)">1 Minuto<span class="btn-tag">01:00</span></button>
    <button class="btn btn-3m" onclick="triggerTimer(3, 0)">3 Minutos<span class="btn-tag">03:00</span></button>
    <button class="btn btn-5m" onclick="triggerTimer(5, 0)">5 Minutos<span class="btn-tag">05:00</span></button>
    <button class="btn btn-10m" onclick="triggerTimer(10, 0)">10 Minutos<span class="btn-tag">10:00</span></button>
    <button class="btn btn-play" onclick="triggerAction('play', 'Play / Pausa')">⏸️ Play / Pausa</button>
    <button class="btn btn-mute" onclick="triggerAction('mute', 'Silenciar Alarma')">🔇 Silenciar</button>
    <button class="btn btn-ret" onclick="triggerAction('ret', 'Regresando a la hora...')">🕒 Regresar a Hora Normal</button>
  </div>

  <div class="custom-card">
    <div class="custom-title">Temporizador Personalizado</div>
    <div class="custom-row">
      <input type="number" class="time-input" id="inp_m" min="0" max="99" value="2" placeholder="00">
      <span style="font-weight:bold; color:var(--text-secondary);">:</span>
      <input type="number" class="time-input" id="inp_s" min="0" max="59" value="0" placeholder="00">
    </div>
    <button class="btn-start-custom" onclick="triggerCustom()">Iniciar Temporizador</button>
  </div>
</div>

<!-- Modal Servidor MAM -->
<div class="modal-overlay" id="mam_modal" onclick="if(event.target===this)closeMamModal()">
  <div class="modal-card">
    <div class="modal-header">
      <div style="display:flex; align-items:center; gap:8px;">
        <span class="modal-title">Servidor MAM</span>
        <span class="mam-chip" id="mam_chip">...</span>
      </div>
      <button class="modal-close" onclick="closeMamModal()">&times;</button>
    </div>
    <div style="font-size:0.75rem; color:var(--text-secondary);">
      Ingresa la URL base de tu servidor MAM (ej. <code>http://mam.vertice24.com</code>). Los endpoints de sincronización ya están integrados.
    </div>
    <input type="text" class="mam-input" id="mam_url" placeholder="http://mam.colli.co" autocapitalize="off" autocorrect="off" spellcheck="false">
    <label class="mam-toggle">
      <input type="checkbox" id="mam_enabled" checked> Sincronizar automáticamente con MAM
    </label>
    <button class="mam-save" id="mam_save" onclick="saveMam()">Guardar y Conectar</button>
  </div>
</div>

<script>
let countdownInterval = null;
let remainingSeconds = 0;
let isBusy = false;

function setButtonsDisabled(disabled) {
  isBusy = disabled;
  document.querySelectorAll('button').forEach(b => b.disabled = disabled);
}

function formatTime(s) {
  const m = Math.floor(s / 60);
  const sec = s % 60;
  return (m < 10 ? '0' : '') + m + ':' + (sec < 10 ? '0' : '') + sec;
}

function startLocalTimer(totalSec) {
  clearInterval(countdownInterval);
  remainingSeconds = totalSec;
  const disp = document.getElementById('live_timer');
  disp.innerText = formatTime(remainingSeconds);
  
  countdownInterval = setInterval(() => {
    remainingSeconds--;
    if (remainingSeconds <= 0) {
      clearInterval(countdownInterval);
      disp.innerText = '00:00';
      document.getElementById('status_msg').innerText = '¡Tiempo concluido!';
      document.getElementById('status_msg').style.color = '#FF453A';
    } else {
      disp.innerText = formatTime(remainingSeconds);
    }
  }, 1000);
}

function triggerTimer(m, s) {
  if (isBusy) return;
  if (navigator.vibrate) navigator.vibrate(10);
  clearInterval(countdownInterval);
  const disp = document.getElementById('live_timer');
  const st = document.getElementById('status_msg');
  disp.innerText = formatTime(m * 60 + s);
  st.innerText = 'Programando reloj por IR (~10s)...';
  st.style.color = '#FF9F0A';
  setButtonsDisabled(true);
  
  fetch('/timer?m=' + m + '&s=' + s)
    .then(r => r.text())
    .then(msg => {
      st.innerText = msg;
      st.style.color = '#30D158';
      startLocalTimer(m * 60 + s);
      setButtonsDisabled(false);
    })
    .catch(e => {
      st.innerText = 'Error de conexión';
      st.style.color = '#FF453A';
      setButtonsDisabled(false);
    });
}

function triggerAction(action, label) {
  if (isBusy) return;
  if (navigator.vibrate) navigator.vibrate(10);
  const st = document.getElementById('status_msg');
  st.innerText = label;
  st.style.color = '#64D2FF';
  setButtonsDisabled(true);
  
  if (action === 'ret') {
    clearInterval(countdownInterval);
    document.getElementById('live_timer').innerText = '--:--';
  }
  fetch('/' + action)
    .then(r => r.text())
    .then(msg => {
      st.innerText = msg;
      st.style.color = '#30D158';
      setTimeout(() => setButtonsDisabled(false), 1500);
    })
    .catch(e => {
      st.innerText = 'Error de conexión';
      st.style.color = '#FF453A';
      setButtonsDisabled(false);
    });
}

function triggerCustom() {
  const m = parseInt(document.getElementById('inp_m').value) || 0;
  const s = parseInt(document.getElementById('inp_s').value) || 0;
  if (m === 0 && s === 0) { alert('Ingresa al menos 1 segundo'); return; }
  triggerTimer(m, s);
}

function renderMam(d) {
  const chip = document.getElementById('mam_chip');
  const topBtn = document.getElementById('top_mam_btn');
  const inp = document.getElementById('mam_url');
  if (document.activeElement !== inp && d.url) inp.value = d.url;
  document.getElementById('mam_enabled').checked = d.enabled;
  if (!d.enabled) {
    if (chip) { chip.className = 'mam-chip'; chip.innerText = 'Desactivado'; }
    if (topBtn) { topBtn.innerText = '☁️ MAM: OFF'; topBtn.style.color = 'var(--text-secondary)'; }
  } else if (d.linked) {
    if (chip) { chip.className = 'mam-chip ok'; chip.innerText = 'Conectado'; }
    if (topBtn) { topBtn.innerText = '☁️ MAM: Online'; topBtn.style.color = '#30D158'; }
  } else {
    if (chip) { chip.className = 'mam-chip err'; chip.innerText = d.error ? 'Sin conexión' : 'Conectando...'; }
    if (topBtn) { topBtn.innerText = '☁️ MAM: Sin conexión'; topBtn.style.color = '#FF453A'; }
  }
}

function openMamModal() {
  document.getElementById('mam_modal').classList.add('active');
}

function closeMamModal() {
  document.getElementById('mam_modal').classList.remove('active');
}

function syncTimerState(t) {
  if (!t) return;
  const disp = document.getElementById('live_timer');
  const st = document.getElementById('status_msg');
  if (t.status === 'programming') {
    if (countdownInterval) { clearInterval(countdownInterval); countdownInterval = null; }
    disp.innerText = formatTime(t.total);
    disp.style.color = '#FF9F0A';
    st.innerText = '⏳ Programando reloj por IR (~10s)...';
    st.style.color = '#FF9F0A';
    setButtonsDisabled(true);
  } else if (t.status === 'running') {
    disp.style.color = '#30D158';
    st.innerText = 'Temporizador activo';
    st.style.color = '#30D158';
    setButtonsDisabled(false);
    if (!countdownInterval || Math.abs(remainingSeconds - t.rem) > 1) {
      startLocalTimer(t.rem);
    }
  } else if (t.status === 'ended') {
    if (countdownInterval) { clearInterval(countdownInterval); countdownInterval = null; }
    disp.innerText = '00:00';
    disp.style.color = '#FF453A';
    st.innerText = '¡Tiempo concluido!';
    st.style.color = '#FF453A';
    setButtonsDisabled(false);
  } else if (t.status === 'idle') {
    if (countdownInterval) {
      clearInterval(countdownInterval);
      countdownInterval = null;
      disp.innerText = '--:--';
      disp.style.color = '#FFFFFF';
      st.innerText = 'Listo para transmitir';
      st.style.color = 'var(--text-secondary)';
      setButtonsDisabled(false);
    }
  }
}

function loadMam() {
  fetch('/mam-status').then(r => r.json()).then(d => {
    renderMam(d);
    if (d && d.timer) syncTimerState(d.timer);
  }).catch(() => {});
}

function saveMam() {
  const url = encodeURIComponent(document.getElementById('mam_url').value.trim());
  const en = document.getElementById('mam_enabled').checked ? '1' : '0';
  const btn = document.getElementById('mam_save');
  btn.innerText = 'Guardando...';
  fetch('/mam-save?url=' + url + '&enabled=' + en)
    .then(r => r.json())
    .then(d => {
      renderMam(d);
      btn.innerText = '¡Guardado!';
      setTimeout(() => {
        btn.innerText = 'Guardar y Conectar';
        closeMamModal();
      }, 700);
    })
    .catch(() => {
      btn.innerText = 'Error al guardar';
      setTimeout(() => btn.innerText = 'Guardar y Conectar', 1500);
    });
}

loadMam();
setInterval(loadMam, 1500);
</script>
</body>
</html>
"""

active_timer = {
    'running': False,
    'total_s': 0,
    'started_at_ms': 0,
    'programming': False,
}

def _get_timer_state():
    if active_timer['programming']:
        return {'status': 'programming', 'rem': active_timer['total_s'], 'total': active_timer['total_s']}
    if active_timer['running']:
        elapsed_s = time.ticks_diff(time.ticks_ms(), active_timer['started_at_ms']) // 1000
        rem = active_timer['total_s'] - elapsed_s
        if rem <= 0:
            active_timer['running'] = False
            return {'status': 'ended', 'rem': 0, 'total': active_timer['total_s']}
        return {'status': 'running', 'rem': rem, 'total': active_timer['total_s']}
    return {'status': 'idle', 'rem': 0, 'total': 0}

def _do_countdown(m, s):
    global is_transmitting
    if is_transmitting:
        return
    try:
        is_transmitting = True
        active_timer['total_s'] = m * 60 + s
        active_timer['programming'] = True
        active_timer['running'] = False
        ir_tx.countdown(m, s)
        active_timer['started_at_ms'] = time.ticks_ms()
        active_timer['programming'] = False
        active_timer['running'] = True
    except Exception as e:
        print('Error countdown:', e)
        active_timer['programming'] = False
        active_timer['running'] = False
    finally:
        is_transmitting = False

def _do_action(act):
    global is_transmitting
    if is_transmitting:
        return
    try:
        is_transmitting = True
        if act == 'ret':
            ir_tx.return_to_clock()
            active_timer['running'] = False
            active_timer['programming'] = False
            active_timer['total_s'] = 0
        elif act == 'play':
            ir_tx.send(ir_tx.CODES['PLAY1'])
        elif act == 'mute':
            ir_tx.send(ir_tx.CODES['MUTE'])
    except Exception as e:
        print('Error action:', e)
    finally:
        is_transmitting = False

def _mam_exec():
    """Run the command fetched by the MAM worker thread (IR must stay on the main thread)."""
    cmd = mam_link.inbox
    mam_link.inbox = None
    if not cmd:
        return
    seq = cmd.get('seq')
    name = cmd.get('cmd')
    if seq == mam_link.state['last_seq']:
        return
    mam_link.state['last_seq'] = seq
    print('MAM cmd:', name, seq)
    if name == 'timer':
        _do_countdown(int(cmd.get('m', 1)), int(cmd.get('s', 0)))
        # The worker reports how long ago PLAY1 was sent so the server can
        # start its countdown in lockstep with the physical clock.
        mam_link.ack_q = (seq, time.ticks_ms())
    elif name in ('ret', 'play', 'mute'):
        _do_action(name)
        mam_link.ack_q = (seq, 0)

def _turn_off_ap_later():
    time.sleep(3)
    try:
        ap = network.WLAN(network.AP_IF)
        ap.active(False)
        print('AP apagado con exito tras asociacion!')
    except Exception as e:
        print('Error apagando AP:', e)

def parse_query(qs):
    params = {}
    for part in qs.split('&'):
        if '=' in part:
            k, v = part.split('=', 1)
            params[k] = wifi_mgr.unquote(v)
    return params

def send_resp(cl, body, ctype="text/html; charset=utf-8", status="200 OK"):
    import gc
    gc.collect()
    if isinstance(body, str):
        raw = body.encode()
    else:
        raw = body
    header = "HTTP/1.1 " + status + "\r\nContent-Type: " + ctype + "\r\nAccess-Control-Allow-Origin: *\r\nContent-Length: " + str(len(raw)) + "\r\nConnection: close\r\n\r\n"
    cl.write(header.encode())
    mv = memoryview(raw)
    n = len(raw)
    for i in range(0, n, 1024):
        cl.write(mv[i:min(i+1024, n)])
    gc.collect()

def start_server(port=80):
    global current_mode, local_ip
    addr = socket.getaddrinfo('0.0.0.0', port)[0][-1]
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(addr)
    s.listen(5)
    s.settimeout(0.25)
    print('Servidor Web iniciado en puerto', port, '| Modo:', current_mode)
    btn_pressed_since = None
    mam_link.can_run = lambda: current_mode == 'control'

    while True:
        try:
            # Revisar si el botón físico BOOT (GPIO 0) está presionado para reset de Wi-Fi (3 segundos)
            if boot_btn.value() == 0:
                if btn_pressed_since is None:
                    btn_pressed_since = time.ticks_ms()
                    print('Botón BOOT presionado...')
                else:
                    elapsed = time.ticks_diff(time.ticks_ms(), btn_pressed_since)
                    # Parpadear LED mientras se mantiene presionado
                    status_led.value((elapsed // 100) % 2)
                    if elapsed >= 3000:
                        print('¡Reset Wi-Fi por botón BOOT! Borrando configuración y levantando AP Vertice24-Timer...')
                        wifi_mgr.clear_config()
                        for _ in range(20):
                            status_led.value(1)
                            time.sleep_ms(50)
                            status_led.value(0)
                            time.sleep_ms(50)
                        machine.reset()
            else:
                if btn_pressed_since is not None:
                    btn_pressed_since = None
                    status_led.value(0)

            try:
                cl, addr_client = s.accept()
            except OSError:
                mam_link.step()
                if mam_link.inbox is not None:
                    _mam_exec()
                    mam_link.step()
                continue
            cl.settimeout(2.5)
            req = b''
            try:
                req = cl.recv(1024)
            except Exception:
                pass

            if not req:
                cl.close()
                continue

            try:
                req_text = req.decode()
            except Exception:
                req_text = str(req)

            req_line = req_text.split('\r\n')[0]
            parts = req_line.split()
            url = parts[1] if len(parts) >= 2 else '/'

            path = url.split('?')[0]
            qs = url.split('?')[1] if '?' in url else ''

            if path == '/scan':
                nets = wifi_mgr.scan_networks()
                import json
                send_resp(cl, json.dumps(nets), ctype='application/json')
            elif path == '/status':
                import json
                send_resp(cl, json.dumps({'status': 'ok', 'service': 'vertice24-timer', 'ip': local_ip, 'transmitting': is_transmitting, 'timer': _get_timer_state()}), ctype='application/json')
            elif path == '/save-wifi':
                params = parse_query(qs)
                raw_ssid = params.get('ssid', '')
                raw_pwd = params.get('pwd', '')
                clean_ssid, clean_pwd = wifi_mgr.save_config(raw_ssid, raw_pwd)
                print('Conectando a:', clean_ssid)
                ip = wifi_mgr.connect_sta(clean_ssid, clean_pwd, timeout=10)
                if ip:
                    current_mode = 'control'
                    local_ip = ip
                    _thread.start_new_thread(_turn_off_ap_later, ())
                    send_resp(cl, 'OK:http://' + ip, ctype='text/plain; charset=utf-8')
                else:
                    send_resp(cl, 'Error: No se pudo conectar a ' + clean_ssid + '. Verifica la clave.', ctype='text/plain; charset=utf-8')
            elif path == '/mam-status':
                import json
                st = mam_link.status()
                st['timer'] = _get_timer_state()
                send_resp(cl, json.dumps(st), ctype='application/json')
            elif path == '/mam-save':
                import json
                params = parse_query(qs)
                mam_link.save(params.get('url', ''), params.get('enabled', '1') == '1', mam_link.cfg['key'])
                st = mam_link.status()
                st['timer'] = _get_timer_state()
                send_resp(cl, json.dumps(st), ctype='application/json')
            elif path == '/setup':
                send_resp(cl, HTML_SETUP)
            elif path == '/timer':
                params = parse_query(qs)
                m = int(params.get('m', '1'))
                s_val = int(params.get('s', '0'))
                if is_transmitting:
                    send_resp(cl, 'Transmision ocupada, reintenta en un momento', ctype='text/plain; charset=utf-8')
                    cl.close()
                else:
                    # Ejecutar primero la secuencia IR completa y responder en el instante exacto en que se envía PLAY1
                    _do_countdown(m, s_val)
                    send_resp(cl, 'Temporizador de ' + str(m) + 'm ' + str(s_val) + 's en marcha', ctype='text/plain; charset=utf-8')
                    cl.close()
                continue
            elif path == '/ret':
                send_resp(cl, 'Regresando a modo reloj...', ctype='text/plain; charset=utf-8')
                cl.close()
                _do_action('ret')
                continue
            elif path == '/play':
                send_resp(cl, 'Comando Play / Pausa enviado', ctype='text/plain; charset=utf-8')
                cl.close()
                _do_action('play')
                continue
            elif path == '/mute':
                send_resp(cl, 'Alarma silenciada', ctype='text/plain; charset=utf-8')
                cl.close()
                _do_action('mute')
                continue
            else:
                if current_mode == 'setup':
                    send_resp(cl, HTML_SETUP)
                else:
                    send_resp(cl, HTML_CONTROL)

            cl.close()
        except Exception as e:
            try: cl.close()
            except Exception: pass
            print('Web error:', e)
