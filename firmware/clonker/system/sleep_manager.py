# The Clonker 10000
# clonker/system/sleep_manager.py
#
# Clonker Designed by David Jacobson
#
# Developer-only inactivity and sleep management.
#
# CircuitPython 10.3.1 on Pico 2 W lacks the alarm module.
# RP2350 alarm support appeared in CircuitPython 11.x alpha
# builds. Revisit hardware deep sleep when 11.x is stable.
#
# Initial implementation: DRY RUN ONLY.
# No Wi-Fi changes, OLED shutdown, or microcontroller reset.

import time

from clonker.system import logger


# Developer settings
SLEEP_ENABLED = False
SLEEP_DRY_RUN = True
SLEEP_IDLE_TIMEOUT_S = 600

_NS_PER_SECOND = 1_000_000_000

_AWAKE = "AWAKE"
_ASLEEP = "ASLEEP"

_state = _AWAKE
_last_activity_ns = time.monotonic_ns()


def initialize():
    """Initialize inactivity tracking."""
    global _state, _last_activity_ns

    _state = _AWAKE
    _last_activity_ns = time.monotonic_ns()

    if SLEEP_ENABLED:
        logger.info(
            "SLEEP: enabled, dry_run={}, timeout={}s".format(
                SLEEP_DRY_RUN, SLEEP_IDLE_TIMEOUT_S
            )
        )


def is_sleeping():
    """Return the current simulated sleep state."""
    return SLEEP_ENABLED and _state == _ASLEEP


def note_activity(name, wake_eligible=False):
    """Record physical activity and evaluate simulated wake."""
    global _state, _last_activity_ns

    if not SLEEP_ENABLED:
        return

    if _state == _ASLEEP:
        # While asleep, only eligible button presses can wake us.
        # Encoder rotation must not alter the inactivity timer.
        if not wake_eligible:
            return

        logger.info(
            "SLEEP: wake requested by {} (DRY RUN)".format(
                name
            )
        )
        logger.info(
            "SLEEP: would reboot; no action taken"
        )

        # Simulate waking and restart the inactivity countdown.
        _state = _AWAKE
        _last_activity_ns = time.monotonic_ns()
        return

    # Normal physical activity while awake resets inactivity.
    _last_activity_ns = time.monotonic_ns()


def tick(config_mode=False, actions_pending=False):
    """Evaluate inactivity without changing hardware state."""
    global _state, _last_activity_ns

    if not SLEEP_ENABLED:
        return

    if config_mode:
        # Config Mode must remain fully operational.
        # Restart inactivity timing when leaving Config Mode.
        _last_activity_ns = time.monotonic_ns()
        if _state == _ASLEEP:
            logger.info("SLEEP: CONFIG mode canceled simulation")
            _state = _AWAKE
        return

    if _state == _ASLEEP:
        return

    if actions_pending:
        # Do not enter sleep while queued work remains.
        _last_activity_ns = time.monotonic_ns()
        return

    elapsed_ns = time.monotonic_ns() - _last_activity_ns
    timeout_ns = SLEEP_IDLE_TIMEOUT_S * _NS_PER_SECOND

    if elapsed_ns >= timeout_ns:
        _state = _ASLEEP
        logger.info(
            "SLEEP: inactivity timeout reached ({}s)".format(
                SLEEP_IDLE_TIMEOUT_S
            )
        )
        logger.info(
            "SLEEP: would disable Wi-Fi and OLED (DRY RUN)"
        )
