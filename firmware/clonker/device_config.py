# The Clonker 10000
# clonker/device_config.py
#
# Read-only, three-room XML configuration prototype.
#
# Clonker Designed by David Jacobson
# GitHub: https://github.com/djacobson/clonker-10000
import os
import storage

CONFIG_FILE = "/clonker/device_config.xml"
CONFIG_VERSION = "1"
MAX_CONFIG_BYTES = 8192
MAX_ROOM_NAME_LENGTH = 40


# Developer-defined number of supported rooms.
ROOM_COUNT = 3

ROOM_IDS = tuple(
    "room-{}".format(n)
    for n in range(1, ROOM_COUNT + 1)
)

_current = None


def _attribute(opening_tag, name):
    """Extract a quoted attribute from an opening tag."""
    marker = name + '="'
    start = opening_tag.find(marker)

    if start < 0:
        raise ValueError("Missing attribute: " + name)

    start += len(marker)
    end = opening_tag.find('"', start)

    if end < 0:
        raise ValueError("Unclosed attribute: " + name)

    return opening_tag[start:end]


def _element(xml, tag):
    """Return opening tag and contents of an XML element."""
    start = xml.find("<" + tag)

    if start < 0:
        raise ValueError("Missing element: " + tag)

    opening_end = xml.find(">", start)
    closing = "</" + tag + ">"
    end = xml.find(closing, opening_end)

    if opening_end < 0 or end < 0:
        raise ValueError("Incomplete element: " + tag)

    opening = xml[start:opening_end + 1]
    contents = xml[opening_end + 1:end]

    return opening, contents


def _device_ip(room_xml, tag):
    """Read an IP attribute from a device element."""
    start = room_xml.find("<" + tag + " ")

    if start < 0:
        raise ValueError("Missing device: " + tag)

    end = room_xml.find(">", start)

    if end < 0:
        raise ValueError("Incomplete device: " + tag)

    return _attribute(room_xml[start:end + 1], "ip")


def _validate_ip(value, field_name):
    """Validate an optional IPv4 address."""
    value = value.strip()

    # Empty means the device is not configured.
    if not value:
        return ""

    parts = value.split(".")

    if len(parts) != 4:
        raise ValueError("Invalid {} address".format(field_name))

    for part in parts:
        if not part or any(ch not in "0123456789" for ch in part): 
            raise ValueError(
                "Invalid {} address".format(field_name)
            )

        if len(part) > 3 or int(part) > 255:
            raise ValueError(
                "Invalid {} address".format(field_name)
            )

    return value


def _validate_room_elements(contents):
    """Reject duplicate expected elements within one room."""
    for tag in ("devices", "preferences", "volume_device"):
        opening = "<" + tag + ">"
        if contents.count(opening) != 1:
            raise ValueError(
                "Expected exactly one " + tag + " element"
            )

    for tag in ("tv", "avr"):
        opening = "<" + tag + " "
        if contents.count(opening) != 1:
            raise ValueError(
                "Expected exactly one " + tag + " device"
            )


def _parse_room(room_xml):
    """Parse and validate one room's structure."""
    opening, contents = _element(room_xml, "room")
    _validate_room_elements(contents)

    room_id = _attribute(opening, "id")
    name = _unescape_xml(_attribute(opening, "name")).strip()

    if not name or len(name) > MAX_ROOM_NAME_LENGTH:
        raise ValueError("Invalid room name: " + room_id)

    # Devices must be inside <devices>.
    _, devices_xml = _element(contents, "devices")

    for tag in ("tv", "avr"):
        if devices_xml.count("<" + tag + " ") != 1:
            raise ValueError(
                "{} must be inside devices".format(tag)
            )

    # Volume preference must be inside <preferences>.
    _, preferences_xml = _element(contents, "preferences")

    if preferences_xml.count("<volume_device>") != 1:
        raise ValueError(
            "volume_device must be inside preferences"
        )

    tv_ip = _validate_ip(
        _device_ip(devices_xml, "tv"), "TV"
    )
    avr_ip = _validate_ip(
        _device_ip(devices_xml, "avr"), "AVR"
    )

    _, volume_text = _element(
        preferences_xml, "volume_device"
    )
    volume_device = volume_text.strip().lower()

    if volume_device not in ("tv", "avr"):
        raise ValueError("Invalid volume device")

    return room_id, {
        "name": name,
        "tv_ip": tv_ip,
        "avr_ip": avr_ip,
        "volume_device": volume_device,
    }


