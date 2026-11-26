# The Clonker 10000
# clonker/net/web.py -- JSON configuration HTTP service
#
# Clonker Designed by David Jacobson
# GitHub: https://github.com/djacobson/clonker-10000

"""Small, cooperative HTTP server for CONFIG mode.

Only one client is serviced at a time. poll() advances one accept, receive,
or send operation so the main loop can service physical controls later.

Static HTML is streamed from flash in bounded chunks rather than loaded
into RAM as a complete response.

Configuration saves use the active JSON engine's revision and path safeguards.
Connection diagnostics are maintained separately by net/web_diag.py.
"""

import time
import wifi
import socketpool
import json
import errno
import storage
import os
import gc

from clonker.system import clock, logger
from clonker.net import web_diag
from clonker import device_config
from clonker import actions
from clonker.controls import physical
from clonker.display import oled
from clonker.devices import device_types

WEB_ROOT = "/clonker/www"
FLIGHT_RECORDER_PATH = "/clonker/flight_recorder.txt"
PORT = 9090
HTTP_DIAGNOSTICS = False

# Maximum configuration plus HTTP headers and revision metadata.
MAX_REQUEST_BYTES = device_config.MAX_CONFIG_BYTES + 2048
MAX_HEADER_BYTES = 2048
# Inbound HTTP server transport tuning.
IO_CHUNK_BYTES = 128
WEB_SEND_CHUNK_BYTES = 512
WEB_SEND_INTERVAL_NS = 10_000_000       # 10 ms

# Abandon silent browser connections quickly.
IDLE_CLIENT_TIMEOUT_NS = 200_000_000    # 200 ms

# Allow active requests and responses more time.
CLIENT_TIMEOUT_NS = 4_000_000_000       # 4 seconds

# Connection state persists across cooperative poll() calls.
_pool = None
_listener = None
_client = None
_request = None
_response = None
_sent = 0
_sent_total = 0
_response_total = 0
_last_activity = 0
_next_send_ns = 0
# Bounded HTTP processing diagnostics.
_stage = "IDLE"
_expected_request_bytes = 0
_body_start = 0
_received_request_bytes = 0
# Reusable receive storage for the single active HTTP client.
_receive_buffer = bytearray(IO_CHUNK_BYTES)
_receive_view = memoryview(_receive_buffer)

# Optional static-file stream for the current response.
_file = None


def http_trace(message):
    if HTTP_DIAGNOSTICS:
        logger.info("HTTP TRACE: {}".format(message))


def _socket_would_block(error):
    """CircuitPython uses EAGAIN; EWOULDBLOCK is not always defined."""
    return error.errno == errno.EAGAIN


def clock_status():
    return {"source": clock.source(), "timestamp": clock.timestamp()}


def _close_client(reason="closed"):
    """Release the current connection even if diagnostics fail."""
    global _client, _request, _response
    global _sent, _sent_total, _response_total
    global _last_activity, _file

    client = _client
    file_handle = _file
    sent_total = _sent_total

    # Release references before potentially failing operations.
    _client = None
    _request = None
    _response = None
    _file = None
    _sent = 0
    _sent_total = 0
    _response_total = 0
    _last_activity = 0

    if file_handle is not None:
        try:
            file_handle.close()
        except OSError:
            pass

    if client is not None:
        try:
            client.close()
        except OSError as error:
            try:
                logger.warning(
                    "HTTP client close error: {}".format(error)
                )
            except MemoryError:
                pass

    # Diagnostics must never prevent connection cleanup.
    if client is not None:
        try:
            web_diag.close(reason, sent_total)
        except Exception:
            web_diag.discard()


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
            listener.setsockopt(
                _pool.SOL_SOCKET, _pool.SO_REUSEADDR, 1
            )
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
    global _expected_request_bytes, _body_start
    # Once validated, reuse the expected request length
    # while receiving the remaining POST body.
    if _expected_request_bytes:
        return len(request) >= _expected_request_bytes
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
                lengths.append(
                    int(header.split(b":", 1)[1].strip())
                )
            except ValueError:
                raise ValueError("Invalid Content-Length")

    if len(lengths) != 1 or lengths[0] < 0:
        raise ValueError("Missing or invalid Content-Length")

    if lengths[0] > device_config.MAX_CONFIG_BYTES + 256:
        raise ValueError("Configuration body too large")

    if header_end + 4 + lengths[0] > MAX_REQUEST_BYTES:
        raise ValueError("Configuration request too large")

    _body_start = header_end + 4
    _expected_request_bytes = header_end + 4 + lengths[0]
    return len(request) >= _expected_request_bytes


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


