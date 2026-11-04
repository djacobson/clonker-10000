# THE CLONKER 10000
## Hardware & Physical Controls

**Design reference:** November 3, 2026  
**Controller:** Raspberry Pi Pico 2 W (RP2350), CircuitPython 10.3.1  
**Baseline:** Chapter 6 complete — physical room selection, Power Toggle, Bourns volume encoder, and GP10 push-to-mute operational in both rooms
**Source of GPIO truth:** [`firmware/clonker/controls/pins.py`](../firmware/clonker/controls/pins.py)

> A gloriously overengineered, tactile Wi-Fi home-theater remote. Real knobs, real buttons, questionable restraint, and absolutely no desire to become another touchscreen.

---

## 1. Purpose and evidence conventions

This is the **current hardware reference**: intent, layout, parts, wiring, electrical boundaries, verified behavior, and remaining work. The source code defines the implemented GPIO assignments and drivers; this document explains why the hardware is arranged as it is and what has actually been tested.

Use these distinctions throughout:

- **Operational:** integrated into the running firmware and exercised against real equipment.
- **Bench verified:** electrical or standalone test passed; not necessarily integrated.
- **Selected / obtained:** component chosen or purchased, without implying installation.
- **Concept / planned:** design intent, not a working feature.
- **Historical:** earlier decision or experiment retained for context.

Configuration and command semantics belong in [Configuration](CONFIGURATION.md); dispatch, queue, and adapter boundaries in [Architecture](ARCHITECTURE.md); timing and network behavior in [Firmware, Network & Clock](FIRMWARE_NETWORK.md); dated experiments in [Development History](DEVELOPMENT_HISTORY.md).

**Hardware detects events. Physical coordination maps intent. The shared Dumb Queue™ executes commands.** No GPIO driver should contain Denon or Roku command strings.

---

## 2. The Clonker Design Manifesto

**The Clonker 10000 is not a return to the past. It's a selective rescue operation.**

Once upon a time, remotes had substantial buttons, satisfying feedback, and enough heft to remind you that you were holding a piece of equipment. Unfortunately, some also had 117 buttons, six POWER switches, three mysterious INPUT selectors, and controls nobody had touched since the Reagan administration.

Then came the minimalist remote: sleek, tiny, and apparently designed for microscopic thumbs, perfect eyesight, and an unusually strong emotional attachment to sponsored streaming services.

The Clonker rejects the worst of both eras.

### Keep the good stuff

- Big, tactile controls identifiable without looking down.
- Beautiful metal knobs, purposeful switches, and mechanical feedback.
- Straightforward Home, Back, navigation, volume, and power operation.
- Serviceable construction, accessible fasteners, and repairable wiring.
- Modern Wi-Fi networking, editable JSON configuration, and reusable actions.
- A healthy appreciation for vintage Hi-Fi equipment and nuclear submarines.

### Throw the rest overboard

- A forest of tiny rubber buttons and sponsored streaming shortcuts.
- Sealed enclosures and microscopic, proprietary fasteners.
- Manufacturer-code archaeology and remotes teaching other remotes to blink.
- Elaborate activity wizards that lose their minds when someone changes an input.
- Features justified mainly by their appearance in a marketing photograph.

### The Harmony Memorial Department

Logitech Harmony and other universal-remote pioneers tackled a genuinely fragmented industry. The Clonker keeps their useful ambition—one configurable controller for multiple devices—without reproducing the old configuration rituals. Network control is the current path; IR is not an implemented feature.

**We want to watch the movie, not spend Saturday teaching the remote what a movie is.**

### Accessibility is good engineering

Large, distinct controls and operation in the dark are useful to everyone, not just a niche demographic. A remote should be usable by feel, without a scavenger hunt for the right button.

### Serviceability, Clonker style

Accessible internals, labeled wires, reasonable maintenance access, and space for experiments are worthwhile. An internal work light or elaborate latches are concepts, not commitments. If servicing the remote requires holding a flashlight in your teeth while chasing microscopic screws, we've failed.

