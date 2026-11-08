# The Clonker 10000
# clonker/system/perf.py
#
# Clonker Designed by David Jacobson
# GitHub: https://github.com/djacobson/clonker-10000

"""Lightweight performance statistics for Clonker.

Collect execution durations using integer nanosecond timestamps.

Each named measurement tracks:
- Number of observations
- Total elapsed time
- Maximum elapsed time
- Number of observations exceeding the slow threshold

No per-event history or logging is retained.

The scheduler owns reporting intervals and decides when to reset
statistics. This module does not schedule work or perform I/O.
"""

import time


NS_PER_MS = 1_000_000
DEFAULT_SLOW_NS = 20_000_000

# Registered measurement name -> statistics.
_stats = {}


def register(name, slow_ns=DEFAULT_SLOW_NS):
    """Register a measurement with its slow threshold.

    Re-registering an existing name preserves its statistics.
    """
    if name in _stats:
        return

    _stats[name] = {
        "count": 0,
        "total_ns": 0,
        "max_ns": 0,
        "slow_count": 0,
        "slow_ns": slow_ns,
    }


def start():
    """Capture a high-resolution start timestamp."""
    return time.monotonic_ns()


def record(name, elapsed_ns):
    """Record one elapsed duration in nanoseconds.

    Measurements must be registered before use.
    """
    stat = _stats[name]

    stat["count"] += 1
    stat["total_ns"] += elapsed_ns

    if elapsed_ns > stat["max_ns"]:
        stat["max_ns"] = elapsed_ns

    if elapsed_ns > stat["slow_ns"]:
        stat["slow_count"] += 1


def stop(name, started_ns):
    """Finish and record a measurement."""
    elapsed_ns = time.monotonic_ns() - started_ns
    record(name, elapsed_ns)
    return elapsed_ns


def snapshot(name):
    """Return a summary of one measurement.

    Returns None if the measurement is not registered.
    """
    stat = _stats.get(name)

    if stat is None:
        return None

    count = stat["count"]

    return {
        "count": count,
        "avg_ms": (
            stat["total_ns"] / count / NS_PER_MS
            if count else 0.0
        ),
        "max_ms": stat["max_ns"] / NS_PER_MS,
        "slow_count": stat["slow_count"],
    }


def reset(name=None):
    """Reset one measurement or all registered measurements.

    Registered names and thresholds are preserved.
    """
    if name is None:
        names = _stats
    else:
        names = (name,)

    for key in names:
        stat = _stats[key]
        stat["count"] = 0
        stat["total_ns"] = 0
        stat["max_ns"] = 0
        stat["slow_count"] = 0