def _http_header(status, content_type, content_length,
                 download_name=None):
    """Build a small HTTP response header."""
    header = (
        "HTTP/1.1 {}\r\n"
        "Content-Type: {}\r\n"
        "Content-Length: {}\r\n"
        "Cache-Control: no-store\r\n"
        "Connection: close\r\n"
    ).format(
        status, content_type, content_length
    )

    if download_name is not None:
        header += (
            'Content-Disposition: attachment; '
            'filename="{}"\r\n'
        ).format(download_name)

    return (header + "\r\n").encode("utf-8")


def _build_response(first_line):
    """Build response bytes or prepare a static-file stream.

    Returns:
        (initial_bytes, file_path, total_response_bytes)

    For static HTML, initial_bytes contains only the HTTP header.
    The file is opened and streamed separately by poll().

    For other routes, initial_bytes contains the complete response.
    """
    global _stage, _request
    logger.debug("HTTP request: {}".format(first_line))
    content_type = "application/json"
    file_path = None

    # Static HTML is streamed directly from Pico flash.
    if first_line.startswith(b"GET / "):
        file_path = WEB_ROOT + "/index.html"
        status = "200 OK"
        content_type = "text/html; charset=utf-8"

    elif first_line.startswith(b"GET /remote.html "):
        file_path = WEB_ROOT + "/remote.html"
        status = "200 OK"
        content_type = "text/html; charset=utf-8"

    elif (
        first_line.startswith(b"GET /api/flight-recorder ")
        or first_line.startswith(b"GET /api/flight-recorder?")
    ):
        path = first_line.split(b" ", 2)[1]
        prefix = b"/api/flight-recorder?backup="

        if path == b"/api/flight-recorder":
            backup = 0
        elif path.startswith(prefix):
            value = path[len(prefix):]
            if value in (b"1", b"2", b"3"):
                backup = int(value)
            else:
                backup = -1
        else:
            backup = -1

        if backup < 0:
            body = "Invalid flight recorder backup parameter"
            status = "400 Bad Request"
            content_type = "text/plain"
        else:
            snapshot_path = FLIGHT_RECORDER_PATH

            if backup:
                snapshot_path += ".{}".format(backup)

            try:
                os.stat(snapshot_path)
                file_path = snapshot_path
                status = "200 OK"
                content_type = "text/plain; charset=utf-8"
            except OSError:
                body = "Flight recorder snapshot not found"
                status = "404 Not Found"
                content_type = "text/plain"

    elif first_line.startswith(b"GET /api/clock "):
        body = json.dumps(clock_status())
        status = "200 OK"

    # Include response-only configuration metadata.
    # current() returns a copy, so these fields are not saved.
    elif first_line.startswith(b"GET /api/config "):
        _stage = "GET_CONFIG_COPY"
        config = device_config.current()
        config["filesystem_writable"] = (
            not storage.getmount("/").readonly
        )
        _stage = "GET_CONFIG_REVISION"
        config["revision"] = device_config.revision()
        config["device_types"] = device_types.DEVICE_TYPES
        _stage = "GET_CONFIG_JSON"
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

    # Configuration saving requires a writable filesystem (boot mode: DEVICE).
    # The engine checks schema, expected revision,
    # disk-vs-RAM consistency, and the path bound by the initial load().
    elif first_line.startswith(b"POST /api/config "):
        if storage.getmount("/").readonly:
            body, status = _json_error(
                "Filesystem is read-only", "403 Forbidden"
            )
        else:
            try:
                _stage = "POST_BODY_COPY"

                body_bytes = bytes(
                    memoryview(_request)[
                        _body_start:_expected_request_bytes
                    ]
                )

                # Release the accumulated HTTP request before
                # decoding and validating the configuration.
                _request = None

                _stage = "POST_BODY_DECODE"
                body_text = body_bytes.decode("utf-8")
                del body_bytes

                _stage = "POST_JSON"
                submitted = json.loads(body_text)
                del body_text

                if not isinstance(submitted, dict):
                    raise ValueError(
                        "Configuration must be a JSON object"
                    )

                expected_revision = submitted.pop(
                    "revision", None
                )

                post_started = time.monotonic_ns()

                _stage = "POST_SAVE"
                changed = device_config.save(
                    submitted, expected_revision
                )
                saved_at = time.monotonic_ns()

                _stage = "POST_ACTIVATION"
                if changed:
                    # Discard physical gestures captured under
                    # the previous configuration.
                    physical.configuration_changed()

                    # Discard queued commands and reset toggle
                    # histories after configuration activation.
                    actions.clear(
                        "Configuration changed",
                        reset_toggles=True
                    )

                    # Confirm successful configuration activation
                    # independently of the browser response.
                    oled.show_text("CONFIG", "SAVED!")
                cleared_at = time.monotonic_ns()

                _stage = "POST_REVISION"
                new_revision = device_config.revision()
                revised_at = time.monotonic_ns()

                _stage = "POST_RESPONSE"
                body = json.dumps({
                    "message": (
                        "Configuration saved"
                        if changed else "Configuration unchanged"
                    ),
                    "saved": changed,
                    "revision": new_revision
                })
                status = "200 OK"
                finished_at = time.monotonic_ns()

                logger.info(
                    "HTTP POST PERF: save={:.1f}ms, "
                    "queue_clear={:.1f}ms, "
                    "revision={:.1f}ms, "
                    "response={:.1f}ms, "
                    "total={:.1f}ms".format(
                        (saved_at - post_started) / 1_000_000,
                        (cleared_at - saved_at) / 1_000_000,
                        (revised_at - cleared_at) / 1_000_000,
                        (finished_at - revised_at) / 1_000_000,
                        (finished_at - post_started) / 1_000_000,
                    )
                )

            except (ValueError, TypeError, UnicodeError) as error:
                body, status = _json_error(error)

            except OSError as error:
                logger.warning(
                    "Configuration persistence error: {}".format(error)
                )
                body, status = _json_error(
                    "Configuration storage failed",
                    "500 Internal Server Error"
                )

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

    if file_path is not None:
        file_size = os.stat(file_path)[6]
        download_name = None

        if file_path.startswith(FLIGHT_RECORDER_PATH):
            download_name = (
                "flight_recorder.txt"
                + file_path[len(FLIGHT_RECORDER_PATH):]
            )

        header = _http_header(
            status, content_type, file_size,
            download_name
        )
        return header, file_path, len(header) + file_size

    _stage = "RESPONSE_ENCODE"
    payload = body.encode("utf-8")
    header = _http_header(
        status, content_type, len(payload)
    )
    response = header + payload

    return response, None, len(response)


