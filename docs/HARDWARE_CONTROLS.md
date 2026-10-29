# THE CLONKER 10000
## Hardware & Physical Controls

**Design reference:** Updated October 29, 2026  
**Controller:** Raspberry Pi Pico 2 W (RP2350) / CircuitPython 10.3.1  
**Firmware baseline:** Chapter 5 — physical GPIO initialization, button polling, and live application-mode switching operational  
**Hardware baseline:** GP17 boot-mode switch, GP18 CONFIG/RUN switch, and GP2 momentary button tested

> A gloriously overengineered, tactile, Wi-Fi home theater remote. Two rotary controls, real buttons, questionable restraint, and absolutely no interest in becoming another touchscreen.

---

## 1. Purpose and hardware philosophy

The Clonker 10000 is a substantial, serviceable, purpose-built remote for multiple home theater systems.

The goal is tactile operation without constantly looking down: a prominent volume knob, a separate custom-action selector, dedicated navigation and function buttons, and an unmistakable power control. Optional display and audible feedback may improve usability without becoming dependencies.

**Core boundary:** Physical controls produce generic events. The selected room and validated configuration determine the action and network destination. GPIO drivers must not embed Denon or Roku commands.

This document is the hardware design and implementation reference. Configuration schema, HTTP behavior, and scheduling details belong in [Configuration](CONFIGURATION.md), [Architecture](ARCHITECTURE.md), and [Firmware, HTTP & Clock](FIRMWARE_NETWORK.md).

Procurement records distinguish *ordered or candidate* from *received, installed, electrically verified,* and *tested*. Purchasing a component does not establish that it works.

## 2. The Clonker Design Manifesto

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

We respect the ambitious efforts of Logitech Harmony and the other universal-remote pioneers. They were attempting to bring order to a spectacularly fragmented home theater industry. We also remember the configuration software.

The Clonker keeps the useful idea—one configurable controller for multiple devices—and leaves the infrared archaeology behind.

Initial control uses network commands and editable configuration, not IR libraries or synchronization rituals. IR is not on the current implementation path, though future optional support is not ruled out.

**We want to watch the movie, not spend Saturday teaching the remote what a movie is.**

### A tip of the hat to accessibility

We applaud companies producing simplified, large-button remotes for seniors and people with accessibility needs. They're solving real problems, and we're not trying to replace or compete with those products.

We're simply wondering why tactile, easy-to-find controls, sensible button counts, and straightforward operation shouldn't be desirable for everybody.

After all, you shouldn't have to qualify for a senior discount to get a volume button you can find in the dark.

**Accessibility isn't a niche feature. Sometimes it's just good engineering.**

### Serviceability, Clonker style

Possible enclosure features include actual lunchbox-style latches, accessible internal electronics, an internal work light, convenient USB maintenance access, labeled wiring and connectors, and space for future experiments.

These are concepts, **not finalized enclosure features**.

If servicing the remote requires holding a flashlight in your teeth while searching for microscopic screws, we've failed.

The Clonker isn't retro. It isn't minimalist. It's **selectively maximalist**: maximum attention to the things that matter; minimum tolerance for everything that doesn't.

**The Clonker 10000 — Less sleek. More CLONK.**

---

## 3. Controller and verified hardware

### Active controller

**Raspberry Pi Pico 2 W**, RP2350, integrated Wi-Fi, running CircuitPython 10.3.1.

The Pico provides USB serial/filesystem maintenance, GPIO inputs, and the operational Config v4 browser/HTTP firmware under `firmware/clonker/`.

The earlier **Unexpected Maker FeatherS3[D] / ESP32-S3** selection is historical. Its pinout, sleep behavior, and firmware assumptions must not be transferred to the Pico without verification.

### GP17 boot-mode switch — implemented and tested

The former removable GP17 jumper has been replaced by a permanent two-position physical toggle switch.

| Connection | Pico physical pin | Behavior |
|---|---:|---|
| GP17, internal pull-up | 22 | Boot-time filesystem ownership |
| GND | 23 | Common ground |

