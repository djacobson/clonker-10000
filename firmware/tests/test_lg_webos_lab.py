"""Standalone LG webOS test lab, CircuitPython 10.3.1 / Pico 2 W.

Copy to /tests/test_lg_webos_lab.py. Requires the existing
/tests/test_lg_webos_home.py for tested WebSocket helpers and CLIENT_KEY.
Run: exec(open('/tests/test_lg_webos_lab.py').read())

No production Clonker changes. Never prints the client key.
"""
import json
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


def request(sock, pending, uri, payload=None):
    message = {'id': 'lab-request', 'type': 'request', 'uri': uri}
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
        choice = input('Choose 1, 2, or 3: ').strip()
        if choice == '1':
            request(control, pending, 'ssap://system.launcher/launch',
                    {'id': 'com.webos.app.home'})
            print('Check TV: webOS Home should be visible')
        elif choice == '2':
            request(control, pending, 'ssap://audio/getVolume')
        elif choice == '3':
            print('Requesting pointer-input socket (previously returned 401)...')
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
        else:
            print('No test selected')
    except Exception as exc:
        print('TEST RESULT:', type(exc).__name__, str(exc))
        if '401' in str(exc):
            print('Pointer service still denies access. Launcher/audio tests remain valid.')
    finally:
        for sock in (pointer, control):
            if sock is not None:
                try:
                    sock.close()
                except Exception:
                    pass
        print('Sockets closed. Laboratory finished.')


run()
