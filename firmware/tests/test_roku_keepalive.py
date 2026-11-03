# The Clonker 10000 -- Chapter 6 Roku persistent HTTP experiment
# Save as /tests/test_roku_keepalive.py on the Pico.
# Execute from REPL with the main Clonker loop stopped.
# No commands are sent merely by loading this module.

import time
import wifi
import socketpool
from clonker import device_config_v2 as config

ROOM_ID = 'room-2'
TIMEOUT = 1.0
_pool = None


def _endpoint():
    endpoint = config.current()['rooms'][ROOM_ID]['devices']['device-3']
    host, port = endpoint.split(':')
    return host, int(port)


def _read_response(sock):
    # Read through header terminator; preserve any body bytes already read.
    raw = bytearray()
    chunk = bytearray(256)
    while b'\r\n\r\n' not in raw:
        n = sock.recv_into(chunk)
        if n == 0:
            raise OSError('Server closed before headers completed')
        raw.extend(chunk[:n])
        if len(raw) > 4096:
            raise ValueError('Headers exceed 4096 bytes')
    head, body = bytes(raw).split(b'\r\n\r\n', 1)
    lines = head.decode('latin-1').split('\r\n')
    headers = {}
    for line in lines[1:]:
        if ':' in line:
            k, v = line.split(':', 1)
            headers[k.lower()] = v.strip()
    # For these POST keypress commands the Roku normally returns no body.
    # Never attempt to read an unbounded response on a persistent socket.
    if 'transfer-encoding' in headers:
        raise ValueError('Chunked response: test does not support it')
    if 'content-length' not in headers:
        raise ValueError('No Content-Length: cannot safely delimit persistent response')
    remaining = int(headers['content-length']) - len(body)
    if remaining < 0:
        raise ValueError('Unexpected bytes after declared response body')
    while remaining:
        n = sock.recv_into(chunk, min(len(chunk), remaining))
        if n == 0:
            raise OSError('Server closed during body')
        remaining -= n
    return lines[0], headers


def probe(count=3, key='VolumeUp'):
    """Attempt sequential ECP requests over ONE TCP socket.

    Only VolumeUp/VolumeDown/VolumeMute are accepted. Start with count=2.
    Prints status, headers and elapsed time for each request.
    """
    global _pool
    if key not in ('VolumeUp', 'VolumeDown', 'VolumeMute'):
        raise ValueError('Use VolumeUp, VolumeDown, or VolumeMute')
    if not 1 <= count <= 10:
        raise ValueError('count must be 1..10')
    if not wifi.radio.connected:
        raise OSError('Wi-Fi not connected')
    host, port = _endpoint()
    if _pool is None:
        _pool = socketpool.SocketPool(wifi.radio)
    sock = _pool.socket(_pool.AF_INET, _pool.SOCK_STREAM)
    sock.settimeout(TIMEOUT)
    print('Roku keep-alive probe -> {}:{} | {} x {}'.format(host, port, count, key))
    try:
        start = time.monotonic()
        sock.connect((host, port))
        print('Connect: {:.1f} ms'.format((time.monotonic()-start)*1000))
        for i in range(count):
            request = (
                'POST /keypress/{} HTTP/1.1\r\n'
                'Host: {}:{}\r\n'
                'Connection: keep-alive\r\n'
                'Content-Length: 0\r\n'
                '\r\n'
            ).format(key, host, port).encode('ascii')
            t = time.monotonic()
            sent = 0
            while sent < len(request):
                n = sock.send(request[sent:])
                if not n:
                    raise OSError('Socket send failed')
                sent += n
            status, headers = _read_response(sock)
            print('Request {}: {} | {:.1f} ms'.format(i+1, status, (time.monotonic()-t)*1000))
            print('  Connection: {} | Content-Length: {}'.format(
                headers.get('connection', '(absent)'), headers.get('content-length')))
            if not status.startswith('HTTP/1.1 2') and not status.startswith('HTTP/1.0 2'):
                print('Stopping: non-success HTTP response')
                break
            if headers.get('connection', '').lower() == 'close':
                print('Server explicitly requested close; stopping')
                break
        print('Probe finished')
    except Exception as exc:
        print('Probe stopped:', repr(exc))
        print('If after first success: Roku may close or time out the connection.')
    finally:
        sock.close()

print('Roku keep-alive test loaded. Run probe(2) to start.')
