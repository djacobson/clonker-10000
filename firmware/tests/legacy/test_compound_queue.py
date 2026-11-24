# The Clonker 10000
# Phase 3B.3 -- Compound Queue Tests
#
# No real HTTP commands. No config file writes.
# Run while the main application is stopped.

from clonker import actions
from clonker import device_config_v2 as config

original_send = actions.http_transport.send
original_config = config._current
original_queue = list(actions._queue)
original_last_result = actions._last_result
original_last_error = actions._last_error
original_peak = actions._peak_depth

calls = []
fail_next = False
passed = 0
failed = 0


def fake_send(endpoint, method, path):
    global fail_next

    calls.append((endpoint, method, path))

    if fail_next:
        fail_next = False
        raise OSError("Simulated HTTP failure")

    return {"status": 200, "total_ms": 1}


def check(label, condition):
    global passed, failed

    if condition:
        passed += 1
        print("PASS:", label)
    else:
        failed += 1
        print("FAIL:", label)


def make_config():
    fundamental = {}

    for action_id in config.ACTION_IDS:
        if action_id in ("mute-toggle", "power-toggle"):
            fundamental[action_id] = {
                "target": "device-2",
                "method": "GET",
                "on_path": "",
                "off_path": "",
            }
        else:
            fundamental[action_id] = {
                "target": "device-2",
                "method": "GET",
                "path": "",
            }

    fundamental["volume-up"]["path"] = "/goform/formiPhoneAppDirect.xml?MVUP"

    return {
        "version": config.CONFIG_VERSION,
        "rooms": {
            "room-2": {
                "name": "Sunroom",
                "devices": {
                    "device-1": "",
                    "device-2": "192.168.50.40:8080",
                    "device-3": "192.168.50.28:8060",
                },
                "actions": fundamental,
                "custom_actions": [
                    {
                        "id": "sunroom-movie",
                        "name": "Sunroom Movie Mode",
                        "steps": [
                            {
                                "target": "device-3",
                                "method": "POST",
                                "path": "/keypress/Home",
                                "wait_after_ms": 3000,
                            },
                            {
                                "target": "device-2",
                                "method": "GET",
                                "path": "/goform/formiPhoneAppDirect.xml?MSQUICK1",
                                "wait_after_ms": 0,
                            },
                        ],
                    }
                ],
            }
        },
    }


def reset():
    global fail_next
    actions.clear("Test reset")
    calls.clear()
    fail_next = False


print("CLONKER -- COMPOUND QUEUE TESTS")
print("--------------------------------")

try:
    config._current = config.validate_config(make_config())
    actions.http_transport.send = fake_send
    actions.clear("Test setup")

    # Test 1: Custom action is admitted.
    result = actions.dispatch("room-2", "sunroom-movie")
    check("Custom dispatch", result["ok"] and result["configured"])
    check("One queue entry", actions.status()["depth"] == 1)

    # Test 2: First command executes.
    actions.poll()

    check(
        "Roku Home executed first",
        len(calls) == 1
        and calls[0][1:] == ("POST", "/keypress/Home"),
    )

    check(
        "Next step scheduled",
        len(actions._queue) == 1
        and actions._queue[0]["step"] == 1
        and actions._queue[0]["due"] > actions.time.monotonic(),
    )

    # Test 3: The pending wait does not execute early.
    check("Wait is nonblocking", actions.poll() is False)

    # Test 4: Unrelated command runs during the wait.
    actions.dispatch("room-2", "volume-up")
    actions.poll()

    check(
        "Volume interleaves",
        len(calls) == 2
        and "MVUP" in calls[1][2],
    )

    # Simulate the three-second deadline expiring.
    # No real three-second sleep is necessary.
    actions._queue[0]["due"] = 0
    actions.poll()

    check(
        "Denon Quick Select executes last",
        len(calls) == 3
        and calls[2][1:] == (
            "GET",
            "/goform/formiPhoneAppDirect.xml?MSQUICK1",
        ),
    )

    check("Compound task completes", actions.status()["depth"] == 0)

    # Test 5: Clearing cancels an unfinished compound action.
    reset()
    actions.dispatch("room-2", "sunroom-movie")
    actions.poll()
    actions.clear("Cancellation test")

    check("Clear cancels pending step", actions.status()["depth"] == 0)
    check("Cancelled step does not run", actions.poll() is False)

    # Test 6: An HTTP failure clears the queue.
    reset()
    actions.dispatch("room-2", "sunroom-movie")
    actions.dispatch("room-2", "volume-up")

    fail_next = True
    actions.poll()

    check("HTTP failure clears queue", actions.status()["depth"] == 0)
    check("Failure recorded", actions.status()["last_error"] is not None)

    # Test 7: Unknown custom actions are rejected.
    reset()

    try:
        actions.dispatch("room-2", "nonexistent-action")
        rejected = False
    except ValueError:
        rejected = True

    check("Unknown custom action rejected", rejected)

finally:
    # Restore the imported modules' original state.
    actions.http_transport.send = original_send
    config._current = original_config
    actions._queue[:] = original_queue
    actions._last_result = original_last_result
    actions._last_error = original_last_error
    actions._peak_depth = original_peak

print("--------------------------------")
print("PASSED: {}  FAILED: {}".format(passed, failed))
print("Original runtime state restored.")
