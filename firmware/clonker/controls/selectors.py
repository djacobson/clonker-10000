# The Clonker 10000
# clonker/controls/selectors.py
#
# Clonker Designed by David Jacobson
# GitHub: https://github.com/djacobson/clonker-10000

"""Physical three-position room selector.

LEFT   (GP3) = room-1
MIDDLE (GP6) = room-2
RIGHT  (GP7) = room-3

The selected room is application state, not an action.

Exactly one GPIO must be grounded for a valid selection.
Invalid or transitional readings are ignored.

Room existence is checked by the command caller, not here.
"""

import time
import board
import digitalio

from clonker.controls import pins


_DEBOUNCE_SECONDS = 0.05

_inputs = []
_initialized = False

_selected_room = None
_last_raw_room = None
_last_change_time = 0.0


def initialize():
    """Initialize selector GPIOs and capture the startup position."""
    global _initialized
    global _selected_room, _last_raw_room, _last_change_time

    if _initialized:
        return True

    assignments = (
        ("room-1", pins.ROOM_SELECTOR_A_PIN),
        ("room-2", pins.ROOM_SELECTOR_B_PIN),
        ("room-3", pins.ROOM_SELECTOR_C_PIN),
    )

    if any(pin is None for _, pin in assignments):
        return False

    try:
        for room_id, pin_number in assignments:
            gpio = digitalio.DigitalInOut(
                getattr(board, "GP{}".format(pin_number))
            )
            try:
                gpio.direction = digitalio.Direction.INPUT
                gpio.pull = digitalio.Pull.UP
            except Exception:
                gpio.deinit()
                raise

            _inputs.append((room_id, gpio))

        _selected_room = _read()
        _last_raw_room = _selected_room
        _last_change_time = time.monotonic()
        _initialized = True
        return True

    except Exception:
        deinit()
        raise


def _read():
    """Return the uniquely grounded room, or None."""
    active = [
        room_id for room_id, gpio in _inputs
        if not gpio.value
    ]

    return active[0] if len(active) == 1 else None


def selected_room():
    """Return the last valid, stable room selection."""
    return _selected_room


def poll():
    """Update selection; return a room ID only when it changes."""
    global _selected_room, _last_raw_room, _last_change_time

    if not _initialized:
        return None

    now = time.monotonic()
    raw_room = _read()

    if raw_room != _last_raw_room:
        _last_raw_room = raw_room
        _last_change_time = now

    if (
        raw_room is not None
        and raw_room != _selected_room
        and now - _last_change_time >= _DEBOUNCE_SECONDS
    ):
        _selected_room = raw_room
        return _selected_room

    return None


def deinit():
    """Release selector GPIO resources."""
    global _initialized
    global _selected_room, _last_raw_room, _last_change_time

    for _, gpio in _inputs:
        gpio.deinit()

    _inputs.clear()
    _initialized = False
    _selected_room = None
    _last_raw_room = None
    _last_change_time = 0.0