The Clonker isn't retro. It isn't minimalist. It's **selectively maximalist**: maximum attention to what matters, minimum tolerance for what doesn't.

**Less sleek. More CLONK.**

---

## 3. Current operational hardware

### 3.1 Controller and terminal expansion

The active platform is a **Raspberry Pi Pico 2 W**, running **CircuitPython 10.3.1**. The Pico Cowbell Terminal board provides screw-down access for wiring. Earlier microcontroller choices, including the Unexpected Maker FeatherS3[D], are historical.

The current project uses WAGO lever connectors for common ground distribution, solid-core and pre-crimped wiring as appropriate, and insulated soldered component leads. Check each connector's conductor compatibility and retention: a small wire merely inserted into a lever terminal is not proof of a sound connection.

### 3.2 Verified GPIO assignment table

| Function | GPIO / connection | Status |
|---|---|---|
| Power Toggle momentary button | GP2 | Operational; real equipment ON/OFF tested |
| Room selector LEFT / Den (yellow) | GP3 | Operational |
| Room selector MIDDLE / Sunroom (green) | GP6 | Operational |
| Room selector RIGHT / reserved Room 3 (blue) | GP7 | Operational selection; action no-op |
| Room selector common (black) | GND | Wired through ground distribution |
| Volume encoder A (yellow) | GP8 | Operational |
| Volume encoder B (green) | GP9 | Operational |
| SERVICE (USB) / DEVICE boot switch | GP17 | Operational; handled by `boot.py` |
| CONFIG / RUN guarded switch | GP18 | Operational |
| Volume encoder push / Mute | GP10 | Operational; Den and Sunroom tested |
| Custom-action encoder A/B/push | `None` | Not assigned |
| Navigation, Home, Back | `None` | Not assigned |
| OLED I²C | GP4/GP5 reserved for STEMMA QT | Not integrated |
| Playback controls, speaker, indicator LEDs | TBD | Not integrated |

`None` means no GPIO is assigned; it does **not** mean that a component has been physically discarded. Do not fill unused pins in a diagram merely to make it look complete. Check pin conflicts, wake requirements, electrical compatibility, and physical routing first.

### 3.3 SERVICE (USB) / DEVICE — GP17

This maintained boot-mode switch controls **filesystem write ownership**, not the Clonker's equipment power.

| Electrical state | Mode | Filesystem writer |
|---|---|---|
| Open / pulled HIGH | SERVICE (USB) | USB host |
| Grounded / LOW | DEVICE | Pico firmware |

`boot.py` reads the switch during startup. Changing ownership requires a full power cycle; Ctrl+D does not reproduce a cold boot. In SERVICE mode the browser may inspect configuration, but firmware-side persistent saves are rejected because the Pico filesystem is read-only to the application.

### 3.4 CONFIG / RUN — GP18

This separate maintained switch controls the application management interface.

| Electrical state | Mode | Management HTTP |
|---|---|---|
| Open / pulled HIGH | RUN | Off |
| Grounded / LOW | CONFIG | On, port 9090 |

The application responds to GP18 changes without rebooting. The action queue operates in both modes. A simulated source and software override remain available for development. **SERVICE/DEVICE and CONFIG/RUN are independent dimensions.** See [Operating Modes](OPERATING_MODES.md).

### 3.5 Physical Power Toggle — GP2

The debounced momentary input is integrated with `physical.dispatch_selected("power-toggle")`. It selects the active physical room and enters the same action queue used by the browser Test Remote.

On November 2, real equipment testing passed Den ON/OFF and Sunroom ON/OFF, with independent per-room command-direction histories. Pressing the button while Room 3 was selected produced a harmless no-op because Room 3 was not configured.

This is **last-successful-command memory**, not equipment-state discovery. HDMI-CEC or another remote can change equipment state behind Clonker's back.

---

## 4. Three-position physical room selector

The selector is a maintained, three-position rotary control. It changes **room context**, not an equipment action.

