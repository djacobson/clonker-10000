"""
THE CLONKER 10000
Audio Amplifier Laboratory v3 - Beyond the Beep!

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
    Three-tone Hello World
    Adjustable volume and duration
    Individual tones and frequency sweeps
    Continuous glides and simple effects
    Fade-in/fade-out

v3:
    Sine, triangle, square, sawtooth waveforms
    Side-by-side waveform comparison
    Adjustable comparison frequency and volume
    Selected-waveform custom tone and glide
    Preserve original tests 1-9 as sine waves

Listening notes:
    Speaker produces smooth tones at 50-70%
    inside the closed foam Clonker case.
    Loose speaker contact with hard surfaces
    can produce mechanical buzzing.

No production Clonker app imports.
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

# Independent settings for richer waveforms.
DEFAULT_COMPARE_VOLUME = 20
DEFAULT_COMPARE_FREQUENCY = 800

MIN_FREQUENCY = 100
MAX_FREQUENCY = 4000

FADE_MS = 15

# 1 second maximum at 16 kHz.
MAX_SAMPLES = 16000

WAVEFORMS = (
    "sine",
    "triangle",
    "square",
    "sawtooth",
)


# --------------------------------------------------
# Waveform generation
# --------------------------------------------------

def waveform_value(kind, phase):
    """
    Return a waveform value from -1.0 to +1.0.

    phase is measured in radians and may grow
    continuously across sample boundaries.
    """

    cycle = (phase / (2 * math.pi)) % 1.0

    if kind == "sine":
        return math.sin(phase)

    if kind == "triangle":
        return 1.0 - 4.0 * abs(cycle - 0.5)

    if kind == "square":
        return 1.0 if cycle < 0.5 else -1.0

    if kind == "sawtooth":
        return 2.0 * cycle - 1.0

    raise ValueError(
        "Unknown waveform: {}".format(kind)
    )


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

        self.audio = audiopwmio.PWMAudioOut(PIN)

    def close(self):
        if self.audio is not None:
            self.audio.stop()
            self.audio.deinit()
            self.audio = None

    def make_samples(
        self,
        frequencies,
        duration_ms,
        volume=None,
        fade=True,
        waveform="sine"
    ):
        """
        Generate unsigned 16-bit mono PCM samples.

        frequencies:
            Number for a constant tone, or
            (start_hz, end_hz) for a glide.

        volume:
            Percentage of full-scale peak amplitude.

        waveform:
            sine, triangle, square, sawtooth
        """

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

        fade_count = int(
            SAMPLE_RATE * FADE_MS / 1000
        )

        fade_count = min(
            fade_count,
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

            shape = waveform_value(
                waveform,
                phase
            )

            value = (
                32768 +
                int(
                    amplitude *
                    envelope *
                    shape
                )
            )

            value = max(
                0,
                min(65535, value)
            )

            samples.append(value)

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

        self.audio.play(sample)

        while self.audio.playing:
            time.sleep(0.01)

        self.audio.stop()

        # Keep samples alive until playback ends.
        del sample
        del samples
        gc.collect()

    def tone(self, hz, duration=None):
        print(
            "Tone:",
            hz,
            "Hz | Volume:",
            self.volume,
            "% | Duration:",
            duration or self.duration,
            "ms"
        )

        self.play(hz, duration)

    def pause(self, ms=200):
        time.sleep(ms / 1000)

    # ----------------------------------------------
    # Original v2 tests
    # ----------------------------------------------

    def hello_world(self):
        print()
        print("Hello World: 440 / 660 / 880 Hz")

        for hz in (440, 660, 880):
            self.tone(hz)
            self.pause(250)

    def stepped_sweep(self):
        print()
        print("Stepped frequency sweep")
        print("Each tone:", self.duration, "ms")

        frequencies = (
            200, 300, 400, 500,
            600, 700, 800, 900,
            1000, 1200, 1500,
            2000, 3000, 4000
        )

        for hz in frequencies:
            self.tone(hz)
            self.pause(150)

    def reverse_sweep(self):
        print()
        print("Descending stepped sweep")

        frequencies = (
            4000, 3000, 2000,
            1500, 1200, 1000,
            900, 800, 700, 600,
            500, 400, 300, 200
        )

        for hz in frequencies:
            self.tone(hz)
            self.pause(150)

    def glide(
        self,
        start_hz,
        end_hz,
        duration=750
    ):
        print(
            "Glide:",
            start_hz,
            "->",
            end_hz,
            "Hz"
        )

        self.play(
            (start_hz, end_hz),
            duration
        )

    def ascending_glide(self):
        self.glide(300, 1500)

    def descending_glide(self):
        self.glide(1500, 300)

    def chirps(self):
        print("Three chirps")

        for _ in range(3):
            self.glide(700, 1600, 150)
            self.pause(150)

    def confirmation(self):
        print("Confirmation effect")

        self.play(700, 120)
        self.pause(80)
        self.play(1050, 180)

    def warning(self):
        print("Warning effect")

        for _ in range(3):
            self.play(450, 250)
            self.pause(120)

    def custom_tone(self):
        hz = ask_int(
            "Frequency Hz",
            880,
            MIN_FREQUENCY,
            MAX_FREQUENCY
        )

        self.tone(hz)

    def set_volume(self):
        self.volume = ask_int(
            "Volume percentage",
            self.volume,
            0,
            100
        )

        print(
            "Original-test volume:",
            self.volume,
            "%"
        )

    def set_duration(self):
        self.duration = ask_int(
            "Tone duration (ms)",
            self.duration,
            25,
            1000
        )

        print(
            "Duration set to",
            self.duration,
            "ms"
        )

    # ----------------------------------------------
    # New v3 waveform experiments
    # ----------------------------------------------

    def compare_waveforms(self):
        print()
        print("WAVEFORM COMPARISON")
        print(
            "Frequency:",
            self.compare_frequency,
            "Hz"
        )
        print(
            "Amplitude:",
            self.compare_volume,
            "%"
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
        print()
        print("Available waveforms:")

        for i, kind in enumerate(WAVEFORMS):
            print(
                " {}  {}".format(
                    i + 1,
                    kind
                )
            )

        choice = ask_int(
            "Waveform number",
            WAVEFORMS.index(self.waveform) + 1,
            1,
            len(WAVEFORMS)
        )

        self.waveform = WAVEFORMS[choice - 1]

        print(
            "Selected waveform:",
            self.waveform
        )

    def waveform_tone(self):
        print()
        print("SELECTED-WAVEFORM TONE")

        print(
            "Waveform:",
            self.waveform
        )

        print(
            "Frequency:",
            self.compare_frequency,
            "Hz"
        )

        print(
            "Amplitude:",
            self.compare_volume,
            "%"
        )

        self.play(
            self.compare_frequency,
            self.duration,
            volume=self.compare_volume,
            waveform=self.waveform
        )

    def waveform_glide(self):
        print()
        print("SELECTED-WAVEFORM GLIDE")

        print(
            "Waveform:",
            self.waveform
        )

        print(
            "300 -> 1500 Hz"
        )

        self.play(
            (300, 1500),
            750,
            volume=self.compare_volume,
            waveform=self.waveform
        )

    def set_compare_frequency(self):
        self.compare_frequency = ask_int(
            "Comparison frequency Hz",
            self.compare_frequency,
            MIN_FREQUENCY,
            MAX_FREQUENCY
        )

        print(
            "Comparison frequency:",
            self.compare_frequency,
            "Hz"
        )

    def set_compare_volume(self):
        self.compare_volume = ask_int(
            "Comparison amplitude percentage",
            self.compare_volume,
            0,
            50
        )

        print(
            "Comparison amplitude:",
            self.compare_volume,
            "%"
        )


# --------------------------------------------------
# Input helper
# --------------------------------------------------

def ask_int(prompt, default, minimum, maximum):

    while True:
        response = input(
            "{} [{}]: ".format(
                prompt,
                default
            )
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

        print(
            "Valid range:",
            minimum,
            "to",
            maximum
        )


# --------------------------------------------------
# Menu
# --------------------------------------------------

def show_menu(lab):

    print()
    print("=" * 42)
    print("THE CLONKER 10000")
    print("AUDIO LABORATORY v3")
    print("=" * 42)

    print(
        "Sine volume: {}% | Duration: {} ms".format(
            lab.volume,
            lab.duration
        )
    )

    print(
        "Waveform: {} | {} Hz | {}%".format(
            lab.waveform,
            lab.compare_frequency,
            lab.compare_volume
        )
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
    print("10  Compare all four waveforms")
    print("11  Select waveform")
    print("12  Play selected-waveform tone")
    print("13  Play selected-waveform glide")
    print("14  Repeat waveform comparison")

    print()
    print("SETTINGS")
    print(" v  Set original sine-test volume")
    print(" d  Set tone duration")
    print(" f  Set waveform comparison frequency")
    print(" a  Set waveform comparison amplitude")
    print(" m  Show menu")
    print(" q  Quit")

    print()


# --------------------------------------------------
# Main
# --------------------------------------------------

def main():

    lab = None

    try:
        lab = AudioLab()

        print()
        print("Audio amplifier initialized.")
        print("Output: GP0")
        print("Sample rate:", SAMPLE_RATE)
        print()

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
                    lab.reverse_sweep()

                elif choice == "5":
                    lab.ascending_glide()

                elif choice == "6":
                    lab.descending_glide()

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
        if lab is not None:
            lab.close()

        print("Audio output released.")


main()
b