# The Clonker 10000 -- JSON configuration
# clonker/device_config.py
#
# Clonker Designed by David Jacobson
# GitHub: https://github.com/djacobson/clonker-10000

"""Validated JSON configuration and revision-protected persistence.

The active schema version is defined by CONFIG_VERSION.

Config v5 uses typed device records and protocol-aware
command objects for fundamental and custom actions.

Blank endpoints and fundamental commands are valid no-ops.
Normal load() may fall back to backups but NEVER silently
repairs a primary.
A successful load binds the file path for subsequent saves.
"""

import json
import os
import time
import gc
from clonker.system import logger
from clonker.devices import device_types
from clonker.devices import device_adapters

# Clonker Config v5 (JSON): optional rooms, typed device
# records, protocol-aware commands, fourteen fundamental
# actions, and user-defined custom actions.
#
# Custom destinations (device-4 onward) remain reserved
# for a future schema extension.

CONFIG_FILE = "/clonker/device_config.json"
CONFIG_VERSION = 5

MAX_CONFIG_BYTES = 16384
MAX_ROOM_NAME_LENGTH = 40
MAX_PATH_LENGTH = 512

MAX_CUSTOM_ACTIONS_PER_ROOM = 16
MAX_STEPS_PER_ACTION = 16
MAX_WAIT_AFTER_MS = 60000
MAX_CUSTOM_ACTION_ID_LENGTH = 40
MAX_CUSTOM_ACTION_NAME_LENGTH = 60

ROOM_IDS = ("room-1", "room-2", "room-3")
MIN_ROOMS = 1
MAX_ROOMS = len(ROOM_IDS)

DEVICE_IDS = ("device-1", "device-2", "device-3")

ACTION_IDS = (
    "volume-up", "volume-down", "mute-toggle",
    "nav-up", "nav-down", "nav-left", "nav-right",
    "select", "back", "home", "play-pause",
    "skip-back", "skip-forward", "power-toggle",
)

# Active validated data and the exact primary path selected by load().
_current = None
_current_path = None


def _keys(obj, expected, location):
    """Reject missing and unknown fields rather than silently ignoring them."""
    if not isinstance(obj, dict) or set(obj) != set(expected):
        raise ValueError("Invalid fields: " + location)


def _ip(value, location):
    """Accept a blank endpoint, IPv4, or IPv4:port."""
    if not isinstance(value, str):
        raise ValueError("Invalid IP type: " + location)

    if value == "":
        return value

    # A port is optional, but must be 1-65535 when supplied.
    endpoint = value.split(":")
    if len(endpoint) > 2:
        raise ValueError("Invalid IP port: " + location)

    address = endpoint[0]

    if len(endpoint) == 2:
        port = endpoint[1]

        if (not port or
                any(ch not in "0123456789" for ch in port) or
                not 1 <= int(port) <= 65535):
            raise ValueError("Invalid IP port: " + location)

    # Preserve existing strict dotted-IPv4 validation.
    parts = address.split(".")
    if len(parts) != 4:
        raise ValueError("Invalid IPv4: " + location)

    for part in parts:
        if (not part or len(part) > 3 or
                any(ch not in "0123456789" for ch in part) or
                int(part) > 255):
            raise ValueError("Invalid IPv4: " + location)

    return value


def resolve_device(room, device_id):
    """Return a read-only reference to a validated device record."""
    if device_id in DEVICE_IDS:
        return room["devices"][device_id]

    raise ValueError("Unknown device destination: " + str(device_id))


def resolve_endpoint(room, device_id):
    """Resolve the endpoint of a validated device."""
    return resolve_device(room, device_id)["endpoint"]


def command_is_blank(command):
    """Check an already-validated command without revalidation."""
    kind = command["kind"]

    if kind == device_types.HTTP:
        return command["path"] == ""

    if kind == device_types.SSAP:
        return command["uri"] == ""

    if kind == device_types.POINTER:
        return command["button"] == ""

    if kind == device_types.WAKE_ON_LAN:
        return command["mac"] == ""

    raise ValueError("Unknown command kind")