| Position | Wire | Grounded input | Room |
|---|---|---|---|
| LEFT | Yellow | GP3 | `room-1` — Den |
| MIDDLE | Green | GP6 | `room-2` — Sunroom |
| RIGHT | Blue | GP7 | `room-3` — reserved |

The common terminal connects to GND. The GPIO inputs use internal pull-ups, so the active position pulls exactly one input LOW. The selector rejects invalid zero-active or multiple-active readings, retains the last valid room, and requires **50 ms** of stable input before accepting a change.

**Development chronology:** The selector was electrically verified on October 31 using GP3/GP4/GP5. It was integrated with the application November 2; green and blue were then moved to GP6/GP7 and retested to free GP4/GP5 for the Cowbell STEMMA QT/I²C connection. The older pin arrangement is historical and must not be used for current wiring.

Room 3 is a valid physical position but is not currently configured. A physical action for that room is rejected **before queue admission**; it must not silently fall back to Den or Sunroom. This preserves predictable operation if the third position is used later.

The selector wiring was continuity-tested, soldered/insulated as needed, and prepared for mechanical strain relief. Recheck connections after enclosure installation, especially where flexible leads meet component terminals.

---

## 5. Rotary encoders — Chapter 6

### 5.1 Component decision

Both principal rotary controls use the **Bourns PEC11R-4215F-S0024** mechanical incremental encoder. The earlier **Grayhill 62A22-02-040C** volume-encoder plan was superseded; the Grayhill is reserved for another project. Do not assume the Grayhill and Bourns electrical interfaces are interchangeable.

| Control | Rotation | Shaft press | Current status |
|---|---|---|---|
| Volume | `volume-up` / `volume-down` | `mute-toggle` | Rotation GP8/9 and push-to-mute GP10 operational in both rooms |
| Custom Actions | Cycle room's named actions | Execute selected action | Bench component work done; application integration pending |

Neither encoder is an absolute-position knob. Shaft angle does not represent a stored volume level or action index.

### 5.2 Operational volume encoder — GP8/GP9

The volume encoder is integrated into the running Pico firmware:

1. `controls/encoders.py` samples the A/B quadrature inputs with internal pull-ups.
2. Its transition table rejects invalid two-bit changes and accumulates valid movement.
3. A completed movement returns `+1` or `-1` to `physical.py`.
4. `physical.py` maps the direction to a generic `volume-up` or `volume-down` action.
5. `dispatch_selected()` applies the current physical room and admits work to the Dumb Queue™.
6. `device_adapters.py` selects the transport from the configured fundamental-action signature: Denon TCP, Roku ECP held-volume, or generic HTTP.

The reusable `Encoder` class supports direction reversal and configurable `steps_per_detent` (1, 2, or 4; current default 4). It does not know the selected room, receiver model, or network syntax.

The encoder's independent momentary pushbutton is connected between **GP10 and GND**. The existing `Button` driver detects its press, and `physical.py` dispatches the `mute-toggle` fundamental action.

**Observed equipment verification:**

- **Den:** Persistent Denon TCP volume control; slow, moderate, and aggressive rotation exercised.
- **Sunroom:** Roku ECP held-volume control; single detents, fast twists, direction reversals, and sustained rotation exercised.
- **Both rooms:** Physical encoder push-to-mute and push-to-unmute confirmed on real receivers.
- **RUN mode:** Fast and sustained Roku volume testing passed with the configuration listener disabled.

These are practical tests, not proof that no encoder transitions can ever be lost under every network condition.

### 5.3 Why volume is responsive now

The cooperative physical polling target is **1 ms**, not the former 10 ms.

The Denon TCP adapter reuses a connection and spaces native `MVUP`/`MVDOWN` commands by at least **50 ms**, without sleeping inside the queue.

The Roku held-volume adapter starts a key hold on the first detent and extends it locally on additional same-direction detents. An idle timeout releases the key, while direction reversal releases the previous direction before starting the opposite one.

