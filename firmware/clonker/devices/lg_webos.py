# The Clonker 10000
# clonker/devices/lg_webos.py
# Chapter 13 -- Typed LG webOS device adapter
# Clonker Designed by David Jacobson

"""LG webOS adapter for validated Config v5 device and command records.

Supports SSAP requests with optional JSON payloads and pointer buttons.
Authentication credentials are supplied by the active configuration.

Execution uses transmit-and-continue semantics. SSAP responses are
matched asynchronously by request ID. Outstanding request metadata
does not constitute an execution queue.

Connect, upgrade, registration, pointer acquisition and transmission
use bounded blocking I/O. Normal response polling is cooperative.

No automatic replay, filesystem writes or internal execution queue.
Pairing helpers are retained for future configuration UI integration.
The separate tested runtime and pairing manifests remain unchanged.
"""
import binascii
import json
import os
import time
import socketpool
import wifi
from clonker.devices import device_types

IDLE_NS = 10_000_000_000
OP_TIMEOUT = 0.5
SETUP_NS = 1_500_000_000
RESPONSE_NS = 1_500_000_000  # SSAP response deadline (1.5 seconds).
MAX_PENDING = 8
MAX_READS = 4
MAX_FRAMES = 8
MAX_BUFFER = 8192
READ_SIZE = 256

# Runtime registration manifest from the successful navigation lab.
MANIFEST = {
    'manifestVersion': 1, 'appVersion': '1.0',
    'appId': 'com.clonker.webos.test', 'appName': 'Clonker webOS Test',
    'permissions': ['LAUNCH', 'CONTROL_AUDIO', 'CONTROL_INPUT_TV',
                    'CONTROL_INPUT_TEXT', 'CONTROL_MOUSE_AND_KEYBOARD',
                    'CONTROL_POWER', 'READ_RUNNING_APPS', 'READ_INPUT_DEVICE_LIST'],
}
# Pairing lab used a DIFFERENT manifest. Preserve both tested forms rather
# than assuming they are interchangeable. Unification requires TV testing.
_PAIR_PERMISSIONS = ['LAUNCH', 'CONTROL_AUDIO', 'CONTROL_INPUT_MEDIA',
                     'CONTROL_INPUT_TV', 'CONTROL_POWER', 'READ_RUNNING_APPS',
                     'READ_INPUT_DEVICE_LIST']
PAIR_MANIFEST = {
    'manifestVersion': 1, 'appVersion': '1.0',
    'signed': {'created': '20140509', 'appId': 'com.lge.test',
               'vendorId': 'com.lge',
               'localizedAppNames': {'': 'Clonker webOS Test'},
               'localizedVendorNames': {'': 'Clonker'},
               'permissions': _PAIR_PERMISSIONS,
               'serial': '2f930e2d2cfe083771f68e4fe7bb07'},
    'permissions': _PAIR_PERMISSIONS,
}
PAIR_WAIT_NS = 45_000_000_000

POINTER_URI = 'ssap://com.webos.service.networkinput/getPointerInputSocket'

_pool = None
_control = None
_pointer = None
_endpoint = None
_client_key = None
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


def _registration_message(client_key=None, pairing=False):
    payload = {'forcePairing': pairing, 'pairingType': 'PROMPT',
               'manifest': PAIR_MANIFEST if pairing else MANIFEST}
    if not pairing:
        if not client_key:
            raise ValueError('LG pairing key required')
        payload['client-key'] = client_key
    return {'id': _id(), 'type': 'register', 'payload': payload}


def _connect_control(host, port, client_key):
    global _control
    if _control is not None:
        _stats['control_reuses'] += 1
        return
    started = _now()
    deadline = started + SETUP_NS
    conn = _open(host, port, '/', deadline)
    try:
        _json_send(conn, _registration_message(client_key), deadline)
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
    global _endpoint, _client_key

    _close_one('pointer')
    _close_one('control')

    _stats['abandoned'] += len(_pending)
    _pending.clear()

    _endpoint = None
    _client_key = None


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


