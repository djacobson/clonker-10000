"""
THE CLONKER 10000
Test Kitchen Sink - Piezo Laboratory v2

Repository:
    firmware/tests/test_piezo.py

Pico:
    /tests/test_piezo.py

Hardware:
    Raspberry Pi Pico 2 W
    CircuitPython 10.3.1
    Adafruit #160 passive piezo
    GP0 -> piezo -> GND

REPL:
    exec(open("/tests/test_piezo.py").read())

Standalone hardware experiment.
Does not import or modify the Clonker application.

OBSERVED HARDWARE RESULTS
-------------------------
Initial broad frequency test:
    4000 Hz was the only clearly audible tone.

Detailed 3500-4500 Hz test:
    3500-3800 Hz: very faint
    4100-4200 Hz: loudest
    4500 Hz: starting to fade

Modulation at 4150 Hz:
    5, 15, 30, 60 and 100 Hz patterns were
    audibly distinguishable.

These are observations from one device and
test setup, not manufacturer specifications.

All tests use GP0 hardware PWM.
"""

import board
import pwmio
import time

PIN = board.GP0

CARRIER = 4150
DUTY = 32768

MIN_HZ = 100
MAX_HZ = 10000


class Piezo:
    def __init__(self):
        self.pwm = pwmio.PWMOut(
            PIN,
            frequency=CARRIER,
            duty_cycle=0,
            variable_frequency=True,
        )

    def on(self, hz=CARRIER, duty=DUTY):
        self.pwm.duty_cycle = 0
        self.pwm.frequency = max(
            MIN_HZ, min(MAX_HZ, int(hz))
        )
        self.pwm.duty_cycle = duty

    def off(self):
        self.pwm.duty_cycle = 0

    def tone(self, hz, duration, duty=DUTY):
        self.on(hz, duty)
        try:
            time.sleep(duration)
        finally:
            self.off()

    def rest(self, duration):
        self.off()
        time.sleep(duration)

    def pulse(self, on_time, off_time, count,
              hz=CARRIER, duty=DUTY):
        for _ in range(count):
            self.tone(hz, on_time, duty)
            self.rest(off_time)

    def sweep(self, start, stop, duration, steps=40):
        delay = duration / steps

        for i in range(steps + 1):
            hz = start + (stop - start) * i / steps
            self.tone(hz, delay)

    def close(self):
        self.off()
        self.pwm.deinit()


# -----------------------------------------
# CHARACTERIZATION
# -----------------------------------------

def original_scale(p):
    print("Original musical scale")

    for hz in (262, 330, 392, 523, 659, 784, 1047):
        print(hz, "Hz")
        p.tone(hz, 0.2)
        p.rest(0.05)


def broad_frequency(p):
    print("Broad frequency response")

    for hz in (
        250, 440, 880, 1500,
        2500, 3000, 3500, 4000,
        4150, 4500, 5000, 6000
    ):
        print(hz, "Hz")
        p.tone(hz, 0.6)
        p.rest(0.3)


def resonance_map(p):
    print("Resonance map: 3500-4600 Hz")

    for hz in range(3500, 4601, 100):
        print(hz, "Hz")
        p.tone(hz, 0.7)
        p.rest(0.35)


def fine_resonance(p):
    print("Fine resonance: 3900-4400 Hz")

    for hz in range(3900, 4401, 25):
        print(hz, "Hz")
        p.tone(hz, 0.35)
        p.rest(0.2)


def duty_cycle_test(p):
    print("Duty-cycle experiment at 4150 Hz")

    for percent in (5, 10, 20, 30, 40, 50):
        duty = int(65535 * percent / 100)

        print(percent, "% duty")
        p.tone(CARRIER, 0.8, duty)
        p.rest(0.4)


# -----------------------------------------
# SOUND EFFECTS
# -----------------------------------------

def clicks(p):
    print("Short resonant bursts")

    for duration in (
        0.005, 0.01, 0.02,
        0.04, 0.08, 0.15
    ):
        print("Burst:", duration, "seconds")

        for _ in range(3):
            p.tone(CARRIER, duration)
            p.rest(0.25)

        p.rest(0.3)


def double_clonk(p):
    print("Double CLONK")

    for gap in (0.04, 0.08, 0.15, 0.3):
        print("Gap:", gap)

        p.tone(CARRIER, 0.035)
        p.rest(gap)
        p.tone(CARRIER, 0.075)
        p.rest(0.7)


