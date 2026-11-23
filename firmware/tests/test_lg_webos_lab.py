"""Standalone LG webOS test lab, CircuitPython 10.3.1 / Pico 2 W.

Copy to /tests/test_lg_webos_lab.py. Requires the existing
/tests/test_lg_webos_home.py for tested WebSocket helpers and CLIENT_KEY.
Run: exec(open('/tests/test_lg_webos_lab.py').read())

No production Clonker changes. Never prints the client key.
"""
import json
import time
import socketpool
import wifi

with open('/tests/test_lg_webos_home.py') as source_file:
    helpers = source_file.read().split('\ndef run():', 1)[0]
exec(helpers)


def registered_socket(pool):
    sock, pending = open_ws(pool, TV_IP, TV_PORT, '/')
    try:
        registration = {
            'id': 'lab-register', 'type': 'register',
            'payload': {'forcePairing': False, 'pairingType': 'PROMPT',
                        'client-key': CLIENT_KEY, 'manifest': MANIFEST}}
        send_frame(sock, 1, json.dumps(registration).encode('utf-8'))
        for _ in range(8):
            msg = next_json(sock, pending)
            if msg.get('type') == 'registered':
                print('PASS: TV registration')
                return sock, pending
            if msg.get('type') == 'error':
                raise RuntimeError('Registration: {}'.format(msg.get('error', msg)))
        raise RuntimeError('No registration confirmation')
    except Exception:
        sock.close()
        raise


_request_number = 0


def request(sock, pending, uri, payload=None):
    global _request_number
    _request_number += 1
    message = {'id': 'lab-request-{}'.format(_request_number),
               'type': 'request', 'uri': uri}
    if payload is not None:
        message['payload'] = payload
    print('Request:', uri)
    send_frame(sock, 1, json.dumps(message).encode('utf-8'))
    for _ in range(8):
        msg = next_json(sock, pending)
        if msg.get('id') == message['id']:
            if msg.get('type') == 'error':
                raise RuntimeError('TV error: {}'.format(msg.get('error', msg)))
            result = msg.get('payload', {})
            if result.get('returnValue') is False:
                raise RuntimeError('TV rejected: {}'.format(result))
            print('PASS: API response:', result if uri.endswith('getVolume') else 'accepted')
            return result
    raise RuntimeError('No matching response')


def pointer_socket(pool, control, pending):
    result = request(control, pending,
                     'ssap://com.webos.service.networkinput/getPointerInputSocket')
    url = result.get('socketPath', '')
    if not url.startswith('ws://'):
        raise RuntimeError('Pointer URL is not ws:// (TLS not supported in this test): {}'.format(url.split(':', 1)[0]))
    authority, _, path = url[5:].partition('/')
    host, sep, port = authority.partition(':')
    pointer, leftover = open_ws(pool, host, int(port) if sep else 80, '/' + path)
    print('PASS: Pointer WebSocket connected')
    return pointer


def volume_lab(control, pending):
    print('Volume commands: U=up D=down G=get M=mute X=unmute')
    print('                R=repeat up 5 times F=repeat down 5 times Q=quit')
    print('NOTE: TV uses external ARC; check whether Denon actually changes.')
    while True:
        key = input('Volume command: ').strip().upper()
        if key in ('Q', 'QUIT', ''):
            break
        if key == 'G':
            request(control, pending, 'ssap://audio/getVolume')
        elif key == 'U':
            request(control, pending, 'ssap://audio/volumeUp')
        elif key == 'D':
            request(control, pending, 'ssap://audio/volumeDown')
        elif key == 'M':
            request(control, pending, 'ssap://audio/setMute', {'mute': True})
        elif key == 'X':
            request(control, pending, 'ssap://audio/setMute', {'mute': False})
        elif key in ('R', 'F'):
            uri = 'ssap://audio/volumeUp' if key == 'R' else 'ssap://audio/volumeDown'
            print('Sending 5 volume steps at ~200 ms intervals...')
            for i in range(5):
                request(control, pending, uri)
                if i < 4:
                    time.sleep(0.2)
            print('Repeat test complete; check TV/Denon.')
        else:
            print('Unknown command')


def connection_lab(control, pending):
    """Measure passive idle lifetime of the control WebSocket."""
    print("=== LG WebSocket idle test ===")
    print("No keep-alive traffic; read-only getVolume.")

    seconds = input("Idle seconds (5, 10, 20, 25, 30): ").strip()
    if seconds not in ("5", "10", "20", "25", "30"):
        print("Test cancelled.")
        return

    seconds = int(seconds)

    print("Baseline request...")
    start = time.monotonic_ns()
    request(control, pending, "ssap://audio/getVolume")
    print("Baseline: {:.1f} ms".format(
        (time.monotonic_ns() - start) / 1000000
    ))

    print("Sleeping {} seconds...".format(seconds))
    time.sleep(seconds)

    print("Reusing same WebSocket...")
    start = time.monotonic_ns()

    try:
        request(control, pending, "ssap://audio/getVolume")
        print("PASS: Socket reused after {} seconds".format(seconds))
    except Exception as error:
        print("FAIL:", type(error).__name__, str(error))
    finally:
        print("Request elapsed: {:.1f} ms".format(
            (time.monotonic_ns() - start) / 1000000
        ))


