# The Clonker 10000
# clonker/devices/device_adapters.py
#
# Chapter 13 -- Typed device adapter coordination
#
# Clonker Designed by David Jacobson

"""Select and coordinate configured device adapters.

Device type is explicitly declared in configuration.

Specialized transport selection remains dependent on
recognized command signatures and action context.

Custom Actions retain single-command execution semantics.

The in-memory adapter cache is rebuilt when configuration
becomes active. No adapter information is persisted to JSON.

This module owns adapter execution and lifecycle coordination.
The Dumb Queue owns scheduling and failure policy.
"""

import time

from clonker.net import http_transport
from clonker.devices import device_types
from clonker.devices import denon
from clonker.devices import roku


ROKU_VOLUME_HOLD = "roku-volume-hold"
ROKU_BUTTON_HOLD = "roku-button-hold"
ROKU_BUTTON_TAP = "roku-button-tap"

GENERIC_HTTP = "generic-http"
DENON_TCP = "denon-tcp"
LG_WEBOS = "lg-webos"

# Only specialized transport selections are cached.
#
# Ordinary actions: (room_id, action_id)
# Physical holds: ("hold", room_id, action_id)
# Value: adapter identifier

_adapter_map = {}


def resolve(device, kind, action_id, command):
    """Select a transport for a validated device and command.

    This function performs no network operations.

    Device type determines adapter eligibility.
    Command signatures determine specialized transport
    eligibility within that device type.
    """

    type_id = device["type"]
    command_kind = command["kind"]

    if not device_types.is_enabled(type_id):
        raise ValueError(
            "Device type not operational: " + type_id
        )

    if not device_types.supports_command(type_id, command_kind):
        raise ValueError(
            "Unsupported command kind for device: " + type_id
        )

    # LG commands use the WebSocket transport regardless
    # of fundamental, toggle or Custom Action context.
    if type_id == "lg-webos":
        return LG_WEBOS
    if command_kind != device_types.HTTP:
        raise ValueError(
            "Unsupported runtime command kind: " + command_kind
        )

    method = command["method"]
    path = command["path"]

    # Custom Actions retain their established single-command
    # HTTP behavior during the initial regression phase.
    if kind == "custom":
        return GENERIC_HTTP

    if type_id == "denon":
        if (
            kind == "fundamental"
            and action_id in ("volume-up", "volume-down")
            and method == "GET"
            and path in denon.VOLUME_COMMANDS
        ):
            return DENON_TCP

    elif type_id == "roku":
        if (
            kind == "fundamental"
            and action_id in ("volume-up", "volume-down")
            and method == "POST"
            and path in roku.VOLUME_COMMANDS
        ):
            return ROKU_VOLUME_HOLD

        if (
            kind in ("fundamental", "hold")
            and action_id in (
                "nav-up", "nav-down", "nav-left", "nav-right",
                "skip-back", "skip-forward",
            )
            and method == "POST"
            and path in roku.BUTTON_COMMANDS
        ):
            if kind == "hold":
                return ROKU_BUTTON_HOLD

            return ROKU_BUTTON_TAP

    return GENERIC_HTTP


def prepare_cache(config):
    """Prepare a specialized transport cache without publishing.

    Configuration-only device types are permitted in the
    schema but are not assigned operational transports.

    Performs no network operations and does not modify
    the active adapter cache.

    Returns the prepared adapter map.
    """

    new_map = {}

    for room_id, room in config["rooms"].items():
        devices = room["devices"]

        for action_id, action in room["actions"].items():

            if action_id in ("power-toggle", "mute-toggle"):
                continue

            device = devices[action["target"]]
            command = action["command"]

            if not device_types.is_enabled(device["type"]):
                continue

            adapter = resolve(
                device,
                "fundamental",
                action_id,
                command,
            )

            if adapter != GENERIC_HTTP:
                new_map[(room_id, action_id)] = adapter

            if adapter == ROKU_BUTTON_TAP:
                new_map[
                    ("hold", room_id, action_id)
                ] = ROKU_BUTTON_HOLD

    return new_map


def publish_cache(new_map):
    """Publish a previously prepared adapter cache."""
    global _adapter_map
    _adapter_map = new_map

    return len(new_map)


def rebuild(config):
    """Prepare and publish the specialized adapter cache."""
    return publish_cache(prepare_cache(config))


def activate(new_map):
    """Retire existing sessions and publish a prepared cache.

    Session cleanup is best-effort. A cleanup failure must
    not prevent activation of an already-persisted config.
    """
    try:
        close()
    except Exception as error:
        print(
            "ADAPTER: Session retirement warning: {}".format(
                repr(error)
            )
        )

    return publish_cache(new_map)


def lookup(room_id, action_id):
    """Return a cached fundamental transport selection.

    Runtime callers must also enforce device availability.
    """

    return _adapter_map.get(
        (room_id, action_id),
        GENERIC_HTTP,
    )


