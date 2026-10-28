# THE CLONKER 10000
## Hardware & Physical Controls

**Design reference:** Updated October 28, 2026  
**Controller:** Raspberry Pi Pico 2 W (RP2350) / CircuitPython 10.3.1  
**Firmware baseline:** Chapter 5 / physical GPIO scheduler shell operational  
**Hardware baseline:** GP17 SERVICE/DEVICE jumper tested; physical action controls not yet wired

> A gloriously overengineered, tactile, Wi-Fi home theater remote. Two rotary controls, real buttons, questionable restraint, and absolutely no interest in becoming another touchscreen.

---

## 1. Purpose and hardware philosophy

The Clonker 10000 is a substantial, serviceable, purpose-built remote for multiple home theater systems. It should offer physical controls usable without looking, a prominent volume knob, a separate selection knob, dedicated navigation and playback controls, an unmistakable power control, and—if useful—a small display and short audible feedback.

**Core boundary:** Physical controls produce generic events. The selected room and validated configuration determine the action and network destination. GPIO code must not embed Denon or Roku commands.

This is the **hardware design and implementation reference**, not the authority for configuration schema or HTTP behavior. See [Configuration](CONFIGURATION.md), [Architecture](ARCHITECTURE.md), and [Firmware, HTTP & Clock](FIRMWARE_NETWORK.md) for those details. Procurement entries below distinguish *ordered or candidate* from *received, electrically verified, installed,* and *tested*; a purchase record alone proves none of the latter.

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

The Clonker keeps the useful idea—one configurable controller for multiple devices—and leaves the infrared archaeology behind. Initial control uses network commands and editable configuration, not IR libraries or synchronization rituals. IR is not on the current implementation path, though future optional support is not ruled out.

**We want to watch the movie, not spend Saturday teaching the remote what a movie is.**

### A tip of the hat to accessibility

We applaud companies producing simplified, large-button remotes for seniors and people with accessibility needs. They're solving real problems, and we're not trying to replace or compete with those products.

We're simply wondering why tactile, easy-to-find controls, sensible button counts, and straightforward operation shouldn't be desirable for everybody. After all, you shouldn't have to qualify for a senior discount to get a volume button you can find in the dark.

**Accessibility isn't a niche feature. Sometimes it's just good engineering.**

### Serviceability, Clonker style

Possible enclosure features include actual lunchbox-style latches, accessible internal electronics, an internal work light, convenient USB maintenance access, labeled wiring and connectors, and space for future experiments. These are concepts, **not finalized enclosure features**.

If servicing the remote requires holding a flashlight in your teeth while searching for microscopic screws, we've failed.

The Clonker isn't retro. It isn't minimalist. It's **selectively maximalist**: maximum attention to the things that matter; minimum tolerance for everything that doesn't.

**The Clonker 10000 — Less sleek. More CLONK.**

---

## 3. Controller platform and the one working hardware input

### Active controller

**Raspberry Pi Pico 2 W**, RP2350, integrated Wi-Fi, CircuitPython 10.3.1. It provides USB serial/filesystem maintenance, GPIO for future physical controls, and the running Config v4 browser/HTTP firmware under `firmware/clonker/`.

The earlier **Unexpected Maker FeatherS3[D] / ESP32-S3** selection is historical. Its pinout, sleep behavior, and firmware assumptions must not be transferred to the Pico without verification.

### GP17 SERVICE/DEVICE jumper — implemented and tested

| Connection | Pico physical pin | Behavior |
|---|---:|---|
| GP17, internal pull-up | 22 | Boot-time ownership input |
| GND | 23 | Jumper ground |

| Jumper at power-on | Mode | Filesystem writer |
|---|---|---|
| Open | SERVICE (USB) | USB host |
| GP17 grounded | DEVICE | Pico firmware |

`firmware/boot.py` reads GP17 during boot; DEVICE remounts the filesystem writable for the Pico. **Change the jumper only while unpowered and perform a full power cycle.** Ctrl+D is not an ownership-mode change. A removable internal jumper, recessed switch, or internal slide switch could eventually replace the bench jumper; final choice TBD. It must remain distinct from CONFIG/RUN and SYSTEM MASTER.

See [Operating Modes](OPERATING_MODES.md) for precise mode behavior and deployment cautions.

### Physical GPIO subsystem — Chapter 5 foundation

**Status: Implemented and Pico-tested October 28, 2026. Physical switches not yet connected.**

The firmware now includes a dedicated physical-control subsystem:

