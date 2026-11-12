"""
THE CLONKER 10000
Test Kitchen Sink - Piezo Laboratory v3

Repository: firmware/tests/test_piezo.py
Pico:       /tests/test_piezo.py

Hardware:
    Raspberry Pi Pico 2 W
    CircuitPython 10.3.1
    Adafruit #160 passive piezo
    GP0 -> piezo -> GND

REPL:
    exec(open("/tests/test_piezo.py").read())

Standalone experiment. No Clonker app imports.

Observed resonance: approximately 4150 Hz.
The results are specific to our test hardware.

v3:
    Preserve original tests 1-14.
    Add continuous sweeps and duty envelopes.
    Explore clicks, chirps, power effects,
    pitch/duty combinations, and oddities.
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

    def set(self, hz=CARRIER, percent=50):
        hz = max(MIN_HZ, min(MAX_HZ, int(hz)))
        percent = max(0, min(50, percent))

        self.pwm.frequency = hz
        self.pwm.duty_cycle = int(65535 * percent / 100)

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
        # Original v2 behavior: discrete tone steps.
        delay = duration / steps
        for i in range(steps + 1):
            hz = start + (stop - start) * i / steps
            self.tone(hz, delay)

    def glide(self, start, stop, duration,
              steps=50, percent=50):
        # v3: continuous PWM with no intentional gaps.
        delay = duration / steps
        try:
            for i in range(steps + 1):
                hz = start + (stop - start) * i / steps
                self.set(hz, percent)
                time.sleep(delay)
        finally:
            self.off()

    def envelope(self, start, peak, end,
                 rise, fall, hz=CARRIER,
                 steps=25):
        # Continuous PWM throughout rise and fall.
        try:
            for i in range(steps + 1):
                pct = start + (peak - start) * i / steps
                self.set(hz, pct)
                time.sleep(rise / steps)

            for i in range(1, steps + 1):
                pct = peak + (end - peak) * i / steps
                self.set(hz, pct)
                time.sleep(fall / steps)
        finally:
            self.off()

    def close(self):
        self.off()
        self.pwm.deinit()


# ------------------------------------------
# ORIGINAL CHARACTERIZATION - TESTS 1-5
# ------------------------------------------

def original_scale(p):
    for hz in (262, 330, 392, 523, 659, 784, 1047):
        print(hz, "Hz")
        p.tone(hz, 0.2)
        p.rest(0.05)


def broad_frequency(p):
    for hz in (
        250, 440, 880, 1500,
        2500, 3000, 3500, 4000,
        4150, 4500, 5000, 6000
    ):
        print(hz, "Hz")
        p.tone(hz, 0.6)
        p.rest(0.3)


def resonance_map(p):
    for hz in range(3500, 4601, 100):
        print(hz, "Hz")
        p.tone(hz, 0.7)
        p.rest(0.35)


def fine_resonance(p):
    for hz in range(3900, 4401, 25):
        print(hz, "Hz")
        p.tone(hz, 0.35)
        p.rest(0.2)


def duty_cycle_test(p):
    for pct in (5, 10, 20, 30, 40, 50):
        print(pct, "% duty")
        p.tone(
            CARRIER, 0.8,
            int(65535 * pct / 100)
        )
        p.rest(0.4)


# ------------------------------------------
# ORIGINAL SOUND EFFECTS - TESTS 6-10
# ------------------------------------------

def clicks(p):
    for duration in (
        0.005, 0.01, 0.02,
        0.04, 0.08, 0.15
    ):
        print("Burst:", duration)
        for _ in range(3):
            p.tone(CARRIER, duration)
            p.rest(0.25)
        p.rest(0.3)


def double_clonk(p):
    for gap in (0.04, 0.08, 0.15, 0.3):
        print("Gap:", gap)
        p.tone(CARRIER, 0.035)
        p.rest(gap)
        p.tone(CARRIER, 0.075)
        p.rest(0.7)


def rattles(p):
    for on_t, off_t, count in (
        (0.015, 0.025, 12),
        (0.025, 0.035, 10),
        (0.04, 0.025, 8),
        (0.01, 0.015, 20)
    ):
        p.pulse(on_t, off_t, count)
        p.rest(0.5)


def alarm(p):
    p.pulse(0.15, 0.15, 4)
    p.rest(0.5)
    p.pulse(0.06, 0.06, 10)
    p.rest(0.5)
    p.pulse(0.4, 0.2, 3)


def falling_clonk(p):
    for start, stop in (
        (4400, 3900),
        (4300, 4000),
        (4250, 4050)
    ):
        p.sweep(start, stop, 0.18, steps=20)
        p.rest(0.45)


# ------------------------------------------
# ORIGINAL RETRO AUDIO - TESTS 11-14
# ------------------------------------------

def modulation_tour(p):
    for rate in (5, 15, 30, 60, 100):
        print("Modulation:", rate, "Hz")
        period = 1.0 / rate
        p.pulse(period / 2, period / 2, rate)
        p.rest(0.5)


def envelope_test(p):
    for env in (
        (5, 10, 20, 35, 50),
        (50, 35, 20, 10, 5),
        (5, 20, 50, 20, 5)
    ):
        for pct in env:
            p.tone(
                CARRIER, 0.055,
                int(65535 * pct / 100)
            )
        p.rest(0.5)


def retro_chatter(p):
    for on_t, off_t, count in (
        (0.02, 0.02, 15),
        (0.04, 0.015, 12),
        (0.01, 0.04, 15),
        (0.03, 0.01, 20)
    ):
        p.pulse(on_t, off_t, count)
        p.rest(0.2)


def fake_speech(p):
    print("Rhythmic pseudo-syllables, not speech")
    for rate, duration in (
        (30, 0.25),
        (65, 0.15),
        (20, 0.35),
        (90, 0.12),
        (40, 0.3)
    ):
        count = max(1, int(rate * duration))
        period = 1.0 / rate
        p.pulse(
            period * 0.55,
            period * 0.45,
            count
        )
        p.rest(0.08)


# ------------------------------------------
# v3 - ENVELOPES AND CONTINUOUS SWEEPS
# ------------------------------------------

def long_swell(p):
    print("Smooth 3-second swell and fade")
    p.envelope(2, 50, 2, 1.5, 1.5)


def continuous_sweeps(p):
    print("Compare three uninterrupted glides")
    for start, stop in (
        (4400, 3900),
        (3900, 4400),
        (4600, 3500)
    ):
        print(start, "to", stop)
        p.glide(start, stop, 0.7)
        p.rest(0.5)


def short_confirmation(p):
    print("Four confirmation click candidates")
    for duration, pct in (
        (0.01, 50),
        (0.02, 50),
        (0.03, 20),
        (0.05, 10)
    ):
        print(duration, "seconds;", pct, "%")
        p.set(CARRIER, pct)
        time.sleep(duration)
        p.rest(0.6)


def double_confirmation(p):
    print("Two different confirmation chirps")
    p.tone(4150, 0.025)
    p.rest(0.07)
    p.tone(4150, 0.055)
    p.rest(0.7)

    p.tone(3900, 0.035)
    p.rest(0.06)
    p.tone(4300, 0.065)
    p.rest(0.7)


def power_down(p):
    print("Descending pitch plus fading duty")
    steps = 55
    try:
        for i in range(steps + 1):
            t = i / steps
            hz = 4400 - 850 * t
            pct = 50 - 48 * t
            p.set(hz, pct)
            time.sleep(0.018)
    finally:
        p.off()


def power_up(p):
    print("Ascending pitch plus growing duty")
    steps = 55
    try:
        for i in range(steps + 1):
            t = i / steps
            hz = 3550 + 850 * t
            pct = 2 + 48 * t
            p.set(hz, pct)
            time.sleep(0.018)
    finally:
        p.off()


def pitch_duty_comparison(p):
    print("Three different pitch/duty shapes")
    steps = 50

    for mode in range(3):
        print("Variation", mode + 1)
        try:
            for i in range(steps + 1):
                t = i / steps
                if mode == 0:
                    hz = 3900 + 500 * t
                    pct = 2 + 48 * t
                elif mode == 1:
                    hz = 4400 - 500 * t
                    pct = 2 + 48 * t
                else:
                    hz = 3900 + 500 * t
                    pct = 50 - 48 * t

                p.set(hz, pct)
                time.sleep(0.02)
        finally:
            p.off()
        p.rest(0.6)


def breathing_cricket(p):
    print("Three smooth breathing cycles")
    for _ in range(3):
        p.envelope(
            2, 35, 2,
            0.35, 0.5,
            steps=20
        )
        p.rest(0.2)


def tiny_laser(p):
    print("Short swept chirps")
    for duration in (0.05, 0.1, 0.2):
        print("Duration:", duration)
        p.glide(
            4500, 3700,
            duration, steps=20
        )
        p.rest(0.5)


def alien_transmission(p):
    print("Experimental pitch/duty modulation")
    steps = 100
    try:
        for i in range(steps):
            phase = i % 25
            if (i // 25) % 2 == 0:
                hz = 3900 + phase * 20
            else:
                hz = 4400 - phase * 20

            pct = 5 + phase * 1.5
            p.set(hz, pct)
            time.sleep(0.012)
    finally:
        p.off()


# ------------------------------------------
# MENU
# ------------------------------------------

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
    "15": ("Long swell and fade", long_swell),
    "16": ("Continuous frequency sweeps", continuous_sweeps),
    "17": ("Short confirmation clicks", short_confirmation),
    "18": ("Double confirmation chirps", double_confirmation),
    "19": ("Power-down effect", power_down),
    "20": ("Power-up effect", power_up),
    "21": ("Pitch/duty combinations", pitch_duty_comparison),
    "22": ("Breathing cricket", breathing_cricket),
    "23": ("Tiny laser", tiny_laser),
    "24": ("Alien transmission", alien_transmission),
}


def menu():
    print()
    print("=" * 44)
    print("THE CLONKER 10000")
    print("PIEZO LABORATORY v3")
    print("=" * 44)

    groups = (
        ("CHARACTERIZATION", range(1, 6)),
        ("ORIGINAL SOUND EFFECTS", range(6, 11)),
        ("RETRO AUDIO", range(11, 15)),
        ("NEW EXPERIMENTS", range(15, 25)),
    )

    for heading, numbers in groups:
        print()
        print(heading)
        for number in numbers:
            key = str(number)
            print(" {:>2}. {}".format(
                key, TESTS[key][0]
            ))

    print()
    print(" a. Run original sound effects (6-14)")
    print(" n. Run new experiments (15-24)")
    print(" q. Quit")
    print()


def run_test(p, key):
    name, function = TESTS[key]
    print()
    print("Running:", name)
    function(p)
    p.rest(0.25)


def main():
    p = Piezo()
    try:
        while True:
            menu()
            choice = input(
                "Select test: "
            ).strip().lower()

            if choice == "q":
                break

            if choice == "a":
                for number in range(6, 15):
                    run_test(p, str(number))
                continue

            if choice == "n":
                for number in range(15, 25):
                    run_test(p, str(number))
                continue

            if choice in TESTS:
                run_test(p, choice)
            else:
                print("Unknown selection")

    except KeyboardInterrupt:
        print("\nInterrupted")

    finally:
        p.close()
        print("Piezo released; GP0 deinitialized")


main()
