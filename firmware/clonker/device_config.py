# The Clonker 10000
# clonker/device_config.py
#
# Initial read-only configuration prototype.
#
# Clonker Designed by David Jacobson
# GitHub: https://github.com/djacobson/clonker-10000


CONFIG_FILE = "/clonker/device_config.xml"

_current = None


def _attribute(xml, tag, name):
    """Read a quoted attribute from a simple XML opening tag."""
    start = xml.find("<" + tag + " ")
    if start < 0:
        raise ValueError("Missing XML element: " + tag)

    end = xml.find(">", start)
    if end < 0:
        raise ValueError("Incomplete XML element: " + tag)

    opening_tag = xml[start:end]
    marker = name + '="'
    position = opening_tag.find(marker)

    if position < 0:
        raise ValueError("Missing XML attribute: " + name)

    position += len(marker)
    finish = opening_tag.find('"', position)

    if finish < 0:
        raise ValueError("Unclosed XML attribute: " + name)

    return opening_tag[position:finish]


def load():
    """Load configuration from flash into memory."""
    global _current

    with open(CONFIG_FILE, "r") as file:
        xml = file.read()

    tv_ip = _attribute(xml, "tv", "ip")
    avr_ip = _attribute(xml, "avr", "ip")

    start = xml.find("<volume_device>")
    end = xml.find("</volume_device>")

    if start < 0 or end < 0:
        raise ValueError("Missing volume_device")

    start += len("<volume_device>")
    volume_device = xml[start:end].strip().lower()

    if volume_device not in ("tv", "avr"):
        raise ValueError("Invalid volume_device")

    _current = {
        "tv_ip": tv_ip,
        "avr_ip": avr_ip,
        "volume_device": volume_device,
    }

    return _current


def current():
    """Return the configuration currently held in memory."""
    return _current
