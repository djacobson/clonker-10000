CLONKER 10000 — Audio Laboratory V2
===================================
All WAV files: mono, 16,000 samples/sec, 16-bit PCM. Copy to Pico /tests/audio/.
Run Audio Laboratory v5 option 22 and type the full path, for example:
/tests/audio/female_synthetic_systems_ready.wav

VOICE NOTE: The four female_synthetic_* files use an offline female-styled
synthetic voice (eSpeak), NOT a recording or a modern natural-sounding TTS
voice. They are useful for speech clarity but will still sound robotic.
A real natural female voice recording is a separate future audition.

FILES:
female_synthetic_systems_ready.wav — “The Clonker ten thousand. Systems ready.”
female_synthetic_soft.wav — “Hello there. Ready when you are.”
female_synthetic_clonk.wav — “Clonk! Mission accomplished.”
female_synthetic_confirmations.wav — “Ready. Done. Power on.”
mechanical_clatter_original.wav — prior test baseline
mechanical_clatter_louder.wav — peak normalized to ~70% full scale
mechanical_clatter_maximum_clean.wav — peak normalized to ~92% full scale
percussion_rhythm_original.wav — prior test baseline
percussion_rhythm_louder.wav — peak normalized to ~70% full scale
percussion_rhythm_maximum_clean.wav — peak normalized to ~92% full scale
short_mechanical_clonk.wav — newly synthesized noise-rich impact (not a real recording)

Volume changes are peak normalization, not dynamic range compression.
If a source is already louder than the target, the resulting version can be
quieter; compare by ear. Avoid playback with speaker near ears.
