# The Clonker 10000
# clonker/devices/lg_webos.py
# Chapter 11 -- LG webOS adapter design draft (NOT ROUTED)
# Clonker Designed by David Jacobson

"""Experimental adapter, intentionally not imported by device_adapters.py.

Lab evidence: registered control socket reuse, 10-second idle retirement,
nonblocking RX, three outstanding read-only requests matched by ID, pointer
navigation, volume and explicit mute. Cold control requests took ~160 ms;
warm requests ~14-27 ms. Burst replies arrived in ~32-53 ms.

Connect, upgrade, registration and transmission remain bounded blocking I/O.
Normal response processing is cooperative. Pointer acquisition is currently
bounded blocking too; consider a cooperative setup state machine later.
No internal command queue, automatic replay, pairing UI or filesystem writes.
A successful send is NOT proof of execution. Poll failures must eventually
reach the shared action failure handler; integration is deliberately deferred.
"""
import binascii
import json
import os
import time
import socketpool
import wifi

IDLE_NS = 10_000_000_000
OP_TIMEOUT = 0.5
SETUP_NS = 1_500_000_000
RESPONSE_NS = 1_500_000_000  # Proposed; lab used 5 seconds.
MAX_PENDING = 8
MAX_READS = 4
MAX_FRAMES = 8
MAX_BUFFER = 8192
READ_SIZE = 256

# Preserve the tested application identity. Pairing is external for now.
MANIFEST = {
    'manifestVersion': 1, 'appVersion': '1.0',
    'appId': 'com.clonker.webos.test', 'appName': 'Clonker webOS Test',
    'permissions': ['LAUNCH', 'CONTROL_AUDIO', 'CONTROL_INPUT_TV',
                    'CONTROL_INPUT_TEXT', 'CONTROL_MOUSE_AND_KEYBOARD',
                    'CONTROL_POWER', 'READ_RUNNING_APPS', 'READ_INPUT_DEVICE_LIST'],
}
# Proposed adapter-local command vocabulary, NOT a config schema decision.
SSAP_COMMANDS = {
    'volume-up': ('ssap://audio/volumeUp', None),
    'volume-down': ('ssap://audio/volumeDown', None),
    'mute-on': ('ssap://audio/setMute', {'mute': True}),
    'mute-off': ('ssap://audio/setMute', {'mute': False}),
    'get-volume': ('ssap://audio/getVolume', None),
    'launch-home': ('ssap://system.launcher/launch', {'id': 'com.webos.app.home'}),
}
BUTTON_COMMANDS = {'nav-up': 'UP', 'nav-down': 'DOWN', 'nav-left': 'LEFT',
                   'nav-right': 'RIGHT', 'select': 'ENTER', 'back': 'BACK', 'home': 'HOME'}
POINTER_URI = 'ssap://com.webos.service.networkinput/getPointerInputSocket'

_pool = None
_control = None
_pointer = None
_endpoint = None
_sequence = 0
_pending = {}  # Sent request metadata only; never queued commands.
_stats = dict.fromkeys(('control_opens', 'pointer_opens', 'control_reuses',
    'pointer_reuses', 'control_closes', 'pointer_closes', 'idle_closes',
    'ssap_sent', 'ssap_acknowledged', 'pointer_sent', 'rx_polls', 'rx_reads',
    'rx_bytes', 'other_messages', 'failures', 'timeouts', 'abandoned'), 0)
_stats.update({'last_connect_ms': None, 'last_send_ms': None,
               'last_ack_ms': None, 'last_poll_ms': None, 'last_error': None})


def _now():
    return time.monotonic_ns()


def _ms(start):
    return round((_now() - start) / 1_000_000, 1)


def _prepare(sock, deadline):
    remaining = (deadline - _now()) / 1_000_000_000
    if remaining <= 0:
        raise OSError('LG operation deadline exceeded')
    sock.settimeout(min(OP_TIMEOUT, remaining))


def _send_all(sock, data, deadline):
    offset = 0
    while offset < len(data):
        _prepare(sock, deadline)
        n = sock.send(data[offset:])
        if not n:
            raise OSError('LG socket send failed')
        offset += n


def _frame(sock, opcode, payload, deadline):
    size = len(payload)
    if size > MAX_BUFFER or (opcode >= 8 and size > 125):
        raise ValueError('LG outgoing frame too large')
    data = bytearray([0x80 | opcode])
    if size < 126:
        data.append(0x80 | size)
    else:
        data.extend((0xfe, size >> 8, size & 255))
    mask = os.urandom(4)
    data.extend(mask)
    for i, value in enumerate(payload):
        data.append(value ^ mask[i % 4])
    _send_all(sock, data, deadline)


