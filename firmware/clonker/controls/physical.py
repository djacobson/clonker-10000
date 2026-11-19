# The Clonker 10000
# clonker/controls/physical.py
#
# Clonker Designed by David Jacobson
# GitHub: https://github.com/djacobson/clonker-10000

"""Physical control initialization, polling, and action routing.

Hardware modules detect events.
This module maps physical events to Clonker actions.

The CONFIG/RUN switch is managed separately in switches.py.
The room selector maintains its own selected-room state.
"""
import time
from clonker.controls import switches
from clonker.system import logger
from clonker.system import sleep_manager
from clonker.system import flight_recorder
from clonker import actions
from clonker import device_config_v2 as device_config
from clonker import device_adapters
from clonker.controls import pins
from clonker.controls import selectors
from clonker.controls.buttons import Button
from clonker.controls.encoders import Encoder
from clonker.display import oled

from clonker.system import perf as _perf

# Physical performance diagnostics.
# Enable only the measurements needed for an experiment.
PHYSICAL_PERF_ENABLED = False

PERF_SCAN = False
PERF_EVENTS = False
PERF_VOLUME = False
PERF_DISPATCH = False
PERF_HOLD = False

# Threshold for correlated slow-poll diagnostics.
PHYSICAL_SLOW_NS = 20_000_000


class _DisabledPerf:
    """No-op instrumentation for disabled diagnostics."""

    @staticmethod
    def register(*args, **kwargs):
        pass

    @staticmethod
    def start():
        return 0

    @staticmethod
    def stop(*args):
        return 0

    @staticmethod
    def record(*args):
        pass


# Existing dispatch helpers can continue using this interface.
perf = _perf if PHYSICAL_PERF_ENABLED else _DisabledPerf()

perf.register("physical.dispatch")
perf.register("physical.hold")
perf.register("physical.scan")
perf.register("physical.events")
perf.register("physical.events.active")
perf.register("physical.events.idle")
perf.register("physical.volume")
perf.register("physical.non_scan")
perf.register("physical.slow.scan")
perf.register("physical.slow.non_scan")


# Diagnostic: suppress physical input event INFO logging.
# Warnings, errors, and action/network logs remain enabled.
PHYSICAL_EVENT_LOGGING = False

# Physical button names -> fundamental action IDs.
# Only assigned GPIO buttons are initialized.
#
# FUTURE DESIGN NOTE -- optional panel orientation:
#
# Keep physical button identity separate from logical actions.
# A future configuration setting could select between predefined
# BUTTON_ACTIONS_NORMAL and BUTTON_ACTIONS_ROTATED dictionaries.
#
# For a 180-degree panel rotation, the alternate mapping would
# exchange these logical actions:
#
#   nav-up       <-> nav-down
#   nav-left     <-> nav-right
#   skip-back    <-> skip-forward
#
# Other controls (Power, Home, Back, Select, Mute) can retain
# their original logical meanings regardless of orientation.
#
# The event loop should continue using:
#
#   action_id = BUTTON_ACTIONS.get(button.name)
#
# Selecting a different dictionary reference would require
# no changes to event processing or action dispatch.
#
# Future rotary encoder drivers should independently support
# an optional reverse=False parameter, applied to decoded
# rotation direction rather than raw quadrature signals.
#
# No orientation feature is currently implemented.
BUTTON_ACTIONS = {
    "POWER_TOGGLE": "power-toggle",
    "HOME": "home",
    "BACK": "back",
    "UP": "nav-up",
    "DOWN": "nav-down",
    "LEFT": "nav-left",
    "RIGHT": "nav-right",
    "SELECT": "select",
    "VOLUME_MUTE": "mute-toggle",
    "SKIP_BACK": "skip-back",
    "PLAY_PAUSE": "play-pause",
    "SKIP_FORWARD": "skip-forward",
}

# Physical buttons using queued keydown/keyup events.
HOLD_BUTTONS = (
    "UP",
    "DOWN",
    "LEFT",
    "RIGHT",
    "SKIP_BACK",
    "SKIP_FORWARD",
)