- `firmware/clonker/controls/physical.py` — initialization and polling interface.
- `firmware/clonker/main.py` — startup integration and cooperative scheduler.
- `PHYSICAL_CONTROLS_ENABLED` — development-time enable/disable flag.

The subsystem follows a simple lifecycle:

1. Initialize physical controls once during application startup, if enabled.
2. Record whether initialization succeeded.
3. Poll the initialized subsystem ahead of queued-action execution.
4. Do not repeatedly initialize controls or attempt automatic hot-plug recovery.
5. Restart the application when hardware connections or GPIO configuration change.

The current physical polling interval is 10 ms. This is a scheduler target, **not a guaranteed input sampling interval**: synchronous outbound HTTP operations can temporarily block the cooperative loop.

#### Brain-only mode

`PHYSICAL_CONTROLS_ENABLED = False` disables physical-control initialization and polling.

The browser configuration interface, Test Remote, shared Dumb Queue, outbound HTTP transport, and simulated CONFIG/RUN switch remain operational.

The flag does not affect the GP17 SERVICE/DEVICE boot jumper.

When enabled, the current subsystem initializes successfully but contains no actual GPIO readers or action dispatch. It is intentionally an empty framework.

#### Initialization and failure policy

Subsystem initialization errors must not prevent the rest of Clonker from starting.

Future individual controls should fail independently wherever practical. An initialized GPIO input does not necessarily prove a mechanical switch is connected.

Ordinary switches and encoders do not require hot-plug support. Initial input states must not generate unintended actions.

Debouncing, encoder decoding, event capture, and per-control fault isolation remain future work.

#### Pico verification — October 28, 2026

| Test | Result |
|---|---|
| Physical controls disabled | PASS — brain-only startup confirmed |
| CONFIG listener with controls disabled | PASS |
| Sunroom Home with controls disabled | PASS — HTTP 200 |
| Physical controls enabled | PASS — startup without GPIO errors |
| CONFIG listener with controls enabled | PASS |
| Sunroom Home with controls enabled | PASS — HTTP 200 |
| Unexpected physical actions | None observed |

Both flag settings were deployed and tested on the Raspberry Pi Pico 2 W running CircuitPython 10.3.1.

These tests establish that the empty physical-control subsystem does not disrupt the verified browser and network-control paths. They do **not** establish actual switch or encoder functionality.

**The Monster has a nervous system. The nerve endings are still on order.**

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
        CONFIG/RUN: LOCATION TBD
