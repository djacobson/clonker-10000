# THE CLONKER 10000
## Hardware & Physical Controls

**Design reference:** Updated November 2, 2026  
**Controller:** Raspberry Pi Pico 2 W (RP2350) / CircuitPython 10.3.1  
**Firmware baseline:** Chapter 6 — physical room selection and room-aware Power Toggle operational  
**Hardware baseline:** GP17, GP18, GP2, and three-position GP3/GP4/GP5 selector verified  
**Current development focus:** Two Bourns rotary encoders and remaining physical controls

> A gloriously overengineered, tactile, Wi-Fi home theater remote. Two rotary controls, real buttons, questionable restraint, and absolutely no interest in becoming another touchscreen.

---

## 1. Purpose and hardware philosophy

The Clonker 10000 is a substantial, serviceable, purpose-built remote for multiple home theater systems.

The goal is tactile operation without constantly looking down: a prominent volume knob, a separate custom-action selector, dedicated navigation and function buttons, and an unmistakable power control.

Optional display and audible feedback may improve usability without becoming dependencies.

**Core boundary:** Physical controls produce generic events. The selected room and validated configuration determine the action and network destination. GPIO drivers must not embed Denon or Roku commands.

This document is the hardware design, component, wiring, and verification reference.

Configuration schema, action execution, HTTP behavior, and scheduling details belong in [Configuration](CONFIGURATION.md), [Architecture](ARCHITECTURE.md), and [Firmware, HTTP & Clock](FIRMWARE_NETWORK.md).

Procurement records distinguish *ordered or candidate* from *received, installed, electrically verified,* and *tested*.

Purchasing a component does not establish that it works.

---

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

We respect the ambitious efforts of Logitech Harmony and the other universal-remote pioneers.

They were attempting to bring order to a spectacularly fragmented home theater industry.

We also remember the configuration software.

The Clonker keeps the useful idea—one configurable controller for multiple devices—and leaves the infrared archaeology behind.

Initial control uses network commands and editable configuration, not IR libraries or synchronization rituals.

IR is not on the current implementation path, though future optional support is not ruled out.

**We want to watch the movie, not spend Saturday teaching the remote what a movie is.**

### A tip of the hat to accessibility

We applaud companies producing simplified, large-button remotes for seniors and people with accessibility needs.

They're solving real problems, and we're not trying to replace or compete with those products.

We're simply wondering why tactile, easy-to-find controls, sensible button counts, and straightforward operation shouldn't be desirable for everybody.

After all, you shouldn't have to qualify for a senior discount to get a volume button you can find in the dark.

**Accessibility isn't a niche feature. Sometimes it's just good engineering.**

### Serviceability, Clonker style

Possible enclosure features include accessible internal electronics, an internal work light, convenient USB maintenance access, labeled wiring and connectors, and space for future experiments.

Lunchbox-style latches and other elaborate service features remain concepts, not finalized hardware.

If servicing the remote requires holding a flashlight in your teeth while searching for microscopic screws, we've failed.

The Clonker isn't retro.

It isn't minimalist.

It's **selectively maximalist**: maximum attention to the things that matter; minimum tolerance for everything that doesn't.

**The Clonker 10000 — Less sleek. More CLONK.**

---

## 3. Controller and verified hardware

### 3.1 Active controller

**Raspberry Pi Pico 2 W**, RP2350, integrated Wi-Fi, running CircuitPython 10.3.1.

The Pico provides:

- USB serial and filesystem maintenance.
- GPIO inputs.
- Wi-Fi networking.
- Browser configuration management.
- Config v4 action execution.
- The cooperative physical-control scheduler.

The active firmware resides under `firmware/clonker/`.

The earlier **Unexpected Maker FeatherS3[D] / ESP32-S3** selection is historical.

Its pinout, sleep behavior, and firmware assumptions must not be transferred to the Pico without verification.

### 3.2 Pico Cowbell Terminal board

The current bench assembly uses an **Adafruit Pico Cowbell Terminal** board with screw-terminal GPIO connections.

This replaces much of the earlier temporary breadboard wiring.

Benefits include:

- More secure GPIO connections.
- Easier individual signal wiring.
- Less dependence on temporary Dupont-to-breadboard connections.
- A cleaner foundation for enclosure installation.
- Better serviceability as additional controls arrive.

Use **GPIO labels**, such as GP2 and GP18, when documenting wiring.

Avoid confusing Pico physical pin numbers with GPIO numbers.

Ground terminals on the Cowbell must be identified by their actual board markings, including the underside markings where necessary.

### 3.3 Ground distribution

A WAGO lever-connector ground bus distributes the common ground reference to physical controls.

The GP2 button, GP18 switch, and room selector use common ground connections.

The selector's black common wire connects to this ground distribution.

All grounds must share the Pico's electrical ground.

Verify wire retention, particularly when small-gauge wires are used in connectors intended for a range of conductor sizes.

Strain relief and terminal insulation remain important as wiring becomes permanent.

### 3.4 GP17 boot-mode switch — implemented and tested

The former removable GP17 jumper has been replaced by a permanent two-position physical toggle switch.

| Connection | Function |
|---|---|
| GP17, internal pull-up | Boot-time filesystem ownership |
| GND | Common ground |

| Switch position | GP17 state | Boot mode | Filesystem writer |
|---|---|---|---|
| OFF / open | HIGH | SERVICE (USB) | USB host |
| ON / grounded | LOW | DEVICE | Pico firmware |

`firmware/boot.py` reads the switch during boot.

DEVICE mode remounts the filesystem writable for the Pico, enabling configuration persistence.

The source variable is named `boot_mode_switch`, replacing the historical jumper terminology.

Expected boot diagnostics:

