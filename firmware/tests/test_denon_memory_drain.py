# The Clonker 10000
# tests/test_denon_memory_drain.py
#
# Chapter 10 -- Operation Catch the Gremlin
# Persistent Denon TCP with receive-buffer draining
#
# Clonker Designed by David Jacobson

import gc
import time
import traceback
import wifi

from clonker import device_config_v2 as device_config
from clonker.devices import denon


ROOM_ID = "room-1"
DEVICE_ID = "device-2"

PAIRS_PER_CYCLE = 30
CYCLES = 3

COMMAND_INTERVAL = 0.10
POLL_INTERVAL = 0.005
SEND_TIMEOUT = 3.0

IDLE_SECONDS = 20
SAMPLE_INTERVAL = 5

# Limit work per drain call so receive processing cannot
# monopolize the main loop in a future implementation.
RX_BUFFER_SIZE = 256
MAX_READS_PER_DRAIN = 8

# CircuitPython socket timeout is normally 1 second.
NORMAL_SOCKET_TIMEOUT = denon.SOCKET_TIMEOUT

_rx_buffer = bytearray(RX_BUFFER_SIZE)
_rx_bytes = 0
_rx_reads = 0
_rx_calls = 0


def sample(label):
    gc.collect()
    free = gc.mem_free()
    allocated = gc.mem_alloc()

    print(
        "MEM:", label,
        "free=", free,
        "allocated=", allocated,
        "total=", free + allocated
    )
    return free


def drain_rx():
    """Read available Denon data without waiting.

    Test-only access to the production adapter socket.
    No production firmware changes are made.
    """
    global _rx_bytes, _rx_reads, _rx_calls

    sock = denon._socket

    if sock is None:
        return

    _rx_calls += 1
    sock.settimeout(0)

    try:
        for _ in range(MAX_READS_PER_DRAIN):
            try:
                count = sock.recv_into(_rx_buffer)
            except OSError as error:
                # EAGAIN / EWOULDBLOCK: no data available.
                # Unexpected socket errors must remain visible.
                if error.errno in (11, 35):
                    break
                raise

            if count == 0:
                raise OSError("Denon closed TCP connection")

            _rx_bytes += count
            _rx_reads += 1

    finally:
        sock.settimeout(NORMAL_SOCKET_TIMEOUT)


def send_when_ready(endpoint, command):
    started = time.monotonic()

    while True:
        if denon.send_volume(endpoint, command):
            drain_rx()
            return

        if time.monotonic() - started > SEND_TIMEOUT:
            raise RuntimeError("Denon pacing timeout")

        time.sleep(POLL_INTERVAL)


def idle_observation(seconds):
    started = time.monotonic()

    while time.monotonic() - started < seconds:
        # Keep draining even while no commands are sent.
        drain_rx()
        time.sleep(SAMPLE_INTERVAL)
        sample("IDLE / SOCKET OPEN")


def run():
    print()
    print("THE CLONKER 10000")
    print("OPERATION CATCH THE GREMLIN")
    print("DENON RX DRAIN EXPERIMENT")
    print("--------------------------------")

    if not wifi.radio.connected:
        print("FAIL: Wi-Fi disconnected")
        return

    settings = device_config.load()
    room = settings["rooms"][ROOM_ID]
    endpoint = room["devices"][DEVICE_ID]

    if not endpoint:
        print("FAIL: Denon endpoint not configured")
        return

    print("Room:", room["name"])
    print("Endpoint:", endpoint)
    print("Pairs per cycle:", PAIRS_PER_CYCLE)
    print("Cycles:", CYCLES)
    print()

    denon.close()
    baseline = sample("BASELINE")

    try:
        for cycle in range(1, CYCLES + 1):
            print()
            print("=== CYCLE", cycle, "===")

            print("PHASE 1: CONNECT")
            denon.connect(endpoint)
            sample("CONNECTED")

            print("PHASE 2: VOLUME COMMANDS")

            for index in range(PAIRS_PER_CYCLE):
                send_when_ready(endpoint, "MVUP")
                time.sleep(COMMAND_INTERVAL)

                send_when_ready(endpoint, "MVDOWN")
                time.sleep(COMMAND_INTERVAL)

                # Drain responses that arrived during pacing.
                drain_rx()

                if (index + 1) % 10 == 0:
                    sample(
                        "ACTIVE PAIR {}".format(index + 1)
                    )

            sample("AFTER COMMANDS")

            print("PHASE 3: IDLE WITH SOCKET OPEN")
            idle_observation(IDLE_SECONDS)

            print("RX calls:", _rx_calls)
            print("RX reads:", _rx_reads)
            print("RX bytes:", _rx_bytes)

            print("PHASE 4: CLOSE SOCKET")
            denon.close()
            sample("AFTER CLOSE")

            time.sleep(2)
            sample("AFTER CLOSE + 2 SEC")

        print()
        print("=== TEST COMPLETE ===")
        final = sample("FINAL")

        print("Baseline free:", baseline)
        print("Final free:", final)
        print("Difference:", final - baseline)

    except Exception as error:
        print()
        print("FAIL:", repr(error))
        traceback.print_exception(
            type(error), error, error.__traceback__
        )

    finally:
        denon.close()
        sample("FINAL CLEANUP")
        print("Denon connection closed")


run()
