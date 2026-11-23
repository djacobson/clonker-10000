"""LG webOS nonblocking WebSocket RX experiment (Pico 2 W / CircuitPython).

Copy to /tests/test_lg_webos_rx_poll.py alongside the existing LG lab and
home helper. No production Clonker changes, no TV setting changes.
Run: exec(open('/tests/test_lg_webos_rx_poll.py').read())
"""
import json
import time
import socketpool
import wifi

with open('/tests/test_lg_webos_lab.py') as _f:
    _lab_source = _f.read().split('\nrun()', 1)[0]
exec(_lab_source)

POLL_INTERVAL_S = 0.02
MAX_READS_PER_POLL = 4
READ_SIZE = 256
MAX_BUFFER = 8192
RESPONSE_TIMEOUT_S = 5


def pop_frame(buffer):
    """Return one complete frame, or None; never reads the socket."""
    if len(buffer) < 2:
        return None
    first, second = buffer[0], buffer[1]
    if first & 0x70:
        raise ValueError('Unexpected WebSocket reserved bits')
    if not first & 0x80:
        raise ValueError('Fragmented WebSocket frame not supported in this test')
    length = second & 0x7f
    pos = 2
    if length == 126:
        if len(buffer) < 4:
            return None
        length = (buffer[2] << 8) | buffer[3]
        pos = 4
    elif length == 127:
        raise ValueError('64-bit frame length not supported')
    if length > MAX_BUFFER:
        raise ValueError('Oversized WebSocket frame')
    masked = bool(second & 0x80)
    if masked:
        pos += 4
    end = pos + length
    if len(buffer) < end:
        return None
    payload = bytearray(buffer[pos:end])
    if masked:
        mask = buffer[pos - 4:pos]
        for i in range(length):
            payload[i] ^= mask[i % 4]
    del buffer[:end]
    return first & 15, bytes(payload)


def poll_rx(sock, buffer, stats):
    """Bounded, nonblocking receive. No network write from this poll."""
    sock.settimeout(0)
    try:
        for _ in range(MAX_READS_PER_POLL):
            chunk = bytearray(READ_SIZE)
            try:
                count = sock.recv_into(chunk)
            except OSError as error:
                if getattr(error, 'errno', None) in (11, 35):
                    break
                raise
            if count == 0:
                raise OSError('LG closed WebSocket')
            buffer.extend(chunk[:count])
            stats['bytes'] += count
            stats['reads'] += 1
            if len(buffer) > MAX_BUFFER:
                raise ValueError('Receive buffer exceeded limit')
    finally:
        sock.settimeout(TIMEOUT)


def run_rx_test():
    print('=== LG nonblocking WebSocket RX test ===')
    print('TV:', TV_IP, 'port', TV_PORT)
    if not wifi.radio.connected:
        print('STOP: Wi-Fi disconnected')
        return
    if not CLIENT_KEY or CLIENT_KEY == 'PASTE_YOUR_CLIENT_KEY_HERE':
        print('STOP: Set CLIENT_KEY in /tests/test_lg_webos_home.py')
        return

    pool = socketpool.SocketPool(wifi.radio)
    sock = None
    try:
        sock, pending = registered_socket(pool)
        # Registration is complete; all subsequent receive handling is polled.
        request_id = 'rx-poll-1'
        msg = {'id': request_id, 'type': 'request',
               'uri': 'ssap://audio/getVolume'}
        send_frame(sock, 1, json.dumps(msg).encode('utf-8'))
        print('Sent read-only getVolume; starting nonblocking polls...')
        stats = {'polls': 0, 'reads': 0, 'bytes': 0, 'empty': 0}
        deadline = time.monotonic() + RESPONSE_TIMEOUT_S
        start = time.monotonic_ns()
        while time.monotonic() < deadline:
            stats['polls'] += 1
            before = stats['bytes']
            poll_rx(sock, pending, stats)
            if stats['bytes'] == before:
                stats['empty'] += 1
            while True:
                frame = pop_frame(pending)
                if frame is None:
                    break
                opcode, payload = frame
                if opcode == 8:
                    raise OSError('LG sent WebSocket CLOSE')
                if opcode == 9:
                    # Reply to PING outside poll_rx, using the normal bounded send.
                    send_frame(sock, 10, payload)
                    continue
                if opcode != 1:
                    print('Other frame opcode:', opcode)
                    continue
                answer = json.loads(payload.decode('utf-8'))
                if answer.get('id') != request_id:
                    print('Unsolicited message:', answer.get('type'))
                    continue
                elapsed = (time.monotonic_ns() - start) / 1000000
                result = answer.get('payload', {})
                if answer.get('type') == 'error' or result.get('returnValue') is False:
                    raise RuntimeError('TV rejected getVolume: {}'.format(answer))
                print('PASS: Response received in {:.1f} ms'.format(elapsed))
                print('Polls:', stats['polls'], 'reads:', stats['reads'],
                      'bytes:', stats['bytes'], 'empty polls:', stats['empty'])
                print('Volume status:', result.get('volumeStatus', {}))
                return
            time.sleep(POLL_INTERVAL_S)
        print('FAIL: No matching response in {} seconds'.format(RESPONSE_TIMEOUT_S))
        print('Stats:', stats, 'buffered:', len(pending))
    except Exception as error:
        print('TEST ERROR:', type(error).__name__, str(error))
    finally:
        if sock is not None:
            try:
                sock.close()
            except OSError:
                pass
        print('Socket closed. Test complete.')


run_rx_test()
