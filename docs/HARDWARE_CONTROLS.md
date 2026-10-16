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

## Fundamental command vocabulary

Clonker defines fourteen fundamental command IDs per room.

| Command ID | Function |
|---|---|
| `volume-up` | Increase volume |
| `volume-down` | Decrease volume |
| `mute-toggle` | Toggle mute |
| `nav-up` | Navigate up |
| `nav-down` | Navigate down |
| `nav-left` | Navigate left |
| `nav-right` | Navigate right |
| `select` | Select / OK |
| `back` | Navigate back |
| `home` | Return home |
| `play-pause` | Toggle playback |
| `skip-back` | Skip backward |
| `skip-forward` | Skip forward |
| `power-toggle` | Toggle external equipment power |

Fundamental command IDs are fixed and developer-defined. Each room must contain all fourteen commands.

Each command has three configurable properties:

- `target`: `tv`, `avr`, or `streaming`
- `method`: `GET` or `POST`
- `path`: HTTP command path

A fundamental command may intentionally do nothing. An empty path or an unconfigured target IP is valid and produces a no-op.

The command vocabulary describes available functions, not mandatory capabilities of every room or device.

## User-defined commands

User-defined commands are intended for additional functions outside the fourteen fundamental commands.

Unlike fundamental commands, their identities and names will be supplied by the user.

The guiding model remains simple HTTP commands, not a scripting language or graphical shortcut editor.

User-defined commands are reserved for future implementation. Configuration v2 currently requires an empty `custom_actions` array for each room.

## Internal controls versus HTTP commands

The CONFIG/RUN switch controls Clonker's own operating state.

- CONFIG enables the browser configuration service.
- RUN disables the browser configuration service.
- Changing CONFIG/RUN does not send an HTTP command.
- CONFIG/RUN is not a fundamental or user-defined command.

The dedicated Power Toggle pushbutton is different: it invokes the configurable `power-toggle` fundamental command.

The SERVICE (USB) / DEVICE jumper is another independent internal control, determining filesystem write ownership at boot.

## Physical input implementation

Physical switch positions are authoritative and are not continuously written to flash.

Encoders produce step/direction events. Mechanical controls require appropriate debounce.

Input capture must remain responsive even when network operations are pending.

The exact GPIO map, button assignments, encoder handling, and room-selector behavior remain under development.

The fourteen fundamental command IDs do not require fourteen dedicated physical buttons. Physical controls may invoke commands according to the eventual control mapping.
