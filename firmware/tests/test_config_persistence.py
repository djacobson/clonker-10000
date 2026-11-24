# The Clonker 10000
# tests/test_config_persistence.py
#
# Chapter 12 -- Config v5 persistence regression
#
# Uses an isolated scratch directory.
# Never reads or writes the live Clonker configuration.
# Requires CircuitPython filesystem write access.

import os
import gc

from clonker import device_config as cfg

TEST_DIR = "/config_v5_test"
TEST_FILE = TEST_DIR + "/device_config.json"
BACKUP = TEST_FILE + ".bak"
OLDER = BACKUP + ".old"
TEMP = TEST_FILE + ".tmp"

passed = 0
failed = 0


def check(name, condition):
    global passed, failed

    if condition:
        passed += 1
        print("PASS:", name)
    else:
        failed += 1
        print("FAIL:", name)
        raise AssertionError(name)


def expect_error(name, operation, error_type=ValueError):
    try:
        operation()
    except error_type:
        check(name, True)
    else:
        check(name, False)


def exists(path):
    try:
        os.stat(path)
        return True
    except OSError as error:
        if error.errno == 2:
            return False
        raise


def read_file(path):
    with open(path, "rb") as file:
        return file.read()


def write_file(path, contents):
    with open(path, "wb") as file:
        file.write(contents)
        file.flush()


def read_config(path):
    return cfg.from_json(read_file(path))


def write_config(path, config):
    write_file(path, cfg.to_json(config).encode("utf-8"))


def http(path="", method="POST"):
    return {
        "kind": "http",
        "method": method,
        "path": path,
    }


def make_config(name):
    devices = {
        "device-1": {
            "type": "generic-http",
            "endpoint": "",
        },
        "device-2": {
            "type": "denon",
            "endpoint": "192.168.1.20:8080",
        },
        "device-3": {
            "type": "roku",
            "endpoint": "192.168.1.30:8060",
        },
    }

    actions = {}

    for action_id in cfg.ACTION_IDS:
        if action_id in ("power-toggle", "mute-toggle"):
            actions[action_id] = {
                "target": "device-2",
                "on_command": http("", "GET"),
                "off_command": http("", "GET"),
            }
        else:
            actions[action_id] = {
                "target": "device-3",
                "command": http(),
            }

    actions["home"]["command"] = http("/keypress/Home")

    custom_actions = [
        {
            "id": "custom-action-1",
            "name": "Test Action",
            "steps": [
                {
                    "target": "device-3",
                    "command": http("/keypress/Home"),
                    "wait_after_ms": 0,
                },
            ],
        },
    ]

    return {
        "version": 5,
        "rooms": {
            "room-2": {
                "name": name,
                "devices": devices,
                "actions": actions,
                "custom_actions": custom_actions,
            },
        },
    }


def cleanup():
    for path in (TEST_FILE, BACKUP, OLDER, TEMP):
        if exists(path):
            os.remove(path)

    os.rmdir(TEST_DIR)


def run():
    gc.collect()
    heap_before = gc.mem_free()

    print()
    print("=== CONFIG V5 PERSISTENCE ===")
    print("Scratch directory:", TEST_DIR)
    print()

    # Refuse to overwrite an existing scratch directory.
    # A previous interrupted test may have left evidence.
    if exists(TEST_DIR):
        raise RuntimeError(
            "Scratch directory already exists; inspect first"
        )

    # Preserve any existing state of the isolated v5 module.
    previous_current = cfg._current
    previous_path = cfg._current_path

    os.mkdir(TEST_DIR)

    try:
        test_persistence()

    finally:
        cfg._current = previous_current
        cfg._current_path = previous_path

        # Preserve scratch files if a test failed.
        if failed == 0 and passed == EXPECTED_PASSES:
            cleanup()
            print("Scratch files removed")
        else:
            print("Scratch files retained for inspection")

    gc.collect()

    print()
    print("=== RESULTS ===")
    print("Passed:", passed)
    print("Failed:", failed)
    print("Free heap before:", heap_before)
    print("Free heap after:", gc.mem_free())

    if failed == 0 and passed == EXPECTED_PASSES:
        print("CONFIG V5 PERSISTENCE: PASS")
    else:
        print("CONFIG V5 PERSISTENCE: FAIL")


