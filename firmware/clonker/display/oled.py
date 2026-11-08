# The Clonker 10000
# clonker/display/oled.py
#
# Clonker Designed by David Jacobson
# GitHub: https://github.com/djacobson/clonker-10000

"""Small SH1106 display driver for the Custom Action encoder experiment.

128x64 SH1106 at 0x3C, GP5 SCL / GP4 SDA, 400 kHz.
No third-party display libraries or action queue involvement.

set_count() is cheap: it records the latest value and activity time.
poll() performs rate-limited I2C updates and idle display-off.
"""

import time
import board
import busio

ADDRESS = 0x3C
WIDTH = 128
COLUMN_OFFSET = 2
IDLE_TIMEOUT = 15.0
REFRESH_INTERVAL = 0.10

# Each digit is five columns, with a blank column added by the renderer.
_FONT = {
    "0": (0x3E, 0x51, 0x49, 0x45, 0x3E),
    "1": (0x00, 0x42, 0x7F, 0x40, 0x00),
    "2": (0x42, 0x61, 0x51, 0x49, 0x46),
    "3": (0x21, 0x41, 0x45, 0x4B, 0x31),
    "4": (0x18, 0x14, 0x12, 0x7F, 0x10),
    "5": (0x27, 0x45, 0x45, 0x45, 0x39),
    "6": (0x3C, 0x4A, 0x49, 0x49, 0x30),
    "7": (0x01, 0x71, 0x09, 0x05, 0x03),
    "8": (0x36, 0x49, 0x49, 0x49, 0x36),
    "9": (0x06, 0x49, 0x49, 0x29, 0x1E),
    "-": (0x08, 0x08, 0x08, 0x08, 0x08),
    "+": (0x08, 0x08, 0x3E, 0x08, 0x08),
}

_i2c = None
_awake = False
_count = 0
_dirty = False
_last_activity = 0.0
_last_refresh = 0.0
# Successful screen updates since module initialization.
_refresh_count = [0]


def _write(payload):
    # Bus is owned by this module; avoid an infinite lock wait.
    if not _i2c.try_lock():
        return False
    try:
        _i2c.writeto(ADDRESS, payload)
    finally:
        _i2c.unlock()
    return True


def _command(*values):
    return _write(bytes((0x00,)) + bytes(values))


def _page(page, pixels):
    col = COLUMN_OFFSET
    if not _command(0xB0 | page, col & 0x0F, 0x10 | (col >> 4)):
        return False
    for pos in range(0, len(pixels), 16):
        if not _write(bytes((0x40,)) + pixels[pos:pos + 16]):
            return False
    return True


def _render(value):
    # Two enlarged pages (16 pixels high) in the center of the display.
    # Scale the 5x7 font by 2 in both directions.
    text = ("+" if value >= 0 else "-") + str(abs(value))
    text = text[-10:]  # Bound rendering work for unusual counter values.
    upper = bytearray(WIDTH)
    lower = bytearray(WIDTH)
    char_width = 12
    x = max(0, (WIDTH - len(text) * char_width) // 2)
    for ch in text:
        glyph = _FONT.get(ch, _FONT["0"])
        for bits in glyph:
            if x + 1 >= WIDTH:
                break
            top = 0
            bottom = 0
            for y in range(7):
                if bits & (1 << y):
                    for dy in (0, 1):
                        yy = y * 2 + dy
                        if yy < 8:
                            top |= 1 << yy
                        else:
                            bottom |= 1 << (yy - 8)
            upper[x] = upper[x + 1] = top
            lower[x] = lower[x + 1] = bottom
            x += 2
        x += 2  # Character spacing.
    return upper, lower


def initialize():
    """Initialize the display and leave it blank and asleep."""
    global _i2c, _awake, _dirty, _last_activity, _last_refresh
    if _i2c is not None:
        return True
    bus = busio.I2C(board.GP5, board.GP4, frequency=400000)
    _i2c = bus
    try:
        # Same initialization commands proven in firmware/tests/test_oled.py.
        for values in (
            (0xAE,), (0xD5, 0x80), (0xA8, 0x3F),
            (0xD3, 0x00), (0x40,), (0xAD, 0x8B),
            (0xA1,), (0xC8,), (0xDA, 0x12),
            (0x81, 0x7F), (0xD9, 0x22), (0xDB, 0x35),
            (0xA4,), (0xA6,),
        ):
            if not _command(*values):
                raise RuntimeError("OLED I2C bus busy during initialization")
        blank = bytes(WIDTH)
        for page in range(8):
            if not _page(page, blank):
                raise RuntimeError("OLED I2C bus busy during clear")
        _command(0xAE)
        _awake = False
        _dirty = False
        _last_activity = time.monotonic()
        _last_refresh = 0.0
        return True
    except Exception:
        bus.deinit()
        _i2c = None
        raise


def set_count(value):
    """Record a changed counter without performing any I2C work."""
    global _count, _dirty, _last_activity
    if _i2c is None:
        return
    if value != _count or not _awake:
        _count = value
        _dirty = True
        _last_activity = time.monotonic()


def poll():
    """Do at most one partial refresh, or one display-off command."""
    global _awake, _dirty, _last_refresh
    if _i2c is None:
        return
    now = time.monotonic()
    if _awake and now - _last_activity >= IDLE_TIMEOUT:
        if _command(0xAE):
            _awake = False
        return
    if not _dirty or now - _last_refresh < REFRESH_INTERVAL:
        return
    upper, lower = _render(_count)
    if not _page(3, upper) or not _page(4, lower):
        return
    if not _awake:
        if not _command(0xAF):
            return
        _awake = True
    _dirty = False
    _refresh_count[0] += 1
    _last_refresh = time.monotonic()


def get_refresh_count():
    """Return the cumulative number of successful screen refreshes."""
    return _refresh_count


def close():
    """Switch off the panel and release the I2C peripheral."""
    global _i2c, _awake, _dirty
    if _i2c is None:
        return
    try:
        _command(0xAE)
    finally:
        _i2c.deinit()
        _i2c = None
        _awake = False
        _dirty = False
