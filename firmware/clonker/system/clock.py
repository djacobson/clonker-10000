# The Clonker 10000
# clonker/clock.py
#
# Central time service for Clonker.
# DEFAULTTIME requires no network connection.
# Future browser/NTP updates can supply UTC time.
#
# Clonker Designed by David Jacobson
# GitHub: https://github.com/djacobson/clonker-10000

# Test
# from clonker.system import clock
# clock.set_utc(1791579600, "BROWSER")
# print(clock.timestamp())

import time
# Shared application-relative reference.
# Independent of optional browser/NTP UTC synchronization.
_application_started_at = time.monotonic_ns()

_source = "DEFAULTTIME"
_reference_utc = None
_reference_monotonic = None


def source():
    """Return the current clock source."""
    return _source


def set_utc(unix_seconds, source_name="BROWSER"):
    """Set an approximate UTC reference using Unix seconds."""
    global _source, _reference_utc, _reference_monotonic

    if source_name not in ("BROWSER", "NTP"):
        raise ValueError("Invalid clock source")

    unix_seconds = int(unix_seconds)

    if not (946684800 <= unix_seconds <= 4102444800):
        raise ValueError("UTC timestamp out of range")

    _reference_monotonic = time.monotonic_ns()
    _reference_utc = unix_seconds
    _source = source_name


def uptime_ns():
    """Return elapsed nanoseconds since the Clonker clock initialized."""
    return time.monotonic_ns() - _application_started_at


def timestamp():
    """Return a printable timestamp for log messages."""
    if _reference_utc is None:
        return "[DEFAULTTIME +{:07.1f}s]".format(
            uptime_ns() / 1_000_000_000
        )

    elapsed_ns = time.monotonic_ns() - _reference_monotonic
    current_utc = _reference_utc + elapsed_ns // 1_000_000_000

    t = time.localtime(current_utc)

    return (
        "{:04d}-{:02d}-{:02d}T"
        "{:02d}:{:02d}:{:02d}Z"
    ).format(
        t.tm_year, t.tm_mon, t.tm_mday,
        t.tm_hour, t.tm_min, t.tm_sec
    )