# Short presses use one keypress command.
# Longer presses use the existing keydown/keyup hold path.
TAP_HOLD_THRESHOLD_MS = 250
TAP_HOLD_THRESHOLD_NS = TAP_HOLD_THRESHOLD_MS * 1_000_000

_initialized = False

# Flight recorder diagnostics.
# Counters are updated without logging or filesystem I/O.
_button_events = 0
_button_presses = 0
_last_button = None
_dispatch_attempts = 0
_dispatch_accepted = 0
_dispatch_failed = 0
_dispatch_skipped = 0
_last_dispatch = None


def snapshot():
    """Return lightweight physical-control diagnostics."""
    return {
        "initialized": _initialized,
        "button_events": _button_events,
        "button_presses": _button_presses,
        "last_button": _last_button,
        "dispatch_attempts": _dispatch_attempts,
        "dispatch_accepted": _dispatch_accepted,
        "dispatch_failed": _dispatch_failed,
        "dispatch_skipped": _dispatch_skipped,
        "last_dispatch": _last_dispatch,
    }


def _record_dispatch(action_id, outcome):
    """Count a physical dispatch outcome without logging."""
    global _dispatch_attempts, _dispatch_accepted
    global _dispatch_failed, _dispatch_skipped
    global _last_dispatch

    if outcome == "skipped":
        _dispatch_skipped += 1
    else:
        _dispatch_attempts += 1
        if outcome == "accepted":
            _dispatch_accepted += 1
        else:
            _dispatch_failed += 1

    _last_dispatch = (action_id, outcome)


_buttons = []

_volume_encoder = None
_action_encoder = None
_action_index = 0

# Physical button name -> room selected when pressed.
_hold_rooms = {}

# Releases awaiting space in the Dumb Queue.
# A new press must not overtake its previous keyup.
_pending_releases = {}


# Secret reboot handshake.
# Physical CONFIG ON, then 2 -> 3 -> 2 -> 3 -> 2 -> 3.
# The first room-2 event must be an actual selector transition.
REBOOT_SEQUENCE = (
    "room-2", "room-3", "room-2",
    "room-3", "room-2", "room-3",
)
REBOOT_SEQUENCE_TIMEOUT_NS = 10_000_000_000

_reboot_sequence_index = 0
_reboot_sequence_started = 0


def _reboot_sequence_reset():
    """Cancel an incomplete reboot handshake."""
    global _reboot_sequence_index, _reboot_sequence_started

    _reboot_sequence_index = 0
    _reboot_sequence_started = 0


def _reboot_sequence_step(room_id):
    """Observe a debounced room change for the secret handshake."""
    global _reboot_sequence_index, _reboot_sequence_started

    now = time.monotonic_ns()

    if (
        _reboot_sequence_index
        and now - _reboot_sequence_started
        > REBOOT_SEQUENCE_TIMEOUT_NS
    ):
        _reboot_sequence_reset()

    expected = REBOOT_SEQUENCE[_reboot_sequence_index]

    if room_id != expected:
        _reboot_sequence_reset()
        return

    if _reboot_sequence_index == 0:
        _reboot_sequence_started = now

    _reboot_sequence_index += 1

    if _reboot_sequence_index < len(REBOOT_SEQUENCE):
        return

    _reboot_sequence_reset()

    logger.warning("SECRET REBOOT: Handshake accepted")
    oled.show_text("REBOOTING!")

    # Allow the OLED to refresh before resetting.
    oled.poll()
    time.sleep(1.0)

    # Best-effort persistent diagnostic snapshot.
    # Failure must never prevent the deliberate reboot.
    saved = flight_recorder.flush_now("manual_reboot")

    if not saved:
        logger.warning(
            "FLIGHT RECORDER: Reboot snapshot failed: {}".format(
                flight_recorder.persistence_status()["last_error"]
            )
        )

    import microcontroller
    microcontroller.reset()


# Secret sleep toggle handshake.
# Physical CONFIG ON, then 1 -> 2 -> 1 -> 2 -> 1 -> 2.
# The first room-1 event must be an actual selector transition.
SLEEP_SEQUENCE = (
    "room-1", "room-2", "room-1",
    "room-2", "room-1", "room-2",
)
SLEEP_SEQUENCE_TIMEOUT_NS = 10_000_000_000

