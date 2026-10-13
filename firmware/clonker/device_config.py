
# The Clonker 10000
# clonker/device_config.py
#
# Read-only, three-room XML configuration prototype.
#
# Clonker Designed by David Jacobson
# GitHub: https://github.com/djacobson/clonker-10000

CONFIG_FILE = "/clonker/device_config.xml"


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


def _parse_room(room_xml):
    """Parse one room's name, devices and preferences."""
    opening, contents = _element(room_xml, "room")

    room_id = _attribute(opening, "id")
    name = _attribute(opening, "name")

    tv_ip = _device_ip(contents, "tv")
    avr_ip = _device_ip(contents, "avr")

    _, volume_text = _element(contents, "volume_device")
    volume_device = volume_text.strip().lower()

    if not name:
        raise ValueError("Room name cannot be empty")

    if volume_device not in ("tv", "avr"):
        raise ValueError("Invalid volume device")

    return room_id, {
        "name": name,
        "tv_ip": tv_ip,
        "avr_ip": avr_ip,
        "volume_device": volume_device,
    }


def load():
    """Load all configured rooms from XML into memory."""
    global _current

    with open(CONFIG_FILE, "r") as file:
        xml = file.read()

    rooms = {}
    position = 0

    for expected_id in ROOM_IDS:
        start = xml.find("<room ", position)

        if start < 0:
            raise ValueError("Missing room: " + expected_id)

        end = xml.find("</room>", start)

        if end < 0:
            raise ValueError("Unclosed room: " + expected_id)

        room_xml = xml[start:end + len("</room>")]
        room_id, room_settings = _parse_room(room_xml)

        if room_id != expected_id:
            raise ValueError("Unexpected room ID: " + room_id)

        rooms[room_id] = room_settings
        position = end + len("</room>")

    if xml.find("<room ", position) >= 0:
        raise ValueError("More rooms than ROOM_COUNT allows")

    # Publish only after all three rooms validate.
    _current = {"rooms": rooms}

    return _current


def current():
    """Return the currently loaded configuration."""
    return _current


def room(room_id):
    """Return settings for one room."""
    if _current is None:
        raise RuntimeError("Configuration not loaded")

    return _current["rooms"][room_id]
