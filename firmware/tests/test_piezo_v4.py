
"""THE CLONKER 10000 - Test Kitchen Sink - Piezo Laboratory v4

Repository: firmware/tests/test_piezo_v4.py
Pico:       /tests/test_piezo_v4.py
REPL (after Ctrl+C):
    exec(open('/tests/test_piezo_v4.py').read())

Hardware: Raspberry Pi Pico 2 W, CircuitPython 10.3.1,
          Adafruit #160 passive piezo, GP0 -> piezo -> GND.
Standalone experiment; no production Clonker imports.

PURPOSE
-------
Characterize a passive piezo and collect useful sound-design ingredients.
This is NOT a decision to install the piezo in the Clonker. Keep evaluation
of the eventual production sound hardware separate from this experiment.

LISTENING JOURNAL - v2/v3 (subjective, this hardware only)
----------------------------------------------------------
* The conventional musical scale (262-1047 Hz) was inaudible.
* Strong, narrow audible region near 4150 Hz: 3500-3800 Hz faint,
  4100-4200 Hz loudest, with output fading by about 4500 Hz.
* 50% PWM duty was strongest. Changing duty produced strikingly smooth
  perceived swells and fades, although duty also alters waveform harmonics.
* 20 ms at 50% duty was a pleasant confirmation click; 10 ms was audible.
  Lower-duty click candidates were too faint.
* Rattles, alarms and pseudo-speech mostly sounded like crickets/chirps,
  not mechanical impacts or intelligible speech.
* Three-second duty swell/fade was exceptionally smooth.
* Continuous glides resembled bird calls; longer glides sometimes revealed
  individual pitch steps. A 100 ms 4500->3700 Hz chirp sounded most natural;
  200 ms revealed more steps.
* Power-up resembled a human whistle; power-down was smooth but initially
  a little quick. Opposing pitch/duty movements sounded more expressive.
* Breathing patterns sounded like tuning forks rather than crickets.
* Alternating pitch/duty modulation sounded like birds conversing.

LISTENING JOURNAL - v4 (15 tests, observations as reported)
----------------------------------------------------------
 1-2: No new v4 listening notes recorded; earlier duty and resonance
      characterization remains the reference.
 3. Glide resolution: First chirp initially sounded different, but this
      could not be reproduced after restarting the test program. Later
      chirps sounded almost alike; no clear resolution winner.
 4. Glide duration: Progressively longer chirps, moderately audible;
      slight frequency-step perception in the last two.
 5. Click candidates: First sounded like short tics; latter candidates
      sounded smoother; third seemed loudest. (Subjective impression.)
 6. Double confirmations: Quick short tones, not bird-like.
 7. Smooth swell/fade: Smooth, rising/tuning-fork-like impression followed
      by a fade. Note: this test holds frequency constant at 4150 Hz;
      the apparent pitch rise was perceptual, not a programmed glide.
 8. Power-down durations: All smooth; first possibly too quick; third
      resembled a bomb falling from the sky.
 9. Power-up durations: Similar smooth sounds, primarily differentiated
      by length; perceived as a sigh rather than a tuning fork.
10. Opposing pitch/duty: Two related, reversed-sounding variations;
      second had a slightly sharper onset.
11. Whistle phrases: Three variations very difficult to distinguish.
12. Bird calls: All three sounded like identical bird chirps.
13. Bird conversation: Smooth, blended bird-like conversation.
14. Percussive envelopes: First sharp/short; second smoother; third
      smooth with a quick fade-away.
15. Resonance compensation: Both frequency series started very faint,
      became loudest around the third tone, then faded stepwise. The
      third frequency is 4150 Hz in both series. No compelling evidence
      that the exploratory duty changes flattened perceived loudness.

WHAT THESE OBSERVATIONS SUPPORT
-------------------------------
* Frequency is a strong determinant of audible level on this resonant
  piezo; near-4150-Hz sounds are easiest to hear.
* Duty envelopes and continuous frequency changes offer more expressive
  results than simple rapid on/off sequences.
* Some differences in step count, chirp shape and whistle phrases were
  too subtle to identify reliably by ear in these informal trials.
* A sound's perceived pitch or loudness can differ from the programmed
  parameter: resonance, PWM harmonics and hearing all contribute.
* The one-off first-chirp anomaly remains unexplained and unreproduced.
* These are informal listening impressions, not calibrated measurements;
  do not infer temperature warm-up, timing bugs or true acoustic amplitude
  from these results alone.

POTENTIAL SOUND-DESIGN INGREDIENTS (NOT PRODUCT DECISIONS)
---------------------------------------------------------
* Crisp feedback: short 10-20 ms resonant burst; or sharp attack plus
  a brief smooth decay (v4 test 14).
* Gentle indication: fixed-frequency duty swell/fade (v4 test 7).
* Dramatic descending cue: longer pitch/duty power-down (v4 test 8).
* Soft rising/sigh-like cue: extended power-up envelope (v4 test 9).
* Character sounds: 100 ms descending chirp, or blended bird phrases
  (v4 tests 12-13). These may be fun without being practical UI feedback.
* For future experiments, compare effects at matched perceived loudness,
  consider long silence before a first chirp, and measure PWM timing if
  audible stepping becomes a real design constraint.

VERSIONING
----------
The original v3 test module remains firmware/tests/test_piezo.py.
This v4 module is a standalone, focused lab; its executable tests and
menu are preserved unchanged by this documentation update.
"""
import board
import pwmio
import time