```

**Concept only.** Dimensions, ergonomics, button spacing, mounting depths, guard clearance, and display position are not fixed. Thumb reach and tactile identification take precedence over decorative symmetry.

## 5. Primary rotary controls

### Volume — Grayhill 62A22-02-040C

**Selected for evaluation / ordered from DigiKey; electrical testing not confirmed in this reference.** Associated large silver/clear-matte knob: **Kilo OEJNI-90-3-5**, approximately 23.5 mm diameter.

- Clockwise: generic `volume-up`; counterclockwise: `volume-down`.
- Initial firmware behavior: one action per accepted step; avoid acceleration, batching, or aggressive network repeat until responsiveness is measured.
- Encoder driver, wiring, GPIO assignment, and physical tests: **not implemented**.
- **Critical electrical check:** Verify the Grayhill encoder's actual datasheet, pinout, power requirements, signal type, and 3.3 V GPIO compatibility. An optical encoder must not be assumed equivalent to a passive mechanical quadrature encoder; interface circuitry may be necessary.
- Future investigation: encoder detent behavior, debounce/decoding, repeat rate, command backlog, and interaction with the cooperative queue.

### Selector — Bourns PEC11R-4215F-S0024

**Selected for evaluation / ordered from DigiKey; installation and testing not confirmed.** Associated smaller black knob with white indicator: **Kilo OEJL-63-4-7**.

Possible roles: cycling configured custom actions, OLED menu selection, function context, or future settings. **No final selector behavior is committed.** Confirm the actual purchased part's terminals and whether its push-switch contact is available before assigning a press action.

GPIO A/B, any switch GPIO, step decoding, debounce, and display integration are TBD. Unlike the volume encoder, the selector is context-sensitive by design; it must still produce generic events rather than device-specific URLs.

## 6. Navigation, playback, and function buttons

The desired navigation cluster is **UP / DOWN / LEFT / RIGHT / OK**, preferably intuitive by touch. Candidates include individual tactile switches, a purpose-built directional assembly, or a mechanically linked cluster. None has been finalized or integrated.

The other likely dedicated functions are Back, Home, Play/Pause, Skip Back, Skip Forward, Mute, and a guarded power control. The fourteen firmware fundamentals **do not require fourteen physical buttons**; selector/OLED access may expose other functions.

**Candidate tactile hardware:** Adafruit **#3347 metal-ball momentary switches**, ordered for experimentation. They may suit navigation, playback, or secondary controls; actual feel and mounting must be auditioned.

**Still open:** switch travel and force, spacing, long-press/repeat policy, debounce, illumination, and mechanical layout. A held navigation button must not inadvertently flood the network.

### Generic action vocabulary

The current fourteen fixed action IDs are:

| Category | IDs |
|---|---|
| Volume | `volume-up`, `volume-down`, `mute-toggle` |
| Navigation | `nav-up`, `nav-down`, `nav-left`, `nav-right`, `select`, `back`, `home` |
| Playback | `play-pause`, `skip-back`, `skip-forward` |
| Equipment power | `power-toggle` |

The current Config v4 firmware also supports **room-specific executable custom actions**, including multi-step GET/POST commands and cooperative waits. A future selector or dedicated button may invoke a custom action through the **same dispatcher**. Physical control mapping remains a hardware/UI design decision; exact schema and execution behavior belong in the configuration and firmware references.

**Toggle boundary:** Configured ON/OFF paths for mute and power are operational through the shared dispatcher, with independent volatile direction histories per room and action. The browser Test Remote exercised these commands successfully on October 27, 2026. Command history is not authoritative equipment state, and the physical controls remain unimplemented.

---

## 7. SYSTEM MASTER: guarded power and ignition concept

**Design status: Provisionally agreed October 20, 2026; not implemented or tested.** This is a signature feature and deserves its own design record.

The guarded **SYSTEM MASTER momentary button** is intended to perform two logically distinct jobs:

1. While Clonker is awake, invoke the configured `power-toggle` action for the selected room.
2. When Clonker is in deep sleep, wake the controller and, **only if the wake cause is reliably identified**, initiate a single theater-power ON action.

SYSTEM MASTER is **not** GP17 filesystem ownership, CONFIG/RUN, the Pico reset control, or necessarily a direct power cut to the controller. The physical button contains no hardcoded Denon/Roku commands.

### Normal awake operation

A press is intended to request `power-toggle` through the common action dispatcher. The implemented runtime selects the configured ON/OFF path using independent, volatile per-room/action command history. This does **not** establish the equipment's actual state; other remotes, HDMI-CEC, and manual controls can change that state independently. The physical SYSTEM MASTER button itself is not yet wired or tested.

### Preferred deep-sleep ignition sequence

1. Lift the protective guard.
2. Press SYSTEM MASTER **once**.
3. Wake or reboot the Pico as required.
4. Play a short *engine-starting* sound, if audio hardware is available.
5. Reconnect Wi-Fi and load validated runtime configuration.
6. Invoke the selected room's configured **ON** command.
7. Resume normal remote operation.

**Provisional rule: Assume ON after deep sleep.** Do not attempt to reconstruct the theater's previous power state across sleep. The wake-triggered operation should use the configured `on_path`; this is only safe if the real device command has the intended ON semantics. A native toggle may turn off equipment already on and must be tested separately.

The ignition sound is reserved for genuine deep-sleep ignition, not every ordinary power press.

### Wake-cause safety and exactly-once behavior

The Pico must reliably distinguish a SYSTEM MASTER wake from an ordinary reset, power restoration, or unrelated reboot **before automatically sending any theater power command**.

If that cannot be established, the acceptable fallback is to wake, restore operation, **send no automatic power command**, and wait for the next deliberate SYSTEM MASTER press. One physical press/release must never generate duplicate equipment commands; debounce and release handling must account for boot and Wi-Fi startup.

### Light sleep is optional

Light sleep could begin after inactivity and wake transparently on an ordinary control, performing that control's intended action without an ignition ritual. If the power savings are small or Wi-Fi/input complexity excessive, omit it. A simple **AWAKE / DEEP SLEEP** model is acceptable.

### Battery and power architecture

Rechargeable battery operation is preferred, but the battery, charging circuitry, and power distribution are **not selected**. A regulated USB power bank is a candidate for early experiments, not a finalized solution.

Measure or verify Pico Wi-Fi current, idle/sleep draw, reconnection cost, OLED and audio load, optical encoder supply, battery capacity, safe charging, and USB maintenance access. Some power banks shut off under low-current loads. Mechanical unilluminated switches should have negligible steady-state draw, but illuminated controls and supporting circuits may not.

### Required experiments before implementing ignition

1. Verify Pico 2 W / CircuitPython support for the intended sleep state and wake GPIO.
2. Confirm a **brief** momentary press can wake the system without being held through boot.
3. Reliably identify wake cause; distinguish it from reset or power restoration.
4. Measure awake, idle, sleep, and Wi-Fi reconnect current and timing.
5. Prove one press produces **at most one** power action, including bounce/release cases.
6. Verify the actual configured ON command against the home theater.
7. Test optional startup audio and assess light-sleep benefits.
8. Verify the battery/power architecture can support the chosen wake mechanism.

Prior ESP32-S3 sleep experiments are historical, **not proof** of Pico 2 W behavior. No wake GPIO, sleep state machine, battery management, ignition sound, or wake-triggered equipment action exists in current firmware.

**One guarded button. One deliberate press. The Clonker handles the rest.**

*Because apparently turning on the television now requires starting an engine.*

### Guard, button, and illumination candidates

Preferred mechanical concept: flip-up red ignition guard over a comfortably accessible **momentary** button, with optional illumination.

- **FILN 19 mm black ring-illuminated momentary pushbutton**, three-pack ordered for evaluation. Advertised 12 V/24 V illumination, approximately 19 mm mounting hole, black metal-style housing. **Candidate, not final selection.**
- **Red “Start Engine” protective cover**, ordered for fit/appearance evaluation. Compatibility with the eventual button is unverified.
- Other prominent power-toggle hardware remains under consideration; no final guard/button pairing is recorded.

Evaluate button height, guard clearance, actuation feel, contact layout, mounting depth, illumination voltage, and available enclosure space. **Never drive a 12 V/24 V LED ring directly from Pico GPIO**; illumination and switch contacts are separate circuits requiring correct supply/driver design and terminal verification.

## 8. CONFIG/RUN switch and room selector

### CONFIG/RUN — physical implementation pending

Firmware currently simulates CONFIG enabled (`_simulated_config = True` in `controls/switches.py`; `CONFIG_SWITCH_PIN = None` in `controls/pins.py`). The management listener can be started/stopped by application mode logic, but no real switch is wired.

Candidate: a maintained two-position switch, final type/location TBD. Requirements:

- Stable runtime input with known polarity and debounce.
- Listener starts/stops **on state changes**, not on every poll.
- No AV power command and no unnecessary flash writes.
- Independent of GP17 SERVICE/DEVICE and the guarded SYSTEM MASTER button.
- Validated configuration stays available in RAM through transitions.

See [Operating Modes](OPERATING_MODES.md) for the four mode combinations and filesystem permissions.

### Physical room selector — candidate three-position switch

Original proposed positions:

```text
DEN  /  BOTH  /  SUNROOM
```

**uxcell three-position DPDT slide switch assortment**, ordered for evaluation; final selection and GPIO wiring TBD. This is a *physical selection concept*, not the Config v4 room-ID model. The current configuration supports up to three rooms; `room-1` (Den), `room-2` (Sunroom), and `room-3` (third room/placeholder) are examples. **BOTH is not a fourth configured room.**

Open decisions: whether BOTH broadcasts to both rooms; whether commands are sequential; how one-room failures behave; whether volume, mute, and power participate; how per-room toggle history is handled; and what happens to the third configured room. Do not silently implement group semantics before those choices are made.

Electrical design may use two GPIO inputs with defined pull-ups/pull-downs and transition/debounce handling. `ROOM_SELECTOR_A_PIN` and `ROOM_SELECTOR_B_PIN` remain unassigned.

## 9. OLED and audible feedback

### OLED status display

Candidate: **0.49-inch SSD1306 OLED, 64 × 32 pixels, I2C**, two-pack ordered for experimentation. No final mounting, pinout, driver, or UI is implemented.

Potential indications: selected room, selector context/custom action, CONFIG/RUN, Wi-Fi, and brief action status. It should be readable at arm's length, update cheaply, and remain **optional**: ordinary volume and navigation must work without looking at a screen.

### Audible feedback

Candidate components previously ordered:

| Component | Proposed role |
|---|---|
| Adafruit PS1240 piezo element (PID 160) | Simple tones/beeps |
| Adafruit MAX98357A I2S amplifier (PID 3006) | Richer sound playback |
| MECCANIXITY 23 mm, 8 Ω, 1 W mini speakers (two-pack) | Speaker audition |

Possible uses include short startup/ignition sound, action confirmation, mode-change chirp, and errors. Sound should be brief, optional, appropriate for handheld use, and **not block input responsiveness**. Verify power, amplifier/speaker compatibility, and GPIO/I2S assignments before wiring. No audio subsystem is implemented.

---

## 10. Parts and procurement register

**Status convention:** The records below reflect selected/ordered candidates documented in project discussions. They do **not** assert receipt, inspection, or successful bench tests unless explicitly stated. Update this table when hardware is physically inventoried.

| Item | Part / description | Intended evaluation | Recorded status |
|---|---|---|---|
| Controller | Raspberry Pi Pico 2 W | Active controller | **In use; tested** |
| Earlier controller | Unexpected Maker FeatherS3[D] | Historical platform | Historical, not active |
| Volume encoder | Grayhill 62A22-02-040C | Main volume | Ordered; interface unverified |
| Volume knob | Kilo OEJNI-90-3-5 | Large silver knob | Ordered |
| Selector encoder | Bourns PEC11R-4215F-S0024 | Function selection | Ordered |
| Selector knob | Kilo OEJL-63-4-7 | Small black knob | Ordered |
| Tactile switches | Adafruit #3347 metal-ball | Navigation/playback | Ordered candidate |
| Guarded button | FILN 19 mm red-ring momentary, 3-pack | SYSTEM MASTER | Ordered candidate |
| Guard | Red “Start Engine” cover | SYSTEM MASTER | Ordered candidate |
| Slide selector | uxcell 3-position DPDT assortment | Room selection | Ordered candidate |
| OLED | 0.49-inch SSD1306 64×32 I2C, 2-pack | Status | Ordered candidate |
| Piezo | Adafruit PS1240 | Tones | Ordered candidate |
| I2S amp | Adafruit MAX98357A | Audio | Ordered candidate |
| Speakers | MECCANIXITY 23 mm, 8 Ω, 1 W, 2-pack | Audio | Ordered candidate |
| Breadboard | Adafruit 830-tie, PID 239 | Prototyping | Ordered |
| Jumpers | Dupont assortment | Temporary wiring | Ordered |
| Solid wire | Ledvillage 22 AWG assortment | Breadboard wiring | Ordered |
| Test leads | WG-026 alligator leads | Temporary testing | Ordered |
| Resistors | ALLECIN assortment | Biasing/LED circuits | Ordered |
| LEDs | 300-piece 3 mm / 5 mm assortment | Indicator experiments | Ordered |

A soldering iron and miscellaneous personal parts may also be available; this is not a verified warehouse inventory. Other switches mentioned informally but not identified by model should **not** be assigned invented specifications. When adding parts, record manufacturer/model, quantity, photo, received/tested status, contact type, voltage, dimensions, intended function, and eventual GPIO.

## 11. GPIO ownership and physical-input software boundary

### Current pin assignment status

| Control/interface | GPIO | Status |
|---|---|---|
| SERVICE/DEVICE jumper | **GP17** | Implemented/tested |
| CONFIG/RUN | TBD (`None`) | Simulated |
| Room selector A/B | TBD (`None`) | Unwired |
| Volume encoder A/B | TBD (`None`) | Unwired |
| Selector encoder A/B | TBD (`None`) | Unwired |
| Navigation, playback, mute, power | TBD | Unwired |
| OLED I2C | TBD | Not integrated |
| Audio / I2S | TBD | Not integrated |
| Indicator LEDs | TBD | Not integrated |

The existing placeholders live in `firmware/clonker/controls/pins.py`. Do not assign pins for the sake of completing a diagram. Review electrical requirements, supply voltage, pin conflicts, wake capability, and enclosure wiring first.

### Intended event path

```text
Physical switch / encoder
          |
          v
