# The Clonker 10000
# clonker/web.py
#
# Cooperative HTTP server for CircuitPython 10.x / Raspberry Pi Pico 2 W.
#
# Port 9090: Clonker config
#
# Note:
# Disable CircuitPython Web Workflow (Port 80)
# Avoids suspected socket conflicts with Clonker HTTP.
# settings.toml: CIRCUITPY_WEB_API_PORT = 0
#
# No external libraries required.
#
# Clonker Designed by David Jacobson
# GitHub: https://github.com/djacobson/clonker-10000

import time
import wifi
import socketpool
import json
import errno
import storage

from clonker import clock, logger, device_config

WEB_ROOT = "/clonker/www"
PORT = 9090
HTTP_DIAGNOSTICS = False

# Tunable limits. One client at a time; no socket call waits for network data.
MAX_REQUEST_BYTES = 2048
IO_CHUNK_BYTES = 512
CLIENT_TIMEOUT_SECONDS = 4.0

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
    """Return True for a temporary nonblocking socket condition."""
    return error.errno == errno.EAGAIN


def clock_page():
    with open(WEB_ROOT + "/index.html", "r") as file:
        return file.read()


def clock_status():
    return {"source": clock.source(), "timestamp": clock.timestamp()}


def _close_client():
    global _client, _request, _response, _sent, _last_activity
    if _client is not None:
        try:
            _client.close()
        except OSError:
            pass
        http_trace("Client closed")
    _client = None
    _request = None
    _response = None
    _sent = 0
    _last_activity = 0.0


def start():
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
    """Check whether headers and any required POST body have arrived."""
    header_end = request.find(b"\r\n\r\n")
    if header_end < 0:
        return False

    headers = bytes(request[:header_end]).split(b"\r\n")
    first_line = headers[0]

    # Existing GET and clock requests need no body.
    if not first_line.startswith(b"POST /api/config "):
        return True

    content_length = None

    for header in headers[1:]:
        if header.lower().startswith(b"content-length:"):
            try:
                content_length = int(header.split(b":", 1)[1].strip())
            except ValueError:
                raise ValueError("Invalid Content-Length")

    if content_length is None or content_length < 0:
        raise ValueError("Missing or invalid Content-Length")

    total_length = header_end + 4 + content_length

    if total_length > MAX_REQUEST_BYTES:
        raise ValueError("Configuration request too large")

    return len(request) >= total_length


def _build_response(first_line, request=None):
    logger.debug("HTTP request: {}".format(first_line))
    if first_line.startswith(b"GET / "):
        body = clock_page()
        status = "200 OK"
        content_type = "text/html; charset=utf-8"

    # HTTP Routes and handlers

    elif first_line.startswith(b"GET /api/clock "):
        body = json.dumps(clock_status())
        status = "200 OK"
        content_type = "application/json"

    elif first_line.startswith(b"GET /api/config "):
        config = device_config.current().copy()
        config["filesystem_writable"] = not storage.getmount("/").readonly
        config["revision"] = device_config.revision()
        body = json.dumps(config)
        status = "200 OK"
        content_type = "application/json"

    elif first_line.startswith(b"POST /api/clock?utc="):
        content_type = "application/json"
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
            body = '{"error":"Invalid UTC timestamp"}'
            status = "400 Bad Request"

    elif first_line.startswith(b"POST /api/config "):
        content_type = "application/json"

        if storage.getmount("/").readonly:
            status = "403 Forbidden"
            body = json.dumps({
                "error": "Filesystem is read-only"
            })
        else:
            try:
                header_end = request.find(b"\r\n\r\n")
                headers = bytes(request[:header_end]).split(b"\r\n")

                content_length = None
                for header in headers[1:]:
                    if header.lower().startswith(b"content-length:"):
                        content_length = int(
                            header.split(b":", 1)[1].strip()
                        )
                        break

                if content_length is None:
                    raise ValueError("Missing Content-Length")

                body_start = header_end + 4
                body_bytes = bytes(
                    request[body_start:body_start + content_length]
                )

                submitted = json.loads(body_bytes.decode("utf-8"))
                if not isinstance(submitted, dict):
                    raise ValueError("Configuration must be a JSON object")

                expected_revision = submitted.pop("revision", None)

                changed = device_config.save(
                    submitted,
                    expected_revision
                )

                status = "200 OK"
                body = json.dumps({
                    "message": (
                        "Configuration saved"
                        if changed else "Configuration unchanged"
                    ),
                    "saved": changed,
                    "revision": device_config.revision()
                })

            except (ValueError, TypeError, UnicodeError) as error:
                status = "400 Bad Request"
                body = json.dumps({
                    "error": str(error)
                })

    else:
        body = "Not Found"
        status = "404 Not Found"
        content_type = "text/plain"

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
    if _client is None:

        # accept Handler
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

    if now - _last_activity > CLIENT_TIMEOUT_SECONDS:
        logger.warning("HTTP client timed out")
        _close_client()
        return

    if _response is None:
        # Receive at most one bounded chunk; never wait for a slow client.
        buf = bytearray(IO_CHUNK_BYTES)
        
        # recv_into Handler
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

        # Wait for complete headers and, for config POSTs, the body.
        try:
            if not _request_complete(_request):
                return
        except ValueError as error:
            logger.warning("HTTP invalid request: {}".format(error))
            _close_client()
            return

        first_line = bytes(_request).split(b"\r\n", 1)[0]
        http_trace("RECV completed: {} bytes".format(len(_request)))
        _response = _build_response(first_line, _request)
        _request = None
        http_trace("Response prepared: {} bytes".format(len(_response)))

        return

    # Send at most one chunk; partial sends are resumed next poll.
    chunk = memoryview(_response)[_sent:_sent + IO_CHUNK_BYTES]

    # send Handler
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
        http_trace("SEND completed: {} bytes".format(_sent))
        _close_client()


def stop():
    global _listener, _pool
    _close_client()
    if _listener is not None:
        _listener.close()
        _listener = None
    _pool = None
    logger.info("Clonker HTTP stopped")
 