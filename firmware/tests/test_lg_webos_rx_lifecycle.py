"""LG webOS polled-RX + activity-based socket lifecycle experiment.

Copy alongside /tests/test_lg_webos_lab.py and /tests/test_lg_webos_home.py.
Run: exec(open('/tests/test_lg_webos_rx_lifecycle.py').read())
No Clonker production changes. G and W are read-only.
"""
import json
import time
import socketpool
import wifi

# Reuse the known-good handshake, registration, and WebSocket frame helpers.
with open('/tests/test_lg_webos_lab.py') as f:
    exec(f.read().split('\nrun()', 1)[0])

POLL_S = 0.02
IDLE_S = 10
RESPONSE_S = 5
MAX_READS = 4
READ_SIZE = 256
MAX_BUFFER = 8192


def take_frame(buf):
    if len(buf) < 2:
        return None
    first, second = buf[0], buf[1]
    if first & 0x70 or not first & 0x80:
        raise ValueError('Unsupported WebSocket frame flags/fragmentation')
    length = second & 127
    offset = 2
    if length == 126:
        if len(buf) < 4:
            return None
        length = (buf[2] << 8) | buf[3]
        offset = 4
    elif length == 127:
        raise ValueError('64-bit WebSocket frame unsupported')
    if length > MAX_BUFFER:
        raise ValueError('WebSocket frame too large')
    masked = bool(second & 128)
    if masked:
        offset += 4
    end = offset + length
    if len(buf) < end:
        return None
    payload = bytearray(buf[offset:end])
    if masked:
        mask = buf[offset-4:offset]
        for i in range(length):
            payload[i] ^= mask[i % 4]
    return first & 15, bytes(payload), end


def poll_socket(sock, buf, stats):
    # Socket reads only. Restore bounded timeout for subsequent send_frame().
    sock.settimeout(0)
    try:
        for _ in range(MAX_READS):
            chunk = bytearray(READ_SIZE)
            try:
                n = sock.recv_into(chunk)
            except OSError as e:
                if getattr(e, 'errno', None) in (11, 35):
                    break
                raise
            if n == 0:
                raise OSError('LG closed WebSocket')
            buf.extend(chunk[:n])
            stats['reads'] += 1
            stats['bytes'] += n
            if len(buf) > MAX_BUFFER:
                raise ValueError('Receive buffer overflow')
    finally:
        sock.settimeout(TIMEOUT)


def main():
    print('=== LG polled RX + idle lifecycle ===')
    print('TV:', TV_IP, 'port', TV_PORT)
    print('Idle timeout:', IDLE_S, 'seconds')
    print('G=getVolume (read only), U=volumeUp, D=volumeDown')
    print('W=simulate 12 seconds of scheduler ticks, Q=quit')
    print('Note: input() itself blocks; W exercises the poll/idle loop.')
    if not wifi.radio.connected:
        print('STOP: Wi-Fi disconnected')
        return
    if not CLIENT_KEY or CLIENT_KEY == 'PASTE_YOUR_CLIENT_KEY_HERE':
        print('STOP: Set CLIENT_KEY in /tests/test_lg_webos_home.py')
        return
    pool = socketpool.SocketPool(wifi.radio)
    sock = None
    pending = bytearray()
    last_activity = None
    opened = reused = closed = 0
    sequence = 0
    stats = {'polls': 0, 'reads': 0, 'bytes': 0}

    def close_socket(reason):
        nonlocal sock, pending, last_activity, closed
        if sock is not None:
            print('CLOSE:', reason)
            try:
                sock.close()
            except OSError:
                pass
            closed += 1
        sock = None
        pending = bytearray()
        last_activity = None

    def tick():
        nonlocal pending
        if sock is None:
            return []
        if last_activity is not None and time.monotonic() - last_activity >= IDLE_S:
            close_socket('idle timeout')
            return []
        stats['polls'] += 1
        poll_socket(sock, pending, stats)
        messages = []
        while True:
            frame = take_frame(pending)
            if frame is None:
                break
            opcode, payload, consumed = frame
            pending = pending[consumed:]  # CircuitPython-compatible; no item deletion
            if opcode == 8:
                raise OSError('LG sent CLOSE')
            if opcode == 9:
                send_frame(sock, 10, payload)
            elif opcode == 1:
                messages.append(json.loads(payload.decode('utf-8')))
        return messages

    try:
        while True:
            cmd = input('Command: ').strip().upper()
            if cmd in ('Q', 'QUIT'):
                break
            if cmd == 'W':
                print('Simulating 12 seconds of 20ms scheduler ticks...')
                end = time.monotonic() + 12
                try:
                    while time.monotonic() < end:
                        for msg in tick():
                            print('Unsolicited:', msg.get('type'), msg.get('id'))
                        time.sleep(POLL_S)
                except Exception as e:
                    print('POLL ERROR:', type(e).__name__, str(e))
                    close_socket('receive failure')
                continue
            if cmd not in ('G', 'U', 'D'):
                print('Unknown command')
                continue
            # Check inactivity after user input too (input() cannot run scheduler).
            if sock is not None and time.monotonic() - last_activity >= IDLE_S:
                close_socket('expired while waiting for input')
            try:
                if sock is None:
                    print('CONNECT: new WebSocket (blocking handshake/registration)')
                    sock, pending = registered_socket(pool)
                    opened += 1
                else:
                    print('REUSE: existing WebSocket')
                    reused += 1
                sequence += 1
                request_id = 'rx-life-{}'.format(sequence)
                uri = {'G': 'ssap://audio/getVolume',
                       'U': 'ssap://audio/volumeUp',
                       'D': 'ssap://audio/volumeDown'}[cmd]
                message = {'id': request_id, 'type': 'request', 'uri': uri}
                started = time.monotonic()
                send_frame(sock, 1, json.dumps(message).encode('utf-8'))
                last_activity = time.monotonic()
                print('SEND:', uri, '- polling for response')
                deadline = time.monotonic() + RESPONSE_S
                matched = False
                while time.monotonic() < deadline:
                    for answer in tick():
                        if answer.get('id') != request_id:
                            print('Other message:', answer.get('type'), answer.get('id'))
                            continue
                        result = answer.get('payload', {})
                        if answer.get('type') == 'error' or result.get('returnValue') is False:
                            raise RuntimeError('LG rejected request: {}'.format(answer))
                        print('PASS: response in {:.1f} ms'.format(
                            (time.monotonic() - started) * 1000))
                        if cmd == 'G':
                            print('Volume:', result.get('volumeStatus', {}))
                        last_activity = time.monotonic()
                        matched = True
                        break
                    if matched:
                        break
                    time.sleep(POLL_S)
                if not matched:
                    raise RuntimeError('No matching response within {}s'.format(RESPONSE_S))
            except Exception as e:
                print('FAIL:', type(e).__name__, str(e))
                close_socket('error; next command reconnects')
    finally:
        close_socket('test exit')
        print('Connections opened:', opened, 'reused:', reused, 'closed:', closed)
        print('Polls:', stats['polls'], 'reads:', stats['reads'], 'bytes:', stats['bytes'])
        print('Test complete.')


main()
