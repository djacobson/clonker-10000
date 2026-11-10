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

from clonker.system import logger
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

_initialized = False
_buttons = []

_volume_encoder = None
_action_encoder = None
_action_index = 0

# Physical button name -> room selected when pressed.
_hold_rooms = {}


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
        return True
    except Exception as exc:
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
    """Queue a hold using the room and endpoint from press."""
    if event == "pressed":
        room_id = selectors.selected_room()

        if not device_config.has_room(room_id):
            logger.info(
                "PHYSICAL HOLD NO-OP: {} / {} "
                "(room unavailable)".format(room_id, action_id)
            )
            return False

        if button_name in _hold_rooms:
            return False

        measure = PHYSICAL_PERF_ENABLED and PERF_HOLD
        started = _perf.start() if measure else None

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
            actions.dispatch_hold(
                room_id, action_id, event,
                endpoint, command, adapter
            )
        except Exception as exc:
            logger.warning(
                "PHYSICAL hold dispatch failed: {}".format(exc)
            )
            return False
        finally:
            if measure:
                _perf.stop("physical.hold", started)

        _hold_rooms[button_name] = (
            room_id, endpoint, command, adapter
        )
        return True

    if event == "released":
        original = _hold_rooms.pop(button_name, None)

        if original is None:
            return False

        room_id, endpoint, command, adapter = original

        measure = PHYSICAL_PERF_ENABLED and PERF_HOLD
        started = _perf.start() if measure else None

        try:
            actions.dispatch_hold(
                room_id, action_id, event,
                endpoint, command, adapter
            )
            return True
        except Exception as exc:
            logger.warning(
                "PHYSICAL hold release failed: {}".format(exc)
            )
            return False
        finally:
            if measure:
                _perf.stop("physical.hold", started)

    return False


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

        button = Button(name, pin_number)

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

    if measure_scan:
        scan_ns += _perf.start() - started

    if room_id is not None:
        if measure_events:
            event_seen = True

        if PHYSICAL_EVENT_LOGGING:
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
                elif button.name == "HOME":
                    oled.show_text("HOME :)")
                elif button.name == "BACK":
                    oled.show_text("BACK :(")
                elif button.name == "SELECT":
                    oled.show_text(button.name)

    # Volume encoder.
    if _volume_encoder is not None:
        if measure_scan:
            started = _perf.start()

        step = _volume_encoder.poll()

        if measure_scan:
            scan_ns += _perf.start() - started

        if step:
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

        if step:
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