def _device(value, location):
    """Validate and normalize a typed device record."""
    if not isinstance(value, dict):
        raise ValueError("Invalid device: " + location)

    type_id = value.get("type")

    if not isinstance(type_id, str):
        raise ValueError("Invalid device type: " + location)

    definition = device_types.get(type_id)

    if definition is None:
        raise ValueError("Unknown device type: " + location)

    # LG configuration is supported before runtime integration.
    # Other unimplemented device types remain unavailable.
    if not definition["enabled"] and type_id != "lg-webos":
        raise ValueError("Unavailable device type: " + location)

    expected = ("type", "endpoint") + definition["attributes"]
    _keys(value, expected, location)

    validated = {
        "type": type_id,
        "endpoint": _ip(value["endpoint"], location),
    }

    if "client_key" in definition["attributes"]:
        client_key = value["client_key"]

        if (not isinstance(client_key, str) or
                len(client_key) > 512):
            raise ValueError("Invalid client key: " + location)

        validated["client_key"] = client_key

    return validated


def _target(value, location):
    """Validate a built-in destination identifier."""
    if not isinstance(value, str) or value not in DEVICE_IDS:
        raise ValueError("Invalid target: " + location)

    return value


def _json_copy(value):
    """Copy JSON-compatible data with deterministic object ordering."""
    if isinstance(value, dict):
        for key in value:
            if not isinstance(key, str):
                raise ValueError("Invalid JSON object key")

        return {
            key: _json_copy(value[key])
            for key in sorted(value)
        }

    if isinstance(value, list):
        return [_json_copy(item) for item in value]

    if value is None or type(value) in (str, bool, int):
        return value

    if type(value) is float:
        # Reject NaN and positive/negative infinity.
        if value - value != 0:
            raise ValueError("Invalid JSON number")
        return value

    raise ValueError("Invalid JSON value")


def _command(value, device, location, allow_blank=False):
    """Validate a command against its configured device type."""
    if not isinstance(value, dict):
        raise ValueError("Invalid command: " + location)

    kind = value.get("kind")

    if not isinstance(kind, str):
        raise ValueError("Invalid command kind: " + location)

    if not device_types.supports_command(device["type"], kind):
        raise ValueError(
            "Command kind incompatible with device: " + location
        )

    if kind == device_types.HTTP:
        _keys(value, ("kind", "method", "path"), location)

        method = value["method"]
        path = value["path"]

        if method not in ("GET", "POST"):
            raise ValueError("Invalid HTTP method: " + location)

        if (not isinstance(path, str) or
                len(path) > MAX_PATH_LENGTH):
            raise ValueError("Invalid HTTP path: " + location)

        if path and not path.startswith("/"):
            raise ValueError("Invalid HTTP path: " + location)

        validated = {
            "kind": kind,
            "method": method,
            "path": path,
        }

    elif kind == device_types.SSAP:
        expected = ("kind", "uri")

        if "payload" in value:
            expected += ("payload",)

        _keys(value, expected, location)

        uri = value["uri"]

        if (not isinstance(uri, str) or
                len(uri) > MAX_PATH_LENGTH):
            raise ValueError("Invalid SSAP URI: " + location)

        if uri and (
                not uri.startswith("ssap://") or
                len(uri) <= len("ssap://") or
                any(ch.isspace() for ch in uri)):
            raise ValueError("Invalid SSAP URI: " + location)

        validated = {
            "kind": kind,
            "uri": uri,
        }

        if "payload" in value:
            payload = value["payload"]

            if not isinstance(payload, dict):
                raise ValueError("Invalid SSAP payload: " + location)

            if not uri:
                raise ValueError(
                    "Blank SSAP command cannot have payload: "
                    + location
                )

            validated["payload"] = _json_copy(payload)

    elif kind == device_types.POINTER:
        _keys(value, ("kind", "button"), location)

        button = value["button"]

        if (not isinstance(button, str) or
                len(button) > 64):
            raise ValueError("Invalid pointer button: " + location)

        allowed = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"

        if any(ch not in allowed for ch in button):
            raise ValueError("Invalid pointer button: " + location)

        validated = {
            "kind": kind,
            "button": button,
        }

    elif kind == device_types.WAKE_ON_LAN:
        _keys(
            value,
            ("kind", "mac", "broadcast", "port"),
            location
        )

        mac = value["mac"]
        broadcast = value["broadcast"]
        port = value["port"]

        if not isinstance(mac, str):
            raise ValueError("Invalid MAC address: " + location)

        if mac:
            parts = mac.split(":")

            if (
                len(parts) != 6
                or any(
                    len(part) != 2
                    or any(
                        ch not in "0123456789ABCDEFabcdef"
                        for ch in part
                    )
                    for part in parts
                )
            ):
                raise ValueError(
                    "Invalid MAC address: " + location
                )

        if (
            not isinstance(broadcast, str)
            or not broadcast
            or ":" in broadcast
        ):
            raise ValueError(
                "Invalid broadcast address: " + location
            )

        broadcast = _ip(broadcast, location)

        if type(port) is not int or not 1 <= port <= 65535:
            raise ValueError(
                "Invalid Wake-on-LAN port: " + location
            )

        validated = {
            "kind": kind,
            "mac": mac.upper(),
            "broadcast": broadcast,
            "port": port,
        }

    else:
        raise ValueError("Unsupported command kind: " + location)

    if not allow_blank and command_is_blank(validated):
        raise ValueError("Blank command: " + location)

    return validated