```text
CLONKER BOOT: SERVICE (USB) mode (switch OFF)
CLONKER BOOT: DEVICE mode (switch ON)
```

**Changing boot mode requires a full power cycle.**

Do not rely on Ctrl+D to change filesystem ownership.

SERVICE (USB)/DEVICE is independent of the application's CONFIG/RUN mode.

See [Operating Modes](OPERATING_MODES.md).

### 3.5 GP18 CONFIG/RUN switch — implemented and tested

A maintained, guarded physical switch selects the application operating mode.

| Connection | GPIO | Function |
|---|---|---|
| Switch signal | GP18 | Application-mode input |
| Switch common | GND | Ground reference |

The input uses the Pico's internal pull-up.

| Electrical state | Application mode | Management listener |
|---|---|---|
| Open / HIGH | RUN | Stopped |
| Grounded / LOW | CONFIG | Running |

Implementation:

- `controls/pins.py` — `CONFIG_SWITCH_PIN = 18`.
- `controls/switches.py` — physical state, simulated state, and override.
- `main.py` — starts and stops the management HTTP listener.

**Verified live behavior:**

1. RUN — browser Config page unavailable on refresh.
2. CONFIG — browser Config page accessible.
3. RUN again — browser Config page unavailable.
4. CONFIG again — browser Config page accessible.

These transitions require **no reboot**.

The action queue continues operating regardless of management-listener state.

Serial diagnostics include:

```text
App mode source = PHYSICAL
App mode = CONFIG
App mode = RUN
```

Changing application mode must not transmit an AV power command or unnecessarily write configuration data.

### 3.6 GP2 momentary Power Toggle — fully operational

The first physical action button is connected to **GP2**.

`POWER_TOGGLE_PIN = 2` is assigned in `controls/pins.py`.

The button uses an internal pull-up and active-low momentary contact.

The reusable `Button` class handles debouncing and reports stable press/release events.

`physical.py` maps a stable press to the generic `power-toggle` action.

The currently selected room comes from `selectors.py`.

The shared dispatcher then queues and executes the configured command.

**November 2 verification:**

| Room | Power ON | Power OFF |
|---|---|---|
| Room 1 — Den | PASS | PASS |
| Room 2 — Sunroom | PASS | PASS |
| Room 3 — Reserved | No-op | No-op |

The tests included actual equipment observation, not merely HTTP acknowledgments.

Both configured rooms demonstrated independent volatile toggle histories.

**The GP2 button is no longer just a tested input. It is a working physical home-theater control.**

### 3.7 Physical GPIO subsystem

The firmware contains a dedicated physical-control subsystem:

| Module | Responsibility |
|---|---|
| `pins.py` | Central GPIO assignments |
| `buttons.py` | Reusable debounced momentary inputs |
| `switches.py` | CONFIG/RUN state |
| `selectors.py` | Three-position room state |
| `physical.py` | Initialization, polling, event mapping, dispatch |
| `main.py` | Cooperative scheduling |
| `actions.py` | Shared action queue and execution |

The lifecycle is deliberately simple:

1. Initialize assigned physical controls once during startup.
2. Log initialization success or failure.
3. Poll physical controls cooperatively.
4. Detect stable events.
5. Map supported events to generic actions.
6. Dispatch those actions through the existing queue.
7. Avoid repeated initialization and unnecessary hot-plug detection.

The current physical polling target is approximately **10 ms**.

This is not a guaranteed sampling interval.

Synchronous outbound HTTP can temporarily block the cooperative loop.

#### Brain-only mode

`PHYSICAL_CONTROLS_ENABLED = False` disables optional physical-control initialization and polling.

The browser configuration interface, Test Remote, Dumb Queue™, and outbound HTTP transport remain usable.

GP17 boot handling and GP18 application-mode selection are separate concerns.

#### Initialization and failure policy

Missing or failed noncritical controls should not prevent the rest of Clonker from starting.

Unassigned GPIO controls are skipped.

Individual button initialization failures are logged.

An initialized GPIO input does not necessarily prove a mechanical switch is connected.

Initial input states must not generate unintended button actions.

Hot-plug detection and automatic reinitialization are not current requirements.

### 3.8 GPIO foundation verification

| Test | Result |
|---|---|
| Brain-only startup | PASS |
| Browser management with controls disabled | PASS |
| Sunroom Home with controls disabled | PASS |
| Physical controls enabled | PASS |
| Browser management with controls enabled | PASS |
| GP2 press/release detection | PASS |
| Browser responsiveness with GP2 enabled | PASS |
| GP17 boot-mode selection | PASS |
| GP18 live CONFIG/RUN transitions | PASS |
| GP3/GP4/GP5 standalone selector test | PASS |
| Integrated room selection | PASS |
| Room 3 safe no-op | PASS |
| Room 2 Power Toggle ON/OFF | PASS |
| Room 1 Power Toggle ON/OFF | PASS |

The original Chapter 5 foundation has now become an operational Chapter 6 physical-control system.

**The Monster has a nervous system. And some of its nerve endings can turn on the television.**

---

## 4. Enclosure, faceplate, and proposed layout

### 4.1 Current enclosure direction

The enclosure concept has progressed beyond a loose breadboard prototype.

The current construction uses:

- A black semi-rigid zippered electronics case.
- A pre-cut aluminum faceplate.
- A rectangular opening beneath the plate for internal component access.
- Ten distributed faceplate mounting bolts.
- Underside washers, star washers, and nuts.

The aluminum plate has protective film.

The plan is to retain protection during drilling and component fitting, then remove the visible protective film after the machining work is complete.

The assembly is intended to remain serviceable and mechanically substantial.

