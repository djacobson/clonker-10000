# The Clonker 10000
# tests/test_config_activation.py
#
# Chapter 12 -- Configuration activation regression
#
# Requires filesystem write access.
# Uses isolated scratch files and simulated session cleanup.
# No equipment commands are transmitted.

import os
import gc

from clonker import device_config as cfg
from clonker.devices import device_adapters as adapters

TEST_DIR = "/config_activation_test"
TEST_FILE = TEST_DIR + "/device_config.json"
BACKUP = TEST_FILE + ".bak"
OLDER = BACKUP + ".old"
TEMP = TEST_FILE + ".tmp"

HTTP = adapters.GENERIC_HTTP
TCP = adapters.DENON_TCP
TAP = adapters.ROKU_BUTTON_TAP
HOLD = adapters.ROKU_BUTTON_HOLD

passed = 0
failed = 0

close_calls = 0
close_should_fail = False


def check(name, condition):
    global passed, failed

    if condition:
        passed += 1
        print("PASS:", name)
    else:
        failed += 1
        print("FAIL:", name)
        raise AssertionError(name)


def reject(name, operation, error_type=ValueError):
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


def write_config(path, config):
    with open(path, "wb") as file:
        file.write(cfg.to_json(config).encode("utf-8"))
        file.flush()


def read_config(path):
    with open(path, "rb") as file:
        return cfg.from_json(file.read())


def simulated_close():
    """Record session retirement without network activity."""
    global close_calls

    close_calls += 1

    if close_should_fail:
        raise OSError("Simulated adapter cleanup failure")


def simulated_persistence_failure(path, contents):
    """Reject persistence before modifying any files."""
    raise OSError("Simulated persistence failure")


def http(path="", method="POST"):
    return {
        "kind": "http",
        "method": method,
        "path": path,
    }


