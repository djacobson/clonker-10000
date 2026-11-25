# The Clonker 10000
# tests/test_typed_queue.py
#
# Chapter 13 -- Typed Dumb Queue regression
#
# No filesystem writes or network operations.

import gc
import time

from clonker import actions
from clonker import device_config as cfg
from clonker.devices import device_adapters as adapters
from clonker.devices import denon, roku
from clonker.net import http_transport
from clonker.display import oled

passed = 0
failed = 0

sent = []
displayed = []

cancel_calls = 0
transport_ready = True
transport_accept = True
transport_fail = False

DENON_UP = "/goform/formiPhoneAppDirect.xml?MVUP"


def check(name, condition):
    global passed, failed

    if condition:
        passed += 1
        print("PASS:", name)
    else:
        failed += 1
        print("FAIL:", name)
        raise AssertionError(name)


def depth():
    return actions.status()["depth"]


def record(transport, endpoint, method, command):
    if transport_fail:
        raise OSError("Simulated transport failure")

    sent.append((
        transport,
        endpoint,
        method,
        command,
    ))


# -------------------------------------------------
# Simulated transport functions
# -------------------------------------------------

def fake_http(endpoint, method, path):
    record("http", endpoint, method, path)
    return {"status": 200}


def fake_denon_ready():
    return transport_ready


def fake_denon_send(endpoint, command):
    if not transport_accept:
        return False

    record("denon", endpoint, None, command)
    return True


def fake_roku_volume(endpoint, direction):
    record("roku-volume", endpoint, None, direction)
    return True


def fake_roku_tap(endpoint, method, path, action_id):
    record("roku-tap", endpoint, method, path)
    return {"status": 200}


def fake_roku_hold(endpoint, method, path, event):
    record("roku-hold", endpoint, event, path)
    return "Simulated Roku " + event


def fake_lg_ready(device, command):
    return transport_ready


def fake_lg_execute(device, command):
    if not transport_accept:
        return {
            "accepted": False,
            "detail": "Simulated LG busy",
        }

    record(
        "lg",
        device["endpoint"],
        command["kind"],
        command,
    )

    return {
        "accepted": True,
        "detail": "Simulated LG transmission",
    }


def fake_cancel():
    global cancel_calls
    cancel_calls += 1
    return True


def fake_oled(*args, **kwargs):
    displayed.append(args)


# -------------------------------------------------
# Configuration fixtures
# -------------------------------------------------

def http(path="", method="POST"):
    return {
        "kind": "http",
        "method": method,
        "path": path,
    }


def make_room(name, subnet):
    devices = {
        "device-1": {
            "type": "lg-webos",
            "endpoint": subnet + ".10:3000",
            "client_key": "TEST_KEY",
        },
        "device-2": {
            "type": "denon",
            "endpoint": subnet + ".20:8080",
        },
        "device-3": {
            "type": "roku",
            "endpoint": subnet + ".30:8060",
        },
    }

    fundamental = {}

    for action_id in cfg.ACTION_IDS:
        if action_id in ("power-toggle", "mute-toggle"):
            fundamental[action_id] = {
                "target": "device-2",
                "on_command": http("", "GET"),
                "off_command": http("", "GET"),
            }
        else:
            fundamental[action_id] = {
                "target": "device-3",
                "command": http(),
            }

    fundamental["volume-up"] = {
        "target": "device-2",
        "command": http(DENON_UP, "GET"),
    }

    fundamental["volume-down"] = {
        "target": "device-3",
        "command": http("/keypress/VolumeDown"),
    }

    fundamental["home"]["command"] = http("/keypress/Home")
    fundamental["nav-up"]["command"] = http("/keypress/Up")

    fundamental["mute-toggle"] = {
        "target": "device-2",
        "on_command": http("/mute/on", "GET"),
        "off_command": http("/mute/off", "POST"),
    }

    fundamental["power-toggle"] = {
        "target": "device-2",
        "on_command": http("/power/on", "GET"),
        "off_command": http("/power/off", "GET"),
    }

    fundamental["nav-left"] = {
        "target": "device-1",
        "command": {
            "kind": "pointer",
            "button": "LEFT",
        },
    }

    custom = [
        {
            "id": "custom-action-1",
            "name": "Mixed HTTP",
            "steps": [
                {
                    "target": "device-2",
                    "command": http(DENON_UP, "GET"),
                    "wait_after_ms": 1000,
                },
                {
                    "target": "device-3",
                    "command": http("/keypress/Up"),
                    "wait_after_ms": 0,
                },
            ],
        },
        {
            "id": "custom-action-2",
            "name": "LG Volume",
            "steps": [
                {
                    "target": "device-1",
                    "command": {
                        "kind": "ssap",
                        "uri": "ssap://audio/volumeUp",
                    },
                    "wait_after_ms": 0,
                },
            ],
        },
    ]

    return {
        "name": name,
        "devices": devices,
        "actions": fundamental,
        "custom_actions": custom,
    }


