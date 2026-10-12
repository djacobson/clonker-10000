
# The Clonker 10000
# clonker/web.py
#
# Cooperative HTTP server experiment.
# CircuitPython 10.x / Raspberry Pi Pico 2 W.
#
# Port 8080: Clonker application
# Port 80: CircuitPython Web Workflow
#
# No external libraries required.

import wifi
import socketpool
import json

from clonker import clock
from clonker import logger


WEB_ROOT = "/clonker/www"
PORT = 8080

_pool = None
_listener = None


def clock_page():
    """Load the Clonker home page."""
    with open(WEB_ROOT + "/index.html", "r") as file:
        return file.read()


def clock_status():
    """Return current clock information."""
    return {
        "source": clock.source(),
        "timestamp": clock.timestamp(),
    }


def start():
    """Start the HTTP listener."""
    global _pool, _listener

    if _listener is not None:
        return

    if not wifi.radio.connected:
        raise RuntimeError("Wi-Fi is not connected")

    _pool = socketpool.SocketPool(wifi.radio)
    _listener = _pool.socket(
        _pool.AF_INET,
        _pool.SOCK_STREAM
    )

    try:
        _listener.setsockopt(
            _pool.SOL_SOCKET,
            _pool.SO_REUSEADDR,
            1
        )
    except (AttributeError, OSError):
        pass

    _listener.bind(("0.0.0.0", PORT))
    _listener.listen(1)
    _listener.settimeout(0)

    logger.info("Clonker HTTP listening on port {}".format(PORT))


def poll():
    """Handle at most one incoming HTTP request."""
    if _listener is None:
        return

    try:
        client, address = _listener.accept()
    except OSError:
        # No incoming connection.
        return

    try:
        client.settimeout(1)

        request = bytearray(1024)
        count = client.recv_into(request)

        if count <= 0:
            return

        first_line = bytes(request[:count]).split(b"\r\n", 1)[0]
        logger.debug("HTTP request: {}".format(first_line))

        if first_line.startswith(b"GET / "):
            body = clock_page()
            status = "200 OK"
            content_type = "text/html; charset=utf-8"

        elif first_line.startswith(b"GET /api/clock "):
            body = json.dumps(clock_status())
            status = "200 OK"
            content_type = "application/json"

        elif first_line.startswith(b"POST /api/clock?utc="):
            content_type = "application/json"

            try:
                # Extract UTC seconds from the URL.
                path = first_line.split(b" ", 2)[1]
                value = path.split(b"utc=", 1)[1]

                # Ensure the query contains only a timestamp.
                if not value.isdigit():
                    raise ValueError("Invalid timestamp")

                utc_seconds = int(value)

                # clock.py validates the timestamp range.
                clock.set_utc(utc_seconds, "BROWSER")

                logger.info("Clock synchronized from browser")

                body = json.dumps(clock_status())
                status = "200 OK"

            except (ValueError, OverflowError):
                body = '{"error":"Invalid UTC timestamp"}'
                status = "400 Bad Request"

        else:
            body = "Not Found"
            status = "404 Not Found"
            content_type = "text/plain"

        client.sendall(header.encode("utf-8"))
        client.sendall(payload)

    except OSError as error:
        logger.warning("HTTP connection error: {}".format(error))

    finally:
        client.close()


def stop():
    """Stop the HTTP listener."""
    global _listener, _pool

    if _listener is not None:
        _listener.close()
        _listener = None

    _pool = None
    logger.info("Clonker HTTP stopped")