def _validate_document(xml):
    """Validate the Clonker XML document wrapper."""
    text = xml.strip()

    # Allow the standard XML declaration.
    if text.startswith("<?xml"):
        declaration_end = text.find("?>")
        if declaration_end < 0:
            raise ValueError("Invalid XML declaration")
        text = text[declaration_end + 2:].strip()

    opening = '<clonker version="{}">'.format(CONFIG_VERSION)

    if not text.startswith(opening):
        raise ValueError("Invalid Clonker root or version")

    if not text.endswith("</clonker>"):
        raise ValueError("Missing Clonker closing tag")

    contents = text[len(opening):-len("</clonker>")].strip()

    if not contents.startswith("<rooms>"):
        raise ValueError("Missing rooms container")

    if not contents.endswith("</rooms>"):
        raise ValueError("Missing rooms closing tag")


def validate_config(config):
    """Validate browser-submitted settings without saving."""
    if not isinstance(config, dict):
        raise ValueError("Configuration must be an object")

    rooms = config.get("rooms")
    if not isinstance(rooms, dict):
        raise ValueError("Missing rooms object")

    if set(rooms) != set(ROOM_IDS):
        raise ValueError("Incorrect room IDs")

    validated = {}

    for room_id in ROOM_IDS:
        room = rooms[room_id]

        if not isinstance(room, dict):
            raise ValueError("Invalid room: " + room_id)

        required = (
            "name", "tv_ip", "avr_ip", "volume_device"
        )

        if set(room) != set(required):
            raise ValueError("Invalid fields: " + room_id)

        if not all(isinstance(room[key], str)
                   for key in required):
            raise ValueError("Invalid field type: " + room_id)

        name = room["name"].strip()

        if not name or len(name) > MAX_ROOM_NAME_LENGTH:
            raise ValueError("Invalid room name: " + room_id)

        volume = room["volume_device"].strip().lower()

        if volume not in ("tv", "avr"):
            raise ValueError("Invalid volume device: " + room_id)

        validated[room_id] = {
            "name": name,
            "tv_ip": _validate_ip(room["tv_ip"], "TV"),
            "avr_ip": _validate_ip(room["avr_ip"], "AVR"),
            "volume_device": volume,
        }

    return {"rooms": validated}


def load():
    """Load configuration, trying backups if primary is invalid."""
    for path in (
        CONFIG_FILE,
        CONFIG_FILE + ".bak",
        CONFIG_FILE + ".bak.old",
    ):
        try:
            return _load_existing(path)
        except (ValueError, OSError) as error:
            print(
                "CLONKER CONFIG: Cannot load {}: {}".format(
                    path, error
                )
            )

    raise RuntimeError("No valid Clonker configuration found")


def _load_existing(config_path=CONFIG_FILE):
    """Load configuration, recovering an interrupted save if needed."""
    global _current

    with open(config_path, "r") as file:
        xml = file.read(MAX_CONFIG_BYTES + 1)

    if len(xml.encode("utf-8")) > MAX_CONFIG_BYTES:
        raise ValueError("Configuration XML exceeds size limit")
    _validate_document(xml)

    rooms = {}
    position = 0
    closing_tag = "</room>"

    while True:
        start = xml.find("<room ", position)

        if start < 0:
            break

        end = xml.find(closing_tag, start)

        if end < 0:
            raise ValueError("Unclosed room element")

        end += len(closing_tag)
        room_xml = xml[start:end]

        room_id, room_settings = _parse_room(room_xml)

        if room_id not in ROOM_IDS:
            raise ValueError("Unsupported room ID: " + room_id)

        if room_id in rooms:
            raise ValueError("Duplicate room ID: " + room_id)

        rooms[room_id] = room_settings
        position = end

    for room_id in ROOM_IDS:
        if room_id not in rooms:
            raise ValueError("Missing room: " + room_id)

    # Publish only after all rooms pass validation.
    _current = {"rooms": rooms}

    return _current


def current():
    """Return the currently loaded configuration."""
    return _current


def revision():
    """Return a stable identifier for the loaded configuration."""
    xml = to_xml(current())
    value = 2166136261

    for byte in xml.encode("utf-8"):
        value = ((value ^ byte) * 16777619) & 0xFFFFFFFF

    return "{:08x}".format(value)


def save(config, expected_revision):
    """Validate and persist configuration if its revision matches."""
    global _current

    if not isinstance(expected_revision, str):
        raise ValueError("Missing configuration revision")

    if _current is None:
        raise RuntimeError("Configuration not loaded")

    # Reject stale browser submissions.
    if expected_revision != revision():
        raise ValueError("Configuration revision mismatch")

    validated = validate_config(config)
    xml = to_xml(validated)

    # Never overwrite a missing or invalid primary configuration.
    if not _backup_looks_valid(CONFIG_FILE):
        raise ValueError("Primary configuration is missing or invalid")

    # Confirm the file still matches the active configuration.
    with open(CONFIG_FILE, "r") as file:
        existing_xml = file.read(MAX_CONFIG_BYTES + 1)

    if existing_xml != to_xml(_current):
        raise ValueError("Configuration changed on disk; reload required")

    # Do not write flash when nothing has changed.
    if xml == to_xml(_current):
        return False

    # Rotate backups and install the verified replacement.
    _replace_with_backup(CONFIG_FILE, xml)

    # Publish the new configuration only after successful persistence.
    _current = validated
    return True