def _take_frame(buf):
    if len(buf) < 2:
        return None
    first, second = buf[0], buf[1]
    if first & 0x70 or not first & 0x80 or second & 0x80:
        raise ValueError('Unsupported LG frame flags/fragmentation')
    opcode = first & 15
    size = second & 127
    offset = 2
    if size == 126:
        if len(buf) < 4:
            return None
        size = (buf[2] << 8) | buf[3]
        offset = 4
    elif size == 127:
        raise ValueError('LG 64-bit frame length unsupported')
    if size > MAX_BUFFER - offset or (opcode >= 8 and size > 125):
        raise ValueError('LG frame too large')
    end = offset + size
    if len(buf) < end:
        return None
    return opcode, bytes(buf[offset:end]), end


class _Connection:
    def __init__(self, sock, leftover):
        self.sock = sock
        self.buffer = bytearray(leftover)
        self.last_activity = _now()
        self.opened = self.last_activity
        self.chunk = bytearray(READ_SIZE)

    def send(self, opcode, payload, deadline):
        _frame(self.sock, opcode, payload, deadline)
        self.last_activity = _now()

    def take(self):
        frame = _take_frame(self.buffer)
        if frame is None:
            return None
        opcode, payload, consumed = frame
        self.buffer = self.buffer[consumed:]  # CircuitPython: no del slice.
        return opcode, payload

    def read(self):
        n = self.sock.recv_into(self.chunk)
        if not n:
            raise OSError('LG closed WebSocket')
        self.buffer.extend(self.chunk[:n])
        _stats['rx_reads'] += 1
        _stats['rx_bytes'] += n
        if len(self.buffer) > MAX_BUFFER:
            raise ValueError('LG receive buffer overflow')

    def handle_protocol(self, opcode, payload, deadline):
        if opcode == 8:
            raise OSError('LG sent CLOSE')
        if opcode == 9:
            # Bounded write, not a strictly nonblocking operation.
            self.send(10, payload, deadline)
        elif opcode not in (1, 10):
            raise ValueError('Unsupported LG opcode')

    def next_json(self, deadline):
        # Setup only. Never used for normal SSAP response polling.
        while _now() < deadline:
            frame = self.take()
            if frame is None:
                _prepare(self.sock, deadline)
                self.read()
                continue
            opcode, payload = frame
            self.handle_protocol(opcode, payload, deadline)
            if opcode == 1:
                return json.loads(payload.decode('utf-8'))
        raise OSError('LG setup response timeout')


def _open(host, port, path, deadline):
    global _pool
    if _pool is None:
        _pool = socketpool.SocketPool(wifi.radio)
    if not path.startswith('/') or '\r' in path or '\n' in path:
        raise ValueError('Invalid LG socket path')
    sock = _pool.socket(_pool.AF_INET, _pool.SOCK_STREAM)
    try:
        _prepare(sock, deadline)
        sock.connect((host, port))
        key = binascii.b2a_base64(os.urandom(16)).strip().decode('ascii')
        request = ('GET {} HTTP/1.1\r\nHost: {}:{}\r\nUpgrade: websocket\r\n'
                   'Connection: Upgrade\r\nSec-WebSocket-Key: {}\r\n'
                   'Sec-WebSocket-Version: 13\r\n\r\n').format(path, host, port, key)
        _send_all(sock, request.encode('ascii'), deadline)
        raw = bytearray()
        chunk = bytearray(512)
        while b'\r\n\r\n' not in raw:
            _prepare(sock, deadline)
            n = sock.recv_into(chunk)
            if not n:
                raise OSError('LG closed during upgrade')
            raw.extend(chunk[:n])
            if len(raw) > 4096:
                raise ValueError('LG upgrade headers too large')
        headers, leftover = bytes(raw).split(b'\r\n\r\n', 1)
        if b' 101 ' not in headers.split(b'\r\n', 1)[0]:
            raise OSError('LG upgrade rejected')
        # TODO: validate Upgrade/Connection and Sec-WebSocket-Accept.
        # Lab validated status 101 only; investigate SHA-1 availability on Pico.
        return _Connection(sock, leftover)
    except Exception:
        sock.close()
        raise


def _id():
    global _sequence
    _sequence += 1
    return 'clonker-{}'.format(_sequence)


def _json_send(conn, message, deadline):
    conn.send(1, json.dumps(message).encode('utf-8'), deadline)


