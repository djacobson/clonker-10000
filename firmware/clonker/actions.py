# The Clonker 10000
# clonker/actions.py -- The Dumb Queue
#
# Chapter 6 -- Device adapter integration
#
# Clonker Designed by David Jacobson

"""Shared action dispatcher and cooperative task queue.

One poll executes at most one eligible command.
Future-dated tasks never prevent immediate tasks from running.

Fundamental actions remain single-command tasks.
Custom actions execute ordered steps using one queue entry.

Commands resolve against CURRENT configuration at execution time.
Adapter selections are cached when configuration becomes active.

Commands execute through the device adapter router.
The queue preserves ordering when an adapter is not ready.

Configuration saves clear pending work through the web service.

An execution failure discards all remaining tasks.
No automatic retries.

Power and mute use independent, volatile ON/OFF command histories.
"""

import time

from clonker.system import logger
from clonker import device_adapters
from clonker import device_config_v2 as device_config


QUEUE_CAPACITY = 128

# Entries contain room, action, kind, step, and due time.
# Custom tasks advance through their steps without blocking.
_queue = []

_last_result = None
_last_error = None
_peak_depth = 0

# Key: (room_id, action_id)
# Value: next direction ("on" or "off").
# Missing entries default to ON.
_toggle_next = {}


def dispatch(room_id, action_id, delay_seconds=0):
    """Validate and enqueue a fundamental or custom action."""
    global _peak_depth

    if room_id not in device_config.ROOM_IDS:
        raise ValueError("Unknown room")

    if delay_seconds < 0:
        raise ValueError("Negative action delay")

    if len(_queue) >= QUEUE_CAPACITY:
        logger.warning("DUMB QUEUE: Full; action rejected")
        raise ValueError("Action queue full")

    # Resolve and validate before admitting any task.
    if action_id in device_config.ACTION_IDS:
        kind = "fundamental"
        room, action = device_config.action_details(
            room_id, action_id
        )

        target = action["target"]
        endpoint = device_config.resolve_endpoint(
            room, target
        )

        is_toggle = action_id in (
            "mute-toggle", "power-toggle"
        )

        paths = (
            (action["on_path"], action["off_path"])
            if is_toggle else (action["path"],)
        )

        configured = bool(endpoint and any(paths))

    else:
        kind = "custom"

        try:
            room, action = device_config.custom_action_details(
                room_id, action_id
            )
        except KeyError:
            raise ValueError("Unknown custom action")

        # All steps are validated by the configuration engine.
        configured = all(
            device_config.resolve_endpoint(
                room, step["target"]
            )
            for step in action["steps"]
        )

    due = (
        0 if delay_seconds == 0
        else time.monotonic() + delay_seconds
    )

    _queue.append({
        "room": room_id,
        "action": action_id,
        "kind": kind,
        "step": 0,
        "due": due,
    })

    if len(_queue) > _peak_depth:
        _peak_depth = len(_queue)

    message = "QUEUED: {} / {} (depth {})".format(
        room["name"], action_id, len(_queue)
    )

    logger.info(message)

    return {
        "ok": True,
        "status": "queued",
        "room": room_id,
        "room_name": room["name"],
        "action": action_id,
        "configured": configured,
        "queue_depth": len(_queue),
        "message": message,
    }


def dispatch_hold(room_id, action_id, event, destination=None, command=None):
    """Queue a physical held-button press or release."""
    global _peak_depth

    if room_id not in device_config.ROOM_IDS:
        raise ValueError("Unknown room")

    if action_id not in ("skip-back", "skip-forward"):
        raise ValueError("Unsupported held-button action")

    if event not in ("pressed", "released"):
        raise ValueError("Invalid held-button event")

    if len(_queue) >= QUEUE_CAPACITY:
        logger.warning("DUMB QUEUE: Full; hold rejected")
        raise ValueError("Action queue full")

    room, action = device_config.action_details(
        room_id, action_id
    )

    if destination is None:
        endpoint = device_config.resolve_endpoint(
            room, action["target"]
        )
    else:
        endpoint = destination

    if command is None:
        command = (
            action["target"],
            action["method"],
            action["path"],
        )

    target, method, path = command

    # Preserve the destination at press/release time.
    # Later configuration changes must not redirect a keyup.
    _queue.append({
        "room": room_id,
        "action": action_id,
        "kind": "hold",
        "event": event,
        "endpoint": endpoint,
        "target": target,
        "method": method,
        "path": path,
        "due": 0,
    })

    _peak_depth = max(_peak_depth, len(_queue))

    logger.info(
        "QUEUED HOLD: {} / {} {} (depth {})".format(
            room["name"],
            action_id,
            event.upper(),
            len(_queue),
        )
    )

    return True


