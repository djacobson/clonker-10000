# THE CLONKER 10000 -- exploratory Roku ECP volume test
# Place at /tests/test_roku_volume.py on the Pico.
# Run from REPL after stopping the Clonker main loop with Ctrl-C.
# Does not change configuration or send commands automatically.

import time
from clonker import device_config_v2 as config
from clonker.net import http_transport

ROOM_ID = "room-2"  # Sunroom
KEYS = {
    "up": "/keypress/VolumeUp",
    "down": "/keypress/VolumeDown",
    "mute": "/keypress/VolumeMute",
}


def endpoint():
    # Read the active configuration, not a hard-coded network address.
    try:
        room = config.room(ROOM_ID)
    except RuntimeError:
        config.load()
        room = config.room(ROOM_ID)
    return config.resolve_endpoint(room, "device-3")


def send(key):
    """Send one ECP keypress; inspect equipment to confirm actual effect."""
    if key not in KEYS:
        raise ValueError("Choose up, down, or mute")
    target = endpoint()
    if not target:
        raise ValueError("Sunroom Roku endpoint is blank")
    print("ROKU TEST:", key, "->", target)
    try:
        result = http_transport.send(target, "POST", KEYS[key])
        print("HTTP:", result["status"], "total_ms:", result["total_ms"])
        print("Observe actual TV/AVR behavior; HTTP success is not proof.")
        return result
    except Exception as error:
        print("ROKU TEST FAILED:", repr(error))
        raise


def burst(key="up", count=5, pause=0.15):
    """Optional paced repeated keypress test; never runs automatically."""
    if key not in ("up", "down"):
        raise ValueError("Burst supports up or down only")
    if not 1 <= count <= 10 or pause < 0.1:
        raise ValueError("Use 1-10 presses, pause >= 0.1 seconds")
    results = []
    for i in range(count):
        print("Press", i + 1, "of", count)
        results.append(send(key))
        if i + 1 < count:
            time.sleep(pause)
    return results


print("Roku ECP volume test loaded. No commands sent.")
print("Try: send('up'), send('down'), send('mute')")
print("Optional: burst('up', 5, 0.15)")
