# THE CLONKER 10000
## Hardware & Physical Controls

**Design reference:** Updated October 19, 2026  
**Project:** The Clonker 10000  
**Current controller:** Raspberry Pi Pico 2 W  
**Firmware:** CircuitPython 10.3.1  
**Hardware status:** Bench prototype / component evaluation / physical controls not yet integrated

> A gloriously overengineered, tactile, Wi-Fi home theater remote. Two rotary controls, real buttons, questionable restraint, and absolutely no interest in becoming another touchscreen.

---

## 1. Hardware Philosophy

The Clonker 10000 is intended to be a substantial, tactile, purpose-built remote control for multiple home theater systems.

The design emphasizes:

- Physical controls that can be operated without looking.
- A prominent rotary volume control.
- A separate rotary selection control.
- Dedicated navigation and playback controls.
- Satisfying mechanical button action.
- A visually distinctive power control.
- A small, useful status display.
- Optional audible feedback.
- Wi-Fi control of configured AV equipment.
- A serviceable, expandable electronics architecture.
- An enclosure worthy of the name Clonker.

The hardware should feel deliberate and mechanically satisfying.

The software should remain flexible enough to accommodate changing equipment and control assignments without rewiring the entire remote.

**Design principle:** Physical controls generate generic events. Configuration determines what those events do.

## 1A. The Clonker Design Manifesto

**The Clonker 10000 is not a return to the past. It's a selective rescue operation.**

Once upon a time, remote controls had real buttons, satisfying mechanical feedback, and enough heft to remind you that you were holding an actual piece of equipment.

Unfortunately, they also had 117 buttons, six POWER switches, three mysterious INPUT selectors, and a row of controls nobody had touched since the Reagan administration.

Then came the modern remote: sleek, minimalist, and apparently designed for people with microscopic thumbs, perfect eyesight, and a deep emotional attachment to sponsored streaming services.

The Clonker rejects the worst of both eras.

### What we're keeping

- Big, substantial, tactile switches and beautiful metallic knobs.
- Essential controls that can be found and operated in pitch-black darkness.
- Mechanical feedback that leaves no doubt something happened.
- Repairability, accessible internals, and honest construction.
- Modern Wi-Fi connectivity and configurable network commands.
- Software-defined actions without a forest of dedicated buttons.
- Firmware updates and a readable configuration format.
- A healthy appreciation for vintage Hi-Fi equipment and nuclear submarines.

### What we're throwing overboard

- The 117-button remote with six different POWER buttons.
- Tiny rubber chiclets masquerading as controls.
- Sponsored streaming-service buttons.
- Sealed enclosures designed to discourage repairs.
- Microscopic screws requiring specialized tools and reading glasses.
- Complicated universal-remote programming rituals.
- Hunting through hundreds of manufacturer IR codes.
- Teaching one remote to blink at another remote.
- Elaborate activity wizards that lose their minds when someone manually changes an input.
- Any design decision made primarily because it looked fabulous in a marketing photograph.

### The Harmony Memorial Department

We respect the ambitious efforts of Logitech Harmony and the other universal-remote pioneers.

They were attempting to bring order to a spectacularly fragmented home theater industry.

We also remember the configuration software.

The Clonker keeps the useful idea — one configurable controller for multiple devices — and leaves the infrared archaeology behind.

Our initial design uses network commands and editable configuration instead of IR code libraries and synchronization rituals.

IR is not part of the current plan. Future optional support is not ruled out.

**We want to watch the movie, not spend Saturday teaching the remote what a movie is.**

### A Tip of the Hat to Accessibility

We applaud companies producing simplified, large-button remotes for seniors and people with accessibility needs.

They're solving real problems, and we're not trying to replace or compete with those products.

We're simply wondering why tactile, easy-to-find controls, sensible button counts, and straightforward operation shouldn't be desirable for everybody.

After all, you shouldn't have to qualify for a senior discount to get a volume button you can find in the dark.

**Accessibility isn't a niche feature. Sometimes it's just good engineering.**

### Serviceability, Clonker Style

