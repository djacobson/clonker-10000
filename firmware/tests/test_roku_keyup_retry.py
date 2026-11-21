# The Clonker 10000
# firmware/tests/test_roku_keyup_retry.py
#
# Isolated Roku physical-button release recovery test.
#
# No Roku HTTP requests are sent.
# No physical controls are modified.
# Run with the Clonker application stopped.

import time
from clonker.devices import roku


ENDPOINT = "192.168.50.28:8060"  # Simulated only
KEY = "Down"

_original_send = roku._send_button
_attempts = []
_fail_first_keyup = True


def fake_send(endpoint, operation, key):
    global _fail_first_keyup

    _attempts.append((endpoint, operation, key))
    print("SIMULATED: /{}/{}".format(operation, key))

    if operation == "keyup" and _fail_first_keyup:
        _fail_first_keyup = False
        raise OSError("Simulated keyup network failure")

    return 200


def check(condition, description):
    if not condition:
        raise AssertionError(description)
    print("PASS:", description)


print()
print("ROKU KEYUP RETRY TEST")
print("---------------------")

try:
    check(
        roku.button_held_key() is None,
        "No physical key held before test"
    )

    # Replace only the physical-button HTTP sender.
    roku._send_button = fake_send

    roku.button_down(ENDPOINT, KEY)
    check(
        roku.button_held_key() == KEY,
        "DOWN held state established"
    )

    try:
        roku.button_up(ENDPOINT, KEY)
        raise AssertionError("Expected keyup failure")
    except OSError as error:
        check(
            "Simulated keyup network failure" in str(error),
            "First keyup fails as intended"
        )

    check(
        roku.button_held_key() == KEY,
        "Held key retained after failure"
    )
    check(
        roku._button_release_pending,
        "Release marked pending"
    )

    before = len(_attempts)
    result = roku.button_poll()

    check(
        result is False and len(_attempts) == before,
        "No premature retry"
    )

    print("Waiting 550 ms for retry eligibility...")
    time.sleep(0.55)

    result = roku.button_poll()

    check(
        result is True,
        "Periodic poll retries keyup successfully"
    )
    check(
        roku.button_held_key() is None,
        "Held key cleared after successful release"
    )
    check(
        not roku._button_release_pending,
        "Pending-release flag cleared"
    )

    expected = ["keydown", "keyup", "keyup"]
    actual = [item[1] for item in _attempts]

    check(
        actual == expected,
        "Exactly one keydown and two keyup attempts"
    )

    print()
    print("RESULT: ALL TESTS PASSED")

finally:
    # Restore production sender even if a test fails.
    roku._send_button = _original_send
    roku._reset_button()
    print("Test cleanup complete.")
