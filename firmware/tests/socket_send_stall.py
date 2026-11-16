# The Clonker 10000
# firmware/tests/socket_send_stall.py
#
# Cooperative socket send-stall regression test.
# CircuitPython 10.3.1 / Raspberry Pi Pico 2 W.
#
# Run from the REPL:
# exec(open("/tests/socket_send_stall.py").read())
#
# Stop with Ctrl+C.

import os
import time
import errno
import wifi
import socketpool

PORT = 9091
CHUNK_SIZE = 512
BODY_SIZE = 5300

POLL_INTERVAL_S = 0.001
SLOW_SEND_NS = 20_000_000
CLIENT_TIMEOUT_NS = 4_000_000_000
IDLE_TIMEOUT_NS = 200_000_000

ssid = os.getenv("CIRCUITPY_WIFI_SSID")
password = os.getenv("CIRCUITPY_WIFI_PASSWORD")

if not wifi.radio.connected:
    if not ssid:
        raise RuntimeError("Wi-Fi credentials unavailable")
    wifi.radio.connect(ssid, password)

pool = socketpool.SocketPool(wifi.radio)
listener = pool.socket(pool.AF_INET, pool.SOCK_STREAM)

try:
    listener.setsockopt(
        pool.SOL_SOCKET, pool.SO_REUSEADDR, 1
    )
except (AttributeError, OSError):
    pass

listener.bind(("0.0.0.0", PORT))
listener.listen(2)
listener.settimeout(0)

body = b"X" * BODY_SIZE
header = (
    "HTTP/1.1 200 OK\r\n"
    "Content-Type: text/plain\r\n"
    "Content-Length: {}\r\n"
    "Cache-Control: no-store\r\n"
    "Connection: close\r\n\r\n"
).format(len(body)).encode("utf-8")

response_bytes = header + body

client = None
request = None
response = None
sent = 0
last_activity = 0

requests = 0
completed = 0
timed_out = 0
send_errors = 0
slow_sends = 0
max_send_ns = 0
send_calls = 0
started = 0


def would_block(error):
    return error.errno == errno.EAGAIN


def close_client(reason):
    global client, request, response
    global sent, completed, timed_out

    if client is None:
        return

    elapsed_ms = (
        time.monotonic_ns() - started
    ) / 1_000_000

    if reason == "complete":
        completed += 1
    elif reason == "timeout":
        timed_out += 1

    print(
        "Request {}: {}, sent={}/{}, "
        "send_calls={}, max_send={:.1f}ms, "
        "slow={}, total={:.1f}ms".format(
            requests,
            reason,
            sent,
            len(response) if response else 0,
            send_calls,
            max_send_ns / 1_000_000,
            slow_sends,
            elapsed_ms
        )
    )

    try:
        client.close()
    except OSError:
        pass

    client = None
    request = None
    response = None
    sent = 0


def poll():
    global client, request, response
    global sent, last_activity, requests
    global started, send_calls, max_send_ns
    global slow_sends, send_errors

    now = time.monotonic_ns()

    # ACCEPT: one connection, then return.
    if client is None:
        try:
            new_client, address = listener.accept()
        except OSError as error:
            if would_block(error):
                return
            raise

        new_client.settimeout(0)

        client = new_client
        request = bytearray()
        response = None
        sent = 0
        send_calls = 0
        slow_sends = 0
        max_send_ns = 0
        last_activity = now
        started = now
        requests += 1
        return

    # TIMEOUT: based on the last successful progress.
    silent = response is None and len(request) == 0
    limit = (
        IDLE_TIMEOUT_NS if silent
        else CLIENT_TIMEOUT_NS
    )

    if now - last_activity > limit:
        close_client("timeout")
        return

    # RECEIVE: one read per poll.
    if response is None:
        buf = bytearray(CHUNK_SIZE)

        try:
            count = client.recv_into(buf)
        except OSError as error:
            if would_block(error):
                return
            print("Receive error:", error)
            close_client("receive_error")
            return

        if count == 0:
            close_client("peer_closed")
            return

        request.extend(memoryview(buf)[:count])
        last_activity = now

        if len(request) > 2048:
            close_client("request_too_large")
            return

        if b"\r\n\r\n" not in request:
            return

        # BUILD: prepare the complete response.
        response = response_bytes
        request = None
        sent = 0
        return

    # SEND: one 512-byte chunk per poll.
    if sent >= len(response):
        close_client("complete")
        return

    chunk = memoryview(response)[
        sent:sent + CHUNK_SIZE
    ]

    send_calls += 1
    send_started = time.monotonic_ns()

    try:
        count = client.send(chunk)
    except OSError as error:
        if would_block(error):
            return

        send_errors += 1
        print("Send error:", error)
        close_client("send_error")
        return
    finally:
        duration = (
            time.monotonic_ns() - send_started
        )

        if duration > max_send_ns:
            max_send_ns = duration

        if duration > SLOW_SEND_NS:
            slow_sends += 1
            print(
                "SLOW SEND: request={}, sent={}, "
                "duration={:.1f}ms".format(
                    requests,
                    sent,
                    duration / 1_000_000
                )
            )

    if count is None or count <= 0:
        return

    sent += count
    last_activity = now

    if sent >= len(response):
        close_client("complete")


print("Cooperative socket test ready")
print("Address: http://{}:{}".format(
    wifi.radio.ipv4_address, PORT
))
print("Response bytes:", len(response_bytes))

try:
    while True:
        poll()
        time.sleep(POLL_INTERVAL_S)

except KeyboardInterrupt:
    print("Stopped by user")

finally:
    if client is not None:
        try:
            client.close()
        except OSError:
            pass

    listener.close()

    print(
        "SUMMARY: requests={}, completed={}, "
        "timeouts={}, send_errors={}".format(
            requests, completed, timed_out, send_errors
        )
    )