Final component holes, wiring routes, and interior mounting details are still under development.

### 4.2 Faceplate design

The earlier target faceplate was approximately **4.5 × 6.5 inches**, with enclosure depth around **1.5–2 inches**.

These dimensions were design targets, not immutable specifications.

The working design prioritizes:

- Tactile identification.
- Knob clearance.
- Thumb reach.
- Guarded power operation.
- OLED visibility.
- Internal wiring clearance.
- Component mounting depth.
- Access for future service.

The faceplate should be drilled only after component placement and clearances are verified.

### 4.3 Control layout concept

```text
              THE CLONKER 10000

         __________________________
        /                          \
       |  VOLUME       ACTIONS      |
       |     O            O         |
       |                            |
       |       BACK     HOME        |
       |                            |
       |             UP             |
       |              ^             |
       |       LEFT   OK   RIGHT    |
       |              v             |
       |            DOWN            |
       |                            |
       |  [ STATUS OLED ]           |
       |                    PLAY    |
       |                  <<   >>   |
       |                            |
       |              [ POWER ]     |
       |              (guarded)     |
       |____________________________|

          SIDE: ROOM SELECTOR

          CONFIG/RUN: GUARDED SWITCH
          SERVICE/DEVICE: BOOT SWITCH
```

**Concept only.** This is not a drilling template.

The current plan places volume and custom-action encoders prominently near the top.

The room selector is intended for the right side.

The guarded power control is intended toward the lower right.

The OLED and playback controls occupy the lower portion of the faceplate.

Final positions remain subject to component fit and ergonomic testing.

---

## 5. Primary rotary controls

### 5.1 Current encoder decision

The design now uses **two Bourns PEC11R-4215F-S0024 rotary encoders**.

The earlier Grayhill volume-encoder plan has been superseded.

Both encoder positions use the same model, simplifying electrical characterization and driver development.

The two controls have different application roles but share the same hardware mechanism.

| Encoder | Rotation | Push |
|---|---|---|
| Volume | Volume Up / Down | Mute Toggle |
| Custom Action | Cycle custom actions | Execute selected action |

The encoders are incremental, nonpositional controls.

Their physical shaft angle does not represent an absolute volume or action-selection value.

### 5.2 Volume encoder — Bourns PEC11R

The volume encoder is intended to provide:

- Clockwise rotation: `volume-up`.
- Counterclockwise rotation: `volume-down`.
- Shaft press: `mute-toggle`.

The original large volume-knob concept remains.

The earlier Grayhill plan included the **Kilo OEJNI-90-3-5** large silver/clear-matte knob.

Final knob compatibility and shaft fit must be confirmed against the selected Bourns encoder.

The initial firmware should favor predictable behavior over acceleration or elaborate volume algorithms.

One accepted detent or movement should produce a clearly defined number of generic volume actions.

The actual event-to-command policy must be tested against network latency and queue behavior.

### 5.3 Custom-action encoder — Bourns PEC11R

The custom-action encoder is intended to:

- Rotate through the selected room's configured custom actions.
- Maintain the current selection in software.
- Execute the selected custom action when pressed.

The associated smaller black knob concept uses the **Kilo OEJL-63-4-7**.

The encoder should not contain device-specific command logic.

The custom-action list is room-dependent.

Selection behavior when changing rooms, encountering an empty list, or finding an unavailable action will be established during integration.

No elaborate menu system is required initially.

### 5.4 Reusable encoder class

A future `controls/encoders.py` module should provide a reusable `Encoder` class.

The class should handle:

- A/B quadrature input.
- Direction detection.
- Contact bounce.
- Movement event reporting.
- Nonblocking operation.
- Initialization and cleanup.

It should **not** know whether it controls volume or custom actions.

`physical.py` interprets encoder movement according to the assigned control role.

The encoder pushbuttons can reuse the existing `Button` class.

### 5.5 Encoder bench history

The Bourns custom-action encoder has undergone soldering and standalone electrical experimentation.

Earlier work included:

- Identifying A/B and common contacts.
- Continuity testing.
- Identifying the separate pushbutton contacts.
- Soldering signal and ground leads.
- Heat-shrink insulation.
- Bench observation of rotary movement.

These tests established useful electrical familiarity with the component.

They do **not** establish that a production encoder driver is integrated or that high-rate rotation is reliably captured during network traffic.

The permanent `Encoder` class remains future work.

### 5.6 Polling and blocking HTTP

The current physical-control scheduler targets a 10 ms interval.

This is adequate for the tested momentary button and maintained room selector.

Rotary encoders can generate transitions much faster.

Synchronous outbound HTTP may temporarily block the scheduler.

Possible future solutions include faster polling, separate scheduling intervals, hardware-assisted decoding, event accumulation, or volume-command coalescing.

These are options to evaluate, not implemented features.

**Measure the real Bourns behavior before adding complexity.**

### 5.7 Historical Grayhill decision

The **Grayhill 62A22-02-040C** was originally considered for volume control.

Its electrical interface and possible optical-encoder requirements motivated caution about voltage, signal type, and decoder compatibility.

That plan was replaced by the decision to use two Bourns PEC11R encoders.

The Grayhill is no longer part of the active hardware integration plan.

Historical discussion remains useful for understanding why encoder interfaces should never be assumed interchangeable.

---

## 6. Navigation, playback, and function buttons

The desired navigation cluster is:

**UP / DOWN / LEFT / RIGHT / OK**

It should be intuitive by touch.

Additional intended controls include:

- Back.
- Home.
- Play/Pause.
- Skip Back.
- Skip Forward.
- Guarded Power Toggle.

Mute is assigned to the volume encoder's pushbutton.

The fourteen firmware fundamentals **do not require fourteen dedicated physical buttons**.

