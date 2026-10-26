# The Clonker 10000 -- JSON configuration
# clonker/device_config_v2.py
#
# Clonker Designed by David Jacobson
# GitHub: https://github.com/djacobson/clonker-10000

"""Validated JSON configuration and revision-protected persistence.

The active schema version is defined by CONFIG_VERSION below.
The module retains its original v2 filename for import stability.
The XML v1 engine remains available separately for historical reference
and rollback with a compatible earlier firmware/configuration combination.

Blank IP addresses and HTTP paths are intentional, valid no-ops.
Normal load() may fall back to backups but NEVER silently repairs a primary.
A successful load binds the file path for all subsequent save() operations.
"""

import json
import os


# Clonker Config v4 (JSON): optional rooms, three reserved built-in destinations,
# fourteen fundamental actions, and user-defined custom actions.
#
# Custom destinations (device-4 onward) are reserved for a
# future schema extension; they are not accepted yet.

CONFIG_FILE = "/clonker/device_config.json"
CONFIG_VERSION = 4

MAX_CONFIG_BYTES = 8192
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


def resolve_endpoint(room, device_id):
    """Resolve a built-in destination from a validated room.

    Future custom destinations will extend this single helper
    without changing command-step target identifiers.
    """
    if device_id in DEVICE_IDS:
        return room["devices"][device_id]

    raise ValueError("Unknown device destination: " + str(device_id))


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


def _custom_actions(value, room_id):
    """Validate and normalize ordered custom HTTP actions."""
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
                ("target", "method", "path", "wait_after_ms"),
                step_where
            )

            target = step["target"]
            method = step["method"]
            path = step["path"]
            wait_ms = step["wait_after_ms"]

            # Custom destinations will be added to this resolution
            # model later. Only built-in destinations exist today.
            if not isinstance(target, str) or target not in DEVICE_IDS:
                raise ValueError("Invalid custom target: " + step_where)

            if method not in ("GET", "POST"):
                raise ValueError("Invalid custom method: " + step_where)

            if (not isinstance(path, str) or
                    not path or
                    len(path) > MAX_PATH_LENGTH or
                    not path.startswith("/")):
                raise ValueError("Invalid custom path: " + step_where)

            if (type(wait_ms) is not int or
                    not 0 <= wait_ms <= MAX_WAIT_AFTER_MS):
                raise ValueError("Invalid custom wait: " + step_where)

            if step_index == len(steps) - 1 and wait_ms != 0:
                raise ValueError("Final custom step must have zero wait: " + step_where)

            validated_steps.append({
                "target": target,
                "method": method,
                "path": path,
                "wait_after_ms": wait_ms,
            })

        validated.append({
            "id": action_id,
            "name": name.strip(),
            "steps": validated_steps,
        })

    return validated


def validate_config(config):
    """Return a validated, ordered copy; blank endpoints/paths are valid."""
    _keys(config, ("version", "rooms"), "root")
    if type(config["version"]) is not int or config["version"] != CONFIG_VERSION:
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

    # Preserve the established room-ID ordering while allowing
    # unused rooms to be absent from the configuration.
    for room_id in ROOM_IDS:
        if room_id not in configured_rooms:
            continue

        room = configured_rooms[room_id]

        _keys(room, ("name", "devices", "actions", "custom_actions"), room_id)
        name = room["name"]
        if (not isinstance(name, str) or not name.strip() or
                len(name) > MAX_ROOM_NAME_LENGTH):
            raise ValueError("Invalid room name: " + room_id)

        # Missing device addresses are valid; physical actions will no-op.
        _keys(room["devices"], DEVICE_IDS, room_id + ".devices")
        devices = {}
        for device_id in DEVICE_IDS:
            devices[device_id] = _ip(room["devices"][device_id], room_id + "." + device_id)

        # Fundamental action IDs always exist, even when unconfigured.
        _keys(room["actions"], ACTION_IDS, room_id + ".actions")
        actions = {}
        for action_id in ACTION_IDS:
            action = room["actions"][action_id]
            where = room_id + "." + action_id

            # Toggle actions have separate ON and OFF paths.
            # All other fundamental actions retain one path.
            is_toggle = action_id in ("power-toggle", "mute-toggle")

            if is_toggle:
                expected_fields = (
                    "target", "method", "on_path", "off_path"
                )
            else:
                expected_fields = ("target", "method", "path")

            _keys(action, expected_fields, where)

            if (not isinstance(action["target"], str) or
                    action["target"] not in DEVICE_IDS):
                raise ValueError("Invalid target: " + where)

            if (not isinstance(action["method"], str) or
                    action["method"] not in ("GET", "POST")):
                raise ValueError("Invalid method: " + where)

            validated_action = {
                "target": action["target"],
                "method": action["method"],
            }

            if is_toggle:
                for field in ("on_path", "off_path"):
                    path = action[field]
                    if (not isinstance(path, str) or
                            len(path) > MAX_PATH_LENGTH):
                        raise ValueError(
                            "Invalid " + field + ": " + where
                        )
                    validated_action[field] = path
            else:
                path = action["path"]
                if (not isinstance(path, str) or
                        len(path) > MAX_PATH_LENGTH):
                    raise ValueError("Invalid path: " + where)
                validated_action["path"] = path

            actions[action_id] = validated_action

        # User-defined actions are validated independently of
        # fundamental actions and preserve their declared order.
        custom_actions = _custom_actions(
            room["custom_actions"], room_id
        )

        rooms[room_id] = {
            "name": name.strip(),
            "devices": devices,
            "actions": actions,
            "custom_actions": custom_actions,
        }

    return {"version": CONFIG_VERSION, "rooms": rooms}