The enclosure should be designed for maintenance, experimentation, and modification.

Possible features include:

- Actual lunchbox-style latches for opening the case.
- An accessible internal electronics workspace.
- A real internal work light.
- Convenient USB maintenance access.
- Clearly identified wiring and connectors.
- Room for future hardware experimentation.

These are design ideas, not finalized or implemented features.

The objective is to make the Clonker pleasant to own, operate, modify, and repair.

If servicing the remote requires holding a flashlight in your teeth while searching for microscopic screws, we've failed.

### The Bottom Line

The Clonker isn't retro.

It isn't minimalist.

It's **selectively maximalist**.

Maximum attention to the things that matter. Minimum tolerance for everything that doesn't.

**The Clonker 10000 — Less sleek. More CLONK.**

---

## 2. Current Controller Platform

### Active processor

**Raspberry Pi Pico 2 W**

- RP2350 microcontroller.
- Integrated Wi-Fi.
- CircuitPython 10.3.1.
- GPIO for physical controls.
- USB serial and filesystem access.
- Local HTTP management interface.
- JSON v2 configuration storage.

This is the active firmware and development platform.

The repository's current firmware is located under:

`firmware/clonker/`

### Earlier processor selection

**Unexpected Maker FeatherS3[D] — ESP32-S3**

Originally selected for the first Clonker prototype.

This board remains part of the project's hardware history and may be useful for future experimentation.

However:

- It is not the current production firmware target.
- The current firmware is written and tested for Pico 2 W.
- GPIO assignments must not be copied between platforms without verification.
- Earlier ESP32-S3 assumptions must not be treated as current implementation details.

The Pico 2 W is the authoritative hardware platform for the present development chapter.

---

## 3. Implemented Hardware: SERVICE / DEVICE Jumper

**Status: IMPLEMENTED AND TESTED**

The first functioning physical hardware input is the internal filesystem-ownership jumper.

### Electrical connection

| Signal | Pico GPIO | Physical pin |
|---|---|---|
| SERVICE/DEVICE input | GP17 | 22 |
| Ground | GND | 23 |

GP17 is configured with an internal pull-up.

### Jumper states

| Jumper | Mode | Filesystem ownership |
|---|---|---|
| Open | SERVICE (USB) | USB host writes |
| Connected to GND | DEVICE | Pico firmware writes |

Implementation:

`firmware/boot.py`

The jumper is read during boot.

In DEVICE mode, firmware executes:

```python
storage.remount("/", readonly=False)
```

The selection requires a full power cycle.

A CircuitPython soft reload is not sufficient to reliably change filesystem ownership.

### Final enclosure considerations

The SERVICE/DEVICE jumper should remain an internal maintenance control.

Possible final implementations include:

- Removable jumper.
- Recessed maintenance switch.
- Internal two-position slide switch.

**Final hardware: TBD**

It should not be confused with the user-facing CONFIG/RUN control.

---

## 4. Planned Physical Control Layout

The original design concept includes:

- Two rotary controls near the top.
- A large VOLUME knob.
- A smaller SELECTOR knob.
- Directional navigation controls.
- Dedicated playback and function buttons.
- A guarded system-power control.
- A small side-mounted room selector.
- A CONFIG/RUN control.
- Optional OLED status display.
- Optional audio feedback.

The layout is a design direction, not a finalized mechanical drawing.

### Proposed control arrangement

```text
             THE CLONKER 10000
        __________________________
       /                          \
      |   VOLUME       SELECTOR    |
      |      O             o       |
      |                            |
      |       [ STATUS OLED ]      |
      |                            |
      |             UP             |
      |              ^             |
      |       LEFT   OK   RIGHT    |
      |              v             |
      |            DOWN            |
      |                            |
      |        BACK    HOME        |
      |                            |
      |       <<   PLAY   >>       |
      |                            |
      |          [ MUTE ]          |
      |                            |
      |        [ POWER ]           |
      |       (guarded TBD)        |
      |____________________________|

        SIDE: ROOM SELECTOR TBD

        CONFIG/RUN: LOCATION TBD
```

