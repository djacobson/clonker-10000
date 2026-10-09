# The Clonker 10000
# clonker/clock.py
#
# Central time service for Clonker.
# DEFAULTTIME requires no network connection.
# Future browser/NTP updates can supply UTC time.

# Test
# from clonker import clock
# clock.set_utc(1791579600, "BROWSER")
# print(clock.timestamp())

import time

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

    unix_seconds = float(unix_seconds)

    if not (946684800 <= unix_seconds <= 4102444800):
        raise ValueError("UTC timestamp out of range")

    _reference_monotonic = time.monotonic()
    _reference_utc = unix_seconds
    _source = source_name


def timestamp():
    """Return a printable timestamp for log messages."""
    if _reference_utc is None:
        return "[DEFAULTTIME +{:07.1f}s]".format(
            time.monotonic()
        )

    elapsed = time.monotonic() - _reference_monotonic
    current_utc = _reference_utc + elapsed

    t = time.localtime(current_utc)

    return (
        "{:04d}-{:02d}-{:02d}T"
        "{:02d}:{:02d}:{:02d}Z"
    ).format(
        t.tm_year, t.tm_mon, t.tm_mday,
        t.tm_hour, t.tm_min, t.tm_sec
    )