| Switch position | GP17 state | Boot mode | Filesystem writer |
|---|---|---|---|
| OFF / open | HIGH | SERVICE (USB) | USB host |
| ON / grounded | LOW | DEVICE | Pico firmware |

`firmware/boot.py` reads the switch during boot. DEVICE mode remounts the filesystem writable for the Pico, enabling configuration persistence.

The source variable is named `boot_mode_switch`, replacing the historical jumper terminology.

Expected boot diagnostics:

```text
CLONKER BOOT: SERVICE (USB) mode (switch OFF)
CLONKER BOOT: DEVICE mode (switch ON)
```

**Changing boot mode requires a full power cycle.** Do not rely on Ctrl+D to change filesystem ownership, and do not change the switch while powered.

SERVICE (USB)/DEVICE is independent of the application's CONFIG/RUN mode.

See [Operating Modes](OPERATING_MODES.md) for filesystem ownership and deployment procedures.

### GP18 CONFIG/RUN switch — implemented and tested

A maintained, guarded physical switch now selects the application operating mode.

| Connection | GPIO | Function |
|---|---|---|
| Switch signal | GP18 | Application-mode input |
| Switch common | GND | Ground reference |

The input uses the Pico's internal pull-up.

| Switch electrical state | Application mode | Management listener |
|---|---|---|
| Open / HIGH | RUN | Stopped |
| Grounded / LOW | CONFIG | Running |

The switch was initially wired through the breadboard, with its large screw terminals making it particularly appropriate for the Monster's industrial aesthetic.

The implementation uses:

- `firmware/clonker/controls/pins.py` — `CONFIG_SWITCH_PIN = 18`.
- `firmware/clonker/controls/switches.py` — physical mode selection.
- `firmware/clonker/main.py` — detects changes and starts/stops the management HTTP listener.

**Verified live behavior:**

1. RUN — browser Config page becomes unavailable on refresh.
2. CONFIG — browser Config page becomes accessible.
3. RUN again — browser Config page becomes unavailable.
4. CONFIG again — browser Config page becomes accessible.

These transitions require **no reboot**.

The action queue continues operating independently of whether the management listener is enabled.

Serial diagnostics use:

```text
App mode source = PHYSICAL
App mode = CONFIG
App mode = RUN
```

Changing application mode must not transmit an AV power command or unnecessarily write configuration data.

### GP2 momentary power button — input tested

The first physical action button is connected to **GP2**.

`POWER_TOGGLE_PIN = 2` is assigned in `firmware/clonker/controls/pins.py`.

The button driver and physical coordinator detect and log press/release events.

**Verified:** GPIO initialization, physical button operation, debounce/event reporting, and continued browser responsiveness.

**Not yet implemented:** Dispatching the button event as a room-specific `power-toggle` action.

This distinction is important. A working button input is not yet a working physical theater-power control.

Room selection will establish the missing context before connecting this button to the shared action dispatcher.

### Physical GPIO subsystem — Chapter 5 foundation

The firmware contains a dedicated physical-control subsystem:

- `firmware/clonker/controls/physical.py` — physical input initialization and polling.
- `firmware/clonker/controls/buttons.py` — momentary button input handling.
- `firmware/clonker/controls/switches.py` — maintained application-mode selection.
- `firmware/clonker/controls/pins.py` — central GPIO assignments.
- `firmware/clonker/main.py` — cooperative scheduler integration.
- `PHYSICAL_CONTROLS_ENABLED` — development-time enable/disable flag.

The subsystem follows a deliberately simple lifecycle:

1. Initialize enabled physical controls once during application startup.
2. Record initialization success or failure.
3. Poll physical controls cooperatively, ahead of queued-action execution.
4. Do not repeatedly initialize hardware or require hot-plug detection.
5. Restart the application when changing GPIO assignments or hardware connections.

The physical polling target is approximately 10 ms, **not a guaranteed sampling interval**. Synchronous outbound HTTP can temporarily block the cooperative loop.

#### Brain-only mode

`PHYSICAL_CONTROLS_ENABLED = False` disables the optional physical-control initialization and polling path.

The browser configuration interface, Test Remote, shared Dumb Queue™, and outbound HTTP transport remain usable.