This diagram is illustrative only.

Control spacing, button grouping, display placement, enclosure dimensions, and guard geometry remain open.

The final design should prioritize ergonomics and thumb reach over symmetry alone.

---

## 5. Volume Encoder

**Selected component: Grayhill 62A22-02-040C**

**Procurement status:** Ordered from DigiKey; delivery and physical testing not independently confirmed in this document.

### Associated knob

**Kilo OEJNI-90-3-5**

- Approximately 23.5 mm diameter.
- Silver / clear-matte appearance.
- Intended as the larger, visually dominant VOLUME knob.

### Intended behavior

The volume encoder generates directional steps:

- Clockwise: `volume-up`.
- Counterclockwise: `volume-down`.

The action dispatcher resolves the current room and configured target.

Typical initial target: Denon AVR.

The encoder itself should contain no Denon-specific logic.

### Initial firmware strategy

V1 should use one fundamental action per accepted encoder step.

Initially avoid:

- Volume acceleration.
- Large accumulated step batches.
- Complex velocity curves.
- Continuous network-command flooding.

These features may be evaluated after real-world responsiveness testing.

### Electrical integration

**TBD**

Before wiring:

- Verify the encoder's actual electrical interface and pinout.
- Confirm required supply voltage and current.
- Determine appropriate signal conditioning.
- Verify compatibility with Pico 2 W GPIO voltage limits.
- Confirm whether additional interface circuitry is required.

Do not assume that an optical encoder is electrically interchangeable with a simple mechanical quadrature encoder.

### Firmware status

- GPIO assignment: TBD.
- Driver: Not implemented.
- Physical step testing: Pending.
- Network command testing: Pending.

---

## 6. Selector Encoder

**Selected component: Bourns PEC11R-4215F-S0024**

**Procurement status:** Ordered from DigiKey; installation and testing pending confirmation.

### Associated knob

**Kilo OEJL-63-4-7**

- Small black knob.
- White position indicator.
- Intended to contrast with the larger silver VOLUME knob.

### Intended behavior

The selector encoder is reserved for context-dependent selection.

Possible uses include:

- Cycling available custom actions.
- Navigating a small OLED menu.
- Selecting a function or operating context.
- Adjusting future user-facing options.

The final behavior has not been decided.

### Push-switch behavior

Any integrated encoder push-switch functionality must be verified against the actual purchased part and datasheet before assigning a function.

Do not assume an additional push action exists or is wired.

### Electrical and firmware status

- GPIO A: TBD.
- GPIO B: TBD.
- Push-switch GPIO, if used: TBD.
- Debounce and step decoding: Not implemented.
- UI behavior: TBD.

---

## 7. Navigation Controls

Clonker defines five primary navigation actions:

- `nav-up`
- `nav-down`
- `nav-left`
- `nav-right`
- `select`

The physical design should provide an intuitive directional arrangement with a central selection control.

### Candidate implementation

A five-button directional cluster:

```text
             UP
              ^
              |
       LEFT - OK - RIGHT
              |
              v
             DOWN
```

This may be implemented using:

- Individual tactile switches.
- A purpose-built navigation assembly.
- A mechanically linked directional control.

**Final hardware: TBD**

### Firmware behavior

Each press produces a generic action event.

The current room configuration determines the target and HTTP command.

For example, navigation may be mapped to Roku POST commands.

The physical navigation layer must not hardcode Roku URLs.

### Open design questions

- Button type and travel.
- Actuation force.
- Mechanical spacing.
- Single-click versus long-press behavior.
- Repeat behavior while held.
- Debounce timing.
- Whether the navigation assembly is illuminated.

No navigation buttons have yet been integrated into the Pico firmware.

---

## 8. Function and Playback Buttons

Clonker's fourteen fundamental actions do not require fourteen dedicated physical buttons.

The current physical design direction includes convenient access to:

- Back.
- Home.
- Play/Pause.
- Skip Back.
- Skip Forward.
- Mute Toggle.
- Power Toggle.

