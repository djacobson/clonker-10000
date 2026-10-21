# The Clonker 10000
# firmware/tests/test_tcp_poll.py
#
# Chapter 3, Phase B - Nonblocking TCP Readiness Test
#
# Target: Raspberry Pi Pico 2 W
# Runtime: CircuitPython 10.3.1
#
# Clonker Designed by David Jacobson
#
# PURPOSE:
# Investigate select.poll() behavior following a nonblocking
# TCP connect() that initially reports OSError(119).
#
# This is an isolated diagnostic, NOT production firmware.
# It must be run manually from the CircuitPython REPL.

import time
import wifi
import socketpool
import select


# Sunroom Roku Ultra - HTTP ECP
HOST = "192.168.50.28"
PORT = 8060

TIMEOUT_SECONDS = 2.0
POLL_INTERVAL_SECONDS = 0.01

REQUEST = (
    "GET /query/device-info HTTP/1.1\r\n"
    "Host: 192.168.50.28:8060\r\n"
    "Connection: close\r\n"
    "\r\n"
).encode()


def test_tcp_poll():
    print()
    print("CLONKER TCP POLL DIAGNOSTIC")
    print("Wi-Fi connected:", wifi.radio.connected)
    print("Target: {}:{}".format(HOST, PORT))

    pool = socketpool.SocketPool(wifi.radio)
    sock = pool.socket(pool.AF_INET, pool.SOCK_STREAM)
    sock.settimeout(0)

    poller = select.poll()
    registered = False

    try:
        start = time.monotonic()

        # Initiate the TCP connection without blocking.
        try:
            sock.connect((HOST, PORT))
            print("CONNECT: immediate success")

        except OSError as error:
            print("CONNECT:", repr(error))
            print("CONNECT ERRNO:", error.errno)

            if error.errno != 119:
                raise

        # Watch for writable, error, or hangup conditions.
        poller.register(
            sock,
            select.POLLOUT | select.POLLERR | select.POLLHUP
        )
        registered = True

        print("Polling for readiness...")

        deadline = start + TIMEOUT_SECONDS
        ready = False

        while time.monotonic() < deadline:
            # Zero timeout: poll() itself must not wait.
            events = poller.poll(0)

            if events:
                elapsed = time.monotonic() - start

                print("EVENTS:", events)
                print("ELAPSED:", elapsed)

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
                        print("Connection error/hangup reported")
                        return

                    if flags & select.POLLOUT:
                        ready = True
                        break

                if ready:
                    break

            time.sleep(POLL_INTERVAL_SECONDS)

        if not ready:
            print("TIMEOUT: socket never became writable")
            return

        # POLLOUT is only a readiness indication.
        # Verify whether the connection actually accepts data.
        print("Attempting HTTP request...")

        offset = 0
        send_deadline = time.monotonic() + TIMEOUT_SECONDS

        while offset < len(REQUEST):
            if time.monotonic() >= send_deadline:
                print("SEND TIMEOUT")
                return

            try:
                count = sock.send(REQUEST[offset:])

                if count <= 0:
                    print("SEND: connection closed")
                    return

                offset += count

            except OSError as error:
                print("SEND ERROR:", repr(error))
                return

        print("SENT:", offset, "bytes")

        # Wait for the HTTP response without blocking.
        poller.modify(
            sock,
            select.POLLIN | select.POLLERR | select.POLLHUP
        )

        buffer = bytearray(128)
        receive_deadline = time.monotonic() + TIMEOUT_SECONDS

        while time.monotonic() < receive_deadline:
            events = poller.poll(0)

            for descriptor, flags in events:
                if flags & (select.POLLERR | select.POLLHUP):
                    print("RECEIVE: error/hangup event")
                    return

                if flags & select.POLLIN:
                    try:
                        count = sock.recv_into(buffer)

                        if count == 0:
                            print("RECEIVE: connection closed")
                            return

                        print(
                            "RESPONSE:",
                            bytes(buffer[:count])
                        )
                        print("HTTP exchange completed")
                        return

                    except OSError as error:
                        print("RECV ERROR:", repr(error))
                        return

            time.sleep(POLL_INTERVAL_SECONDS)

        print("RECEIVE TIMEOUT")

    finally:
        if registered:
            try:
                poller.unregister(sock)
            except Exception:
                pass

        sock.close()
        print("Socket closed")
        print("Diagnostic complete")


test_tcp_poll()