PIN = board.GP0
RESONANCE = 4150


class Piezo:
    def __init__(self):
        self.pwm = pwmio.PWMOut(
            PIN, frequency=RESONANCE, duty_cycle=0,
            variable_frequency=True)

    def set(self, hz=RESONANCE, duty=50):
        hz = max(100, min(10000, int(hz)))
        duty = max(0, min(50, duty))
        self.pwm.frequency = hz
        self.pwm.duty_cycle = int(65535 * duty / 100)

    def off(self):
        self.pwm.duty_cycle = 0

    def rest(self, seconds):
        self.off()
        time.sleep(seconds)

    def tone(self, hz, seconds, duty=50):
        try:
            self.set(hz, duty)
            time.sleep(seconds)
        finally:
            self.off()

    def curve(self, start_hz, end_hz, seconds, steps=50,
              start_duty=50, end_duty=50, shape='linear'):
        """Time-scheduled updates; print elapsed time for comparison.

        No intentional off gaps between steps. The interpreter may
        overrun deadlines at high update rates.
        """
        start = time.monotonic_ns()
        interval_ns = int(seconds * 1_000_000_000 / steps)
        try:
            for i in range(steps + 1):
                t = i / steps
                if shape == 'ease':
                    t = t * t * (3 - 2 * t)
                hz = start_hz + (end_hz - start_hz) * t
                duty = start_duty + (end_duty - start_duty) * t
                self.set(hz, duty)
                if i < steps:
                    deadline = start + (i + 1) * interval_ns
                    remaining = (deadline - time.monotonic_ns()) / 1e9
                    if remaining > 0:
                        time.sleep(remaining)
        finally:
            self.off()
        elapsed = (time.monotonic_ns() - start) / 1e9
        print(' requested {:.3f}s, actual {:.3f}s, {} steps'.format(
            seconds, elapsed, steps))

    def envelope(self, rise=1.5, fall=1.5, peak=50,
                 hz=RESONANCE, steps=60):
        self.curve(hz, hz, rise, steps, 2, peak, 'ease')
        self.curve(hz, hz, fall, steps, peak, 2, 'ease')

    def close(self):
        self.off()
        self.pwm.deinit()


def duty_comparison(p):
    for duty in (5, 10, 20, 35, 50):
        print('Duty', duty, '%')
        p.tone(RESONANCE, 0.5, duty)
        p.rest(0.3)


def resonance_check(p):
    for hz in (3700, 3900, 4050, 4150, 4250, 4400, 4550):
        print(hz, 'Hz')
        p.tone(hz, 0.35)
        p.rest(0.2)


def glide_resolution(p):
    for steps in (20, 50, 100, 200):
        print('200 ms descending bird chirp:', steps, 'steps')
        p.curve(4500, 3700, 0.2, steps)
        p.rest(0.7)


def glide_duration(p):
    for seconds in (0.05, 0.1, 0.2, 0.35):
        print('Descending chirp duration:', seconds)
        p.curve(4500, 3700, seconds, 100)
        p.rest(0.5)


def click_candidates(p):
    for seconds, duty in ((0.01, 50), (0.02, 50),
                          (0.03, 35), (0.04, 20)):
        print('Click:', seconds, 's,', duty, '%')
        for _ in range(2):
            p.tone(RESONANCE, seconds, duty)
            p.rest(0.25)
        p.rest(0.3)


def double_confirmation(p):
    for gap in (0.04, 0.08, 0.15):
        print('Double click gap:', gap)
        p.tone(RESONANCE, 0.02)
        p.rest(gap)
        p.tone(RESONANCE, 0.035)
        p.rest(0.6)


def smooth_swell(p):
    print('3-second duty swell/fade')
    p.envelope()


