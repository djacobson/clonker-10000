# The Clonker 10000
# tests/test_adapter_save.py
#
# Chapter 6 -- Configuration save / adapter cache test
#
# Clonker Designed by David Jacobson

import os
import traceback

from clonker import device_config_v2 as config
from clonker import device_adapters


TEST_FILE = "/clonker/test_adapter_save.json"
ROOM_ID = "room-2"
ACTION_ID = "volume-up"

DENON_PATH = (
    "/goform/formiPhoneAppDirect.xml?MVUP"
)
GENERIC_PATH = "/keypress/VolumeUp"


def remove_if_exists(path):
    try:
        os.remove(path)
    except OSError as error:
        if error.errno != 2:
            raise


def check_adapter(expected):
    actual = device_adapters.lookup(
        ROOM_ID, ACTION_ID
    )
    print("Expected:", expected)
    print("Actual:  ", actual)
    assert actual == expected
    print("PASS")


def run():
    print()
    print("THE CLONKER 10000")
    print("ADAPTER SAVE SYNCHRONIZATION TEST")
    print("--------------------------------")

    # This test must never save to the production file.
    assert TEST_FILE != config.CONFIG_FILE

    paths = (
        TEST_FILE,
        TEST_FILE + ".bak",
        TEST_FILE + ".bak.old",
        TEST_FILE + ".tmp",
    )

    try:
        print()
        print("TEST 1: CREATE DISPOSABLE CONFIG")

        original = config.load()
        test_config = config.current()

        # Make sure our test starts with a recognized
        # Denon volume command, without changing production.
        test_config["rooms"][ROOM_ID]["actions"][
            ACTION_ID
        ]["method"] = "GET"

        test_config["rooms"][ROOM_ID]["actions"][
            ACTION_ID
        ]["path"] = DENON_PATH

        for path in paths:
            remove_if_exists(path)

        with open(TEST_FILE, "w") as file:
            file.write(config.to_json(test_config))

        config.load(TEST_FILE)

        check_adapter(device_adapters.DENON_TCP)

        print()
        print("TEST 2: SAVE GENERIC HTTP COMMAND")

        changed = config.current()
        changed["rooms"][ROOM_ID]["actions"][
            ACTION_ID
        ]["method"] = "POST"

        changed["rooms"][ROOM_ID]["actions"][
            ACTION_ID
        ]["path"] = GENERIC_PATH

        old_revision = config.revision()

        assert config.save(
            changed, old_revision, path=TEST_FILE
        ) is True

        check_adapter(device_adapters.GENERIC_HTTP)

        print()
        print("TEST 3: REJECT STALE REVISION")

        before = device_adapters.snapshot()

        rejected = config.current()
        rejected["rooms"][ROOM_ID]["actions"][
            ACTION_ID
        ]["method"] = "GET"

        rejected["rooms"][ROOM_ID]["actions"][
            ACTION_ID
        ]["path"] = DENON_PATH

        try:
            config.save(
                rejected,
                old_revision,
                path=TEST_FILE,
            )
        except ValueError:
            print("Stale revision correctly rejected")
        else:
            raise AssertionError(
                "Stale revision was accepted"
            )

        assert device_adapters.snapshot() == before
        print("PASS: Cache unchanged")

        print()
        print("TEST 4: SAVE DENON COMMAND AGAIN")

        assert config.save(
            rejected,
            config.revision(),
            path=TEST_FILE,
        ) is True

        check_adapter(device_adapters.DENON_TCP)

        print()
        print("TEST 5: VERIFY DISK CONFIG")

        config.load(TEST_FILE)
        check_adapter(device_adapters.DENON_TCP)

        print()
        print("ALL ADAPTER SAVE TESTS PASSED")

    except Exception as error:
        print()
        print("FAIL:", repr(error))
        traceback.print_exception(
            type(error), error, error.__traceback__
        )

    finally:
        print()
        print("RESTORING PRODUCTION CONFIGURATION")

        # Restore normal active configuration first.
        # This also rebuilds the production adapter cache.
        try:
            config.load(config.CONFIG_FILE)
            print("Production configuration restored")
            print("Adapter cache:", device_adapters.snapshot())
        except Exception as error:
            print("RESTORE FAILED:", repr(error))

        # Remove only our disposable test files.
        for path in paths:
            try:
                remove_if_exists(path)
            except OSError as error:
                print("Cleanup warning:", repr(error))

        print("Disposable files cleaned up")


run()
