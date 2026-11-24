# The Clonker 10000
# tests/test_typed_adapters.py
#
# Chapter 12 -- Typed adapter selection regression
#
# No network operations or filesystem writes.

import gc

from clonker import device_config as cfg
from clonker.devices import device_adapters as adapters

passed = 0
failed = 0

DENON_UP = "/goform/formiPhoneAppDirect.xml?MVUP"
DENON_DOWN = "/goform/formiPhoneAppDirect.xml?MVDOWN"

ROKU_UP = "/keypress/VolumeUp"
ROKU_DOWN = "/keypress/VolumeDown"

HTTP = adapters.GENERIC_HTTP
TCP = adapters.DENON_TCP
VOLUME = adapters.ROKU_VOLUME_HOLD
TAP = adapters.ROKU_BUTTON_TAP
HOLD = adapters.ROKU_BUTTON_HOLD


def check(name, condition):
    global passed, failed

    if condition:
        passed += 1
        print("PASS:", name)
    else:
        failed += 1
        print("FAIL:", name)


def reject(name, operation):
    try:
        operation()
    except ValueError:
        check(name, True)
    else:
        check(name, False)


def device(type_id):
    result = {
        "type": type_id,
        "endpoint": "",
    }

    if type_id == "lg-webos":
        result["client_key"] = ""

    return result


def http(path="", method="POST"):
    return {
        "kind": "http",
        "method": method,
        "path": path,
    }


def ssap(uri):
    return {
        "kind": "ssap",
        "uri": uri,
    }


def pointer(button):
    return {
        "kind": "pointer",
        "button": button,
    }


def resolve(type_id, kind, action_id, command):
    return adapters.resolve(
        device(type_id),
        kind,
        action_id,
        command,
    )


def make_room(name):
    devices = {
        "device-1": device("generic-http"),
        "device-2": device("denon"),
        "device-3": device("roku"),
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
        "command": http(DENON_UP, "GET"),
    }

    actions["volume-down"] = {
        "target": "device-2",
        "command": http(DENON_DOWN, "GET"),
    }

    for action_id, path in (
        ("nav-up", "/keypress/Up"),
        ("nav-down", "/keypress/Down"),
        ("nav-left", "/keypress/Left"),
        ("nav-right", "/keypress/Right"),
        ("skip-back", "/keypress/Rev"),
        ("skip-forward", "/keypress/Fwd"),
    ):
        actions[action_id]["command"] = http(path)

    actions["home"]["command"] = http("/keypress/Home")

    return {
        "name": name,
        "devices": devices,
        "actions": actions,
        "custom_actions": [],
    }