This reduces repeated HTTP traffic during rapid rotation. The observed Sunroom receiver response was smooth, with slight display lag and very small overshoot.

The firmware remains cooperative rather than asynchronous. Network operations can still block physical sampling. No second volume queue or separate encoder execution pipeline is implemented.

See [Firmware, Network & Clock](FIRMWARE_NETWORK.md) for exact transport and scheduling behavior.

### 5.4 Custom-action encoder — remaining work

The second Bourns encoder has undergone contact identification, continuity checks, soldering, insulation, and standalone experimentation. It is **not yet initialized as an application rotary input**: its A/B/push GPIO assignments remain `None`.

Planned behavior is to cycle the selected room's named custom actions and run the chosen action on shaft press. Room changes, empty lists, and invalid selections need deliberate behavior. The encoder should reuse the quadrature driver and common action dispatcher, with software owning the current selection. No second command execution pipeline is justified.

### 5.5 Knobs and fit

The original large volume knob candidate was **Kilo OEJNI-90-3-5**; the smaller action knob candidate is **Kilo OEJL-63-4-7**. Confirm actual shaft diameter, flat/spline profile, panel clearance, retention, and hand ergonomics before final mounting. Component selection alone does not establish mechanical compatibility.

---

## 6. Buttons, navigation, and generic actions

The intended faceplate includes dedicated **Back** and **Home** controls, a five-way navigation cluster (Up/Down/Left/Right/OK), and selected playback controls. The large guarded Power Toggle is distinct from the boot and CONFIG switches.

`controls/buttons.py` provides a reusable active-low, internal-pull-up, nonblocking momentary driver. Its default debounce is **30 ms**. Stable `pressed` events dispatch; `released` events are diagnostic. `physical.py` maps button names to generic action IDs, so a future GPIO reassignment does not require changing device protocols.

Current firmware maps names such as `POWER_TOGGLE`, `HOME`, `BACK`, `UP`, `DOWN`, `LEFT`, `RIGHT`, `SELECT`, and `VOLUME_MUTE`. **Only assigned pins are initialized.** The Power Toggle and volume-encoder push-to-mute are operational. Physical navigation, Home, Back, and playback controls remain unintegrated.

The generic action vocabulary is defined by Config v4; do not confuse a physical button label with a manufacturer-specific command. The browser Test Remote already exercises the same action IDs independently of physical GPIO.

A future panel-orientation option has been discussed: a 180-degree layout could swap logical navigation directions (and playback skip direction) while retaining physical button identities. It is **not implemented**. Encoder reversal is supported at the driver level, but no general orientation configuration exists.

---

## 7. Enclosure and faceplate

### 7.1 Current mechanical direction

The project has progressed from loose breadboard wiring toward a **black semi-rigid zippered electronics case** with a **pre-cut aluminum faceplate**. The documented prototype concept includes a rectangular opening beneath the plate, ten distributed mounting bolts, underside washers/star washers/nuts, and accessible internals. Protective film stays on the aluminum during fitting and drilling where practical.

An early faceplate target was approximately **4.5 × 6.5 inches**, with **1.5–2 inches** of enclosure depth. Treat these as design targets, not final machining dimensions.

### 7.2 Proposed face layout — not a drilling template

```text
                THE CLONKER 10000

          +----------------------------+
          |   VOLUME        ACTIONS    |
          |      O             O       |
          |                            |
          |        BACK     HOME       |
          |                            |
          |              UP            |
          |               ^            |
          |        LEFT  OK  RIGHT     |
          |               v            |
          |             DOWN           |
          |                            |
          |    [ STATUS OLED ]         |
          |                  PLAY      |
          |                <<    >>    |
          |                            |
          |             [ POWER ]      |
          |             (guarded)      |
          +----------------------------+

             SIDE: ROOM SELECTOR
             CONFIG/RUN: GUARDED SWITCH
             SERVICE/DEVICE: BOOT SWITCH
```

