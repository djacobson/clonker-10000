# The Clonker 10000
# clonker/web.py -- JSON v2 configuration HTTP service
#
# Clonker Designed by David Jacobson
# GitHub: https://github.com/djacobson/clonker-10000

"""Small, cooperative HTTP server for CONFIG mode.

Only one client is serviced at a time. poll() advances one accept, receive,
or send operation so the main loop can service physical controls later.
Configuration saves use the JSON v2 engine's revision and path safeguards.
"""

import time
import wifi
import socketpool
import json
import errno
import storage

from clonker import clock, logger
from clonker import device_config_v2 as device_config
from clonker import actions


# HTTP service and request limits. JSON v2 is larger than the XML v1 payload.
WEB_ROOT = "/clonker/www"
PORT = 9090
HTTP_DIAGNOSTICS = False
# 8192-byte maximum config plus HTTP headers and revision metadata.
MAX_REQUEST_BYTES = 10240
MAX_HEADER_BYTES = 2048
IO_CHUNK_BYTES = 512

# Abandon silent browser connections quickly.
IDLE_CLIENT_TIMEOUT_SECONDS = 0.5

# Allow active requests and responses more time.
CLIENT_TIMEOUT_SECONDS = 4.0

# Connection state is kept across poll() calls rather than blocking on I/O.
_pool = None
_listener = None
_client = None
_request = None
_response = None
_sent = 0
_last_activity = 0.0


def http_trace(message):
    if HTTP_DIAGNOSTICS:
        logger.info("HTTP TRACE: {}".format(message))


def _socket_would_block(error):
    """CircuitPython uses EAGAIN; EWOULDBLOCK is not always defined."""
    return error.errno == errno.EAGAIN


def clock_page():
    with open(WEB_ROOT + "/index.html", "r") as file:
        return file.read()


def clock_status():
    return {"source": clock.source(), "timestamp": clock.timestamp()}


def _close_client():
    """Reset the entire current connection after completion or failure."""
    global _client, _request, _response, _sent, _last_activity
    if _client is not None:
        try:
            _client.close()
        except OSError:
            pass
    _client = None
    _request = None
    _response = None
    _sent = 0
    _last_activity = 0.0


def start():
    """Open a nonblocking listener only when CONFIG mode is enabled."""
    global _pool, _listener
    if _listener is not None:
        return
    if not wifi.radio.connected:
        raise RuntimeError("Wi-Fi is not connected")
    _pool = socketpool.SocketPool(wifi.radio)
    listener = _pool.socket(_pool.AF_INET, _pool.SOCK_STREAM)
    try:
        try:
            listener.setsockopt(_pool.SOL_SOCKET, _pool.SO_REUSEADDR, 1)
        except (AttributeError, OSError):
            pass
        listener.bind(("0.0.0.0", PORT))
        listener.listen(2)
        listener.settimeout(0)
    except Exception:
        listener.close()
        _pool = None
        raise
    _listener = listener
    logger.info("Clonker HTTP listening on port {}".format(PORT))


def _request_complete(request):
    """Wait for a complete POST body before attempting JSON decoding.

    GET and clock-sync requests need only their headers; configuration POSTs
    additionally require one valid Content-Length and the entire body.
    """
    header_end = request.find(b"\r\n\r\n")
    if header_end < 0:
        if len(request) > MAX_HEADER_BYTES:
            raise ValueError("HTTP headers too large")
        return False
    if header_end + 4 > MAX_HEADER_BYTES:
        raise ValueError("HTTP headers too large")
    headers = bytes(request[:header_end]).split(b"\r\n")
    if not headers[0].startswith(b"POST /api/config "):
        return True
    lengths = []
    for header in headers[1:]:
        if header.lower().startswith(b"content-length:"):
            try:
                lengths.append(int(header.split(b":", 1)[1].strip()))
            except ValueError:
                raise ValueError("Invalid Content-Length")
    if len(lengths) != 1 or lengths[0] < 0:
        raise ValueError("Missing or invalid Content-Length")
    if lengths[0] > device_config.MAX_CONFIG_BYTES + 256:
        raise ValueError("Configuration body too large")
    if header_end + 4 + lengths[0] > MAX_REQUEST_BYTES:
        raise ValueError("Configuration request too large")
    return len(request) >= header_end + 4 + lengths[0]


def _json_error(message, status="400 Bad Request"):
    return json.dumps({"error": str(message)}), status


