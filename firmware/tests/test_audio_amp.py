"""
THE CLONKER 10000 - Audio Amplifier Laboratory v5

Repository: firmware/tests/test_audio_amp.py
Pico:       /tests/test_audio_amp.py
REPL:       exec(open('/tests/test_audio_amp.py').read())

STATUS (November 2026)
----------------------
Experimental audio hardware evaluation completed through v5.
Audio integration into the Clonker is UNDECIDED.
This is a standalone test program, not production firmware.
The amplifier experiment may be shelved indefinitely.

HARDWARE
--------
MCU:       Raspberry Pi Pico 2 W
Firmware:  CircuitPython 10.3.1
Amplifier: Adafruit STEMMA Audio Amp #5647
Speaker:   23 mm, 8 ohm, 1 W
Signal:    GP0 -> amplifier input
Power:     3V3 -> amplifier power
Ground:    Common GND
Speaker:   Connected ONLY to amplifier speaker outputs

Speaker was tested free-standing, resting on different
surfaces, and inside the zipped foam Clonker case with
its aluminum faceplate.

The amplifier has an illuminated green power LED.
Deinitializing PWMAudioOut releases the Pico audio
peripheral but DOES NOT remove amplifier power.

For temporary storage, power off the Pico before
disconnecting the amplifier. Prefer disconnecting
both 3V3 and GP0, leaving GND connected. Avoid
driving GP0 into an unpowered amplifier.

EXPERIMENT HISTORY
------------------
v1-v2:
    Basic tones, frequency sweeps, glides and effects.

v3:
    Sine, triangle, square and sawtooth comparisons.

v4:
    Audio initialization, release, warm idle and
    repeated lifecycle tests.

v5:
    Mechanical effects, precomputed samples,
    8-bit and 16-bit WAV generation and playback,
    timing and memory observations.

RESULTS - BASIC AUDIO
---------------------
* 440 Hz was relatively faint.
* 660 and 880 Hz were clearly audible.
* Approximately 200-400 Hz sounded weak.
* Higher frequencies, including 3-4 kHz, were audible.
* No calibrated frequency-response measurements exist.
* Sine and triangle sounded smooth and similar.
* Square and sawtooth sounded brighter or buzzier.
* Some apparent buzzing was mechanical coupling to
  the surface supporting the speaker.
* Suspending the speaker or placing it on foam
  substantially reduced this buzzing.
* Speaker inside zipped case remained audible and
  generally clean at previously tested amplitudes.
* Case enclosure reduced apparent loudness, especially
  for speech. Final mounting is not established.

RESULTS - SOFTWARE LIFECYCLE (v4)
---------------------------------
Test 15, cold initialization/release:
    Initialization: approximately 0.214 ms
    Release:        approximately 0.122 ms
    Free memory:    310176 before and after
    No audible pops reported.

Test 16, warm idle:
    Three confirmation sequences sounded consistent.
    Elapsed times: approximately 786.7, 786.7,
    and 786.3 ms, including synthesis overhead.

Test 17, five restart cycles:
    Average initialization: approximately 0.189 ms
    Average release:        approximately 0.159 ms
    Free memory: 310176 -> 310080 bytes
    No audible pops or behavioral differences.
    Small memory difference does not establish a leak.

RESULTS - SYNTHESIZED EFFECTS (v5)
----------------------------------
Five initial mechanical-effect candidates:
    Clonk, Ratchet, Bell, Click and Power.

They generally sounded like electronic tones rather
than convincing mechanical sounds.
The Power effect resembled a smooth siren.

Conclusion:
    Simple periodic waveforms and pitch glides were
    not convincing substitutes for mechanical impacts.

RESULTS - WAV PLAYBACK
----------------------
* 8-bit and 16-bit mono PCM WAV playback worked.
* Test WAVs used a 16 kHz sample rate.
* The two formats sounded virtually identical for
  a simple 700-1050 Hz sine glide.
* Playback durations were approximately 404 ms.
* External WAV playback succeeded without changing
  the production Clonker firmware.

COMPLEX SOUND AUDITIONS
-----------------------
Original robotic male speech:
    Understandable, with an obviously robotic sound.

Synthetic female speech:
    Unnatural and less intelligible than the male
    robot. Rejected as a natural-voice test.

Mechanical clatter:
    Convincing metallic character.
    Somewhat quiet.
    Louder versions produced little perceived
    improvement.

Metallic bell:
    More tonal than expected; less convincingly
    metallic than the mechanical clatter.

Percussion rhythm:
    Convincing hi-hat character.
    Could benefit from greater loudness.

Musical chords:
    Pleasant, distinct simultaneous notes.
    Resembled a vibrating string instrument.

Natural female speech:
    Julie Etchingham recording converted to
    16-bit mono 16 kHz PCM WAV.
    Natural, clear and intelligible outside case.
    Still understandable inside zipped case when
    listening carefully, but noticeably subdued.
    Louder processed version offered little
    perceived improvement.

    Full-length WAVs occupied substantial storage.
    Short phrases would require much less space.
    Both Julie WAVs were backed up externally and
    approved for deletion from the Pico.

    Recording was used for hardware evaluation,
    not for voice cloning or custom speech.
    Source: Wikimedia Commons / VocalEyes project.
    License: CC BY-SA 4.0; retain attribution
    and license information with archived copies.

LOUDNESS OBSERVATIONS
---------------------
* Good audio quality does not guarantee sufficient
  acoustic output for practical remote-control alerts.
* Increased WAV peak levels did not necessarily
  produce noticeably greater perceived loudness.
* Short alert tones may be more effective than speech.
* No calibrated SPL, distortion, amplifier output
  power, or electrical power measurements were made.
* The maximum clean loudness has NOT been established.
* Frequency, waveform, amplitude and enclosure effects
  require further controlled testing.

STORAGE / TEST ASSETS
---------------------
Test script:
    firmware/tests/test_audio_amp.py

Audio assets:
    firmware/tests/audio/ (where retained)
    /tests/audio/ on Pico

Some generated comparison WAVs use /tests directly;
consult the constants in this test program.

Large speech files and rejected effects need not
remain on Pico flash after external backup.

FUTURE EXPERIMENTS (OPTIONAL)
-----------------------------
1. Frequency versus perceived loudness, speaker
   mounted inside the zipped case.
2. Compare sine, triangle and limited square waves
   at the strongest audible frequencies.
3. Explore increasing amplitude while listening
   for distortion and mechanical rattling.
4. Compare short alert patterns and transient sounds.
5. Measure system current draw with amplifier powered
   versus disconnected, if power budget matters.
6. Evaluate speaker mounting or acoustic opening if
   the case significantly reduces usable loudness.

No decision has been made to integrate audio.
No production firmware changes are authorized by
these experimental results.
"""
import board
import time
import math
import array
import gc
import audiocore
import audiopwmio

