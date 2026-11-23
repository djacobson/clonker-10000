"""Standalone LG webOS HOME test, CircuitPython 10.3.1 / Pico 2 W.

Set CLIENT_KEY to the key printed by the successful pairing test.
Copy to /tests/test_lg_webos_home.py and run:
    exec(open('/tests/test_lg_webos_home.py').read())

No production Clonker files are modified.
"""
import binascii
import json
import os
import socketpool
import time
import wifi

TV_IP = "192.168.50.47"
TV_PORT = 3000
CLIENT_KEY = "PASTE_YOUR_CLIENT_KEY_HERE"
TIMEOUT = 5

MANIFEST = {
    "manifestVersion": 1,
    "appVersion": "1.0",
    "appId": "com.clonker.webos.test",
    "appName": "Clonker webOS Test",
    "permissions": [
        "LAUNCH",
        "CONTROL_AUDIO",
        "CONTROL_INPUT_TV",
        "CONTROL_INPUT_TEXT",
        "CONTROL_MOUSE_AND_KEYBOARD",
        "CONTROL_POWER",
        "READ_RUNNING_APPS",
        "READ_INPUT_DEVICE_LIST",
    ],
}


def send_all(sock, data):
    offset = 0
    while offset < len(data):
        n = sock.send(data[offset:])
        if not n:
            raise RuntimeError("Socket closed during send")
        offset += n


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
            raise RuntimeError("Socket closed during receive")
        result.extend(buf[:count])
    return bytes(result)


def send_frame(sock, opcode, payload=b""):
    frame = bytearray([0x80 | opcode])
    size = len(payload)
    if size < 126:
        frame.append(0x80 | size)
    elif size < 65536:
        frame.extend((0x80 | 126, (size >> 8) & 255, size & 255))
    else:
        raise ValueError("Frame too large")
    mask = os.urandom(4)
    frame.extend(mask)
    for i, value in enumerate(payload):
        frame.append(value ^ mask[i % 4])
    send_all(sock, frame)


def receive_frame(sock, pending):
    header = read_exact(sock, 2, pending)
    opcode = header[0] & 15
    length = header[1] & 127
    masked = bool(header[1] & 128)
    if length == 126:
        ext = read_exact(sock, 2, pending)
        length = (ext[0] << 8) | ext[1]
    elif length == 127:
        raise ValueError("Oversized frame")
    if length > 8192:
        raise ValueError("Response too large: {}".format(length))
    mask = read_exact(sock, 4, pending) if masked else None
    data = bytearray(read_exact(sock, length, pending))
    if mask:
        for i in range(length):
            data[i] ^= mask[i % 4]
    return opcode, bytes(data)


def open_ws(pool, host, port, path):
    sock = pool.socket(pool.AF_INET, pool.SOCK_STREAM)
    try:
        sock.settimeout(TIMEOUT)
        sock.connect((host, port))
        key = binascii.b2a_base64(os.urandom(16)).strip().decode("ascii")
        request = (
            "GET {} HTTP/1.1\r\n"
            "Host: {}:{}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            "Sec-WebSocket-Key: {}\r\n"
            "Sec-WebSocket-Version: 13\r\n\r\n"
        ).format(path, host, port, key).encode("ascii")
        send_all(sock, request)
        response = bytearray()
        while b"\r\n\r\n" not in response and len(response) < 4096:
            buf = bytearray(512)
            n = sock.recv_into(buf)
            if not n:
                raise RuntimeError("Socket closed during handshake")
            response.extend(buf[:n])
        if b"\r\n\r\n" not in response:
            raise RuntimeError("Incomplete HTTP upgrade")
        headers, leftover = bytes(response).split(b"\r\n\r\n", 1)
        status = headers.split(b"\r\n", 1)[0]
        print("Handshake:", status.decode("ascii", "replace"))
        if b" 101 " not in status:
            raise RuntimeError("WebSocket upgrade rejected")
        return sock, bytearray(leftover)
    except Exception:
        sock.close()
        raise


def next_json(sock, pending):
    while True:
        opcode, data = receive_frame(sock, pending)
        if opcode == 9:
            send_frame(sock, 10, data)
        elif opcode == 8:
            raise RuntimeError("TV closed WebSocket")
        elif opcode == 1:
            return json.loads(data.decode("utf-8"))


def run():
    print("=== LG webOS HOME test ===")
    print("Pico Wi-Fi:", wifi.radio.connected)
    print("TV:", TV_IP)
    if not wifi.radio.connected:
        print("FAIL: Pico is not connected to Wi-Fi")
        return
    if not CLIENT_KEY or CLIENT_KEY == "PASTE_YOUR_CLIENT_KEY_HERE":
        print("STOP: Paste your pairing client key into CLIENT_KEY first")
        return

    pool = socketpool.SocketPool(wifi.radio)
    control = None
    pointer = None
    try:
        print("Connecting control WebSocket...")
        control, pending = open_ws(pool, TV_IP, TV_PORT, "/")
        registration = {
            "id": "clonker-register-home",
            "type": "register",
            "payload": {
                "forcePairing": False,
                "pairingType": "PROMPT",
                "client-key": CLIENT_KEY,
                "manifest": MANIFEST,
            },
        }
        send_frame(control, 1, json.dumps(registration).encode("utf-8"))
        print("Waiting for registration...")
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            msg = next_json(control, pending)
            kind = msg.get("type")
            print("Registration message:", kind)
            if kind == "registered":
                print("PASS: Authorized")
                break
            if kind == "error":
                raise RuntimeError("Registration error: {}".format(msg.get("error", msg)))
        else:
            raise RuntimeError("Registration timed out")

        request = {
            "id": "clonker-pointer-1",
            "type": "request",
            "uri": "ssap://com.webos.service.networkinput/getPointerInputSocket",
        }
        print("Requesting pointer-input socket...")
        send_frame(control, 1, json.dumps(request).encode("utf-8"))
        deadline = time.monotonic() + 15
        socket_url = None
        while time.monotonic() < deadline:
            msg = next_json(control, pending)
            if msg.get("id") != request["id"]:
                print("Other TV message:", msg.get("type"))
                continue
            if msg.get("type") == "error":
                raise RuntimeError("Pointer request error: {}".format(msg.get("error", msg)))
            payload = msg.get("payload", {})
            if payload.get("returnValue") is False:
                raise RuntimeError("Pointer request failed: {}".format(payload))
            socket_url = payload.get("socketPath")
            break
        if not socket_url:
            raise RuntimeError("TV did not return pointer socket URL")
        print("Pointer URL received")
        print("URL scheme:", socket_url.split(":", 1)[0])
        if not socket_url.startswith("ws://"):
            raise RuntimeError("Pointer URL requires TLS or unexpected scheme: {}".format(socket_url.split(":", 1)[0]))

        # Expected form: ws://host:port/path
        remainder = socket_url[5:]
        authority, slash, path = remainder.partition("/")
        host, colon, port_text = authority.partition(":")
        port = int(port_text) if colon else 80
        path = "/" + path if slash else "/"
        print("Connecting pointer WebSocket on port", port)
        pointer, pointer_pending = open_ws(pool, host, port, path)
        print("PASS: Pointer socket connected")
        print("Sending HOME...")
        send_frame(pointer, 1, b"type:button\nname:HOME\n\n")
        print("HOME sent. Check the LG screen!")
        time.sleep(1)
    except Exception as exc:
        print("TEST ERROR:", type(exc).__name__, str(exc))
    finally:
        for sock in (pointer, control):
            if sock is not None:
                try:
                    sock.close()
                except Exception:
                    pass
        print("Sockets closed. Test complete.")


run()