Some actions may eventually be accessed through the selector encoder or OLED menu.

### Known candidate button hardware

**Adafruit #3347 metal ball tactile momentary switches**

Previously ordered for experimentation.

Possible uses:

- Navigation functions.
- Playback functions.
- Secondary action buttons.

Final assignments are not established.

### Additional switches

**NEW SWITCH INVENTORY — TBD**

Additional switches have been acquired or selected but have not yet been documented with photographs, model numbers, or electrical specifications.

Reserve the following entries:

| Placeholder | Proposed purpose | Status |
|---|---|---|
| New Switch A | TBD | Awaiting identification |
| New Switch B | TBD | Awaiting identification |
| New Switch C | TBD | Awaiting identification |
| Additional switches | TBD | Inventory update pending |

These placeholders are intentionally noncommittal.

Do not infer switch type, rating, illumination, latching behavior, or pinout until the parts are identified.

---

## 9. System Power Control

**Design status: UNDER ACTIVE EVALUATION**

One of Clonker's signature features is a prominent system-power control.

The intended experience is mechanically satisfying and visually distinctive.

The original concept involved a guarded, race-car-style control.

### Important architectural distinction

The system-power control is an external equipment action.

It invokes the configurable fundamental action:

`power-toggle`

It is not the same as:

- SERVICE/DEVICE.
- CONFIG/RUN.
- Pico power supply control.
- A firmware reset switch.

### Current action model

The JSON v2 configuration defines:

```json
{
  "target": "avr",
  "method": "GET",
  "on_path": "/example/on",
  "off_path": "/example/off"
}
```

The paths above are illustrative, not actual equipment commands.

The future dispatcher will select ON or OFF according to independent RAM command history.

The toggle-state algorithm is not yet implemented.

### Guarded momentary concept

The preferred direction has included:

- A flip-up protective guard.
- A momentary pushbutton beneath the guard.
- A distinctive mechanical action.
- Optional illumination.
- A button tall enough to operate comfortably with the guard open.

The final guard/button combination has not been selected.

### Known candidate hardware

**FILN 19 mm black ring-illuminated momentary pushbutton**

Previously ordered as a three-pack for experimentation.

Reported characteristics:

- Black metal-style housing.
- Momentary / self-reset operation.
- Illuminated ring.
- Advertised 12 V / 24 V LED illumination.
- Approximately 19 mm mounting diameter.

This is a candidate, not the final selected power button.

### Electrical caution

The switch contacts and LED illumination are separate electrical considerations.

The Pico 2 W GPIO must not be used to directly supply a 12 V or 24 V illumination circuit.

Any illumination implementation requires an appropriate power source and driver arrangement.

Switch contact wiring, common terminals, and polarity must be verified before connecting to GPIO.

### New power-switch candidates

**TBD — awaiting photographs and specifications.**

Future evaluation should compare:

- Guard compatibility.
- Button height.
- Momentary versus maintained operation.
- Mechanical feel.
- Mounting diameter.
- Contact configuration.
- Illumination voltage.
- Overall appearance.
- Enclosure clearance.

No final power-switch hardware decision is recorded here.

---

## 10. CONFIG / RUN Control

**Status: Firmware mode logic implemented; physical control TBD.**

CONFIG/RUN is a separate internal application mode.

### CONFIG

Enables Clonker's browser management interface.

### RUN

Disables the browser management listener while preserving the intended remote-control application.

### Current implementation

`firmware/clonker/controls/switches.py`

Currently:

```python
_simulated_config = True
```

The mode is simulated because:

```python
CONFIG_SWITCH_PIN = None
```

The future physical implementation will replace this simulation.

### Proposed hardware

A maintained two-position switch.

Previous design discussions included a guarded race-car-style switch for this purpose.

However, the final hardware assignment remains open.

**CONFIG/RUN SWITCH: TBD**

### Requirements

The control must:

- Produce a stable logical state.
- Be read at runtime.
- Avoid accidental mode changes.
- Avoid flash writes on every poll.
- Start or stop the management server only on transitions.
- Not send an AV equipment HTTP command.
- Remain electrically independent of the GP17 SERVICE/DEVICE jumper.