_sleep_sequence_index = 0
_sleep_sequence_started = 0


def _sleep_sequence_reset():
    """Cancel an incomplete sleep-toggle handshake."""
    global _sleep_sequence_index, _sleep_sequence_started

    _sleep_sequence_index = 0
    _sleep_sequence_started = 0


def _sleep_sequence_step(room_id):
    """Observe a room change; return True on a completed handshake."""
    global _sleep_sequence_index, _sleep_sequence_started

    now = time.monotonic_ns()

    if (
        _sleep_sequence_index
        and now - _sleep_sequence_started
        > SLEEP_SEQUENCE_TIMEOUT_NS
    ):
        _sleep_sequence_reset()

    expected = SLEEP_SEQUENCE[_sleep_sequence_index]

    if room_id != expected:
        _sleep_sequence_reset()
        return False

    if _sleep_sequence_index == 0:
        _sleep_sequence_started = now

    _sleep_sequence_index += 1

    if _sleep_sequence_index < len(SLEEP_SEQUENCE):
        return False

    _sleep_sequence_reset()

    enabled = sleep_manager.toggle_enabled()
    logger.info("SECRET SLEEP: Handshake accepted")

    oled.show_text("SLEEP ON" if enabled else "SLEEP OFF")
    return True


def _custom_actions_for_room(room_id):
    """Return ordered Custom Actions without revalidation."""
    return device_config.custom_actions_for_room(room_id)


def _log_custom_selection(room_id):
    """Log the selected Custom Action without executing it."""
    custom_actions = _custom_actions_for_room(room_id)

    if not custom_actions:
        oled.show_text("No customs", reset_ack=True)
        logger.info(
            "CUSTOM SELECT: {} / No customs".format(room_id)
        )
        return

    selected = custom_actions[_action_index]
    oled.show_text(selected["name"], reset_ack=True)

    logger.info(
        "CUSTOM SELECT: {} / {} ({}/{})".format(
            room_id,
            selected["name"],
            _action_index + 1,
            len(custom_actions)
        )
    )


def _run_selected_custom():
    """Dispatch the selected room's Custom Action."""
    room_id = selectors.selected_room()
    custom_actions = _custom_actions_for_room(room_id)

    if not custom_actions:
        logger.info(
            "CUSTOM RUN NO-OP: {} / No customs".format(room_id)
        )
        return False

    selected = custom_actions[_action_index]

    logger.info(
        "CUSTOM RUN: {} / {}".format(
            room_id, selected["name"]
        )
    )

    if dispatch_selected(selected["id"]):
        oled.show_text(selected["name"])
        oled.acknowledge()
        return True

    return False


def dispatch_selected(action_id):
    """Dispatch an action to the currently selected room.

    Unconfigured rooms are harmless no-ops.
    All physical controls can reuse this helper.
    """
    room_id = selectors.selected_room()

    if not device_config.has_room(room_id):
        _record_dispatch(action_id, "skipped")
        logger.info(
            "PHYSICAL NO-OP: {} / {} (room unavailable)".format(
                room_id, action_id
            )
        )
        return False

    measure = PHYSICAL_PERF_ENABLED and PERF_DISPATCH
    started = _perf.start() if measure else None

    try:
        actions.dispatch(room_id, action_id)
        _record_dispatch(action_id, "accepted")
        return True
    except Exception as exc:
        _record_dispatch(action_id, "failed")
        logger.warning(
            "PHYSICAL dispatch failed: {} / {}: {}".format(
                room_id, action_id, exc
            )
        )
        return False
    finally:
        if measure:
            _perf.stop("physical.dispatch", started)


