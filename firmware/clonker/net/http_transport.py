# The Clonker 10000
# clonker/net/http_transport.py
#
# Chapter 3, Phase B -- Minimal outbound HTTP transport
#
# Clonker Designed by David Jacobson

"""Send simple HTTP commands to configured LAN devices.

Supports:
    - IPv4 addresses with optional port
    - HTTP GET and POST
    - Empty POST bodies (Roku ECP)
    - Bounded socket operations
    - HTTP status validation

This module knows nothing about rooms, actions, or the queue.
It sends exactly one command per call.

Draft 1 is synchronous. No retries or connection reuse.
"""

import socketpool
import wifi


DEFAULT_PORT = 80
SOCKET_TIMEOUT = 1.0
MAX_STATUS_LINE = 128


def _parse_endpoint(endpoint):
    """Convert '192.168.1.10:8080' into (host, port)."""
    if not isinstance(endpoint, str) or not endpoint:
        raise ValueError("HTTP endpoint is empty")

    parts = endpoint.split(":")

    if len(parts) > 2:
        raise ValueError("Invalid HTTP endpoint")

    host = parts[0]
    port = DEFAULT_PORT

    if len(parts) == 2:
        try:
            port = int(parts[1])
        except ValueError:
            raise ValueError("Invalid HTTP port")

    if not host or not 1 <= port <= 65535:
        raise ValueError("Invalid HTTP endpoint or port")

    # IPv4 only for this first implementation.
    octets = host.split(".")
    if len(octets) != 4:
        raise ValueError("HTTP endpoint must use IPv4")

    for octet in octets:
        if not octet.isdigit() or not 0 <= int(octet) <= 255:
            raise ValueError("Invalid IPv4 address")

    return host, port


def _read_status_line(sock):
    """Read only the first HTTP response line.

    The body is deliberately ignored. Device commands only need
    acknowledgment of HTTP success or failure.
    """
    line = bytearray()
    chunk = bytearray(1)

    while len(line) < MAX_STATUS_LINE:
        count = sock.recv_into(chunk)

        if count == 0:
            raise OSError("Connection closed before HTTP status")

        if chunk[0] == 10:  # LF
            break

        if chunk[0] != 13:  # Ignore CR
            line.append(chunk[0])
    else:
        raise ValueError("HTTP status line too long")

    try:
        text = line.decode("ascii")
        fields = text.split(" ", 2)

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


def send(endpoint, method, path):
    """Send one HTTP command and return its status.

    Args:
        endpoint: IPv4 address, optionally followed by :port.
        method: 'GET' or 'POST'.
        path: HTTP request path beginning with '/'.

    Returns:
        Dictionary with endpoint, method, path, and status.

    Raises:
        ValueError: Invalid command or unsuccessful HTTP response.
        OSError: Socket, connection, or timeout failure.
    """
    host, port = _parse_endpoint(endpoint)

    if method not in ("GET", "POST"):
        raise ValueError("Unsupported HTTP method")

    if not isinstance(path, str) or not path.startswith("/"):
        raise ValueError("Invalid HTTP command path")

    if not path or any(c in path for c in "\r\n"):
        raise ValueError("Unsafe HTTP command path")

    if not wifi.radio.connected:
        raise OSError("Wi-Fi is not connected")

    request = (
        "{} {} HTTP/1.1\r\n"
        "Host: {}:{}\r\n"
        "Connection: close\r\n"
        "Content-Length: 0\r\n"
        "\r\n"
    ).format(method, path, host, port).encode("utf-8")

    pool = socketpool.SocketPool(wifi.radio)
    sock = None

    try:
        sock = pool.socket(
            pool.AF_INET,
            pool.SOCK_STREAM
        )
        sock.settimeout(SOCKET_TIMEOUT)
        sock.connect((host, port))

        # send() may write fewer bytes than requested.
        offset = 0
        while offset < len(request):
            sent = sock.send(request[offset:])

            if sent <= 0:
                raise OSError("HTTP socket send failed")

            offset += sent

        status = _read_status_line(sock)

        if not 200 <= status <= 299:
            raise ValueError(
                "HTTP command returned status {}".format(status)
            )

        return {
            "endpoint": endpoint,
            "method": method,
            "path": path,
            "status": status,
        }

    finally:
        if sock is not None:
            sock.close()