PIN = board.GP0
RATE = 16000
MAX_SAMPLES = RATE  # 1 second at 16 kHz, mono, 16-bit
WAV_DIR = '/tests'
WAV_8 = WAV_DIR + '/audio_lab_8bit.wav'
WAV_16 = WAV_DIR + '/audio_lab_16bit.wav'
WAVES = ('sine', 'triangle', 'square', 'sawtooth')


def ms_since(t):
    return (time.monotonic_ns() - t) / 1000000


def ask_int(label, default, low, high):
    while True:
        raw = input('{} [{}]: '.format(label, default)).strip()
        if not raw:
            return default
        try:
            value = int(raw)
            if low <= value <= high:
                return value
        except ValueError:
            pass
        print('Enter an integer from {} to {}.'.format(low, high))


def shape(kind, phase):
    cycle = (phase / (2 * math.pi)) % 1
    if kind == 'sine':
        return math.sin(phase)
    if kind == 'triangle':
        return 1 - 4 * abs(cycle - 0.5)
    if kind == 'square':
        return 1 if cycle < 0.5 else -1
    if kind == 'sawtooth':
        return 2 * cycle - 1
    raise ValueError('Unknown waveform')


def pcm(start_hz, end_hz, duration_ms, volume, kind='sine',
        attack_ms=15, release_ms=15, decay=False):
    """Unsigned 16-bit PCM. A phase-continuous frequency glide."""
    count = int(RATE * duration_ms / 1000)
    if not 1 <= count <= MAX_SAMPLES:
        raise ValueError('Duration must fit 1-second PCM buffer')
    samples = array.array('H')
    phase = 0.0
    amp = 32767 * max(0, min(100, volume)) / 100
    attack = max(1, int(RATE * attack_ms / 1000))
    release = max(1, int(RATE * release_ms / 1000))
    for i in range(count):
        p = i / max(1, count - 1)
        hz = start_hz + (end_hz - start_hz) * p
        phase += 2 * math.pi * hz / RATE
        envelope = min(1.0, i / attack, (count - 1 - i) / release)
        if decay:
            envelope *= (1 - p) ** 2
        value = 32768 + int(amp * envelope * shape(kind, phase))
        samples.append(max(0, min(65535, value)))
    return samples


