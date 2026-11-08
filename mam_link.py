"""Link between the Vertice24 Timer and a Vertice Live MAM server.

The timer polls the MAM server over plain HTTP, so it works from any
network (venue Wi-Fi, behind NAT, MAM published through Cloudflare) without
opening ports. Only the server base URL is configurable; the endpoints are
fixed.

Protocol (all GET, JSON responses):
  /api/mam/timer/poll?device=<id>[&key=<key>]
      -> {"cmd": null}
      -> {"cmd": "timer", "seq": N, "m": M, "s": S}
      -> {"cmd": "ret" | "play" | "mute", "seq": N}
  /api/mam/timer/ack?seq=N&age=<ms since PLAY1>[&device=<id>][&key=<key>]
"""
import socket
import json
import time

CONFIG_FILE = '/mam_config.json'
DEFAULT_URL = 'http://mam.colli.co'
POLL_PATH = '/api/mam/timer/poll'
ACK_PATH = '/api/mam/timer/ack'
DEVICE_ID = 'vertice24-timer'
POLL_INTERVAL_MS = 3000

# Shared with the main loop (single-threaded: threads proved unstable together
# with the web server and the RMT peripheral).
inbox = None      # command fetched by the worker, executed by the main loop
ack_q = None      # (seq, ticks_ms when PLAY1 was sent) waiting to be reported
can_run = lambda: True

cfg = {'url': DEFAULT_URL, 'enabled': True, 'key': ''}
state = {'linked': False, 'last_ok': 0, 'last_err': '', 'last_seq': None, 'last_poll': 0}


def normalize_url(url):
    url = (url or '').strip().rstrip('/')
    if not url:
        return DEFAULT_URL
    if '://' not in url:
        url = 'http://' + url
    return url


def load():
    try:
        with open(CONFIG_FILE, 'r') as f:
            data = json.loads(f.read())
        cfg['url'] = normalize_url(data.get('url'))
        cfg['enabled'] = bool(data.get('enabled', True))
        cfg['key'] = data.get('key', '')
    except Exception:
        pass
    return cfg


def save(url, enabled, key=''):
    cfg['url'] = normalize_url(url)
    cfg['enabled'] = bool(enabled)
    cfg['key'] = key or ''
    with open(CONFIG_FILE, 'w') as f:
        f.write(json.dumps(cfg))
    state['linked'] = False
    state['last_err'] = ''
    state['last_poll'] = 0
    return cfg


def _split(url):
    scheme, rest = url.split('://', 1)
    hostport, _, base = rest.partition('/')
    base = '/' + base if base else ''
    if ':' in hostport:
        host, port = hostport.rsplit(':', 1)
        port = int(port)
    else:
        host = hostport
        port = 443 if scheme == 'https' else 80
    return scheme, host, port, base


def _key_query():
    return '&key=' + cfg['key'] if cfg['key'] else ''


def http_get(path, timeout=3):
    """Minimal HTTP/1.0 GET. `path` may be a callable evaluated right before
    the request is written (after the TLS handshake)."""
    scheme, host, port, base = _split(cfg['url'])
    if scheme != 'http':
        # The TLS handshake blocks the whole MicroPython VM on this firmware
        # build, so only plain HTTP is supported.
        raise OSError('solo http://')
    addr = socket.getaddrinfo(host, port)[0][-1]
    s = socket.socket()
    s.settimeout(timeout)
    try:
        s.connect(addr)
        p = path() if callable(path) else path
        req = 'GET %s%s HTTP/1.0\r\nHost: %s\r\nUser-Agent: %s\r\nAccept: application/json\r\n\r\n' % (
            base, p, host, DEVICE_ID)
        s.write(req.encode())
        buf = b''
        while len(buf) < 3072:
            chunk = s.read(512)
            if not chunk:
                break
            buf += chunk
    finally:
        try:
            s.close()
        except Exception:
            pass
    head, _, body = buf.partition(b'\r\n\r\n')
    try:
        code = int(head.split(b' ', 2)[1])
    except Exception:
        code = 0
    return code, body


def due():
    if not cfg['enabled']:
        return False
    return time.ticks_diff(time.ticks_ms(), state['last_poll']) >= POLL_INTERVAL_MS or state['last_poll'] == 0


def poll_once():
    """Returns a command dict or None."""
    state['last_poll'] = time.ticks_ms() or 1
    try:
        code, body = http_get(POLL_PATH + '?device=' + DEVICE_ID + _key_query())
        if code != 200:
            raise OSError('HTTP %d' % code)
        a = body.find(b'{')
        b = body.rfind(b'}')
        data = json.loads(body[a:b + 1])
        state['linked'] = True
        state['last_ok'] = time.time()
        state['last_err'] = ''
        return data if data.get('cmd') else None
    except Exception as e:
        state['linked'] = False
        state['last_err'] = str(e)
        return None


def step():
    """One non-blocking-ish unit of work, called from the main loop when idle.
    Sends a pending ack, or polls the server. Timeouts are short (3 s)."""
    global inbox, ack_q
    if not (cfg['enabled'] and can_run()):
        return
    try:
        if ack_q is not None:
            seq, t0 = ack_q
            ack_q = None
            ack(seq, (lambda: time.ticks_diff(time.ticks_ms(), t0)) if t0 else None)
        elif inbox is None and due():
            cmd = poll_once()
            if cmd:
                inbox = cmd
    except Exception as e:
        state['last_err'] = str(e)


def ack(seq, age_fn=None):
    def path():
        age = age_fn() if age_fn else 0
        return '%s?seq=%s&age=%d&device=%s%s' % (ACK_PATH, seq, age, DEVICE_ID, _key_query())
    try:
        http_get(path)
    except Exception as e:
        state['last_err'] = 'ack: ' + str(e)


def status():
    return {
        'url': cfg['url'],
        'enabled': cfg['enabled'],
        'has_key': bool(cfg['key']),
        'linked': state['linked'],
        'error': state['last_err'],
    }


load()
