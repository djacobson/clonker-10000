# clonker/devices/device_types.py
#
# Chapter 12 -- Central device-type registry

"""Device-type definitions for configuration and adapter selection.

This module contains configuration metadata only.
It does not import adapters or perform network operations.
"""

DEFAULT_TYPE = "generic-http"

HTTP = "http"
SSAP = "ssap"
POINTER = "pointer"

# Registry order determines device selector display order.
#
# enabled:
#     Available for normal configuration and execution.
#
# default_port:
#     Suggested configuration port, not necessarily
#     the port used by every adapter transport.
#
# attributes:
#     Additional device-specific configuration fields.
#
# pairing:
#     Device supports a pairing operation.

DEVICE_TYPES = {
    "generic-http": {
        "label": "Generic HTTP",
        "enabled": True,
        "default_port": 80,
        "command_kinds": (HTTP,),
        "attributes": (),
        "pairing": False,
    },
    "denon": {
        "label": "Denon AVR",
        "enabled": True,
        "default_port": 8080,
        "command_kinds": (HTTP,),
        "attributes": (),
        "pairing": False,
    },
    "roku": {
        "label": "Roku ECP",
        "enabled": True,
        "default_port": 8060,
        "command_kinds": (HTTP,),
        "attributes": (),
        "pairing": False,
    },
    "lg-webos": {
        "label": "LG webOS",
        "enabled": True,
        "default_port": 3000,
        "command_kinds": (SSAP, POINTER),
        "attributes": ("client_key",),
        "pairing": True,
    },
    "apple-tv": {
        "label": "Apple TV",
        "enabled": False,
        "default_port": None,
        "command_kinds": (),
        "attributes": (),
        "pairing": False,
    },
    "fire-tv": {
        "label": "Amazon Fire TV",
        "enabled": False,
        "default_port": None,
        "command_kinds": (),
        "attributes": (),
        "pairing": False,
    },
}


def get(type_id):
    """Return the registered device definition, or None."""
    return DEVICE_TYPES.get(type_id)


def is_enabled(type_id):
    """Return whether a device type is operational."""
    definition = get(type_id)

    return (
        definition is not None
        and definition["enabled"]
    )


def supports_command(type_id, kind):
    """Return whether a device type supports a command kind.

    Capability is independent of runtime availability.
    """
    definition = get(type_id)

    return (
        definition is not None
        and kind in definition["command_kinds"]
    )