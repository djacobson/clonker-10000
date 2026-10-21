# The Clonker 10000
# Chapter 3, Phase B1
# Blocking HTTP Reliability and Timeout Diagnostics
#
# Standalone test -- no production action queue changes.

import time

from clonker.net import http_transport


DENON = "192.168.50.40:8080"
ROKU = "192.168.50.28:8060"
UNREACHABLE = "192.168.50.100:8060"

DENON_UP = "/goform/formiPhoneAppDirect.xml?MVUP"
DENON_DOWN = "/goform/formiPhoneAppDirect.xml?MVDOWN"
ROKU_INFO = "/query/device-info"

# Two candidate socket timeouts.
TIMEOUTS = (1.0, 0.5)

# Allow a little breathing room between commands.
PAUSE_SECONDS = 0.2


def run_request(label, endpoint, method, path):
    print()
    print("TEST:", label)

    start = time.monotonic()

    try:
        result = http_transport.send(
            endpoint, method, path
        )

        elapsed = round(
            (time.monotonic() - start) * 1000, 1
        )

        print(
            "PASS: HTTP {} | {} ms".format(
                result["status"], elapsed
            )
        )

        return True, elapsed

    except Exception as error:
        elapsed = round(
            (time.monotonic() - start) * 1000, 1
        )

        print(
            "ERROR: {} | {} ms".format(
                repr(error), elapsed
            )
        )

        return False, elapsed


print()
print("=" * 56)
print("CLONKER HTTP TRANSPORT RELIABILITY TEST")
print("=" * 56)

original_timeout = http_transport.SOCKET_TIMEOUT
original_total = http_transport.TOTAL_TIMEOUT

try:
    for timeout in TIMEOUTS:
        print()
        print("#" * 56)
        print("SOCKET TIMEOUT:", timeout, "seconds")
        print("#" * 56)

        http_transport.SOCKET_TIMEOUT = timeout

        # Keep the total deadline above the socket timeout.
        http_transport.TOTAL_TIMEOUT = 2.5

        results = []

        # Five read-only Roku GET requests.
        for i in range(5):
            ok, ms = run_request(
                "Roku GET {}".format(i + 1),
                ROKU,
                "GET",
                ROKU_INFO
            )
            results.append(("Roku GET", ok, ms))
            time.sleep(PAUSE_SECONDS)

        # Three Denon volume-up/down pairs.
        # Each pair should approximately restore the
        # original volume.
        for i in range(3):
            ok, ms = run_request(
                "Denon UP {}".format(i + 1),
                DENON,
                "GET",
                DENON_UP
            )
            results.append(("Denon UP", ok, ms))
            time.sleep(PAUSE_SECONDS)

            ok, ms = run_request(
                "Denon DOWN {}".format(i + 1),
                DENON,
                "GET",
                DENON_DOWN
            )
            results.append(("Denon DOWN", ok, ms))
            time.sleep(PAUSE_SECONDS)

        # Deliberately unreachable device.
        # Failure here is expected.
        ok, ms = run_request(
            "Unreachable device",
            UNREACHABLE,
            "GET",
            ROKU_INFO
        )
        results.append(("Unreachable", ok, ms))

        # Recovery test: immediately contact Roku again.
        ok, ms = run_request(
            "Roku recovery after failure",
            ROKU,
            "GET",
            ROKU_INFO
        )
        results.append(("Recovery", ok, ms))

        print()
        print("RESULTS FOR TIMEOUT:", timeout)

        successful = [
            ms for name, ok, ms in results
            if ok and name != "Unreachable"
        ]

        unexpected_failures = [
            name for name, ok, ms in results
            if not ok and name != "Unreachable"
        ]

        if successful:
            print(
                "Successful request range: {} - {} ms".format(
                    min(successful),
                    max(successful)
                )
            )

        print(
            "Unexpected failures:",
            len(unexpected_failures)
        )

        print(
            "Unreachable correctly failed:",
            not results[-2][1]
        )

        print(
            "Recovery succeeded:",
            results[-1][1]
        )

finally:
    http_transport.SOCKET_TIMEOUT = original_timeout
    http_transport.TOTAL_TIMEOUT = original_total

print()
print("=" * 56)
print("B1 RELIABILITY TEST COMPLETE")
print("=" * 56)