def poll():
    """Execute at most one eligible command."""
    global _last_result, _last_error

    if not _queue:
        return False

    now = time.monotonic()
    selected = None

    for index, task in enumerate(_queue):
        if task["due"] == 0 or now >= task["due"]:
            selected = index
            break

    if selected is None:
        return False

    # Leave the selected task queued until we know whether
    # its command can execute. This prevents pacing delays
    # from allowing later commands to overtake it.
    task = _queue[selected]

    room_id = task["room"]
    action_id = task["action"]
    kind = task["kind"]

    try:
        if kind == "custom":
            room, action = device_config.custom_action_details(
                room_id, action_id
            )

            step_index = task["step"]
            steps = action["steps"]

            if step_index >= len(steps):
                raise ValueError("Custom step no longer exists")

            command = steps[step_index]

            target = command["target"]
            method = command["method"]
            path = command["path"]

            endpoint = device_config.resolve_endpoint(
                room, target
            )

            # Unlike fundamental actions, a missing custom
            # destination is an execution failure.
            if not endpoint:
                raise ValueError(
                    "Custom destination is unconfigured"
                )

            # Custom actions always use generic HTTP.
            adapter = device_adapters.GENERIC_HTTP

        elif kind == "hold":
            room = device_config.current()["rooms"][room_id]
            target = task["target"]
            endpoint = task["endpoint"]
            method = task["method"]
            path = task["path"]
            event = task["event"]

            adapter = device_adapters.ROKU_BUTTON

        else:
            room, action = device_config.action_details(
                room_id, action_id
            )

            target = action["target"]
            method = action["method"]

            endpoint = device_config.resolve_endpoint(
                room, target
            )

            # Toggle direction tracking.
            if action_id in ("mute-toggle", "power-toggle"):
                toggle_key = (room_id, action_id)
                toggle_direction = _toggle_next.get(
                    toggle_key, "on"
                )
                path = action[
                    "on_path" if toggle_direction == "on"
                    else "off_path"
                ]
            else:
                path = action["path"]

            # Fundamental actions retain blank-command no-ops.
            if not endpoint or not path:
                _queue.pop(selected)

                message = "NO-OP: {} / {} (unconfigured)".format(
                    room["name"], action_id
                )

                logger.info(message)
                _last_result = message
                _last_error = None
                return True

            adapter = device_adapters.lookup(
                room_id, action_id
            )

        # Adapter readiness preserves queue ordering.
        # An ineligible command stays queued.
        if not device_adapters.ready(adapter):
            return False

        logger.info(
            "EXECUTING: {} / {} -> {} {} {} [{}]".format(
                room["name"],
                action_id,
                target,
                method,
                path,
                adapter,
            )
        )

        if kind == "hold":
            result = device_adapters.execute_hold(
                endpoint, method, path, event
            )
        else:
            result = device_adapters.execute(
                adapter, endpoint, method, path
            )

        if not result["accepted"]:
            return False

        message = (
            "EXECUTED: {} / {} -> {} ({} ms)"
        ).format(
            room["name"],
            action_id,
            result["detail"],
            result["total_ms"],
        )

        # Command transmission completed successfully.
        # TCP success means bytes were sent, not that the
        # receiver explicitly acknowledged execution.
        _queue.pop(selected)

        logger.info(message)
        _last_result = message
        _last_error = None

        if kind == "fundamental" and action_id in (
            "mute-toggle", "power-toggle"
        ):
            _toggle_next[toggle_key] = (
                "off" if toggle_direction == "on" else "on"
            )

            logger.info(
                "TOGGLE: {} / {} completed {}; next {}".format(
                    room["name"],
                    action_id,
                    toggle_direction.upper(),
                    _toggle_next[toggle_key].upper(),
                )
            )

        if kind == "custom":
            next_index = task["step"] + 1

            if next_index < len(steps):
                # Start the wait AFTER the command completes.
                wait_seconds = (
                    command["wait_after_ms"] / 1000.0
                )

                task["step"] = next_index
                task["due"] = (
                    0 if wait_seconds == 0
                    else time.monotonic() + wait_seconds
                )

                # Return to the queue so other eligible
                # commands can run during the wait.
                _queue.append(task)

                logger.info(
                    "CUSTOM: {} / {} next step {} "
                    "after {} ms".format(
                        room["name"],
                        action_id,
                        next_index + 1,
                        command["wait_after_ms"],
                    )
                )

            else:
                logger.info(
                    "CUSTOM COMPLETE: {} / {}".format(
                        room["name"], action_id
                    )
                )

        return True

    except Exception as error:
        # The selected task remains in the queue until
        # successful completion. Remove it before counting
        # and discarding the remaining pending tasks.
        if selected < len(_queue) and _queue[selected] is task:
            _queue.pop(selected)

        discarded = len(_queue)
        _queue.clear()

        # A failed command cancels the remaining queue.
        # Release any active held controls as well.
        try:
            device_adapters.cancel_active()
        except Exception as cleanup_error:
            logger.warning(
                "ADAPTER: Failure cleanup failed: {}".format(
                    repr(cleanup_error)
                )
            )

        _last_error = "{} / {}: {}".format(
            room_id, action_id, repr(error)
        )

        _last_result = (
            "FAILED; {} pending tasks discarded"
        ).format(discarded)

        logger.warning(
            "DUMB QUEUE: {}".format(_last_error)
        )
        logger.warning(
            "DUMB QUEUE: {}".format(_last_result)
        )

        return True


def clear(reason="Manual reset", reset_toggles=False):
    """Discard pending tasks and release active held controls."""
    discarded = len(_queue)
    _queue.clear()

    try:
        device_adapters.cancel_active()
    except Exception as error:
        logger.warning(
            "ADAPTER: Cancel cleanup failed: {}".format(repr(error))
        )

    if reset_toggles:
        _toggle_next.clear()
        logger.info("TOGGLE: All direction histories reset")

    logger.info(
        "DUMB QUEUE: Cleared {} tasks ({})".format(
            discarded, reason
        )
    )

    return discarded


def status():
    """Return a small diagnostic snapshot."""
    return {
        "depth": len(_queue),
        "capacity": QUEUE_CAPACITY,
        "peak_depth": _peak_depth,
        "last_result": _last_result,
        "last_error": _last_error,
    }
