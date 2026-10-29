"""Standalone GPIO button test for THE CLONKER 10000.

Wiring:
    Pico GP2 -> pushbutton terminal
    Pico GND -> other pushbutton terminal

Uses the Pico's internal pull-up resistor.
Run manually from the CircuitPython REPL.
"""

import time
import board
import digitalio

button = digitalio.DigitalInOut(board.GP2)
button.direction = digitalio.Direction.INPUT
button.pull = digitalio.Pull.UP

print("CLONKER physical button test")
print("Press the button. Ctrl+C to stop.")

last_state = button.value

try:
    while True:
        current_state = button.value

        if current_state != last_state:
            time.sleep(0.03)  # Basic contact debounce
            current_state = button.value

            if current_state != last_state:
                if current_state:
                    print("Button RELEASED")
                else:
                    print("Button PRESSED! CLONK!")

                last_state = current_state

        time.sleep(0.01)

finally:
    button.deinit()
    print("Button test stopped.")