Volume and action knobs belong prominently at the top. Back and Home should be distinguishable by touch; Home has been considered slightly higher. The room selector is intended for the right side, and the guarded power control near the lower right. A speaker may sit beneath the lid.

Before drilling, verify component dimensions, shaft clearance, washer/fastener footprints, reach, guard movement, OLED viewing angle, wiring bend radius, and access to the Pico USB port. The layout is intentionally provisional.

### 7.3 Strain relief and construction

Use insulated solder joints, heat-shrink tubing, sensible wire colors, and cable ties or anchors that transfer tugging force to the cable jacket rather than solder lugs. Leave service loops where the lid moves. Check the faceplate for burrs and protect wiring from sharp aluminum edges. Confirm no exposed conductor or mounting hardware can short the Pico or Cowbell.

---

## 8. SYSTEM MASTER — guarded power and future ignition

The current GP2 **Power Toggle** is a working command button. It does **not** presently turn Pico power on/off, enter deep sleep, or implement a wake sequence.

The broader **SYSTEM MASTER** concept is a conspicuous guarded control that could eventually wake a battery-powered remote, trigger its startup behavior, and command equipment. A red Start Engine-style guard and a **FILN 19 mm red-ring momentary** button have been considered or bench-tested. The guarded control's final mechanical and electrical implementation remains undecided.

### 8.1 Future deep-sleep behavior — design only

A potential sequence is: dormant Pico → intentional wake input → initialize Wi-Fi and application → interpret the initiating control exactly once → dispatch the appropriate action. This requires real testing of RP2350/CircuitPython sleep and wake support, GPIO wake constraints, switch polarity, startup timing, and the risk of duplicate events.

Do **not** assume a maintained guard switch and momentary press have the same semantics. Do not promise that a sleeping Pico can preserve a TCP connection or queue. A full restart after wake is acceptable as a design choice, but it is not yet implemented.

### 8.2 Battery and power architecture — open

Rechargeable operation, charging circuitry, protection, voltage regulation, runtime, safe charging access, and power isolation remain to be designed and measured. Never connect an unknown battery voltage directly to a GPIO or assume a nominal cell voltage is a suitable Pico supply. Illumination for a switch sold as 12/24 V requires its own electrical review; the button contacts and LED circuit are distinct.

---

## 9. OLED, audio, and tactile feedback

### 9.1 Display

A small **SSD1306 64×32, approximately 0.49-inch OLED** was selected for experimentation; a larger approximately **1.3-inch** option has also been considered. The display may eventually show room, selected custom action, mode, and brief status. GP4/GP5 are reserved for STEMMA QT/I²C, but **no OLED driver or UI is operational**.

Display failure should not disable basic remote operation. Mechanical visibility, mounting depth, legibility, I²C addressing, and power draw need testing. Bivar 907-3MM nylon spacers are among the mounting supplies noted.

### 9.2 Audible feedback

Potential components include an **Adafruit MAX98357A I²S amplifier**, **Adafruit PS1240 piezo**, and **MECCANIXITY 23 mm 8 Ω / 1 W speakers**. The design goal is a satisfying, optional audible **CLONK!**, not a dependency for every command. No sound subsystem is currently implemented.

---

## 10. Parts and procurement register

This is a **design and purchase-history register**, not a verified warehouse inventory. An order, receipt, bench test, and completed installation are different statuses.