Candidate tactile hardware includes **Adafruit #3347 metal-ball momentary switches**, ordered for experimentation.

Open decisions include travel, force, spacing, repeat behavior, debounce, illumination, and final mounting.

Held navigation buttons must not flood the network.

### 6.1 Generic action vocabulary

The current fourteen fixed action IDs are:

| Category | IDs |
|---|---|
| Volume | `volume-up`, `volume-down`, `mute-toggle` |
| Navigation | `nav-up`, `nav-down`, `nav-left`, `nav-right`, `select`, `back`, `home` |
| Playback | `play-pause`, `skip-back`, `skip-forward` |
| Equipment power | `power-toggle` |

Config v4 also supports room-specific executable custom actions.

These may contain multiple GET/POST steps and cooperative waits.

All physical controls should invoke actions through the **same shared dispatcher** used by the browser Test Remote.

### 6.2 Current button mapping

`physical.py` owns the hardware-name-to-action mapping.

```python
BUTTON_ACTIONS = {
    "POWER_TOGGLE": "power-toggle",
    "HOME": "home",
    "BACK": "back",
    "UP": "nav-up",
    "DOWN": "nav-down",
    "LEFT": "nav-left",
    "RIGHT": "nav-right",
    "SELECT": "select",
    "VOLUME_MUTE": "mute-toggle",
}
```

Only controls with assigned GPIO pins are initialized.

At present, the GP2 Power Toggle is the verified physical action button.

The remaining mappings are prepared for future hardware integration.

The custom-action encoder's pushbutton is intentionally handled separately because it executes a selected custom-action ID rather than a fixed fundamental action.

### 6.3 Toggle semantics

Configured ON/OFF paths for mute and power are operational through the dispatcher.

The system maintains independent volatile command-direction histories per room and action.

History is not authoritative equipment state.

Other remotes, HDMI-CEC, applications, and manual controls may change equipment state independently.

---

## 7. SYSTEM MASTER: guarded power and ignition concept

**Design status:** Awake physical Power Toggle operational; deep-sleep ignition remains conceptual.

This is a signature feature and deserves its own design record.

The guarded **SYSTEM MASTER momentary button** is intended to perform two logically distinct jobs:

1. While Clonker is awake, invoke the configured `power-toggle` action for the selected room.
2. When Clonker is in deep sleep, wake the controller and, **only if the wake cause is reliably identified**, initiate a single theater-power ON action.

SYSTEM MASTER is **not** GP17 filesystem ownership, GP18 CONFIG/RUN, the Pico reset control, or necessarily a direct power cut to the controller.

The physical button contains no hardcoded Denon/Roku commands.

### 7.1 Normal awake operation — implemented

A GP2 press invokes the configured `power-toggle` through the common action dispatcher.

The selected room comes from the physical room selector.

The existing dispatcher chooses the configured ON/OFF command using independent volatile histories.

November 2 testing verified real equipment ON and OFF in both configured rooms.

This does **not** establish the equipment's actual state independently of the command history.

### 7.2 Preferred deep-sleep ignition sequence

1. Lift the protective guard.
2. Press SYSTEM MASTER **once**.
3. Wake or reboot the Pico as required.
4. Play a short *engine-starting* sound, if audio hardware is available.
5. Reconnect Wi-Fi and load validated runtime configuration.
6. Invoke the selected room's configured **ON** command.
7. Resume normal remote operation.

**Provisional rule: Assume ON after deep sleep.**

Do not attempt to reconstruct the theater's previous power state across sleep.

The wake-triggered operation should use the configured `on_path`, and only if the real device command has the intended ON semantics.

A native toggle may turn off equipment already on and must be tested separately.

The ignition sound is reserved for genuine deep-sleep ignition, not every ordinary power press.

### 7.3 Wake-cause safety and exactly-once behavior

The Pico must reliably distinguish a SYSTEM MASTER wake from an ordinary reset, power restoration, or unrelated reboot **before automatically sending any theater power command**.

If that cannot be established, the acceptable fallback is to wake, restore operation, **send no automatic power command**, and wait for the next deliberate SYSTEM MASTER press.

One physical press/release must never generate duplicate equipment commands.

Debounce and release handling must account for boot and Wi-Fi startup.

### 7.4 Light sleep is optional

Light sleep could begin after inactivity and wake transparently on an ordinary control.

If power savings are small or Wi-Fi/input complexity excessive, omit it.

A simple **AWAKE / DEEP SLEEP** model is acceptable.

### 7.5 Battery and power architecture

Rechargeable battery operation is preferred, but battery, charging circuitry, and power distribution are **not finalized**.

A regulated USB power bank is a candidate for early experiments.

Measure or verify:

- Pico Wi-Fi current.
- Idle and sleep current.
- Reconnection cost.
- OLED and audio load.
- Encoder input requirements.
- Battery capacity.
- Safe charging.
- USB maintenance access.

Some power banks shut off under low-current loads.

Mechanical unilluminated switches should have negligible steady-state draw, but illuminated controls and supporting circuits may not.

### 7.6 Required experiments before ignition

1. Verify Pico 2 W / CircuitPython support for the intended sleep state and wake GPIO.
2. Confirm a brief momentary press can wake the system without being held through boot.
3. Reliably identify wake cause.
4. Measure awake, idle, sleep, and Wi-Fi reconnect current and timing.
5. Prove one press produces **at most one** power action.
6. Verify the actual configured ON command.
7. Test optional startup audio.
8. Verify battery and power compatibility.

Prior ESP32-S3 sleep experiments are historical, **not proof** of Pico 2 W behavior.

No wake GPIO, sleep state machine, battery management, ignition sound, or wake-triggered equipment action exists in current firmware.

