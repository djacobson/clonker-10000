# The Clonker 10000
# clonker/controls/physical.py
#
# Clonker Designed by David Jacobson
# GitHub: https://github.com/djacobson/clonker-10000

"""Physical control initialization and event polling.

Coordinates reusable input components.
The CONFIG/RUN switch is managed separately in switches.py.
"""

from clonker.system import logger
from clonker.controls import pins
from clonker.controls.buttons import Button


_initialized = False
_buttons = []


def initialize():
    """Initialize assigned physical buttons."""
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

    _initialized = True
    return True


def poll():
    """Poll all initialized buttons for events."""

    if not _initialized:
        return

    for button in _buttons:
        event = button.poll()

        if event is None:
            continue

        logger.info(
            "{} {}".format(button.name, event.upper())
        )
