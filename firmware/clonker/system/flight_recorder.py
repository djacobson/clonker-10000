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

# Registered diagnostic providers.
# Each provider is a callable returning a small snapshot.
_providers = {}


def register_provider(name, callback):
    """Register or replace a diagnostic snapshot provider."""
    if not isinstance(name, str) or not name:
        raise ValueError("Provider name must be a nonempty string")

    if not callable(callback):
        raise ValueError("Provider must be callable")

    _providers[name] = callback


def collect_diagnostics():
    """Collect registered diagnostics without filesystem I/O.

    Providers are evaluated only when explicitly requested.
    A failing provider must not prevent other collections.
    """
    results = {}

    for name, callback in _providers.items():
        try:
            results[name] = callback()
        except Exception as exc:
            results[name] = {
                "error": "{}: {}".format(
                    type(exc).__name__,
                    str(exc)
                )
            }

    return results


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


# Persistent flight recorder snapshots.
#
# One synchronous streaming writer serves both scheduled
# snapshots and deliberate reboot captures.
#
# Filesystem errors are nonfatal. No logging is performed
# here to avoid recursion through logger -> flight_recorder.

import os
import time

SNAPSHOT_PATH = "/clonker/flight_recorder.txt"
SNAPSHOT_TEMP = "/clonker/flight_recorder.tmp"
SNAPSHOT_BACKUPS = 3

_flush_attempts = 0
_flush_successes = 0
_flush_failures = 0
_last_flush_ms = None
_last_flush_error = None
_last_flush_reason = None


def persistence_status():
    """Return persistence statistics without filesystem I/O."""
    return {
        "attempts": _flush_attempts,
        "successes": _flush_successes,
        "failures": _flush_failures,
        "last_ms": _last_flush_ms,
        "last_error": _last_flush_error,
        "last_reason": _last_flush_reason,
    }


def _exists(path):
    """Check whether a snapshot file exists."""
    try:
        os.stat(path)
        return True
    except OSError:
        return False


def _rotate_snapshots():
    """Rotate completed snapshots, oldest first.

    Called only after the temporary snapshot is fully written.
    """
    for index in range(SNAPSHOT_BACKUPS, 0, -1):
        destination = "{}.{}".format(SNAPSHOT_PATH, index)

        if index == 1:
            source = SNAPSHOT_PATH
        else:
            source = "{}.{}".format(SNAPSHOT_PATH, index - 1)

        if not _exists(source):
            continue

        if _exists(destination):
            os.remove(destination)

        os.rename(source, destination)

    os.rename(SNAPSHOT_TEMP, SNAPSHOT_PATH)


def flush_now(reason="manual"):
    """Write a complete snapshot, returning True on success.

    A failed write or rotation never raises to the caller.
    Previous completed snapshots are preserved where possible.
    """
    global _flush_attempts, _flush_successes
    global _flush_failures, _last_flush_ms
    global _last_flush_error, _last_flush_reason

    _flush_attempts += 1
    _last_flush_reason = reason
    _last_flush_error = None

    started = time.monotonic_ns()

    try:
        # Capture diagnostic values once per snapshot.
        diagnostics = collect_diagnostics()
        recorder_stats = stats()

        with open(SNAPSHOT_TEMP, "w") as output:
            output.write("=== CLONKER FLIGHT RECORDER ===\n")
            output.write("Reason: {}\n".format(reason))
            output.write(
                "Uptime ns: {}\n".format(
                    time.monotonic_ns()
                )
            )

            output.write("\n=== RECORDER ===\n")
            for name, value in recorder_stats.items():
                output.write("{}: {}\n".format(name, value))

            output.write("\n=== DIAGNOSTICS ===\n")
            for name, values in diagnostics.items():
                output.write("{}: {}\n".format(name, values))

            output.write("\n=== RECENT LOG ===\n")
            for message in entries():
                output.write(message)
                output.write("\n")

            output.write("=== END SNAPSHOT ===\n")

        # Rotate only after the temporary file closes.
        _rotate_snapshots()

        _flush_successes += 1
        return True

    except Exception as exc:
        _flush_failures += 1
        _last_flush_error = "{}: {}".format(
            type(exc).__name__, exc
        )
        return False

    finally:
        _last_flush_ms = (
            time.monotonic_ns() - started
        ) / 1_000_000
