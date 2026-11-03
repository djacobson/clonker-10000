# The Clonker 10000
# tests/test_queue_regression.py
#
# Chapter 6 -- Dumb Queue regression tests
#
# Clonker Designed by David Jacobson

import time
import traceback

from clonker import actions
from clonker import device_config_v2 as config
from clonker.net import http_transport
from clonker.devices import denon

ROOM = "room-2"
CUSTOM = "custom-action-1"

events = []
allow_denon = True

original_http = http_transport.send
original_denon = denon.send_volume
original_ready = denon.ready


def fake_http(endpoint, method, path):
    events.append(("HTTP", path))
    return {"status": 200, "total_ms": 0.0}


def fake_denon(endpoint, command):
    events.append(("TCP", command))
    return True


def fake_ready():
    return allow_denon


def drain(timeout=5):
    start = time.monotonic()
    while actions.status()["depth"]:
        if time.monotonic() - start > timeout:
            raise RuntimeError("Queue did not drain")
        actions.poll()
        if actions.status()["last_error"]:
            raise RuntimeError(actions.status()["last_error"])
        time.sleep(0.005)


def reset():
    global allow_denon
    allow_denon = True
    events.clear()
    actions.clear("Regression test reset")


def run():
    global allow_denon

    print()
    print("THE CLONKER 10000")
    print("DUMB QUEUE REGRESSION TEST")
    print("----------------------------")

    try:
        config.load()

        # No actual network commands are sent.
        http_transport.send = fake_http
        denon.send_volume = fake_denon
        denon.ready = fake_ready

        print()
        print("TEST 1: MIXED COMMAND ORDER")
        reset()

        actions.dispatch(ROOM, "volume-up")
        actions.dispatch(ROOM, "home")
        actions.dispatch(ROOM, "volume-down")
        drain()

        assert events == [
            ("TCP", "MVUP"),
            ("HTTP", "/keypress/Home"),
            ("TCP", "MVDOWN"),
        ], events
        print("PASS")

        print()
        print("TEST 2: PACING HOLDS QUEUE")
        reset()

        actions.dispatch(ROOM, "volume-up")
        actions.dispatch(ROOM, "home")

        allow_denon = False

        assert actions.poll() is False
        assert actions.status()["depth"] == 2
        assert events == []

        allow_denon = True
        drain()

        assert events == [
            ("TCP", "MVUP"),
            ("HTTP", "/keypress/Home"),
        ], events
        print("PASS")

        print()
        print("TEST 3: FUTURE TASK DOES NOT BLOCK")
        reset()

        actions.dispatch(
            ROOM, "volume-up", delay_seconds=1
        )
        actions.dispatch(ROOM, "home")

        assert actions.poll() is True
        assert events == [
            ("HTTP", "/keypress/Home")
        ], events
        assert actions.status()["depth"] == 1

        drain(timeout=3)

        assert events[-1] == ("TCP", "MVUP")
        print("PASS")

        print()
        print("TEST 4: DELAYED CUSTOM ACTION")
        reset()

        room = config.current()["rooms"][ROOM]
        custom = next(
            item for item in room["custom_actions"]
            if item["id"] == CUSTOM
        )
        steps = custom["steps"]

        assert len(steps) == 2
        assert steps[0]["wait_after_ms"] == 3000

        actions.dispatch(ROOM, CUSTOM)

        # First custom step executes immediately.
        assert actions.poll() is True
        assert events == [
            ("HTTP", steps[0]["path"])
        ], events

        # Custom task remains queued during its wait.
        assert actions.status()["depth"] == 1

        # Immediate volume command can run during wait.
        actions.dispatch(ROOM, "volume-up")
        assert actions.poll() is True

        assert events[-1] == ("TCP", "MVUP")
        assert actions.status()["depth"] == 1

        # Wait for the delayed second custom step.
        drain(timeout=5)

        assert events == [
            ("HTTP", steps[0]["path"]),
            ("TCP", "MVUP"),
            ("HTTP", steps[1]["path"]),
        ], events
        print("PASS")

        print()
        print("TEST 5: ERROR CANCELS PENDING WORK")
        reset()

        def failing_http(endpoint, method, path):
            raise OSError("Simulated HTTP failure")

        http_transport.send = failing_http

        actions.dispatch(ROOM, "home")
        actions.dispatch(ROOM, "volume-up")

        assert actions.poll() is True
        result = actions.status()

        assert result["depth"] == 0
        assert result["last_error"] is not None
        assert "Simulated HTTP failure" in result["last_error"]

        print("PASS")

        print()
        print("ALL QUEUE REGRESSION TESTS PASSED")

    except Exception as error:
        print()
        print("FAIL:", repr(error))
        traceback.print_exception(
            type(error), error, error.__traceback__
        )

    finally:
        # Always restore real transport functions.
        http_transport.send = original_http
        denon.send_volume = original_denon
        denon.ready = original_ready

        actions.clear("Regression test cleanup")
        print("Real transports restored")
        print("Queue cleaned up")


run()
