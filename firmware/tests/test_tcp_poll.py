
# The Clonker 10000
# firmware/tests/test_tcp_poll.py
#
# Chapter 3, Phase B - TCP Connection Diagnostics
#
# Hardware: Raspberry Pi Pico 2 W
# Runtime: CircuitPython 10.3.1
#
# Investigates:
#   1. Nonblocking TCP connection establishment
#   2. select.poll() readiness behavior
#   3. getsockopt(SO_ERROR) availability
#   4. Unreachable-device timeout behavior
#
# Diagnostic only. Not production firmware.
# Run manually from the REPL.

import time
import wifi
import socketpool
import select


# Known working Sunroom Roku.
ROKU_HOST = "192.168.50.28"
ROKU_PORT = 8060

# Use an address confirmed unused on your LAN.
# This example assumes the 192.168.50.0/24 subnet.
# Change it if .254 is assigned to a real device.
UNREACHABLE_HOST = "192.168.50.100"
UNREACHABLE_PORT = 8060

TIMEOUT_SECONDS = 2.0
POLL_INTERVAL_SECONDS = 0.01

# Avoid repeated output from a permanently signaled POLLOUT.
REPORT_INTERVAL_SECONDS = 0.25


def check_getsockopt(sock):
    print()
    print("SOCKET CAPABILITY CHECK")

    supported = hasattr(sock, "getsockopt")
    print("getsockopt available:", supported)

    if not supported:
        print("SO_ERROR inspection unavailable")
        return

    try:
        value = sock.getsockopt(
            socketpool.SOL_SOCKET,
            socketpool.SO_ERROR
        )
        print("SO_ERROR:", value)

    except Exception as error:
        print("getsockopt error:", repr(error))


def test_endpoint(label, host, port):
    print()
    print("=" * 45)
    print("TEST:", label)
    print("TARGET: {}:{}".format(host, port))

    pool = socketpool.SocketPool(wifi.radio)
    sock = pool.socket(pool.AF_INET, pool.SOCK_STREAM)
    sock.settimeout(0)

    poller = select.poll()
    registered = False

    try:
        start = time.monotonic()

        try:
            sock.connect((host, port))
            print("CONNECT: immediate success")

        except OSError as error:
            print("CONNECT:", repr(error))
            print("ERRNO:", error.errno)

            if error.errno != 119:
                print("Unexpected connect error")
                return

        check_getsockopt(sock)

        poller.register(
            sock,
            select.POLLOUT | select.POLLERR | select.POLLHUP
        )
        registered = True

        deadline = start + TIMEOUT_SECONDS
        next_report = start

        last_flags = None
        samples = 0

        print()
        print("Polling for", TIMEOUT_SECONDS, "seconds")

        while time.monotonic() < deadline:
            events = poller.poll(0)
            samples += 1

            flags = 0

            for descriptor, event_flags in events:
                flags |= event_flags

            now = time.monotonic()

            if flags != last_flags or now >= next_report:
                print(
                    "t={:.3f}s flags={}".format(
                        now - start,
                        flags
                    )
                )

                print(
                    "  OUT={} ERR={} HUP={}".format(
                        bool(flags & select.POLLOUT),
                        bool(flags & select.POLLERR),
                        bool(flags & select.POLLHUP)
                    )
                )

                last_flags = flags
                next_report = now + REPORT_INTERVAL_SECONDS

            if flags & (select.POLLERR | select.POLLHUP):
                print("Socket error/hangup reported")
                break

            # Do not send on the unreachable endpoint.
            # This test observes connection readiness only.
            time.sleep(POLL_INTERVAL_SECONDS)

        print()
        print("TOTAL SAMPLES:", samples)
        print(
            "TOTAL ELAPSED:",
            time.monotonic() - start
        )

        check_getsockopt(sock)

    finally:
        if registered:
            try:
                poller.unregister(sock)
            except Exception:
                pass

        close_start = time.monotonic()
        sock.close()

        print(
            "SOCKET CLOSE ELAPSED:",
            time.monotonic() - close_start
        )


def main():
    print()
    print("CLONKER TCP CONNECTION DIAGNOSTICS")
    print("Wi-Fi connected:", wifi.radio.connected)

    test_endpoint(
        "Reachable Roku",
        ROKU_HOST,
        ROKU_PORT
    )

    test_endpoint(
        "Unreachable LAN address",
        UNREACHABLE_HOST,
        UNREACHABLE_PORT
    )

    print()
    print("Diagnostics complete")


main()