The GP17 boot-mode switch is handled separately by `boot.py`.

Application-mode selection is also a distinct concern; the GP18 switch should not be confused with the ordinary physical-action buttons.

#### Initialization and failure policy

A missing or failed noncritical control should not prevent the rest of Clonker from starting.

Individual controls should fail independently wherever practical. An initialized GPIO input does not necessarily prove a mechanical switch is connected.

Initial input states must not generate unintended button actions.

Hot-plug detection and automatic reinitialization are not requirements.

### Chapter 5 GPIO foundation verification — October 28–29, 2026

| Test | Result |
|---|---|
| Physical controls disabled | PASS — brain-only startup |
| CONFIG listener with controls disabled | PASS |
| Sunroom Home with controls disabled | PASS — HTTP 200 |
| Physical controls enabled | PASS — startup |
| CONFIG listener with controls enabled | PASS |
| Sunroom Home with controls enabled | PASS — HTTP 200 |
| GP2 press/release detection | PASS |
| Browser responsiveness with GP2 enabled | PASS |
| GP17 physical boot-mode selection | PASS |
| GP18 live CONFIG/RUN transitions | PASS |
| GP2 room-specific action dispatch | NOT YET IMPLEMENTED |

These tests establish the foundation for real hardware input without claiming that the remaining controls are operational.

**The Monster has a nervous system. Some of the nerve endings now work.**

---

## 4. Proposed control layout

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
        CONFIG/RUN: GUARDED SWITCH
        SERVICE (USB)/DEVICE: BOOT SWITCH