def make_config():
    return cfg.validate_config({
        "version": 5,
        "rooms": {
            "room-1": make_room("Den", "192.168.1"),
            "room-2": make_room("Sunroom", "192.168.2"),
        },
    })


def reset_test():
    global cancel_calls
    global transport_ready, transport_accept, transport_fail

    actions._queue.clear()
    actions._toggle_next.clear()
    actions._last_result = None
    actions._last_error = None
    actions._peak_depth = 0

    sent.clear()
    displayed.clear()

    cancel_calls = 0
    transport_ready = True
    transport_accept = True
    transport_fail = False

    cfg._current = make_config()
    adapters.rebuild(cfg._current)


# -------------------------------------------------
# Fundamental commands
# -------------------------------------------------

def test_fundamental():
    reset_test()

    result = actions.dispatch("room-1", "home")

    check("Fundamental admitted", result["ok"])
    check("Fundamental configured", result["configured"])
    check("One task queued", depth() == 1)
    check("Admission performs no transport", len(sent) == 0)

    check("Fundamental poll succeeds", actions.poll())
    check("Fundamental removed", depth() == 0)

    check(
        "Generic HTTP execution",
        sent[-1] == (
            "http", "192.168.1.30:8060",
            "POST", "/keypress/Home"
        )
    )

    actions.dispatch("room-1", "volume-up")
    actions.poll()

    check("Denon TCP execution", sent[-1][0] == "denon")

    actions.dispatch("room-1", "volume-down")
    actions.poll()

    check(
        "Roku volume execution",
        sent[-1][0] == "roku-volume"
    )

    actions.dispatch("room-1", "nav-up")
    actions.poll()

    check("Roku tap execution", sent[-1][0] == "roku-tap")

    before = len(sent)

    result = actions.dispatch("room-1", "nav-down")

    check("Blank command reported unconfigured",
          not result["configured"])

    check("Blank command completes as no-op", actions.poll())
    check("Blank command sends nothing", len(sent) == before)
    check("Blank command removed", depth() == 0)

    room = cfg._current["rooms"]["room-1"]
    room["devices"]["device-3"]["endpoint"] = ""

    result = actions.dispatch("room-1", "home")

    check("Blank endpoint reported unconfigured",
          not result["configured"])

    check("Blank endpoint completes as no-op", actions.poll())
    check("Blank endpoint sends nothing", len(sent) == before)
    check("Empty queue poll returns False", not actions.poll())


# -------------------------------------------------
# Toggle histories
# -------------------------------------------------

def test_toggles():
    reset_test()

    actions.dispatch("room-1", "mute-toggle")
    actions.dispatch("room-1", "mute-toggle")

    actions.poll()

    check("First mute uses ON", sent[-1][3] == "/mute/on")
    check("Mute ON uses GET", sent[-1][2] == "GET")
    check("Mute ON OLED", displayed[-1] == ("MUTE ON",))
    check("Only one command per poll", depth() == 1)

    actions.poll()

    check("Second mute uses OFF", sent[-1][3] == "/mute/off")
    check("Mute OFF uses POST", sent[-1][2] == "POST")
    check("Mute OFF OLED", displayed[-1] == ("MUTE OFF",))

    actions.dispatch("room-1", "mute-toggle")
    actions.poll()

    check("Third mute returns to ON", sent[-1][3] == "/mute/on")

    actions.dispatch("room-2", "mute-toggle")
    actions.poll()

    check("Room 2 independent mute", sent[-1][3] == "/mute/on")

    actions.dispatch("room-1", "power-toggle")
    actions.poll()

    check("Power history independent", sent[-1][3] == "/power/on")

    actions.clear("Test toggle reset", reset_toggles=True)

    check("Toggle histories cleared", not actions._toggle_next)

    actions.dispatch("room-1", "mute-toggle")
    actions.poll()

    check("Reset mute returns to ON", sent[-1][3] == "/mute/on")