**One guarded button. One deliberate press. The Clonker handles the rest.**

*Because apparently turning on the television now requires starting an engine.*

### 7.7 Guard, button, and illumination

The preferred mechanical concept is a flip-up red ignition guard over a comfortably accessible momentary button.

The **FILN 19 mm red-ring momentary pushbutton** has been obtained for experimentation.

The mechanical switch uses separate contact and illumination circuits.

The NO/COM contacts were used during earlier button testing.

The advertised illumination is for 12 V/24 V operation.

**Never drive a 12 V/24 V LED ring directly from Pico GPIO.**

The red protective guard remains part of the design.

Evaluate button height, guard clearance, mounting depth, actuation feel, and illumination compatibility before final assembly.

---

## 8. Operating-mode switches and room selector

### 8.1 Two independent operating-mode switches

| Control | GPIO | Evaluated | Purpose |
|---|---|---|---|
| Boot-mode switch | GP17 | At boot | SERVICE (USB) / DEVICE |
| Application-mode switch | GP18 | During runtime | CONFIG / RUN |

Neither switch is an AV equipment power control.

GP17 determines filesystem write ownership.

GP18 determines whether the management interface is available.

**These are independent operating dimensions.**

The application-mode switch can change without rebooting.

Changing boot-mode filesystem ownership requires a power cycle.

### 8.2 Physical room selector — operational

The three-position rotary room selector is electrically verified and integrated into the running application.

It establishes room context for physical actions.

The current mapping is:

| Knob position | GPIO | Wire | Room |
|---|---|---|---|
| LEFT | GP3 | Yellow | `room-1` — Den |
| MIDDLE | GP4 | Green | `room-2` — Sunroom |
| RIGHT | GP5 | Blue | `room-3` — Reserved |

Room 3 is a harmless no-op until configured.

There is **no fallback to Room 1**.

There is no BOTH mode.

Changing the room selector alone does not transmit AV commands.

### 8.3 Selected hardware

The selected device is a three-position, two-pole rotary selector.

Only one pole is used.

Its terminals were initially undocumented, requiring manual continuity testing to identify the common and individual position contacts.

### 8.4 Verified terminal mapping

**Orientation:** Viewed from the rear, with the selector's metal crossbar horizontal. Knob positions are described from the front.

| Knob position | Common terminal | Connected terminal |
|---|---|---|
| 1 — full left | 9 o'clock | 6 o'clock |
| 2 — middle | 9 o'clock | 5 o'clock |
| 3 — full right | 9 o'clock | 4 o'clock |

These connections were established through multimeter continuity testing.

The selector's other pole remains unused.

### 8.5 Wiring

| Connection | Wire | Earlier breadboard reference | Pico |
|---|---|---|---|
| Common, 9 o'clock | Black | WAGO ground bus | GND |
| Position 1, 6 o'clock | Yellow | Row 15 | GP3 |
| Position 2, 5 o'clock | Green | Row 16 | GP4 |
| Position 3, 4 o'clock | Blue | Row 17 | GP5 |

The breadboard row numbers are historical test references, not permanent wiring requirements.

The current application GPIO assignments are:

```python
ROOM_SELECTOR_A_PIN = 3
ROOM_SELECTOR_B_PIN = 4
ROOM_SELECTOR_C_PIN = 5
```

Each GPIO input uses the Pico's internal pull-up resistor.

The selected position connects one input to ground, producing LOW.

The other inputs remain HIGH.

No external pull-up resistors or selector power supply are required.

### 8.6 Standalone verification — October 31, 2026

A standalone CircuitPython test was executed from the REPL:

```python
exec(open("/tests/test_room_selector.py").read())
```

The test monitored all three GPIO inputs and reported the selected position.

Observed results:

```text
SELECTED: LEFT
SELECTED: MIDDLE
SELECTED: RIGHT
```

Additional rotations confirmed reverse transitions.

**Result: PASS — all three positions detected correctly.**

This established the contact mapping, ground connection, signal wiring, and GPIO input configuration.

### 8.7 Permanent wiring preparation

The selector's component-side connections were prepared for soldering and individual heat-shrink insulation after the successful breadboard test.

Permanent wiring should follow these practices:

1. Disconnect power before soldering.
2. Solder component-side connections securely.
3. Insulate individual terminals.
4. Provide wire strain relief.
5. Verify continuity and absence of shorts.
6. Repeat the GPIO test after significant wiring changes.

The later Cowbell-based runtime test confirms that the installed GPIO connections operate, but final enclosure cable routing and strain relief still require inspection.

### 8.8 Application integration — November 2, 2026

`controls/selectors.py` now owns the physical room-selection state.

It initializes GP3, GP4, and GP5 as active-low inputs with internal pull-ups.

A valid position requires exactly one grounded input.

Zero or multiple grounded inputs are considered invalid or transitional.

Invalid readings do not replace the last valid selection.

A new valid selection must remain stable for **50 ms** before being accepted.

The module exposes:

```python
selectors.initialize()
selectors.selected_room()
selectors.poll()
selectors.deinit()
```

`selected_room()` returns the last valid stable room ID.

`poll()` reports a changed stable selection.

The module does not send network commands and does not know whether a room is configured.

### 8.9 Runtime verification

PuTTY confirmed startup initialization and changes among all three positions.

Representative output:

```text
Room selector initialized; selected = room-1
ROOM SELECTED: room-2
ROOM SELECTED: room-3
ROOM SELECTED: room-1
```

The selector operated alongside the browser and other physical controls.

**Result: PASS — physical room-selection state operational.**

### 8.10 Reserved Room 3

The third selector position is reserved for a future third configured room.