| Item | Identifying part / type | Intended use | Evidence / status |
|---|---|---|---|
| Controller | Raspberry Pi Pico 2 W | Core firmware | Operational |
| Earlier controller | Unexpected Maker FeatherS3[D] | Previous platform | Historical / superseded |
| Terminal expansion | Adafruit Pico Cowbell Terminal | Screw-down GPIO | In use |
| Ground bus | WAGO lever connectors | Shared ground | In use |
| SERVICE/DEVICE switch | Maintained toggle | GP17 boot ownership | Verified |
| CONFIG/RUN switch | Guarded maintained toggle | GP18 app mode | Verified |
| Power Toggle button | Momentary switch | GP2 physical action | Operational |
| Room selector | Three-position rotary | Room context | Operational GP3/6/7 |
| Volume encoder | Bourns PEC11R-4215F-S0024 | Volume / push-to-mute | Rotation GP8/9 and mute GP10 operational |
| Action encoder | Bourns PEC11R-4215F-S0024 | Select / run custom action | Bench work; integration pending |
| Former encoder | Grayhill 62A22-02-040C | Former volume candidate | Superseded; reserved elsewhere |
| Large knob | Kilo OEJNI-90-3-5 | Volume | Fit to verify |
| Small knob | Kilo OEJL-63-4-7 | Actions | Fit to verify |
| Navigation switches | Adafruit #3347 tactile | Buttons | Candidate / ordered |
| Guarded momentary | FILN 19 mm red-ring | SYSTEM MASTER concept | Contact bench test; final use pending |
| Guard | Red Start Engine-style cover | Power control | Candidate |
| Slide switches | uxcell 3-position DPDT assortment | Early selector experiments | Historical candidate |
| Small OLED | SSD1306 64×32 | Status | Candidate / not integrated |
| Larger OLED | Approx. 1.3-inch module | Status | Mounting evaluation |
| OLED spacers | Bivar 907-3MM | Mounting | Ordered |
| Piezo | Adafruit PS1240 | Sound | Ordered candidate |
| I²S amplifier | Adafruit MAX98357A | Sound | Ordered candidate |
| Speakers | MECCANIXITY 23 mm, 8 Ω, 1 W | Sound | Ordered candidate |
| Faceplate | Pre-cut aluminum | Mounting | Prototype fitted to enclosure |
| Enclosure | Black semi-rigid zippered case | Housing | Current prototype concept |
| Breadboard | Adafruit 830-tie PID 239 | Early testing | Previously in use |
| Jumper wires | Dupont assortment | Wiring | In use |
| Solid wire | 22 AWG assortment | Signal wiring | In use |
| Test leads | WG-026 alligator leads | Bench work | Ordered |
| Resistors | ALLECIN assortment | Experiments | Ordered |
| LEDs | 3 mm / 5 mm assortment | Indicators | Ordered |

For any newly selected part, record exact model, quantity, received/installed/tested status, pinout, voltage, dimensions, mounting requirements, and GPIO assignment. Avoid promoting an unverified candidate to an operational component.

---

## 11. Electrical and firmware boundaries

### 11.1 Active-low inputs

Buttons and selector positions use internal pull-ups and connect their input to **GND** when active. Confirm contact types with a meter before wiring. A rotary encoder's A/B/common contacts are not interchangeable with its independent shaft pushbutton contacts.

Always disconnect Pico power before rewiring. Never put 12/24 V switch illumination or another external voltage directly onto a Pico GPIO. Verify polarity, continuity, shorts, and mechanical strain relief before powering a new assembly.

### 11.2 Module responsibilities

| Module | Responsibility | Current status |
|---|---|---|
| `controls/pins.py` | Named GPIO assignments | Operational |
| `controls/buttons.py` | Debounced momentary events | Operational |
| `controls/switches.py` | CONFIG/RUN switch state and override | Operational |
| `controls/selectors.py` | Debounced room context | Operational |
| `controls/encoders.py` | Reusable quadrature decoder | Operational for volume |
| `controls/physical.py` | Initialize/poll controls, map events, dispatch | Operational |
| `actions.py` | Shared Dumb Queue™ and execution | Operational |
| `device_adapters.py` | Cached recognition of specialized commands | Operational |
| `devices/denon.py` | Persistent TCP volume adapter and pacing | Operational |

The volume encoder uses the **same generic action dispatcher** as the physical Power Toggle and browser remote. The adapter is selected from the configured fundamental command signature, not the room name or a hardcoded AVR slot. Custom-action steps currently use generic HTTP.

### 11.3 Cooperative timing and limits

