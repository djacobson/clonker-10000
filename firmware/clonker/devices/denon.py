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

from clonker.system import perf


TCP_PORT = 23
SOCKET_TIMEOUT = 1.0
MIN_COMMAND_INTERVAL_NS = 50_000_000  # 50 ms

# Bounded, nonblocking processing of incoming AVR status.
RX_BUFFER_SIZE = 256
MAX_RX_READS = 8
_rx_buffer = bytearray(RX_BUFFER_SIZE)

# Aggregate TCP timing, controlled by main.py.
DENON_PERF_ENABLED = False

PERF_NAMES = (
    "denon.connect",
    "denon.send",
    "denon.total",
    "denon.failure.connect",
    "denon.failure.send",
    "denon.failure.total",
)

for _name in PERF_NAMES:
    perf.register(_name)

# Recognized HTTP paths with equivalent native TCP commands.
# Other Denon commands continue through generic HTTP.
VOLUME_COMMANDS = {
    "/goform/formiPhoneAppDirect.xml?MVUP": "MVUP",
    "/goform/formiPhoneAppDirect.xml?MVDOWN": "MVDOWN",
}


def volume_command(path):
    """Translate a recognized HTTP path to a Denon TCP command."""
    command = VOLUME_COMMANDS.get(path)

    if command is None:
        raise ValueError("Unsupported Denon TCP command")

    return command


_pool = None
_socket = None
_host = None
_next_send_time = 0

# Chapter 11 -- persistent TCP transport diagnostics.
# Counters live in RAM and are never written per command.
_transport_stats = {
    "connects": 0,
    "reuses": 0,
    "connect_failures": 0,
    "send_successes": 0,
    "send_failures": 0,
    "rx_failures": 0,
    "rx_bytes": 0,
    "closes": 0,
    "last_connect_ms": None,
    "last_send_ms": None,
    "last_error": None,
}

_connected_at_ns = 0
_last_send_ns = 0


def transport_snapshot():
    """Collect Denon diagnostics without network or filesystem I/O."""
    now = time.monotonic_ns()

    return {
        "connection_active": _socket is not None,
        "connected_host": _host,
        "connection_age_ms": (
            round((now - _connected_at_ns) / 1_000_000, 1)
            if _socket is not None and _connected_at_ns
            else None
        ),
        "last_send_age_ms": (
            round((now - _last_send_ns) / 1_000_000, 1)
            if _last_send_ns else None
        ),
        "pacing_remaining_ms": max(
            0,
            round((_next_send_time - now) / 1_000_000, 1)
        ),
        "socket_timeout_ms": int(SOCKET_TIMEOUT * 1000),
        "minimum_command_interval_ms":
            MIN_COMMAND_INTERVAL_NS // 1_000_000,
        "requests": dict(_transport_stats),
    }


def _record(name, elapsed_ns):
    """Record timing only when Denon PERF is enabled."""
    if DENON_PERF_ENABLED:
        perf.record(name, elapsed_ns)


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
    global _connected_at_ns

    sock = _socket

    _socket = None
    _host = None
    _next_send_time = 0
    _connected_at_ns = 0

    if sock is not None:
        _transport_stats["closes"] += 1
        try:
            sock.close()
        except OSError:
            pass


def ready():
    """Return True when another volume command may be sent."""
    return time.monotonic_ns() >= _next_send_time


def remaining_seconds():
    """Return the remaining command pacing delay in seconds."""
    remaining_ns = _next_send_time - time.monotonic_ns()
    return max(0, remaining_ns) / 1_000_000_000


def connected_host():
    """Return the active receiver IP, or None."""
    return _host


def connect(endpoint):
    """Connect or reuse the persistent receiver TCP connection."""
    global _socket, _host, _connected_at_ns

    host = _host_from_endpoint(endpoint)

    if not wifi.radio.connected:
        close()
        raise OSError("Wi-Fi is not connected")

    if _socket is not None and _host == host:
        _transport_stats["reuses"] += 1
        return

    close()

    sock = None
    started = time.monotonic_ns()

    try:
        pool = _socket_pool()
        sock = pool.socket(pool.AF_INET, pool.SOCK_STREAM)
        sock.settimeout(SOCKET_TIMEOUT)
        sock.connect((host, TCP_PORT))

        _socket = sock
        _host = host
        _connected_at_ns = time.monotonic_ns()

        _transport_stats["connects"] += 1
        _transport_stats["last_connect_ms"] = round(
            (_connected_at_ns - started) / 1_000_000, 1
        )
        _transport_stats["last_error"] = None

        _record(
            "denon.connect",
            _connected_at_ns - started,
        )

    except Exception as error:
        _transport_stats["connect_failures"] += 1
        _transport_stats["last_error"] = (
            "connect: {}: {}".format(
                type(error).__name__, error
            )
        )
        _record(
            "denon.failure.connect",
            time.monotonic_ns() - started,
        )

        if sock is not None:
            try:
                sock.close()
            except OSError:
                pass
        raise


def send_volume(endpoint, command):
    """Send a paced volume command without automatic retries."""
    global _next_send_time, _last_send_ns

    if command not in ("MVUP", "MVDOWN"):
        raise ValueError("Unsupported Denon volume command")

    if not ready():
        return False

    started = time.monotonic_ns()
    stage = "connect"
    send_started = 0

    try:
        connect(endpoint)

        stage = "send"
        send_started = time.monotonic_ns()

        data = (command + "\r").encode("ascii")
        _socket.sendall(data)

        # Preserve the existing receive-buffer drain.
        # poll_rx() retains its own failure handling.
        poll_rx()

        now = time.monotonic_ns()

        _transport_stats["send_successes"] += 1
        _transport_stats["last_send_ms"] = round(
            (now - send_started) / 1_000_000, 1
        )
        _transport_stats["last_error"] = None
        _last_send_ns = now

        _record("denon.send", now - send_started)

        _next_send_time = (
            now + MIN_COMMAND_INTERVAL_NS
        )

        _record(
            "denon.total",
            time.monotonic_ns() - started,
        )

        return True

    except Exception as error:
        now = time.monotonic_ns()

        if stage == "send":
            _transport_stats["send_failures"] += 1
            _record(
                "denon.failure.send",
                now - send_started,
            )

        _transport_stats["last_error"] = (
            "{}: {}: {}".format(
                stage, type(error).__name__, error
            )
        )

        _record(
            "denon.failure.total",
            now - started,
        )

        close()
        raise


def poll_rx():
    """Drain pending AVR status without blocking."""
    if _socket is None:
        return 0

    received = 0

    try:
        _socket.settimeout(0)

        for _ in range(MAX_RX_READS):
            try:
                count = _socket.recv_into(_rx_buffer)
            except OSError as error:
                if error.errno in (11, 35):
                    break
                raise

            if count == 0:
                raise OSError("Denon closed TCP connection")

            received += count

        _transport_stats["rx_bytes"] += received
        return received

    except Exception as error:
        _transport_stats["rx_failures"] += 1
        _transport_stats["last_error"] = (
            "receive: {}: {}".format(
                type(error).__name__, error
            )
        )
        close()
        raise

    finally:
        if _socket is not None:
            try:
                _socket.settimeout(SOCKET_TIMEOUT)
            except OSError as error:
                _transport_stats["rx_failures"] += 1
                _transport_stats["last_error"] = (
                    "restore timeout: {}: {}".format(
                        type(error).__name__, error
                    )
                )
                close()
                raise