def rattles(p):
    print("Mechanical rattles")

    patterns = (
        (0.015, 0.025, 12),
        (0.025, 0.035, 10),
        (0.04, 0.025, 8),
        (0.01, 0.015, 20),
    )

    for on_time, off_time, count in patterns:
        p.pulse(on_time, off_time, count)
        p.rest(0.5)


def alarm(p):
    print("Resonant alarm patterns")

    p.pulse(0.15, 0.15, 4)
    p.rest(0.5)

    p.pulse(0.06, 0.06, 10)
    p.rest(0.5)

    p.pulse(0.4, 0.2, 3)


def falling_clonk(p):
    print("Descending resonant bursts")

    for start, stop in (
        (4400, 3900),
        (4300, 4000),
        (4250, 4050),
    ):
        p.sweep(start, stop, 0.18, steps=20)
        p.rest(0.45)


# -----------------------------------------
# RETRO AUDIO MISCHIEF
# -----------------------------------------

def modulation_tour(p):
    print("Amplitude modulation tour")

    for rate in (5, 15, 30, 60, 100):
        print("Modulation:", rate, "Hz")

        period = 1.0 / rate

        p.pulse(
            period / 2,
            period / 2,
            rate,
        )

        p.rest(0.5)


def envelope_test(p):
    print("Duty-cycle envelope")

    envelopes = (
        (5, 10, 20, 35, 50),
        (50, 35, 20, 10, 5),
        (5, 20, 50, 20, 5),
    )

    for envelope in envelopes:
        for percent in envelope:
            duty = int(65535 * percent / 100)
            p.tone(CARRIER, 0.055, duty)

        p.rest(0.5)


def retro_chatter(p):
    print("Retro digital chatter")

    patterns = (
        (0.02, 0.02, 15),
        (0.04, 0.015, 12),
        (0.01, 0.04, 15),
        (0.03, 0.01, 20),
    )

    for on_time, off_time, count in patterns:
        p.pulse(on_time, off_time, count)
        p.rest(0.2)


def fake_speech(p):
    print("Primitive speech-like modulation")
    print("Not actual speech synthesis")

    syllables = (
        (30, 0.25),
        (65, 0.15),
        (20, 0.35),
        (90, 0.12),
        (40, 0.3),
    )

    for rate, duration in syllables:
        count = max(1, int(rate * duration))
        period = 1.0 / rate

        p.pulse(
            period * 0.55,
            period * 0.45,
            count,
        )

        p.rest(0.08)


TESTS = {
    "1": ("Original musical scale", original_scale),
    "2": ("Broad frequency response", broad_frequency),
    "3": ("Resonance map", resonance_map),
    "4": ("Fine resonance map", fine_resonance),
    "5": ("Duty-cycle response", duty_cycle_test),

    "6": ("Short clicks", clicks),
    "7": ("Double CLONK", double_clonk),
    "8": ("Mechanical rattles", rattles),
    "9": ("Alarm patterns", alarm),
    "10": ("Descending CLONK", falling_clonk),

    "11": ("Modulation tour", modulation_tour),
    "12": ("Duty-cycle envelopes", envelope_test),
    "13": ("Retro chatter", retro_chatter),
    "14": ("Fake speech", fake_speech),
}


def menu():
    print()
    print("=" * 45)
    print("THE CLONKER 10000")
    print("PIEZO LABORATORY v2")
    print("=" * 45)

    print()
    print("CHARACTERIZATION")

    for key in ("1", "2", "3", "4", "5"):
        print(" {:>2}. {}".format(
            key, TESTS[key][0]
        ))

    print()
    print("SOUND EFFECTS")

    for key in ("6", "7", "8", "9", "10"):
        print(" {:>2}. {}".format(
            key, TESTS[key][0]
        ))

    print()
    print("RETRO AUDIO")

    for key in ("11", "12", "13", "14"):
        print(" {:>2}. {}".format(
            key, TESTS[key][0]
        ))

    print()
    print("  a. Run all sound effects (6-14)")
    print("  q. Quit")
    print()


def main():
    p = Piezo()

    try:
        while True:
            menu()

            choice = input("Select test: ").strip().lower()

            if choice == "q":
                break

            if choice == "a":
                for number in range(6, 15):
                    name, function = TESTS[str(number)]

                    print()
                    print("Running:", name)

                    function(p)
                    p.rest(0.5)

                continue

            if choice not in TESTS:
                print("Unknown selection")
                continue

            name, function = TESTS[choice]

            print()
            print("Running:", name)

            function(p)
            p.rest(0.25)

    except KeyboardInterrupt:
        print("\nInterrupted")

    finally:
        p.close()
        print("Piezo released; GP0 deinitialized")


main()
