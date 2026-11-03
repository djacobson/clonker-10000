# The Clonker 10000
# tests/test_denon_tcp.py
#
# Chapter 6 -- Denon TCP volume repeat experiment
#
# Clonker Designed by David Jacobson

import time
import traceback
import wifi
import socketpool

from clonker import device_config_v2 as device_config


ROOM_ID = "room-2"
DENON_DEVICE = "device-2"
DENON_TCP_PORT = 23

SOCKET_TIMEOUT = 1.0
REPEAT_COUNT = 10
COMMAND_INTERVAL = 0.05


def elapsed_ms(start):
    return round((time.monotonic() - start) * 1000, 1)


def send_command(sock, command):
    data = (command + "\r").encode("ascii")
    start = time.monotonic()
    sock.sendall(data)
    return elapsed_ms(start)


def read_response(sock):
    """Read available TCP data using known-working calls."""
    response = bytearray(256)
    count = sock.recv_into(response)

    if count <= 0:
        raise OSError("Denon closed connection")

    return bytes(response[:count])


def query_volume(sock, label):
    """Query volume and print raw Denon status messages."""
    print()
    print(label)

    send_command(sock, "MV?")
    data = read_response(sock)

    print("RX:", repr(data))

    # TCP can contain multiple status messages.
    # This is diagnostic, not a guaranteed synchronized
    # response to the latest MV? query.
    values = []

    for message in data.split(b"\r"):
        if (
            message.startswith(b"MV")
            and message[2:].isdigit()
        ):
            values.append(message[2:].decode("ascii"))

    if values:
        print("Volume reports:", values)
    else:
        print("No complete volume report in this read")

    return values


def repeat_commands(sock, command, count):
    print()
    print("REPEAT:", command, "x", count)

    start = time.monotonic()

    for index in range(count):
        sent_ms = send_command(sock, command)

        print(
            "  {}: send {} ms".format(
                index + 1, sent_ms
            )
        )

        time.sleep(COMMAND_INTERVAL)

    total_ms = elapsed_ms(start)

    print("TOTAL:", total_ms, "ms")
    print(
        "AVERAGE:",
        round(total_ms / count, 1),
        "ms/command"
    )


def run():
    print()
    print("THE CLONKER 10000")
    print("DENON TCP REPEAT TEST")
    print("----------------------------")

    if not wifi.radio.connected:
        print("FAIL: Wi-Fi disconnected")
        return

    settings = device_config.load()
    room = settings["rooms"][ROOM_ID]
    endpoint = room["devices"][DENON_DEVICE]

    if not endpoint:
        print("FAIL: Denon not configured")
        return

    host = endpoint.split(":")[0]

    print("Room:", room["name"])
    print("Denon:", host)
    print("TCP port:", DENON_TCP_PORT)
    print("Repeats:", REPEAT_COUNT)
    print("Interval:", COMMAND_INTERVAL, "seconds")

    pool = socketpool.SocketPool(wifi.radio)
    sock = None

    try:
        sock = pool.socket(pool.AF_INET, pool.SOCK_STREAM)
        sock.settimeout(SOCKET_TIMEOUT)

        start = time.monotonic()
        sock.connect((host, DENON_TCP_PORT))

        print("Connected in", elapsed_ms(start), "ms")

        query_volume(sock, "STARTING VOLUME")

        print()
        print("BEGINNING REPEAT TEST")

        repeat_commands(sock, "MVUP", REPEAT_COUNT)

        time.sleep(0.5)
        query_volume(sock, "AFTER VOLUME UP")

        repeat_commands(sock, "MVDOWN", REPEAT_COUNT)

        time.sleep(0.5)
        query_volume(sock, "FINAL VOLUME")

        print()
        print("TEST COMPLETE")

    except Exception as exc:
        print()
        print("FAIL:", repr(exc))
        traceback.print_exception(
            type(exc), exc, exc.__traceback__
        )

    finally:
        if sock is not None:
            try:
                sock.close()
            except OSError:
                pass

        print("Connection closed")


run()
