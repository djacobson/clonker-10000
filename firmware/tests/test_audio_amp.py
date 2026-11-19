"""
THE CLONKER 10000
Audio Amplifier Laboratory v4 - Software Lifecycle

Repository: firmware/tests/test_audio_amp.py
Pico:       /tests/test_audio_amp.py

Hardware:
    Raspberry Pi Pico 2 W
    CircuitPython 10.3.1
    Adafruit STEMMA Audio Amp #5647
    23 mm, 8 ohm / 1 W speaker

Wiring:
    GP0 -> amplifier signal
    3V3 -> amplifier power
    GND -> amplifier ground
    Speaker -> amplifier speaker terminals

REPL:
    exec(open("/tests/test_audio_amp.py").read())

Standalone experiment. No Clonker app imports.

v1-v2:
    Hello World, tones, sweeps, glides,
    sound effects, volume and duration.

v3:
    Sine, triangle, square, sawtooth.
    Waveform comparisons and selection.

v4:
    Explicit audio initialization/release.
    Cold initialization and playback test.
    Warm idle/playback test.
    Repeated start/stop/restart test.
    Monotonic timing and memory reporting.

Notes:
    Releasing PWMAudioOut does NOT electrically
    shut down the external amplifier.

    Timing includes CircuitPython overhead.
    Playback time includes generated sound duration.

    Software volume is peak waveform amplitude,
    not calibrated amplifier power.
"""

import board
import time
import math
import array
import gc
import audiocore
import audiopwmio


# --------------------------------------------------
# Configuration
# --------------------------------------------------

PIN = board.GP0
SAMPLE_RATE = 16000

DEFAULT_VOLUME = 20
DEFAULT_DURATION = 750

DEFAULT_COMPARE_VOLUME = 20
DEFAULT_COMPARE_FREQUENCY = 800

MIN_FREQUENCY = 100
MAX_FREQUENCY = 4000

FADE_MS = 15
MAX_SAMPLES = 16000

WAVEFORMS = (
    "sine",
    "triangle",
    "square",
    "sawtooth",
)

LIFECYCLE_CYCLES = 5
LIFECYCLE_IDLE_MS = 500
LIFECYCLE_VOLUME = 30


# --------------------------------------------------
# Utilities
# --------------------------------------------------

def now_ns():
    return time.monotonic_ns()


def elapsed_ms(start_ns):
    return (now_ns() - start_ns) / 1000000


def memory_free():
    gc.collect()
    return gc.mem_free()


def ask_int(prompt, default, minimum, maximum):
    while True:
        response = input(
            "{} [{}]: ".format(prompt, default)
        ).strip()

        if not response:
            return default

        try:
            value = int(response)
        except ValueError:
            print("Enter a whole number.")
            continue

        if minimum <= value <= maximum:
            return value

        print("Valid range:", minimum, "to", maximum)


def waveform_value(kind, phase):
    cycle = (phase / (2 * math.pi)) % 1.0

    if kind == "sine":
        return math.sin(phase)

    if kind == "triangle":
        return 1.0 - 4.0 * abs(cycle - 0.5)

    if kind == "square":
        return 1.0 if cycle < 0.5 else -1.0

    if kind == "sawtooth":
        return 2.0 * cycle - 1.0

    raise ValueError("Unknown waveform: " + kind)


# --------------------------------------------------
# Audio Laboratory
# --------------------------------------------------

