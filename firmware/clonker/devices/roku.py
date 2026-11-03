# The Clonker 10000
# clonker/devices/roku.py
# Chapter 6 -- Experimental Roku ECP held-volume adapter
# Clonker Designed by David Jacobson

"""Roku ECP held-volume controller.

Call volume(endpoint, direction) for each observed encoder detent.
Call poll() regularly, even with an empty action queue.

This module does not own the action queue. Network calls use the existing
bounded blocking HTTP transport. A successful HTTP status is not proof
that a connected AVR changed volume.
"""

import time
from clonker.net import http_transport

IDLE_RELEASE_SECONDS = 0.25
MAX_HOLD_SECONDS = 2.0  # Experimental safety limit; tune after testing.

_endpoint = None
_direction = None
_deadline = 0.0
_started = 0.0


def _path(operation, direction):
    key = "VolumeUp" if direction == "up" else "VolumeDown"
    return "/{}/{}".format(operation, key)


def held_direction():
    return _direction


def _reset():
    global _endpoint, _direction, _deadline, _started
    _endpoint = None
    _direction = None
    _deadline = 0.0
    _started = 0.0


def release():
    """Attempt release of the current held key; clear local state first.

    A network failure cannot guarantee remote key release. The caller
    should surface failures rather than silently assume success.
    """
    endpoint, direction = _endpoint, _direction
    _reset()
    if direction is None:
        return False
    http_transport.send(endpoint, "POST", _path("keyup", direction))
    return True


def volume(endpoint, direction):
    """Observe one detent. Return True if an HTTP keydown was sent.

    Same-direction detents refresh the idle deadline without network I/O.
    Direction/endpoint changes release the previous key first.
    """
    global _endpoint, _direction, _deadline, _started
    if direction not in ("up", "down"):
        raise ValueError("Roku direction must be up or down")
    if not endpoint:
        raise ValueError("Roku endpoint is empty")

    now = time.monotonic()
    if _direction is not None and (
        endpoint != _endpoint
        or direction != _direction
        or now >= _started + MAX_HOLD_SECONDS
    ):
        release()

    if _direction == direction and _endpoint == endpoint:
        _deadline = time.monotonic() + IDLE_RELEASE_SECONDS
        return False

    # Do not mark a key held until keydown has been acknowledged.
    http_transport.send(endpoint, "POST", _path("keydown", direction))
    now = time.monotonic()
    _endpoint = endpoint
    _direction = direction
    _started = now
    _deadline = now + IDLE_RELEASE_SECONDS
    return True


def poll():
    """Release a held key when idle or maximum hold time expires."""
    if _direction is None:
        return False
    now = time.monotonic()
    if now >= _deadline or now >= _started + MAX_HOLD_SECONDS:
        return release()
    return False


def close():
    """Best-effort cleanup for shutdown or configuration replacement."""
    return release()