def lookup_hold(room_id, action_id):
    """Return a cached physical held-button transport."""

    return _adapter_map.get(
        ("hold", room_id, action_id),
        GENERIC_HTTP,
    )


def snapshot():
    """Return a copy of the adapter map for diagnostics."""

    return dict(_adapter_map)


def ready(adapter, device=None, command=None):
    """Can this adapter accept its next queued command?"""

    if adapter == DENON_TCP:
        return denon.ready()

    if adapter == LG_WEBOS:
        return lg_webos.ready(device, command)

    return True


def _http_fields(device, command):
    """Extract HTTP execution fields from validated records.

    Enforce runtime availability before any transport call.
    """

    type_id = device["type"]

    if not device_types.is_enabled(type_id):
        raise ValueError(
            "Device type not operational: " + type_id
        )

    if command["kind"] != device_types.HTTP:
        raise ValueError("HTTP execution requires HTTP command")

    if not device_types.supports_command(
        type_id, command["kind"]
    ):
        raise ValueError(
            "Unsupported command kind for device: " + type_id
        )

    return (
        device["endpoint"],
        command["method"],
        command["path"],
    )


def execute(adapter, device, command, action_id=None):
    """Execute one validated command through its transport.

    Returns:
        accepted: False means leave the command queued.
        detail: Transport-specific diagnostic text.
        total_ms: Time spent executing this command.

    Raises on execution failure.
    """

    start = time.monotonic_ns()

    if adapter == LG_WEBOS:
        if (
            device["type"] != "lg-webos"
            or not device_types.is_enabled("lg-webos")
            or not device_types.supports_command(
                "lg-webos", command["kind"]
            )
        ):
            raise ValueError("Unsupported LG execution")

        result = lg_webos.execute(device, command)

        return {
            "accepted": result["accepted"],
            "detail": result["detail"],
            "total_ms": round(
                (time.monotonic_ns() - start) / 1_000_000, 1
            ),
        }

    endpoint, method, path = _http_fields(device, command)

    if adapter == DENON_TCP:
        volume_command = denon.volume_command(path)

        accepted = denon.send_volume(
            endpoint, volume_command
        )

        detail = "DENON TCP {}".format(volume_command)

    elif adapter == ROKU_VOLUME_HOLD:
        direction = roku.VOLUME_COMMANDS.get(path)

        if direction is None:
            raise ValueError("Unsupported Roku volume command")

        started = roku.volume(endpoint, direction)
        accepted = True

        detail = "ROKU HOLD {} ({})".format(
            direction,
            "keydown" if started else "extended",
        )

    elif adapter == ROKU_BUTTON_TAP:
        result = roku.tap(
            endpoint, method, path, action_id
        )

        accepted = True

        if "reused" in result:
            detail = "ROKU HTTP {} ({}, {} ms)".format(
                result["status"],
                "reused" if result["reused"] else "new",
                result["total_ms"],
            )
        else:
            detail = "ROKU HTTP {}".format(result["status"])

    elif adapter == GENERIC_HTTP:
        result = http_transport.send(
            endpoint, method, path
        )

        accepted = True

        detail = "HTTP {}".format(result["status"])

    else:
        raise ValueError("Unknown device adapter")

    return {
        "accepted": accepted,
        "detail": detail,
        "total_ms": round(
            (time.monotonic_ns() - start) / 1_000_000, 1
        ),
    }


def execute_hold(adapter, device, command, event):
    """Execute a validated held-button event."""

    start = time.monotonic_ns()

    endpoint, method, path = _http_fields(device, command)

    if adapter == ROKU_BUTTON_HOLD:
        detail = roku.execute_hold(
            endpoint, method, path, event
        )
    else:
        raise ValueError(
            "Unsupported held-button adapter: {}".format(adapter)
        )

    return {
        "accepted": True,
        "detail": detail,
        "total_ms": round(
            (time.monotonic_ns() - start) / 1_000_000, 1
        ),
    }


def poll():
    """Advance stateful adapters requiring maintenance.

    Roku manages held-button and volume releases.
    Denon drains incoming TCP status messages.
    LG processes asynchronous WebSocket responses
    and retires expired sessions.
    """

    roku.poll()
    denon.poll_rx()
    try:
        lg_webos.poll()
    except Exception as error:
        return LG_WEBOS, error

    return None


def cancel_active():
    """Best-effort cleanup of active Roku holds.

    Attempt both releases independently so a failure
    in one does not prevent the other.
    """

    first_error = None

    for release in (roku.button_up, roku.release):
        try:
            release()
        except Exception as error:
            if first_error is None:
                first_error = error

    if first_error is not None:
        raise first_error

    return True


def close():
    """Release adapter resources during shutdown or activation."""

    try:
        roku.close()
    finally:
        try:
            denon.close()
        finally:
            lg_webos.close()