def room(room_id):
    """Return settings for one room."""
    if _current is None:
        raise RuntimeError("Configuration not loaded")

    return _current["rooms"][room_id]


def _escape_xml(value):
    """Escape text for use in XML attributes or elements."""
    return (value.replace("&", "&amp;")
                 .replace("<", "&lt;")
                 .replace(">", "&gt;")
                 .replace('"', "&quot;")
                 .replace("'", "&apos;"))


def _unescape_xml(value):
    """Decode the XML entities used by our serializer."""
    return (value.replace("&quot;", '"')
                 .replace("&apos;", "'")
                 .replace("&lt;", "<")
                 .replace("&gt;", ">")
                 .replace("&amp;", "&"))


def to_xml(config):
    """Validate and serialize configuration to XML in memory."""
    validated = validate_config(config)

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<clonker version="{}">'.format(CONFIG_VERSION),
        '    <rooms>',
    ]

    for room_id in ROOM_IDS:
        room = validated["rooms"][room_id]

        lines.extend([
            '        <room id="{}" name="{}">'.format(
                room_id, _escape_xml(room["name"])
            ),
            '            <devices>',
            '                <tv ip="{}" />'.format(room["tv_ip"]),
            '                <avr ip="{}" />'.format(room["avr_ip"]),
            '            </devices>',
            '            <preferences>',
            '                <volume_device>{}</volume_device>'.format(
                room["volume_device"]
            ),
            '            </preferences>',
            '        </room>',
        ])

    lines.extend([
        '    </rooms>',
        '</clonker>',
    ])

    xml = "\n".join(lines) + "\n"

    if len(xml.encode("utf-8")) > MAX_CONFIG_BYTES:
        raise ValueError("Configuration XML exceeds size limit")

    return xml


def _write_verified_temp(path, contents):
    """Write a temporary file and verify its contents."""
    temp_path = path + ".tmp"

    with open(temp_path, "w") as file:
        file.write(contents)
        file.flush()

    with open(temp_path, "r") as file:
        verified = file.read()

    if verified != contents:
        raise OSError("Temporary file verification failed")

    return temp_path


def _replace_with_backup(path, contents):
    """Replace a file while retaining the previous version."""
    temp_path = _write_verified_temp(path, contents)
    backup_path = path + ".bak"

    # Preserve the previous backup until the new one is ready.
    previous_backup = backup_path + ".old"
 
    # Confirm the primary exists before changing any backups.
    os.stat(path)

    # Never rotate an invalid primary into the backup chain.
    if not _backup_looks_valid(path):
        raise ValueError("Primary configuration is invalid")

    # Move the existing backup aside, if present.
    try:
        os.rename(backup_path, previous_backup)
    except OSError as error:
        if error.errno != 2:
            raise

    # Preserve the current configuration as the new backup.
    # A missing primary is an error, not a fresh installation.
    os.rename(path, backup_path)

    # Install the verified replacement.
    os.rename(temp_path, path)

    # Verify the installed contents.
    with open(path, "r") as file:
        if file.read() != contents:
            raise OSError("Installed file verification failed")

    return path


def _backup_looks_valid(path):
    """Check basic XML integrity before restoring a backup."""
    try:
        with open(path, "r") as file:
            xml = file.read(MAX_CONFIG_BYTES + 1)

        if len(xml.encode("utf-8")) > MAX_CONFIG_BYTES:
            return False

        _validate_document(xml)

        rooms = {}
        position = 0

        while True:
            start = xml.find("<room ", position)
            if start < 0:
                break

            end = xml.find("</room>", start)
            if end < 0:
                return False

            end += len("</room>")
            room_id, settings = _parse_room(xml[start:end])

            if room_id not in ROOM_IDS or room_id in rooms:
                return False

            rooms[room_id] = settings
            position = end

        if set(rooms) != set(ROOM_IDS):
            return False

        return True

    except (OSError, ValueError):
        return False


def _recover_missing_file(path):
    """Restore a missing primary from an available backup."""
    try:
        os.stat(path)
        return False
    except OSError as error:
        if error.errno != 2:
            raise

    backup_path = path + ".bak"
    old_backup_path = backup_path + ".old"

    for candidate in (backup_path, old_backup_path):
        try:
            os.stat(candidate)
        except OSError as error:
            if error.errno == 2:
                continue
            raise

        # Never restore a backup that fails validation.
        if not _backup_looks_valid(candidate):
            print("CLONKER CONFIG: Invalid backup:", candidate)
            continue

        os.rename(candidate, path)
        return True

    return False
