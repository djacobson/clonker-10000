"""Standalone LG webOS WebSocket handshake test for CircuitPython 10.3.1.

No pairing, registration, or TV commands are sent.
Run from the REPL: exec(open('/tests/test_lg_webos.py').read())
"""

import binascii
import os
import socketpool
import time
import wifi

TV_IP = "192.168.50.47"
TV_PORT = 3000
TIMEOUT_SECONDS = 5


def run():
    print("=== LG webOS WebSocket handshake test ===")
    print("Wi-Fi connected:", wifi.radio.connected)
    print("Pico IP:", wifi.radio.ipv4_address)
    print("TV:", TV_IP, "port", TV_PORT)
    if not wifi.radio.connected:
        print("FAIL: Pico Wi-Fi is not connected")
        return

    pool = socketpool.SocketPool(wifi.radio)
    sock = None
    try:
        print("Opening TCP connection...")
        sock = pool.socket(pool.AF_INET, pool.SOCK_STREAM)
        sock.settimeout(TIMEOUT_SECONDS)
        sock.connect((TV_IP, TV_PORT))
        print("TCP connected")

        # The WebSocket client key must be a fresh, random 16-byte value.
        key = binascii.b2a_base64(os.urandom(16)).strip().decode("ascii")
        request = (
            "GET / HTTP/1.1\r\n"
            "Host: {}:{}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            "Sec-WebSocket-Key: {}\r\n"
            "Sec-WebSocket-Version: 13\r\n"
            "\r\n"
        ).format(TV_IP, TV_PORT, key).encode("ascii")

        print("Sending WebSocket upgrade request...")
        sent = 0
        while sent < len(request):
            count = sock.send(request[sent:])
            if not count:
                raise RuntimeError("Socket closed during request")
            sent += count

        response = bytearray()
        deadline = time.monotonic() + TIMEOUT_SECONDS
        while b"\r\n\r\n" not in response and len(response) < 4096:
            if time.monotonic() >= deadline:
                raise RuntimeError("Timed out waiting for HTTP response headers")
            chunk = sock.recv(512)
            if not chunk:
                break
            response.extend(chunk)

        headers = bytes(response).split(b"\r\n\r\n", 1)[0]
        print("--- TV response ---")
        print(headers.decode("utf-8", "replace"))
        print("-------------------")

        status = headers.split(b"\r\n", 1)[0]
        if b" 101 " in status or status.endswith(b" 101"):
            print("PASS: WebSocket upgrade accepted (HTTP 101)")
            print("Next experiment: webOS registration/pairing")
        else:
            print("NOT ACCEPTED: HTTP status was not 101")
    except Exception as exc:
        print("TEST ERROR:", type(exc).__name__, str(exc))
    finally:
        if sock is not None:
            try:
                sock.close()
            except Exception:
                pass
        print("Socket closed. Test complete.")


run()