def _custom_action_id(value, location):
    """Validate a stable, URL-friendly custom action identifier."""
    if (not isinstance(value, str) or
            not 1 <= len(value) <= MAX_CUSTOM_ACTION_ID_LENGTH):
        raise ValueError("Invalid custom action ID: " + location)

    allowed = "abcdefghijklmnopqrstuvwxyz0123456789-"

    if (value[0] == "-" or value[-1] == "-" or
            any(ch not in allowed for ch in value)):
        raise ValueError("Invalid custom action ID: " + location)

    return value


def _custom_actions(value, room_id, devices):
    """Validate and normalize ordered protocol-aware Custom Actions."""
    if not isinstance(value, list):
        raise ValueError("Invalid custom actions: " + room_id)

    if len(value) > MAX_CUSTOM_ACTIONS_PER_ROOM:
        raise ValueError("Too many custom actions: " + room_id)

    validated = []
    seen_ids = set()

    for index, action in enumerate(value):
        where = "{}.custom_actions[{}]".format(room_id, index)

        _keys(action, ("id", "name", "steps"), where)

        action_id = _custom_action_id(action["id"], where)

        if action_id in seen_ids:
            raise ValueError("Duplicate custom action ID: " + action_id)

        seen_ids.add(action_id)

        name = action["name"]

        if (not isinstance(name, str) or
                not name.strip() or
                len(name) > MAX_CUSTOM_ACTION_NAME_LENGTH):
            raise ValueError("Invalid custom action name: " + where)

        steps = action["steps"]

        if (not isinstance(steps, list) or
                not 1 <= len(steps) <= MAX_STEPS_PER_ACTION):
            raise ValueError("Invalid custom action steps: " + where)

        validated_steps = []

        for step_index, step in enumerate(steps):
            step_where = "{}.steps[{}]".format(where, step_index)

            _keys(
                step,
                ("target", "command", "wait_after_ms"),
                step_where
            )

            target = _target(step["target"], step_where)

            command = _command(
                step["command"],
                devices[target],
                step_where + ".command"
            )

            wait_ms = step["wait_after_ms"]

            if (type(wait_ms) is not int or
                    not 0 <= wait_ms <= MAX_WAIT_AFTER_MS):
                raise ValueError("Invalid custom wait: " + step_where)

            if step_index == len(steps) - 1 and wait_ms != 0:
                raise ValueError(
                    "Final custom step must have zero wait: "
                    + step_where
                )

            validated_steps.append({
                "target": target,
                "command": command,
                "wait_after_ms": wait_ms,
            })

        validated.append({
            "id": action_id,
            "name": name.strip(),
            "steps": validated_steps,
        })

    return validated


