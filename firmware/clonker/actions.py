# The Clonker 10000
# clonker/actions.py -- The Dumb Queue (logging-only prototype)
#
# Clonker Designed by David Jacobson

"""Shared action dispatcher and cooperative task queue.

Chapter 3, Phase A: simulate command execution through serial logging.
No outbound HTTP requests are sent.

One poll executes at most one eligible task. Future-dated tasks never
prevent immediate tasks from running. An execution failure discards all
remaining tasks, but does not disable the queue.
"""

import time

from clonker import logger
from clonker import device_config_v2 as device_config


QUEUE_CAPACITY = 128

# Entries contain room, action, and monotonic due time.
_queue = []

# Diagnostics, intentionally kept small.
_last_result = None
_last_error = None
_peak_depth = 0

# Manual failure injection for bench testing only.
_fail_next = False


def dispatch(room_id, action_id, delay_seconds=0):
    """Validate and enqueue one fundamental action.

    The browser uses the default immediate scheduling. The optional delay
    supports future custom commands and direct REPL scheduler tests.
    """
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

    # Configuration is authoritative. Do not retain references to it
    # inside queued tasks.
    room, action = device_config.action_details(room_id, action_id)

    target = action["target"]
    endpoint = room["devices"][target]
    is_toggle = action_id in ("mute-toggle", "power-toggle")

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
    """Execute at most one eligible task; never wait for a deadline."""
    global _last_result, _last_error, _fail_next

    if not _queue:
        return False

    now = time.monotonic()
    selected = None

    # Find the first eligible task in insertion order.
    # A delayed task cannot hold an immediate task hostage.
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
        if _fail_next:
            _fail_next = False
            raise RuntimeError("Simulated outbound command failure")

        # Resolve the CURRENT configuration at execution time.
        room, action = device_config.action_details(room_id, action_id)
        target = action["target"]
        endpoint = room["devices"][target]

        is_toggle = action_id in ("mute-toggle", "power-toggle")
        if is_toggle:
            # Toggle history is a later milestone. Neither direction
            # is selected or implied during this logging-only phase.
            paths = (action["on_path"], action["off_path"])
        else:
            paths = (action["path"],)

        configured = bool(endpoint and any(paths))

        if configured:
            message = "SIMULATED: {} / {} -> {} {} (no HTTP sent)".format(
                room["name"], action_id, target, endpoint
            )
        else:
            message = "NO-OP: {} / {} (unconfigured)".format(
                room["name"], action_id
            )

        logger.info(message)
        _last_result = message
        _last_error = None
        return True

    except Exception as error:
        # This catches simulated failures and unexpected execution errors.
        # The task being executed has already been removed.
        discarded = len(_queue)
        _queue.clear()

        _last_error = "{} / {}: {}".format(
            room_id, action_id, error
        )
        _last_result = "FAILED; {} pending tasks discarded".format(
            discarded
        )

        logger.warning("DUMB QUEUE: {}".format(_last_error))
        logger.warning("DUMB QUEUE: {}".format(_last_result))
        return True


def clear(reason="Manual reset"):
    """Discard pending tasks, preserving diagnostic history."""
    discarded = len(_queue)
    _queue.clear()
    logger.info("DUMB QUEUE: Cleared {} tasks ({})".format(
        discarded, reason
    ))
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


def inject_failure_once():
    """Make the next eligible task fail. Bench diagnostics only."""
    global _fail_next
    _fail_next = True
    logger.warning("DUMB QUEUE: Next execution will simulate failure")