def dispatch_hold_button(button_name, action_id, event):
    """Classify a physical button gesture as a tap or hold."""
    if event == "pressed":
        # Preserve ordering if an earlier release is pending.
        if button_name in _pending_releases:
            retry_pending_releases()
            if button_name in _pending_releases:
                _record_dispatch(action_id, "skipped")
                return False

        room_id = selectors.selected_room()

        if not device_config.has_room(room_id):
            _record_dispatch(action_id, "skipped")
            return False

        if button_name in _hold_rooms:
            _record_dispatch(action_id, "skipped")
            return False

        try:
            room, action = device_config.action_details(
                room_id, action_id
            )
            endpoint = device_config.resolve_endpoint(
                room, action["target"]
            )
            command = (
                action["target"],
                action["method"],
                action["path"],
            )
            adapter = device_adapters.lookup_hold(
                room_id, action_id
            )

            if not endpoint or not action["path"]:
                _record_dispatch(action_id, "skipped")
                return False

            if adapter == device_adapters.GENERIC_HTTP:
                raise ValueError("No native hold adapter")

            _hold_rooms[button_name] = (
                room_id,
                action_id,
                endpoint,
                command,
                adapter,
                time.monotonic_ns(),
                False,
            )
            return True

        except Exception as exc:
            _record_dispatch(action_id, "failed")
            logger.warning(
                "PHYSICAL gesture press failed: {}".format(exc)
            )
            return False

    if event == "released":
        original = _hold_rooms.pop(button_name, None)
        if original is None:
            return False

        (
            room_id, saved_action_id, endpoint,
            command, adapter, pressed_ns, holding
        ) = original

        try:
            if holding:
                actions.dispatch_hold(
                    room_id, saved_action_id, "released",
                    endpoint, command, adapter
                )
            else:
                # A short gesture needs only one keypress.
                actions.dispatch(room_id, saved_action_id)

            _record_dispatch(saved_action_id, "accepted")
            return True

        except Exception as exc:
            if holding:
                # Retain the original destination for retry.
                _pending_releases[button_name] = (
                    room_id, saved_action_id,
                    endpoint, command, adapter
                )

            _record_dispatch(saved_action_id, "failed")
            logger.warning(
                "PHYSICAL gesture release failed: {}".format(exc)
            )
            return False

    return False


def retry_pending_releases():
    """Retry held-button releases that could not enter the queue."""
    for button_name, state in tuple(_pending_releases.items()):
        room_id, action_id, endpoint, command, adapter = state

        try:
            actions.dispatch_hold(
                room_id, action_id, "released",
                endpoint, command, adapter
            )
        except Exception:
            # Keep the release pending for the next poll.
            continue

        del _pending_releases[button_name]
        _record_dispatch(action_id, "accepted")


def poll_pending_holds():
    """Start holds that remain pressed beyond the threshold."""
    now = time.monotonic_ns()

    for button_name, state in tuple(_hold_rooms.items()):
        (
            room_id, action_id, endpoint,
            command, adapter, pressed_ns, holding
        ) = state

        if holding:
            continue

        if now - pressed_ns < TAP_HOLD_THRESHOLD_NS:
            continue

        try:
            actions.dispatch_hold(
                room_id, action_id, "pressed",
                endpoint, command, adapter
            )

            _hold_rooms[button_name] = (
                room_id, action_id, endpoint,
                command, adapter, pressed_ns, True
            )
            _record_dispatch(action_id, "accepted")

        except Exception as exc:
            _record_dispatch(action_id, "failed")
            logger.warning(
                "PHYSICAL hold start failed: {}".format(exc)
            )


