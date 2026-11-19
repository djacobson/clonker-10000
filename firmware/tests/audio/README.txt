Clonker Audio Laboratory — Complex WAV Audition

All files are 16-bit signed PCM, mono, 16,000 Hz.
Copy the .wav files into firmware/tests/audio/ in the repo and /tests/audio/ on the Pico.
Run test_audio_amp.py, select option 22, and enter a full path such as:
  /tests/audio/voice_clonker.wav

voice_clonker.wav — synthetic spoken phrase: The Clonker ten thousand. Less sleek. More clonk. Systems ready.
voice_countdown.wav — synthetic spoken countdown.
mechanical_clatter.wav — synthetic layered impact, bounce, and rattle (not a real recording).
metallic_bell.wav — synthesized inharmonic metallic strike and decay.
musical_chords.wav — original multi-note chord sequence.
percussion_rhythm.wav — synthesized percussion rhythm with noisy transients.

Start with the voice at a comfortable level. Option 22 plays the WAV at its encoded amplitude; the v5 volume controls do not scale external WAV playback.
Keep the speaker clear of hard surfaces that can rattle.
