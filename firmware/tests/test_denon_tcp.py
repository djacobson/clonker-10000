# The Clonker 10000
# tests/test_denon_tcp.py
#
# Chapter 6 -- Denon persistent TCP volume experiment
#
# Clonker Designed by David Jacobson

import time
import wifi
import socketpool

from clonker import device_config_v2 as device_config


ROOM_ID = "room-2"
DENON_DEVICE = "device-2"
DENON_TCP_PORT = 23

SOCKET_TIMEOUT = 1.0
REPEAT_COUNT = 5
COMMAND_INTERVAL = 0.10

# Safety limit for this experiment.
MAX_REPEATS = 10


def elapsed_ms(start):
    return round((time.monotonic() - start) * 1000, 1)


def read_messages(sock, wait_seconds=0.15):
    """Collect complete CR-terminated Denon messages.

    TCP is a byte stream: messages may be split or combined.
    """
    deadline = time.monotonic() + wait_seconds
    buffer = bytearray()
    chunk = bytearray(128)
    messages = []

    while time.monotonic() < deadline:
        remaining = deadline - time.monotonic()
        sock.settimeout(SOCKET_TIMEOUT)

        try:
            count = sock.recv_into(chunk)
        except OSError:
            # A socket timeout is expected while collecting
            # optional asynchronous Denon status messages.
            continue

        if count == 0:
            raise OSError("Denon closed TCP connection")

        buffer.extend(chunk[:count])

        while 13 in buffer:
            end = buffer.index(13)
            message = bytes(buffer[:end])
            del buffer[:end + 1]

            if message:
                messages.append(message)

    return messages


def send_command(sock, command):
    """Send one command and report timing."""
    data = (command + "\r").encode("ascii")

    start = time.monotonic()
    sock.sendall(data)
    send_ms = elapsed_ms(start)

    print(
        "{} sent in {} ms".format(command, send_ms)
    )


def volume_query(sock):
    """Query and display current Denon volume."""
    send_command(sock, "MV?")

    messages = read_messages(sock, 0.25)

    for message in messages:
        print("  RX:", repr(message))

    for message in reversed(messages):
        if (
            message.startswith(b"MV")
            and message[2:].isdigit()
        ):
            return int(message[2:])

    return None


def repeat_commands(sock, command, count):
    """Send repeated commands on one TCP connection."""
    print()
    print("REPEAT:", command, "x", count)

    start = time.monotonic()

    for index in range(count):
        command_start = time.monotonic()

        send_command(sock, command)

        # Maintain a conservative minimum command interval.
        remaining = (
            COMMAND_INTERVAL -
            (time.monotonic() - command_start)
        )

        if remaining > 0:
            time.sleep(remaining)

    total_ms = elapsed_ms(start)

    print(
        "TOTAL: {} commands in {} ms".format(
            count, total_ms
        )
    )

    print(
        "AVERAGE: {} ms/command".format(
            round(total_ms / count, 1)
        )
    )

    messages = read_messages(sock, 0.3)

    for message in messages:
        print("  RX:", repr(message))

    return total_ms


def run():
    print()
    print("THE CLONKER 10000")
    print("DENON TCP REPEAT TEST")
    print("----------------------------")

    if REPEAT_COUNT < 1 or REPEAT_COUNT > MAX_REPEATS:
        print("FAIL: Invalid repeat count")
        return

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

        print()
        print("STARTING VOLUME")
        starting_volume = volume_query(sock)
        print("Starting:", starting_volume)

        if starting_volume is None:
            print("FAIL: Could not read starting volume")
            return

        # Avoid increasing volume near the receiver's maximum.
        if starting_volume > 75:
            print("ABORT: Starting volume too high")
            return

        repeat_commands(sock, "MVUP", REPEAT_COUNT)

        # Let the receiver settle before reversing direction.
        time.sleep(0.3)

        repeat_commands(sock, "MVDOWN", REPEAT_COUNT)

        time.sleep(0.3)

        print()
        print("FINAL VOLUME")
        final_volume = volume_query(sock)
        print("Final:", final_volume)

        if final_volume == starting_volume:
            print("PASS: Volume returned to starting level")
        else:
            print("CHECK: Volume differs from starting level")

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
