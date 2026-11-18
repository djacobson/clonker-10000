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
import socketpool
import wifi
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


# Roku HTTP transport policy.
#
# Select transport independently of control behavior.
# Navigation taps currently use persistent HTTP.
# Holds, volume, and other controls retain generic HTTP.
#
# Supported values: "generic", "persistent".

TRANSPORT_POLICY = {
    "power-toggle": "generic",
    "mute-toggle": "generic",
    "volume-up": "generic",
    "volume-down": "generic",
    "nav-up": "persistent",
    "nav-down": "persistent",
    "nav-left": "persistent",
    "nav-right": "persistent",
    "skip-back": "persistent",
    "skip-forward": "persistent",
    "home": "generic",
    "back": "generic",
    "select": "generic",
    "play-pause": "generic",
}

# Physical holds are separate from ordinary taps.
HOLD_TRANSPORT = "generic"


def transport_for(action_id, hold=False):
    """Return the configured Roku HTTP transport."""
    transport = (
        HOLD_TRANSPORT if hold
        else TRANSPORT_POLICY.get(action_id, "generic")
    )

    if transport not in ("generic", "persistent"):
        raise ValueError(
            "Unsupported Roku transport: {}".format(transport)
        )

    return transport


def send(endpoint, method, path, action_id, hold=False):
    """Send Roku ECP using the selected HTTP transport.

    Transport selection does not change control behavior.
    Callers remain responsible for keydown/keyup sequencing,
    hold timing, and release safeguards.

    No automatic retry of failed requests.
    """
    transport = transport_for(action_id, hold=hold)

    if transport == "persistent":
        return persistent_send(endpoint, method, path)

    return http_transport.send(endpoint, method, path)


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
    """Release held controls and close persistent HTTP."""
    try:
        try:
            release()
        finally:
            button_up()
    finally:
        persistent_close()


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


def execute_hold(endpoint, method, path, event):
    """Execute a configured physical-button hold event."""
    if method != "POST":
        raise ValueError("Roku held-button adapter requires POST")

    key = BUTTON_COMMANDS.get(path)
    if key is None:
        raise ValueError(
            "Unsupported Roku held-button path: {}".format(path)
        )

    if not endpoint:
        raise ValueError("Roku held-button endpoint is empty")

    if event == "pressed":
        button_down(endpoint, key)
        operation = "keydown"
    elif event == "released":
        button_up(endpoint, key)
        operation = "keyup"
    else:
        raise ValueError("Invalid held-button event")

    return "ROKU {} {}".format(operation, key)


# Roku persistent HTTP transport.
#
# Reuse a recent connection for ordinary navigation taps.
# Physical holds and encoder volume retain their existing
# keydown/keyup transport and release safeguards.
# Failed requests are never automatically replayed.

PERSIST_REUSE_NS = 1_000_000_000  # 1 second
PERSIST_TIMEOUT = 0.5
PERSIST_MAX_HEADERS = 4096

_persist_pool = None
_persist_socket = None
_persist_endpoint = None
_persist_last_ns = 0


def persistent_close():
    """Discard the persistent Roku HTTP connection."""
    global _persist_socket, _persist_endpoint
    global _persist_last_ns

    sock = _persist_socket
    _persist_socket = None
    _persist_endpoint = None
    _persist_last_ns = 0

    if sock is not None:
        try:
            sock.close()
        except OSError:
            pass


def _persistent_response(sock):
    """Consume an entire, bounded HTTP response."""
    raw = bytearray()
    chunk = bytearray(256)

    while b"\r\n\r\n" not in raw:
        count = sock.recv_into(chunk)
        if count <= 0:
            raise OSError("Roku closed before HTTP headers")

        raw.extend(chunk[:count])

        if len(raw) > PERSIST_MAX_HEADERS:
            raise ValueError("Roku HTTP headers too large")

    header_bytes, body = bytes(raw).split(b"\r\n\r\n", 1)
    lines = header_bytes.decode("latin-1").split("\r\n")

    fields = lines[0].split(" ", 2)
    if len(fields) < 2 or not fields[0].startswith("HTTP/"):
        raise ValueError("Invalid Roku HTTP status line")

    status = int(fields[1])
    headers = {}

    for line in lines[1:]:
        if ":" in line:
            name, value = line.split(":", 1)
            headers[name.strip().lower()] = value.strip().lower()

    if "transfer-encoding" in headers:
        raise ValueError("Unsupported Roku transfer encoding")

    if "content-length" not in headers:
        raise ValueError("Roku response has no Content-Length")

    length = int(headers["content-length"])
    if length < 0 or length > 4096:
        raise ValueError("Invalid Roku response length")

    if len(body) > length:
        raise ValueError("Unexpected bytes after Roku response")

    remaining = length - len(body)

    while remaining:
        count = sock.recv_into(
            chunk, min(len(chunk), remaining)
        )
        if count <= 0:
            raise OSError("Roku closed during response body")
        remaining -= count

    if not 200 <= status <= 299:
        raise ValueError("Roku HTTP status {}".format(status))

    return status, headers.get("connection") == "close"


def persistent_send(endpoint, method, path):
    """Send one Roku ECP request, optionally reusing TCP.
    Never automatically retries an ambiguous request.
    """
    global _persist_pool, _persist_socket
    global _persist_endpoint, _persist_last_ns

    if method != "POST":
        raise ValueError("Roku persistent transport requires POST")

    if (
        not isinstance(path, str)
        or not path.startswith("/")
        or "\r" in path or "\n" in path
    ):
        raise ValueError("Invalid Roku request path")

    if not wifi.radio.connected:
        persistent_close()
        raise OSError("Wi-Fi disconnected")

    host, port = http_transport._parse_endpoint(endpoint)
    now = time.monotonic_ns()

    reuse = (
        _persist_socket is not None
        and _persist_endpoint == endpoint
        and 0 <= now - _persist_last_ns <= PERSIST_REUSE_NS
    )

    if not reuse:
        persistent_close()

    start = time.monotonic_ns()

    try:
        if _persist_socket is None:
            if _persist_pool is None:
                _persist_pool = socketpool.SocketPool(wifi.radio)

            sock = _persist_pool.socket(
                _persist_pool.AF_INET,
                _persist_pool.SOCK_STREAM,
            )
            _persist_socket = sock
            sock.settimeout(PERSIST_TIMEOUT)
            sock.connect((host, port))
            _persist_endpoint = endpoint

        request = (
            "POST {} HTTP/1.1\r\n"
            "Host: {}:{}\r\n"
            "Connection: keep-alive\r\n"
            "Content-Length: 0\r\n"
            "\r\n"
        ).format(path, host, port).encode("ascii")

        offset = 0
        while offset < len(request):
            count = _persist_socket.send(request[offset:])
            if count <= 0:
                raise OSError("Roku socket send failed")
            offset += count

        status, server_close = _persistent_response(
            _persist_socket
        )

        elapsed_ms = round(
            (time.monotonic_ns() - start) / 1_000_000, 1
        )

        if server_close:
            persistent_close()
        else:
            _persist_last_ns = time.monotonic_ns()

        return {
            "status": status,
            "reused": reuse,
            "total_ms": elapsed_ms,
        }

    except Exception:
        persistent_close()
        raise
