# The Clonker 10000
# firmware/tests/test_tcp_send.py
#
# Chapter 3, Phase B - Nonblocking TCP Send Diagnostics
#
# Hardware: Raspberry Pi Pico 2 W
# Runtime: CircuitPython 10.3.1
#
# Investigates whether nonblocking send() can distinguish
# a completed TCP connection from an unreachable endpoint.
#
# Diagnostic only. Not production firmware.
# Run manually from the REPL.

import time
import wifi
import socketpool


ROKU_HOST = "192.168.50.28"
ROKU_PORT = 8060

UNREACHABLE_HOST = "192.168.50.100"
UNREACHABLE_PORT = 8060

DELAYS = (0.0, 0.01, 0.05, 0.25)


def test_endpoint(label, host, port, delay):
    print()
    print("=" * 48)
    print("TEST:", label)
    print("TARGET: {}:{}".format(host, port))
    print("DELAY:", delay)

    pool = socketpool.SocketPool(wifi.radio)
    sock = pool.socket(pool.AF_INET, pool.SOCK_STREAM)
    sock.settimeout(0)

    # Harmless read-only HTTP request.
    request = (
        "GET /query/device-info HTTP/1.1\r\n"
        "Host: {}:{}\r\n"
        "Connection: close\r\n"
        "\r\n"
    ).format(host, port).encode()

    try:
        start = time.monotonic()

        # Step 1: Start TCP connection.
        connect_start = time.monotonic()

        try:
            sock.connect((host, port))
            print("CONNECT: immediate success")

        except OSError as error:
            print("CONNECT:", repr(error))

            if error.errno != 119:
                print("CONNECT: unexpected error")
                return

        print(
            "CONNECT CALL ELAPSED:",
            time.monotonic() - connect_start
        )

        # Step 2: Wait a controlled interval.
        # This is diagnostic only, not a production strategy.
        time.sleep(delay)

        # Step 3: Attempt exactly one nonblocking send.
        send_start = time.monotonic()

        try:
            sent = sock.send(request)

            print(
                "SEND: {} of {} bytes".format(
                    sent,
                    len(request)
                )
            )

            if sent == len(request):
                print("SEND RESULT: full buffer accepted")

            elif sent > 0:
                print("SEND RESULT: partial buffer accepted")

            else:
                print("SEND RESULT: zero bytes accepted")

        except OSError as error:
            print("SEND ERROR:", repr(error))
            print("SEND ERRNO:", error.errno)

        print(
            "SEND CALL ELAPSED:",
            time.monotonic() - send_start
        )

        print(
            "TOTAL ELAPSED:",
            time.monotonic() - start
        )

    finally:
        close_start = time.monotonic()

        try:
            sock.close()
            print("SOCKET CLOSED")

        except Exception as error:
            print("CLOSE ERROR:", repr(error))

        print(
            "CLOSE CALL ELAPSED:",
            time.monotonic() - close_start
        )


def main():
    print()
    print("CLONKER NONBLOCKING TCP SEND DIAGNOSTICS")
    print("Wi-Fi connected:", wifi.radio.connected)

    for delay in DELAYS:
        test_endpoint(
            "Reachable Roku",
            ROKU_HOST,
            ROKU_PORT,
            delay
        )

    for delay in DELAYS:
        test_endpoint(
            "Unreachable LAN address",
            UNREACHABLE_HOST,
            UNREACHABLE_PORT,
            delay
        )

    print()
    print("Diagnostics complete")


main()