def validate_config(config):
    """Return a validated, ordered Config v5 copy."""
    _keys(config, ("version", "rooms"), "root")

    if (type(config["version"]) is not int or
            config["version"] != CONFIG_VERSION):
        raise ValueError("Unsupported configuration version")

    configured_rooms = config["rooms"]

    if not isinstance(configured_rooms, dict):
        raise ValueError("Invalid rooms collection")

    if not MIN_ROOMS <= len(configured_rooms) <= MAX_ROOMS:
        raise ValueError("Invalid room count")

    for room_id in configured_rooms:
        if room_id not in ROOM_IDS:
            raise ValueError("Unknown room: " + str(room_id))

    rooms = {}

    # Preserve stable room IDs and canonical room ordering.
    for room_id in ROOM_IDS:
        if room_id not in configured_rooms:
            continue

        room = configured_rooms[room_id]

        _keys(
            room,
            ("name", "devices", "actions", "custom_actions"),
            room_id
        )

        name = room["name"]

        if (not isinstance(name, str) or
                not name.strip() or
                len(name) > MAX_ROOM_NAME_LENGTH):
            raise ValueError("Invalid room name: " + room_id)

        _keys(room["devices"], DEVICE_IDS, room_id + ".devices")

        devices = {}

        for device_id in DEVICE_IDS:
            devices[device_id] = _device(
                room["devices"][device_id],
                room_id + "." + device_id
            )

        _keys(room["actions"], ACTION_IDS, room_id + ".actions")

        actions = {}

        for action_id in ACTION_IDS:
            action = room["actions"][action_id]
            where = room_id + "." + action_id

            is_toggle = action_id in (
                "power-toggle",
                "mute-toggle"
            )

            if is_toggle:
                fields = ("target", "on_command", "off_command")
                command_fields = ("on_command", "off_command")
            else:
                fields = ("target", "command")
                command_fields = ("command",)

            _keys(action, fields, where)

            target = _target(action["target"], where)

            validated_action = {
                "target": target,
            }

            for field in command_fields:
                validated_action[field] = _command(
                    action[field],
                    devices[target],
                    where + "." + field,
                    allow_blank=True
                )

                if (
                    validated_action[field]["kind"]
                    == device_types.WAKE_ON_LAN
                    and action_id != "power-toggle"
                ):
                    raise ValueError(
                        "Wake-on-LAN requires power-toggle: "
                        + where
                    )

            actions[action_id] = validated_action

        custom_actions = _custom_actions(
            room["custom_actions"],
            room_id,
            devices
        )

        rooms[room_id] = {
            "name": name.strip(),
            "devices": devices,
            "actions": actions,
            "custom_actions": custom_actions,
        }

    return {
        "version": CONFIG_VERSION,
        "rooms": rooms,
    }


def _serialize_validated(config):
    """Serialize an already validated canonical configuration."""
    # CircuitPython json.dumps() does not accept ensure_ascii.
    result = json.dumps(config, separators=(",", ":"))

    if len(result.encode("utf-8")) > MAX_CONFIG_BYTES:
        raise ValueError("Configuration exceeds byte limit")

    return result


def to_json(config):
    """Canonical compact JSON; deterministic regardless of input key order."""
    return _serialize_validated(validate_config(config))


def from_json(contents):
    """Parse bounded JSON text or bytes without changing active state."""
    if isinstance(contents, bytes):
        if len(contents) > MAX_CONFIG_BYTES:
            raise ValueError("Configuration exceeds byte limit")
        contents = contents.decode("utf-8")
    if not isinstance(contents, str):
        raise ValueError("Configuration must be JSON text")
    if len(contents.encode("utf-8")) > MAX_CONFIG_BYTES:
        raise ValueError("Configuration exceeds byte limit")
    return validate_config(json.loads(contents))