def run():
    print('=== Clonker LG webOS laboratory ===')
    print('TV:', TV_IP, 'port', TV_PORT)
    if not wifi.radio.connected:
        print('STOP: Pico Wi-Fi disconnected')
        return
    if not CLIENT_KEY or CLIENT_KEY == 'PASTE_YOUR_CLIENT_KEY_HERE':
        print('STOP: Configure CLIENT_KEY in /tests/test_lg_webos_home.py')
        return
    pool = socketpool.SocketPool(wifi.radio)
    control = None
    pointer = None
    try:
        control, pending = registered_socket(pool)
        print('1 = Home dashboard (launcher API)')
        print('2 = Read audio status (no change)')
        print('3 = Test pointer access and navigation')
        print('4 = Volume / mute laboratory')
        print('5 = Persistent WebSocket lifecycle')
        print('6 = Activity-based WebSocket lifecycle')
        choice = input('Choose 1, 2, 3, 4, 5, or 6: ').strip()
        if choice == '1':
            request(control, pending, 'ssap://system.launcher/launch',
                    {'id': 'com.webos.app.home'})
            print('Check TV: webOS Home should be visible')
        elif choice == '2':
            request(control, pending, 'ssap://audio/getVolume')
        elif choice == '3':
            print('Requesting pointer-input socket...')
            pointer = pointer_socket(pool, control, pending)
            print('Commands: UP DOWN LEFT RIGHT ENTER BACK HOME; Q to quit')
            while True:
                key = input('Navigation key: ').strip().upper()
                if key in ('Q', 'QUIT', ''):
                    break
                if key not in ('UP', 'DOWN', 'LEFT', 'RIGHT', 'ENTER', 'BACK', 'HOME'):
                    print('Unknown key')
                    continue
                send_frame(pointer, 1, ('type:button\nname:{}\n\n'.format(key)).encode('ascii'))
                print('Sent', key, '- check TV')
        elif choice == '4':
            volume_lab(control, pending)
        elif choice == '5':
            connection_lab(control, pending)
        elif choice == '6':
            activity_lifecycle_lab(pool, control, pending)
            control = None
        else:
            print('No test selected')
    except Exception as exc:
        print('TEST RESULT:', type(exc).__name__, str(exc))
        if '401' in str(exc):
            print('TV denied access to the requested service.')
    finally:
        for sock in (pointer, control):
            if sock is not None:
                try:
                    sock.close()
                except Exception:
                    pass
        print('Sockets closed. Laboratory finished.')


def activity_lifecycle_lab(pool, control, pending):
    """Prototype LG activity-based WebSocket reuse."""
    idle_timeout_ns = 10_000_000_000
    last_activity_ns = time.monotonic_ns()
    connects = 0
    reuses = 0
    closes = 0

    print("=== LG activity lifecycle prototype ===")
    print("Idle timeout: 10 seconds")
    print("Commands: G=getVolume, U=volumeUp,")
    print("          D=volumeDown, W=wait 12s, Q=quit")
    print("W simulates nonblocking scheduler polling.")

    try:
        while True:
            key = input("Command: ").strip().upper()

            if key == "Q":
                break

            if key == "W":
                print("Simulating 12 seconds of scheduler ticks...")
                for _ in range(120):
                    if control is not None:
                        elapsed = time.monotonic_ns() - last_activity_ns
                        if elapsed >= idle_timeout_ns:
                            print("IDLE: closing LG WebSocket")
                            try:
                                control.close()
                            finally:
                                control = None
                                pending = None
                            closes += 1
                    time.sleep(0.1)
                continue

            if key not in ("G", "U", "D"):
                print("Unknown command")
                continue

            if control is not None:
                elapsed = time.monotonic_ns() - last_activity_ns
                if elapsed >= idle_timeout_ns:
                    print("IDLE: closing expired connection")
                    control.close()
                    control = None
                    pending = None
                    closes += 1

            started = time.monotonic_ns()

            if control is None:
                print("CONNECT: opening new WebSocket")
                control, pending = registered_socket(pool)
                connects += 1
            else:
                print("REUSE: existing WebSocket")
                reuses += 1

            uri = {
                "G": "ssap://audio/getVolume",
                "U": "ssap://audio/volumeUp",
                "D": "ssap://audio/volumeDown",
            }[key]

            try:
                request(control, pending, uri)
                last_activity_ns = time.monotonic_ns()
                print("PASS: {:.1f} ms".format(
                    (last_activity_ns - started) / 1_000_000
                ))
            except Exception as error:
                print("FAIL:", type(error).__name__, str(error))
                control.close()
                control = None
                pending = None
                closes += 1
                print("Connection discarded; next command reconnects")

    finally:
        if control is not None:
            control.close()
            closes += 1
        print("Connections opened:", connects)
        print("Connections reused:", reuses)
        print("Connections closed:", closes)


run()
