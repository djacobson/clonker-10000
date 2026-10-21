# The Clonker 10000
# clonker/actions.py -- The Dumb Queue
#
# Chapter 3, Phase B2 -- Real HTTP execution
#
# Clonker Designed by David Jacobson

"""Shared action dispatcher and cooperative task queue.

One poll executes at most one eligible task. Future-dated tasks
never prevent immediate tasks from running.

Commands resolve against the CURRENT configuration at execution time.

An execution failure discards all remaining tasks, but does not
disable the queue. No automatic retries.

Toggle state tracking is deferred. Toggle actions are not
transmitted until ON/OFF selection is implemented.
"""

import time

from clonker.system import logger
from clonker.net import http_transport
from clonker import device_config_v2 as device_config


QUEUE_CAPACITY = 128

# Entries contain room, action, and monotonic due time.
_queue = []

# Diagnostics, intentionally kept small.
_last_result = None
_last_error = None
_peak_depth = 0


def dispatch(room_id, action_id, delay_seconds=0):
    """Validate and enqueue one fundamental action."""
    global _peak_depth

    if room_id not in device_config.ROOM_IDS:
        raise ValueError("Unknown room")
    if action_id not in device_config.ACTION_IDS:
        raise ValueError("Unknown action")

    if delay_seconds < 0:
        raise ValueError("Negative action delay")

    if len(_queue) >= QUEUE_CAPACITY:
        logger.warning("DUMB QUEUE: Full; action rejected")
        raise ValueError("Action queue full")

    # Configuration is authoritative. Do not retain references
    # to it inside queued tasks.
    room, action = device_config.action_details(
        room_id, action_id
    )

    target = action["target"]
    endpoint = room["devices"][target]

    is_toggle = action_id in (
        "mute-toggle", "power-toggle"
    )

    paths = (
        (action["on_path"], action["off_path"])
        if is_toggle else (action["path"],)
    )

    configured = bool(endpoint and any(paths))

    due = (
        0 if delay_seconds == 0
        else time.monotonic() + delay_seconds
    )

    _queue.append({
        "room": room_id,
        "action": action_id,
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


def poll():
    """Execute at most one eligible task."""
    global _last_result, _last_error

    if not _queue:
        return False

    now = time.monotonic()
    selected = None

    # Find the first eligible task in insertion order.
    for index, task in enumerate(_queue):
        if task["due"] == 0 or now >= task["due"]:
            selected = index
            break

    if selected is None:
        return False

    task = _queue.pop(selected)

    room_id = task["room"]
    action_id = task["action"]

    try:
        # Resolve CURRENT configuration at execution time.
        room, action = device_config.action_details(
            room_id, action_id
        )

        room_name = room["name"]
        target = action["target"]
        endpoint = room["devices"][target]
        method = action["method"]

        # Toggle selection requires state tracking.
        # Never guess ON or OFF.
        if action_id in ("mute-toggle", "power-toggle"):
            message = (
                "DEFERRED: {} / {} "
                "(toggle state not implemented)"
            ).format(room_name, action_id)

            logger.info(message)
            _last_result = message
            _last_error = None
            return True

        path = action["path"]

        # Blank endpoint or path means an intentional no-op.
        if not endpoint or not path:
            message = "NO-OP: {} / {} (unconfigured)".format(
                room_name, action_id
            )

            logger.info(message)
            _last_result = message
            _last_error = None
            return True

        logger.info(
            "EXECUTING: {} / {} -> {} {} {}".format(
                room_name,
                action_id,
                target,
                method,
                path,
            )
        )

        # Blocking HTTP. The scheduler resumes when this
        # request completes or raises an exception.
        result = http_transport.send(
            endpoint,
            method,
            path,
        )

        message = (
            "EXECUTED: {} / {} -> HTTP {} ({} ms)"
        ).format(
            room_name,
            action_id,
            result["status"],
            result["total_ms"],
        )

        logger.info(message)
        _last_result = message
        _last_error = None

        return True

    except Exception as error:
        # The executing task has already been removed.
        # Preserve Phase A fail-stop queue semantics.
        discarded = len(_queue)
        _queue.clear()

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


def clear(reason="Manual reset"):
    """Discard pending tasks, preserving diagnostic history."""
    discarded = len(_queue)
    _queue.clear()

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