def _parse_endpoint(endpoint):
    host, colon, port_text = endpoint.partition(':')
    octets = host.split('.')
    if len(octets) != 4 or any(not x.isdigit() or int(x) > 255 for x in octets):
        raise ValueError('LG endpoint requires IPv4')
    port = int(port_text) if colon else 3000
    if not 1 <= port <= 65535:
        raise ValueError('Invalid LG port')
    return host, port


def _resolve_key(client_key):
    """Require an explicitly supplied operational credential."""
    if (
        not isinstance(client_key, str)
        or not client_key.strip()
        or client_key == 'PASTE_OR_PAIR_CLIENT_KEY_HERE'
    ):
        raise ValueError('LG pairing key required')
    return client_key


def ready(device, command):
    """No I/O. False leaves the original command in the Dumb Queue."""
    host, port = _parse_endpoint(device['endpoint'])
    endpoint = '{}:{}'.format(host, port)
    client_key = _resolve_key(device['client_key'])

    if _pair_conn is not None:
        return False

    if _pending and (
        endpoint != _endpoint or client_key != _client_key
    ):
        return False

    if (
        command['kind'] == device_types.POINTER
        and _pointer is None
        and _pending
    ):
        return False

    return len(_pending) < MAX_PENDING


def execute(device, command):
    """Transmit one validated Config v5 command.

    Acceptance means transmitted, not acknowledged.
    Credentials belong to configuration.
    No automatic replay or internal execution queue.
    """
    global _endpoint, _client_key

    kind = command['kind']

    if kind not in (device_types.SSAP, device_types.POINTER):
        raise ValueError('Unsupported LG command kind')

    host, port = _parse_endpoint(device['endpoint'])
    endpoint = '{}:{}'.format(host, port)
    client_key = _resolve_key(device['client_key'])

    try:
        if not wifi.radio.connected:
            raise OSError('Wi-Fi disconnected')

        _expire()

        if not ready(device, command):
            return {
                'accepted': False,
                'detail': 'LG busy',
            }

        if (
            endpoint != _endpoint
            or client_key != _client_key
        ):
            close()
            _endpoint = endpoint
            _client_key = client_key

        _connect_control(host, port, client_key)

        if kind == device_types.POINTER:
            _connect_pointer(host)
            started = _now()

            payload = (
                'type:button\nname:{}\n\n'.format(
                    command['button']
                )
            ).encode('ascii')

            _pointer.send(
                1, payload, started + SETUP_NS
            )

            _stats['pointer_sent'] += 1
            detail = 'LG pointer transmitted'

        else:
            msg = _request_message(
                command['uri'],
                command.get('payload'),
            )

            started = _now()

            _json_send(
                _control, msg, started + SETUP_NS
            )

            _pending[msg['id']] = (
                kind,
                started,
                _now() + RESPONSE_NS,
            )

            _stats['ssap_sent'] += 1
            detail = 'LG SSAP transmitted'

        _stats['last_send_ms'] = _ms(started)

        return {
            'accepted': True,
            'detail': detail,
        }

    except Exception as error:
        _failure('execute', error)
        raise RuntimeError('LG transmission failure')


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

    The adapter coordinator propagates asynchronous failures to the
    dispatcher, which cancels remaining queued tasks. Transmitted
    commands have already left the queue and are never replayed.
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
        had_pending = bool(_pending)
        _failure('poll', error)
        if had_pending:
            raise RuntimeError('LG asynchronous request failure')
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
            'requests': dict(_stats), 'pairing': pair_status(),
            'pairing_counts': dict(_pair_stats)}

# Pairing is explicitly driven by the future configuration layer, not poll().
# A temporary session never enters the runtime request dictionary.
_pair_conn = None
_pair_deadline = 0
_pair_state = 'idle'
_pair_endpoint = None
_pair_key = None
_pair_error = None
_pair_stats = dict.fromkeys(('started', 'approved', 'failed', 'cancelled', 'timed_out'), 0)


def _pair_finish(state, error=None):
    global _pair_conn, _pair_state, _pair_error, _pair_deadline
    conn = _pair_conn
    _pair_conn = None
    _pair_deadline = 0
    _pair_state = state
    _pair_error = error
    if conn is not None:
        try:
            conn.sock.close()
        except OSError:
            pass
    if state in _pair_stats:
        _pair_stats[state] += 1