def _action_request(first_line):
    """Parse a fixed room/action request without urllib.parse.

    The browser sends ASCII IDs such as:
        /api/action?room=room-1&action=volume-up

    Reject unexpected query parameters and malformed requests.
    The dispatcher independently validates both identifiers.
    """
    path = first_line.split(b" ", 2)[1]
    prefix = b"/api/action?"

    if not path.startswith(prefix):
        raise ValueError("Invalid action URL")

    parameters = path[len(prefix):].split(b"&")

    if (len(parameters) != 2 or
            not parameters[0].startswith(b"room=") or
            not parameters[1].startswith(b"action=")):
        raise ValueError("Invalid action parameters")

    room_id = parameters[0][5:].decode("ascii")
    action_id = parameters[1][7:].decode("ascii")

    return actions.dispatch(room_id, action_id)


def _build_response(first_line, request=None):
    """Route a completed request and return an entire HTTP response as bytes."""
    logger.debug("HTTP request: {}".format(first_line))
    content_type = "application/json"

    # Serve the browser interface from Pico flash.
    if first_line.startswith(b"GET / "):
        body = clock_page()
        status = "200 OK"
        content_type = "text/html; charset=utf-8"

    elif first_line.startswith(b"GET /api/clock "):
        body = json.dumps(clock_status())
        status = "200 OK"

    # Include the active revision and filesystem ownership state.
    # current() returns a copy, so these response-only fields are not saved.
    elif first_line.startswith(b"GET /api/config "):
        config = device_config.current()
        config["filesystem_writable"] = not storage.getmount("/").readonly
        config["revision"] = device_config.revision()
        body = json.dumps(config)
        status = "200 OK"

    elif first_line.startswith(b"POST /api/clock?utc="):
        try:
            path = first_line.split(b" ", 2)[1]
            value = path.split(b"utc=", 1)[1]
            if not value.isdigit():
                raise ValueError("Invalid timestamp")
            clock.set_utc(int(value), "BROWSER")
            logger.info("Clock synchronized from browser")
            body = json.dumps(clock_status())
            status = "200 OK"
        except (ValueError, OverflowError):
            body, status = _json_error("Invalid UTC timestamp")

    # Save only in DEVICE mode. The engine checks schema, expected revision,
    # disk-vs-RAM consistency, and the path bound by the initial load().
    elif first_line.startswith(b"POST /api/config "):
        if storage.getmount("/").readonly:
            body, status = _json_error("Filesystem is read-only", "403 Forbidden")
        else:
            try:
                header_end = request.find(b"\r\n\r\n")
                headers = bytes(request[:header_end]).split(b"\r\n")
                length = None
                for header in headers[1:]:
                    if header.lower().startswith(b"content-length:"):
                        length = int(header.split(b":", 1)[1].strip())
                        break
                if length is None or length < 0:
                    raise ValueError("Missing Content-Length")
                body_start = header_end + 4
                body_bytes = bytes(request[body_start:body_start + length])
                submitted = json.loads(body_bytes.decode("utf-8"))
                if not isinstance(submitted, dict):
                    raise ValueError("Configuration must be a JSON object")
                expected_revision = submitted.pop("revision", None)
                changed = device_config.save(submitted, expected_revision)
                if changed:
                    actions.clear("Configuration changed")
                body = json.dumps({
                    "message": "Configuration saved" if changed else "Configuration unchanged",
                    "saved": changed,
                    "revision": device_config.revision()
                })
                status = "200 OK"
            except (ValueError, TypeError, UnicodeError) as error:
                body, status = _json_error(error)
            except OSError as error:
                logger.warning("Configuration persistence error: {}".format(error))
                body, status = _json_error("Configuration storage failed", "500 Internal Server Error")

    elif first_line.startswith(b"GET /remote.html "):
        with open(WEB_ROOT + "/remote.html", "r") as file:
            body = file.read()
        status = "200 OK"
        content_type = "text/html; charset=utf-8"

    # --------------------------------------------------------
    # TEMPORARY TEST ENDPOINT -- REMOVE BEFORE OUTBOUND HTTP
    #
    # CONFIG-mode bench testing only. No actual AV commands
    # are sent by the current logging-only action dispatcher.
    # --------------------------------------------------------
    elif first_line.startswith(b"POST /api/test/queue?"):
        try:
            path = first_line.split(b" ", 2)[1]
            command = path.split(b"?", 1)[1]

            if command == b"run=delayed":
                result = actions.test_delayed_bypass()

            elif command == b"run=failure":
                result = actions.test_failure_clears_queue()

            elif command == b"run=capacity":
                result = actions.test_fill_queue()

            elif command == b"run=status":
                result = actions.test_queue_status()

            elif command == b"run=clear":
                result = actions.test_clear_queue()

            else:
                raise ValueError("Unknown queue test")

            body = json.dumps(result)
            status = "200 OK"

        except (ValueError, IndexError) as error:
            body, status = _json_error(str(error))

    elif first_line.startswith(b"POST /api/action?"):
        try:
            result = _action_request(first_line)
            body = json.dumps(result)
            status = "200 OK"
        except (ValueError, IndexError, UnicodeError) as error:
            body, status = _json_error(str(error))

    else:
        body = "Not Found"
        status = "404 Not Found"
        content_type = "text/plain"

    # Send a complete Content-Length so the browser knows when to stop reading.
    payload = body.encode("utf-8")
    header = (
        "HTTP/1.1 {}\r\n"
        "Content-Type: {}\r\n"
        "Content-Length: {}\r\n"
        "Cache-Control: no-store\r\n"
        "Connection: close\r\n\r\n"
    ).format(status, content_type, len(payload))
    return header.encode("utf-8") + payload


