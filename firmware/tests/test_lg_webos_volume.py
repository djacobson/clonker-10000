"""Read-only LG webOS volume API experiment.

Requires /tests/test_lg_webos_home.py (existing helper functions and CLIENT_KEY).
Run in CircuitPython REPL:
    exec(open('/tests/test_lg_webos_volume.py').read())
"""
import time
import json
import socketpool
import wifi

# Reuse the exact, previously tested WebSocket framing and registration manifest.
# Do not execute the HOME test's run() function.
with open('/tests/test_lg_webos_home.py') as source_file:
    helpers = source_file.read().split('\ndef run():', 1)[0]
exec(helpers)


def test_volume():
    print('=== LG webOS read-only getVolume test ===')
    print('Pico Wi-Fi:', wifi.radio.connected)
    print('TV:', TV_IP)
    if not wifi.radio.connected:
        print('STOP: Wi-Fi disconnected')
        return
    if not CLIENT_KEY or CLIENT_KEY == 'PASTE_YOUR_CLIENT_KEY_HERE':
        print('STOP: Set CLIENT_KEY in /tests/test_lg_webos_home.py')
        return

    pool = socketpool.SocketPool(wifi.radio)
    sock = None
    try:
        sock, pending = open_ws(pool, TV_IP, TV_PORT, '/')
        register = {
            'id': 'clonker-register-volume',
            'type': 'register',
            'payload': {
                'forcePairing': False,
                'pairingType': 'PROMPT',
                'client-key': CLIENT_KEY,
                'manifest': MANIFEST,
            },
        }
        print('Registering with existing client key...')
        send_frame(sock, 1, json.dumps(register).encode('utf-8'))
        for attempt in range(6):
            msg = next_json(sock, pending)
            print('Registration message:', msg.get('type'))
            if msg.get('type') == 'registered':
                print('PASS: Registered')
                break
            if msg.get('type') == 'error':
                raise RuntimeError('Registration error: {}'.format(msg.get('error', msg)))
        else:
            raise RuntimeError('No registration confirmation')

        request = {
            'id': 'clonker-get-volume-1',
            'type': 'request',
            'uri': 'ssap://audio/getVolume',
        }
        print('Requesting ssap://audio/getVolume...')
        send_frame(sock, 1, json.dumps(request).encode('utf-8'))
        for attempt in range(8):
            msg = next_json(sock, pending)
            if msg.get('id') != request['id']:
                print('Other message:', msg.get('type'))
                continue
            print('Response type:', msg.get('type'))
            if msg.get('type') == 'error':
                print('FAIL: TV returned:', msg.get('error', msg))
            else:
                print('Response payload:', msg.get('payload', {}))
                if msg.get('payload', {}).get('returnValue') is True:
                    print('PASS: Audio API request accepted')
                else:
                    print('NOTE: Audio API returned an unsuccessful response')
            break
        else:
            print('FAIL: No matching volume response')
    except Exception as exc:
        print('TEST ERROR:', type(exc).__name__, str(exc))
    finally:
        if sock is not None:
            try:
                sock.close()
            except Exception:
                pass
        print('Socket closed. Test complete.')


test_volume()
