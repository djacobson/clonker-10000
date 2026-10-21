# test_tcp_blocking.py
#
# CLONKER 10000 - Blocking TCP Timeout Diagnostics
#
# Investigates whether CircuitPython socket timeouts
# reliably bound outbound TCP connection attempts.
#
# Run from the CircuitPython REPL:
#
# exec(open("/tests/test_tcp_blocking.py").read())
#
# Standalone diagnostic. Does not modify Clonker firmware.

import time
import wifi
import socketpool


# --------------------------------------------------
# Test configuration
# --------------------------------------------------

TARGETS = [
    ("Reachable Roku", "192.168.50.28", 8060),
    ("Unreachable LAN address", "192.168.50.100", 8060),
]

TIMEOUTS = [
    0.05,
    0.10,
    0.25,
    0.50,
    1.00,
]

# Allow a short recovery interval between attempts.
RECOVERY_SECONDS = 0.25

# Guard against unexpected long-running connections.
# This is diagnostic only; it cannot interrupt a
# blocking socket operation.
WARNING_SECONDS = 2.0


# --------------------------------------------------
# Helpers
# --------------------------------------------------

def elapsed_since(start):
    return time.monotonic() - start


def print_error(label, error):
    print(label + ":", repr(error))
    if isinstance(error, OSError):
        print(label + " errno:", error.args[0] if error.args else None)


def test_connection(pool, name, host, port, timeout):
    print()
    print("=" * 50)
    print("TEST:", name)
    print("TARGET:", "{}:{}".format(host, port))
    print("TIMEOUT:", timeout)

    sock = None
    connected = False
    started = time.monotonic()

    try:
        sock = pool.socket(
            pool.AF_INET,
            pool.SOCK_STREAM
        )

        try:
            sock.settimeout(timeout)
            print("SETTIMEOUT: accepted")
        except Exception as error:
            print_error("SETTIMEOUT ERROR", error)
            print("Skipping connection: timeout not configured")
            return

        connect_started = time.monotonic()

        try:
            sock.connect((host, port))
            connected = True
            print("CONNECT: success")
        except Exception as error:
            print_error("CONNECT ERROR", error)

        connect_elapsed = elapsed_since(connect_started)
        print("CONNECT ELAPSED:", connect_elapsed)

        # Only send when connect() explicitly succeeds.
        # This avoids treating an in-progress connection
        # as an established TCP connection.
        if connected:
            request = (
                "GET /query/device-info HTTP/1.1\r\n"
                "Host: {}\r\n"
                "Connection: close\r\n"
                "\r\n"
            ).format(host).encode("ascii")

            send_started = time.monotonic()

            try:
                count = sock.send(request)
                print("SEND BYTES:", count)
                print("REQUEST LENGTH:", len(request))
            except Exception as error:
                print_error("SEND ERROR", error)

            print("SEND ELAPSED:", elapsed_since(send_started))

    except Exception as error:
        print_error("SOCKET ERROR", error)

    finally:
        if sock is not None:
            close_started = time.monotonic()

            try:
                sock.close()
                print("SOCKET CLOSED")
            except Exception as error:
                print_error("CLOSE ERROR", error)

            print("CLOSE ELAPSED:", elapsed_since(close_started))

        total = elapsed_since(started)
        print("TOTAL ELAPSED:", total)

        if total > WARNING_SECONDS:
            print("WARNING: Test exceeded", WARNING_SECONDS, "seconds")

        print("RESULT:", "CONNECTED" if connected else "NOT CONNECTED")


# --------------------------------------------------
# Main diagnostic
# --------------------------------------------------

print()
print("CLONKER BLOCKING TCP DIAGNOSTICS")
print("Wi-Fi connected:", wifi.radio.connected)

if not wifi.radio.connected:
    print("ABORT: Wi-Fi is not connected")
else:
    pool = socketpool.SocketPool(wifi.radio)

    for name, host, port in TARGETS:
        for timeout in TIMEOUTS:
            test_connection(pool, name, host, port, timeout)
            time.sleep(RECOVERY_SECONDS)

    print()
    print("Diagnostics complete")