class AudioLab:

    def __init__(self):
        self.volume = DEFAULT_VOLUME
        self.duration = DEFAULT_DURATION
        self.compare_volume = DEFAULT_COMPARE_VOLUME
        self.compare_frequency = DEFAULT_COMPARE_FREQUENCY
        self.waveform = "sine"

        # Deliberately lazy in v4.
        self.audio = None

    # ----------------------------------------------
    # Audio hardware lifecycle
    # ----------------------------------------------

    def initialize_audio(self):
        if self.audio is not None:
            return 0.0

        start = now_ns()
        self.audio = audiopwmio.PWMAudioOut(PIN)
        return elapsed_ms(start)

    def release_audio(self):
        if self.audio is None:
            return 0.0

        start = now_ns()

        try:
            self.audio.stop()
        finally:
            self.audio.deinit()
            self.audio = None

        return elapsed_ms(start)

    def close(self):
        self.release_audio()

    # ----------------------------------------------
    # PCM sample generation
    # ----------------------------------------------

    def make_samples(
        self,
        frequencies,
        duration_ms,
        volume=None,
        fade=True,
        waveform="sine"
    ):
        if volume is None:
            volume = self.volume

        volume = max(0, min(100, volume))

        count = max(
            1,
            int(SAMPLE_RATE * duration_ms / 1000)
        )

        if count > MAX_SAMPLES:
            raise ValueError(
                "Sound too long for sample buffer"
            )

        if isinstance(frequencies, tuple):
            start_hz, end_hz = frequencies
        else:
            start_hz = frequencies
            end_hz = frequencies

        start_hz = max(
            MIN_FREQUENCY,
            min(MAX_FREQUENCY, start_hz)
        )

        end_hz = max(
            MIN_FREQUENCY,
            min(MAX_FREQUENCY, end_hz)
        )

        samples = array.array("H")
        amplitude = 32767 * volume / 100

        fade_count = min(
            int(SAMPLE_RATE * FADE_MS / 1000),
            count // 2
        )

        phase = 0.0

        for i in range(count):
            progress = (
                i / (count - 1)
                if count > 1 else 0
            )

            frequency = (
                start_hz +
                (end_hz - start_hz) * progress
            )

            phase += (
                2 * math.pi *
                frequency / SAMPLE_RATE
            )

            envelope = 1.0

            if fade and fade_count:
                if i < fade_count:
                    envelope = i / fade_count
                elif i >= count - fade_count:
                    envelope = (
                        (count - 1 - i) /
                        fade_count
                    )

            shape = waveform_value(waveform, phase)

            value = 32768 + int(
                amplitude * envelope * shape
            )

            samples.append(
                max(0, min(65535, value))
            )

        return samples

    def play(
        self,
        frequencies,
        duration_ms=None,
        volume=None,
        fade=True,
        waveform="sine"
    ):
        if duration_ms is None:
            duration_ms = self.duration

        # Generate first, then initialize hardware.
        samples = self.make_samples(
            frequencies,
            duration_ms,
            volume,
            fade,
            waveform
        )

        sample = audiocore.RawSample(
            samples,
            sample_rate=SAMPLE_RATE
        )

        self.initialize_audio()

        try:
            self.audio.play(sample)

            while self.audio.playing:
                time.sleep(0.01)

        finally:
            # Stop playback, but retain audio hardware.
            self.audio.stop()

        del sample
        del samples
        gc.collect()

    def pause(self, ms=200):
        time.sleep(ms / 1000)

    # ----------------------------------------------
    # Original tests 1-9
    # ----------------------------------------------

    def tone(self, hz, duration=None):
        print(
            "Tone:", hz,
            "Hz | Volume:", self.volume,
            "% | Duration:",
            duration or self.duration, "ms"
        )
        self.play(hz, duration)

    def hello_world(self):
        print("Hello World: 440 / 660 / 880 Hz")
        for hz in (440, 660, 880):
            self.tone(hz)
            self.pause(250)

    def stepped_sweep(self, reverse=False):
        frequencies = (
            200, 300, 400, 500,
            600, 700, 800, 900,
            1000, 1200, 1500,
            2000, 3000, 4000
        )

        if reverse:
            frequencies = tuple(reversed(frequencies))

        print("Stepped frequency sweep")

        for hz in frequencies:
            self.tone(hz)
            self.pause(150)

    def glide(self, start_hz, end_hz, duration=750):
        print("Glide:", start_hz, "->", end_hz, "Hz")
        self.play((start_hz, end_hz), duration)

    def chirps(self):
        print("Three chirps")
        for _ in range(3):
            self.glide(700, 1600, 150)
            self.pause(150)

    def confirmation(self, volume=None):
        print("Confirmation effect")
        self.play(700, 120, volume=volume)
        self.pause(80)
        self.play(1050, 180, volume=volume)

    def warning(self):
        print("Warning effect")
        for _ in range(3):
            self.play(450, 250)
            self.pause(120)

    def custom_tone(self):
        hz = ask_int(
            "Frequency Hz", 880,
            MIN_FREQUENCY, MAX_FREQUENCY
        )
        self.tone(hz)

    # ----------------------------------------------
    # Waveform tests 10-14
    # ----------------------------------------------

    def compare_waveforms(self):
        print(
            "Waveform comparison:",
            self.compare_frequency, "Hz |",
            self.compare_volume, "%"
        )

        for kind in WAVEFORMS:
            print("Playing:", kind)
            self.play(
                self.compare_frequency,
                750,
                volume=self.compare_volume,
                waveform=kind
            )
            self.pause(350)

        print("Comparison complete.")

    def select_waveform(self):
        for i, kind in enumerate(WAVEFORMS):
            print(i + 1, kind)

        choice = ask_int(
            "Waveform number",
            WAVEFORMS.index(self.waveform) + 1,
            1, len(WAVEFORMS)
        )

        self.waveform = WAVEFORMS[choice - 1]
        print("Selected:", self.waveform)

    def waveform_tone(self):
        print(
            self.waveform,
            self.compare_frequency, "Hz",
            self.compare_volume, "%"
        )

        self.play(
            self.compare_frequency,
            self.duration,
            volume=self.compare_volume,
            waveform=self.waveform
        )

    def waveform_glide(self):
        print(
            self.waveform,
            "glide 300 -> 1500 Hz"
        )

        self.play(
            (300, 1500),
            750,
            volume=self.compare_volume,
            waveform=self.waveform
        )

    # ----------------------------------------------
    # v4 lifecycle tests 15-17
    # ----------------------------------------------

    def lifecycle_confirmation(self):
        # Fixed level for consistent comparisons.
        self.confirmation(volume=LIFECYCLE_VOLUME)

    def cold_start_test(self):
        print()
        print("TEST 15: COLD START")
        print("Releasing audio output...")

        self.release_audio()
        self.pause(LIFECYCLE_IDLE_MS)

        free_before = memory_free()

        init_ms = self.initialize_audio()
        free_initialized = memory_free()

        print(
            "Initialization: {:.3f} ms".format(
                init_ms
            )
        )

        print("Playing confirmation...")
        self.lifecycle_confirmation()

        release_ms = self.release_audio()
        free_after = memory_free()

        print(
            "Release: {:.3f} ms".format(
                release_ms
            )
        )

        print("Free memory before:", free_before)
        print(
            "Free memory initialized:",
            free_initialized
        )
        print("Free memory after:", free_after)
        print("Cold start complete.")

    def warm_idle_test(self):
        print()
        print("TEST 16: WARM IDLE")
        print("Audio remains initialized.")

        self.release_audio()

        init_ms = self.initialize_audio()
        print(
            "Initial setup: {:.3f} ms".format(
                init_ms
            )
        )

        try:
            for cycle in range(1, 4):
                print(
                    "Warm playback",
                    cycle,
                    "of 3"
                )

                start = now_ns()
                self.lifecycle_confirmation()

                print(
                    "Confirmation elapsed:"
                    " {:.1f} ms".format(
                        elapsed_ms(start)
                    )
                )

                if cycle < 3:
                    print(
                        "Idle:",
                        LIFECYCLE_IDLE_MS,
                        "ms"
                    )
                    self.pause(LIFECYCLE_IDLE_MS)

        finally:
            self.release_audio()

        print("Warm idle test complete.")

    def restart_test(self):
        print()
        print("TEST 17: REPEATED RESTART")
        print(
            "Cycles:",
            LIFECYCLE_CYCLES
        )

        self.release_audio()
        baseline = memory_free()

        init_times = []
        release_times = []

        try:
            for cycle in range(
                1, LIFECYCLE_CYCLES + 1
            ):
                print()
                print(
                    "Cycle",
                    cycle,
                    "of",
                    LIFECYCLE_CYCLES
                )

                init_ms = self.initialize_audio()
                init_times.append(init_ms)

                print(
                    " Init: {:.3f} ms".format(
                        init_ms
                    )
                )

                self.lifecycle_confirmation()

                release_ms = self.release_audio()
                release_times.append(release_ms)

                print(
                    " Release: {:.3f} ms".format(
                        release_ms
                    )
                )

                print(
                    " Free memory:",
                    memory_free()
                )

                if cycle < LIFECYCLE_CYCLES:
                    self.pause(LIFECYCLE_IDLE_MS)

        finally:
            self.release_audio()

        final_memory = memory_free()

        print()
        print("RESTART SUMMARY")
        print(
            "Average initialization:"
            " {:.3f} ms".format(
                sum(init_times) / len(init_times)
            )
        )
        print(
            "Average release:"
            " {:.3f} ms".format(
                sum(release_times) / len(release_times)
            )
        )

        print("Baseline free memory:", baseline)
        print("Final free memory:", final_memory)
        print(
            "Difference:",
            final_memory - baseline,
            "bytes"
        )

        print("Restart test complete.")

    # ----------------------------------------------
    # Settings
    # ----------------------------------------------

    def set_volume(self):
        self.volume = ask_int(
            "Original-test volume %",
            self.volume, 0, 100
        )

    def set_duration(self):
        self.duration = ask_int(
            "Tone duration ms",
            self.duration, 25, 1000
        )

    def set_compare_frequency(self):
        self.compare_frequency = ask_int(
            "Comparison frequency Hz",
            self.compare_frequency,
            MIN_FREQUENCY, MAX_FREQUENCY
        )

    def set_compare_volume(self):
        self.compare_volume = ask_int(
            "Comparison amplitude %",
            self.compare_volume, 0, 50
        )