# -------------------------------------------------
# Scheduling and adapter readiness
# -------------------------------------------------

def test_scheduling():
    global transport_ready, transport_accept

    reset_test()

    actions.dispatch("room-1", "home", delay_seconds=60)

    check("Future task remains queued", not actions.poll())
    check("Future task sends nothing", len(sent) == 0)

    actions.dispatch("room-2", "home")

    check("Immediate task bypasses future task", actions.poll())

    check(
        "Correct immediate destination",
        sent[-1][1] == "192.168.2.30:8060"
    )

    check("Future task retained", depth() == 1)

    # Advance eligibility without sleeping.
    actions._queue[0]["due"] = 0

    check("Previously delayed task executes", actions.poll())

    check(
        "Correct delayed destination",
        sent[-1][1] == "192.168.1.30:8060"
    )

    sent.clear()

    transport_ready = False

    actions.dispatch("room-1", "volume-up")
    actions.dispatch("room-1", "home")

    check("Unready adapter defers poll", not actions.poll())
    check("Unready adapter preserves ordering", depth() == 2)
    check("Unready adapter sends nothing", len(sent) == 0)

    transport_ready = True
    transport_accept = False

    check("Unaccepted command remains queued", not actions.poll())
    check("Unaccepted command preserves depth", depth() == 2)
    check("Unaccepted command sends nothing", len(sent) == 0)

    transport_accept = True

    check("Ready adapter resumes execution", actions.poll())
    check("Denon executes first", sent[-1][0] == "denon")
    check("Later task still queued", depth() == 1)

    actions.poll()

    check("HTTP executes second", sent[-1][0] == "http")
    check("Queue drained", depth() == 0)


# -------------------------------------------------
# Custom Action sequencing
# -------------------------------------------------

def test_custom():
    reset_test()

    result = actions.dispatch("room-1", "custom-action-1")

    check("Custom Action admitted", result["ok"])
    check("Custom uses one queue entry", depth() == 1)

    check("Custom first step executes", actions.poll())

    check(
        "Custom Denon command remains single HTTP",
        sent[-1][0] == "http" and sent[-1][3] == DENON_UP
    )

    check("Custom retains one entry", depth() == 1)
    check("Custom advances step", actions._queue[0]["step"] == 1)

    remaining = (
        actions._queue[0]["due"] - time.monotonic_ns()
    )

    check(
        "Custom wait begins after execution",
        0 < remaining <= 1_000_000_000
    )

    # Extend the wait so logging overhead cannot make
    # the following scheduling assertions intermittent.
    actions._queue[0]["due"] = (
        time.monotonic_ns() + 60_000_000_000
    )

    check("Custom wait prevents early execution", not actions.poll())

    actions.dispatch("room-2", "home")
    actions.poll()

    check(
        "Immediate command runs during custom wait",
        sent[-1][1] == "192.168.2.30:8060"
    )

    check("Waiting custom retained", depth() == 1)

    actions._queue[0]["due"] = 0

    check("Custom final step executes", actions.poll())

    check(
        "Custom Roku command remains single HTTP",
        sent[-1][0] == "http"
        and sent[-1][3] == "/keypress/Up"
    )

    check("Custom completes and leaves queue", depth() == 0)
    check("Exactly three transmissions", len(sent) == 3)


# -------------------------------------------------
# Captured held-button destinations
# -------------------------------------------------

def test_holds():
    reset_test()

    room, action = cfg.action_details("room-1", "nav-up")

    device = cfg.resolve_device(room, action["target"])
    command = action["command"]
    adapter = adapters.lookup_hold("room-1", "nav-up")

    actions.dispatch_hold(
        "room-1", "nav-up", "pressed",
        device, command, adapter
    )

    check("Hold press admitted", depth() == 1)
    check("Hold retains device reference",
          actions._queue[0]["device"] is device)
    check("Hold retains command reference",
          actions._queue[0]["command"] is command)

    actions.poll()

    check(
        "Hold press uses captured destination",
        sent[-1] == (
            "roku-hold", "192.168.1.30:8060",
            "pressed", "/keypress/Up"
        )
    )

    # Interleave an ordinary command to the other room.
    actions.dispatch("room-2", "home")
    actions.poll()

    check(
        "Other room executes independently",
        sent[-1][1] == "192.168.2.30:8060"
    )

    actions.dispatch_hold(
        "room-1", "nav-up", "released",
        device, command, adapter
    )

    actions.poll()

    check(
        "Hold release uses original destination",
        sent[-1] == (
            "roku-hold", "192.168.1.30:8060",
            "released", "/keypress/Up"
        )
    )

    check("Hold queue drained", depth() == 0)


