# The Clonker 10000
# firmware/tests/test_tcp_reconnect.py
#
# Chapter 3, Phase B - TCP Connection State Diagnostics
#
# Hardware: Raspberry Pi Pico 2 W
# Runtime: CircuitPython 10.3.1
#
# Experimental only. Run manually from the REPL.
#
# Question:
# Can a second connect() call on the SAME nonblocking
# socket reveal whether TCP connection setup completed?
#
# Do not use repeated connect() in production until
# its behavior has been established.

import time
import wifi
import socketpool


ROKU_HOST = "192.168.50.28"
ROKU_PORT = 8060

UNREACHABLE_HOST = "192.168.50.100"
UNREACHABLE_PORT = 8060

DELAYS = (0.0, 0.01, 0.05, 0.25, 0.50)


def attempt_connect(sock, host, port, label):
    start = time.monotonic()

    try:
        result = sock.connect((host, port))
        print(label, "SUCCESS:", repr(result))

    except OSError as error:
        print(label, "ERROR:", repr(error))
        print(label, "ERRNO:", error.errno)

    except Exception as error:
        print(label, "EXCEPTION:", repr(error))

    print(
        label,
        "ELAPSED:",
        time.monotonic() - start
    )


def test_endpoint(label, host, port, delay):
    print()
    print("=" * 45)
    print("TEST:", label)
    print("TARGET: {}:{}".format(host, port))
    print("DELAY:", delay)

    pool = socketpool.SocketPool(wifi.radio)
    sock = pool.socket(pool.AF_INET, pool.SOCK_STREAM)
    sock.settimeout(0)

    try:
        attempt_connect(
            sock,
            host,
            port,
            "FIRST CONNECT"
        )

        time.sleep(delay)

        attempt_connect(
            sock,
            host,
            port,
            "SECOND CONNECT"
        )

    finally:
        close_start = time.monotonic()

        try:
            sock.close()
            print("SOCKET CLOSED")

        except Exception as error:
            print("CLOSE ERROR:", repr(error))

        print(
            "CLOSE ELAPSED:",
            time.monotonic() - close_start
        )


def main():
    print()
    print("CLONKER TCP RECONNECT DIAGNOSTICS")
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