Until then, physical actions are ignored safely.

Representative diagnostic:

```text
PHYSICAL NO-OP: room-3 / power-toggle (room unavailable)
```

No command is queued.

No HTTP request is sent.

The other rooms' toggle histories remain unchanged.

The selector is already capable of representing `room-3`; future room support should not require changing the physical mapping.

**Room 3 is reserved for future CLONKING.**

---

## 9. OLED and audible feedback

### 9.1 OLED status display

The early candidate was a **0.49-inch SSD1306 OLED, 64 × 32 pixels, I2C**.

Subsequent mechanical planning has also included a larger approximately **1.3-inch OLED module**, with a blue PCB and four mounting holes.

M2.5 mounting hardware and nylon spacers have been considered for installation.

The final display choice, mounting arrangement, GPIO assignment, driver, and UI remain to be verified.

The display is optional.

Ordinary volume, navigation, and action execution must not depend on it.

Potential information includes selected room, selected custom action, operating mode, and concise status feedback.

These are design possibilities, not implemented UI features.

### 9.2 Audible feedback

Candidate components include:

| Component | Proposed role |
|---|---|
| Adafruit PS1240 piezo element (PID 160) | Simple tones |
| Adafruit MAX98357A I2S amplifier (PID 3006) | Richer audio |
| MECCANIXITY 23 mm, 8 Ω, 1 W mini speakers | Speaker audition |

Possible uses include startup ignition, action confirmation, mode-change chirps, and errors.

Sound should be brief, optional, and appropriate for handheld use.

It must **not block input responsiveness**.

An internal speaker without visible exterior holes remains a mechanical possibility.

Verify amplifier/speaker compatibility, power requirements, and GPIO/I2S assignments before wiring.

No audio subsystem is implemented.

---

## 10. Parts and procurement register

**Status convention:** These records distinguish documented selection and purchase history from actual testing.

| Item | Part / description | Purpose | Current record |
|---|---|---|---|
| Controller | Raspberry Pi Pico 2 W | Active controller | In use; verified |
| Earlier controller | Unexpected Maker FeatherS3[D] | Historical platform | Superseded |
| Terminal board | Adafruit Pico Cowbell Terminal | Screw-terminal GPIO | In use |
| Ground distribution | WAGO lever connectors | Shared GND | In use |
| Boot switch | Maintained toggle | GP17 SERVICE/DEVICE | Installed; verified |
| CONFIG/RUN switch | Guarded maintained switch | GP18 application mode | Installed; verified |
| Power button | Momentary button, GP2 | Power Toggle | Installed; ON/OFF verified |
| Room selector | Three-position rotary, two-pole | Room selection | Wired; verified |
| Volume encoder | Bourns PEC11R-4215F-S0024 | Volume and Mute | Selected; integration pending |
| Action encoder | Bourns PEC11R-4215F-S0024 | Custom-action selection | Bench-tested; integration pending |
| Former volume encoder | Grayhill 62A22-02-040C | Earlier design | Superseded |
| Large knob | Kilo OEJNI-90-3-5 | Volume knob candidate | Fit to verify |
| Small knob | Kilo OEJL-63-4-7 | Action knob candidate | Fit to verify |
| Tactile switches | Adafruit #3347 metal-ball | Navigation/playback | Ordered candidate |
| Guarded button | FILN 19 mm red-ring momentary | SYSTEM MASTER | Bench-tested contact concept |
| Guard | Red Start Engine cover | Power control | Candidate |
| Slide switches | uxcell 3-position DPDT assortment | Earlier selector experiments | Historical candidate |
| OLED, small | SSD1306 64×32 I2C | Status | Earlier candidate |
| OLED, larger | Approx. 1.3-inch module | Status | Mounting evaluation |
| OLED spacers | Bivar 907-3MM nylon spacers | Mounting | Ordered |
| Piezo | Adafruit PS1240 | Tones | Ordered candidate |
| I2S amp | Adafruit MAX98357A | Audio | Ordered candidate |
| Speakers | MECCANIXITY 23 mm, 8 Ω, 1 W | Audio | Ordered candidate |
| Faceplate | Pre-cut aluminum | Control mounting | Fitted to enclosure |
| Enclosure | Black semi-rigid zippered case | Housing | Current prototype |
| Breadboard | Adafruit 830-tie, PID 239 | Early prototyping | Previously in use |
| Jumpers | Dupont assortment | Wiring/tests | In use |
| Solid wire | 22 AWG assortment | Signal wiring | In use |
| Test leads | WG-026 alligator leads | Temporary testing | Ordered |
| Resistors | ALLECIN assortment | Experiments | Ordered |
| LEDs | 3 mm / 5 mm assortment | Indicators | Ordered |

This is a project record, not a verified warehouse inventory.

Where receipt, exact dimensions, or final installation are uncertain, do not infer them from purchase history.

When adding parts, record manufacturer/model, quantity, received/tested status, contact type, voltage, dimensions, intended function, and eventual GPIO.

---

## 11. GPIO ownership and physical-input software boundary

### 11.1 Current pin assignment status

| Control/interface | GPIO | Status |
|---|---|---|
| SERVICE/DEVICE boot switch | GP17 | Implemented; verified |
| CONFIG/RUN switch | GP18 | Implemented; verified |
| Power Toggle momentary input | GP2 | Operational |
| Room selector LEFT, yellow | GP3 | Operational |
| Room selector MIDDLE, green | GP4 | Operational |
| Room selector RIGHT, blue | GP5 | Operational |
| Room selector common, black | GND | WAGO distribution |
| Volume encoder A/B/press | TBD (`None`) | Not integrated |
| Action encoder A/B/press | TBD (`None`) | Not integrated |
| Navigation, Back, Home | TBD (`None`) | Not integrated |
| Playback buttons | TBD | Not integrated |
| OLED I2C | TBD | Not integrated |
| Audio / I2S | TBD | Not integrated |
| Indicator LEDs | TBD | Not integrated |

