# The Clonker 10000
# clonker/system/sleep_manager.py
#
# Clonker Designed by David Jacobson
#
# Developer-configurable inactivity and software sleep management.
#
# CircuitPython 10.3.1 on Raspberry Pi Pico 2 W does not provide
# the alarm module needed for our planned hardware sleep/wake.
# RP2350 alarm support has appeared in CircuitPython 11.x alpha.
# Revisit light/deep sleep when a suitable stable release arrives.
#
# Current approach: application-level software sleep.
# The CPU continues polling physical inputs while the OLED and
# Wi-Fi radio are shut down to reduce current consumption.
#
# Why reboot on wake?
# Experiments with disabling and re-enabling the Wi-Fi radio did
# not restore stable network operation as expected. Reconnection
# also took approximately four seconds. A full microcontroller
# reset provides a simpler, more predictable initialization path.
#
# Experiments with wifi.radio.power_management did not produce
# useful power savings; observed Wi-Fi behavior instead appeared
# less favorable. We therefore do not rely on that API for sleep.
#
# Dry-run mode simulates sleep/wake without hardware changes.
# Real wake consumes the triggering input and reboots the Pico.

import time

from clonker.system import logger


# Developer settings
SLEEP_ENABLED = True
SLEEP_DRY_RUN = False
SLEEP_IDLE_TIMEOUT_S = 600  # 600 = 10 mins
SLEEP_FAREWELL_S = 1.5

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


def toggle_enabled():
    """Toggle sleep availability until the next reboot."""
    global SLEEP_ENABLED, _state, _last_activity_ns

    SLEEP_ENABLED = not SLEEP_ENABLED
    _state = _AWAKE
    _last_activity_ns = time.monotonic_ns()

    logger.info(
        "SLEEP: manually {}".format(
            "enabled" if SLEEP_ENABLED else "disabled"
        )
    )

    return SLEEP_ENABLED


def is_sleeping():
    """Return whether software sleep is currently active."""
    return SLEEP_ENABLED and _state == _ASLEEP


def note_activity(name, wake_eligible=False):
    """Record activity; return True if sleep consumed the event."""
    global _state, _last_activity_ns

    if not SLEEP_ENABLED:
        return False

    if _state == _ASLEEP:
        if wake_eligible:
            logger.info(
                "SLEEP: wake requested by {}".format(name)
            )

            if SLEEP_DRY_RUN:
                logger.info(
                    "SLEEP: would reboot; no action taken (DRY RUN)"
                )
                _state = _AWAKE
                _last_activity_ns = time.monotonic_ns()
            else:
                logger.info("SLEEP: rebooting")
                import microcontroller
                microcontroller.reset()

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
    """Evaluate inactivity and enter software sleep when eligible."""
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
        logger.info(
            "SLEEP: inactivity timeout reached ({}s)".format(
                SLEEP_IDLE_TIMEOUT_S
            )
        )

        if SLEEP_DRY_RUN:
            _state = _ASLEEP
            logger.info(
                "SLEEP: would disable Wi-Fi and OLED (DRY RUN)"
            )
            return

        try:
            import wifi
            from clonker.display import oled

            # Brief farewell, even if the OLED is already dark.
            logger.info("SLEEP: displaying bedtime message")
            oled.show_text("Going Zzzz!")
            oled.poll()

            # Allow time for the queued display refresh.
            # The OLED driver rate-limits its own updates.
            deadline = time.monotonic() + SLEEP_FAREWELL_S
            while time.monotonic() < deadline:
                oled.poll()
                time.sleep(0.05)

            logger.info("SLEEP: closing OLED")
            oled.close()

            logger.info("SLEEP: disabling Wi-Fi")
            wifi.radio.enabled = False

        except Exception as exc:
            logger.warning(
                "SLEEP: shutdown failed: {}".format(exc)
            )
            logger.warning("SLEEP: rebooting to recover")
            import microcontroller
            microcontroller.reset()
            return

        _state = _ASLEEP
        logger.info("SLEEP: entered software sleep")
