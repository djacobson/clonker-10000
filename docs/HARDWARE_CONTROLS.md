# Hardware & Physical Controls

**Design reference · 15 October 2026**

## Active processor

**Raspberry Pi Pico 2 W (RP2350)** running CircuitPython 10.3.1. Earlier Unexpected Maker FeatherS3[D] / Feather ESP32 experiments are historical, not the active firmware target.

## Confirmed service jumper

- **GP17**, physical Pico pin **22**, internal pull-up.
- **GND**, physical pin **23**.
- **Open:** SERVICE (USB) mode; host can write CIRCUITPY.
- **Grounded:** DEVICE mode; firmware can write CIRCUITPY.
- Jumper sampled in `boot.py` at cold boot. **Power cycle** to change mode.

## Physical design direction (not yet integrated)

- Dedicated physical pushbutton for the configurable
  `power-toggle` fundamental action.
- Guarded race-car-style switch for internal CONFIG/RUN mode.
  This switch changes firmware state and does not send HTTP commands.
- CONFIG/RUN GPIO pin and polarity remain TBD.

## Action vocabulary (proposed)

`NAV_UP`, `NAV_DOWN`, `NAV_LEFT`, `NAV_RIGHT`, `NAV_SELECT`, `BACK`, `HOME`, `REWIND`, `PLAYPAUSE`, `FFWD`, `VOLUME_UP`, `VOLUME_DOWN`, `MUTE`, `POWER`, `MODE_1`, `MODE_2`, `MODE_3`, `STATUS`, `INFO`.

Physical switch positions are authoritative state and are not continuously written to flash. Encoders produce step/direction events; debounce mechanical controls; avoid a blocking HTTP command for each electrical transition. Exact pin map and input implementation are pending.