`controls/pins.py` is the authoritative assignment map for application physical inputs.

GP17 boot-mode handling is implemented separately in `boot.py`.

Do not assign GPIO pins merely to complete a diagram.

Review electrical requirements, voltage, pin conflicts, wake capability, and enclosure wiring first.

### 11.2 Physical-control software modules

| Module | Responsibility | Status |
|---|---|---|
| `pins.py` | GPIO assignments | Implemented |
| `buttons.py` | Momentary inputs, debounce | Implemented; tested |
| `switches.py` | CONFIG/RUN state | Implemented; tested |
| `selectors.py` | Physical room state | Implemented; tested |
| `physical.py` | Polling, mapping, shared dispatch | Implemented; tested |
| `encoders.py` | Rotary movement/direction | Planned |

**Buttons produce events. Maintained switches and selectors represent states.**

The GP18 switch represents application mode.

The room selector represents room context.

The GP2 button produces an event that can trigger a room-specific action.

### 11.3 Operational event path

```text
       PHYSICAL CONTROL
              |
              v
      GPIO + DEBOUNCE
              |
              v
       physical.poll()
              |
              v
       BUTTON_ACTIONS
              |
              v
    dispatch_selected()
              |
              +----> selectors.selected_room()
              |
              v
       ROOM CONFIGURED?
          /       \
        YES        NO
         |          |
         |        NO-OP
         v
 actions.dispatch(room_id, action_id)
         |
         v
      DUMB QUEUE
         |
         v
    actions.poll()
         |
         v
  CONFIGURED HTTP COMMAND
         |
         v
    AV EQUIPMENT
```

The physical-control code must not contain Roku commands, Denon commands, or device-specific URLs.

GPIO wiring definitions are developer-owned firmware constants, not ordinary user-editable JSON configuration fields.

### 11.4 Shared dispatch helper

`physical.py` provides:

```python
dispatch_selected(action_id)
```

The helper:

1. Reads the selected room.
2. Checks whether it exists in the active configuration.
3. Returns a safe no-op if unavailable.
4. Calls the existing `actions.dispatch()` for configured rooms.
5. Logs dispatch errors without crashing the poller.

The same helper can serve future navigation buttons, volume events, and other ordinary physical actions.

Custom-action selection will require additional selection state, but should still use the shared action dispatcher.

### 11.5 Polling responsibilities

`main.py` schedules `physical.poll()` at approximately 10 ms intervals.

`physical.poll()` updates the selector before processing button events.

This ordering helps ensure that a button event uses the latest accepted room state.

The selector's own debounce is 50 ms.

The reusable button debounce defaults to 30 ms.

These are independent of the 10 ms scheduler target.

No blocking sleep is required inside the input drivers.

The physical polling path runs before action-queue execution in the main cooperative loop.

### 11.6 Performance boundary

The existing network transport is synchronous and blocking.

A blocking outbound HTTP operation can delay GPIO polling.

That limitation has not caused a reported problem with the tested room selector or Power Toggle.

It remains important for the planned rotary encoders.

Future input drivers must avoid flooding the queue with bounce, held-button repeats, or excessively fast encoder events.

Do not assume that a faster nominal poll interval alone solves blocking-network capture problems.

---

## 12. Electrical design and bench safety

Before connecting a component:

1. Confirm its exact manufacturer part number and datasheet.
2. Identify contacts, commons, polarity, push-switch terminals, and separate illumination terminals.
3. Verify momentary versus maintained behavior, supply voltage, signal levels, and maximum current.
4. Keep Pico GPIO at compatible **3.3 V logic**; never apply 5 V, 12 V, or 24 V directly to GPIO.
5. Use appropriate pull-ups/pull-downs, current limiting, and drivers.
6. Avoid floating inputs and verify power and ground before energizing.
7. Prototype one input at a time.
8. Observe raw transitions before adding debounce or dispatch.
9. Confirm encoder A/B and pushbutton contacts independently.
10. Check battery, charging, and audio power budgets before combining loads.
11. Document verified wiring and pin assignments after actual bench tests.
12. Inspect screw-terminal retention, solder joints, heat-shrink insulation, and strain relief.

For GP17, GP18, GP2, and the room selector, the established convention uses active-low GPIO inputs with common ground.

Mechanical switch terminals and wire strain relief deserve particular attention before final enclosure installation.

The Cowbell screw-terminal board improves serviceability but does not eliminate the need for careful electrical verification.

No final PCB or permanent battery architecture is implied.

---

## 13. Open mechanical and system decisions

- Final component drilling and faceplate layout.
- Encoder spacing, shaft fit, and knob mounting.
- Navigation cluster and button feel.
- Guarded Power Toggle mounting and illumination.
- Final mounting and cable routing for GP17 and GP18.
- Room selector enclosure mounting and strain relief.
- OLED module selection and mounting.
- Speaker placement, amplifier wiring, and sound level.
- Battery chemistry, capacity, charging, and low-power behavior.
- Wake-capable GPIO and reliable ignition wake identification.
- Final GPIO allocation.
- Service connectors and USB access.
- Encoder polling strategy under blocking HTTP.
- Custom-action selection behavior across room changes.

These are **open decisions**, not omissions to fill with guesses.

The room selector's electrical mapping and Room 3 semantics are no longer open decisions.

Both are implemented and tested.

---

## 14. Hardware development sequence

The browser-controlled firmware already executes real Denon/Roku commands and compound custom actions.