def power_down(p):
    for seconds in (1, 2, 3):
        print('Power-down:', seconds, 'seconds')
        p.curve(4400, 3550, seconds, 120, 50, 2, 'ease')
        p.rest(0.8)


def power_up(p):
    for seconds in (1, 2, 3):
        print('Power-up:', seconds, 'seconds')
        p.curve(3550, 4400, seconds, 120, 2, 50, 'ease')
        p.rest(0.8)


def opposing_pitch_duty(p):
    print('Falling pitch / rising duty')
    p.curve(4400, 3900, 1, 100, 2, 50, 'ease')
    p.rest(0.6)
    print('Rising pitch / falling duty')
    p.curve(3900, 4400, 1, 100, 50, 2, 'ease')


def whistle_phrases(p):
    phrases = (
        ((3850, 4250, 0.32), (4250, 4100, 0.22)),
        ((3950, 4400, 0.24), (4400, 4000, 0.38)),
        ((4100, 4350, 0.20), (4350, 3900, 0.30)),
    )
    for index, phrase in enumerate(phrases, 1):
        print('Whistle phrase', index)
        for a, b, seconds in phrase:
            p.curve(a, b, seconds, 60, 25, 40, 'ease')
            p.rest(0.035)
        p.rest(0.65)


def bird_calls(p):
    for index, (a, b, seconds) in enumerate((
            (4500, 3700, 0.1), (4400, 3900, 0.14),
            (4300, 4000, 0.08)), 1):
        print('Bird call', index)
        p.curve(a, b, seconds, 70, 45, 25)
        p.rest(0.55)


def bird_conversation(p):
    for index, (a, b, seconds, gap) in enumerate((
            (3900, 4400, 0.22, 0.12),
            (4400, 3900, 0.18, 0.25),
            (3950, 4350, 0.15, 0.08),
            (4350, 3850, 0.28, 0.35)), 1):
        print('Bird phrase', index)
        p.curve(a, b, seconds, 75, 12, 40)
        p.rest(gap)


def percussive_envelopes(p):
    for attack, decay in ((0.005, 0.08), (0.01, 0.2),
                          (0.02, 0.4)):
        print('Attack', attack, 'decay', decay)
        p.curve(RESONANCE, RESONANCE, attack, 10, 2, 50)
        p.curve(RESONANCE, RESONANCE, decay, 70, 50, 2, 'ease')
        p.rest(0.6)


def resonance_compensation(p):
    print('Fixed 35% duty: compare loudness across frequency')
    for hz in (3800, 3950, 4150, 4350, 4500):
        print(hz, 'Hz at 35%')
        p.tone(hz, 0.35, 35)
        p.rest(0.15)
    p.rest(0.5)
    print('Exploratory duty changes; not calibrated compensation')
    for hz, duty in ((3800, 50), (3950, 45), (4150, 25),
                     (4350, 45), (4500, 50)):
        print(hz, 'Hz at', duty, '%')
        p.tone(hz, 0.35, duty)
        p.rest(0.15)


TESTS = {
    '1': ('Duty response', duty_comparison),
    '2': ('Quick resonance check', resonance_check),
    '3': ('Glide resolution', glide_resolution),
    '4': ('Glide duration', glide_duration),
    '5': ('Confirmation clicks', click_candidates),
    '6': ('Double confirmations', double_confirmation),
    '7': ('Smooth swell/fade', smooth_swell),
    '8': ('Power-down durations', power_down),
    '9': ('Power-up durations', power_up),
    '10': ('Opposing pitch/duty', opposing_pitch_duty),
    '11': ('Human whistle phrases', whistle_phrases),
    '12': ('Bird calls', bird_calls),
    '13': ('Bird conversation', bird_conversation),
    '14': ('Percussive envelopes', percussive_envelopes),
    '15': ('Resonance compensation', resonance_compensation),
}


def menu():
    print('\n' + '=' * 42)
    print('THE CLONKER 10000 - PIEZO LAB v4')
    print('Whistles, Birds & Other Nonsense')
    print('=' * 42)
    for number in range(1, 16):
        key = str(number)
        print('{:>2}. {}'.format(number, TESTS[key][0]))
    print(' q. Quit\n')


def main():
    p = Piezo()
    try:
        while True:
            menu()
            choice = input('Select test: ').strip().lower()
            if choice == 'q':
                break
            if choice in TESTS:
                print('\nRunning:', TESTS[choice][0])
                TESTS[choice][1](p)
                p.rest(0.25)
            else:
                print('Unknown selection')
    except KeyboardInterrupt:
        print('\nInterrupted')
    finally:
        p.close()
        print('Piezo released; GP0 deinitialized')


main()
