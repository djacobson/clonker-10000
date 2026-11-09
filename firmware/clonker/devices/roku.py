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

IDLE_RELEASE_NS = 250_000_000   # 250 ms
MAX_HOLD_NS = 2_000_000_000     # 2 seconds; safety limit
RELEASE_RETRY_NS = 500_000_000  # 500 ms

# Recognized configured commands for specialized Roku behavior.
VOLUME_COMMANDS = {
    "/keypress/VolumeUp": "up",
    "/keypress/VolumeDown": "down",
}

# Physical-button paths supporting explicit keydown/keyup.
BUTTON_COMMANDS = {
    "/keypress/Up": "Up",
    "/keypress/Down": "Down",
    "/keypress/Left": "Left",
    "/keypress/Right": "Right",
    "/keypress/Rev": "Rev",
    "/keypress/Fwd": "Fwd",
}

_endpoint = None
_direction = None
_deadline = 0
_started = 0
_next_release_attempt = 0
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
    _deadline = 0
    _started = 0
    _next_release_attempt = 0
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
    now = time.monotonic_ns()
    if now < _next_release_attempt:
        return False

    # Set pacing before I/O so a failure cannot cause a busy retry loop.
    _next_release_attempt = now + RELEASE_RETRY_NS
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

    now = time.monotonic_ns()
    expired = (
        _direction is not None
        and (now >= _deadline
             or now >= _started + MAX_HOLD_NS)
    )

    if _direction is not None and (
        _release_pending or expired
        or endpoint != _endpoint or direction != _direction
    ):
        release()
        if _direction is not None:
            raise OSError("Roku key release pending")

    if _direction == direction and _endpoint == endpoint:
        _deadline = time.monotonic_ns() + IDLE_RELEASE_NS
        return False

    _send(endpoint, "keydown", direction)

    now = time.monotonic_ns()
    _endpoint = endpoint
    _direction = direction
    _started = now
    _deadline = now + IDLE_RELEASE_NS
    return True


def poll():
    """Maintain encoder and physical-button holds."""
    volume_result = False
    button_result = False

    if _direction is not None:
        now = time.monotonic_ns()
        if (
            _release_pending or now >= _deadline
            or now >= _started + MAX_HOLD_NS
        ):
            volume_result = release()

    button_result = button_poll()

    return volume_result or button_result


def close():
    """Attempt to release both types of held controls."""
    try:
        release()
    finally:
        button_up()


# Explicit physical-button holds.
# Independent of the encoder-driven volume hold.
BUTTON_MAX_HOLD_NS = 30_000_000_000     # 30 seconds

_button_endpoint = None
_button_key = None
_button_started = 0
_button_release_pending = False


def button_held_key():
    """Return the currently held physical-button key."""
    return _button_key


def _reset_button():
    global _button_endpoint, _button_key, _button_started
    global _button_release_pending

    _button_endpoint = None
    _button_key = None
    _button_started = 0
    _button_release_pending = False


def _send_button(endpoint, operation, key):
    """Send a Roku keydown or keyup for a physical button."""
    if not key or "/" in key:
        raise ValueError("Invalid Roku button key")

    path = "/{}/{}".format(operation, key)

    try:
        return http_transport.send(endpoint, "POST", path)
    except (OSError, ValueError) as error:
        raise OSError(
            "ROKU {} -> {} failed: {}".format(
                path, endpoint, repr(error)
            )
        )


def button_down(endpoint, key):
    """Begin one explicit physical-button hold."""
    global _button_endpoint, _button_key, _button_started

    if not endpoint:
        raise ValueError("Roku endpoint is empty")

    if _button_key is not None:
        if _button_endpoint == endpoint and _button_key == key:
            return False

        raise OSError(
            "Another Roku physical button is already held"
        )

    # Record the hold before transmission. If the Roku
    # receives keydown but the response fails, queue-failure
    # cleanup can still attempt the matching keyup.
    _button_endpoint = endpoint
    _button_key = key
    _button_started = time.monotonic_ns()

    _send_button(endpoint, "keydown", key)
    return True


def button_up(endpoint=None, key=None):
    """Release the active physical button once.

    Optional endpoint/key arguments verify that the release
    belongs to the original press.
    """
    global _button_release_pending

    if _button_key is None:
        return False

    if endpoint is not None and endpoint != _button_endpoint:
        raise ValueError("Roku button endpoint mismatch")

    if key is not None and key != _button_key:
        raise ValueError("Roku button key mismatch")

    _button_release_pending = True
    _send_button(_button_endpoint, "keyup", _button_key)
    _reset_button()
    return True


def button_poll():
    """Attempt one safety release if a button stays held too long."""
    if _button_key is None or _button_release_pending:
        return False

    if (
        time.monotonic_ns() - _button_started
        >= BUTTON_MAX_HOLD_NS
    ):
        return button_up()

    return False