def _result(message):
    payload = message.get('payload', {})
    if message.get('type') == 'error' or payload.get('returnValue') is False:
        # Do not include arbitrary server payloads (could contain credentials).
        raise OSError('LG rejected request')
    return payload


def _request_message(uri, payload=None):
    message = {'id': _id(), 'type': 'request', 'uri': uri}
    if payload is not None:
        message['payload'] = payload
    return message


def _connect_control(host, port, client_key):
    global _control
    if _control is not None:
        _stats['control_reuses'] += 1
        return
    started = _now()
    deadline = started + SETUP_NS
    conn = _open(host, port, '/', deadline)
    try:
        rid = _id()
        _json_send(conn, {'id': rid, 'type': 'register', 'payload': {
            'forcePairing': False, 'pairingType': 'PROMPT',
            'client-key': client_key, 'manifest': MANIFEST}}, deadline)
        while True:
            msg = conn.next_json(deadline)
            if msg.get('type') == 'error':
                raise OSError('LG registration rejected')
            if msg.get('type') == 'registered':
                break
        conn.last_activity = _now()
        _control = conn
        _stats['control_opens'] += 1
        _stats['last_connect_ms'] = _ms(started)
    except Exception:
        conn.sock.close()
        raise


def _connect_pointer(host):
    global _pointer
    if _pointer is not None:
        _stats['pointer_reuses'] += 1
        return
    # No outstanding SSAP requests may exist during this synchronous setup.
    if _pending:
        raise RuntimeError('Pointer setup requires drained SSAP requests')
    deadline = _now() + SETUP_NS
    msg = _request_message(POINTER_URI)
    _json_send(_control, msg, deadline)
    while True:
        reply = _control.next_json(deadline)
        if reply.get('id') == msg['id']:
            url = _result(reply).get('socketPath', '')
            break
        _stats['other_messages'] += 1
    if not url.startswith('ws://'):
        raise ValueError('LG pointer requires unsupported URL scheme')
    authority, slash, path = url[5:].partition('/')
    target, colon, port = authority.partition(':')
    if target != host or not slash:
        raise ValueError('Unexpected LG pointer destination')
    _pointer = _open(target, int(port) if colon else 80, '/' + path, deadline)
    _stats['pointer_opens'] += 1


def _close_one(name):
    global _control, _pointer
    conn = _control if name == 'control' else _pointer
    if name == 'control':
        _control = None
    else:
        _pointer = None
    if conn is not None:
        _stats[name + '_closes'] += 1
        try:
            conn.sock.close()
        except OSError:
            pass


def close():
    global _endpoint
    _close_one('pointer')
    _close_one('control')
    _stats['abandoned'] += len(_pending)
    _pending.clear()
    _endpoint = None


def _failure(stage, error):
    _stats['failures'] += 1
    # Exception type only: no key, manifest or pointer URL in diagnostics.
    _stats['last_error'] = '{}: {}'.format(stage, type(error).__name__)
    close()


def _expire():
    now = _now()
    if _pointer is not None and now - _pointer.last_activity >= IDLE_NS:
        _close_one('pointer')
        _stats['idle_closes'] += 1
    if _control is not None and not _pending and now - _control.last_activity >= IDLE_NS:
        # Conservative: retire pointer too when its parent control expires.
        # Independent pointer lifetime after control closure remains untested.
        _close_one('pointer')
        _close_one('control')
        _stats['idle_closes'] += 1


def ready(endpoint, command):
    """No I/O. False means leave the original command in the Dumb Queue."""
    if _pending and endpoint != _endpoint:
        return False
    if command in BUTTON_COMMANDS and _pointer is None and _pending:
        return False
    return len(_pending) < MAX_PENDING