def make_config(name, specialized=True):
    devices = {
        "device-1": {
            "type": "generic-http",
            "endpoint": "",
        },
        "device-2": {
            "type": "denon" if specialized else "generic-http",
            "endpoint": "192.168.1.20:8080",
        },
        "device-3": {
            "type": "roku" if specialized else "generic-http",
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

    actions["volume-up"] = {
        "target": "device-2",
        "command": http(
            "/goform/formiPhoneAppDirect.xml?MVUP",
            "GET"
        ),
    }

    actions["nav-up"]["command"] = http("/keypress/Up")
    actions["home"]["command"] = http("/keypress/Home")

    return cfg.validate_config({
        "version": 5,
        "rooms": {
            "room-2": {
                "name": name,
                "devices": devices,
                "actions": actions,
                "custom_actions": [],
            },
        },
    })


def cleanup():
    for path in (TEST_FILE, BACKUP, OLDER, TEMP):
        if exists(path):
            os.remove(path)

    os.rmdir(TEST_DIR)


def test_activation():
    global close_should_fail

    a = make_config("Generation A", True)
    b = make_config("Generation B", False)
    c = make_config("Generation C", True)

    # -------------------------------------------------
    # Initial configuration load
    # -------------------------------------------------

    write_config(TEST_FILE, a)

    check("Initial load", cfg.load(TEST_FILE) == a)
    check("Initial load retires sessions", close_calls == 1)

    check(
        "Initial Denon cache",
        adapters.lookup("room-2", "volume-up") == TCP
    )

    check(
        "Initial Roku tap cache",
        adapters.lookup("room-2", "nav-up") == TAP
    )

    check(
        "Initial Roku hold cache",
        adapters.lookup_hold("room-2", "nav-up") == HOLD
    )

    check(
        "Initial specialized cache size",
        len(adapters.snapshot()) == 3
    )

    original_cache = adapters.snapshot()
    rev_a = cfg.revision()

    # -------------------------------------------------
    # Cache preparation must not activate anything
    # -------------------------------------------------

    prepared = adapters.prepare_cache(b)

    check("Generic cache prepared", len(prepared) == 0)

    check(
        "Preparation preserves active cache",
        adapters.snapshot() == original_cache
    )

    check(
        "Preparation preserves active config",
        cfg.current() == a
    )

    check(
        "Preparation does not retire sessions",
        close_calls == 1
    )

    # -------------------------------------------------
    # Unchanged and rejected saves
    # -------------------------------------------------

    check("Unchanged save", cfg.save(a, rev_a) is False)

    check(
        "Unchanged save preserves sessions",
        close_calls == 1
    )

    check(
        "Unchanged save preserves cache",
        adapters.snapshot() == original_cache
    )

    reject(
        "Reject stale revision",
        lambda: cfg.save(b, "00000000")
    )

    check(
        "Rejected save preserves sessions",
        close_calls == 1
    )

    check(
        "Rejected save preserves cache",
        adapters.snapshot() == original_cache
    )

    check(
        "Rejected save preserves active config",
        cfg.current() == a
    )

    check(
        "Rejected save preserves primary",
        read_config(TEST_FILE) == a
    )

    # -------------------------------------------------
    # Simulated persistence failure
    # -------------------------------------------------

    original_replace = cfg._replace_with_backup

    try:
        cfg._replace_with_backup = simulated_persistence_failure

        reject(
            "Persistence failure propagated",
            lambda: cfg.save(b, rev_a),
            OSError
        )

    finally:
        cfg._replace_with_backup = original_replace

    check(
        "Failed persistence preserves sessions",
        close_calls == 1
    )

    check(
        "Failed persistence preserves cache",
        adapters.snapshot() == original_cache
    )

    check(
        "Failed persistence preserves active config",
        cfg.current() == a
    )

    check(
        "Failed persistence preserves revision",
        cfg.revision() == rev_a
    )

    check(
        "Failed persistence preserves primary",
        read_config(TEST_FILE) == a
    )

    check(
        "Failed persistence creates no backup",
        not exists(BACKUP)
    )

    # -------------------------------------------------
    # Successful changed save
    # -------------------------------------------------

    check("Changed save succeeds", cfg.save(b, rev_a) is True)

    check(
        "Changed save retires sessions once",
        close_calls == 2
    )

    check("Changed save activates B", cfg.current() == b)
    check("Changed save persists B", read_config(TEST_FILE) == b)
    check("Changed save backs up A", read_config(BACKUP) == a)

    check(
        "Changed save replaces cache",
        len(adapters.snapshot()) == 0
    )

    check(
        "Denon specialization removed",
        adapters.lookup("room-2", "volume-up") == HTTP
    )

    check(
        "Roku tap specialization removed",
        adapters.lookup("room-2", "nav-up") == HTTP
    )

    check(
        "Roku hold specialization removed",
        adapters.lookup_hold("room-2", "nav-up") == HTTP
    )

    # -------------------------------------------------
    # Session cleanup failure after persistence
    # -------------------------------------------------

    close_should_fail = True

    try:
        check(
            "Cleanup failure does not reject save",
            cfg.save(c, cfg.revision()) is True
        )

    finally:
        close_should_fail = False

    check(
        "Cleanup was attempted",
        close_calls == 3
    )

    check(
        "Cleanup failure still activates C",
        cfg.current() == c
    )

    check(
        "Cleanup failure preserves persisted C",
        read_config(TEST_FILE) == c
    )

    check(
        "Cleanup failure publishes Denon cache",
        adapters.lookup("room-2", "volume-up") == TCP
    )

    check(
        "Cleanup failure publishes Roku tap cache",
        adapters.lookup("room-2", "nav-up") == TAP
    )

    check(
        "Cleanup failure publishes Roku hold cache",
        adapters.lookup_hold("room-2", "nav-up") == HOLD
    )

    check(
        "Backup rotation preserved B",
        read_config(BACKUP) == b
    )

    check(
        "Older backup preserved A",
        read_config(OLDER) == a
    )

    # -------------------------------------------------
    # Backup load must activate the backup's cache
    # -------------------------------------------------

    damaged = b"{invalid-json"

    with open(TEST_FILE, "wb") as file:
        file.write(damaged)
        file.flush()

    check(
        "Damaged primary falls back to B",
        cfg.load(TEST_FILE) == b
    )

    check(
        "Backup load retires sessions once",
        close_calls == 4
    )

    check(
        "Backup load activates B",
        cfg.current() == b
    )

    check(
        "Backup load replaces specialized cache",
        len(adapters.snapshot()) == 0
    )

    with open(TEST_FILE, "rb") as file:
        actual = file.read()

    check(
        "Backup load does not repair primary",
        actual == damaged
    )

    # -------------------------------------------------
    # Explicit recovery alone must not activate
    # -------------------------------------------------

    os.remove(TEST_FILE)

    check(
        "Explicit recovery succeeds",
        cfg._recover_missing_file(TEST_FILE) is True
    )

    check(
        "Recovery alone does not retire sessions",
        close_calls == 4
    )

    check(
        "Recovery alone preserves cache",
        len(adapters.snapshot()) == 0
    )

    check(
        "Recovered primary contains B",
        read_config(TEST_FILE) == b
    )

    check(
        "Recovered primary reloads",
        cfg.load(TEST_FILE) == b
    )

    check(
        "Explicit reload retires sessions",
        close_calls == 5
    )


def run():
    global passed, failed
    global close_calls, close_should_fail

    passed = 0
    failed = 0
    close_calls = 0
    close_should_fail = False

    gc.collect()
    heap_before = gc.mem_free()

    print()
    print("=== CONFIG ACTIVATION REGRESSION ===")
    print("Scratch directory:", TEST_DIR)
    print()

    if exists(TEST_DIR):
        raise RuntimeError(
            "Scratch directory already exists; inspect first"
        )

    previous_current = cfg._current
    previous_path = cfg._current_path
    previous_map = adapters._adapter_map
    previous_close = adapters.close

    os.mkdir(TEST_DIR)

    completed = False

    try:
        adapters.close = simulated_close

        test_activation()
        completed = True

    finally:
        adapters.close = previous_close
        adapters._adapter_map = previous_map

        cfg._current = previous_current
        cfg._current_path = previous_path

        if completed and failed == 0:
            cleanup()
            print("Scratch files removed")
        else:
            print("Scratch files retained for inspection")

    gc.collect()

    print()
    print("=== RESULTS ===")
    print("Passed:", passed)
    print("Failed:", failed)
    print("Simulated session retirements:", close_calls)
    print("Free heap before:", heap_before)
    print("Free heap after:", gc.mem_free())

    if completed and failed == 0:
        print("CONFIG ACTIVATION REGRESSION: PASS")
    else:
        print("CONFIG ACTIVATION REGRESSION: FAIL")


run()
