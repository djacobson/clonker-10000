# The Clonker 10000
# tests/test_room_selector.py
#
# Standalone three-position room selector test.

import time
import board
import digitalio

from clonker.controls import pins

assignments = (
    ("LEFT", pins.ROOM_SELECTOR_A_PIN),
    ("MIDDLE", pins.ROOM_SELECTOR_B_PIN),
    ("RIGHT", pins.ROOM_SELECTOR_C_PIN),
)

inputs = []

try:
    for name, gpio in assignments:
        pin = getattr(board, "GP{}".format(gpio))
        switch = digitalio.DigitalInOut(pin)
        switch.direction = digitalio.Direction.INPUT
        switch.pull = digitalio.Pull.UP
        inputs.append((name, switch))

    print("CLONKER ROOM SELECTOR TEST")
    print("Rotate knob through all three positions.")
    print("Press Ctrl-C to stop.")
    print()

    previous = None

    while True:
        # LOW means the selector connected that input to GND.
        active = tuple(
            name for name, switch in inputs
            if not switch.value
        )

        if active != previous:
            if len(active) == 1:
                print("SELECTED:", active[0])
            else:
                print("UNEXPECTED:", active)

            previous = active

        time.sleep(0.05)

finally:
    for _, switch in inputs:
        switch.deinit()