# --------------------------------------------------
# Menu
# --------------------------------------------------

def show_menu(lab):
    print()
    print("=" * 42)
    print("THE CLONKER 10000")
    print("AUDIO LABORATORY v4")
    print("=" * 42)

    print(
        "Sine: {}% | Duration: {} ms".format(
            lab.volume, lab.duration
        )
    )
    print(
        "Waveform: {} | {} Hz | {}%".format(
            lab.waveform,
            lab.compare_frequency,
            lab.compare_volume
        )
    )
    print(
        "Audio output:",
        "INITIALIZED"
        if lab.audio is not None
        else "RELEASED"
    )

    print()
    print("ORIGINAL TONES")
    print(" 1  Hello World (440/660/880)")
    print(" 2  Custom sine frequency")
    print(" 3  Stepped sweep ascending")
    print(" 4  Stepped sweep descending")

    print()
    print("GLIDES")
    print(" 5  Ascending sine glide")
    print(" 6  Descending sine glide")

    print()
    print("SOUND EFFECTS")
    print(" 7  Three sine chirps")
    print(" 8  Confirmation")
    print(" 9  Warning")

    print()
    print("WAVEFORM LAB")
    print("10  Compare four waveforms")
    print("11  Select waveform")
    print("12  Selected-waveform tone")
    print("13  Selected-waveform glide")
    print("14  Repeat waveform comparison")

    print()
    print("SOFTWARE LIFECYCLE")
    print("15  Cold start / release")
    print("16  Warm idle / playback")
    print("17  Repeated restart (5 cycles)")

    print()
    print("SETTINGS")
    print(" v  Set original sine-test volume")
    print(" d  Set tone duration")
    print(" f  Set waveform frequency")
    print(" a  Set waveform amplitude")
    print(" m  Show menu")
    print(" q  Quit")
    print()


