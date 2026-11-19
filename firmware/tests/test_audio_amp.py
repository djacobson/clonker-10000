"""
THE CLONKER 10000
Audio Amplifier Laboratory v2

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

v1 observations:
    440 Hz: smooth but faint
    660 Hz: smooth, louder
    880 Hz: smooth, louder still

    200 ms tones were difficult to identify.
    750 ms tones were clearly recognizable.

v2:
    Interactive menu
    Adjustable volume and tone duration
    Individual tones
    Stepped frequency sweeps
    Continuous frequency glides
    Simple sound effects
    Gentle fade-in/fade-out
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

MIN_FREQUENCY = 100
MAX_FREQUENCY = 4000

FADE_MS = 15

# Avoid excessively large sample buffers.
MAX_SAMPLES = 16000


# --------------------------------------------------
# Audio Laboratory
# --------------------------------------------------

class AudioLab:

    def __init__(self):
        self.volume = DEFAULT_VOLUME
        self.duration = DEFAULT_DURATION
        self.audio = audiopwmio.PWMAudioOut(PIN)

    def close(self):
        if self.audio is not None:
            self.audio.stop()
            self.audio.deinit()
            self.audio = None

    def make_samples(self, frequencies, duration_ms,
                     volume=None, fade=True):
        """
        Generate unsigned 16-bit PCM samples.

        frequencies:
            A number for a constant tone, or
            (start_hz, end_hz) for a glide.

        Volume is percentage of full-scale
        waveform amplitude.
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

            value = (
                32768 +
                int(
                    amplitude *
                    envelope *
                    math.sin(phase)
                )
            )

            value = max(
                0,
                min(65535, value)
            )

            samples.append(value)

        return samples

    def play(self, frequencies, duration_ms=None,
             volume=None, fade=True):

        if duration_ms is None:
            duration_ms = self.duration

        samples = self.make_samples(
            frequencies,
            duration_ms,
            volume,
            fade
        )

        sample = audiocore.RawSample(
            samples,
            sample_rate=SAMPLE_RATE
        )

        self.audio.play(sample)

        while self.audio.playing:
            time.sleep(0.01)

        # Keep references alive until playback ends.
        self.audio.stop()

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

    def glide(self, start_hz, end_hz,
              duration=750):
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
            "Volume set to",
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


# --------------------------------------------------
# Input helpers
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
    print("=" * 38)
    print("THE CLONKER 10000")
    print("AUDIO LABORATORY v2")
    print("=" * 38)

    print(
        "Volume: {}% | Duration: {} ms".format(
            lab.volume,
            lab.duration
        )
    )

    print()
    print("TONES")
    print(" 1  Hello World (440/660/880)")
    print(" 2  Custom frequency")
    print(" 3  Stepped sweep ascending")
    print(" 4  Stepped sweep descending")

    print()
    print("GLIDES")
    print(" 5  Ascending glide")
    print(" 6  Descending glide")

    print()
    print("SOUND EFFECTS")
    print(" 7  Three chirps")
    print(" 8  Confirmation")
    print(" 9  Warning")

    print()
    print("SETTINGS")
    print(" v  Set volume")
    print(" d  Set tone duration")
    print(" m  Show menu")
    print(" q  Quit")

    print()


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

                elif choice == "v":
                    lab.set_volume()

                elif choice == "d":
                    lab.set_duration()

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