def poll():
    """Advance at most one accept, receive, or send operation per call."""
    global _client, _request, _response, _sent, _last_activity
    if _listener is None:
        return
    now = time.monotonic()

    # Accept a new client if the server is idle.
    if _client is None:
        try:
            client, address = _listener.accept()
        except OSError as error:
            if not _socket_would_block(error):
                logger.warning("HTTP accept error: {}".format(error))
            return
        try:
            client.settimeout(0)
        except OSError:
            client.close()
            return
        _client = client
        _request = bytearray()
        _response = None
        _sent = 0
        _last_activity = now
        http_trace("ACCEPTED connection")
        return

    # Discard clients that stop making progress.
    # A connection that has sent no request data gets a short grace
    # period. Active requests and responses retain the full timeout.
    silent_client = (
        _response is None
        and _request is not None
        and len(_request) == 0
    )

    timeout = (
        IDLE_CLIENT_TIMEOUT_SECONDS
        if silent_client else CLIENT_TIMEOUT_SECONDS
    )

    if now - _last_activity > timeout:
        phase = "RECEIVING" if _response is None else "SENDING"

        logger.warning(
            "HTTP client timed out: phase={}, "
            "request_bytes={}, sent_bytes={}, response_bytes={}".format(
                phase,
                len(_request) if _request is not None else 0,
                _sent,
                len(_response) if _response is not None else 0
            )
        )

        _close_client()
        return

    # Read a bounded chunk, accumulating until the request is complete.
    if _response is None:
        buf = bytearray(IO_CHUNK_BYTES)
        try:
            count = _client.recv_into(buf)
        except OSError as error:
            if not _socket_would_block(error):
                logger.warning("HTTP receive error: {}".format(error))
                _close_client()
            return
        if count == 0:
            _close_client()
            return
        _last_activity = now
        _request.extend(memoryview(buf)[:count])
        if len(_request) > MAX_REQUEST_BYTES:
            logger.warning("HTTP request exceeded size limit")
            _close_client()
            return
        try:
            if not _request_complete(_request):
                return
        except ValueError as error:
            logger.warning("HTTP invalid request: {}".format(error))
            _close_client()
            return
        first_line = bytes(_request).split(b"\r\n", 1)[0]
        _response = _build_response(first_line, _request)
        _request = None
        return

    # Send the prepared response incrementally, then release the client.
    chunk = memoryview(_response)[_sent:_sent + IO_CHUNK_BYTES]
    try:
        count = _client.send(chunk)
    except OSError as error:
        if not _socket_would_block(error):
            logger.warning("HTTP send error: {}".format(error))
            _close_client()
        return
    if count is None or count <= 0:
        return
    _sent += count
    _last_activity = now
    if _sent >= len(_response):
        _close_client()


def stop():
    """Close the HTTP service when leaving CONFIG mode."""
    global _listener, _pool
    _close_client()
    if _listener is not None:
        _listener.close()
        _listener = None
    _pool = None
    logger.info("Clonker HTTP stopped")
