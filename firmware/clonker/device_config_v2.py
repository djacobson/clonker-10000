# The Clonker 10000 -- JSON configuration v2 (isolated engine)
# XML v1 remains the active firmware until coordinated cutover.
#
# Clonker Designed by David Jacobson
# GitHub: https://github.com/djacobson/clonker-10000
import json
import os

CONFIG_FILE = "/clonker/device_config.json"
CONFIG_VERSION = 2
MAX_CONFIG_BYTES = 8192
MAX_ROOM_NAME_LENGTH = 40
MAX_PATH_LENGTH = 512
ROOM_IDS = ("room-1", "room-2", "room-3")
DEVICE_IDS = ("tv", "avr", "streaming")
ACTION_IDS = (
    "volume-up", "volume-down", "mute-toggle",
    "nav-up", "nav-down", "nav-left", "nav-right",
    "select", "back", "home", "play-pause",
    "skip-back", "skip-forward", "power-toggle",
)

_current = None


def _keys(obj, expected, location):
    if not isinstance(obj, dict) or set(obj) != set(expected):
        raise ValueError("Invalid fields: " + location)


def _ip(value, location):
    if not isinstance(value, str):
        raise ValueError("Invalid IP type: " + location)
    if value == "":
        return value
    parts = value.split(".")
    if len(parts) != 4:
        raise ValueError("Invalid IPv4: " + location)
    for part in parts:
        if (not part or len(part) > 3 or
                any(ch not in "0123456789" for ch in part) or
                int(part) > 255):
            raise ValueError("Invalid IPv4: " + location)
    return value


def validate_config(config):
    """Return a validated, ordered copy; blank endpoints/paths are valid."""
    _keys(config, ("version", "rooms"), "root")
    if type(config["version"]) is not int or config["version"] != CONFIG_VERSION:
        raise ValueError("Unsupported configuration version")
    _keys(config["rooms"], ROOM_IDS, "rooms")
    rooms = {}
    for room_id in ROOM_IDS:
        room = config["rooms"][room_id]
        _keys(room, ("name", "devices", "actions", "custom_actions"), room_id)
        name = room["name"]
        if (not isinstance(name, str) or not name.strip() or
                len(name) > MAX_ROOM_NAME_LENGTH):
            raise ValueError("Invalid room name: " + room_id)
        _keys(room["devices"], DEVICE_IDS, room_id + ".devices")
        devices = {}
        for device_id in DEVICE_IDS:
            devices[device_id] = _ip(room["devices"][device_id], room_id + "." + device_id)
        _keys(room["actions"], ACTION_IDS, room_id + ".actions")
        actions = {}
        for action_id in ACTION_IDS:
            action = room["actions"][action_id]
            where = room_id + "." + action_id
            _keys(action, ("target", "method", "path"), where)
            if not isinstance(action["target"], str) or action["target"] not in DEVICE_IDS:
                raise ValueError("Invalid target: " + where)
            if not isinstance(action["method"], str) or action["method"] not in ("GET", "POST"):
                raise ValueError("Invalid method: " + where)
            if not isinstance(action["path"], str) or len(action["path"]) > MAX_PATH_LENGTH:
                raise ValueError("Invalid path: " + where)
            actions[action_id] = {
                "target": action["target"],
                "method": action["method"],
                "path": action["path"],
            }
        if not isinstance(room["custom_actions"], list) or room["custom_actions"]:
            raise ValueError("Custom actions not yet supported: " + room_id)
        rooms[room_id] = {
            "name": name.strip(),
            "devices": devices,
            "actions": actions,
            "custom_actions": [],
        }
    return {"version": CONFIG_VERSION, "rooms": rooms}


def to_json(config):
    """Canonical compact JSON; deterministic regardless of input key order."""
    validated = validate_config(config)
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


def load(path=CONFIG_FILE):
    """Load primary, then backups. Never silently rewrite disk."""
    global _current
    for candidate in (path, path + ".bak", path + ".bak.old"):
        try:
            loaded = _load_existing(candidate)
            _current = loaded
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
    # Check primary before touching the backup chain.
    if not _backup_looks_valid(path):
        raise ValueError("Primary JSON configuration is missing or invalid")
    temp_path = _write_verified_temp(path, contents)
    backup = path + ".bak"
    older = backup + ".old"
    # The existing XML implementation uses these same rename operations.
    try:
        os.rename(backup, older)
    except OSError as error:
        if error.errno != 2:
            raise
    os.rename(path, backup)
    os.rename(temp_path, path)
    with open(path, "rb") as file:
        actual = file.read(MAX_CONFIG_BYTES + 1)
    if actual != contents.encode("utf-8"):
        raise OSError("Installed JSON verification failed")
    _load_existing(path)


def save(config, expected_revision, path=CONFIG_FILE):
    """Persist a changed config only if RAM and disk revisions agree."""
    global _current
    if _current is None:
        raise RuntimeError("Configuration not loaded")
    if not isinstance(expected_revision, str) or expected_revision != revision():
        raise ValueError("Configuration revision mismatch")
    validated = validate_config(config)
    serialized = to_json(validated)
    # A backup-loaded configuration is not permission to overwrite bad primary.
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
    for candidate in (path + ".bak", path + ".bak.old"):
        if not _backup_looks_valid(candidate):
            continue
        os.rename(candidate, path)
        return True
    return False
 