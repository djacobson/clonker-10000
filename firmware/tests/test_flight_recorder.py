# The Clonker 10000
# firmware/tests/test_flight_recorder.py
#
# Kitchen Sink regression tests for the flight recorder.
# Run from the CircuitPython REPL.
#
# Clonker Designed by David Jacobson

import gc

from clonker.system import flight_recorder as fr
from clonker.controls import physical


def check(name, condition):
    if not condition:
        print("FAIL:", name)
        raise AssertionError(name)
    print("PASS:", name)


def test_ring():
    print("\n--- RAM RING ---")

    fr.clear()
    gc.collect()
    baseline = gc.mem_free()

    check("Initially empty", fr.entries() == [])
    check("Initial count", fr.stats()["total"] == 0)

    for index in range(5):
        fr.record("EVENT {:03d}".format(index))

    check("Five retained", fr.stats()["retained"] == 5)
    check("First entry", fr.entries()[0] == "EVENT 000")
    check("Last entry", fr.entries()[-1] == "EVENT 004")

    fr.clear()
    total = fr.CAPACITY + 20

    for index in range(total):
        fr.record("EVENT {:03d}".format(index))

    stats = fr.stats()
    history = fr.entries()

    check("Capacity enforced", stats["retained"] == fr.CAPACITY)
    check("Total recorded", stats["total"] == total)
    check("Overwrite count", stats["overwritten"] == 20)
    check("Oldest retained", history[0] == "EVENT 020")
    check(
        "Newest retained",
        history[-1] == "EVENT {:03d}".format(total - 1)
    )
    check(
        "Chronological order",
        all(
            history[i] == "EVENT {:03d}".format(i + 20)
            for i in range(fr.CAPACITY)
        )
    )

    history = None
    gc.collect()
    print("Approx. retained heap:", baseline - gc.mem_free(), "bytes")

    fr.clear()
    check("Clear empties ring", fr.entries() == [])
    check("Clear resets total", fr.stats()["total"] == 0)
    check("Clear resets overwrites", fr.stats()["overwritten"] == 0)


def test_providers():
    print("\n--- DIAGNOSTIC PROVIDERS ---")

    fr.register_provider("test_ok", lambda: {"value": 42})
    fr.register_provider("test_error", lambda: 1 / 0)

    results = fr.collect_diagnostics()

    check("Provider returns data",
          results["test_ok"]["value"] == 42)
    check("Provider failure isolated",
          "error" in results["test_error"])

    # Remove only our test registrations.
    # Production providers, if present, remain untouched.
    fr._providers.pop("test_ok", None)
    fr._providers.pop("test_error", None)


class FakeButton:
    def __init__(self, name, events):
        self.name = name
        self.events = events

    def poll(self):
        if self.events:
            return self.events.pop(0)
        return None


def test_physical():
    print("\n--- PHYSICAL EVENT COUNTERS ---")

    # Save the existing runtime state.
    original = {
        "initialized": physical._initialized,
        "buttons": physical._buttons,
        "volume": physical._volume_encoder,
        "action": physical._action_encoder,
        "events": physical._button_events,
        "presses": physical._button_presses,
        "last": physical._last_button,
        "selector_poll": physical.selectors.poll,
        "config_source": physical.switches.config_source,
        "config_enabled": physical.switches.config_enabled,
        "note_activity": physical.sleep_manager.note_activity,
        "is_sleeping": physical.sleep_manager.is_sleeping,
        "dispatch": physical.dispatch_selected,
        "show_text": physical.oled.show_text,
    }

    try:
        # Synthetic events: no GPIO or network commands.
        physical._initialized = True
        physical._buttons = [
            FakeButton("HOME", ["pressed", "released"]),
            FakeButton("BACK", ["pressed", "released"]),
        ]
        physical._volume_encoder = None
        physical._action_encoder = None

        physical._button_events = 0
        physical._button_presses = 0
        physical._last_button = None

        physical.selectors.poll = lambda: None
        physical.switches.config_source = lambda: "PHYSICAL"
        physical.switches.config_enabled = lambda: False
        physical.sleep_manager.note_activity = (
            lambda *args, **kwargs: False
        )
        physical.sleep_manager.is_sleeping = lambda: False
        physical.dispatch_selected = lambda action_id: True
        physical.oled.show_text = lambda *args: None

        check("Initially zero events",
              physical.snapshot()["button_events"] == 0)

        physical.poll()

        first = physical.snapshot()
        check("Two presses detected",
              first["button_presses"] == 2)
        check("Two events detected",
              first["button_events"] == 2)
        check("Last button BACK",
              first["last_button"] == "BACK")

        physical.poll()

        second = physical.snapshot()
        check("Four total events",
              second["button_events"] == 4)
        check("Presses remain two",
              second["button_presses"] == 2)

        physical.poll()
        check("No phantom events",
              physical.snapshot()["button_events"] == 4)

        print("Physical snapshot:", physical.snapshot())

    finally:
        physical._initialized = original["initialized"]
        physical._buttons = original["buttons"]
        physical._volume_encoder = original["volume"]
        physical._action_encoder = original["action"]
        physical._button_events = original["events"]
        physical._button_presses = original["presses"]
        physical._last_button = original["last"]

        physical.selectors.poll = original["selector_poll"]
        physical.switches.config_source = original["config_source"]
        physical.switches.config_enabled = original["config_enabled"]
        physical.sleep_manager.note_activity = original["note_activity"]
        physical.sleep_manager.is_sleeping = original["is_sleeping"]
        physical.dispatch_selected = original["dispatch"]
        physical.oled.show_text = original["show_text"]


