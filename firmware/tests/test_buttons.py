# The Clonker 10000
# tests/test_buttons.py
#
# Standalone test for all 13 momentary buttons.
# Raspberry Pi Pico 2 W / CircuitPython 10.x
#
# All buttons connect GPIO to GND when pressed.
# Internal pull-ups are enabled.
#
# Does not import or start Clonker.
#
# Run from the CircuitPython REPL:
# exec(open("/tests/test_buttons.py").read())

import time
import board
import digitalio

DEBOUNCE_SECONDS = 0.03

# Button name, GPIO number
BUTTONS = (
    # System control
    ("POWER TOGGLE",   2),

    # Encoder pushbuttons
    ("VOLUME MUTE",   10),
    ("ACTION RUN",    13),

    # Navigation
    ("UP",            14),
    ("DOWN",          15),
    ("LEFT",          16),
    ("RIGHT",         19),
    ("SELECT",        20),

    # Navigation shortcuts
    ("BACK",          21),
    ("HOME",          22),

    # Playback controls
    ("SKIP BACK",     26),  # Cowbell A0
    ("PLAY/PAUSE",    27),  # Cowbell A1
    ("SKIP FORWARD",  28),  # Cowbell A2
)


def run_test():
    inputs = []
    counts = {}

    print()
    print("=== CLONKER FULL BUTTON TEST ===")
    print("Initializing %d buttons..." % len(BUTTONS))

    try:
        for name, pin_number in BUTTONS:
            pin = getattr(board, "GP{}".format(pin_number))

            gpio = digitalio.DigitalInOut(pin)
            gpio.direction = digitalio.Direction.INPUT
            gpio.pull = digitalio.Pull.UP

            state = gpio.value

            inputs.append({
                "name": name,
                "pin": pin_number,
                "gpio": gpio,
                "raw": state,
                "stable": state,
                "changed": time.monotonic(),
            })

            counts[name] = 0

            print(
                "%-15s GP%-2d  %s" %
                (
                    name,
                    pin_number,
                    "RELEASED" if state else "HELD/LOW"
                )
            )

        print()
        print("Ready! Press each button.")
        print("Each should report PRESSED and RELEASED.")
        print("Press Ctrl-C to finish and see results.")
        print()

        while True:
            now = time.monotonic()

            for item in inputs:
                raw = item["gpio"].value

                if raw != item["raw"]:
                    item["raw"] = raw
                    item["changed"] = now

                if (
                    raw != item["stable"]
                    and now - item["changed"] >= DEBOUNCE_SECONDS
                ):
                    item["stable"] = raw

                    if not raw:
                        counts[item["name"]] += 1
                        event = "PRESSED"
                    else:
                        event = "RELEASED"

                    print(
                        "%-15s GP%-2d  %-8s  count=%d" %
                        (
                            item["name"],
                            item["pin"],
                            event,
                            counts[item["name"]]
                        )
                    )

            time.sleep(0.005)

    except KeyboardInterrupt:
        print()
        print("Test stopped.")

    finally:
        for item in inputs:
            item["gpio"].deinit()

        print()
        print("=== BUTTON TEST SUMMARY ===")

        passed = 0

        for name, pin_number in BUTTONS:
            count = counts[name]

            if count > 0:
                passed += 1
                status = "TESTED"
            else:
                status = "NOT TESTED"

            print(
                "%-15s GP%-2d  presses=%-3d %s" %
                (name, pin_number, count, status)
            )

        print()
        print(
            "Buttons exercised: %d/%d" %
            (passed, len(BUTTONS))
        )
        print("GPIO resources released.")


run_test()