The final GPIO, polarity, debounce, and mounting location are TBD.

See [Operating Modes](OPERATING_MODES.md).

---

## 11. Physical Room Selector

**Design status: Candidate hardware ordered; behavior not finalized.**

The room selector determines which configured room receives fundamental actions.

The current browser Test Remote already supports selecting a room.

The physical remote needs an equivalent selection mechanism.

### Original proposed positions

```text
DEN  /  BOTH  /  SUNROOM
```

The middle BOTH position is a proposed group-control mode.

It is not one of the three JSON room IDs.

The JSON configuration contains:

- `room-1` — Den.
- `room-2` — Sunroom.
- `room-3` — third room / placeholder.

How a physical BOTH selection interacts with the third configured room remains a design decision.

### Candidate hardware

**uxcell three-position DPDT slide switch assortment**

Previously ordered for experimentation.

Intended as a small side-mounted selector.

Final switch selection is not confirmed.

### Firmware considerations

The current placeholder pins are:

```python
ROOM_SELECTOR_A_PIN = None
ROOM_SELECTOR_B_PIN = None
```

The implementation will need to distinguish switch positions reliably.

Depending on the final switch contact arrangement, it may require:

- Two GPIO inputs.
- Pull-up or pull-down configuration.
- Defined behavior for transitions.
- Debounce or stable-position detection.

### BOTH behavior

**TBD**

Questions include:

- Send an action to both configured rooms?
- Sequential versus independent dispatch?
- Failure behavior if one room is unreachable?
- Whether volume commands should affect both rooms.
- Whether power toggles should operate both rooms.
- How per-room toggle command history is maintained.
- Whether BOTH applies to all fundamental actions.

Do not implement group semantics until these decisions are made.

---

## 12. OLED Status Display

**Status: Proposed / candidate hardware discussed.**

Candidate display:

**0.49-inch SSD1306 OLED, 64 × 32 pixels, I2C**

The small display is intended to provide compact status information without turning Clonker into a touchscreen.

### Possible displayed information

- Selected room.
- Current action context.
- Selected custom action.
- CONFIG/RUN status.
- Wi-Fi connection status.
- Brief command feedback.

### Design priorities

- Legible at arm's length.
- Minimal menu complexity.
- Low update overhead.
- No requirement to look at the display for ordinary volume or navigation.
- Graceful operation if the display is absent.

### Implementation status

- Final display selection: TBD.
- I2C pin assignments: TBD.
- Driver integration: Not implemented.
- Menu system: Not implemented.
- Screen layout: TBD.

The OLED is optional for initial real-device HTTP control testing.

---

## 13. Audible Feedback

**Status: Components ordered / concept evaluation; firmware integration pending.**

Clonker may provide short audible feedback for selected interactions.

### Known components

**Adafruit piezo element — PS1240, PID 160**

Candidate for simple tones or beeps.

**Adafruit MAX98357A I2S amplifier — PID 3006**

Candidate for richer audio output.

**MECCANIXITY 23 mm, 8 ohm, 1 watt mini speakers**

Two-pack ordered for experimentation.

### Potential uses

- Startup sound.
- Power-action confirmation.
- Mode-change feedback.
- Short error tone.
- Signature Clonker sound.

### Design constraints

- Audio feedback must not delay physical input handling.
- Volume should be appropriate for a handheld remote.
- Sounds should be brief and optional.
- Speaker/amplifier power requirements must be verified.
- GPIO and I2S pin assignments are TBD.

The initial real-device command implementation does not depend on audio feedback.

---

## 14. Breadboard and Wiring Inventory

The following supporting components were previously ordered for development.

| Component | Purpose |
|---|---|
| Adafruit 830-tie breadboard, PID 239 | Prototyping |
| Dupont jumper assortment | Temporary interconnects |
| Ledvillage 22 AWG solid-core wire assortment | Breadboard wiring |
| WG-026 alligator leads | Temporary testing |
| ALLECIN resistor assortment | Pull-ups, pull-downs, LED circuits |
| 300-piece 3 mm / 5 mm LED assortment | Visual experiments |
| Soldering iron | Permanent assembly work |