def test_selection():
    # Denon specialized volume commands.

    check(
        "Denon volume up selects TCP",
        resolve("denon", "fundamental", "volume-up",
                http(DENON_UP, "GET")) == TCP
    )

    check(
        "Denon volume down selects TCP",
        resolve("denon", "fundamental", "volume-down",
                http(DENON_DOWN, "GET")) == TCP
    )

    check(
        "Denon unknown volume path uses HTTP",
        resolve("denon", "fundamental", "volume-up",
                http("/unknown", "GET")) == HTTP
    )

    check(
        "Denon wrong method uses HTTP",
        resolve("denon", "fundamental", "volume-up",
                http(DENON_UP, "POST")) == HTTP
    )

    check(
        "Denon non-volume action uses HTTP",
        resolve("denon", "fundamental", "home",
                http(DENON_UP, "GET")) == HTTP
    )

    # Roku specialized volume commands.

    check(
        "Roku volume up selects volume hold",
        resolve("roku", "fundamental", "volume-up",
                http(ROKU_UP)) == VOLUME
    )

    check(
        "Roku volume down selects volume hold",
        resolve("roku", "fundamental", "volume-down",
                http(ROKU_DOWN)) == VOLUME
    )

    check(
        "Roku wrong method uses HTTP",
        resolve("roku", "fundamental", "volume-up",
                http(ROKU_UP, "GET")) == HTTP
    )

    # All six optimized navigation/skip controls.

    for action_id, path in (
        ("nav-up", "/keypress/Up"),
        ("nav-down", "/keypress/Down"),
        ("nav-left", "/keypress/Left"),
        ("nav-right", "/keypress/Right"),
        ("skip-back", "/keypress/Rev"),
        ("skip-forward", "/keypress/Fwd"),
    ):
        check(
            "Roku {} tap".format(action_id),
            resolve("roku", "fundamental",
                    action_id, http(path)) == TAP
        )

        check(
            "Roku {} hold".format(action_id),
            resolve("roku", "hold",
                    action_id, http(path)) == HOLD
        )

    check(
        "Roku Home uses generic HTTP",
        resolve("roku", "fundamental", "home",
                http("/keypress/Home")) == HTTP
    )

    check(
        "Blank Roku command uses generic selection",
        resolve("roku", "fundamental", "nav-up",
                http()) == HTTP
    )

    # Explicit device type overrides command resemblance.

    check(
        "Generic HTTP does not select Denon TCP",
        resolve("generic-http", "fundamental",
                "volume-up", http(DENON_UP, "GET")) == HTTP
    )

    check(
        "Generic HTTP does not select Roku volume hold",
        resolve("generic-http", "fundamental",
                "volume-up", http(ROKU_UP)) == HTTP
    )

    check(
        "Generic HTTP does not select Roku tap",
        resolve("generic-http", "fundamental",
                "nav-up", http("/keypress/Up")) == HTTP
    )

    check(
        "Generic HTTP does not select Roku hold",
        resolve("generic-http", "hold",
                "nav-up", http("/keypress/Up")) == HTTP
    )

    check(
        "Denon type does not select Roku transport",
        resolve("denon", "fundamental",
                "volume-up", http(ROKU_UP)) == HTTP
    )

    check(
        "Roku type does not select Denon transport",
        resolve("roku", "fundamental",
                "volume-up", http(DENON_UP, "GET")) == HTTP
    )

    # Custom Actions must remain single-command HTTP.

    check(
        "Denon custom volume remains HTTP",
        resolve("denon", "custom", "volume-up",
                http(DENON_UP, "GET")) == HTTP
    )

    check(
        "Roku custom volume remains HTTP",
        resolve("roku", "custom", "volume-up",
                http(ROKU_UP)) == HTTP
    )

    check(
        "Roku custom navigation remains HTTP",
        resolve("roku", "custom", "nav-up",
                http("/keypress/Up")) == HTTP
    )

    # Disabled devices and incompatible protocols.

    reject(
        "Reject disabled LG SSAP selection",
        lambda: resolve(
            "lg-webos", "fundamental", "volume-up",
            ssap("ssap://audio/volumeUp")
        )
    )

    reject(
        "Reject disabled LG pointer selection",
        lambda: resolve(
            "lg-webos", "fundamental", "nav-up",
            pointer("UP")
        )
    )

    reject(
        "Reject disabled LG Custom Action",
        lambda: resolve(
            "lg-webos", "custom", None,
            pointer("HOME")
        )
    )

    reject(
        "Reject future Apple TV selection",
        lambda: resolve(
            "apple-tv", "fundamental", "home",
            http("/test")
        )
    )

    reject(
        "Reject future Fire TV selection",
        lambda: resolve(
            "fire-tv", "fundamental", "home",
            http("/test")
        )
    )

    reject(
        "Reject SSAP on Roku",
        lambda: resolve(
            "roku", "fundamental", "volume-up",
            ssap("ssap://audio/volumeUp")
        )
    )