def wav_header(data_bytes, bits):
    """PCM mono RIFF header, built without desktop-only wave/struct modules."""
    def le(number, width):
        return bytes((number >> (8 * i)) & 255 for i in range(width))
    block = bits // 8
    return (b'RIFF' + le(36 + data_bytes, 4) + b'WAVE'
            + b'fmt ' + le(16, 4) + le(1, 2) + le(1, 2)
            + le(RATE, 4) + le(RATE * block, 4)
            + le(block, 2) + le(bits, 2)
            + b'data' + le(data_bytes, 4))


class Lab:
    def __init__(self):
        self.audio = None
        self.volume = 20
        self.duration = 750
        self.compare_volume = 20
        self.frequency = 800
        self.waveform = 'sine'
        self.effect_volume = 35

    def initialize(self):
        if self.audio is not None:
            return 0.0
        start = time.monotonic_ns()
        self.audio = audiopwmio.PWMAudioOut(PIN)
        return ms_since(start)

    def release(self):
        if self.audio is None:
            return 0.0
        start = time.monotonic_ns()
        try:
            self.audio.stop()
            self.audio.deinit()
        finally:
            self.audio = None
        return ms_since(start)

    def play_sample(self, sample):
        self.initialize()
        start = time.monotonic_ns()
        try:
            self.audio.play(sample)
            while self.audio.playing:
                time.sleep(0.005)
        finally:
            self.audio.stop()
        return ms_since(start)

    def play_buffer(self, samples):
        sample = audiocore.RawSample(samples, sample_rate=RATE)
        return self.play_sample(sample)

    def play(self, start_hz, end_hz=None, duration=None, volume=None,
             kind='sine', attack=15, release=15, decay=False):
        if end_hz is None:
            end_hz = start_hz
        if duration is None:
            duration = self.duration
        if volume is None:
            volume = self.volume
        samples = pcm(start_hz, end_hz, duration, volume, kind,
                      attack, release, decay)
        result = self.play_buffer(samples)
        gc.collect()
        return result

    def pause(self, ms=200):
        time.sleep(ms / 1000)

    def confirmation(self, volume=None):
        if volume is None:
            volume = self.volume
        self.play(700, duration=120, volume=volume)
        self.pause(80)
        self.play(1050, duration=180, volume=volume)

    def hello(self):
        for hz in (440, 660, 880):
            print(hz, 'Hz')
            self.play(hz)
            self.pause(250)

    def sweep(self, reverse=False):
        values = (200, 300, 400, 500, 600, 700, 800, 900,
                  1000, 1200, 1500, 2000, 3000, 4000)
        if reverse:
            values = tuple(reversed(values))
        for hz in values:
            print(hz, 'Hz')
            self.play(hz)
            self.pause(150)

    def chirps(self):
        for _ in range(3):
            self.play(700, 1600, 150)
            self.pause(150)

    def warning(self):
        for _ in range(3):
            self.play(450, duration=250)
            self.pause(120)

    def compare(self):
        for kind in WAVES:
            print(kind)
            self.play(self.frequency, duration=750,
                      volume=self.compare_volume, kind=kind)
            self.pause(350)

    def select_waveform(self):
        for i, kind in enumerate(WAVES):
            print(i + 1, kind)
        n = ask_int('Waveform', WAVES.index(self.waveform) + 1, 1, 4)
        self.waveform = WAVES[n - 1]

    def lifecycle_cold(self):
        self.release()
        self.pause(500)
        gc.collect()
        before = gc.mem_free()
        init = self.initialize()
        gc.collect()
        active = gc.mem_free()
        self.confirmation(30)
        release = self.release()
        gc.collect()
        after = gc.mem_free()
        print('Init {:.3f} ms | Release {:.3f} ms'.format(init, release))
        print('Free memory: {} -> {} -> {}'.format(before, active, after))

    def lifecycle_warm(self):
        self.release()
        print('Init {:.3f} ms'.format(self.initialize()))
        try:
            for i in range(3):
                start = time.monotonic_ns()
                self.confirmation(30)
                print('Playback {}: {:.1f} ms'.format(i + 1, ms_since(start)))
                if i < 2:
                    self.pause(500)
        finally:
            self.release()

    def lifecycle_restart(self):
        self.release()
        gc.collect()
        baseline = gc.mem_free()
        init_times = []
        release_times = []
        try:
            for i in range(5):
                init_times.append(self.initialize())
                self.confirmation(30)
                release_times.append(self.release())
                gc.collect()
                print('Cycle {}: init {:.3f}, release {:.3f}, free {}'.format(
                    i + 1, init_times[-1], release_times[-1], gc.mem_free()))
                if i < 4:
                    self.pause(500)
        finally:
            self.release()
        gc.collect()
        print('Avg init {:.3f} ms, release {:.3f} ms'.format(
            sum(init_times) / len(init_times),
            sum(release_times) / len(release_times)))
        print('Memory difference:', gc.mem_free() - baseline)

    def mechanical(self, which):
        """Small synthesized effects; avoid huge in-memory buffers."""
        v = self.effect_volume
        if which == 'clonk':
            self.play(1100, 320, 130, v, 'triangle', 2, 50, True)
        elif which == 'ratchet':
            for i in range(5):
                self.play(1200 - 90 * i, duration=28,
                          volume=v, kind='square', attack=2, release=7)
                self.pause(35)
        elif which == 'bell':
            self.play(1450, 1100, 450, v, 'sine', 2, 180, True)
            self.play(2100, 1800, 230, v // 2, 'sine', 2, 100, True)
        elif which == 'click':
            self.play(1800, 650, 35, v, 'square', 1, 12, True)
        elif which == 'power':
            self.play(350, 1550, 350, v, 'sawtooth', 10, 60)
            self.pause(60)
            self.play(1000, 550, 160, v, 'triangle', 2, 75, True)
        else:
            raise ValueError('Unknown effect')

    def effect_menu(self):
        names = ('clonk', 'ratchet', 'bell', 'click', 'power')
        for i, name in enumerate(names):
            print(i + 1, name)
        n = ask_int('Effect', 1, 1, len(names))
        print('Effect:', names[n - 1], '| Volume:', self.effect_volume)
        self.mechanical(names[n - 1])

    def prepared_benchmark(self):
        """Compare generation cost and playback using the SAME PCM."""
        self.release()
        gc.collect()
        before = gc.mem_free()
        t = time.monotonic_ns()
        samples = pcm(700, 1050, 180, self.effect_volume)
        generation = ms_since(t)
        gc.collect()
        held = gc.mem_free()
        sample = audiocore.RawSample(samples, sample_rate=RATE)
        try:
            init = self.initialize()
            first = self.play_sample(sample)
            second = self.play_sample(sample)
            print('Generate once: {:.2f} ms'.format(generation))
            print('Initialize: {:.3f} ms'.format(init))
            print('Playback 1: {:.1f} ms'.format(first))
            print('Playback 2: {:.1f} ms'.format(second))
            print('Free before: {}, with PCM: {}'.format(before, held))
        finally:
            self.release()
            del sample
            del samples
            gc.collect()
        print('Free after:', gc.mem_free())

    def generate_wavs(self):
        """Create two identical-tone mono PCM WAVs on CIRCUITPY.

        8-bit unsigned and 16-bit signed little-endian WAV. These are
        known-good file-format fixtures, not high-fidelity recordings.
        """
        samples = pcm(700, 1050, 400, 35, 'sine', 10, 80)
        count = len(samples)
        print('Writing', WAV_8, 'and', WAV_16)
        with open(WAV_8, 'wb') as f:
            f.write(wav_header(count, 8))
            chunk = bytearray(256)
            for start in range(0, count, 256):
                n = min(256, count - start)
                for i in range(n):
                    chunk[i] = samples[start + i] >> 8
                f.write(memoryview(chunk)[:n])
        with open(WAV_16, 'wb') as f:
            f.write(wav_header(count * 2, 16))
            chunk = bytearray(512)
            for start in range(0, count, 256):
                n = min(256, count - start)
                for i in range(n):
                    # unsigned 16-bit -> signed 16-bit, same bit pattern
                    x = samples[start + i] ^ 0x8000
                    chunk[2 * i] = x & 255
                    chunk[2 * i + 1] = x >> 8
                f.write(memoryview(chunk)[:2 * n])
        print('Wrote {} samples; 8-bit ~{} B, 16-bit ~{} B'.format(
            count, count + 44, 2 * count + 44))
        print('If files are read-only, see instructions below.')

    def play_wav(self, path):
        """Stream WAV directly from file; no whole-file PCM allocation."""
        self.initialize()
        with open(path, 'rb') as f:
            sample = audiocore.WaveFile(f)
            print('Playing:', path)
            t = time.monotonic_ns()
            self.play_sample(sample)
            print('Elapsed {:.1f} ms'.format(ms_since(t)))
        gc.collect()

    def wav_comparison(self):
        for path in (WAV_8, WAV_16):
            self.play_wav(path)
            self.pause(350)


def menu(lab):
    print('\n' + '=' * 43)
    print('THE CLONKER 10000 - AUDIO LAB v5')
    print('=' * 43)
    print('Sine {}% / {} ms | Wave {} Hz / {}% / {}'.format(
        lab.volume, lab.duration, lab.frequency,
        lab.compare_volume, lab.waveform))
    print('Effects {}% | Audio {}'.format(
        lab.effect_volume, 'ON' if lab.audio else 'RELEASED'))
    print('\nORIGINAL TONES / EFFECTS')
    print(' 1 Hello World       2 Custom sine tone')
    print(' 3 Ascending sweep   4 Descending sweep')
    print(' 5 Ascending glide   6 Descending glide')
    print(' 7 Three chirps      8 Confirmation')
    print(' 9 Warning')
    print('\nWAVEFORM LAB')
    print('10 Compare waves     11 Select waveform')
    print('12 Waveform tone     13 Waveform glide')
    print('14 Repeat comparison')
    print('\nSOFTWARE LIFECYCLE')
    print('15 Cold start        16 Warm idle')
    print('17 Restart 5 times')
    print('\nNEW v5 TESTS')
    print('18 Mechanical effects menu')
    print('19 Precomputed sample timing')
    print('20 Generate 8-bit and 16-bit WAV files')
    print('21 Play generated WAV files')
    print('22 Play a WAV by absolute Pico path')
    print('\nSETTINGS')
    print(' v Sine volume       d Tone duration')
    print(' f Wave frequency    a Wave amplitude')
    print(' e Effect volume     m Menu     q Quit\n')


def main():
    lab = Lab()
    try:
        print('Audio Lab v5 ready. GP0. Hardware initialized on demand.')
        menu(lab)
        while True:
            choice = input('Audio Lab> ').strip().lower()
            try:
                if choice == '1':
                    lab.hello()
                elif choice == '2':
                    hz = ask_int('Frequency Hz', 880, 100, 4000)
                    lab.play(hz)
                elif choice == '3':
                    lab.sweep()
                elif choice == '4':
                    lab.sweep(True)
                elif choice == '5':
                    lab.play(300, 1500, 750)
                elif choice == '6':
                    lab.play(1500, 300, 750)
                elif choice == '7':
                    lab.chirps()
                elif choice == '8':
                    lab.confirmation()
                elif choice == '9':
                    lab.warning()
                elif choice in ('10', '14'):
                    lab.compare()
                elif choice == '11':
                    lab.select_waveform()
                elif choice == '12':
                    lab.play(lab.frequency, duration=lab.duration,
                             volume=lab.compare_volume, kind=lab.waveform)
                elif choice == '13':
                    lab.play(300, 1500, 750, lab.compare_volume, lab.waveform)
                elif choice == '15':
                    lab.lifecycle_cold()
                elif choice == '16':
                    lab.lifecycle_warm()
                elif choice == '17':
                    lab.lifecycle_restart()
                elif choice == '18':
                    lab.effect_menu()
                elif choice == '19':
                    lab.prepared_benchmark()
                elif choice == '20':
                    lab.generate_wavs()
                elif choice == '21':
                    lab.wav_comparison()
                elif choice == '22':
                    path = input('Absolute WAV path: ').strip()
                    if path:
                        lab.play_wav(path)
                elif choice == 'v':
                    lab.volume = ask_int('Sine volume %', lab.volume, 0, 100)
                elif choice == 'd':
                    lab.duration = ask_int('Duration ms', lab.duration, 25, 1000)
                elif choice == 'f':
                    lab.frequency = ask_int('Wave frequency Hz', lab.frequency, 100, 4000)
                elif choice == 'a':
                    lab.compare_volume = ask_int('Wave amplitude %', lab.compare_volume, 0, 50)
                elif choice == 'e':
                    lab.effect_volume = ask_int('Effect amplitude %', lab.effect_volume, 0, 50)
                elif choice == 'm':
                    menu(lab)
                elif choice == 'q':
                    break
                elif choice:
                    print('Unknown command; m for menu.')
            except (ValueError, OSError, RuntimeError) as exc:
                print('Test error:', type(exc).__name__, exc)
                print('Audio remains available; q to exit.')
    except KeyboardInterrupt:
        print('\nInterrupted.')
    finally:
        lab.release()
        print('Audio output released.')


main()