def initialize():
    """Initialize assigned physical buttons and room selector."""
    global _initialized
    global _volume_encoder
    global _action_encoder

    if _initialized:
        return True

    definitions = (
        ("POWER_TOGGLE", pins.POWER_TOGGLE_PIN),
        ("HOME", pins.HOME_BUTTON_PIN),
        ("BACK", pins.BACK_BUTTON_PIN),
        ("UP", pins.UP_BUTTON_PIN),
        ("DOWN", pins.DOWN_BUTTON_PIN),
        ("LEFT", pins.LEFT_BUTTON_PIN),
        ("RIGHT", pins.RIGHT_BUTTON_PIN),
        ("SELECT", pins.SELECT_BUTTON_PIN),
        ("VOLUME_MUTE", pins.VOLUME_ENCODER_BUTTON_PIN),
        ("ACTION_RUN", pins.ACTION_ENCODER_BUTTON_PIN),
        ("SKIP_BACK", pins.SKIP_BACK_BUTTON_PIN),
        ("PLAY_PAUSE", pins.PLAY_PAUSE_BUTTON_PIN),
        ("SKIP_FORWARD", pins.SKIP_FORWARD_BUTTON_PIN),
    )

    for name, pin_number in definitions:
        if pin_number is None:
            continue

        button = Button(
            name,
            pin_number,
            release_debounce_seconds=(
                0.01 if name in HOLD_BUTTONS else None
            ),
        )

        try:
            button.initialize()
            _buttons.append(button)
            logger.info(
                "{} button initialized on GP{}".format(
                    name, pin_number
                )
            )
        except Exception as exc:
            logger.warning(
                "{} button unavailable: {}".format(name, exc)
            )

    try:
        if selectors.initialize():
            logger.info(
                "Room selector initialized; selected = {}".format(
                    selectors.selected_room()
                )
            )
        else:
            logger.warning("Room selector not assigned")
    except Exception as exc:
        logger.warning("Room selector unavailable: {}".format(exc))

    # Initialize the volume rotary encoder.
    if (
        pins.VOLUME_ENCODER_A_PIN is not None
        and pins.VOLUME_ENCODER_B_PIN is not None
    ):
        try:
            encoder = Encoder(
                "VOLUME",
                pins.VOLUME_ENCODER_A_PIN,
                pins.VOLUME_ENCODER_B_PIN,
            )
            encoder.initialize()
            _volume_encoder = encoder
            logger.info("Volume encoder initialized")
        except Exception as exc:
            logger.warning(
                "Volume encoder unavailable: {}".format(exc)
            )

    # Initialize the Custom Action rotary encoder.
    if (
        pins.ACTION_ENCODER_A_PIN is not None
        and pins.ACTION_ENCODER_B_PIN is not None
    ):
        try:
            encoder = Encoder(
                "ACTION",
                pins.ACTION_ENCODER_A_PIN,
                pins.ACTION_ENCODER_B_PIN,
            )
            encoder.initialize()
            _action_encoder = encoder
            logger.info("Action encoder initialized")
        except Exception as exc:
            logger.warning(
                "Action encoder unavailable: {}".format(exc)
            )

    _initialized = True
    return True


