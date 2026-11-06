# The Clonker 10000
# clonker/controls/pins.py
#
# Clonker Designed by David Jacobson
# GitHub: https://github.com/djacobson/clonker-10000

"""Central GPIO assignments for physical controls.

GPIO numbers are integers, not board.GP objects.
None means the control is not yet assigned.

This is developer configuration, not user-editable.
"""

# System and mode controls
POWER_TOGGLE_PIN = 2
CONFIG_SWITCH_PIN = 18  # GP18 -- yellow

# SERVICE / DEVICE boot switch
# GP17 -- yellow (handled separately by boot.py)

# Room selector (three-position rotary switch)
# Each position connects one GPIO input to GND.
ROOM_SELECTOR_A_PIN = 3  # GP3 -- yellow, Room 1
ROOM_SELECTOR_B_PIN = 6  # GP6 -- green, Room 2
ROOM_SELECTOR_C_PIN = 7  # GP7 -- blue, Room 3

# Volume encoder (press for mute)
VOLUME_ENCODER_A_PIN = 8        # GP8 -- yellow
VOLUME_ENCODER_B_PIN = 9        # GP9 -- green
VOLUME_ENCODER_BUTTON_PIN = 10  # GP10 -- blue

# Custom-action encoder (press to run)
ACTION_ENCODER_A_PIN = 11       # GP11 -- yellow
ACTION_ENCODER_B_PIN = 12       # GP12 -- green
ACTION_ENCODER_BUTTON_PIN = 13  # GP13 -- blue

# Navigation buttons
UP_BUTTON_PIN = 14
DOWN_BUTTON_PIN = 15
LEFT_BUTTON_PIN = 16
RIGHT_BUTTON_PIN = 19
SELECT_BUTTON_PIN = 20

# Navigation shortcuts
BACK_BUTTON_PIN = 21
HOME_BUTTON_PIN = 22

# Playback buttons
SKIP_BACK_BUTTON_PIN = 26
PLAY_PAUSE_BUTTON_PIN = 27
SKIP_FORWARD_BUTTON_PIN = 28

# OLED display - I2C (SSD1306, 64x32)
# Pin numbers are printed on the OLED PCB.
#
# Pin 4 -- SDA -- yellow -- GP4
# Pin 3 -- SCK -- green  -- GP5
# Pin 2 -- VCC -- red    -- 3V3
# Pin 1 -- GND -- black  -- GND
#
# GP4/GP5 reserved for OLED I2C.
# OLED initialization will be handled separately.
