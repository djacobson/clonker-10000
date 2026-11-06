# The Clonker 10000
# tests/test_oled.py
#
# Standalone SH1106 OLED hardware experiments.
# Pico 2 W / CircuitPython 10.x
#
# Wiring:
# GP4       -> SDA (yellow)
# GP5       -> SCK (green)
# 3V3(OUT)  -> VCC (red)
# GND       -> GND (black)
#
# SH1106: 128x64, expected I2C address 0x3C
#
# Run from the CircuitPython REPL:
# exec(open("/tests/test_oled.py").read())
#
# Does not import Clonker or use its GPIO poller.

import board
import busio
import time

ADDRESS = 0x3C
WIDTH = 128
HEIGHT = 64
PAGES = HEIGHT // 8
COLUMN_OFFSET = 2

i2c = busio.I2C(
    board.GP5,
    board.GP4,
    frequency=400000
)


def transaction(payload):
    while not i2c.try_lock():
        pass
    try:
        i2c.writeto(ADDRESS, payload)
    finally:
        i2c.unlock()


def command(*values):
    transaction(bytes((0x00,)) + bytes(values))


def data(values):
    # Small transfers for compatibility with I2C buffers.
    for pos in range(0, len(values), 16):
        transaction(
            bytes((0x40,)) + bytes(values[pos:pos + 16])
        )


def scan():
    while not i2c.try_lock():
        pass
    try:
        addresses = i2c.scan()
    finally:
        i2c.unlock()

    print("I2C addresses:", [hex(x) for x in addresses])
    if ADDRESS not in addresses:
        raise RuntimeError("SH1106 not found at 0x3C")


def initialize():
    command(0xAE)        # Display off
    command(0xD5, 0x80)  # Clock divide / oscillator
    command(0xA8, 0x3F)  # Multiplex: 64 rows
    command(0xD3, 0x00)  # Display offset
    command(0x40)        # Start line 0
    command(0xAD, 0x8B)  # Enable charge pump / DC-DC
    command(0xA1)        # Segment remap
    command(0xC8)        # COM scan direction
    command(0xDA, 0x12)  # COM pin configuration
    command(0x81, 0x7F)  # Contrast
    command(0xD9, 0x22)  # Precharge
    command(0xDB, 0x35)  # VCOM level
    command(0xA4)        # Display RAM content
    command(0xA6)        # Normal (not inverted)
    command(0xAF)        # Display on


def write_page(page, pixels):
    col = COLUMN_OFFSET
    command(
        0xB0 | page,
        0x00 | (col & 0x0F),
        0x10 | (col >> 4)
    )
    data(pixels)


def clear():
    blank = bytes(WIDTH)
    for page in range(PAGES):
        write_page(page, blank)


def pattern():
    # Distinctive stationary image for persistence tests.
    start = time.monotonic_ns()
    for page in range(PAGES):
        pixels = bytearray(WIDTH)
        for x in range(WIDTH):
            if x < 3 or x >= 125:
                pixels[x] = 0xFF
            elif page == 0 or page == 7:
                pixels[x] = 0xFF
            elif (x // 8 + page) % 2 == 0:
                pixels[x] = 0x18
        write_page(page, pixels)

    elapsed = (time.monotonic_ns() - start) / 1000000
    print("Full-screen transfer: %.2f ms" % elapsed)


def contrast(level):
    command(0x81, level)


def restore():
    command(0x40)  # Start line zero
    command(0xA4)  # Follow display RAM
    command(0xA6)  # Normal image
    contrast(0x7F)
    command(0xAF)


def test_persistence():
    pattern()
    print("No more OLED commands for 10 seconds.")
    time.sleep(10)
    print("Did the image remain unchanged?")


def test_contrast():
    pattern()
    for level in (255, 128, 32, 0, 128):
        print("Contrast:", level)
        contrast(level)
        time.sleep(2)
    restore()


def test_invert():
    pattern()
    print("Inverted for 3 seconds")
    command(0xA7)
    time.sleep(3)
    command(0xA6)


def test_blank():
    pattern()
    print("Display off for 3 seconds")
    command(0xAE)
    time.sleep(3)
    command(0xAF)
    print("RAM should still be visible.")


def test_all_on():
    pattern()
    print("All pixels forced on for 3 seconds")
    command(0xA5)
    time.sleep(3)
    command(0xA4)
    print("Original RAM image restored.")


def test_start_line():
    pattern()
    print("Changing vertical start line once.")
    command(0x50)  # Start line 16
    print("Watching for 10 seconds with no commands.")
    time.sleep(10)
    print("Did it stay stationary or move?")
    command(0x40)


def test_software_scroll():
    pattern()
    print("Software-driven vertical scroll.")
    for offset in range(64):
        command(0x40 | offset)
        time.sleep(0.04)
    command(0x40)
    print("This requires repeated Pico commands.")


def test_command_speed():
    start = time.monotonic_ns()
    for _ in range(100):
        command(0xA6)
    elapsed = (time.monotonic_ns() - start) / 1000000
    print("100 one-byte commands: %.2f ms" % elapsed)
    print("Average: %.3f ms" % (elapsed / 100))


def menu():
    tests = {
        "1": test_persistence,
        "2": test_contrast,
        "3": test_invert,
        "4": test_blank,
        "5": test_all_on,
        "6": test_start_line,
        "7": test_software_scroll,
        "8": test_command_speed,
        "9": pattern,
        "0": clear,
    }

    while True:
        print()
        print("=== CLONKER OLED LAB ===")
        print("1  Persistence (10 seconds)")
        print("2  Contrast levels")
        print("3  Inversion")
        print("4  Display off/on")
        print("5  Force all pixels on")
        print("6  Start-line autonomy test")
        print("7  Software scroll comparison")
        print("8  Command timing")
        print("9  Draw test pattern")
        print("0  Clear screen")
        print("q  Quit")
        choice = input("Test: ").strip().lower()

        if choice == "q":
            restore()
            clear()
            break

        fn = tests.get(choice)
        if fn is None:
            print("Unknown selection")
            continue

        try:
            fn()
        except Exception as exc:
            print("Test error:", repr(exc))
            restore()


try:
    scan()
    initialize()
    clear()
    pattern()
    menu()
finally:
    try:
        restore()
        clear()
    except Exception:
        pass
    i2c.deinit()
    print("OLED test finished.")
