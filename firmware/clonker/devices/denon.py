# The Clonker 10000
# clonker/devices/denon.py
#
# Chapter 6 -- Denon TCP device adapter
#
# Clonker Designed by David Jacobson

"""Persistent Denon TCP volume control.

Supports MVUP and MVDOWN over TCP port 23.

One active receiver connection is maintained at a time.
Commands are paced without sleeping or blocking for pacing.

This adapter does not own the Dumb Queue or retry commands.
The caller must check readiness before sending and preserve
queue order when a command is not yet eligible.

Future response handling belongs here:
- Buffer incoming TCP bytes.
- Extract complete CR-terminated messages.
- Interpret Denon status responses separately from commands.
No response parser or status polling is implemented yet.
"""

import time
import socketpool
import wifi


TCP_PORT = 23
SOCKET_TIMEOUT = 1.0
MIN_COMMAND_INTERVAL = 0.05

_pool = None
_socket = None
_host = None
_next_send_time = 0


def _socket_pool():
    global _pool

    if _pool is None:
        _pool = socketpool.SocketPool(wifi.radio)

    return _pool


def _host_from_endpoint(endpoint):
    """Extract the IPv4 host from a configured HTTP endpoint."""
    if not isinstance(endpoint, str) or not endpoint:
        raise ValueError("Denon endpoint is empty")

    host = endpoint.split(":")[0]
    octets = host.split(".")

    if len(octets) != 4:
        raise ValueError("Denon endpoint must use IPv4")

    for octet in octets:
        if (
            not octet
            or not octet.isdigit()
            or not 0 <= int(octet) <= 255
        ):
            raise ValueError("Invalid Denon IPv4 address")

    return host


def close():
    """Close the active connection and reset adapter state."""
    global _socket, _host, _next_send_time

    sock = _socket

    _socket = None
    _host = None
    _next_send_time = 0

    if sock is not None:
        try:
            sock.close()
        except OSError:
            pass


def ready():
    """Return True when another volume command may be sent."""
    return time.monotonic() >= _next_send_time


def remaining_seconds():
    """Return the remaining command pacing delay."""
    remaining = _next_send_time - time.monotonic()
    return max(0, remaining)


def connected_host():
    """Return the active receiver IP, or None."""
    return _host


def connect(endpoint):
    """Connect to the configured Denon receiver.

    Reuse an existing connection to the same receiver.
    A changed receiver causes the old connection to close.
    """
    global _socket, _host

    host = _host_from_endpoint(endpoint)

    if not wifi.radio.connected:
        close()
        raise OSError("Wi-Fi is not connected")

    if _socket is not None and _host == host:
        return

    close()

    sock = None

    try:
        pool = _socket_pool()
        sock = pool.socket(pool.AF_INET, pool.SOCK_STREAM)
        sock.settimeout(SOCKET_TIMEOUT)
        sock.connect((host, TCP_PORT))

        _socket = sock
        _host = host

    except Exception:
        if sock is not None:
            try:
                sock.close()
            except OSError:
                pass
        raise


def send_volume(endpoint, command):
    """Send one volume command when pacing permits.

    Returns False if the command must wait.
    Returns True after the socket write completes.

    A successful write does not confirm AVR execution.
    No automatic retries are attempted.
    """
    global _next_send_time

    if command not in ("MVUP", "MVDOWN"):
        raise ValueError("Unsupported Denon volume command")

    if not ready():
        return False

    try:
        connect(endpoint)

        data = (command + "\r").encode("ascii")
        _socket.sendall(data)

        _next_send_time = (
            time.monotonic() + MIN_COMMAND_INTERVAL
        )

        return True

    except Exception:
        close()
        raise