Existing personal parts bins may provide additional components.

This is an inventory reference, not a guarantee that every item has been received, inspected, or tested.

---

## 15. Current Firmware GPIO Map

Source:

`firmware/clonker/controls/pins.py`

Current definitions:

```python
CONFIG_SWITCH_PIN = None

ROOM_SELECTOR_A_PIN = None
ROOM_SELECTOR_B_PIN = None

VOLUME_ENCODER_A_PIN = None
VOLUME_ENCODER_B_PIN = None

SELECT_ENCODER_A_PIN = None
SELECT_ENCODER_B_PIN = None
```

### Assignment status

| Control | GPIO assignment | Status |
|---|---|---|
| SERVICE/DEVICE jumper | GP17 | Implemented |
| CONFIG/RUN switch | TBD | Simulated |
| Room selector A | TBD | Not implemented |
| Room selector B | TBD | Not implemented |
| Volume encoder A | TBD | Not implemented |
| Volume encoder B | TBD | Not implemented |
| Selector encoder A | TBD | Not implemented |
| Selector encoder B | TBD | Not implemented |
| Navigation buttons | TBD | Not implemented |
| Playback buttons | TBD | Not implemented |
| Mute button | TBD | Not implemented |
| System power button | TBD | Not implemented |
| OLED I2C | TBD | Not implemented |
| I2S audio | TBD | Not implemented |
| Indicator LEDs | TBD | Not implemented |

Do not assign pins solely for documentation convenience.

The final map should be determined after reviewing all electrical interfaces, available GPIO, and physical wiring constraints.

---

## 16. Fundamental Action Vocabulary

The firmware defines fourteen fixed fundamental action IDs per room.

| Action ID | Purpose |
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
| `play-pause` | Play / pause |
| `skip-back` | Skip backward |
| `skip-forward` | Skip forward |
| `power-toggle` | Toggle equipment power |

The IDs are fixed in firmware.

Each room configures its own target, HTTP method, and command path or paths.

Ordinary actions use:

- `target`
- `method`
- `path`

Mute and power toggles use:

- `target`
- `method`
- `on_path`
- `off_path`

A blank command path or unconfigured target endpoint is valid and represents a no-op.

### Physical mapping

There is no requirement for fourteen individual physical buttons.

Encoders, dedicated buttons, menus, and future user-defined functions can share the fundamental action vocabulary.

The physical input layer must remain separate from device-specific HTTP command syntax.

---

## 17. Physical Input Software Architecture

The intended event path is:

```text
Physical switch / encoder
          |
          v
GPIO input sampling
          |
          v
Debounce / step decoding
          |
          v
Generic control event
          |
          v
Room selection
          |
          v
actions.dispatch()
          |
          v
Current JSON v2 configuration
          |
          v
Outbound HTTP transport
          |
          v
Configured AV equipment
```

### Current implementation boundary

The browser Test Remote already calls:

```python
actions.dispatch(room_id, action_id)
```

The dispatcher currently validates and logs requests.

It does not send real outbound HTTP commands yet.

Physical GPIO capture has not been connected to the dispatcher.

### Scheduling requirements

The physical input layer should:

- Detect button transitions reliably.
- Decode encoder direction accurately.
- Avoid blocking delays.
- Preserve responsiveness during network operations.
- Avoid repeated actions caused by contact bounce.
- Define behavior for held buttons.
- Handle invalid or disconnected controls safely.

### Configuration ownership

Physical control mappings should use validated runtime configuration wherever appropriate.

GPIO assignments and electrical pin definitions remain developer-controlled firmware settings.

They are not ordinary user-editable JSON configuration fields.

---

## 18. Electrical Design Rules

Before connecting new hardware to the Pico:

