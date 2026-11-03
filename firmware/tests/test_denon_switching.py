# The Clonker 10000
# tests/test_denon_switching.py
#
# Chapter 6 -- Denon adapter receiver switching
#
# Clonker Designed by David Jacobson

import time
import traceback
import wifi

from clonker import device_config_v2 as device_config
from clonker.devices import denon


SUNROOM_ID = "room-2"
LIVING_ROOM_ID = "room-1"
DEVICE_ID = "device-2"


def elapsed_ms(start):
    return round((time.monotonic() - start) * 1000, 1)


def check_connection(label, endpoint):
    expected_host = endpoint.split(":")[0]

    print()
    print(label)
    print("Endpoint:", endpoint)

    start = time.monotonic()
    denon.connect(endpoint)
    duration = elapsed_ms(start)

    actual_host = denon.connected_host()

    print("Connect time:", duration, "ms")
    print("Active host:", actual_host)

    assert actual_host == expected_host
    print("PASS")


def run():
    print()
    print("THE CLONKER 10000")
    print("DENON RECEIVER SWITCHING TEST")
    print("--------------------------------")

    if not wifi.radio.connected:
        print("FAIL: Wi-Fi disconnected")
        return

    config = device_config.load()

    sunroom = config["rooms"][SUNROOM_ID]
    living_room = config["rooms"][LIVING_ROOM_ID]

    sunroom_endpoint = sunroom["devices"][DEVICE_ID]
    living_room_endpoint = living_room["devices"][DEVICE_ID]

    assert sunroom_endpoint
    assert living_room_endpoint

    assert (
        sunroom_endpoint.split(":")[0]
        != living_room_endpoint.split(":")[0]
    ), "Both rooms have the same receiver IP"

    denon.close()

    try:
        check_connection(
            "TEST 1: CONNECT SUNROOM",
            sunroom_endpoint
        )

        check_connection(
            "TEST 2: REUSE SUNROOM",
            sunroom_endpoint
        )

        check_connection(
            "TEST 3: SWITCH TO LIVING ROOM",
            living_room_endpoint
        )

        check_connection(
            "TEST 4: REUSE LIVING ROOM",
            living_room_endpoint
        )

        check_connection(
            "TEST 5: SWITCH BACK TO SUNROOM",
            sunroom_endpoint
        )

        print()
        print("TEST 6: CLOSE")

        denon.close()

        assert denon.connected_host() is None

        print("PASS: Connection closed")

        print()
        print("ALL SWITCHING TESTS PASSED")

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
