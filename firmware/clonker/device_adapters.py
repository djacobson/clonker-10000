# The Clonker 10000
# clonker/device_adapters.py
#
# Chapter 6 -- Device adapter selection
#
# Clonker Designed by David Jacobson

"""Resolve configured commands to device adapters.

Adapter selection is based on recognized command signatures,
not device names, room IDs, or fixed device positions.

Only fundamental actions are eligible for specialized adapters.
Custom actions continue using generic HTTP.

Unknown commands always resolve to generic HTTP.

This module performs no network I/O and does not execute commands.
"""

GENERIC_HTTP = "generic-http"
DENON_TCP = "denon-tcp"


# Exact HTTP command paths recognized by the Denon TCP adapter.
#
# Values are equivalent native Denon TCP commands.
# Other Denon commands remain on the generic HTTP transport.

DENON_VOLUME_COMMANDS = {
    "/goform/formiPhoneAppDirect.xml?MVUP": "MVUP",
    "/goform/formiPhoneAppDirect.xml?MVDOWN": "MVDOWN",
}


def resolve(kind, action_id, method, path):
    """Return the adapter identifier for a configured command.

    kind:
        "fundamental" or "custom"

    action_id:
        Configured fundamental or custom action ID

    method, path:
        Configured HTTP method and command path
    """

    if (
        kind == "fundamental"
        and action_id in ("volume-up", "volume-down")
        and method == "GET"
        and path in DENON_VOLUME_COMMANDS
    ):
        return DENON_TCP

    return GENERIC_HTTP


def denon_command(path):
    """Return the native Denon TCP command for a recognized path.

    Raises ValueError for unsupported paths.
    """

    command = DENON_VOLUME_COMMANDS.get(path)

    if command is None:
        raise ValueError("Unsupported Denon TCP command")

    return command
