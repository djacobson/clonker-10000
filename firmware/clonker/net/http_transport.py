# The Clonker 10000
# clonker/net/http_transport.py
#
# Chapter 3, Phase B1 -- Bounded blocking HTTP transport
#
# Clonker Designed by David Jacobson
# GitHub: https://github.com/djacobson/clonker-10000

"""Minimal outbound HTTP transport for LAN devices.

One request per TCP connection. No retries or connection reuse.

Supports HTTP GET and POST with an empty body, including Roku ECP.
Reports connect, send, response, and total timing.

This module does not know about rooms, actions, or the Dumb Queue.
Blocking calls temporarily pause Clonker's cooperative scheduler.
"""

import time
import socketpool
import wifi

from clonker.system import perf


DEFAULT_PORT = 80

# Initial diagnostic values; tune using real device measurements.
SOCKET_TIMEOUT = 0.5
TOTAL_TIMEOUT_NS = 1_500_000_000  # 1.5 seconds

MAX_STATUS_LINE = 128
HTTP_DIAGNOSTICS = False

# Aggregate timing collection. Enabled by the main scheduler later.
HTTP_PERF_ENABLED = False

_PERF_PHASES = (
    "http.connect",
    "http.send",
    "http.response",
    "http.total",
    "http.failure.total",
    "http.failure.socket",
    "http.failure.connect",
    "http.failure.send",
    "http.failure.response",
)

for _name in _PERF_PHASES:
    perf.register(_name)

_pool = None


def _trace(message):
    if HTTP_DIAGNOSTICS:
        print("HTTP TRANSPORT:", message)


def _elapsed_ms(start):
    return round(
        (time.monotonic_ns() - start) / 1_000_000, 1
    )


def _record(name, elapsed_ns):
    """Record aggregate timing only when enabled."""
    if HTTP_PERF_ENABLED:
        perf.record(name, elapsed_ns)


def _parse_endpoint(endpoint):
    """Return (IPv4 host, port) from an optional host:port string."""
    if not isinstance(endpoint, str) or not endpoint:
        raise ValueError("HTTP endpoint is empty")

    parts = endpoint.split(":")
    if len(parts) > 2:
        raise ValueError("Invalid HTTP endpoint")

    host = parts[0]
    port = DEFAULT_PORT

    if len(parts) == 2:
        port_text = parts[1]
        if not port_text or not port_text.isdigit():
            raise ValueError("Invalid HTTP port")
        port = int(port_text)

    if not 1 <= port <= 65535:
        raise ValueError("Invalid HTTP port")

    octets = host.split(".")
    if len(octets) != 4:
        raise ValueError("HTTP endpoint must use IPv4")

    for octet in octets:
        if (
            not octet
            or len(octet) > 3
            or not octet.isdigit()
            or not 0 <= int(octet) <= 255
        ):
            raise ValueError("Invalid IPv4 address")

    return host, port


def _remaining(deadline):
    """Seconds remaining in the request's cooperative deadline."""
    remaining_ns = deadline - time.monotonic_ns()
    if remaining_ns <= 0:
        raise OSError("HTTP total deadline exceeded")
    return remaining_ns / 1_000_000_000


def _prepare_socket(sock, deadline):
    """Set a bounded timeout before each potentially blocking call."""
    sock.settimeout(min(SOCKET_TIMEOUT, _remaining(deadline)))


def _read_status_line(sock, deadline):
    """Read and validate the HTTP status line, not the response body."""
    line = bytearray()
    chunk = bytearray(1)

    while len(line) < MAX_STATUS_LINE:
        _prepare_socket(sock, deadline)
        count = sock.recv_into(chunk)

        if count == 0:
            raise OSError("Connection closed before HTTP status")

        if chunk[0] == 10:
            break

        if chunk[0] != 13:
            line.append(chunk[0])
    else:
        raise ValueError("HTTP status line too long")

    try:
        fields = line.decode("ascii").split(" ", 2)

        if len(fields) < 2 or not fields[0].startswith("HTTP/"):
            raise ValueError("Malformed HTTP response")

        status = int(fields[1])
        if not 100 <= status <= 599:
            raise ValueError("Invalid HTTP status")

        return status

    except (UnicodeError, ValueError) as error:
        raise ValueError(
            "Invalid HTTP status line: {}".format(error)
        )