1. Verify the component's actual part number and datasheet.
2. Identify contact terminals, common pins, and illumination terminals.
3. Confirm whether the control is momentary or maintained.
4. Verify required operating voltage.
5. Verify the Pico's 3.3 V GPIO compatibility.
6. Use suitable pull-ups, pull-downs, and current-limiting components.
7. Provide a proper driver for higher-voltage LEDs or other loads.
8. Avoid floating GPIO inputs.
9. Confirm power and ground connections before energizing the circuit.
10. Test one new control at a time.

Never connect a 12 V or 24 V illumination supply directly to a Pico GPIO.

The optical volume encoder deserves particular attention because its interface may require more than the wiring used for a mechanical encoder.

---

## 19. Future Hardware Inventory Updates

This document intentionally reserves room for additional switch and enclosure decisions.

### Newly acquired switches

**Awaiting user photographs and identification.**

For each new component, record:

- Manufacturer and model.
- Photographs.
- Quantity.
- Purchased / received / tested status.
- Momentary or maintained operation.
- Contact arrangement.
- Illumination requirements, if applicable.
- Mounting diameter and depth.
- Guard compatibility.
- Proposed Clonker function.
- Final GPIO assignment when decided.

### Open mechanical decisions

- Final enclosure material.
- Enclosure dimensions.
- Volume and selector knob spacing.
- Navigation cluster design.
- Power guard and button pairing.
- CONFIG/RUN switch style and placement.
- Room selector location.
- OLED mounting.
- Speaker grille or sound opening.
- Battery versus external power architecture.
- Charging and power management.
- USB maintenance access.

No final enclosure or PCB design is implied by this document.

---

## 20. Hardware Development Sequence

Recommended sequence after the initial outbound HTTP action milestone:

1. Confirm real device commands work through the browser Test Remote.
2. Finalize the initial GPIO allocation.
3. Wire and test one simple momentary button.
4. Connect that button to the shared action dispatcher.
5. Verify responsive behavior during HTTP requests.
6. Wire and test the Bourns selector encoder.
7. Verify the Grayhill optical encoder electrical requirements.
8. Wire and test the volume encoder.
9. Implement the physical room selector.
10. Implement and test CONFIG/RUN switching.
11. Evaluate mute, playback, and navigation button arrangements.
12. Finalize the guarded system-power control.
13. Integrate OLED and audio feedback if desired.
14. Refine the enclosure and permanent wiring.

This sequence is a recommendation, not a commitment to a fixed build order.

The new switch inventory may change priorities.

---

## 21. Current Hardware Milestone

**As of October 19, 2026:**

### Working

- Pico 2 W running CircuitPython.
- Wi-Fi connectivity.
- USB serial / REPL.
- GP17 SERVICE/DEVICE jumper.
- JSON v2 configuration.
- Browser management interface.
- Browser Test Remote.
- Logging-only action dispatcher.

### Available or previously ordered for evaluation

- Grayhill optical volume encoder.
- Kilo large volume knob.
- Bourns selector encoder.
- Kilo small selector knob.
- Adafruit metal tactile buttons.
- FILN illuminated momentary switches.
- uxcell three-position slide switches.
- Piezo element.
- MAX98357A amplifier.
- Mini speakers.
- Breadboard and wiring supplies.

### Pending

- Newly acquired switch identification.
- Final switch assignments.
- GPIO mapping.
- Physical button and encoder integration.
- Real outbound HTTP commands.
- Power-control hardware decision.
- OLED integration.
- Audio feedback.
- Final enclosure.

**The electronics architecture is taking shape. The physical monster is still being assembled.**

---

## 22. Related Documents

- [Architecture](ARCHITECTURE.md)
- [Configuration & Recovery](CONFIGURATION.md)
- [Firmware, HTTP & Clock](FIRMWARE_NETWORK.md)
- [Operating Modes](OPERATING_MODES.md)
- [Development & Deployment](DEVELOPMENT.md)
- [Configuration Testing](configuration-testing.md)
- [Chapter 2 Handoff](CHAPTER_2_HANDOFF.md)

---

**CLONK! ⚡🔩**

*The Clonker 10000 — because apparently a normal remote control wasn't complicated enough.*
