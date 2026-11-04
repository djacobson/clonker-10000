# The Clonker 10000
# clonker/devices/roku.py
# Chapter 6 -- Experimental Roku ECP held-volume adapter
# Clonker Designed by David Jacobson

"""Roku ECP held-volume controller.

Call volume(endpoint, direction) for each observed encoder detent.
Call poll() regularly, even with an empty action queue.

A failed keyup retains held-key state for paced retries. An unresolved
release blocks new keydowns, including a change of direction.

This module does not own the action queue. HTTP acknowledgment does not
prove that the connected AVR actually changed volume.
"""

import time
from clonker.net import http_transport

IDLE_RELEASE_SECONDS = 0.25
MAX_HOLD_SECONDS = 2.0  # Experimental safety limit.
RELEASE_RETRY_SECONDS = 0.5

_endpoint = None
_direction = None
_deadline = 0.0
_started = 0.0
_next_release_attempt = 0.0
_release_pending = False


def _path(operation, direction):
    key = "VolumeUp" if direction == "up" else "VolumeDown"
    return "/{}/{}".format(operation, key)


def _send(endpoint, operation, direction):
    """Send Roku ECP command with operation-specific error context."""
    path = _path(operation, direction)

    try:
        return http_transport.send(endpoint, "POST", path)
    except (OSError, ValueError) as error:
        raise OSError(
            "ROKU {} -> {} failed: {}".format(
                path, endpoint, repr(error)
            )
        )


def held_direction():
    return _direction


def _reset():
    global _endpoint, _direction, _deadline, _started
    global _next_release_attempt, _release_pending
    _endpoint = None
    _direction = None
    _deadline = 0.0
    _started = 0.0
    _next_release_attempt = 0.0
    _release_pending = False


def release():
    """Release the held key; retain state if keyup fails.

    Return False when no key is held or retry pacing is active.
    Raise on HTTP failure so callers can log the error.
    """
    global _next_release_attempt, _release_pending

    if _direction is None:
        return False

    _release_pending = True
    now = time.monotonic()
    if now < _next_release_attempt:
        return False

    # Set pacing before I/O so a failure cannot cause a busy retry loop.
    _next_release_attempt = now + RELEASE_RETRY_SECONDS
    _send(_endpoint, "keyup", _direction)
    _reset()
    return True


def volume(endpoint, direction):
    """Observe a detent; return True only when keydown is sent.

    Reversal normally sends keyup followed immediately by keydown.
    An unresolved release blocks new keydowns instead.
    """
    global _endpoint, _direction, _deadline, _started

    if direction not in ("up", "down"):
        raise ValueError("Roku direction must be up or down")
    if not endpoint:
        raise ValueError("Roku endpoint is empty")

    now = time.monotonic()
    expired = (
        _direction is not None
        and (now >= _deadline
             or now >= _started + MAX_HOLD_SECONDS)
    )

    if _direction is not None and (
        _release_pending or expired
        or endpoint != _endpoint or direction != _direction
    ):
        release()
        if _direction is not None:
            raise OSError("Roku key release pending")

    if _direction == direction and _endpoint == endpoint:
        _deadline = time.monotonic() + IDLE_RELEASE_SECONDS
        return False

    _send(endpoint, "keydown", direction)

    now = time.monotonic()
    _endpoint = endpoint
    _direction = direction
    _started = now
    _deadline = now + IDLE_RELEASE_SECONDS
    return True


def poll():
    """Release an idle, expired, or pending hold with paced retries."""
    if _direction is None:
        return False
    now = time.monotonic()
    if (
        _release_pending or now >= _deadline
        or now >= _started + MAX_HOLD_SECONDS
    ):
        return release()
    return False


def close():
    """Attempt cleanup; preserve state if release is unresolved."""
    return release()
