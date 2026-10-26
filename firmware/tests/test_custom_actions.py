# The Clonker 10000
# Phase 3A.2 -- Custom Action Validation Tests
#
# Disposable test. No configuration files are modified.

from clonker import device_config_v2 as config
import json


def make_config():
    actions = {}

    for action_id in config.ACTION_IDS:
        if action_id in ("mute-toggle", "power-toggle"):
            actions[action_id] = {
                "target": "device-2",
                "method": "GET",
                "on_path": "",
                "off_path": "",
            }
        else:
            actions[action_id] = {
                "target": "device-2",
                "method": "GET",
                "path": "",
            }

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
                "actions": actions,
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


passed = 0
failed = 0


def check(label, change=None, should_pass=True):
    global passed, failed

    # Build fresh data for each test.
    data = make_config()

    if change is not None:
        change(data)

    try:
        normalized = config.validate_config(data)
        encoded = config.to_json(normalized)
        decoded = config.from_json(encoded)

        if decoded != normalized:
            raise AssertionError("Round-trip mismatch")

        if not should_pass:
            raise AssertionError("Invalid configuration accepted")

        result = "PASS"

    except ValueError as error:
        if should_pass:
            result = "FAIL: " + str(error)
        elif str(error) == "Invalid configuration accepted":
            result = "FAIL: " + str(error)
        else:
            result = "PASS (rejected: {})".format(error)

    except Exception as error:
        result = "FAIL: " + repr(error)

    if result.startswith("PASS"):
        passed += 1
    else:
        failed += 1

    print("{}: {}".format(label, result))


def first_action(data):
    return data["rooms"]["room-2"]["custom_actions"][0]


def first_step(data):
    return first_action(data)["steps"][0]


print("CLONKER -- CONFIG v4 VALIDATION TESTS")
print("------------------------------------")

check("Valid Sunroom Movie Mode")

check(
    "Invalid action ID",
    lambda d: first_action(d).update(id="Bad ID"),
    False,
)

check(
    "Duplicate action ID",
    lambda d: d["rooms"]["room-2"]["custom_actions"].append(
        first_action(d).copy()
    ),
    False,
)

check(
    "Unknown destination",
    lambda d: first_step(d).update(target="device-4"),
    False,
)

check(
    "Invalid HTTP method",
    lambda d: first_step(d).update(method="DELETE"),
    False,
)

check(
    "Excessive wait",
    lambda d: first_step(d).update(wait_after_ms=60001),
    False,
)

check(
    "Negative wait",
    lambda d: first_step(d).update(wait_after_ms=-1),
    False,
)

check(
    "Boolean wait",
    lambda d: first_step(d).update(wait_after_ms=True),
    False,
)

check(
    "Nonzero final wait",
    lambda d: first_action(d)["steps"][-1].update(
        wait_after_ms=1000
    ),
    False,
)

check(
    "Empty custom path",
    lambda d: first_step(d).update(path=""),
    False,
)

check(
    "Empty steps",
    lambda d: first_action(d).update(steps=[]),
    False,
)

check(
    "Single-step action",
    lambda d: first_action(d).update(
        steps=[first_action(d)["steps"][-1]]
    ),
)

check(
    "No custom actions",
    lambda d: d["rooms"]["room-2"].update(custom_actions=[]),
)

print("------------------------------------")
print("PASSED: {}  FAILED: {}".format(passed, failed))
print("Serialized bytes: {}".format(
    len(config.to_json(make_config()).encode("utf-8"))
))
print("Active configuration untouched.")
