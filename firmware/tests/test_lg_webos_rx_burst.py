"""LG webOS burst-request / out-of-order response matching experiment.

CircuitPython 10.3.1, Pico 2 W. Copy into /tests/ alongside
  test_lg_webos_rx_lifecycle.py, test_lg_webos_lab.py, test_lg_webos_home.py
Run: exec(open('/tests/test_lg_webos_rx_burst.py').read())

Sends THREE read-only getVolume requests back-to-back over one registered
WebSocket, WITHOUT receiving between sends. Then nonblocking-polls responses,
matching each by its request ID. Does not modify production Clonker code.
"""
import json
import time
import socketpool
import wifi

# Import tested frame parsing, nonblocking reads, handshake, and registration.
# Don't execute the lifecycle script's interactive main().
with open('/tests/test_lg_webos_rx_lifecycle.py') as f:
    exec(f.read().split('\nmain()', 1)[0])

BURST_COUNT = 3
RESPONSE_TIMEOUT_S = 5


def run_burst():
    print('=== LG WebSocket burst + response ID matching ===')
    print('Three READ-ONLY getVolume requests, no receive between sends.')
    print('Handshake, registration, and send are still blocking.')
    if not wifi.radio.connected:
        print('STOP: Pico Wi-Fi disconnected')
        return
    if not CLIENT_KEY or CLIENT_KEY == 'PASTE_YOUR_CLIENT_KEY_HERE':
        print('STOP: Configure CLIENT_KEY in /tests/test_lg_webos_home.py')
        return

    pool = socketpool.SocketPool(wifi.radio)
    sock = None
    try:
        sock, leftover = registered_socket(pool)
        pending = bytearray(leftover)
        stats = {'polls': 0, 'reads': 0, 'bytes': 0}
        outstanding = {}
        sent_order = []
        received_order = []

        print('Sending {} requests without waiting for responses...'.format(BURST_COUNT))
        for i in range(BURST_COUNT):
            rid = 'clonker-burst-{}'.format(i + 1)
            msg = {'id': rid, 'type': 'request', 'uri': 'ssap://audio/getVolume'}
            started = time.monotonic_ns()
            send_frame(sock, 1, json.dumps(msg).encode('utf-8'))
            outstanding[rid] = started
            sent_order.append(rid)
            print('SENT:', rid)

        print('All sent. Now polling for matching replies...')
        deadline = time.monotonic() + RESPONSE_TIMEOUT_S
        unmatched = 0
        errors = 0
        while outstanding and time.monotonic() < deadline:
            stats['polls'] += 1
            poll_socket(sock, pending, stats)
            while True:
                frame = take_frame(pending)
                if frame is None:
                    break
                opcode, payload, consumed = frame
                pending = pending[consumed:]  # No bytearray item deletion on CircuitPython
                if opcode == 8:
                    raise RuntimeError('TV sent CLOSE frame')
                if opcode == 9:
                    send_frame(sock, 10, payload)  # PONG
                    continue
                if opcode != 1:
                    continue
                msg = json.loads(payload.decode('utf-8'))
                rid = msg.get('id')
                if rid not in outstanding:
                    unmatched += 1
                    print('OTHER:', msg.get('type'), rid)
                    continue
                elapsed_ms = (time.monotonic_ns() - outstanding.pop(rid)) / 1000000
                received_order.append(rid)
                result = msg.get('payload', {})
                if msg.get('type') == 'error' or result.get('returnValue') is False:
                    errors += 1
                    print('FAIL:', rid, 'LG error:', msg.get('error', result))
                else:
                    print('PASS:', rid, 'matched in {:.1f} ms'.format(elapsed_ms),
                          'volume:', result.get('volumeStatus', {}).get('volume'))
            if outstanding:
                time.sleep(POLL_S)

        print('--- Summary ---')
        print('Sent:', len(sent_order), 'matched:', len(received_order),
              'LG errors:', errors, 'missing:', len(outstanding), 'other:', unmatched)
        print('Sent order:', ', '.join(sent_order))
        print('Reply order:', ', '.join(received_order))
        print('Polls:', stats['polls'], 'reads:', stats['reads'], 'bytes:', stats['bytes'])
        if outstanding:
            print('MISSING IDs:', ', '.join(outstanding))
        if len(received_order) == BURST_COUNT and errors == 0:
            print('PASS: All three requests matched by ID on one WebSocket')
        else:
            print('INCOMPLETE: Review response IDs/errors before adapter design')
    except Exception as e:
        print('TEST ERROR:', type(e).__name__, str(e))
    finally:
        if sock is not None:
            try:
                sock.close()
            except Exception:
                pass
        print('Socket closed. Test complete.')


run_burst()
