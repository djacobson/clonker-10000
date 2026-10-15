# boot.py
# Clonker USB / DEVICE jumper detection test
# No filesystem ownership changes yet.

import board
import digitalio

jumper = digitalio.DigitalInOut(board.GP17)
jumper.direction = digitalio.Direction.INPUT
jumper.pull = digitalio.Pull.UP

if jumper.value:
    print("CLONKER BOOT: USB mode (jumper OPEN)")
else:
    print("CLONKER BOOT: DEVICE mode (jumper GROUNDED)")

jumper.deinit()