def to_json(config):
    """Canonical compact JSON; deterministic regardless of input key order."""
    validated = validate_config(config)
    # CircuitPython json.dumps() does not accept ensure_ascii.
    result = json.dumps(validated, separators=(",", ":"))
    if len(result.encode("utf-8")) > MAX_CONFIG_BYTES:
        raise ValueError("Configuration exceeds byte limit")
    return result


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
    """Read and validate one file, without changing active state."""
    with open(path, "rb") as file:
        return from_json(file.read(MAX_CONFIG_BYTES + 1))


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


def room(room_id):
    return current()["rooms"][room_id]


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
        config = current()
    value = 2166136261
    for byte in to_json(config).encode("utf-8"):
        value = ((value ^ byte) * 16777619) & 0xFFFFFFFF
    return "{:08x}".format(value)


def _backup_looks_valid(path):
    try:
        _load_existing(path)
        return True
    except (OSError, ValueError):
        return False


def _write_verified_temp(path, contents):
    """Write and read back a temporary file before any rotation."""
    temp_path = path + ".tmp"
    with open(temp_path, "wb") as file:
        file.write(contents.encode("utf-8"))
        file.flush()
    with open(temp_path, "rb") as file:
        actual = file.read(MAX_CONFIG_BYTES + 1)
    if actual != contents.encode("utf-8"):
        raise OSError("Temporary JSON verification failed")
    if from_json(actual) != from_json(contents):
        raise ValueError("Temporary JSON validation failed")
    return temp_path


def _replace_with_backup(path, contents):
    """Rotate verified generations and install a checked replacement."""
    # Never rotate the backup chain if the primary is already damaged.
    if not _backup_looks_valid(path):
        raise ValueError("Primary JSON configuration is missing or invalid")
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

    # Check the installed primary before publishing new in-memory state.
    with open(path, "rb") as file:
        actual = file.read(MAX_CONFIG_BYTES + 1)
    if actual != contents.encode("utf-8"):
        raise OSError("Installed JSON verification failed")
    _load_existing(path)


def save(config, expected_revision, path=None):
    """Save only to the primary path selected by the last successful load."""
    global _current
    if _current is None or _current_path is None:
        raise RuntimeError("Configuration not loaded")
    if path is None:
        path = _current_path

    # The explicit path guard prevents a disposable-file test from writing
    # to production merely because a module-level default was changed.
    if path != _current_path:
        raise ValueError("Save path differs from loaded configuration")
    if not isinstance(expected_revision, str) or expected_revision != revision():
        raise ValueError("Configuration revision mismatch. Changes not saved. Refresh page.")

    validated = validate_config(config)
    serialized = to_json(validated)

    # A backup-loaded configuration is not permission to overwrite bad primary.
    # Reject out-of-band edits between the original load and this save.
    disk = _load_existing(path)
    if disk != _current:
        raise ValueError("Configuration changed on disk; reload required")
    if serialized == to_json(_current):
        return False

    _replace_with_backup(path, serialized)
    _current = validated
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
