# The Clonker 10000
# clonker/system/flight_recorder.py
#
# Bounded, in-memory diagnostic flight recorder.
# No filesystem I/O, networking, or background tasks.
#
# Clonker Designed by David Jacobson
# GitHub: https://github.com/djacobson/clonker-10000

"""Retain a fixed-size tail of diagnostic messages in RAM.

The recorder owns storage. The logger will eventually supply
formatted messages; the scheduler will eventually coordinate
persistent snapshots.

No automatic logging, flushing, or scheduling occurs here.
"""

CAPACITY = 64

_entries = [None] * CAPACITY
_next = 0
_count = 0
_total = 0


def record(message):
    """Append one message, replacing the oldest when full."""
    global _next, _count, _total

    _entries[_next] = message
    _next = (_next + 1) % CAPACITY

    if _count < CAPACITY:
        _count += 1

    _total += 1


def entries():
    """Return retained messages in chronological order."""
    start = (_next - _count) % CAPACITY

    return [
        _entries[(start + index) % CAPACITY]
        for index in range(_count)
    ]


def stats():
    """Return recorder counters without copying messages."""
    return {
        "capacity": CAPACITY,
        "retained": _count,
        "total": _total,
        "overwritten": _total - _count,
    }


def clear():
    """Clear retained history and reset counters."""
    global _next, _count, _total

    for index in range(CAPACITY):
        _entries[index] = None

    _next = 0
    _count = 0
    _total = 0
