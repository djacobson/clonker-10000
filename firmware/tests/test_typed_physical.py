# The Clonker 10000
# tests/test_typed_physical.py
#
# Chapter 12 -- Typed physical gesture regression
#
# No GPIO initialization, network execution,
# or filesystem writes.

import gc
import time

from clonker import actions
from clonker import device_config as cfg
from clonker.controls import physical
from clonker.controls import selectors
from clonker.devices import device_adapters as adapters

passed = 0
failed = 0

selected_room = "room-1"
cancel_calls = 0


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
    return len(actions._queue)


def fake_selected_room():
    return selected_room


def fake_cancel():
    global cancel_calls
    cancel_calls += 1


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
            "type": "generic-http",
            "endpoint": subnet + ".10:80",
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
        if action_id in ("mute-toggle", "power-toggle"):
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

    paths = {
        "nav-up": "/keypress/Up",
        "nav-down": "/keypress/Down",
        "nav-left": "/keypress/Left",
        "nav-right": "/keypress/Right",
        "skip-back": "/keypress/Rev",
        "skip-forward": "/keypress/Fwd",
        "home": "/keypress/Home",
    }

    for action_id, path in paths.items():
        fundamental[action_id]["command"] = http(path)

    # Generic HTTP navigation fallback in room 2.
    if name == "Sunroom":
        fundamental["nav-left"] = {
            "target": "device-1",
            "command": http("/left", "GET"),
        }

        # Deliberately unconfigured navigation command.
        fundamental["nav-down"]["command"] = http()

    return {
        "name": name,
        "devices": devices,
        "actions": fundamental,
        "custom_actions": [],
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
    global selected_room, cancel_calls

    selected_room = "room-1"
    cancel_calls = 0

    actions._queue.clear()
    actions._toggle_next.clear()
    actions._last_result = None
    actions._last_error = None
    actions._peak_depth = 0

    physical._hold_rooms.clear()
    physical._pending_releases.clear()
    physical._action_index = 0

    physical.NAV_PRESS_FIRST = True

    cfg._current = make_config()
    adapters.rebuild(cfg._current)


def press(button, action_id):
    return physical.dispatch_hold_button(
        button, action_id, "pressed"
    )


def release(button, action_id):
    return physical.dispatch_hold_button(
        button, action_id, "released"
    )


def age_gesture(button, elapsed_ns):
    """Simulate elapsed time without blocking."""
    state = physical._hold_rooms[button]

    physical._hold_rooms[button] = (
        state[:5]
        + (time.monotonic_ns() - elapsed_ns,)
        + state[6:]
    )


def promote_hold(button):
    age_gesture(
        button,
        physical.TAP_HOLD_THRESHOLD_NS + 1_000_000
    )

    physical.poll_pending_holds()


def fill_queue():
    """Fill the real queue without generating network traffic."""
    while depth() < actions.QUEUE_CAPACITY:
        actions._queue.append({"test_filler": True})


# -------------------------------------------------
# Short taps
# -------------------------------------------------

def test_short_taps():
    reset_test()

    check("Navigation press accepted",
          press("UP", "nav-up"))

    check("Initial tap queued immediately", depth() == 1)

    check(
        "Initial tap is fundamental",
        actions._queue[0]["kind"] == "fundamental"
    )

    check("Gesture captured", "UP" in physical._hold_rooms)

    state = physical._hold_rooms["UP"]

    check("Original room captured", state[0] == "room-1")

    check(
        "Original device captured",
        state[2]["endpoint"] == "192.168.1.30:8060"
    )

    check(
        "Original command captured",
        state[3]["path"] == "/keypress/Up"
    )

    check(
        "Native Roku hold adapter captured",
        state[4] == adapters.ROKU_BUTTON_HOLD
    )

    check("Gesture initially not holding", not state[6])

    # Reset press timestamp to avoid dependence on logging time.
    age_gesture("UP", 0)
    physical.poll_pending_holds()

    check("Early poll does not start hold", depth() == 1)

    check("Short release accepted", release("UP", "nav-up"))
    check("Short release sends no extra tap", depth() == 1)
    check("Gesture removed", not physical._hold_rooms)

    check("Duplicate release ignored",
          not release("UP", "nav-up"))

    check("Duplicate release queues nothing", depth() == 1)


# -------------------------------------------------
# All six native hold buttons
# -------------------------------------------------

def test_native_holds():
    buttons = (
        ("UP", "nav-up"),
        ("DOWN", "nav-down"),
        ("LEFT", "nav-left"),
        ("RIGHT", "nav-right"),
        ("SKIP_BACK", "skip-back"),
        ("SKIP_FORWARD", "skip-forward"),
    )

    for button, action_id in buttons:
        reset_test()

        check(button + " press accepted",
              press(button, action_id))

        check(button + " initial tap queued",
              depth() == 1)

        promote_hold(button)

        check(button + " hold queued", depth() == 2)

        task = actions._queue[-1]

        check(
            button + " native keydown",
            task["kind"] == "hold"
            and task["event"] == "pressed"
        )

        check(
            button + " gesture marked holding",
            physical._hold_rooms[button][6]
        )

        physical.poll_pending_holds()

        check(button + " no duplicate keydown",
              depth() == 2)

        check(button + " release accepted",
              release(button, action_id))

        check(
            button + " native keyup",
            depth() == 3
            and actions._queue[-1]["kind"] == "hold"
            and actions._queue[-1]["event"] == "released"
        )

        check(button + " gesture removed",
              not physical._hold_rooms)


# -------------------------------------------------
# Room change during a gesture
# -------------------------------------------------

def test_room_change():
    global selected_room

    reset_test()

    press("UP", "nav-up")

    original = physical._hold_rooms["UP"]
    device = original[2]
    command = original[3]

    selected_room = "room-2"

    promote_hold("UP")

    task = actions._queue[-1]

    check("Hold retains original room",
          task["room"] == "room-1")

    check("Hold retains original device reference",
          task["device"] is device)

    check("Hold retains original command reference",
          task["command"] is command)

    release("UP", "nav-up")

    task = actions._queue[-1]

    check("Release retains original room",
          task["room"] == "room-1")

    check("Release retains original device reference",
          task["device"] is device)

    check("Release retains original command reference",
          task["command"] is command)

    check(
        "Release retains original endpoint",
        task["device"]["endpoint"] == "192.168.1.30:8060"
    )

    press("UP", "nav-up")

    check(
        "Next gesture uses newly selected room",
        physical._hold_rooms["UP"][0] == "room-2"
    )


# -------------------------------------------------
# Generic HTTP fallback and blank commands
# -------------------------------------------------

def test_fallback():
    global selected_room

    reset_test()
    selected_room = "room-2"

    check("Generic navigation press accepted",
          press("LEFT", "nav-left"))

    check("Generic navigation queues one action",
          depth() == 1)

    check(
        "Generic navigation uses fundamental task",
        actions._queue[0]["kind"] == "fundamental"
    )

    check("Generic navigation captures no hold",
          not physical._hold_rooms)

    physical.poll_pending_holds()

    check("Generic navigation creates no keydown",
          depth() == 1)

    release("LEFT", "nav-left")

    check("Generic release creates no extra command",
          depth() == 1)

    check("Blank navigation skipped",
          not press("DOWN", "nav-down"))

    check("Blank navigation queues nothing",
          depth() == 1)

    room = cfg._current["rooms"]["room-2"]
    room["devices"]["device-3"]["endpoint"] = ""

    check("Blank endpoint skipped",
          not press("UP", "nav-up"))

    check("Blank endpoint queues nothing",
          depth() == 1)

    selected_room = "room-3"

    check("Unassigned room skipped",
          not press("UP", "nav-up"))

    check("Unassigned room queues nothing",
          depth() == 1)


# -------------------------------------------------
# Release-first alternative behavior
# -------------------------------------------------

def test_release_first():
    reset_test()
    physical.NAV_PRESS_FIRST = False

    check("Release-first press accepted",
          press("UP", "nav-up"))

    check("Release-first press queues nothing",
          depth() == 0)

    check("Release-first tap accepted",
          release("UP", "nav-up"))

    check("Release-first tap queues one command",
          depth() == 1)

    check(
        "Release-first tap is fundamental",
        actions._queue[0]["kind"] == "fundamental"
    )

    reset_test()
    physical.NAV_PRESS_FIRST = False

    press("UP", "nav-up")
    promote_hold("UP")

    check("Release-first hold queues only keydown",
          depth() == 1)

    check(
        "Release-first hold is native",
        actions._queue[0]["kind"] == "hold"
    )

    release("UP", "nav-up")

    check("Release-first hold queues only keyup",
          depth() == 2)

    check(
        "Release-first release is native",
        actions._queue[-1]["event"] == "released"
    )


# -------------------------------------------------
# Queue admission failures and pending releases
# -------------------------------------------------

def test_queue_pressure():
    reset_test()

    fill_queue()

    check("Full queue rejects initial press",
          not press("UP", "nav-up"))

    check("Rejected press creates no gesture",
          not physical._hold_rooms)

    check("Full queue capacity preserved",
          depth() == actions.QUEUE_CAPACITY)

    reset_test()

    press("UP", "nav-up")
    fill_queue()
    promote_hold("UP")

    check(
        "Full queue defers hold promotion",
        not physical._hold_rooms["UP"][6]
    )

    actions._queue.pop()

    physical.poll_pending_holds()

    check(
        "Hold promotion resumes when space available",
        physical._hold_rooms["UP"][6]
    )

    original = physical._hold_rooms["UP"]

    check("Full queue defers keyup",
          not release("UP", "nav-up"))

    check("Deferred keyup retained",
          "UP" in physical._pending_releases)

    check("Released gesture removed",
          "UP" not in physical._hold_rooms)

    pending = physical._pending_releases["UP"]

    check("Pending release retains device",
          pending[2] is original[2])

    check("Pending release retains command",
          pending[3] is original[3])

    check("New press cannot overtake pending keyup",
          not press("UP", "nav-up"))

    check("Pending keyup remains retained",
          "UP" in physical._pending_releases)

    actions._queue.pop()
    physical.retry_pending_releases()

    check("Pending release admitted",
          "UP" not in physical._pending_releases)

    task = actions._queue[-1]

    check(
        "Retried release is native keyup",
        task["kind"] == "hold"
        and task["event"] == "released"
    )

    check("Retried release retains original device",
          task["device"] is original[2])

    check("Retried release retains original command",
          task["command"] is original[3])

    actions._queue.pop()

    check("New press accepted after keyup admission",
          press("UP", "nav-up"))


# -------------------------------------------------
# Configuration-change cleanup
# -------------------------------------------------

def test_configuration_change():
    reset_test()

    press("UP", "nav-up")
    promote_hold("UP")

    press("DOWN", "nav-down")
    promote_hold("DOWN")

    fill_queue()

    release("DOWN", "nav-down")

    check("Active hold exists before reset",
          "UP" in physical._hold_rooms)

    check("Pending release exists before reset",
          "DOWN" in physical._pending_releases)

    physical._action_index = 7
    actions._toggle_next[("room-1", "mute-toggle")] = "off"

    physical.configuration_changed()

    check("Configuration reset clears gestures",
          not physical._hold_rooms)

    check("Configuration reset clears pending releases",
          not physical._pending_releases)

    check("Configuration reset clears custom index",
          physical._action_index == 0)

    check("Physical reset does not clear queue",
          depth() == actions.QUEUE_CAPACITY)

    check("Physical reset does not cancel adapters",
          cancel_calls == 0)

    # Mirror the web service's changed-save cleanup.
    actions.clear(
        "Configuration changed",
        reset_toggles=True
    )

    check("Dispatcher reset clears queue", depth() == 0)

    check("Dispatcher reset clears toggle history",
          not actions._toggle_next)

    check("Dispatcher invokes adapter cleanup",
          cancel_calls == 1)

    physical.poll_pending_holds()
    physical.retry_pending_releases()

    check("Old gestures cannot restart holds",
          depth() == 0)

    release("UP", "nav-up")
    release("DOWN", "nav-down")

    check("Old releases cannot resurrect sessions",
          depth() == 0)

    check("New gesture accepted after reset",
          press("UP", "nav-up"))

    check("New gesture queues one tap", depth() == 1)


# -------------------------------------------------
# Runner and state restoration
# -------------------------------------------------

def run():
    gc.collect()
    heap_before = gc.mem_free()

    print()
    print("=== TYPED PHYSICAL REGRESSION ===")
    print()

    previous_config = cfg._current
    previous_cache = adapters._adapter_map

    previous_selector = selectors.selected_room
    previous_cancel = adapters.cancel_active

    queue_fields = (
        "_queue",
        "_toggle_next",
        "_last_result",
        "_last_error",
        "_peak_depth",
    )

    physical_fields = (
        "_hold_rooms",
        "_pending_releases",
        "_action_index",
        "NAV_PRESS_FIRST",
        "_dispatch_attempts",
        "_dispatch_accepted",
        "_dispatch_failed",
        "_dispatch_skipped",
        "_last_dispatch",
    )

    previous_queue = {
        name: getattr(actions, name)
        for name in queue_fields
    }

    previous_physical = {
        name: getattr(physical, name)
        for name in physical_fields
    }

    completed = False

    try:
        selectors.selected_room = fake_selected_room
        adapters.cancel_active = fake_cancel

        actions._queue = []
        actions._toggle_next = {}

        physical._hold_rooms = {}
        physical._pending_releases = {}

        test_short_taps()
        test_native_holds()
        test_room_change()
        test_fallback()
        test_release_first()
        test_queue_pressure()
        test_configuration_change()

        completed = True

    finally:
        selectors.selected_room = previous_selector
        adapters.cancel_active = previous_cancel

        cfg._current = previous_config
        adapters._adapter_map = previous_cache

        for name, value in previous_queue.items():
            setattr(actions, name, value)

        for name, value in previous_physical.items():
            setattr(physical, name, value)

        previous_queue.clear()
        previous_physical.clear()

    gc.collect()

    print()
    print("=== RESULTS ===")
    print("Passed:", passed)
    print("Failed:", failed)
    print("Free heap before:", heap_before)
    print("Free heap after:", gc.mem_free())

    if completed and failed == 0:
        print("TYPED PHYSICAL REGRESSION: PASS")
    else:
        print("TYPED PHYSICAL REGRESSION: FAIL")


run()
