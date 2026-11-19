"""
THE CLONKER 10000
Audio Amplifier Laboratory - Hello World v1

Pico:       /tests/test_audio_amp.py
Signal:     GP0 -> STEMMA Audio Amp
Speaker:    8 ohms, connected to amplifier outputs

Run from CircuitPython REPL:
    exec(open("/tests/test_audio_amp.py").read())

Standalone experiment. No Clonker app imports.
"""

import board
import time
import math
import array
import audiocore
import audiopwmio

PIN = board.GP0
SAMPLE_RATE = 16000
VOLUME = 0.10       # 10% waveform amplitude
TONE_SECONDS = 0.20


def make_tone(frequency):
    count = int(SAMPLE_RATE * TONE_SECONDS)
    samples = array.array("H")

    for i in range(count):
        phase = 2 * math.pi * frequency * i / SAMPLE_RATE
        value = 32768 + int(32767 * VOLUME * math.sin(phase))
        samples.append(max(0, min(65535, value)))

    return audiocore.RawSample(
        samples,
        sample_rate=SAMPLE_RATE,
    )


audio = None

try:
    print("Audio Amp Hello World")
    print("GP0 | Volume: 10%")
    print()

    audio = audiopwmio.PWMAudioOut(PIN)

    for frequency in (440, 660, 880):
        print("Playing", frequency, "Hz")

        tone = make_tone(frequency)
        audio.play(tone)

        while audio.playing:
            time.sleep(0.01)

        time.sleep(0.20)

    print()
    print("Hello World complete!")

finally:
    if audio is not None:
        audio.deinit()
    print("Audio output released.")
