# The Clonker 10000
# clonker/actions.py -- shared action dispatcher (logging-only prototype)
#
# Clonker Designed by David Jacobson

"""Dispatch configured fundamental actions.

Phase 1: log and return status only. No device HTTP requests are sent.
Later: this module will own transport, toggle state, and display events.
"""

from clonker import logger
from clonker import device_config_v2 as device_config


def dispatch(room_id, action_id):
    """Return a small JSON-serializable status for a valid action."""
    if room_id not in device_config.ROOM_IDS:
        raise ValueError("Unknown room")
    if action_id not in device_config.ACTION_IDS:
        raise ValueError("Unknown action")

    room, action = device_config.action_details(room_id, action_id)

    target = action["target"]
    endpoint = room["devices"][target]
    is_toggle = action_id in ("mute-toggle", "power-toggle")

    # A toggle has two candidate paths, but no direction is chosen yet.
    # This avoids accidentally implying ON/OFF state before implementation.
    paths = ([action["on_path"], action["off_path"]]
             if is_toggle else [action["path"]])
    configured = bool(endpoint and any(paths))

    message = "STUB: {} / {}".format(room["name"], action_id)
    if not configured:
        message += " (unconfigured; no command sent)"
    else:
        message += " (logged; no command sent)"
    logger.info(message)

    return {
        "ok": True,
        "status": "stub",
        "room": room_id,
        "room_name": room["name"],
        "action": action_id,
        "configured": configured,
        "message": message,
    }
 