def pair_status():
    """Safe status for UI/diagnostics; never contains the client key."""
    return {'state': _pair_state, 'endpoint': _pair_endpoint,
            'error': _pair_error, 'key_available': _pair_key is not None,
            'remaining_ms': max(0, (_pair_deadline - _now()) // 1_000_000)
                            if _pair_conn is not None else 0}


def pair_begin(endpoint):
    """Bounded setup; user approval is handled by subsequent pair_poll calls."""
    global _pair_conn, _pair_deadline, _pair_state, _pair_endpoint, _pair_key, _pair_error
    if _pair_conn is not None or _pending:
        raise RuntimeError('LG adapter busy')
    host, port = _parse_endpoint(endpoint)
    close()
    _pair_key = None
    _pair_endpoint = '{}:{}'.format(host, port)
    _pair_error = None
    _pair_state = 'connecting'
    _pair_stats['started'] += 1
    try:
        if not wifi.radio.connected:
            raise OSError('Wi-Fi disconnected')
        deadline = _now() + SETUP_NS
        _pair_conn = _open(host, port, '/', deadline)
        _json_send(_pair_conn, _registration_message(pairing=True), deadline)
        _pair_deadline = _now() + PAIR_WAIT_NS
        _pair_state = 'waiting'
    except Exception as error:
        _pair_finish('failed', type(error).__name__)
    return pair_status()


def pair_poll():
    """Bounded RX; no sleep or blocking wait for human approval."""
    global _pair_key
    conn = _pair_conn
    if conn is None:
        return pair_status()
    if _now() >= _pair_deadline:
        _pair_finish('timed_out')
        return pair_status()
    try:
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
            conn.handle_protocol(opcode, payload, min(_pair_deadline, _now() + int(OP_TIMEOUT * 1e9)))
            if opcode != 1:
                continue
            msg = json.loads(payload.decode('utf-8'))
            if msg.get('type') == 'error':
                _pair_finish('failed', 'LG rejected pairing')
                break
            if msg.get('type') == 'registered':
                key = msg.get('payload', {}).get('client-key')
                if not isinstance(key, str) or not key:
                    raise ValueError('LG returned no client key')
                _pair_key = key
                _pair_finish('approved')
                break
    except Exception as error:
        _pair_finish('failed', type(error).__name__)
    return pair_status()


def pair_take_client_key():
    """Explicit one-time credential handoff to trusted configuration code."""
    global _pair_key
    key = _pair_key
    _pair_key = None
    return key


def pair_cancel():
    global _pair_key
    _pair_key = None
    if _pair_conn is not None:
        _pair_finish('cancelled')
    return pair_status()


def verify_client_key(endpoint, client_key=None):
    """Bounded synchronous registration on a temporary socket, no forced pairing.

    LG may still prompt if a key is invalid; no human approval wait here.
    Does not verify every permission or execute a TV command.
    """
    if _pair_conn is not None or _pending:
        raise RuntimeError('LG adapter busy')
    host, port = _parse_endpoint(endpoint)
    key = _resolve_key(client_key)
    conn = None
    try:
        deadline = _now() + SETUP_NS
        conn = _open(host, port, '/', deadline)
        _json_send(conn, _registration_message(key), deadline)
        while True:
            msg = conn.next_json(deadline)
            if msg.get('type') == 'registered':
                return True
            if msg.get('type') == 'error':
                return False
    except (OSError, ValueError):
        return False
    finally:
        if conn is not None:
            try:
                conn.sock.close()
            except OSError:
                pass


# Remaining LG development items:
# - Integrate cooperative pairing with the configuration editor.
# - Test credential handoff and pairing cancellation during config transitions.
# - Evaluate unification of the runtime and pairing manifests.
# - Investigate secure WebSocket support and certificate trust for newer TVs.
# - Strengthen WebSocket upgrade and registration response validation.
# - Extend testing of response timeouts, partial frames, ping/pong,
#   endpoint switching, memory endurance and scheduler latency.
# - Evaluate cooperative connection setup and pointer acquisition if needed.
# - Evaluate native pointer button hold/release support.
# - Consider additional performance instrumentation if needed.
# - Do not infer command support from manifest permissions alone.
