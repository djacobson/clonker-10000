# The Clonker 10000
# tests/test_rotary_encoder.py
#
# Clonker Designed by David Jacobson
# GitHub: https://github.com/djacobson/clonker-10000

"""Standalone rotary encoder hardware diagnostic.

Run from the CircuitPython REPL:

    exec(open("/tests/test_rotary_encoder.py").read())

Requires clonker/controls/encoders.py and pins.py.

Tests either encoder without starting Clonker or sending
network commands.

Ctrl+C ends a measurement and displays final totals.
Choose another test or quit from the menu.

Counts represent decoded steps, not raw GPIO transitions.
A zero net count does not guarantee no missed steps.
"""

import time

from clonker.controls import pins
from clonker.controls.encoders import Encoder


POLL_SECONDS = 0.001
REPORT_SECONDS = 1.0
STEPS_PER_DETENT = 4


def choose_encoder():
    print()
    print("=== CLONKER ROTARY ENCODER TEST ===")
    print("1 - Volume")
    print("2 - Custom Actions")
    print("Q - Quit")

    choice = input("Select: ").strip().lower()

    if choice == "1":
        return (
            "VOLUME",
            pins.VOLUME_ENCODER_A_PIN,
            pins.VOLUME_ENCODER_B_PIN,
        )

    if choice == "2":
        return (
            "ACTIONS",
            pins.ACTION_ENCODER_A_PIN,
            pins.ACTION_ENCODER_B_PIN,
        )

    return None


def print_counts(positive, negative):
    print(
        "Positive: {}  Negative: {}  Net: {}  Total: {}".format(
            positive,
            negative,
            positive - negative,
            positive + negative,
        )
    )


def run_test(name, pin_a, pin_b):
    if pin_a is None or pin_b is None:
        print("{} encoder GPIOs are not assigned.".format(name))
        return

    encoder = Encoder(
        name,
        pin_a,
        pin_b,
        reverse=False,
        steps_per_detent=STEPS_PER_DETENT,
    )

    positive = 0
    negative = 0

    try:
        encoder.initialize()

        print()
        print("{} encoder: GP{} / GP{}".format(
            name, pin_a, pin_b
        ))
        print("Rotate the knob in either direction.")
        print("Counters update every second.")
        print("Press Ctrl+C to finish.")
        print()

        last_report = time.monotonic()

        try:
            while True:
                step = encoder.poll()

                if step > 0:
                    positive += step
                elif step < 0:
                    negative -= step

                now = time.monotonic()

                if now - last_report >= REPORT_SECONDS:
                    print_counts(positive, negative)
                    last_report = now

                time.sleep(POLL_SECONDS)

        except KeyboardInterrupt:
            pass

    finally:
        encoder.deinit()

    print()
    print("--- {} FINAL RESULTS ---".format(name))
    print_counts(positive, negative)
    print()


def main():
    while True:
        try:
            selection = choose_encoder()
        except (KeyboardInterrupt, EOFError):
            print("\nTest finished.")
            return

        if selection is None:
            print("Exiting encoder test.")
            return

        try:
            run_test(*selection)
        except Exception as exc:
            print("Encoder test error: {}".format(exc))


main()
