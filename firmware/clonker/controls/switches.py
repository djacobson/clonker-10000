# The Clonker 10000
# Physical switches and simulated switch states.
#
# Clonker Designed by David Jacobson
# GitHub: https://github.com/djacobson/clonker-10000

"""CONFIG/RUN application-mode selection.

There are two configured input sources:

SIMULATED:
    pins.CONFIG_SWITCH_PIN is None.
    Use _simulated_config (True = CONFIG, False = RUN).

PHYSICAL:
    pins.CONFIG_SWITCH_PIN is a GPIO number.
    A grounded input selects CONFIG; an open/high input selects RUN.
    This polarity is provisional until the physical switch is wired.

Software override (independent of the configured source):

    None  = Follow the configured source.
    True  = Force CONFIG.
    False = Force RUN.

An ordinary GPIO cannot distinguish an intentionally open switch
from a disconnected wire. No automatic presence detection is assumed.

The override affects only CONFIG/RUN application mode.
It does not change SERVICE/DEVICE filesystem ownership or send
equipment power commands.
"""

from clonker.controls import pins

_simulated_config = True
_config_override = None

_physical_input = None
_physical_pin = None


def set_simulated_config(enabled):
    """Set the simulated state; used when no physical pin is assigned."""
    global _simulated_config
    _simulated_config = bool(enabled)


def set_config_override(enabled=None):
    """Force CONFIG/ RUN, or pass None to follow the configured source."""
    global _config_override

    if enabled is not None and not isinstance(enabled, bool):
        raise ValueError("CONFIG override must be True, False, or None")

    _config_override = enabled


def config_source():
    """Describe the effective source for diagnostics."""
    if _config_override is not None:
        return "OVERRIDE"
    if pins.CONFIG_SWITCH_PIN is None:
        return "SIMULATED"
    return "PHYSICAL"


def _read_physical_config():
    """Read a physical CONFIG switch with an internal pull-up."""
    global _physical_input, _physical_pin

    pin_number = pins.CONFIG_SWITCH_PIN

    if _physical_input is None or _physical_pin != pin_number:
        import board
        import digitalio

        # Resolve the GPIO before releasing an existing input.
        gpio = getattr(board, "GP{}".format(pin_number))

        new_input = digitalio.DigitalInOut(gpio)

        try:
            new_input.direction = digitalio.Direction.INPUT
            new_input.pull = digitalio.Pull.UP
        except Exception:
            new_input.deinit()
            raise

        if _physical_input is not None:
            _physical_input.deinit()

        _physical_input = new_input
        _physical_pin = pin_number

    # Active low: grounded = CONFIG, high/open = RUN.
    return not _physical_input.value


def config_enabled():
    """Return the effective CONFIG/RUN application-mode state."""
    if _config_override is not None:
        return _config_override

    if pins.CONFIG_SWITCH_PIN is None:
        return _simulated_config

    return _read_physical_config()
