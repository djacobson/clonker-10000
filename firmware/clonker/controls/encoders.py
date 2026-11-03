# The Clonker 10000
# clonker/controls/encoders.py
#
# Clonker Designed by David Jacobson
# GitHub: https://github.com/djacobson/clonker-10000

"""Reusable polling driver for mechanical rotary encoders.

Designed for the Bourns PEC11R quadrature encoders.

The driver:
- Reads two GPIO inputs with internal pull-ups.
- Rejects invalid two-bit transitions.
- Accumulates quadrature transitions into steps.
- Supports optional direction reversal.
- Does not dispatch actions or perform network I/O.

poll() returns:
    +1   one completed step in the positive direction
    -1   one completed step in the negative direction
     0   no completed step

The encoder pushbutton is handled separately by Button.

This is a cooperative polling implementation. Movement during
blocking operations may be missed. Test under actual workloads.

steps_per_detent may require adjustment after bench testing.
"""


import board
import digitalio


# Quadrature transition table.
# Index: (previous_AB << 2) | current_AB
# States are encoded with A as bit 1 and B as bit 0.
_TRANSITIONS = (
     0, -1, +1,  0,
    +1,  0,  0, -1,
    -1,  0,  0, +1,
     0, +1, -1,  0,
)


class Encoder:
    """One two-channel mechanical rotary encoder."""

    def __init__(
        self,
        name,
        pin_a,
        pin_b,
        reverse=False,
        steps_per_detent=4,
    ):
        if steps_per_detent not in (1, 2, 4):
            raise ValueError(
                "steps_per_detent must be 1, 2, or 4"
            )

        self.name = name
        self.pin_a = pin_a
        self.pin_b = pin_b
        self.reverse = reverse
        self.steps_per_detent = steps_per_detent

        self._a = None
        self._b = None
        self._previous = None
        self._accumulator = 0

    def initialize(self):
        """Claim GPIO inputs and capture their initial state."""

        if self._a is not None:
            return True

        if self.pin_a is None or self.pin_b is None:
            return False

        if self.pin_a == self.pin_b:
            raise ValueError("Encoder A and B pins must differ")

        a = None
        b = None

        try:
            a = digitalio.DigitalInOut(
                getattr(board, "GP{}".format(self.pin_a))
            )
            a.direction = digitalio.Direction.INPUT
            a.pull = digitalio.Pull.UP

            b = digitalio.DigitalInOut(
                getattr(board, "GP{}".format(self.pin_b))
            )
            b.direction = digitalio.Direction.INPUT
            b.pull = digitalio.Pull.UP

            self._a = a
            self._b = b
            self._previous = self._read()
            self._accumulator = 0

            return True

        except Exception:
            if b is not None:
                b.deinit()
            if a is not None:
                a.deinit()
            raise

    def _read(self):
        """Return the current two-bit A/B state."""

        return (
            (int(self._a.value) << 1)
            | int(self._b.value)
        )

    def poll(self):
        """Decode movement since the previous sample."""

        if self._a is None:
            return 0

        current = self._read()
        previous = self._previous

        if current == previous:
            return 0

        index = (previous << 2) | current
        delta = _TRANSITIONS[index]

        self._previous = current

        # Both bits changed: invalid or missed transition.
        # Discard the incomplete movement.
        if delta == 0:
            self._accumulator = 0
            return 0

        self._accumulator += delta

        if abs(self._accumulator) < self.steps_per_detent:
            return 0

        direction = (
            1 if self._accumulator > 0 else -1
        )

        self._accumulator = 0

        if self.reverse:
            direction = -direction

        return direction

    def deinit(self):
        """Release GPIO resources."""

        if self._a is not None:
            self._a.deinit()
            self._a = None

        if self._b is not None:
            self._b.deinit()
            self._b = None

        self._previous = None
        self._accumulator = 0
