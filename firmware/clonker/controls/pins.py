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
POWER_TOGGLE_PIN = 2  # GP2 -- tested momentary pushbutton
CONFIG_SWITCH_PIN = 18

# Room selector
ROOM_SELECTOR_A_PIN = None
ROOM_SELECTOR_B_PIN = None

# Volume encoder (press for mute)
VOLUME_ENCODER_A_PIN = None
VOLUME_ENCODER_B_PIN = None
VOLUME_ENCODER_BUTTON_PIN = None

# Custom-action selector (press to run)
ACTION_ENCODER_A_PIN = None
ACTION_ENCODER_B_PIN = None
ACTION_ENCODER_BUTTON_PIN = None

# Navigation buttons
UP_BUTTON_PIN = None
DOWN_BUTTON_PIN = None
LEFT_BUTTON_PIN = None
RIGHT_BUTTON_PIN = None
SELECT_BUTTON_PIN = None

# Navigation shortcuts
BACK_BUTTON_PIN = None
HOME_BUTTON_PIN = None