def _advance_file():
    """Load the next bounded file chunk after the previous one was sent.

    Returns True when another chunk is ready, False when the file
    has reached EOF or a read error has closed the connection.
    """
    global _response, _sent
    global _stage

    try:
        _stage = "FILE_READ"
        data = _file.read(WEB_SEND_CHUNK_BYTES)
    except OSError as error:
        logger.warning("HTTP file read error: {}".format(error))
        _close_client("file_read_error")
        return False

    if not data:
        _close_client("complete")
        return False

    _response = data
    _sent = 0
    return True


def poll():
    """Advance at most one accept, receive, or send operation per call."""
    global _client, _request, _response
    global _sent, _sent_total, _response_total
    global _last_activity, _file
    global _stage, _expected_request_bytes
    global _body_start, _received_request_bytes
    global _next_send_ns

    if _listener is None:
        return

    now = time.monotonic_ns()

    # Accept a new client if the server is idle.
    if _client is None:
        try:
            _stage = "ACCEPT"
            client, address = _listener.accept()

        except OSError as error:
            if _socket_would_block(error):
                return

            # Unexpected accept failure may indicate a broken listener.
            # Let main.py manage listener teardown and retry backoff.
            raise

        # Register ownership immediately so low-memory recovery
        # can close the socket even if initialization fails.
        _client = client
        _expected_request_bytes = 0
        _body_start = 0
        _received_request_bytes = 0
        _stage = "CLIENT_INITIALIZE"

        try:
            _client.settimeout(0)

        except OSError:
            _close_client("client_initialize_error")
            return
        _request = bytearray()
        _response = None
        _file = None
        _sent = 0
        _sent_total = 0
        _response_total = 0
        _last_activity = now

        web_diag.begin(now)

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

    timeout_ns = (
        IDLE_CLIENT_TIMEOUT_NS
        if silent_client else CLIENT_TIMEOUT_NS
    )

    if now - _last_activity > timeout_ns:
        phase = "RECEIVING" if _response is None else "SENDING"

        logger.warning(
            "HTTP client timed out: phase={}, "
            "request_bytes={}, sent_bytes={}, response_bytes={}".format(
                phase,
                len(_request) if _request is not None else 0,
                _sent_total,
                _response_total
            )
        )

        _close_client("timeout")
        return

    # Read a bounded chunk, accumulating until the request is complete.
    if _response is None:
        _stage = "RECEIVE"

        try:
            count = _client.recv_into(_receive_buffer)

        except OSError as error:
            if not _socket_would_block(error):
                logger.warning(
                    "HTTP receive error: {}".format(error)
                )
                _close_client("receive_error")
            return

        if count == 0:
            _close_client("peer_closed")
            return

        _last_activity = now
        _stage = "REQUEST_EXTEND"
        _request.extend(_receive_view[:count])
        _received_request_bytes = len(_request)

        if len(_request) > MAX_REQUEST_BYTES:
            logger.warning("HTTP request exceeded size limit")
            _close_client("request_too_large")
            return

        try:
            _stage = "REQUEST_COMPLETE"
            if not _request_complete(_request):
                return

        except ValueError as error:
            logger.warning(
                "HTTP invalid request: {}".format(error)
            )
            _close_client("invalid_request")
            return

        _stage = "REQUEST_LINE"
        line_end = _request.find(b"\r\n")
        first_line = bytes(_request[:line_end])

        http_trace("REQUEST: {}".format(first_line))

        if web_diag.WEB_DIAGNOSTICS_ENABLED:
            web_diag.request(first_line, len(_request))
            build_started = time.monotonic_ns()

        try:
            _stage = "BUILD_RESPONSE"
            response, file_path, total_bytes = _build_response(
                first_line
            )

            if file_path is not None:
                _stage = "FILE_OPEN"
                _file = open(file_path, "rb")

        except OSError as error:
            logger.warning(
                "HTTP response preparation error: {}".format(error)
            )
            _close_client("response_error")
            return

        _response = response
        _response_total = total_bytes
        _sent = 0
        _request = None

        if web_diag.WEB_DIAGNOSTICS_ENABLED:
            web_diag.response(
                total_bytes,
                time.monotonic_ns() - build_started
            )

        return

    # If the current buffer has finished, advance the file stream.
    # Dynamic responses close immediately when their buffer finishes.
    if _sent >= len(_response):
        if _file is None:
            _close_client("complete")
        else:
            _advance_file()
        return

    # Cooperatively pace TCP send attempts without sleeping.
    # Client inactivity timeouts remain active during pacing.
    if now < _next_send_ns:
        return

    # Send the current response buffer incrementally.
    _stage = "SEND_PREPARE"
    chunk = memoryview(_response)[
        _sent:_sent + WEB_SEND_CHUNK_BYTES
    ]

    web_diag.send_attempt()
    send_started = time.monotonic_ns()

    try:
        # CircuitPython 10.3.1's lwip_tcp_send() can block
        # for up to 10 seconds retrying tcp_write() on ERR_MEM,
        # even with a nonblocking socket.
        #
        # Cooperative send pacing gives lwIP time to process
        # ACKs and reclaim native TCP resources between sends.
        # Whether this prevents the observed stalls is unproven.
        _stage = "SEND"
        count = _client.send(chunk)

    except OSError as error:
        if _socket_would_block(error):
            web_diag.send_blocked()
        else:
            logger.warning(
                "HTTP send error: {}".format(error)
            )
            _close_client("send_error")
        return

    finally:
        send_finished = time.monotonic_ns()
        _next_send_ns = send_finished + WEB_SEND_INTERVAL_NS
        send_duration = send_finished - send_started
        web_diag.send_duration(send_duration)

    if count is None or count <= 0:
        web_diag.send_zero()
        return

    web_diag.send_success(time.monotonic_ns())

    _sent += count
    _sent_total += count
    _last_activity = now

    # Dynamic responses are complete once their buffer is sent.
    # Static streams continue with the next file chunk on a later poll.
    if _sent >= len(_response) and _file is None:
        _close_client("complete")