def execute(endpoint, command, client_key):
    """Draft interface; endpoint is IPv4:port or IPv4 (default 3000).

    Client key supplied externally; never persisted or printed here.
    True acceptance means transmitted, not acknowledged. No replay on failure.
    """
    global _endpoint
    if command not in SSAP_COMMANDS and command not in BUTTON_COMMANDS:
        raise ValueError('Unsupported LG command')
    if not client_key:
        raise ValueError('LG pairing key required')
    host, colon, port_text = endpoint.partition(':')
    octets = host.split('.')
    if len(octets) != 4 or any(not x.isdigit() or int(x) > 255 for x in octets):
        raise ValueError('LG endpoint requires IPv4')
    port = int(port_text) if colon else 3000
    if not 1 <= port <= 65535:
        raise ValueError('Invalid LG port')
    try:
        if not wifi.radio.connected:
            raise OSError('Wi-Fi disconnected')
        _expire()
        if not ready(endpoint, command):
            return {'accepted': False, 'detail': 'LG busy'}
        if endpoint != _endpoint:
            close()
            _endpoint = endpoint
        _connect_control(host, port, client_key)
        if command in BUTTON_COMMANDS:
            _connect_pointer(host)
            started = _now()
            payload = ('type:button\nname:{}\n\n'.format(BUTTON_COMMANDS[command])).encode('ascii')
            _pointer.send(1, payload, started + SETUP_NS)
            _stats['pointer_sent'] += 1
        else:
            uri, payload = SSAP_COMMANDS[command]
            msg = _request_message(uri, payload)
            started = _now()
            _json_send(_control, msg, started + SETUP_NS)
            _pending[msg['id']] = (command, started, _now() + RESPONSE_NS)
            _stats['ssap_sent'] += 1
        _stats['last_send_ms'] = _ms(started)
        return {'accepted': True, 'detail': 'LG transmitted {}'.format(command)}
    except Exception as error:
        _failure('execute', error)
        raise


def _poll_connection(conn, control):
    conn.sock.settimeout(0)
    try:
        for _ in range(MAX_READS):
            try:
                conn.read()
            except OSError as error:
                if getattr(error, 'errno', None) in (11, 35):
                    break
                raise
    finally:
        conn.sock.settimeout(OP_TIMEOUT)
    for _ in range(MAX_FRAMES):
        frame = conn.take()
        if frame is None:
            break
        opcode, payload = frame
        conn.handle_protocol(opcode, payload, _now() + int(OP_TIMEOUT * 1e9))
        if opcode != 1:
            continue
        if not control:
            _stats['other_messages'] += 1
            continue
        msg = json.loads(payload.decode('utf-8'))
        rid = msg.get('id')
        if rid not in _pending or msg.get('type') not in ('response', 'error'):
            _stats['other_messages'] += 1
            continue
        _result(msg)
        command, started, deadline = _pending.pop(rid)
        _stats['ssap_acknowledged'] += 1
        _stats['last_ack_ms'] = _ms(started)
        conn.last_activity = _now()


def poll():
    """Bounded RX and maintenance. Raises on asynchronous failure.

    Future dispatcher must propagate failures to its existing cancellation
    policy even though transmitted commands have already left the queue.
    No sleep, no connection creation, no application keep-alive requests.
    PONG writes can briefly block; handshake/send are not nonblocking either.
    """
    if _control is None and _pointer is None:
        return
    started = _now()
    try:
        if not wifi.radio.connected:
            raise OSError('Wi-Fi disconnected')
        _stats['rx_polls'] += 1
        if _control is not None:
            _poll_connection(_control, True)
        if _pointer is not None:
            _poll_connection(_pointer, False)
        for command, sent, deadline in _pending.values():
            if _now() >= deadline:
                _stats['timeouts'] += 1
                raise OSError('LG response timeout')
        _expire()
    except Exception as error:
        _failure('poll', error)
        raise
    finally:
        _stats['last_poll_ms'] = _ms(started)


def transport_snapshot():
    """RAM-only Flight Recorder snapshot; no credentials or network I/O."""
    now = _now()
    def age(conn):
        return round((now - conn.last_activity) / 1_000_000, 1) if conn else None
    return {'endpoint': _endpoint, 'control_active': _control is not None,
            'pointer_active': _pointer is not None,
            'control_idle_ms': age(_control), 'pointer_idle_ms': age(_pointer),
            'idle_timeout_ms': IDLE_NS // 1_000_000,
            'response_timeout_ms': RESPONSE_NS // 1_000_000,
            'pending_limit': MAX_PENDING, 'pending_count': len(_pending),
            'oldest_pending_ms': max([round((now - x[1]) / 1_000_000, 1)
                                      for x in _pending.values()] or [0]),
            'requests': dict(_stats)}

# Integration TODOs (intentionally no changes outside this module):
# - Decide configuration schema, endpoint normalization, key lookup and pairing UI.
# - Decide generic adapter contract for ready/execute/poll and delayed failures.
# - Add perf.register/record instrumentation following Denon conventions.
# - Test pointer lifetime, ping/pong, partial frames, burst writes, error paths,
#   response timeout, endpoint switching, memory and scheduler latency.
# - Test secure WebSocket support and upgrade validation before production use.
# - Decide whether registration and pointer acquisition need cooperative states.
# - Do not infer power, playback, skip or native hold support from permissions.
