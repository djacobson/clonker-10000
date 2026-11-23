"""Standalone LG webOS registration / pairing test for CircuitPython 10.3.1.

Copy to /tests/test_lg_webos_pairing_v2.py on Pico and run:
    exec(open('/tests/test_lg_webos_pairing_v2.py').read())

Requests CONTROL_INPUT_TV in addition to the previous test permissions.
No remote-control commands are sent; client key is printed but not stored.
"""
import binascii
import json
import os
import socketpool
import time
import wifi

TV_IP = "192.168.50.47"
TV_PORT = 3000
TIMEOUT_SECONDS = 5
PAIRING_WAIT_SECONDS = 45

PERMISSIONS = [
    "LAUNCH", "CONTROL_AUDIO", "CONTROL_INPUT_MEDIA", "CONTROL_INPUT_TV",
    "CONTROL_POWER", "READ_RUNNING_APPS", "READ_INPUT_DEVICE_LIST",
]
MANIFEST = {
    "manifestVersion": 1,
    "appVersion": "1.0",
    "signed": {
        "created": "20140509",
        "appId": "com.lge.test",
        "vendorId": "com.lge",
        "localizedAppNames": {"": "Clonker webOS Test"},
        "localizedVendorNames": {"": "Clonker"},
        "permissions": PERMISSIONS,
        "serial": "2f930e2d2cfe083771f68e4fe7bb07",
    },
    "permissions": PERMISSIONS,
}


def send_all(sock, data):
    offset = 0
    while offset < len(data):
        count = sock.send(data[offset:])
        if not count:
            raise RuntimeError("Socket closed while sending")
        offset += count


def read_exact(sock, n, pending):
    result = bytearray()
    while pending and len(result) < n:
        take = min(n - len(result), len(pending))
        result.extend(pending[:take])
        del pending[:take]
    while len(result) < n:
        buf = bytearray(n - len(result))
        count = sock.recv_into(buf)
        if not count:
            raise RuntimeError("Socket closed while receiving")
        result.extend(buf[:count])
    return bytes(result)


def send_frame(sock, opcode, payload=b""):
    size = len(payload)
    frame = bytearray([0x80 | opcode])
    if size < 126:
        frame.append(0x80 | size)
    elif size < 65536:
        frame.extend((0x80 | 126, (size >> 8) & 255, size & 255))
    else:
        raise ValueError("Payload too large for this test")
    mask = os.urandom(4)
    frame.extend(mask)
    for i, byte in enumerate(payload):
        frame.append(byte ^ mask[i % 4])
    send_all(sock, frame)


def receive_frame(sock, pending):
    header = read_exact(sock, 2, pending)
    opcode = header[0] & 15
    size = header[1] & 127
    masked = bool(header[1] & 0x80)
    if size == 126:
        ext = read_exact(sock, 2, pending)
        size = (ext[0] << 8) | ext[1]
    elif size == 127:
        raise ValueError("Unexpected large WebSocket frame")
    if size > 8192:
        raise ValueError("Response frame too large: {}".format(size))
    mask = read_exact(sock, 4, pending) if masked else None
    data = bytearray(read_exact(sock, size, pending))
    if mask:
        for i in range(size):
            data[i] ^= mask[i % 4]
    return opcode, bytes(data)


def run():
    print("=== LG webOS pairing v2: CONTROL_INPUT_TV ===")
    print("Wi-Fi connected:", wifi.radio.connected)
    print("Pico IP:", wifi.radio.ipv4_address)
    print("TV:", TV_IP, "port", TV_PORT)
    if not wifi.radio.connected:
        print("FAIL: Wi-Fi not connected")
        return

    pool = socketpool.SocketPool(wifi.radio)
    sock = None
    try:
        sock = pool.socket(pool.AF_INET, pool.SOCK_STREAM)
        sock.settimeout(TIMEOUT_SECONDS)
        print("Connecting TCP...")
        sock.connect((TV_IP, TV_PORT))
        print("TCP connected")

        key = binascii.b2a_base64(os.urandom(16)).strip().decode("ascii")
        request = (
            "GET / HTTP/1.1\r\n"
            "Host: {}:{}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            "Sec-WebSocket-Key: {}\r\n"
            "Sec-WebSocket-Version: 13\r\n\r\n"
        ).format(TV_IP, TV_PORT, key).encode("ascii")
        send_all(sock, request)

        response = bytearray()
        while b"\r\n\r\n" not in response and len(response) < 4096:
            buf = bytearray(512)
            count = sock.recv_into(buf)
            if not count:
                raise RuntimeError("Socket closed during handshake")
            response.extend(buf[:count])
        headers, leftover = bytes(response).split(b"\r\n\r\n", 1)
        print("Handshake:", headers.split(b"\r\n", 1)[0].decode("ascii", "replace"))
        if b" 101 " not in headers.split(b"\r\n", 1)[0]:
            print("FAIL: WebSocket upgrade rejected")
            return
        print("PASS: WebSocket upgraded")

        pending = bytearray(leftover)
        registration = {
            "id": "clonker-register-v2",
            "type": "register",
            "payload": {
                "forcePairing": True,
                "pairingType": "PROMPT",
                "manifest": MANIFEST,
            },
        }
        print("Requesting registration with CONTROL_INPUT_TV...")
        send_frame(sock, 1, json.dumps(registration).encode("utf-8"))
        print("Watch the TV for a pairing approval prompt.")

        deadline = time.monotonic() + PAIRING_WAIT_SECONDS
        sock.settimeout(2)
        while time.monotonic() < deadline:
            try:
                opcode, data = receive_frame(sock, pending)
            except OSError as exc:
                if "timed out" in str(exc).lower() or getattr(exc, "errno", None) in (110, 116):
                    continue
                raise
            if opcode == 9:
                send_frame(sock, 10, data)
                continue
            if opcode == 8:
                print("TV closed WebSocket connection")
                break
            if opcode != 1:
                print("Received WebSocket opcode:", opcode)
                continue
            message = json.loads(data.decode("utf-8"))
            print("TV message type:", message.get("type"))
            if message.get("type") == "registered":
                client_key = message.get("payload", {}).get("client-key")
                print("PASS: TV registration accepted")
                print("CLIENT KEY (save privately):", client_key)
                print("No TV buttons sent; key not stored on Pico")
                break
            if message.get("type") == "error":
                print("TV registration error:", message.get("error", message))
                break
            print("TV response:", str(message)[:500])
        else:
            print("Timed out waiting for registration response")
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