def poll():
    """Poll physical inputs and route button presses."""
    global _action_index
    global _button_events, _button_presses, _last_button

    if not _initialized:
        return

    measure_scan = PHYSICAL_PERF_ENABLED and PERF_SCAN
    measure_events = PHYSICAL_PERF_ENABLED and PERF_EVENTS
    measure_volume = PHYSICAL_PERF_ENABLED and PERF_VOLUME

    # Measure the full internal poll independently of scan timing.
    if measure_events:
        poll_started = _perf.start()
        event_seen = False

    if measure_scan:
        scan_ns = 0

    # Room selector.
    if measure_scan:
        started = _perf.start()

    room_id = selectors.poll()

    # Secret handshakes require the physical CONFIG switch.
    sleep_toggled = False

    if switches.config_source() != "PHYSICAL" or not switches.config_enabled():
        _reboot_sequence_reset()
        _sleep_sequence_reset()
    elif room_id is not None:
        _reboot_sequence_step(room_id)
        sleep_toggled = _sleep_sequence_step(room_id)

    if measure_scan:
        scan_ns += _perf.start() - started

    if room_id is not None and not sleep_manager.note_activity(
        "ROOM_SELECTOR",
        wake_eligible=False,
    ) and not sleep_toggled:
        if measure_events:
            event_seen = True

        logger.info("ROOM SELECTED: {}".format(room_id))

        _action_index = 0

        room_number = room_id[-1]

        if device_config.has_room(room_id):
            room_name = device_config.room(room_id)["name"]
            oled.show_text("ROOM " + room_number, room_name)
        else:
            oled.show_text("ROOM " + room_number, "UNASSIGNED")

    # Momentary buttons.
    for button in _buttons:
        if measure_scan:
            started = _perf.start()

        event = button.poll()

        if measure_scan:
            scan_ns += _perf.start() - started

        if event is None:
            continue

        _button_events += 1
        _last_button = button.name

        # Presses can wake Clonker, but the wake press
        # must not execute its normal action.
        if event == "pressed":
            _button_presses += 1
            if sleep_manager.note_activity(
                button.name,
                wake_eligible=True,
            ):
                continue

        # Ignore releases while asleep as well.
        elif sleep_manager.is_sleeping():
            continue

        if measure_events:
            event_seen = True

        if PHYSICAL_EVENT_LOGGING:
            logger.info(
                "{} {}".format(button.name, event.upper())
            )

        if button.name == "ACTION_RUN":
            if event == "pressed":
                _run_selected_custom()
            continue

        action_id = BUTTON_ACTIONS.get(button.name)

        if action_id is None:
            continue

        if button.name in HOLD_BUTTONS:
            dispatched = dispatch_hold_button(
                button.name, action_id, event
            )
            if dispatched and event == "pressed":
                messages = {
                    "UP": "^ UP",
                    "DOWN": "~ DOWN",
                    "LEFT": "< LEFT",
                    "RIGHT": "RIGHT >",
                    "SKIP_BACK": "< SKIP BK",
                    "SKIP_FORWARD": "SKIP FWD >",
                }
                oled.show_text(messages[button.name])
            continue

        if event == "pressed":
            dispatched = dispatch_selected(action_id)
            if dispatched:
                if button.name == "PLAY_PAUSE":
                    oled.show_text("PLAY/PAUSE")
                elif button.name == "POWER_TOGGLE":
                    oled.show_text("POW!")
                elif button.name in (
                    "HOME", "BACK", "SELECT"
                ):
                    oled.show_text(button.name)

    # Retry queued releases before promoting new holds.
    retry_pending_releases()

    # Promote sustained presses to holds without blocking polling.
    poll_pending_holds()

    # Volume encoder.
    if _volume_encoder is not None:
        if measure_scan:
            started = _perf.start()

        step = _volume_encoder.poll()

        if measure_scan:
            scan_ns += _perf.start() - started

        if step and not sleep_manager.note_activity(
            "VOLUME_ENCODER",
            wake_eligible=False,
        ):
            if measure_events:
                event_seen = True

            if measure_volume:
                started = _perf.start()

            action_id = (
                "volume-up" if step > 0 else "volume-down"
            )

            message = (
                "VOL UP +" if step > 0 else "- VOL DOWN"
            )

            if oled.is_showing_or_pending(message):
                oled.touch()
            else:
                oled.show_text(message)

            dispatch_selected(action_id)

            if measure_volume:
                _perf.stop("physical.volume", started)

    # Custom Action encoder.
    if _action_encoder is not None:
        if measure_scan:
            started = _perf.start()

        step = _action_encoder.poll()

        if measure_scan:
            scan_ns += _perf.start() - started

        if step and not sleep_manager.note_activity(
            "ACTION_ENCODER",
            wake_eligible=False,
        ):
            if measure_events:
                event_seen = True

            room_id = selectors.selected_room()
            custom_actions = _custom_actions_for_room(room_id)

            if custom_actions:
                _action_index = (
                    _action_index + step
                ) % len(custom_actions)
            else:
                _action_index = 0

            _log_custom_selection(room_id)

    # End timing before recording statistics.
    if measure_events:
        total_ns = _perf.start() - poll_started

    if measure_scan:
        _perf.record("physical.scan", scan_ns)

    if measure_events:
        # Always report the full internal polling duration.
        _perf.record("physical.events", total_ns)

        if event_seen:
            _perf.record(
                "physical.events.active", total_ns
            )
        else:
            _perf.record(
                "physical.events.idle", total_ns
            )

        if measure_scan:
            non_scan_ns = max(0, total_ns - scan_ns)

            _perf.record(
                "physical.non_scan", non_scan_ns
            )

            # Correlated scan and non-scan durations
            # for individual slow physical polls.
            if total_ns > PHYSICAL_SLOW_NS:
                _perf.record(
                    "physical.slow.scan", scan_ns
                )
                _perf.record(
                    "physical.slow.non_scan",
                    non_scan_ns
                )
