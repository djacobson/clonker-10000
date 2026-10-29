# The Clonker 10000
# clonker/controls/buttons.py
#
# Clonker Designed by David Jacobson
# GitHub: https://github.com/djacobson/clonker-10000

"""Reusable momentary GPIO button input.

Uses an internal pull-up and nonblocking debounce.
A pressed button connects its GPIO input to GND.

poll() returns:
    "pressed"  - stable press detected
    "released" - stable release detected
    None       - no new event
"""

import time
import board
import digitalio


class Button:
    """One active-low, debounced momentary button."""

    def __init__(self, name, pin_number, debounce_seconds=0.03):
        self.name = name
        self.pin_number = pin_number
        self.debounce_seconds = debounce_seconds

        self._input = None
        self._last_raw_state = True
        self._stable_state = True
        self._last_change_time = 0.0

    def initialize(self):
        """Claim and configure the GPIO input."""

        if self._input is not None:
            return True

        if self.pin_number is None:
            return False

        pin = getattr(board, "GP{}".format(self.pin_number))
        gpio = digitalio.DigitalInOut(pin)

        try:
            gpio.direction = digitalio.Direction.INPUT
            gpio.pull = digitalio.Pull.UP

            state = gpio.value

            self._last_raw_state = state
            self._stable_state = state
            self._last_change_time = time.monotonic()
            self._input = gpio

        except Exception:
            gpio.deinit()
            raise

        return True

    def poll(self):
        """Return an event only after a stable state change."""

        if self._input is None:
            return None

        now = time.monotonic()
        raw_state = self._input.value

        if raw_state != self._last_raw_state:
            self._last_raw_state = raw_state
            self._last_change_time = now

        if (
            raw_state != self._stable_state
            and now - self._last_change_time >= self.debounce_seconds
        ):
            self._stable_state = raw_state

            if raw_state:
                return "released"

            return "pressed"

        return None

    def deinit(self):
        """Release the GPIO resource."""

        if self._input is not None:
            self._input.deinit()
            self._input = None