def _load_existing(path):
    """Read and validate one file, without changing active state.

    Bound the read by the actual file size rather than allocating
    a maximum-sized buffer for every configuration load.
    """
    size = os.stat(path)[6]

    if size > MAX_CONFIG_BYTES:
        raise ValueError("Configuration exceeds byte limit")

    with open(path, "rb") as file:
        contents = file.read(size + 1)

    if len(contents) != size:
        raise ValueError("Configuration file size changed during read")

    return from_json(contents)


def load(path=None):
    """Load primary or backups and bind subsequent saves to this path."""
    global _current, _current_path
    if path is None:
        path = CONFIG_FILE

    # A backup can keep the application running if primary is damaged.
    # Merely loading a backup must NOT overwrite or recreate the primary.
    for candidate in (path, path + ".bak", path + ".bak.old"):
        try:
            loaded = _load_existing(candidate)
            prepared_cache = device_adapters.prepare_cache(loaded)

            device_adapters.activate(prepared_cache)

            _current = loaded
            _current_path = path
            return loaded
        except (OSError, ValueError) as error:
            print("CLONKER JSON: Cannot load {}: {}".format(candidate, error))
    raise RuntimeError("No valid Clonker JSON configuration found")


def current():
    """Return a validated copy to prevent accidental in-memory mutations."""
    if _current is None:
        raise RuntimeError("Configuration not loaded")
    return validate_config(_current)


def has_room(room_id):
    """Check active validated configuration without revalidation.

    Returns only a Boolean; does not expose mutable config data.
    """
    if _current is None:
        raise RuntimeError("Configuration not loaded")

    return room_id in _current["rooms"]


def room(room_id):
    return current()["rooms"][room_id]


def custom_actions_for_room(room_id):
    """Fast read-only access to a room's ordered Custom Actions.

    Uses the already-validated active configuration.
    Does not copy or revalidate configuration data.

    Returns an empty tuple for an unavailable room.
    Callers MUST NOT mutate the returned data.
    """
    if _current is None:
        raise RuntimeError("Configuration not loaded")

    room = _current["rooms"].get(room_id)

    if room is None:
        return ()

    return room["custom_actions"]


def action_details(room_id, action_id):
    """Fast internal access to an already-validated fundamental action.

    Returns references to the active configuration, not copies.
    Callers MUST treat these dictionaries as read-only.

    Only this module may publish or modify configuration data.
    """
    if _current is None:
        raise RuntimeError("Configuration not loaded")

    room = _current["rooms"][room_id]
    action = room["actions"][action_id]

    return room, action


def custom_action_details(room_id, action_id):
    """Fast internal access to a validated custom action.

    Returns references to the active configuration, not copies.
    Callers MUST treat these dictionaries as read-only.

    Raises KeyError if the room or custom action does not exist.
    """
    if _current is None:
        raise RuntimeError("Configuration not loaded")

    room = _current["rooms"][room_id]

    for action in room["custom_actions"]:
        if action["id"] == action_id:
            return room, action

    raise KeyError("Unknown custom action: " + str(action_id))


def revision(config=None):
    """Stable 32-bit FNV-1a revision over canonical UTF-8 JSON."""
    if config is None:
        if _current is None:
            raise RuntimeError("Configuration not loaded")
        serialized = _serialize_validated(_current)
    else:
        serialized = to_json(config)

    value = 2166136261

    for byte in serialized.encode("utf-8"):
        value = ((value ^ byte) * 16777619) & 0xFFFFFFFF

    return "{:08x}".format(value)


def _backup_looks_valid(path):
    try:
        _load_existing(path)
        return True
    except (OSError, ValueError):
        return False


def _verify_file_bytes(path, expected):
    """Verify file contents against already validated JSON bytes.

    Compare bounded chunks to avoid allocating another full
    configuration-sized buffer.
    """
    offset = 0

    with open(path, "rb") as file:
        while offset < len(expected):
            chunk = file.read(512)

            if not chunk:
                raise OSError("JSON file verification failed")

            end = offset + len(chunk)

            if chunk != expected[offset:end]:
                raise OSError("JSON file verification failed")

            offset = end

        if file.read(1):
            raise OSError("JSON file contains unexpected data")


