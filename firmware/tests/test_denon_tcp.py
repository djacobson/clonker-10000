# The Clonker 10000
# tests/test_denon_tcp.py
#
# Chapter 6 -- Denon TCP protocol experiment
# Read-only test: MV? volume query.

import time
import wifi
import socketpool

from clonker import device_config_v2 as device_config


ROOM_ID = "room-2"       # Sunroom
DENON_DEVICE = "device-2"
DENON_TCP_PORT = 23
SOCKET_TIMEOUT = 1.0


def elapsed_ms(start):
    return round((time.monotonic() - start) * 1000, 1)


def run():
    print()
    print("THE CLONKER 10000")
    print("DENON TCP TEST -- MV?")
    print("----------------------------")

    if not wifi.radio.connected:
        print("FAIL: Wi-Fi is not connected")
        return

    settings = device_config.load()
    room = settings["rooms"][ROOM_ID]
    endpoint = room["devices"][DENON_DEVICE]

    if not endpoint:
        print("FAIL: Denon endpoint not configured")
        return

    host = endpoint.split(":")[0]

    print("Room:", room["name"])
    print("Denon:", host)
    print("TCP port:", DENON_TCP_PORT)

    pool = socketpool.SocketPool(wifi.radio)
    sock = None

    try:
        sock = pool.socket(pool.AF_INET, pool.SOCK_STREAM)
        sock.settimeout(SOCKET_TIMEOUT)

        start = time.monotonic()
        sock.connect((host, DENON_TCP_PORT))

        print("Connected in", elapsed_ms(start), "ms")

        command = b"MV?\r"

        start = time.monotonic()
        sock.sendall(command)

        print("Sent:", repr(command))

        response = bytearray(128)
        count = sock.recv_into(response)

        print("Response time:", elapsed_ms(start), "ms")

        if count <= 0:
            print("FAIL: Connection closed without response")
            return

        data = bytes(response[:count])
        print("Received:", repr(data))

        if b"MV" in data:
            print("PASS: Denon volume response received")
        else:
            print("CHECK: Unexpected response")

    except Exception as exc:
        print("FAIL:", repr(exc))

    finally:
        if sock is not None:
            try:
                sock.close()
            except OSError:
                pass

        print("Connection closed")
        print("TEST COMPLETE")


run()