The physical subsystem now shares that execution path.

### 14.1 Chapter 5 — completed foundation

1. **DONE:** Establish optional physical-control initialization and cooperative polling.
2. **DONE:** Wire GP2 and verify momentary press/release events.
3. **DONE:** Replace GP17 boot jumper with a maintained physical switch.
4. **DONE:** Wire GP18 and verify live CONFIG/RUN transitions.
5. **DONE:** Characterize three-position room selector using continuity testing.
6. **DONE:** Wire selector to GP3, GP4, GP5, and common ground.
7. **DONE:** Verify LEFT, MIDDLE, and RIGHT using standalone CircuitPython test.
8. **DONE:** Record selector GPIO assignments in `pins.py`.

Chapter 5 established the GPIO foundation.

### 14.2 Chapter 6 — completed integration milestones

1. **DONE:** Add `selectors.py` with debounced room state.
2. **DONE:** Initialize and poll selector through `physical.py`.
3. **DONE:** Verify room transitions through PuTTY.
4. **DONE:** Establish shared physical-event-to-action mapping.
5. **DONE:** Implement `dispatch_selected()` for room-aware actions.
6. **DONE:** Establish Room 3 reserved/no-op behavior.
7. **DONE:** Connect GP2 Power Toggle to existing action dispatcher.
8. **DONE:** Verify Sunroom Power ON.
9. **DONE:** Verify Sunroom Power OFF.
10. **DONE:** Verify Den Power ON.
11. **DONE:** Verify Den Power OFF.
12. **DONE:** Confirm independent per-room power-toggle histories.

**Milestone: First fully operational physical hardware-to-equipment command path.**

### 14.3 Next development work

The next work is proposed rather than fixed:

1. Review current wiring and complete any remaining solder/strain-relief work.
2. Implement reusable Bourns encoder driver.
3. Test one encoder independently.
4. Integrate volume rotation and mute press.
5. Measure missed events during network execution.
6. Integrate custom-action encoder selection and execution.
7. Add navigation, Back, and Home controls.
8. Integrate playback controls.
9. Evaluate OLED status display.
10. Evaluate optional audio feedback.
11. Continue faceplate machining and enclosure assembly.
12. Experiment with rechargeable power and sleep/wake behavior.

The guiding principle remains:

**One meaningful hardware or firmware change at a time, followed by real Pico verification.**

---

## 15. Current verification snapshot — November 2, 2026

### 15.1 Core firmware

**Implemented and tested:**

- Pico 2 W / CircuitPython startup.
- Wi-Fi and USB/REPL operation.
- GP17 filesystem ownership.
- Config v4 browser management.
- Revision-protected configuration persistence.
- Browser Test Remote.
- Fundamental outbound GET/POST actions.
- Named custom actions.
- Cooperative Dumb Queue™.
- Roku → wait → Denon compound sequence.
- Runtime power/mute command-direction histories.

### 15.2 Physical hardware

**Implemented and tested:**

- GP17 SERVICE/DEVICE switch.
- GP18 CONFIG/RUN switch.
- GP2 momentary Power Toggle.
- GP3/GP4/GP5 room selector.
- Common-ground wiring.
- Cowbell-based GPIO connections.
- Room-selection debounce.
- Button press/release debounce.
- Room-aware physical dispatch.

### 15.3 Room selector

| Position | Wire | GPIO | Result |
|---|---|---|---|
| LEFT | Yellow | GP3 | PASS — Room 1 |
| MIDDLE | Green | GP4 | PASS — Room 2 |
| RIGHT | Blue | GP5 | PASS — Room 3 |

The common terminal connects to GND.

Standalone electrical verification occurred October 31.

Integrated runtime verification occurred November 2.

**Result: PASS.**

### 15.4 Physical Power Toggle

| Test | Result |
|---|---|
| Room 3 button press | PASS — no-op |
| Room 2 Power ON | PASS |
| Room 2 Power OFF | PASS |
| Room 1 Power ON | PASS |
| Room 1 Power OFF | PASS |
| Independent room histories | PASS |
| Room changes during runtime | PASS |

The tests used the actual physical controls and real home-theater equipment.

**Result: PASS — hardware-to-equipment execution operational.**

### 15.5 Remaining integration work

**Not yet implemented:**

- Encoder driver and production quadrature decoding.
- Volume rotation.
- Custom-action selection and activation.
- Navigation and playback button integration.
- OLED driver and status UI.
- Audio feedback.
- SYSTEM MASTER wake/ignition.
- Battery management.
- Final enclosure assembly.

**Not exhaustively verified:**

- Encoder capture during blocking HTTP.
- Rapid repeated input under network load.
- Long-duration physical-control operation.
- All network and hardware failure combinations.
- Final permanent wiring and mechanical durability.

For dated engineering details, see [Development History](DEVELOPMENT_HISTORY.md).

Historical implementation snapshots should not be mistaken for current firmware status.

---

## 16. Related documents

- [Architecture](ARCHITECTURE.md) — system boundaries and common action dispatcher.
- [Configuration & Recovery](CONFIGURATION.md) — authoritative Config v4 schema and persistence.
- [Firmware, HTTP & Clock](FIRMWARE_NETWORK.md) — queue, scheduler, networking, and test evidence.
- [Operating Modes](OPERATING_MODES.md) — SERVICE (USB)/DEVICE and CONFIG/RUN.
- [Development & Deployment](DEVELOPMENT.md) — iPad-first workflow and bench deployment.
- [Development History](DEVELOPMENT_HISTORY.md) — historical decisions and dated verification.

---

**CLONK! ⚡🔩**

*The Clonker 10000 — because apparently a normal remote control wasn't complicated enough.*
