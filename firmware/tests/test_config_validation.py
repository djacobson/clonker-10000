# The Clonker 10000
# tests/test_config_validation.py
#
# Chapter 12 -- Config v5 validation regression
#
# No network operations or filesystem writes.

import gc
from clonker import device_config as cfg
from clonker.devices import device_types

passed = 0
failed = 0


def check(name, condition):
    global passed, failed

    if condition:
        passed += 1
        print("PASS:", name)
    else:
        failed += 1
        print("FAIL:", name)


def reject(name, config):
    try:
        cfg.validate_config(config)
    except ValueError:
        check(name, True)
    else:
        check(name, False)


def http(path="", method="POST"):
    return {
        "kind": "http",
        "method": method,
        "path": path,
    }


def ssap(uri="", payload=None):
    command = {
        "kind": "ssap",
        "uri": uri,
    }

    if payload is not None:
        command["payload"] = payload

    return command


def pointer(button=""):
    return {
        "kind": "pointer",
        "button": button,
    }


def make_config():
    devices = {
        "device-1": {
            "type": "lg-webos",
            "endpoint": "192.168.1.10:3000",
            "client_key": "PASTE_OR_PAIR_CLIENT_KEY_HERE",
        },
        "device-2": {
            "type": "denon",
            "endpoint": "192.168.1.20:8080",
        },
        "device-3": {
            "type": "roku",
            "endpoint": "192.168.1.30:8060",
        },
    }

    actions = {}

    for action_id in cfg.ACTION_IDS:
        if action_id in ("power-toggle", "mute-toggle"):
            actions[action_id] = {
                "target": "device-2",
                "on_command": http("", "GET"),
                "off_command": http("", "GET"),
            }
        else:
            actions[action_id] = {
                "target": "device-3",
                "command": http(),
            }

    actions["volume-up"] = {
        "target": "device-2",
        "command": http(
            "/goform/formiPhoneAppDirect.xml?MVUP",
            "GET"
        ),
    }

    actions["home"] = {
        "target": "device-3",
        "command": http("/keypress/Home"),
    }

    actions["nav-up"] = {
        "target": "device-1",
        "command": pointer("UP"),
    }

    actions["mute-toggle"] = {
        "target": "device-1",
        "on_command": ssap(
            "ssap://audio/setMute",
            {"mute": True}
        ),
        "off_command": ssap(
            "ssap://audio/setMute",
            {"mute": False}
        ),
    }

    custom_actions = [
        {
            "id": "custom-action-1",
            "name": "Mixed Protocol Test",
            "steps": [
                {
                    "target": "device-1",
                    "command": pointer("HOME"),
                    "wait_after_ms": 1000,
                },
                {
                    "target": "device-1",
                    "command": ssap(
                        "ssap://system.launcher/launch",
                        {"id": "com.webos.app.home"}
                    ),
                    "wait_after_ms": 2000,
                },
                {
                    "target": "device-3",
                    "command": http("/keypress/Home"),
                    "wait_after_ms": 0,
                },
            ],
        },
    ]

    return {
        "version": 5,
        "rooms": {
            "room-2": {
                "name": "Sunroom",
                "devices": devices,
                "actions": actions,
                "custom_actions": custom_actions,
            },
        },
    }


