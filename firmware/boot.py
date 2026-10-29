# boot.py
# Clonker boot mode: SERVICE (USB) / DEVICE
# Selected by the GP17 maintenance switch.

import board
import digitalio
import storage

boot_mode_switch = digitalio.DigitalInOut(board.GP17)
boot_mode_switch.direction = digitalio.Direction.INPUT
boot_mode_switch.pull = digitalio.Pull.UP

if boot_mode_switch.value:
    print("CLONKER BOOT: SERVICE (USB) mode (switch OFF)")
else:
    print("CLONKER BOOT: DEVICE mode (switch ON)")
    storage.remount("/", readonly=False)

boot_mode_switch.deinit()
