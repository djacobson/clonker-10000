# The Clonker 10000
# Experimental nonblocking TCP diagnostics
#
# Temporary bench-test file. Not production firmware.

# The Clonker 10000
# Chapter 3, Phase B - Nonblocking TCP Investigation
#
# Platform: Raspberry Pi Pico 2 W
# Runtime: CircuitPython 10.3.1
#
# PURPOSE:
# Investigate nonblocking outbound TCP connection behavior
# using CircuitPython socketpool.
#
# OBSERVATIONS:
# - settimeout(0) connect() returned OSError(119) immediately.
# - Sending immediately afterward produced BrokenPipeError(32).
# - Whether connection completion can be polled remains unverified.
#
# This is a diagnostic experiment, NOT a production module.
# It is not intended to run automatically on the Pico.

import time
import wifi
import socketpool
import errno


HOST = "192.168.50.40"
PORT = 8080

# Test several delays between connect() and send().
DELAYS = (0.0, 0.05, 0.25, 1.0)

REQUEST = (
    "GET / HTTP/1.1\r\n"
    "Host: 192.168.50.40:8080\r\n"
    "Connection: close\r\n"
    "\r\n"
).encode()


def test_connection(delay):
    print()
    print("=== Delay: {} seconds ===".format(delay))

    pool = socketpool.SocketPool(wifi.radio)
    sock = pool.socket(pool.AF_INET, pool.SOCK_STREAM)
    sock.settimeout(0)

    try:
        start = time.monotonic()

        try:
            sock.connect((HOST, PORT))
            print("CONNECT: immediate success")

        except OSError as error:
            print("CONNECT:", repr(error))
            print("ERRNO:", error.errno)

        elapsed = time.monotonic() - start
        print("CONNECT ELAPSED:", elapsed)

        # Diagnostic delay only, not production behavior.
        time.sleep(delay)

        try:
            sent = sock.send(REQUEST)
            print("SEND:", sent, "of", len(REQUEST), "bytes")

        except OSError as error:
            print("SEND ERROR:", repr(error))
            return

        # Give the device time to produce its response.
        time.sleep(0.1)

        buffer = bytearray(128)

        try:
            count = sock.recv_into(buffer)

            if count > 0:
                print("RESPONSE:", bytes(buffer[:count]))
            else:
                print("RESPONSE: connection closed")

        except OSError as error:
            print("RECV ERROR:", repr(error))

    finally:
        sock.close()


def main():
    print("CLONKER NONBLOCKING TCP DIAGNOSTICS")
    print("CircuitPython socketpool")
    print("Wi-Fi connected:", wifi.radio.connected)

    for delay in DELAYS:
        test_connection(delay)

    print()
    print("Diagnostics complete")


main()
