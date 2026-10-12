# The Clonker 10000
# Physical switches and simulated switch states.

from clonker.controls import pins


# Temporary simulated CONFIG switch.
# True = CONFIG, False = RUN.
_simulated_config = True


def config_enabled():
    """Return current CONFIG switch state."""
    if pins.CONFIG_SWITCH_PIN is None:
        return _simulated_config

    # Future GPIO implementation goes here.
    raise NotImplementedError("CONFIG GPIO not implemented")


def set_simulated_config(enabled):
    """Set simulated switch state for development."""
    global _simulated_config
    _simulated_config = bool(enabled)
