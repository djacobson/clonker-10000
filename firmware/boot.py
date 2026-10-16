# boot.py
# Clonker SERVICE (USB) / DEVICE jumper selection

import board
import digitalio
import storage

jumper = digitalio.DigitalInOut(board.GP17)
jumper.direction = digitalio.Direction.INPUT
jumper.pull = digitalio.Pull.UP

if jumper.value:
    print("CLONKER BOOT: SERVICE (USB) mode (jumper OPEN)")
else:
    print("CLONKER BOOT: DEVICE mode (jumper GROUNDED)")
    storage.remount("/", readonly=False)

jumper.deinit()