# -------------------------------------------------
# Failure and cancellation policy
# -------------------------------------------------

def test_failures():
    global transport_fail

    reset_test()

    transport_fail = True

    actions.dispatch("room-1", "mute-toggle")
    actions.dispatch("room-2", "home")

    check("Failed execution handled", actions.poll())
    check("Failure discards remaining queue", depth() == 0)
    check("Failure invokes cancellation", cancel_calls == 1)
    check("Failure records error",
          actions.status()["last_error"] is not None)
    check("Failed toggle does not advance",
          not actions._toggle_next)
    check("Failed toggle has no OLED confirmation",
          len(displayed) == 0)

    transport_fail = False

    check("Failed commands not replayed", not actions.poll())
    check("No successful transmissions", len(sent) == 0)

    actions.dispatch("room-1", "mute-toggle")
    actions.poll()

    check("Retry by user starts with ON", sent[-1][3] == "/mute/on")

    reset_test()
    transport_fail = True

    actions.dispatch("room-1", "nav-left")
    actions.dispatch("room-2", "home")

    check("LG fundamental failure handled", actions.poll())
    check("Failed LG sends nothing", len(sent) == 0)
    check("Failed LG cancels queue", depth() == 0)
    check("Failed LG invokes cleanup", cancel_calls == 1)

    reset_test()
    transport_fail = True

    actions.dispatch("room-1", "custom-action-2")
    actions.dispatch("room-2", "home")

    check("LG custom failure handled", actions.poll())
    check("Failed LG custom sends nothing", len(sent) == 0)
    check("Failed LG custom cancels queue", depth() == 0)

    reset_test()

    room = cfg._current["rooms"]["room-1"]
    room["devices"]["device-2"]["endpoint"] = ""

    result = actions.dispatch("room-1", "custom-action-1")

    check("Missing custom endpoint reported",
          not result["configured"])

    actions.dispatch("room-2", "home")

    check("Missing custom endpoint handled", actions.poll())
    check("Missing custom endpoint cancels queue", depth() == 0)
    check("Missing custom endpoint sends nothing", len(sent) == 0)

    reset_test()

    actions.dispatch("room-1", "home")
    actions.dispatch("room-2", "home")

    check("Manual clear discards two tasks",
          actions.clear("Test clear") == 2)

    check("Manual clear invokes cleanup", cancel_calls == 1)
    check("Manual clear empties queue", depth() == 0)