GPIO sampling + debounce / step decoding  [NOT YET INTEGRATED]
          |
          v
Generic event + selected room/context
          |
          v
actions.dispatch(room_id, action_id)      [IMPLEMENTED]
          |
          v
Validated Config v4 + shared Dumb Queue™  [IMPLEMENTED]
          |
          v
Bounded outbound HTTP GET/POST           [IMPLEMENTED]
          |
          v
Configured AV equipment                 [DENON/ROKU VERIFIED]
```

The browser Test Remote already uses the dispatcher, including executable custom actions and cooperative compound waits. **Only the physical input capture and its mapping to that dispatcher remain unconnected.** The shared queue has bounded capacity; future input drivers must avoid flooding it with bounce, held-button repeats, or excessively fast encoder events.

Physical-input code should detect transitions reliably, avoid blocking delays, define repeat behavior, survive disconnected/invalid controls safely, and keep responsive operation during network work. GPIO wiring definitions are developer-owned firmware constants, **not ordinary user-editable JSON configuration fields**.

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

No final PCB, enclosure, or permanent power architecture is implied by this document.

## 13. Open mechanical and system decisions

- Final enclosure material, dimensions, service latches, internal work light, and USB access.
- Volume/selector spacing and shaft/knob mounting.
- Navigation cluster and dedicated button type, feel, layout, and illumination.
- Final guard/button pairing, ignition-button mounting, and ring-light driver.
- CONFIG/RUN switch location and stable electrical default.
- Physical room selector and exact BOTH semantics.
- OLED mount, display behavior, and whether to install it at all.
- Speaker grille, amplifier placement, sound volume, and optional audio design.
- Battery chemistry/capacity, charger, power switch, measurement points, and low-power architecture.
- Wake-capable GPIO and reliable SYSTEM MASTER wake identification.
- Final GPIO allocation, cable routing, service connectors, and strain relief.

These are **open decisions**, not omissions to fill with guesses.

## 14. Recommended hardware development sequence

Real Denon/Roku HTTP execution and compound custom actions have already been demonstrated through the browser. The next hardware phase should build on that proven software path:

1. Inventory the actual received components and verify datasheets, especially the Grayhill interface and power candidates.
2. Plan GPIO/power allocation without prematurely freezing the final enclosure.
3. Wire **one simple momentary button** and verify raw GPIO input.
4. Add debounce and dispatch one existing fundamental action through the shared queue; verify the physical equipment response.
5. Measure responsiveness and queue behavior under rapid/repeated presses.
6. Wire and characterize the Bourns selector encoder; decide its first minimal behavior.
7. Verify and prototype the Grayhill optical volume encoder electrically, then dispatch volume steps.
8. Prototype the room selector; decide BOTH semantics before implementing them.
9. Implement and test the physical CONFIG/RUN switch and transitions.
10. Audition navigation/playback buttons and refine ergonomics.
11. Evaluate guarded SYSTEM MASTER, power supply, and sleep/wake feasibility **before** promising one-press ignition.
12. Add optional OLED/audio only when they improve usability; then refine permanent wiring and enclosure.

This is a proposed order, not a fixed commitment. A compelling new switch or mechanical discovery may change the build sequence.

## 15. Current verification snapshot — October 27, 2026

**Implemented and tested:** Pico 2 W / CircuitPython startup, Wi-Fi, USB/REPL, GP17 filesystem ownership, Config v4 browser configuration/persistence, browser Test Remote, fundamental outbound GET/POST actions, executable custom actions, shared cooperative queue, a real Roku → wait → Denon compound sequence, and runtime power/mute ON/OFF direction selection. October 27 bench tests verified Sunroom mute/power execution, HDMI-CEC power behavior, changed-configuration history reset, and independent Den/Sunroom toggle histories.

**Implemented in firmware but not fully hardware-exercised:** CONFIG/RUN listener transitions through simulated state; action dispatch under all network/failure/load scenarios.

**Not yet implemented:** Physical action buttons, encoder drivers, room selector GPIO, physical CONFIG/RUN switch, SYSTEM MASTER wake/ignition, battery management, OLED, audio feedback, and final enclosure.

**Not finalized:** Physical BOTH semantics, mechanical switch assignments, complete GPIO map, rechargeable power design, and the guarded SYSTEM MASTER's sleep/wake behavior.

For dated tests, use [Development History](DEVELOPMENT_HISTORY.md). The historical October 19 logging-only dispatcher snapshot should **not** be treated as current firmware status.

## 16. Related documents

- [Architecture](ARCHITECTURE.md) — system boundaries and common action dispatcher.
- [Configuration & Recovery](CONFIGURATION.md) — authoritative Config v4 schema and persistence.
- [Firmware, HTTP & Clock](FIRMWARE_NETWORK.md) — live queue, scheduler, networking, and test evidence.
- [Operating Modes](OPERATING_MODES.md) — SERVICE/DEVICE and CONFIG/RUN.
- [Development & Deployment](DEVELOPMENT.md) — iPad-first workflow and bench deployment.
- [Development History](DEVELOPMENT_HISTORY.md) — historical decisions and dated verification.

---

**CLONK! ⚡🔩**

*The Clonker 10000 — because apparently a normal remote control wasn't complicated enough.*