def test_cache():
    config = {
        "version": 5,
        "rooms": {
            "room-1": make_room("Den"),
            "room-2": make_room("Sunroom"),
        },
    }

    room = config["rooms"]["room-2"]

    # Second room uses Roku volume instead of Denon.
    for action_id, path in (
        ("volume-up", ROKU_UP),
        ("volume-down", ROKU_DOWN),
    ):
        room["actions"][action_id] = {
            "target": "device-3",
            "command": http(path),
        }

    config = cfg.validate_config(config)

    count = adapters.rebuild(config)

    # Per room: two volume entries and six tap/hold pairs.
    check("Two-room cache size", count == 28)

    check(
        "Room 1 Denon volume cache",
        adapters.lookup("room-1", "volume-up") == TCP
    )

    check(
        "Room 2 Roku volume cache",
        adapters.lookup("room-2", "volume-up") == VOLUME
    )

    check(
        "Roku tap cache",
        adapters.lookup("room-2", "nav-up") == TAP
    )

    check(
        "Roku hold cache",
        adapters.lookup_hold("room-2", "nav-up") == HOLD
    )

    check(
        "Ordinary Home fallback",
        adapters.lookup("room-2", "home") == HTTP
    )

    check(
        "Unconfigured room fallback",
        adapters.lookup("room-3", "volume-up") == HTTP
    )

    check(
        "Toggle fallback",
        adapters.lookup("room-2", "power-toggle") == HTTP
    )

    # Snapshot must not expose the live cache.
    snapshot = adapters.snapshot()
    snapshot.clear()

    check(
        "Snapshot is independent",
        len(adapters.snapshot()) == 28
    )

    # Remove one room and change the other room's Roku
    # device to generic HTTP without changing commands.
    del config["rooms"]["room-1"]

    room = config["rooms"]["room-2"]
    room["devices"]["device-3"] = device("generic-http")

    config = cfg.validate_config(config)

    check(
        "Rebuild removes obsolete cache entries",
        adapters.rebuild(config) == 0
    )

    check(
        "Removed room cache cleared",
        adapters.lookup("room-1", "volume-up") == HTTP
    )

    check(
        "Changed type clears Roku tap cache",
        adapters.lookup("room-2", "nav-up") == HTTP
    )

    check(
        "Changed type clears Roku hold cache",
        adapters.lookup_hold("room-2", "nav-up") == HTTP
    )

    # Add a configuration-only LG device.
    room = config["rooms"]["room-2"]
    room["devices"]["device-1"] = device("lg-webos")

    room["actions"]["nav-up"] = {
        "target": "device-1",
        "command": pointer("UP"),
    }

    config = cfg.validate_config(config)

    check(
        "Disabled LG configuration can rebuild",
        adapters.rebuild(config) == 0
    )

    check(
        "Disabled LG receives no specialized cache entry",
        ("room-2", "nav-up") not in adapters.snapshot()
    )


def test_execution_guards():
    # These calls must fail before reaching any transport.
    # Blank endpoints provide an additional safeguard.

    lg = device("lg-webos")

    reject(
        "Execution rejects disabled LG SSAP",
        lambda: adapters.execute(
            HTTP, lg, ssap("ssap://audio/volumeUp")
        )
    )

    reject(
        "Execution rejects disabled LG pointer",
        lambda: adapters.execute(
            HTTP, lg, pointer("HOME")
        )
    )

    reject(
        "Held execution rejects disabled LG",
        lambda: adapters.execute_hold(
            HOLD, lg, pointer("UP"), "down"
        )
    )

    reject(
        "HTTP execution rejects SSAP on Roku",
        lambda: adapters.execute(
            HTTP, device("roku"),
            ssap("ssap://audio/volumeUp")
        )
    )


def run():
    gc.collect()
    heap_before = gc.mem_free()

    print()
    print("=== TYPED ADAPTER REGRESSION ===")
    print()

    # Preserve the coordinator's previous cache.
    previous_map = adapters._adapter_map

    try:
        test_selection()
        test_cache()
        test_execution_guards()

    finally:
        adapters._adapter_map = previous_map

    gc.collect()

    print()
    print("=== RESULTS ===")
    print("Passed:", passed)
    print("Failed:", failed)
    print("Free heap before:", heap_before)
    print("Free heap after:", gc.mem_free())

    if failed == 0:
        print("TYPED ADAPTER REGRESSION: PASS")
    else:
        print("TYPED ADAPTER REGRESSION: FAIL")


run()