`main.py` targets **1 ms** physical polling, **10 ms** action polling, **1 ms** CONFIG web polling, and a **1 ms** loop yield. These are cooperative intervals, not hard real-time guarantees. The room selector uses **50 ms** debounce; momentary buttons use **30 ms** by default.

Persistent Denon TCP reduces repeated connection overhead but cannot guarantee capturing every physical transition during a blocking socket operation. Queue capacity is bounded, and one execution failure cancels remaining queued work. Do not interpret a network acknowledgment as proof of physical equipment state.

---

## 12. Verification timeline and present status

| Date / phase | Test or milestone | Result |
|---|---|---|
| Chapter 5 | Optional GPIO initialization, polling, button debounce | Passed |
| October 28–29 | GP17 SERVICE/DEVICE and GP18 CONFIG/RUN | Passed |
| October 31 | Three-position selector standalone test on GP3/4/5 | Passed; historical wiring |
| November 2 | Selector integrated and reassigned to GP3/6/7 | Passed |
| November 2 | Room-aware Power Toggle, Den and Sunroom | Passed; real equipment |
| November 2 | Room 3 selected, physical action rejected | Passed; safe no-op |
| Chapter 6, November 3 | Reusable Bourns encoder driver and GP8/9 volume integration | Passed |
| Chapter 6, November 3 | Slow, moderate, aggressive physical volume testing | Passed in observed trials |
| Chapter 6, November 3 | Persistent Denon TCP and 50 ms command pacing | Passed |
| Chapter 6, November 3 | Mixed-transport queue regression testing | Passed |
| November 3 | Roku ECP held-volume, fast reversals, sustained rotation | Passed; slight lag and overshoot observed |
| November 3 | Mixed-room volume: Denon TCP / Roku ECP | Passed |
| November 3 | Bourns encoder push-to-mute on GP10 | Passed in Den and Sunroom |
| November 3 | Physical controls in RUN mode | Passed |

The first operational hardware-to-equipment control path arrived with the physical Power Toggle. The volume encoder extended that path without inventing a second queue or placing protocol logic in a GPIO driver.

**What these tests do not establish:** indefinite error-free high-rate capture, all receiver-restart scenarios, long-uptime behavior, final enclosure durability, battery operation, or wake-from-sleep semantics. Preserve detailed dated observations in [Development History](DEVELOPMENT_HISTORY.md).

---

## 13. Next physical development work

Recommended sequence, subject to bench realities:

1. Integrate the second **custom-action encoder**, including selection state, room changes, empty lists, and push-to-run.
2. Add Home, Back, and the five-way navigation cluster with the shared button mapping.
3. Evaluate playback controls and their final ergonomic placement.
4. Test OLED and optional sound independently before relying on either for feedback.
5. Finalize the guarded power mechanism, mechanical layout, cable routing, and enclosure assembly.
6. Design and measure battery supply, charging, sleep, and wake behavior before calling SYSTEM MASTER an ignition system.
7. Run extended real-equipment tests, including network interruption, receiver restart, and simultaneous browser/encoder activity.

Keep the known-good Pico configuration and working physical controls intact while introducing each new input. A component can be absent or disconnected without taking down the whole application; warn and continue wherever the existing optional-input architecture allows it.

**One meaningful change at a time. One shared execution path.**

---

## 14. Related documents

- [Architecture](ARCHITECTURE.md) — system boundaries, shared dispatcher, queue, adapter selection.
- [Configuration & Recovery](CONFIGURATION.md) — Config v4 schema, persistence, revision protection.
- [Firmware, Network & Clock](FIRMWARE_NETWORK.md) — scheduler, Denon TCP, generic HTTP, diagnostics, tests.
- [Operating Modes](OPERATING_MODES.md) — GP17 and GP18 behavior.
- [Development & Deployment](DEVELOPMENT.md) — iPad-first workflow, Pico deployment, tests.
- [Development History](DEVELOPMENT_HISTORY.md) — dated decisions, experiments, and evidence.

---

**THE CLONKER 10000**  
*Less sleek. More CLONK.*  
**CLONK! ⚡🔩**