```

**Concept only.** Dimensions, ergonomics, button spacing, mounting depths, guard clearance, and display position are not fixed.

Thumb reach and tactile identification take precedence over decorative symmetry.

The current breadboard arrangement is an electrical prototype, not the final enclosure layout.

## 5. Primary rotary controls

### Volume — Grayhill 62A22-02-040C

**Selected for evaluation / ordered from DigiKey; electrical testing not confirmed in this reference.**

Associated large silver/clear-matte knob: **Kilo OEJNI-90-3-5**, approximately 23.5 mm diameter.

- Clockwise: generic `volume-up`.
- Counterclockwise: generic `volume-down`.
- Initial behavior: one action per accepted step.
- Avoid acceleration, batching, or aggressive network repeat until responsiveness is measured.
- Encoder driver, wiring, GPIO assignment, and physical tests are not implemented.

**Critical electrical check:** Verify the Grayhill encoder's actual datasheet, pinout, power requirements, signal type, and 3.3 V GPIO compatibility.

An optical encoder must not be assumed equivalent to a passive mechanical quadrature encoder. Interface circuitry may be necessary.

Future investigation includes detent behavior, decoding, repeat rate, command backlog, and interaction with the cooperative queue.

### Custom-action selector — Bourns PEC11R-4215F-S0024

**Selected for evaluation / ordered from DigiKey; installation and testing not confirmed.**

Associated smaller black knob with white indicator: **Kilo OEJL-63-4-7**.

The preferred intended role is:

- Rotate to cycle through the selected room's configured custom actions.
- Press the encoder's momentary switch to execute the selected action.

The encoder is nonpositional: selection is maintained by software rather than by a fixed mechanical angle.

The initial implementation should remain simple. No elaborate menu system or encoder acceleration is required.

GPIO A/B, push-switch GPIO, step decoding, and debounce remain unimplemented.

The encoder must produce generic selection/activation events, not device-specific URLs.

## 6. Navigation, playback, and function buttons

The desired navigation cluster is **UP / DOWN / LEFT / RIGHT / OK**, intuitive by touch.

Candidates include individual tactile switches, a purpose-built directional assembly, or a mechanically linked cluster. The final arrangement is not yet selected.

Other intended controls include Back, Home, Play/Pause, Skip Back, Skip Forward, Mute, and guarded power.

The fourteen firmware fundamentals **do not require fourteen dedicated physical buttons**.

**Candidate tactile hardware:** Adafruit **#3347 metal-ball momentary switches**, ordered for experimentation.

Open decisions include switch travel, force, spacing, repeat policy, debounce, illumination, and mechanical layout.

Held navigation buttons must not flood the network.

### Generic action vocabulary

The current fourteen fixed action IDs are:

| Category | IDs |
|---|---|
| Volume | `volume-up`, `volume-down`, `mute-toggle` |
| Navigation | `nav-up`, `nav-down`, `nav-left`, `nav-right`, `select`, `back`, `home` |
| Playback | `play-pause`, `skip-back`, `skip-forward` |
| Equipment power | `power-toggle` |

Config v4 also supports room-specific executable custom actions, including multi-step GET/POST commands and cooperative waits.

Physical controls should invoke fundamental or custom actions through the **same shared dispatcher** already used by the browser Test Remote.

**Toggle boundary:** Configured ON/OFF paths for mute and power are operational through the dispatcher, with independent volatile direction histories per room and action.

The browser Test Remote exercised these commands successfully on October 27, 2026.

Command history is not authoritative equipment state. Other remotes, HDMI-CEC, applications, and manual controls can change equipment state independently.

---

## 7. SYSTEM MASTER: guarded power and ignition concept

**Design status: Provisionally agreed October 20, 2026; sleep/wake behavior not implemented or tested.**

This is a signature feature and deserves its own design record.

The guarded **SYSTEM MASTER momentary button** is intended to perform two logically distinct jobs:

1. While Clonker is awake, invoke the configured `power-toggle` action for the selected room.
2. When Clonker is in deep sleep, wake the controller and, **only if the wake cause is reliably identified**, initiate a single theater-power ON action.

SYSTEM MASTER is **not** GP17 filesystem ownership, GP18 CONFIG/RUN, the Pico reset control, or necessarily a direct power cut to the controller.

The physical button contains no hardcoded Denon/Roku commands.

### Normal awake operation

A press is intended to request `power-toggle` through the common action dispatcher.

The implemented runtime selects the configured ON/OFF path using independent, volatile per-room/action command history.

This does **not** establish the equipment's actual state.

GP2 currently detects the physical power-button events, but room-aware action dispatch is still pending.

### Preferred deep-sleep ignition sequence

1. Lift the protective guard.
2. Press SYSTEM MASTER **once**.
3. Wake or reboot the Pico as required.
4. Play a short *engine-starting* sound, if audio hardware is available.
5. Reconnect Wi-Fi and load validated runtime configuration.
6. Invoke the selected room's configured **ON** command.
7. Resume normal remote operation.

**Provisional rule: Assume ON after deep sleep.**

Do not attempt to reconstruct the theater's previous power state across sleep.

The wake-triggered operation should use the configured `on_path`; this is only safe if the real device command has the intended ON semantics.

A native toggle may turn off equipment already on and must be tested separately.

The ignition sound is reserved for genuine deep-sleep ignition, not every ordinary power press.

### Wake-cause safety and exactly-once behavior

The Pico must reliably distinguish a SYSTEM MASTER wake from an ordinary reset, power restoration, or unrelated reboot **before automatically sending any theater power command**.

If that cannot be established, the acceptable fallback is to wake, restore operation, **send no automatic power command**, and wait for the next deliberate SYSTEM MASTER press.

One physical press/release must never generate duplicate equipment commands.

Debounce and release handling must account for boot and Wi-Fi startup.

### Light sleep is optional

Light sleep could begin after inactivity and wake transparently on an ordinary control, performing that control's intended action without an ignition ritual.

If power savings are small or Wi-Fi/input complexity excessive, omit it.

A simple **AWAKE / DEEP SLEEP** model is acceptable.

### Battery and power architecture

Rechargeable battery operation is preferred, but battery, charging circuitry, and power distribution are **not selected**.

A regulated USB power bank is a candidate for early experiments, not a finalized solution.

Measure or verify Pico Wi-Fi current, idle/sleep draw, reconnection cost, OLED/audio load, optical encoder supply, battery capacity, safe charging, and USB maintenance access.

Some power banks shut off under low-current loads.

Mechanical unilluminated switches should have negligible steady-state draw, but illuminated controls and supporting circuits may not.

### Required experiments before implementing ignition

1. Verify Pico 2 W / CircuitPython support for the intended sleep state and wake GPIO.
2. Confirm a brief momentary press can wake the system without being held through boot.
3. Reliably identify wake cause; distinguish it from reset or power restoration.
4. Measure awake, idle, sleep, and Wi-Fi reconnect current and timing.
5. Prove one press produces **at most one** power action.
6. Verify the actual configured ON command against the home theater.
7. Test optional startup audio and assess light-sleep benefits.
8. Verify the battery/power architecture can support the chosen wake mechanism.

Prior ESP32-S3 sleep experiments are historical, **not proof** of Pico 2 W behavior.

No wake GPIO, sleep state machine, battery management, ignition sound, or wake-triggered equipment action exists in current firmware.

**One guarded button. One deliberate press. The Clonker handles the rest.**

*Because apparently turning on the television now requires starting an engine.*

### Guard, button, and illumination candidates

Preferred mechanical concept: flip-up red ignition guard over a comfortably accessible **momentary** button, with optional illumination.

- **FILN 19 mm black ring-illuminated momentary pushbutton**, three-pack ordered for evaluation. Advertised 12 V/24 V illumination and approximately 19 mm mounting hole. Candidate, not final selection.
- **Red “Start Engine” protective cover**, ordered for fit/appearance evaluation. Compatibility with the eventual button is unverified.
- Other prominent power-toggle hardware remains under consideration.

Evaluate button height, guard clearance, actuation feel, contact layout, mounting depth, illumination voltage, and enclosure space.

**Never drive a 12 V/24 V LED ring directly from Pico GPIO.** Illumination and switch contacts are separate circuits requiring correct supply/driver design.

## 8. Operating-mode switches and room selector

### Two independent operating-mode switches

The Clonker now has two separate physical mode controls:

| Control | GPIO | When evaluated | Purpose |
|---|---|---|---|
| Boot-mode switch | GP17 | At boot | SERVICE (USB) / DEVICE filesystem ownership |
| Application-mode switch | GP18 | During runtime | CONFIG / RUN management listener |

Neither switch is an AV equipment power control.

GP17 determines filesystem write ownership.

GP18 determines whether the HTTP management interface is available.

**These are independent operating dimensions.**

The application-mode switch can be changed without rebooting; changing boot-mode filesystem ownership requires a power cycle.

### Physical room selector — pending

The room selector will establish the room context for physical action dispatch.

The current operational rooms are Den and Sunroom.

An earlier candidate used a three-position arrangement:

```text
DEN  /  BOTH  /  SUNROOM
```

The **uxcell three-position DPDT slide switch assortment** was ordered for evaluation. Additional selector hardware is being considered.

No final selector type, GPIO wiring, or multiroom broadcast behavior has been committed.

**BOTH is not a configured room.** It is a possible future physical-selection behavior requiring explicit semantics.

Open decisions include whether BOTH should exist, which commands could target multiple rooms, command ordering, error behavior, and independent power/mute history.

The immediate objective is simpler: establish reliable room selection so a physical control event can be dispatched to the correct configured room.

`ROOM_SELECTOR_A_PIN` and `ROOM_SELECTOR_B_PIN` remain unassigned.

Room selection should not itself transmit AV commands.

## 9. OLED and audible feedback

### OLED status display

Candidate: **0.49-inch SSD1306 OLED, 64 × 32 pixels, I2C**, two-pack ordered for experimentation.

No final mounting, pinout, driver, or UI has been implemented or hardware-tested.

The display remains optional. Ordinary volume, navigation, and action execution must not depend on it.

Specific display behavior will be documented after hardware experimentation.

### Audible feedback

Candidate components previously ordered:

| Component | Proposed role |
|---|---|
| Adafruit PS1240 piezo element (PID 160) | Simple tones/beeps |
| Adafruit MAX98357A I2S amplifier (PID 3006) | Richer sound playback |
| MECCANIXITY 23 mm, 8 Ω, 1 W mini speakers (two-pack) | Speaker audition |

Possible uses include short startup/ignition sound, action confirmation, mode-change chirp, and errors.

Sound should be brief, optional, appropriate for handheld use, and **not block input responsiveness**.

Verify power, amplifier/speaker compatibility, and GPIO/I2S assignments before wiring.

No audio subsystem is implemented.

---

## 10. Parts and procurement register

**Status convention:** The records below reflect selected/ordered candidates documented in project discussions. They do not assert receipt, inspection, or successful bench tests unless explicitly stated.

| Item | Part / description | Intended evaluation | Recorded status |
|---|---|---|---|
| Controller | Raspberry Pi Pico 2 W | Active controller | **In use; tested** |
| Earlier controller | Unexpected Maker FeatherS3[D] | Historical platform | Historical, not active |
| Boot-mode switch | Two-position maintained toggle | GP17 SERVICE (USB)/DEVICE | **Installed; tested** |
| CONFIG/RUN switch | Guarded maintained switch | GP18 application mode | **Bench-wired; tested** |
| Power button | Momentary pushbutton | GP2 power-toggle input | **Bench-wired; event-tested** |
| Volume encoder | Grayhill 62A22-02-040C | Main volume | Ordered; interface unverified |
| Volume knob | Kilo OEJNI-90-3-5 | Large silver knob | Ordered |
| Selector encoder | Bourns PEC11R-4215F-S0024 | Custom-action selection | Ordered |
| Selector knob | Kilo OEJL-63-4-7 | Small black knob | Ordered |
| Tactile switches | Adafruit #3347 metal-ball | Navigation/playback | Ordered candidate |
| Guarded button | FILN 19 mm red-ring momentary, 3-pack | SYSTEM MASTER | Ordered candidate |
| Guard | Red “Start Engine” cover | SYSTEM MASTER | Ordered candidate |
| Slide selector | uxcell 3-position DPDT assortment | Room selection | Ordered candidate |
| OLED | 0.49-inch SSD1306 64×32 I2C, 2-pack | Status | Ordered candidate |
| Piezo | Adafruit PS1240 | Tones | Ordered candidate |
| I2S amp | Adafruit MAX98357A | Audio | Ordered candidate |
| Speakers | MECCANIXITY 23 mm, 8 Ω, 1 W, 2-pack | Audio | Ordered candidate |
| Breadboard | Adafruit 830-tie, PID 239 | Prototyping | Ordered; bench wiring in use |
| Jumpers | Dupont assortment | Temporary wiring | Ordered |
| Solid wire | Ledvillage 22 AWG assortment | Breadboard wiring | Ordered |
| Test leads | WG-026 alligator leads | Temporary testing | Ordered |
| Resistors | ALLECIN assortment | Biasing/LED circuits | Ordered |
| LEDs | 300-piece 3 mm / 5 mm assortment | Indicator experiments | Ordered |

A soldering iron and miscellaneous personal parts may also be available; this is not a verified warehouse inventory.

Other switches mentioned informally but not identified by model should **not** be assigned invented specifications.

When adding parts, record manufacturer/model, quantity, photo, received/tested status, contact type, voltage, dimensions, intended function, and eventual GPIO.

## 11. GPIO ownership and physical-input software boundary

### Current pin assignment status

| Control/interface | GPIO | Status |
|---|---|---|
| SERVICE (USB)/DEVICE boot switch | **GP17** | Implemented/tested |
| CONFIG/RUN application switch | **GP18** | Implemented/tested |
| Power-toggle momentary input | **GP2** | Press/release tested; dispatch pending |
| Room selector A/B | TBD (`None`) | Unwired |
| Volume encoder A/B/press | TBD (`None`) | Unwired |
| Custom-action encoder A/B/press | TBD (`None`) | Unwired |
| Navigation, Back, Home, playback | TBD | Unwired |
| OLED I2C | TBD | Not integrated |
| Audio / I2S | TBD | Not integrated |
| Indicator LEDs | TBD | Not integrated |

`firmware/clonker/controls/pins.py` is the authoritative assignment map for application physical inputs.

GP17 boot-mode handling is implemented separately in `firmware/boot.py`.

Do not assign GPIO pins merely to complete a diagram. Review electrical requirements, supply voltage, pin conflicts, wake capability, and enclosure wiring first.

### Physical-controls software modules

| Module | Responsibility | Status |
|---|---|---|
| `pins.py` | Central application GPIO assignments | Implemented |
| `buttons.py` | Momentary inputs, debounce, press/release events | Implemented; GP2 tested |
| `switches.py` | Maintained application-mode selection | Implemented; GP18 tested |
| `physical.py` | Initialize and poll physical inputs | Implemented |
| `encoders.py` | Rotary encoder movement and direction | Planned |
| `selectors.py` | Multi-position room selection | Planned |

**Buttons produce events; maintained switches represent states.**

For example, pressing the GP2 momentary button generates a power-button event.

The GP18 maintained switch instead represents the current application operating mode.

The physical coordinator will eventually connect generic hardware events to Clonker behavior.

Individual input drivers must not contain Roku commands, Denon commands, or device-specific network logic.

### Intended event path

```text
Physical switch / encoder
          |
          v
