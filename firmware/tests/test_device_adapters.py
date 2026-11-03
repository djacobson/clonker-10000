# The Clonker 10000
# tests/test_device_adapters.py
#
# Chapter 6 -- Device adapter resolver tests
#
# Clonker Designed by David Jacobson

from clonker import device_adapters


UP = "/goform/formiPhoneAppDirect.xml?MVUP"
DOWN = "/goform/formiPhoneAppDirect.xml?MVDOWN"


def check(label, kind, action_id, method, path, expected):
    actual = device_adapters.resolve(
        kind, action_id, method, path
    )

    print(label)
    print("  Expected:", expected)
    print("  Actual:  ", actual)

    assert actual == expected
    print("  PASS")


def run():
    print()
    print("THE CLONKER 10000")
    print("DEVICE ADAPTER RESOLVER TEST")
    print("--------------------------------")

    check(
        "TEST 1: Denon volume up",
        "fundamental", "volume-up", "GET", UP,
        device_adapters.DENON_TCP
    )

    check(
        "TEST 2: Denon volume down",
        "fundamental", "volume-down", "GET", DOWN,
        device_adapters.DENON_TCP
    )

    check(
        "TEST 3: Roku volume command",
        "fundamental", "volume-up", "POST",
        "/keypress/VolumeUp",
        device_adapters.GENERIC_HTTP
    )

    check(
        "TEST 4: Unknown Denon command",
        "fundamental", "volume-up", "GET",
        "/goform/formiPhoneAppDirect.xml?MV50",
        device_adapters.GENERIC_HTTP
    )

    check(
        "TEST 5: Denon custom action",
        "custom", "movie", "GET", UP,
        device_adapters.GENERIC_HTTP
    )

    check(
        "TEST 6: Wrong HTTP method",
        "fundamental", "volume-up", "POST", UP,
        device_adapters.GENERIC_HTTP
    )

    check(
        "TEST 7: Unrelated fundamental action",
        "fundamental", "power-toggle", "GET", UP,
        device_adapters.GENERIC_HTTP
    )

    print()
    print("TEST 8: Native command translation")

    assert device_adapters.denon_command(UP) == "MVUP"
    assert device_adapters.denon_command(DOWN) == "MVDOWN"

    print("  PASS")

    print()
    print("TEST 9: Unknown command rejection")

    try:
        device_adapters.denon_command("/unknown")
    except ValueError:
        print("  PASS")
    else:
        raise AssertionError("Unknown command was accepted")

    print()
    print("ALL RESOLVER TESTS PASSED")


run()
