# The Clonker 10000
# clonker/device_adapters.py
#
# Chapter 6 -- Device adapter selection and cache
#
# Clonker Designed by David Jacobson

"""Resolve configured fundamental commands to device adapters.

Adapter selection uses recognized command signatures,
not device names, room IDs, or fixed device positions.

Only fundamental actions are eligible for specialized adapters.
Custom actions continue using generic HTTP.

Unknown commands always resolve to generic HTTP.

The in-memory adapter cache is rebuilt when configuration
becomes active. No adapter information is persisted to JSON.

This module performs no network I/O or command execution.
"""

ROKU_HOLD = "roku-hold"
GENERIC_HTTP = "generic-http"
DENON_TCP = "denon-tcp"


# Exact HTTP command paths recognized by the Denon TCP adapter.
# Values are equivalent native Denon TCP commands.
# Other Denon commands remain on generic HTTP.

DENON_VOLUME_COMMANDS = {
    "/goform/formiPhoneAppDirect.xml?MVUP": "MVUP",
    "/goform/formiPhoneAppDirect.xml?MVDOWN": "MVDOWN",
}

ROKU_VOLUME_COMMANDS = {
    "/keypress/VolumeUp": "up",
    "/keypress/VolumeDown": "down",
}

# Only specialized adapter selections are stored.
# Key: (room_id, action_id)
# Value: adapter identifier

_adapter_map = {}


def resolve(kind, action_id, method, path):
    """Recognize the adapter for a configured command."""

    if (
        kind == "fundamental"
        and action_id in ("volume-up", "volume-down")
        and method == "GET"
        and path in DENON_VOLUME_COMMANDS
    ):
        return DENON_TCP

    if (
        kind == "fundamental"
        and action_id in ("volume-up", "volume-down")
        and method == "POST"
        and path in ROKU_VOLUME_COMMANDS
    ):
        return ROKU_HOLD

    return GENERIC_HTTP


def denon_command(path):
    """Translate a recognized HTTP path to a Denon TCP command."""

    command = DENON_VOLUME_COMMANDS.get(path)

    if command is None:
        raise ValueError("Unsupported Denon TCP command")

    return command


def rebuild(config):
    """Build and publish an adapter map from validated configuration.

    Construct the replacement map before publishing it.
    If inspection fails, the existing cache remains unchanged.

    Returns the number of specialized adapter selections.
    """

    new_map = {}

    for room_id, room in config["rooms"].items():
        for action_id, action in room["actions"].items():

            # Only fundamental volume actions are supported
            # by specialized adapters in Chapter 6.
            if action_id not in ("volume-up", "volume-down"):
                continue

            adapter = resolve(
                "fundamental",
                action_id,
                action["method"],
                action["path"],
            )

            if adapter != GENERIC_HTTP:
                new_map[(room_id, action_id)] = adapter

    global _adapter_map
    _adapter_map = new_map

    return len(new_map)


def lookup(room_id, action_id):
    """Return the cached adapter selection for a fundamental action.

    Unknown or unrecognized actions use generic HTTP.
    """

    return _adapter_map.get(
        (room_id, action_id),
        GENERIC_HTTP,
    )


def snapshot():
    """Return a copy of the adapter map for diagnostics."""

    return dict(_adapter_map)
