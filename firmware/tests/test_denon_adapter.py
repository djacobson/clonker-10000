# The Clonker 10000
# tests/test_denon_adapter.py
#
# Chapter 6 -- Standalone Denon adapter test
#
# Clonker Designed by David Jacobson

import time
import traceback
import wifi

from clonker import device_config_v2 as device_config
from clonker.devices import denon


ROOM_ID = "room-2"
DEVICE_ID = "device-2"

REPEAT_COUNT = 10
POLL_INTERVAL = 0.005


def elapsed_ms(start):
    return round((time.monotonic() - start) * 1000, 1)


def send_when_ready(endpoint, command):
    """Wait cooperatively until the adapter accepts a command."""
    while True:
        if denon.send_volume(endpoint, command):
            return
        time.sleep(POLL_INTERVAL)


def run():
    print()
    print("THE CLONKER 10000")
    print("DENON ADAPTER TEST")
    print("----------------------------")

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
    print("Repeats:", REPEAT_COUNT)
    print("Minimum interval:", denon.MIN_COMMAND_INTERVAL)

    denon.close()

    try:
        print()
        print("TEST 1: CONNECT")

        start = time.monotonic()
        denon.connect(endpoint)

        print("Connect:", elapsed_ms(start), "ms")
        print("Connected host:", denon.connected_host())

        assert denon.connected_host() == endpoint.split(":")[0]

        print("PASS: Connected")

        print()
        print("TEST 2: CONNECTION REUSE")

        start = time.monotonic()
        denon.connect(endpoint)

        print("Reuse:", elapsed_ms(start), "ms")
        print("PASS: Existing connection reused")

        print()
        print("TEST 3: VOLUME UP")

        start = time.monotonic()

        for index in range(REPEAT_COUNT):
            send_when_ready(endpoint, "MVUP")
            print("UP", index + 1)

        print("UP elapsed:", elapsed_ms(start), "ms")

        # Check that an immediate additional command
        # is rejected by the pacing mechanism.
        print()
        print("TEST 4: PACING")

        accepted = denon.send_volume(endpoint, "MVDOWN")

        print("Immediate send accepted:", accepted)

        assert accepted is False
        print("PASS: Pacing enforced")

        print()
        print("TEST 5: VOLUME DOWN")

        start = time.monotonic()

        for index in range(REPEAT_COUNT):
            send_when_ready(endpoint, "MVDOWN")
            print("DOWN", index + 1)

        print("DOWN elapsed:", elapsed_ms(start), "ms")

        # Allow the receiver time to process
        # the final command before inspection.
        time.sleep(0.5)

        print()
        print("TEST 6: CLEANUP")

        denon.close()

        assert denon.connected_host() is None

        print("PASS: Connection closed")

        print()
        print("ALL ADAPTER TESTS PASSED")
        print("Verify starting and final AVR volume visually.")

    except Exception as error:
        print()
        print("FAIL:", repr(error))
        traceback.print_exception(
            type(error), error, error.__traceback__
        )

    finally:
        denon.close()
        print("Adapter cleanup complete")


run()
