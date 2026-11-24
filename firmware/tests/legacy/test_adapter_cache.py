# The Clonker 10000
# tests/test_adapter_cache.py
#
# Chapter 6 -- Adapter cache tests
#
# Clonker Designed by David Jacobson

from clonker import device_adapters
from clonker import device_config_v2 as device_config


def run():
    print()
    print("THE CLONKER 10000")
    print("DEVICE ADAPTER CACHE TEST")
    print("--------------------------------")

    config = device_config.load()

    print()
    print("TEST 1: BUILD CACHE")

    count = device_adapters.rebuild(config)

    print("Specialized selections:", count)
    print("Cache:", device_adapters.snapshot())

    assert count == len(device_adapters.snapshot())
    print("PASS")

    print()
    print("TEST 2: VERIFY ACTIVE CONFIGURATION")

    for room_id, room in config["rooms"].items():
        for action_id in device_config.ACTION_IDS:

            action = room["actions"][action_id]

            if action_id in ("volume-up", "volume-down"):
                expected = device_adapters.resolve(
                    "fundamental",
                    action_id,
                    action["method"],
                    action["path"],
                )
            else:
                expected = device_adapters.GENERIC_HTTP

            actual = device_adapters.lookup(
                room_id, action_id
            )

            assert actual == expected, (
                room_id, action_id, expected, actual
            )

            print(
                room_id, action_id, "->", actual
            )

    print("PASS")

    print()
    print("TEST 3: UNKNOWN ACTION FALLBACK")

    assert device_adapters.lookup(
        "room-1", "unknown-action"
    ) == device_adapters.GENERIC_HTTP

    print("PASS")

    print()
    print("TEST 4: CACHE REBUILD REPLACES OLD ENTRIES")

    # A minimal synthetic configuration is sufficient
    # to exercise the cache builder.
    synthetic = {
        "rooms": {
            "test-room": {
                "actions": {
                    "volume-up": {
                        "method": "GET",
                        "path": (
                            "/goform/"
                            "formiPhoneAppDirect.xml?MVUP"
                        ),
                    },
                    "volume-down": {
                        "method": "POST",
                        "path": "/keypress/VolumeDown",
                    },
                },
            },
        },
    }

    device_adapters.rebuild(synthetic)

    assert device_adapters.lookup(
        "test-room", "volume-up"
    ) == device_adapters.DENON_TCP

    assert device_adapters.lookup(
        "test-room", "volume-down"
    ) == device_adapters.GENERIC_HTTP

    assert device_adapters.lookup(
        "room-1", "volume-up"
    ) == device_adapters.GENERIC_HTTP

    print("PASS")

    print()
    print("TEST 5: FAILED REBUILD PRESERVES CACHE")

    before = device_adapters.snapshot()

    try:
        device_adapters.rebuild({"rooms": None})
    except (TypeError, AttributeError):
        pass
    else:
        raise AssertionError(
            "Malformed configuration was accepted"
        )

    assert device_adapters.snapshot() == before

    print("PASS")

    print()
    print("TEST 6: RESTORE ACTIVE CONFIGURATION")

    device_adapters.rebuild(config)

    assert len(device_adapters.snapshot()) == count

    print("PASS")

    print()
    print("ALL ADAPTER CACHE TESTS PASSED")


run()
