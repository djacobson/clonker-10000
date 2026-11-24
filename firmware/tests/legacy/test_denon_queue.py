# The Clonker 10000
# tests/test_denon_queue.py
#
# Chapter 6 -- Denon TCP / Dumb Queue integration
#
# Clonker Designed by David Jacobson

import time
import traceback
import wifi

from clonker import actions
from clonker import device_adapters
from clonker import device_config_v2 as config
from clonker.devices import denon


ROOM_ID = "room-2"
REPEAT_COUNT = 5
TEST_TIMEOUT = 10.0


def run():
    print()
    print("THE CLONKER 10000")
    print("DENON TCP / DUMB QUEUE TEST")
    print("--------------------------------")

    if not wifi.radio.connected:
        print("FAIL: Wi-Fi disconnected")
        return

    try:
        config.load()

        assert device_adapters.lookup(
            ROOM_ID, "volume-up"
        ) == device_adapters.DENON_TCP

        assert device_adapters.lookup(
            ROOM_ID, "volume-down"
        ) == device_adapters.DENON_TCP

        print("PASS: Denon adapters selected")

        actions.clear("Integration test setup")
        denon.close()

        print()
        print("TEST 1: QUEUE VOLUME COMMANDS")

        for index in range(REPEAT_COUNT):
            actions.dispatch(ROOM_ID, "volume-up")

        for index in range(REPEAT_COUNT):
            actions.dispatch(ROOM_ID, "volume-down")

        assert actions.status()["depth"] == (
            REPEAT_COUNT * 2
        )

        print("PASS: 10 commands queued")

        print()
        print("TEST 2: EXECUTE QUEUE")

        start = time.monotonic()
        completed = 0
        pacing_waits = 0

        while actions.status()["depth"] > 0:
            if time.monotonic() - start > TEST_TIMEOUT:
                raise RuntimeError("Queue test timed out")

            before = actions.status()["depth"]

            executed = actions.poll()

            after = actions.status()["depth"]

            if after < before:
                completed += before - after
                print(
                    "Completed:", completed,
                    "Remaining:", after
                )
            elif not executed:
                pacing_waits += 1

            if actions.status()["last_error"]:
                raise RuntimeError(
                    actions.status()["last_error"]
                )

            time.sleep(0.005)

        elapsed = round(
            (time.monotonic() - start) * 1000, 1
        )

        print()
        print("Elapsed:", elapsed, "ms")
        print("Pacing waits:", pacing_waits)
        print("Completed:", completed)

        assert completed == REPEAT_COUNT * 2
        assert pacing_waits > 0

        print("PASS: Queue drained with pacing")

        print()
        print("TEST 3: CONNECTION REUSE")

        room = config.current()["rooms"][ROOM_ID]
        endpoint = room["devices"]["device-2"]

        expected_host = endpoint.split(":")[0]

        print("Expected host:", expected_host)
        print("Active host:", denon.connected_host())

        assert denon.connected_host() == expected_host

        print("PASS: Persistent connection active")

        print()
        print("TEST 4: FINAL QUEUE STATUS")

        result = actions.status()

        print("Queue depth:", result["depth"])
        print("Last result:", result["last_result"])
        print("Last error:", result["last_error"])

        assert result["depth"] == 0
        assert result["last_error"] is None

        print("PASS")

        print()
        print("ALL INTEGRATION TESTS PASSED")
        print("Verify AVR returned to starting volume.")

    except Exception as error:
        print()
        print("FAIL:", repr(error))
        traceback.print_exception(
            type(error), error, error.__traceback__
        )

    finally:
        actions.clear("Integration test cleanup")
        denon.close()
        print("Connection and queue cleaned up")


run()