def run():
    gc.collect()
    heap_before = gc.mem_free()

    print()
    print("=== CONFIG V5 VALIDATION ===")
    print()

    # Registry capabilities and runtime availability.

    check("Schema version", cfg.CONFIG_VERSION == 5)

    check(
        "Generic HTTP enabled",
        device_types.is_enabled("generic-http")
    )

    check(
        "LG runtime enabled",
        device_types.is_enabled("lg-webos")
    )

    check(
        "LG SSAP capability",
        device_types.supports_command("lg-webos", "ssap")
    )

    check(
        "LG pointer capability",
        device_types.supports_command("lg-webos", "pointer")
    )

    check(
        "LG rejects HTTP capability",
        not device_types.supports_command("lg-webos", "http")
    )

    # Valid configuration and round trips.

    config = make_config()
    validated = cfg.validate_config(config)

    check("Mixed protocol configuration", validated == config)

    check(
        "Optional rooms and stable room ID",
        list(validated["rooms"]) == ["room-2"]
    )

    room = validated["rooms"]["room-2"]

    check(
        "Device resolution",
        cfg.resolve_device(room, "device-1")["type"]
        == "lg-webos"
    )

    check(
        "Endpoint resolution",
        cfg.resolve_endpoint(room, "device-2")
        == "192.168.1.20:8080"
    )

    serialized = cfg.to_json(validated)

    check(
        "JSON round trip",
        cfg.from_json(serialized) == validated
    )

    check(
        "Revision round trip",
        cfg.revision(validated)
        == cfg.revision(cfg.from_json(serialized))
    )

    print("Fixture bytes:", len(serialized.encode("utf-8")))

    # Blank fundamental commands.

    check("Blank HTTP", cfg.command_is_blank(http()))
    check("Blank SSAP", cfg.command_is_blank(ssap()))
    check("Blank pointer", cfg.command_is_blank(pointer()))

    check(
        "Nonblank HTTP",
        not cfg.command_is_blank(http("/keypress/Home"))
    )

    check(
        "Nonblank SSAP",
        not cfg.command_is_blank(ssap("ssap://audio/volumeUp"))
    )

    check(
        "Nonblank pointer",
        not cfg.command_is_blank(pointer("HOME"))
    )

    room = config["rooms"]["room-2"]

    room["actions"]["nav-up"]["command"] = pointer("")

    room["actions"]["mute-toggle"]["on_command"] = ssap("")

    check(
        "Blank LG fundamental commands accepted",
        cfg.validate_config(config) == config
    )

    # Blank credentials and endpoints.

    room["devices"]["device-1"]["client_key"] = ""
    room["devices"]["device-2"]["endpoint"] = ""

    check(
        "Blank key and endpoint accepted",
        cfg.validate_config(config) == config
    )

    # Independent toggle methods.

    config = make_config()
    room = config["rooms"]["room-2"]

    room["actions"]["power-toggle"] = {
        "target": "device-2",
        "on_command": http("/power/on", "GET"),
        "off_command": http("/power/off", "POST"),
    }

    check(
        "Independent toggle methods",
        cfg.validate_config(config) == config
    )

    # Deterministic payload ordering and nested JSON.

    config = make_config()
    command = config["rooms"]["room-2"]["custom_actions"][0]
    command = command["steps"][1]["command"]

    command["payload"] = {
        "z": [1, True, None, {"b": 2, "a": 1}],
        "a": {"y": False, "x": 1.5},
    }

    revision = cfg.revision(config)

    command["payload"] = {
        "a": {"x": 1.5, "y": False},
        "z": [1, True, None, {"a": 1, "b": 2}],
    }

    check(
        "Canonical nested payload revision",
        cfg.revision(config) == revision
    )

    check(
        "Nested payload round trip",
        cfg.from_json(cfg.to_json(config))
        == cfg.validate_config(config)
    )

    # Invalid configuration cases.

    config = make_config()
    config["version"] = 4
    reject("Reject v4 schema", config)

    config = make_config()
    config["rooms"] = {}
    reject("Reject zero rooms", config)

    config = make_config()
    config["rooms"]["room-4"] = config["rooms"].pop("room-2")
    reject("Reject unknown room ID", config)

    config = make_config()
    room = config["rooms"]["room-2"]
    room["devices"]["device-3"]["type"] = "unknown"
    reject("Reject unknown device type", config)

    config = make_config()
    room = config["rooms"]["room-2"]
    room["devices"]["device-3"]["type"] = "apple-tv"
    reject("Reject unavailable future device", config)

    config = make_config()
    room = config["rooms"]["room-2"]
    room["devices"]["device-3"]["endpoint"] = "999.1.1.1"
    reject("Reject invalid endpoint", config)

    config = make_config()
    room = config["rooms"]["room-2"]
    room["devices"]["device-3"]["client_key"] = "unexpected"
    reject("Reject unrelated device attribute", config)

    config = make_config()
    room = config["rooms"]["room-2"]
    del room["devices"]["device-1"]["client_key"]
    reject("Reject missing LG key field", config)

    config = make_config()
    room = config["rooms"]["room-2"]
    room["actions"]["home"]["target"] = "device-4"
    reject("Reject unknown target", config)

    config = make_config()
    room = config["rooms"]["room-2"]
    room["actions"]["home"]["command"] = pointer("HOME")
    reject("Reject incompatible command kind", config)

    config = make_config()
    room = config["rooms"]["room-2"]
    del room["actions"]["home"]["command"]["kind"]
    reject("Reject missing command kind", config)

    config = make_config()
    room = config["rooms"]["room-2"]
    room["actions"]["home"]["command"] = http("/test", "PUT")
    reject("Reject invalid HTTP method", config)

    config = make_config()
    room = config["rooms"]["room-2"]
    room["actions"]["home"]["command"] = http("keypress/Home")
    reject("Reject invalid HTTP path", config)

    config = make_config()
    room = config["rooms"]["room-2"]
    room["actions"]["nav-up"]["command"] = pointer("UP\n")
    reject("Reject invalid pointer button", config)

    config = make_config()
    room = config["rooms"]["room-2"]
    room["actions"]["mute-toggle"]["on_command"] = ssap(
        "audio/setMute"
    )
    reject("Reject invalid SSAP URI", config)

    config = make_config()
    room = config["rooms"]["room-2"]
    room["actions"]["mute-toggle"]["on_command"] = ssap(
        "ssap://audio/setMute", "not an object"
    )
    reject("Reject invalid SSAP payload", config)

    config = make_config()
    room = config["rooms"]["room-2"]
    room["actions"]["mute-toggle"]["on_command"] = ssap(
        "", {"mute": True}
    )
    reject("Reject payload on blank SSAP URI", config)

    config = make_config()
    room = config["rooms"]["room-2"]
    room["custom_actions"][0]["steps"][0]["command"] = pointer()
    reject("Reject blank custom pointer", config)

    config = make_config()
    room = config["rooms"]["room-2"]
    room["custom_actions"][0]["steps"][1]["command"] = ssap()
    reject("Reject blank custom SSAP", config)

    config = make_config()
    room = config["rooms"]["room-2"]
    room["custom_actions"][0]["steps"][2]["command"] = http()
    reject("Reject blank custom HTTP", config)

    config = make_config()
    room = config["rooms"]["room-2"]
    room["custom_actions"][0]["steps"][0]["wait_after_ms"] = -1
    reject("Reject negative custom wait", config)

    config = make_config()
    room = config["rooms"]["room-2"]
    room["custom_actions"][0]["steps"][2]["wait_after_ms"] = 100
    reject("Reject nonzero final wait", config)

    config = make_config()
    room = config["rooms"]["room-2"]
    room["custom_actions"].append(room["custom_actions"][0])
    reject("Reject duplicate custom ID in room", config)

    config = make_config()
    room = config["rooms"]["room-2"]
    room["custom_actions"][0]["id"] = "Invalid ID"
    reject("Reject invalid custom ID", config)

    # Same custom ID in different rooms remains valid.

    config = make_config()
    second = make_config()
    config["rooms"]["room-1"] = second["rooms"]["room-2"]

    check(
        "Room-local custom ID uniqueness",
        len(cfg.validate_config(config)["rooms"]) == 2
    )

    check(
        "Canonical room ordering",
        list(cfg.validate_config(config)["rooms"])
        == ["room-1", "room-2"]
    )

    del config, second, room, validated, serialized, command

    gc.collect()

    print()
    print("=== RESULTS ===")
    print("Passed:", passed)
    print("Failed:", failed)
    print("Free heap before:", heap_before)
    print("Free heap after:", gc.mem_free())

    if failed == 0:
        print("CONFIG V5 VALIDATION: PASS")
    else:
        print("CONFIG V5 VALIDATION: FAIL")


run()