def test_lg():
    global transport_ready

    reset_test()

    # Fundamental pointer command.
    actions.dispatch("room-1", "nav-left")

    check("LG pointer admitted", depth() == 1)
    check("LG admission sends nothing", len(sent) == 0)
    check("LG pointer executes", actions.poll())

    check(
        "LG pointer transmission",
        sent[-1] == (
            "lg", "192.168.1.10:3000",
            "pointer", {"kind": "pointer", "button": "LEFT"}
        )
    )

    check("LG transmitted task removed", depth() == 0)

    # SSAP Custom Action.
    actions.dispatch("room-1", "custom-action-2")

    check("LG Custom Action executes", actions.poll())

    check(
        "LG Custom Action uses SSAP",
        sent[-1][0] == "lg"
        and sent[-1][2] == "ssap"
        and sent[-1][3]["uri"] == "ssap://audio/volumeUp"
    )

    check("LG Custom Action completes", depth() == 0)

    # Readiness preserves queue ordering.
    reset_test()
    transport_ready = False

    actions.dispatch("room-1", "nav-left")
    actions.dispatch("room-2", "home")

    check("Busy LG defers execution", not actions.poll())
    check("Busy LG preserves queue", depth() == 2)
    check("Busy LG sends nothing", len(sent) == 0)

    transport_ready = True

    check("Ready LG resumes execution", actions.poll())
    check("LG executes before HTTP", sent[-1][0] == "lg")
    check("Later HTTP remains queued", depth() == 1)

    # Simulate a late LG response failure.
    actions.fail_async(
        adapters.LG_WEBOS,
        RuntimeError("Simulated LG response failure")
    )

    check("LG async failure clears queue", depth() == 0)
    check("LG async failure invokes cleanup", cancel_calls == 1)
    check(
        "LG async failure records error",
        actions.status()["last_error"] is not None
    )
    check("LG async failure does not replay", not actions.poll())
    check("Only original LG transmission", len(sent) == 1)

    # New user input remains operational.
    actions.dispatch("room-2", "home")

    check("New command after LG failure executes", actions.poll())
    check("HTTP recovers after LG failure", sent[-1][0] == "http")

    # LG toggle direction and independent SSAP payloads.
    reset_test()

    room = cfg._current["rooms"]["room-1"]

    room["actions"]["mute-toggle"] = {
        "target": "device-1",
        "on_command": {
            "kind": "ssap",
            "uri": "ssap://audio/setMute",
            "payload": {"mute": True},
        },
        "off_command": {
            "kind": "ssap",
            "uri": "ssap://audio/setMute",
            "payload": {"mute": False},
        },
    }

    actions.dispatch("room-1", "mute-toggle")
    actions.dispatch("room-1", "mute-toggle")

    check("LG mute ON executes", actions.poll())
    check("LG mute ON transport", sent[-1][0] == "lg")
    check(
        "LG mute ON payload",
        sent[-1][3]["payload"] == {"mute": True}
    )
    check("LG mute ON OLED", displayed[-1] == ("MUTE ON",))

    check("LG mute OFF executes", actions.poll())
    check(
        "LG mute OFF payload",
        sent[-1][3]["payload"] == {"mute": False}
    )
    check("LG mute OFF OLED", displayed[-1] == ("MUTE OFF",))
    check("LG toggle queue drained", depth() == 0)


# -------------------------------------------------
# Test runner and state restoration
# -------------------------------------------------

def run():
    gc.collect()
    heap_before = gc.mem_free()

    print()
    print("=== TYPED DUMB QUEUE REGRESSION ===")
    print()

    patches = (
        (http_transport, "send", fake_http),
        (denon, "ready", fake_denon_ready),
        (denon, "send_volume", fake_denon_send),
        (roku, "volume", fake_roku_volume),
        (roku, "tap", fake_roku_tap),
        (roku, "execute_hold", fake_roku_hold),
        (adapters.lg_webos, "ready", fake_lg_ready),
        (adapters.lg_webos, "execute", fake_lg_execute),
        (adapters, "cancel_active", fake_cancel),
        (oled, "show_text", fake_oled),
    )

    originals = []

    previous_config = cfg._current
    previous_cache = adapters._adapter_map

    previous_queue = actions._queue
    previous_toggles = actions._toggle_next

    previous_result = actions._last_result
    previous_error = actions._last_error
    previous_peak = actions._peak_depth

    completed = False

    try:
        for module, name, replacement in patches:
            originals.append((
                module, name, getattr(module, name)
            ))
            setattr(module, name, replacement)

        actions._queue = []
        actions._toggle_next = {}

        test_fundamental()
        test_toggles()
        test_scheduling()
        test_custom()
        test_holds()
        test_failures()
        test_lg()

        completed = True

    finally:
        for module, name, original in reversed(originals):
            setattr(module, name, original)

        cfg._current = previous_config
        adapters._adapter_map = previous_cache

        actions._queue = previous_queue
        actions._toggle_next = previous_toggles

        actions._last_result = previous_result
        actions._last_error = previous_error
        actions._peak_depth = previous_peak

        sent.clear()
        displayed.clear()
        originals.clear()

    gc.collect()

    print()
    print("=== RESULTS ===")
    print("Passed:", passed)
    print("Failed:", failed)
    print("Free heap before:", heap_before)
    print("Free heap after:", gc.mem_free())

    if completed and failed == 0:
        print("TYPED DUMB QUEUE REGRESSION: PASS")
    else:
        print("TYPED DUMB QUEUE REGRESSION: FAIL")


run()