def test_persistence():
    # Four distinguishable configuration generations.
    a = make_config("Generation A")
    b = make_config("Generation B")
    c = make_config("Generation C")
    d = make_config("Generation D")

    # -------------------------------------------------
    # Initial load and active configuration accessors
    # -------------------------------------------------

    write_config(TEST_FILE, a)

    check("Initial load", cfg.load(TEST_FILE) == a)
    check("Active configuration", cfg.current() == a)

    rev_a = cfg.revision()

    check("Initial revision", rev_a == cfg.revision(a))

    check("Configured room exists", cfg.has_room("room-2"))
    check("Absent room", not cfg.has_room("room-1"))

    room, action = cfg.action_details("room-2", "home")

    check(
        "Fundamental action accessor",
        action["command"]["path"] == "/keypress/Home"
    )

    check(
        "Custom Action list accessor",
        len(cfg.custom_actions_for_room("room-2")) == 1
    )

    room, custom = cfg.custom_action_details(
        "room-2", "custom-action-1"
    )

    check(
        "Custom Action detail accessor",
        custom["name"] == "Test Action"
    )

    copied = cfg.current()
    copied["rooms"]["room-2"]["name"] = "Modified Copy"

    check("Current returns independent copy", cfg.current() == a)

    # -------------------------------------------------
    # Unchanged save and revision protection
    # -------------------------------------------------

    check("Unchanged save", cfg.save(a, rev_a) is False)

    check(
        "Unchanged save creates no backups",
        not exists(BACKUP) and not exists(OLDER)
    )

    expect_error(
        "Reject stale revision",
        lambda: cfg.save(b, "00000000")
    )

    check("Stale revision preserves primary", read_config(TEST_FILE) == a)

    expect_error(
        "Reject alternate save path",
        lambda: cfg.save(b, rev_a, TEMP)
    )

    check("Alternate save creates no file", not exists(TEMP))

    # -------------------------------------------------
    # Successful saves and backup rotation
    # -------------------------------------------------

    check("Save generation B", cfg.save(b, rev_a) is True)

    check("Primary contains B", read_config(TEST_FILE) == b)
    check("Backup contains A", read_config(BACKUP) == a)
    check("Active configuration B", cfg.current() == b)

    rev_b = cfg.revision()

    check("Revision changed", rev_b != rev_a)

    expect_error(
        "Reject previously valid revision",
        lambda: cfg.save(c, rev_a)
    )

    check("Save generation C", cfg.save(c, rev_b) is True)

    check("Primary contains C", read_config(TEST_FILE) == c)
    check("Backup contains B", read_config(BACKUP) == b)
    check("Older backup contains A", read_config(OLDER) == a)

    check(
        "Save generation D",
        cfg.save(d, cfg.revision()) is True
    )

    check("Primary contains D", read_config(TEST_FILE) == d)
    check("Backup contains C", read_config(BACKUP) == c)
    check("Older backup contains B", read_config(OLDER) == b)
    check("No temporary file remains", not exists(TEMP))

    # -------------------------------------------------
    # External modification detection
    # -------------------------------------------------

    rev_d = cfg.revision()

    write_config(TEST_FILE, a)

    expect_error(
        "Reject externally modified primary",
        lambda: cfg.save(b, rev_d)
    )

    check("External primary preserved", read_config(TEST_FILE) == a)
    check("Active configuration still D", cfg.current() == d)
    check("Backup preserved", read_config(BACKUP) == c)
    check("Older backup preserved", read_config(OLDER) == b)

    # Restore the expected primary for the next test.
    write_config(TEST_FILE, d)

    # -------------------------------------------------
    # Damaged primary and backup fallback
    # -------------------------------------------------

    damaged = b"{invalid-json"

    write_file(TEST_FILE, damaged)

    check("Load falls back to backup C", cfg.load(TEST_FILE) == c)

    check(
        "Fallback does not repair primary",
        read_file(TEST_FILE) == damaged
    )

    expect_error(
        "Reject save with damaged primary",
        lambda: cfg.save(d, cfg.revision())
    )

    check("Damaged primary preserved", read_file(TEST_FILE) == damaged)
    check("Backup C preserved", read_config(BACKUP) == c)
    check("Older backup B preserved", read_config(OLDER) == b)

    check(
        "Recovery refuses existing primary",
        cfg._recover_missing_file(TEST_FILE) is False
    )

    # -------------------------------------------------
    # Explicit recovery of missing primary
    # -------------------------------------------------

    os.remove(TEST_FILE)

    check("Missing primary falls back to C", cfg.load(TEST_FILE) == c)

    check(
        "Fallback does not recreate primary",
        not exists(TEST_FILE)
    )

    check(
        "Explicit recovery succeeds",
        cfg._recover_missing_file(TEST_FILE) is True
    )

    check("Recovered primary contains C", read_config(TEST_FILE) == c)
    check("Recovered backup consumed", not exists(BACKUP))
    check("Older backup remains B", read_config(OLDER) == b)

    # -------------------------------------------------
    # Older backup fallback and recovery
    # -------------------------------------------------

    write_file(TEST_FILE, damaged)
    write_file(BACKUP, damaged)

    check("Load falls back to older B", cfg.load(TEST_FILE) == b)

    check(
        "Older fallback preserves damaged files",
        read_file(TEST_FILE) == damaged
        and read_file(BACKUP) == damaged
    )

    os.remove(TEST_FILE)

    check(
        "Recovery skips invalid backup",
        cfg._recover_missing_file(TEST_FILE) is True
    )

    check("Recovered primary contains B", read_config(TEST_FILE) == b)
    check("Older backup consumed", not exists(OLDER))
    check("Recovered configuration reloads", cfg.load(TEST_FILE) == b)

    # -------------------------------------------------
    # No valid configuration available
    # -------------------------------------------------

    os.remove(TEST_FILE)
    os.remove(BACKUP)

    expect_error(
        "Reject load with no valid generations",
        lambda: cfg.load(TEST_FILE),
        RuntimeError
    )

    check(
        "Recovery reports no valid backup",
        cfg._recover_missing_file(TEST_FILE) is False
    )


EXPECTED_PASSES = 57

run()
