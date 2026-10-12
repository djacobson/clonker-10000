# The Clonker 10000
# clonker/logger.py
#
# Lightweight serial logger.
# No flash writes, network dependencies, or background tasks.
#
# Clonker Designed by David Jacobson
# GitHub: https://github.com/djacobson/clonker-10000

from clonker import clock

DEBUG = 10
INFO = 20
WARNING = 30
ERROR = 40

_level = INFO

_NAMES = {
    DEBUG: "DEBUG",
    INFO: "INFO",
    WARNING: "WARNING",
    ERROR: "ERROR",
}


def set_level(level):
    """Set the minimum severity to display."""
    global _level

    if level not in _NAMES:
        raise ValueError("Invalid logging level")

    _level = level


def get_level():
    """Return the current minimum severity."""
    return _level


def log(level, message):
    """Write one timestamped message to serial."""
    if level < _level:
        return

    name = _NAMES.get(level, "UNKNOWN")

    print("{} {:<7} {}".format(
        clock.timestamp(),
        name,
        message
    ))


def debug(message):
    log(DEBUG, message)


def info(message):
    log(INFO, message)


def warning(message):
    log(WARNING, message)


def error(message):
    log(ERROR, message)
