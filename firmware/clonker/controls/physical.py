# The Clonker 10000
# clonker/controls/physical.py
#
# Clonker Designed by David Jacobson
# GitHub: https://github.com/djacobson/clonker-10000

"""Physical control initialization, polling, and action routing.

Hardware modules detect events.
This module maps physical events to Clonker actions.

The CONFIG/RUN switch is managed separately in switches.py.
The room selector maintains its own selected-room state.
"""

from clonker.system import logger
from clonker import actions
from clonker import device_config_v2 as device_config
from clonker.controls import pins
from clonker.controls import selectors
from clonker.controls.buttons import Button

# Physical button names -> fundamental action IDs.
# Only assigned GPIO buttons are initialized.
#
# FUTURE DESIGN NOTE -- optional panel orientation:
#
# Keep physical button identity separate from logical actions.
# A future configuration setting could select between predefined
# BUTTON_ACTIONS_NORMAL and BUTTON_ACTIONS_ROTATED dictionaries.
#
# For a 180-degree panel rotation, the alternate mapping would
# exchange these logical actions:
#
#   nav-up       <-> nav-down
#   nav-left     <-> nav-right
#   skip-back    <-> skip-forward
#
# Other controls (Power, Home, Back, Select, Mute) can retain
# their original logical meanings regardless of orientation.
#
# The event loop should continue using:
#
#   action_id = BUTTON_ACTIONS.get(button.name)
#
# Selecting a different dictionary reference would require
# no changes to event processing or action dispatch.
#
# Future rotary encoder drivers should independently support
# an optional reverse=False parameter, applied to decoded
# rotation direction rather than raw quadrature signals.
#
# No orientation feature is currently implemented.
BUTTON_ACTIONS = {
    "POWER_TOGGLE": "power-toggle",
    "HOME": "home",
    "BACK": "back",
    "UP": "nav-up",
    "DOWN": "nav-down",
    "LEFT": "nav-left",
    "RIGHT": "nav-right",
    "SELECT": "select",
    "VOLUME_MUTE": "mute-toggle",
}


_initialized = False
_buttons = []


def dispatch_selected(action_id):
    """Dispatch an action to the currently selected room.

    Unconfigured rooms are harmless no-ops.
    All physical controls can reuse this helper.
    """
    room_id = selectors.selected_room()

    if room_id not in device_config.current()["rooms"]:
        logger.info(
            "PHYSICAL NO-OP: {} / {} (room unavailable)".format(
                room_id, action_id
            )
        )
        return False

    try:
        actions.dispatch(room_id, action_id)
        return True
    except Exception as exc:
        logger.warning(
            "PHYSICAL dispatch failed: {} / {}: {}".format(
                room_id, action_id, exc
            )
        )
        return False


def initialize():
    """Initialize assigned physical buttons and room selector."""
    global _initialized

    if _initialized:
        return True

    definitions = (
        ("POWER_TOGGLE", pins.POWER_TOGGLE_PIN),
        ("HOME", pins.HOME_BUTTON_PIN),
        ("BACK", pins.BACK_BUTTON_PIN),
        ("UP", pins.UP_BUTTON_PIN),
        ("DOWN", pins.DOWN_BUTTON_PIN),
        ("LEFT", pins.LEFT_BUTTON_PIN),
        ("RIGHT", pins.RIGHT_BUTTON_PIN),
        ("SELECT", pins.SELECT_BUTTON_PIN),
        ("VOLUME_MUTE", pins.VOLUME_ENCODER_BUTTON_PIN),
        ("ACTION_RUN", pins.ACTION_ENCODER_BUTTON_PIN),
    )

    for name, pin_number in definitions:
        if pin_number is None:
            continue

        button = Button(name, pin_number)

        try:
            button.initialize()
            _buttons.append(button)
            logger.info(
                "{} button initialized on GP{}".format(
                    name, pin_number
                )
            )
        except Exception as exc:
            logger.warning(
                "{} button unavailable: {}".format(name, exc)
            )

    try:
        if selectors.initialize():
            logger.info(
                "Room selector initialized; selected = {}".format(
                    selectors.selected_room()
                )
            )
        else:
            logger.warning("Room selector not assigned")
    except Exception as exc:
        logger.warning("Room selector unavailable: {}".format(exc))

    _initialized = True
    return True


def poll():
    """Poll physical inputs and route button presses."""

    if not _initialized:
        return

    # Update room state before handling button events.
    room_id = selectors.poll()

    if room_id is not None:
        logger.info("ROOM SELECTED: {}".format(room_id))

    for button in _buttons:
        event = button.poll()

        if event is None:
            continue

        logger.info(
            "{} {}".format(button.name, event.upper())
        )

        # Only stable presses trigger actions.
        if event != "pressed":
            continue

        action_id = BUTTON_ACTIONS.get(button.name)

        if action_id is not None:
            dispatch_selected(action_id)

        # ACTION_RUN will use the custom-action selection
        # maintained by the future encoder integration.