def _socket_pool():
    """Share the SocketPool, not individual TCP connections."""
    global _pool

    if _pool is None:
        _pool = socketpool.SocketPool(wifi.radio)

    return _pool


def send(endpoint, method, path):
    """Send one HTTP request and return acknowledgment and timing.

    Returns:
        endpoint, method, path, status,
        connect_ms, send_ms, response_ms, total_ms

    Raises:
        ValueError for invalid requests or non-2xx HTTP responses.
        OSError for connection, send, receive, or timeout failures.
    """
    host, port = _parse_endpoint(endpoint)

    if method not in ("GET", "POST"):
        raise ValueError("Unsupported HTTP method")

    if (
        not isinstance(path, str)
        or not path.startswith("/")
        or any(ch in path for ch in "\r\n")
    ):
        raise ValueError("Invalid HTTP command path")

    if not wifi.radio.connected:
        raise OSError("Wi-Fi is not connected")

    request = (
        "{} {} HTTP/1.1\r\n"
        "Host: {}:{}\r\n"
        "Connection: close\r\n"
        "Content-Length: 0\r\n"
        "\r\n"
    ).format(method, path, host, port).encode("utf-8")

    start = time.monotonic_ns()
    deadline = start + TOTAL_TIMEOUT_NS
    stage = "socket"
    phase_start = start
    sock = None
    succeeded = False

    connect_ms = None
    send_ms = None
    response_ms = None

    _trace("{} {} -> {}".format(method, path, endpoint))

    try:
        pool = _socket_pool()
        sock = pool.socket(pool.AF_INET, pool.SOCK_STREAM)

        stage = "connect"
        phase_start = time.monotonic_ns()
        _prepare_socket(sock, deadline)
        sock.connect((host, port))
        phase_end = time.monotonic_ns()
        connect_ms = round((phase_end - phase_start) / 1_000_000, 1)
        _record("http.connect", phase_end - phase_start)

        stage = "send"
        phase_start = time.monotonic_ns()
        offset = 0

        while offset < len(request):
            _prepare_socket(sock, deadline)
            count = sock.send(request[offset:])

            if count is None or count <= 0:
                raise OSError("HTTP socket send failed")

            offset += count

        phase_end = time.monotonic_ns()
        send_ms = round((phase_end - phase_start) / 1_000_000, 1)
        _record("http.send", phase_end - phase_start)

        stage = "response"
        phase_start = time.monotonic_ns()
        status = _read_status_line(sock, deadline)
        phase_end = time.monotonic_ns()
        response_ms = round(
            (phase_end - phase_start) / 1_000_000, 1
        )
        _record("http.response", phase_end - phase_start)

        if not 200 <= status <= 299:
            raise ValueError(
                "HTTP command returned status {}".format(status)
            )

        result = {
            "endpoint": endpoint,
            "method": method,
            "path": path,
            "status": status,
            "connect_ms": connect_ms,
            "send_ms": send_ms,
            "response_ms": response_ms,
            "total_ms": _elapsed_ms(start),
        }

        _trace(
            "HTTP {} | connect={} ms | send={} ms | "
            "response={} ms | total={} ms".format(
                status,
                connect_ms,
                send_ms,
                response_ms,
                result["total_ms"],
            )
        )

        succeeded = True
        return result

    except Exception as error:
        if HTTP_PERF_ENABLED:
            failure_end = time.monotonic_ns()
            _record(
                "http.failure." + stage,
                failure_end - phase_start,
            )

        _trace(
            "FAILED at {} after {} ms: {}".format(
                stage, _elapsed_ms(start), repr(error)
            )
        )
        raise

    finally:
        if sock is not None:
            try:
                sock.close()
            except OSError as error:
                _trace("Socket close error: {}".format(error))

        if HTTP_PERF_ENABLED:
            elapsed_ns = time.monotonic_ns() - start
            if succeeded:
                _record("http.total", elapsed_ns)
            else:
                _record("http.failure.total", elapsed_ns)
