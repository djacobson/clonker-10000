# The Clonker 10000
# clonker/controls/physical.py
#
# Clonker Designed by David Jacobson
# GitHub: https://github.com/djacobson/clonker-10000

"""Physical GPIO controls.

Initialize once at startup; poll from the cooperative scheduler.
Chapter 5 first input: GP2 momentary pushbutton.

The CONFIG/RUN switch is managed separately in switches.py.
"""


import time
import board
import digitalio

from clonker.system import logger
from clonker.controls import pins


BUTTON_PIN = getattr(board, "GP{}".format(pins.POWER_TOGGLE_PIN))
DEBOUNCE_SECONDS = 0.03

_initialized = False
_button = None
_last_raw_state = True
_stable_state = True
_last_change_time = 0.0


def initialize():
    """Initialize the first physical button."""
    global _initialized
    global _button
    global _last_raw_state
    global _stable_state
    global _last_change_time

    if _initialized:
        return True

    button = digitalio.DigitalInOut(BUTTON_PIN)

    try:
        button.direction = digitalio.Direction.INPUT
        button.pull = digitalio.Pull.UP

        _last_raw_state = button.value
        _stable_state = _last_raw_state
        _last_change_time = time.monotonic()

        _button = button
        _initialized = True

    except Exception:
        button.deinit()
        raise

    logger.info("Power toggle initialized on GP{}".format(pins.POWER_TOGGLE_PIN))
    return True


def poll():
    """Detect debounced button presses and releases."""
    global _last_raw_state
    global _stable_state
    global _last_change_time

    if not _initialized:
        return

    now = time.monotonic()
    raw_state = _button.value

    if raw_state != _last_raw_state:
        _last_raw_state = raw_state
        _last_change_time = now

    if (
        raw_state != _stable_state
        and now - _last_change_time >= DEBOUNCE_SECONDS
    ):
        _stable_state = raw_state

        if _stable_state:
            logger.info("Physical button RELEASED")
        else:
            logger.info("POWER TOGGLE PRESSED! CLONK!")
