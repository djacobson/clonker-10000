"""
THE CLONKER 10000 -- Test Kitchen Sink
Standalone Adafruit #160 Passive Piezo Experiments

Repository: firmware/tests/test_piezo.py
Pico path:  /tests/test_piezo.py

Hardware:
    Raspberry Pi Pico 2 W
    Adafruit #160 passive piezo buzzer
    Piezo leg 1 -> GP0
    Piezo leg 2 -> GND

Run from CircuitPython REPL:
    exec(open("/tests/test_piezo.py").read())

Stop Clonker before running. No external libraries.
Ctrl+C interrupts playback and releases GP0.
"""

import time
import board
import pwmio

PIN = board.GP0
DUTY = 32768  # 50% duty cycle


class Piezo:
    def __init__(self):
        self.pwm = pwmio.PWMOut(
            PIN,
            frequency=1000,
            duty_cycle=0,
            variable_frequency=True,
        )

    def tone(self, hz, seconds, duty=DUTY):
        hz = max(100, min(10000, int(hz)))

        self.pwm.duty_cycle = 0
        self.pwm.frequency = hz
        self.pwm.duty_cycle = duty

        try:
            time.sleep(max(0, seconds))
        finally:
            self.pwm.duty_cycle = 0

    def rest(self, seconds):
        self.pwm.duty_cycle = 0
        time.sleep(seconds)

    def sweep(self, start, stop, seconds, steps=60):
        delay = seconds / steps

        for i in range(steps + 1):
            hz = start + (stop - start) * i / steps
            self.tone(hz, delay)

    def close(self):
        self.pwm.duty_cycle = 0
        self.pwm.deinit()


def scale(p):
    for hz in (262, 330, 392, 523, 659, 784, 1047):
        p.tone(hz, 0.16)
        p.rest(0.035)


def sweeps(p):
    p.sweep(250, 3000, 0.9)
    p.rest(0.2)
    p.sweep(3000, 250, 0.9)


def chirps(p):
    for _ in range(3):
        p.sweep(1100, 2300, 0.11, steps=12)
        p.rest(0.12)

    p.rest(0.3)

    for _ in range(2):
        p.tone(880, 0.08)
        p.rest(0.06)
        p.tone(1320, 0.1)
        p.rest(0.2)


def alarm(p):
    for _ in range(4):
        p.tone(700, 0.13)
        p.rest(0.07)
        p.tone(1100, 0.13)
        p.rest(0.16)


def clonk(p):
    # Descending pitched thunk.
    # A piezo cannot reproduce genuine bass.

    for start in (2400, 1700, 1000):
        p.sweep(
            start,
            max(150, start // 4),
            0.095,
            steps=15,
        )
        p.rest(0.045)


def retro_voice(p):
    # Experimental PC-speaker-style buzzing.
    # This is NOT actual speech synthesis.

    for base in (180, 230, 195, 260, 170):
        for i in range(12):
            hz = base * (2 if i % 3 == 0 else 1)
            p.tone(hz, 0.014)
            p.rest(0.004)

        p.rest(0.07)


def frequency_test(p):
    frequencies = (
        150, 250, 440, 880, 1500,
        2500, 4000, 6000, 8000,
    )

    for hz in frequencies:
        print("  {} Hz".format(hz))
        p.tone(hz, 0.35)
        p.rest(0.15)


TESTS = {
    "1": ("Ascending scale", scale),
    "2": ("Up/down sweeps", sweeps),
    "3": ("Chirps", chirps),
    "4": ("Two-tone alarm", alarm),
    "5": ("Mechanical-ish CLONK", clonk),
    "6": ("Retro voice-like buzz", retro_voice),
    "7": ("Frequency response tour", frequency_test),
}


def main():
    print()
    print("THE CLONKER 10000 -- PIEZO KITCHEN SINK")
    print("Adafruit #160 | GP0 + GND")
    print()

    piezo = Piezo()

    try:
        while True:
            print()
            print("Choose an experiment:")

            for key in sorted(TESTS):
                print(
                    "  {}. {}".format(
                        key, TESTS[key][0]
                    )
                )

            print("  q. Quit")

            choice = input("> ").strip().lower()

            if choice in ("q", "quit", "exit"):
                break

            if choice not in TESTS:
                print("Unknown choice.")
                continue

            name, function = TESTS[choice]

            print("Playing: {}".format(name))
            function(piezo)
            print("Done.")

    except KeyboardInterrupt:
        print("\nInterrupted.")

    finally:
        piezo.close()
        print("GP0 released.")


# Execute immediately when run using exec(open(...).read()).
main()