GPIO input + debounce / decoding
          |
          v
Generic event + selected room/context
          |
          v
actions.dispatch(room_id, action_id)
          |
          v
Validated Config v4 + Dumb Queue
          |
          v
Bounded outbound HTTP GET/POST
          |
          v
Configured AV equipment
```

**Current implementation boundary:**

- GP2 physical button input and event logging: **VERIFIED**.
- Physical room context: **NOT YET IMPLEMENTED**.
- Physical event-to-action dispatch: **NOT YET CONNECTED**.
- Shared dispatcher and Dumb Queue: **IMPLEMENTED**.
- Configured Denon/Roku network execution: **VERIFIED**.

The browser Test Remote already uses the dispatcher, including executable custom actions and cooperative compound waits.

The physical input layer should reuse this path rather than creating a second action-execution mechanism.

The shared queue has bounded capacity. Future input drivers must avoid flooding it with bounce, held-button repeats, or excessively fast encoder events.

Physical-input code should detect transitions reliably, avoid blocking delays, define repeat behavior, and survive disconnected/invalid controls safely.

GPIO wiring definitions are developer-owned firmware constants, **not ordinary user-editable JSON configuration fields**.

## 12. Electrical design and bench safety

Before connecting a component:

1. Confirm its exact manufacturer part number and **datasheet**.
2. Identify contacts, commons, polarity, push-switch terminals, and separate illumination terminals.
3. Verify momentary versus maintained behavior, supply voltage, signal levels, and maximum current.
4. Keep Pico GPIO at compatible **3.3 V logic**; do not apply 5 V, 12 V, or 24 V directly to GPIO.
5. Use appropriate pull-ups/pull-downs, current limiting, and drivers for LEDs or other loads.
6. Avoid floating inputs and check power/ground before energizing.
7. Prototype **one input at a time**, observe raw transitions, then add debounce and action dispatch.
8. Recheck the Grayhill optical encoder's interface separately; do not wire it as a mechanical encoder on assumption.
9. Check battery, charging, and audio power budgets before combining loads.
10. Document verified wiring and pin assignments only after real bench tests.

For the GP17 and GP18 switches, the established prototype convention uses a GPIO signal wire and a common ground connection.

Mechanical switch terminals and wire strain relief deserve particular attention before enclosure installation.

No final PCB, enclosure, or permanent power architecture is implied by this document.

## 13. Open mechanical and system decisions

- Final enclosure material, dimensions, service latches, internal work light, and USB access.
- Volume/selector spacing and shaft/knob mounting.
- Navigation cluster and dedicated button type, feel, layout, and illumination.
- Final SYSTEM MASTER guard/button pairing, mounting, and ring-light driver.
- Permanent mounting and wiring of the GP17 and GP18 switches.
- Physical room selector hardware, GPIO, and any BOTH semantics.
- OLED mounting and integration, pending hardware experimentation.
- Speaker grille, amplifier placement, sound volume, and optional audio design.
- Battery chemistry/capacity, charger, power switch, measurement points, and low-power architecture.
- Wake-capable GPIO and reliable SYSTEM MASTER wake identification.
- Final GPIO allocation, cable routing, service connectors, and strain relief.

These are **open decisions**, not omissions to fill with guesses.

## 14. Recommended hardware development sequence

The browser-controlled firmware already executes real Denon/Roku commands and compound custom actions.

Chapter 5 has now completed its first physical-input milestones:

1. **DONE:** Establish optional physical-control initialization and cooperative polling.
2. **DONE:** Wire GP2 and verify momentary press/release events.
3. **DONE:** Replace the GP17 boot jumper with a maintained physical switch.
4. **DONE:** Wire GP18 and verify live CONFIG/RUN transitions without reboot.

The next suggested sequence:

1. Evaluate and connect the physical room selector.
2. Establish selected-room context for physical controls.
3. Connect GP2 power-button events to the existing room-specific `power-toggle` dispatcher.
4. Verify physical power execution, debounce, and repeat behavior.
5. Add navigation, Back, and Home buttons incrementally.
6. Wire and characterize the Bourns custom-action selector encoder.
7. Verify the Grayhill volume encoder electrically, then implement volume steps.
8. Measure responsiveness and queue behavior under rapid/repeated input.
9. Evaluate SYSTEM MASTER sleep/wake behavior and rechargeable power.
10. Experiment with optional OLED and audio hardware.
11. Refine permanent wiring, mechanical mounting, and enclosure construction.

This is a proposed order, not a fixed commitment.

The guiding principle remains: **one meaningful hardware or firmware change at a time, followed by real Pico verification**.

## 15. Current verification snapshot — October 29, 2026

**Implemented and tested:** Pico 2 W / CircuitPython startup, Wi-Fi, USB/REPL, GP17 filesystem ownership, Config v4 browser configuration/persistence, browser Test Remote, fundamental outbound GET/POST actions, executable custom actions, shared cooperative Dumb Queue™, a real Roku → wait → Denon compound sequence, and runtime power/mute ON/OFF direction selection.

**Chapter 5 physical hardware verified:**

- **GP17 boot-mode switch:** Maintained toggle selects SERVICE (USB) when OFF/open and DEVICE when ON/grounded.
- **GP2 momentary power button:** Physical input initialization, debounce, and press/release event logging verified. No action dispatch yet.
- **GP18 CONFIG/RUN switch:** Maintained guarded switch controls the application mode.
- **CONFIG/RUN HTTP behavior:** RUN stops the management listener; CONFIG restores it. Live transitions tested without reboot.
- **Serial diagnostics:** Application-mode messages standardized to `App mode source = PHYSICAL` and `App mode = CONFIG` or `App mode = RUN`.

**Implemented in firmware but not fully hardware-exercised:** Shared action dispatch under all network/failure/load scenarios; interaction between future room-aware physical controls and the existing dispatcher.

**Not yet implemented:** Physical room selection, physical-button-to-action dispatch, encoder drivers, navigation-button integration, SYSTEM MASTER wake/ignition, battery management, OLED integration, audio feedback, and final enclosure.

**Not finalized:** Physical room-selector behavior, complete GPIO map, rechargeable power design, and guarded SYSTEM MASTER sleep/wake behavior.

For dated tests, use [Development History](DEVELOPMENT_HISTORY.md). Historical implementation snapshots should not be mistaken for current firmware status.

## 16. Related documents

- [Architecture](ARCHITECTURE.md) — system boundaries and common action dispatcher.
- [Configuration & Recovery](CONFIGURATION.md) — authoritative Config v4 schema and persistence.
- [Firmware, HTTP & Clock](FIRMWARE_NETWORK.md) — live queue, scheduler, networking, and test evidence.
- [Operating Modes](OPERATING_MODES.md) — SERVICE (USB)/DEVICE and CONFIG/RUN.
- [Development & Deployment](DEVELOPMENT.md) — iPad-first workflow and bench deployment.
- [Development History](DEVELOPMENT_HISTORY.md) — historical decisions and dated verification.

---

**CLONK! ⚡🔩**

*The Clonker 10000 — because apparently a normal remote control wasn't complicated enough.*
