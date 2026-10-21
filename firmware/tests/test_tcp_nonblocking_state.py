# The Clonker 10000
# Nonblocking TCP Connection State Diagnostics
#
# Standalone bench test -- NOT production firmware.
#
# Investigates CircuitPython socketpool TCP behavior:
#   1. Initial nonblocking connect()
#   2. Connection state and readiness
#   3. Sending an HTTP request
#   4. Receiving the HTTP response
#   5. Timeout and error behavior
#
# Does not modify the production action engine.

import time
import errno
import wifi
import socketpool


ROKU_IP = "192.168.50.28"
ROKU_PORT = 8060

UNREACHABLE_IP = "192.168.50.100"

POLL_INTERVAL = 0.02
TEST_DEADLINE = 2.0

# Read-only Roku ECP endpoint.
HTTP_REQUEST = (
    "GET /query/device-info HTTP/1.1\r\n"
    "Host: {}\r\n"
    "Connection: close\r\n"
    "\r\n"
).format(ROKU_IP).encode("ascii")


def error_number(error):
    number = getattr(error, "errno", None)

    if number is None and error.args:
        number = error.args[0]

    return number


def trace(start, message):
    elapsed = time.monotonic() - start
    print("{:.3f}s  {}".format(elapsed, message))


def test_connection(label, ip, port, request=None):
    print()
    print("=" * 52)
    print("TEST:", label)
    print("TARGET: {}:{}".format(ip, port))
    print("=" * 52)

    pool = socketpool.SocketPool(wifi.radio)
    sock = pool.socket(pool.AF_INET, pool.SOCK_STREAM)

    start = time.monotonic()
    deadline = start + TEST_DEADLINE

    state = "CONNECTING"
    sent = 0
    received = 0
    response_preview = bytearray()
    attempts = 0
    last_error = None

    try:
        sock.setblocking(False)
        trace(start, "Nonblocking socket created")

        # Initiate connection ONCE.
        try:
            sock.connect((ip, port))
            trace(start, "connect() returned success")

        except OSError as error:
            last_error = error_number(error)
            trace(
                start,
                "connect() returned OSError({})".format(
                    last_error
                )
            )

        # Probe whether the socket becomes usable.
        #
        # CircuitPython socketpool does not necessarily
        # provide select()/poll() or SO_ERROR support.
        #
        # We therefore use send() as a practical probe
        # for this experiment, recording every outcome.
        #
        # A successful send means the socket accepted
        # bytes, NOT that the remote device executed
        # the request.

        if request is None:
            # For an unreachable target, use a harmless
            # HTTP request so we can observe send errors.
            request = (
                "GET / HTTP/1.1\r\n"
                "Host: {}\r\n"
                "Connection: close\r\n"
                "\r\n"
            ).format(ip).encode("ascii")

        while time.monotonic() < deadline:
            attempts += 1

            if state == "CONNECTING":
                try:
                    count = sock.send(request[sent:])

                    if count is None:
                        trace(start, "send() returned None")
                    elif count > 0:
                        sent += count
                        trace(
                            start,
                            "send() accepted {} bytes; total {}"
                            .format(count, sent)
                        )

                        if sent == len(request):
                            state = "RECEIVING"
                            trace(
                                start,
                                "Request fully accepted by socket"
                            )
                    else:
                        trace(start, "send() returned zero")

                except OSError as error:
                    number = error_number(error)

                    if number != last_error:
                        trace(
                            start,
                            "send() OSError({})".format(number)
                        )
                        last_error = number

                    # Don't assume an error is transient.
                    # Keep probing within the deadline,
                    # strictly for diagnostic purposes.

            elif state == "RECEIVING":
                try:
                    data = sock.recv(256)

                    if data:
                        received += len(data)

                        remaining = 512 - len(response_preview)
                        if remaining > 0:
                            response_preview.extend(
                                data[:remaining]
                            )

                        trace(
                            start,
                            "recv() returned {} bytes"
                            .format(len(data))
                        )

                    else:
                        trace(start, "Remote closed connection")
                        state = "COMPLETE"
                        break

                except OSError as error:
                    number = error_number(error)

                    if number != last_error:
                        trace(
                            start,
                            "recv() OSError({})".format(number)
                        )
                        last_error = number

            time.sleep(POLL_INTERVAL)

        if state != "COMPLETE":
            trace(start, "Diagnostic deadline reached")

        print()
        print("FINAL STATE:", state)
        print("POLL ATTEMPTS:", attempts)
        print("BYTES SENT:", sent)
        print("BYTES RECEIVED:", received)
        print(
            "TOTAL ELAPSED:",
            round(time.monotonic() - start, 3)
        )

        if response_preview:
            print()
            print("HTTP RESPONSE PREVIEW:")
            try:
                print(
                    bytes(response_preview).decode(
                        "utf-8", "replace"
                    )
                )
            except Exception as error:
                print("Decode error:", repr(error))

    finally:
        try:
            sock.close()
            trace(start, "Socket closed")
        except OSError as error:
            trace(
                start,
                "Close error: {}".format(repr(error))
            )


print()
print("CLONKER NONBLOCKING TCP STATE DIAGNOSTICS")
print("CircuitPython 10.3.1 / Pico 2 W")
print("Wi-Fi connected:", wifi.radio.connected)

if not wifi.radio.connected:
    raise RuntimeError("Wi-Fi not connected")


test_connection(
    "Reachable Roku",
    ROKU_IP,
    ROKU_PORT,
    HTTP_REQUEST
)

test_connection(
    "Unreachable LAN address",
    UNREACHABLE_IP,
    ROKU_PORT
)

print()
print("Diagnostics complete")
