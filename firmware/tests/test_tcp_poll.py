# The Clonker 10000
# firmware/tests/test_tcp_poll.py
#
# Chapter 3, Phase B - TCP Connection Readiness Diagnostics
#
# Raspberry Pi Pico 2 W / CircuitPython 10.3.1
#
# Experimental only. Run manually from the REPL.

import time
import wifi
import socketpool
import select


HOST = "192.168.50.28"
PORT = 8060

# Fresh TCP connection for each delay.
DELAYS = (0.0, 0.01, 0.02, 0.05, 0.10, 0.25)

REQUEST = (
    "GET /query/device-info HTTP/1.1\r\n"
    "Host: 192.168.50.28:8060\r\n"
    "Connection: close\r\n"
    "\r\n"
).encode()


def test_connection(delay):
    pool = socketpool.SocketPool(wifi.radio)
    sock = pool.socket(pool.AF_INET, pool.SOCK_STREAM)
    sock.settimeout(0)

    poller = select.poll()
    registered = False

    print()
    print("=== Delay: {} seconds ===".format(delay))

    try:
        start = time.monotonic()

        try:
            sock.connect((HOST, PORT))
            print("CONNECT: immediate success")

        except OSError as error:
            print("CONNECT:", repr(error))

            if error.errno != 119:
                return

        # Diagnostic delay. Not a production solution.
        time.sleep(delay)

        poller.register(
            sock,
            select.POLLOUT | select.POLLERR | select.POLLHUP
        )
        registered = True

        events = poller.poll(0)

        print("EVENTS:", events)
        print(
            "ELAPSED:",
            time.monotonic() - start
        )

        if not events:
            print("No readiness event")
            return

        for descriptor, flags in events:
            print("FLAGS:", flags)
            print(
                "POLLOUT:",
                bool(flags & select.POLLOUT)
            )
            print(
                "POLLERR:",
                bool(flags & select.POLLERR)
            )
            print(
                "POLLHUP:",
                bool(flags & select.POLLHUP)
            )

            if flags & (select.POLLERR | select.POLLHUP):
                print("Connection error/hangup")
                return

        # Check whether the socket is actually usable.
        try:
            sent = sock.send(REQUEST)

            print(
                "SEND:",
                sent,
                "of",
                len(REQUEST),
                "bytes"
            )

        except OSError as error:
            print("SEND ERROR:", repr(error))
            return

        # This test is focused on connection readiness.
        # We do not need to read the HTTP response yet.

    finally:
        if registered:
            try:
                poller.unregister(sock)
            except Exception:
                pass

        sock.close()


def main():
    print()
    print("CLONKER TCP READINESS DIAGNOSTIC")
    print("Wi-Fi connected:", wifi.radio.connected)

    for delay in DELAYS:
        test_connection(delay)

    print()
    print("Diagnostics complete")


main()
