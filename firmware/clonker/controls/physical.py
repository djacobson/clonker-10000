# The Clonker 10000
# clonker/controls/physical.py
#
# Clonker Designed by David Jacobson
# GitHub: https://github.com/djacobson/clonker-10000

"""Physical GPIO controls.

Initialize once at application startup; poll during the main loop.
Individual controls and GPIO assignments will be added in Chapter 5.

The CONFIG/RUN switch simulation is managed separately in switches.py.
"""

_initialized = False


def initialize():
    """Initialize physical controls once. Return True on success."""
    global _initialized

    # Future GPIO setup goes here.
    _initialized = True
    return True


def poll():
    """Poll initialized physical controls for input events."""
    if not _initialized:
        return

    # Future switch and encoder polling goes here.