def abort_low_memory():
    """Discard the active HTTP transaction and report failure context.

    Keep the listening socket open so a later request can succeed.
    Release resources before constructing diagnostic messages.
    """
    global _client, _request, _response, _file
    global _sent, _sent_total, _response_total, _last_activity

    free_before = gc.mem_free()
    request_bytes = (
        len(_request)
        if _request is not None
        else _received_request_bytes
    )
    expected_bytes = _expected_request_bytes
    sent_bytes = _sent_total
    response_bytes = _response_total
    stage = _stage

    client = _client
    file_handle = _file

    _client = None
    _request = None
    _response = None
    _file = None

    _sent = 0
    _sent_total = 0
    _response_total = 0
    _last_activity = 0

    web_diag.discard()

    file_close_failed = False
    socket_close_failed = False

    if file_handle is not None:
        try:
            file_handle.close()
        except Exception:
            file_close_failed = True

    if client is not None:
        try:
            client.close()
        except Exception:
            socket_close_failed = True

    client = None
    file_handle = None

    gc.collect()

    try:
        logger.warning(
            "HTTP MEMORY: stage={}, request={}, expected={}, "
            "sent={}, response={}, free_before={}, "
            "free_after={}, socket_close_failed={}, "
            "file_close_failed={}".format(
                stage,
                request_bytes,
                expected_bytes,
                sent_bytes,
                response_bytes,
                free_before,
                gc.mem_free(),
                socket_close_failed,
                file_close_failed,
            )
        )
    except MemoryError:
        pass


def stop():
    """Release the HTTP listener and its connection resources."""
    global _listener, _pool

    listener = _listener

    # Clear listener state before closing the socket.
    _listener = None
    _pool = None

    try:
        _close_client("server_stopped")
    finally:
        if listener is not None:
            try:
                listener.close()
            except OSError as error:
                logger.warning(
                    "HTTP listener close error: {}".format(error)
                )

    logger.info("Clonker HTTP stopped")