def test_dispatch():
    print("\n--- PHYSICAL DISPATCH COUNTERS ---")

    # Save functions and diagnostic state before testing.
    original = {
        "selected_room": physical.selectors.selected_room,
        "has_room": physical.device_config.has_room,
        "dispatch": physical.actions.dispatch,
        "dispatch_hold": physical.actions.dispatch_hold,
        "action_details": physical.device_config.action_details,
        "resolve_endpoint": physical.device_config.resolve_endpoint,
        "lookup_hold": physical.device_adapters.lookup_hold,
        "attempts": physical._dispatch_attempts,
        "accepted": physical._dispatch_accepted,
        "failed": physical._dispatch_failed,
        "skipped": physical._dispatch_skipped,
        "last": physical._last_dispatch,
        "hold_rooms": physical._hold_rooms.copy(),
    }

    calls = []

    def accept(*args, **kwargs):
        calls.append(("accepted", args))
        return {"ok": True}

    def reject(*args, **kwargs):
        raise RuntimeError("Simulated dispatch failure")

    try:
        physical._dispatch_attempts = 0
        physical._dispatch_accepted = 0
        physical._dispatch_failed = 0
        physical._dispatch_skipped = 0
        physical._last_dispatch = None
        physical._hold_rooms.clear()

        physical.selectors.selected_room = lambda: "room-2"
        physical.device_config.has_room = lambda room: True
        physical.actions.dispatch = accept

        # Ordinary dispatch: accepted.
        check(
            "Ordinary dispatch accepted",
            physical.dispatch_selected("home") is True
        )

        # Ordinary dispatch: failed.
        physical.actions.dispatch = reject
        check(
            "Ordinary dispatch failed",
            physical.dispatch_selected("back") is False
        )

        # Ordinary dispatch: skipped.
        physical.device_config.has_room = lambda room: False
        check(
            "Ordinary dispatch skipped",
            physical.dispatch_selected("select") is False
        )

        # Prepare a fake configured hold action.
        physical.device_config.has_room = lambda room: True
        physical.device_config.action_details = (
            lambda room, action: (
                {"name": "Test Room"},
                {
                    "target": "device-3",
                    "method": "POST",
                    "path": "/test",
                }
            )
        )
        physical.device_config.resolve_endpoint = (
            lambda room, target: "test-endpoint"
        )
        physical.device_adapters.lookup_hold = (
            lambda room, action: None
        )
        physical.actions.dispatch_hold = accept

        # Hold press and release: both accepted.
        check(
            "Hold press accepted",
            physical.dispatch_hold_button(
                "UP", "nav-up", "pressed"
            ) is True
        )
        check(
            "Hold release accepted",
            physical.dispatch_hold_button(
                "UP", "nav-up", "released"
            ) is True
        )

        # Hold press: failed.
        physical.actions.dispatch_hold = reject
        check(
            "Hold press failed",
            physical.dispatch_hold_button(
                "DOWN", "nav-down", "pressed"
            ) is False
        )

        # Hold release: failed after successful press.
        physical.actions.dispatch_hold = accept
        check(
            "Second hold press accepted",
            physical.dispatch_hold_button(
                "LEFT", "nav-left", "pressed"
            ) is True
        )

        physical.actions.dispatch_hold = reject
        check(
            "Hold release failed",
            physical.dispatch_hold_button(
                "LEFT", "nav-left", "released"
            ) is False
        )

        # Duplicate hold: skipped, not failed.
        physical.actions.dispatch_hold = accept
        check(
            "Duplicate test press accepted",
            physical.dispatch_hold_button(
                "RIGHT", "nav-right", "pressed"
            ) is True
        )
        check(
            "Duplicate hold skipped",
            physical.dispatch_hold_button(
                "RIGHT", "nav-right", "pressed"
            ) is False
        )

        result = physical.snapshot()

        check("Dispatch attempts", result["dispatch_attempts"] == 7)
        check("Accepted count", result["dispatch_accepted"] == 4)
        check("Failed count", result["dispatch_failed"] == 3)
        check("Skipped count", result["dispatch_skipped"] == 2)
        check(
            "Counters consistent",
            result["dispatch_attempts"] ==
            result["dispatch_accepted"] +
            result["dispatch_failed"]
        )
        check(
            "Last dispatch recorded",
            result["last_dispatch"] == ("nav-right", "skipped")
        )

        print("Dispatch snapshot:", result)

    finally:
        physical.selectors.selected_room = original["selected_room"]
        physical.device_config.has_room = original["has_room"]
        physical.actions.dispatch = original["dispatch"]
        physical.actions.dispatch_hold = original["dispatch_hold"]
        physical.device_config.action_details = original["action_details"]
        physical.device_config.resolve_endpoint = original["resolve_endpoint"]
        physical.device_adapters.lookup_hold = original["lookup_hold"]

        physical._dispatch_attempts = original["attempts"]
        physical._dispatch_accepted = original["accepted"]
        physical._dispatch_failed = original["failed"]
        physical._dispatch_skipped = original["skipped"]
        physical._last_dispatch = original["last"]

        physical._hold_rooms.clear()
        physical._hold_rooms.update(original["hold_rooms"])


def run():
    print("\n=== CLONKER FLIGHT RECORDER TEST ===")

    test_ring()
    test_providers()
    test_physical()
    test_dispatch()

    fr.clear()
    gc.collect()

    print("\nFree heap after tests:", gc.mem_free())
    print("=== ALL FLIGHT RECORDER TESTS PASSED ===")


if __name__ == "__main__":
    run()
