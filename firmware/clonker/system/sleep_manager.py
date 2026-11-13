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
_last_config_mode = None


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
    """Record activity; return True if sleep consumed the event."""
    global _state, _last_activity_ns

    if not SLEEP_ENABLED:
        return False

    if _state == _ASLEEP:
        if wake_eligible:
            logger.info(
                "SLEEP: wake requested by {} (DRY RUN)".format(
                    name
                )
            )
            logger.info("SLEEP: would reboot; no action taken")
            _state = _AWAKE
            _last_activity_ns = time.monotonic_ns()

        # Do not dispatch an input received during sleep.
        return True

    # Any physical activity while awake resets inactivity.
    _last_activity_ns = time.monotonic_ns()
    return False


def note_config_switch(config_mode):
    """Detect CONFIG/RUN transitions in either direction."""
    global _last_config_mode

    config_mode = bool(config_mode)

    if _last_config_mode is None:
        # Establish the initial switch position.
        _last_config_mode = config_mode
        return

    if config_mode == _last_config_mode:
        return

    _last_config_mode = config_mode

    # Both switch directions count as physical activity.
    # During sleep, either direction requests a wake.
    note_activity(
        "CONFIG_SWITCH",
        wake_eligible=True,
    )


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