def _write_verified_temp(path, contents):
    """Write and verify validated JSON before rotating backups."""
    temp_path = path + ".tmp"

    with open(temp_path, "wb") as file:
        file.write(contents)
        file.flush()

    _verify_file_bytes(temp_path, contents)

    return temp_path


def _replace_with_backup(path, contents):
    """Install verified JSON after the caller checks the primary.

    The caller must validate the configuration and confirm
    disk consistency before invoking this function.
    """
    temp_path = _write_verified_temp(path, contents)

    backup = path + ".bak"
    older = backup + ".old"

    # Rotate: .bak -> .bak.old; primary -> .bak; temp -> primary.
    # Individual renames are not a power-loss-atomic transaction.
    try:
        os.rename(backup, older)
    except OSError as error:
        if error.errno != 2:
            raise

    os.rename(path, backup)
    os.rename(temp_path, path)

    # Exact byte equality establishes that the installed file
    # contains the configuration already validated by save().
    _verify_file_bytes(path, contents)


def save(config, expected_revision, path=None):
    """Save only to the primary path selected by the last successful load."""
    global _current

    started = time.monotonic_ns()
    # Configuration saves are allocation-intensive. Reclaim
    # temporary HTTP and configuration objects before proceeding.
    gc.collect()

    if _current is None or _current_path is None:
        raise RuntimeError("Configuration not loaded")

    if path is None:
        path = _current_path

    # Preserve existing path and revision safeguards.
    if path != _current_path:
        raise ValueError("Save path differs from loaded configuration")

    if not isinstance(expected_revision, str) or expected_revision != revision():
        raise ValueError("Configuration revision mismatch. Changes not saved. Refresh page.")

    # Validate the incoming configuration exactly once.
    validated = validate_config(config)
    serialized = _serialize_validated(validated).encode("utf-8")
    validated_at = time.monotonic_ns()

    # Validate the existing primary and confirm disk consistency.
    # Reclaim temporary validation and serialization allocations
    # before loading and validating the existing primary.
    gc.collect()
    disk = _load_existing(path)

    if disk != _current:
        raise ValueError("Configuration changed on disk; reload required")

    # The disk copy is no longer needed.
    del disk

    # Both objects are validated and canonical.
    # Avoid serializing the active configuration again.
    if validated == _current:
        return False

    # Prepare the replacement cache before modifying disk.
    prepared_cache = device_adapters.prepare_cache(validated)
    checked_at = time.monotonic_ns()

    # Persist and verify the already validated configuration.
    _replace_with_backup(path, serialized)
    persisted_at = time.monotonic_ns()

    # Retire old adapter sessions and publish the prepared cache.
    device_adapters.activate(prepared_cache)
    _current = validated

    activated_at = time.monotonic_ns()

    logger.info(
        "CONFIG PERF: validation={:.1f}ms, "
        "disk_check+cache={:.1f}ms, "
        "persistence={:.1f}ms, "
        "activation={:.1f}ms, "
        "total={:.1f}ms".format(
            (validated_at - started) / 1_000_000,
            (checked_at - validated_at) / 1_000_000,
            (persisted_at - checked_at) / 1_000_000,
            (activated_at - persisted_at) / 1_000_000,
            (activated_at - started) / 1_000_000,
        )
    )

    return True


def _recover_missing_file(path=CONFIG_FILE):
    """Explicit recovery only; never replace an existing primary."""
    try:
        os.stat(path)
        return False
    except OSError as error:
        if error.errno != 2:
            raise

    # This operation is intentionally separate from ordinary load().
    for candidate in (path + ".bak", path + ".bak.old"):
        if not _backup_looks_valid(candidate):
            continue
        os.rename(candidate, path)
        return True
    return False
