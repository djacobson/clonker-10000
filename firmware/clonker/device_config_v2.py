# The Clonker 10000 -- JSON configuration v2 (isolated first-stage engine)
# Copy to firmware/clonker/device_config_v2.py
# Does not change active XML v1 configuration or write to flash.
import json

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


def load(path=CONFIG_FILE):
    """Read and validate JSON from a file; no writes or backup recovery yet."""
    with open(path, "rb") as file:
        contents = file.read(MAX_CONFIG_BYTES + 1)
    return from_json(contents)


def revision(config):
    """Stable 32-bit FNV-1a revision over canonical UTF-8 JSON."""
    value = 2166136261
    for byte in to_json(config).encode("utf-8"):
        value = ((value ^ byte) * 16777619) & 0xFFFFFFFF
    return "{:08x}".format(value)
 