# --------------------------------------------------
# Main
# --------------------------------------------------

def main():
    lab = AudioLab()

    try:
        print()
        print("Audio Laboratory v4 ready.")
        print("Output: GP0")
        print("Sample rate:", SAMPLE_RATE)
        print("Audio hardware starts on demand.")

        show_menu(lab)

        while True:
            choice = input(
                "Audio Lab> "
            ).strip().lower()

            try:
                if choice == "1":
                    lab.hello_world()

                elif choice == "2":
                    lab.custom_tone()

                elif choice == "3":
                    lab.stepped_sweep()

                elif choice == "4":
                    lab.stepped_sweep(reverse=True)

                elif choice == "5":
                    lab.glide(300, 1500)

                elif choice == "6":
                    lab.glide(1500, 300)

                elif choice == "7":
                    lab.chirps()

                elif choice == "8":
                    lab.confirmation()

                elif choice == "9":
                    lab.warning()

                elif choice in ("10", "14"):
                    lab.compare_waveforms()

                elif choice == "11":
                    lab.select_waveform()

                elif choice == "12":
                    lab.waveform_tone()

                elif choice == "13":
                    lab.waveform_glide()

                elif choice == "15":
                    lab.cold_start_test()

                elif choice == "16":
                    lab.warm_idle_test()

                elif choice == "17":
                    lab.restart_test()

                elif choice == "v":
                    lab.set_volume()

                elif choice == "d":
                    lab.set_duration()

                elif choice == "f":
                    lab.set_compare_frequency()

                elif choice == "a":
                    lab.set_compare_volume()

                elif choice == "m":
                    show_menu(lab)

                elif choice == "q":
                    print("Leaving audio laboratory.")
                    break

                elif choice:
                    print(
                        "Unknown command. "
                        "Enter m for menu."
                    )

            except ValueError as error:
                print("Test error:", error)

    except KeyboardInterrupt:
        print()
        print("Interrupted.")

    finally:
        lab.close()
        print("Audio output released.")


main()
