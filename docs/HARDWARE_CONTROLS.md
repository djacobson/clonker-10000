# THE CLONKER 10000
## Hardware & Physical Controls

**Design reference:** November 7, 2026  
**Controller:** Raspberry Pi Pico 2 W (RP2350), CircuitPython 10.3.1  
**Baseline:** Chapter 7 in progress — physical room selection, Power Toggle, volume encoder/push-to-mute, and physical navigation/playback buttons operational; six Roku hold-capable buttons tested  
**Source of GPIO truth:** [`firmware/clonker/controls/pins.py`](../firmware/clonker/controls/pins.py)

> A gloriously overengineered, tactile Wi-Fi home-theater remote. Real knobs, real buttons, questionable restraint, and absolutely no desire to become another touchscreen.

---

## 1. Purpose and evidence conventions

This is the **current hardware reference**: design intent, physical layout, parts, wiring, electrical boundaries, verified behavior, and remaining work. Firmware defines the implemented GPIO assignments and drivers; this document records what is built and tested.

- **Operational:** Integrated into running firmware and exercised against real equipment.
- **Bench verified:** Electrical or standalone test passed, but full application integration is not necessarily complete.
- **Assigned:** A GPIO mapping exists in firmware; this alone does not prove functional integration.
- **Selected / obtained:** Component chosen or purchased; installation is not implied.
- **Planned:** Design intent, not a working feature.
- **Historical:** Earlier decisions retained for context.

Configuration semantics belong in [Configuration](CONFIGURATION.md); queue and adapter boundaries in [Architecture](ARCHITECTURE.md); network timing in [Firmware, Network & Clock](FIRMWARE_NETWORK.md); and development milestones in [Development History](DEVELOPMENT_HISTORY.md).

**Hardware detects events. Physical coordination maps intent. The shared Dumb Queue™ executes commands.** GPIO drivers do not contain Roku or Denon command strings.

---

## 2. The Clonker Design Manifesto

**The Clonker 10000 is not a return to the past. It's a selective rescue operation.**

Once upon a time, remotes had substantial buttons, satisfying feedback, and enough heft to remind you that you were holding equipment. Unfortunately, some also had 117 buttons, six POWER switches, three mysterious INPUT selectors, and controls nobody had touched since the Reagan administration.

Then came the minimalist remote: sleek, tiny, and apparently designed for microscopic thumbs, perfect eyesight, and an unusually strong emotional attachment to sponsored streaming services.

The Clonker rejects the worst of both eras.

### Keep the good stuff

- Big, tactile controls identifiable without looking down.
- Beautiful metal knobs, purposeful switches, and mechanical feedback.
- Straightforward Home, Back, navigation, volume, playback, and power operation.
- Serviceable construction, accessible fasteners, and repairable wiring.
- Modern Wi-Fi networking, editable JSON configuration, and reusable actions.
- A healthy appreciation for vintage Hi-Fi equipment and nuclear submarines.

### Throw the rest overboard

- Forests of tiny rubber buttons and sponsored streaming shortcuts.
- Sealed enclosures and microscopic proprietary fasteners.
- Manufacturer-code archaeology and remotes teaching other remotes to blink.
- Elaborate activity wizards confused by a manually changed input.
- Features justified mainly by their appearance in marketing photographs.

### The Harmony Memorial Department

Logitech Harmony and other universal-remote pioneers tackled a fragmented industry. The Clonker keeps the useful ambition—one configurable controller for multiple devices—without reproducing the old configuration rituals. Network control is the current path; IR is not implemented.

**We want to watch the movie, not spend Saturday teaching the remote what a movie is.**

### Accessibility is good engineering

Large, distinct controls and operation in the dark benefit everyone. A remote should be usable by feel, without a scavenger hunt for the right button.

### Serviceability, Clonker style

Accessible internals, labeled wires, reasonable maintenance access, and room for experiments matter. An internal work light or elaborate latches remain concepts. If servicing the remote requires a flashlight in your teeth while chasing microscopic screws, we've failed.

The Clonker isn't retro. It isn't minimalist. It's **selectively maximalist**: maximum attention to what matters, minimum tolerance for what doesn't.

**Less sleek. More CLONK.**

---

## 3. Current controller, wiring, and GPIO assignments

### 3.1 Controller and terminal expansion

The active platform is the **Raspberry Pi Pico 2 W** running **CircuitPython 10.3.1**. The Pico Cowbell Terminal board provides terminal access to GPIO. A WAGO ground bus distributes common ground. Solid-core and pre-crimped wiring, insulated solder joints, and Dupont connections are used as appropriate.

**Mechanical retention matters.** During Chapter 7, a loose GP7 connection at the Cowbell prevented the third room-selector position from registering. Reseating the connection restored Room 3 detection without a firmware change. Check conductor retention and strain relief during assembly; a wire that looks connected may not be electrically reliable.

Earlier controller exploration, including the Unexpected Maker FeatherS3[D], is historical.

### 3.2 Current GPIO assignment table

This table follows [`pins.py`](../firmware/clonker/controls/pins.py). **Assigned** does not automatically mean application behavior is complete.

| Function | GPIO | Current status |
|---|---|---|
| Power Toggle momentary | GP2 | Operational; Den and Sunroom tested |
| Room selector LEFT / Room 1 | GP3 | Operational |
| Room selector MIDDLE / Room 2 | GP6 | Operational |
| Room selector RIGHT / Room 3 | GP7 | Operational; loose connection repaired |
| Volume encoder A/B | GP8 / GP9 | Operational |
| Volume encoder press / Mute | GP10 | Operational |
| Custom-action encoder A/B | GP11 / GP12 | Assigned; application rotation not integrated |
| Custom-action encoder press / Run | GP13 | Assigned and initialized as button; action execution not integrated |
| Navigation Up | GP14 | Operational |
| Navigation Down | GP15 | Operational |
| Navigation Left | GP16 | Operational |
| SERVICE / DEVICE boot switch | GP17 | Operational; `boot.py` |
| CONFIG / RUN switch | GP18 | Operational |
| Navigation Right | GP19 | Operational |
| Navigation Select / OK | GP20 | Press action mapped |
| Back | GP21 | Press action mapped |
| Home | GP22 | Press action mapped |
| Skip Back | GP26 (Cowbell A0) | Operational; held-key behavior tested |
| Play/Pause | GP27 (Cowbell A1) | Press action mapped |
| Skip Forward | GP28 (Cowbell A2) | Operational; held-key behavior tested |
| OLED I²C | GP4 / GP5 | Reserved; display not integrated |

All physical momentary buttons in the table have pin assignments and are initialized by `physical.py` when available. The six hold-capable buttons have explicit real-equipment verification; do not interpret the other button mappings as proof of exhaustive individual regression testing.

### 3.3 SERVICE (USB) / DEVICE — GP17

This maintained switch controls **filesystem write ownership**, not equipment power.

| Electrical state | Mode | Filesystem writer |
|---|---|---|
| Open / pulled HIGH | SERVICE (USB) | USB host |
| Grounded / LOW | DEVICE | Pico firmware |

`boot.py` reads the switch at startup. Changing ownership requires a full power cycle; Ctrl+D does not reproduce a cold boot. In SERVICE mode, firmware-side persistent saves are rejected because the application does not own filesystem writes.

### 3.4 CONFIG / RUN — GP18

| Electrical state | Mode | Management HTTP |
|---|---|---|
| Open / pulled HIGH | RUN | Off |
| Grounded / LOW | CONFIG | On, port 9090 |

The application responds to changes without rebooting. The command queue operates in either mode. SERVICE/DEVICE and CONFIG/RUN are independent. See [Operating Modes](OPERATING_MODES.md).

Chapter 7 scheduler adjustments improved Config-page responsiveness during physical input and network activity. This is cooperative scheduling, not a hard real-time guarantee.

### 3.5 Physical Power Toggle — GP2

The debounced momentary input dispatches the selected room's `power-toggle` action through the same queue used by the browser Test Remote. Den and Sunroom ON/OFF behavior was tested on real equipment, with independent per-room command-direction histories.

The toggle remembers the last **successfully issued command direction**, not the equipment's actual power state. HDMI-CEC or another remote can change equipment state independently.

The physical Power Toggle does **not** currently power the Pico itself, enter deep sleep, or implement wake-from-sleep.

---

## 4. Three-position physical room selector

The selector is a maintained rotary switch that changes **room context**, not an equipment action.

| Position | Wire | Grounded input | Room |
|---|---|---|---|
| LEFT | Yellow | GP3 | `room-1` — Den |
| MIDDLE | Green | GP6 | `room-2` — Sunroom |
| RIGHT | Blue | GP7 | `room-3` — Room 3 |

The common terminal connects to GND. Internal pull-ups mean the selected position grounds exactly one input. `selectors.py` ignores zero-active and multiple-active readings, retains the last valid room, and requires **50 ms** of stable input before accepting a change. `physical.py` logs `ROOM SELECTED: room-N` when selection changes.

The selector originally used GP3/GP4/GP5 during standalone tests. The operational mapping is **GP3/GP6/GP7**, preserving GP4/GP5 for I²C.

**Room 3 configuration, November 7:** The installed Clonker Config v4 JSON now includes `room-3`, named **Room 3**, with three blank device addresses, fourteen defined fundamental actions with blank paths, and an empty custom-action list. The browser editor can populate those fields without implementing an Add/Remove Room feature. Config v4 still permits one to three configured rooms; the room selector's three positions remain fixed.

An absent room is rejected by ordinary physical dispatch before queue admission. A configured room with blank command paths is intended to be inert. **Outstanding:** the explicit Roku keydown/keyup hold path needs a blank-command guard before all six hold buttons can be called harmless no-ops in an empty Room 3. Do not claim that safeguard is implemented yet.

The November 7 GP7 connection issue was a loose Cowbell wire, not a JSON or selector-software defect. After reseating it, Room 3 selection was restored.

---

## 5. Rotary encoders

### 5.1 Component choice

Both primary knobs use the **Bourns PEC11R-4215F-S0024** mechanical incremental encoder. The earlier **Grayhill 62A22-02-040C** volume-encoder plan was superseded; the Grayhill is reserved for another project. Their interfaces should not be assumed interchangeable.

| Control | Rotation | Shaft press | Status |
|---|---|---|---|
| Volume | `volume-up` / `volume-down` | `mute-toggle` | Operational, GP8/9/10 |
| Custom Actions | Intended: cycle room actions | Intended: run selection | GP11/12/13 assigned; application selection/run still pending |

Neither encoder is absolute-position hardware. Shaft angle does not represent a stored volume or custom-action index.

### 5.2 Operational volume encoder — GP8/GP9/GP10

`controls/encoders.py` reads quadrature transitions using internal pull-ups. Its decoder rejects invalid two-bit changes, accumulates valid transitions, and emits completed detent steps. `physical.py` maps positive steps to `volume-up` and negative steps to `volume-down`; the selected room determines the configured action and device adapter.

The reusable encoder supports direction reversal and configurable `steps_per_detent` (1, 2, or 4; current default 4). The physical preference is clockwise = volume up, counterclockwise = volume down.

The independent shaft pushbutton on GP10 uses the ordinary debounced `Button` driver and dispatches `mute-toggle`.

**Verified on real equipment:** Denon persistent-TCP volume in Den; Roku ECP held-volume in Sunroom; slow, moderate, and rapid detents; direction changes; and push-to-mute in both rooms. These tests do not prove lossless input capture under every possible blocking network condition.

### 5.3 Volume transport and responsiveness

The cooperative physical polling target is **1 ms**. Denon TCP reuses a connection and enforces at least **50 ms** between native volume commands without sleeping inside the queue. Roku held-volume starts a key hold on a detent, extends it locally for continued same-direction movement, and releases after inactivity or when reversing direction.

The encoder remains part of the shared dispatcher and Dumb Queue™. There is no second volume queue. Network operations remain synchronous and may temporarily delay GPIO polling. See [Firmware, Network & Clock](FIRMWARE_NETWORK.md).

### 5.4 Custom-action encoder — pending application integration

The second Bourns encoder is wired to GP11/GP12, and its shaft press to GP13. `pins.py` defines all three. `physical.py` initializes `ACTION_RUN` as a button when the pin is available, but it currently has no `BUTTON_ACTIONS` entry and therefore performs no action. The application does **not** yet initialize or poll a second rotary encoder instance.

The intended behavior remains: rotate through the selected room's named custom actions; press to execute the selection. Room changes, empty custom-action lists, and selection persistence require deliberate implementation and testing. Reuse the quadrature driver and shared action execution path rather than adding a new command pipeline.

### 5.5 Knobs and fit

The large volume knob candidate is **Kilo OEJNI-90-3-5**; the smaller action knob candidate is **Kilo OEJL-63-4-7**. Verify shaft profile, diameter, retention, panel clearance, and ergonomics on the actual assembly.

---

## 6. Navigation, playback, and physical button holds

### 6.1 Momentary button architecture

`controls/buttons.py` provides reusable active-low momentary input handling with internal pull-ups and **30 ms** default debounce. `physical.py` owns the button-to-fundamental-action mapping, while `actions.py`, `device_adapters.py`, and protocol modules own execution.

The current physical mappings include Power Toggle, Home, Back, Up, Down, Left, Right, Select, Volume Mute, Skip Back, Play/Pause, and Skip Forward. `ACTION_RUN` is initialized as an input but does not yet have application behavior.

### 6.2 Six operational Roku hold buttons

Chapter 7 added explicit **keydown on press / keyup on release** for:

| Physical button | Fundamental action | Roku ECP key |
|---|---|---|
| Up | `nav-up` | `Up` |
| Down | `nav-down` | `Down` |
| Left | `nav-left` | `Left` |
| Right | `nav-right` | `Right` |
| Skip Back | `skip-back` | `Rev` |
| Skip Forward | `skip-forward` | `Fwd` |

The physical handler captures the selected room, endpoint, and command at **press** time. The matching release uses that captured context, rather than whichever room happens to be selected later. Press and release are distinct queued events; a queue depth of one is normal when each event is dispatched and executed promptly.

`devices/roku.py` implements the physical-button hold independently of encoder-driven Roku volume holding. It includes a **30-second safety release** for an explicit physical-button hold. The safety limit is not the expected normal press duration.

**Observed Chapter 7 verification:** The six buttons were tested against the Sunroom Roku for press, sustained hold/repeat, and release. A logged Nav Down test showed individual keydown/keyup requests completing in approximately 105–121 ms. The defective Skip Back tactile switch was replaced before successful testing.

**Verification boundaries:** A selector change during a held button is designed to release against the original room, but that particular cross-room edge case still deserves a dedicated regression test. Rapid alternating inputs and long-running network failures are not exhaustively verified. Empty Room 3 hold commands require the no-op safeguard described in Section 4.

### 6.3 Other physical buttons

Home, Back, Select, Play/Pause, Power Toggle, and Mute use the ordinary press-only action path. Their GPIO mappings are present in firmware. The six explicit hold buttons are the focus of the completed Chapter 7 press/hold/release testing.

A possible 180-degree panel-orientation mode could swap navigation and skip directions while preserving physical button identities. **This is not implemented.** Encoder reversal is supported by the encoder driver, not by a general panel-orientation configuration.

---

## 7. Enclosure and faceplate

### 7.1 Mechanical direction

The prototype uses a **black semi-rigid zippered electronics case** and **pre-cut aluminum faceplate**. The documented mounting approach includes a rectangular opening beneath the plate, distributed mounting bolts, underside washers/star washers/nuts, and accessible internals. Protective film can remain during fitting and drilling.

An early faceplate target was approximately **4.5 × 6.5 inches**, with **1.5–2 inches** of enclosure depth. These are design targets, not guaranteed final machining dimensions.

### 7.2 Control arrangement — conceptual, not a drilling template

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
             CONFIG/RUN: MAINTAINED SWITCH
             SERVICE/DEVICE: BOOT SWITCH
```

The volume and action knobs occupy the upper positions. Back and Home should be distinguishable by touch; Home has been considered slightly higher. The room selector is intended near the right side and the guarded power control near the lower right. A speaker may fit beneath the lid.

Before further drilling, verify component dimensions, shaft clearance, guard movement, OLED viewing angle, wiring bend radius, fastener footprints, and access to the Pico USB port. The conceptual diagram does not override the actual faceplate.

### 7.3 Wiring and strain relief

Use insulated solder joints, heat-shrink tubing, sensible wire colors, and cable ties or anchors that transfer force away from component lugs and fragile connectors. Leave service loops for lid movement. Check Cowbell terminal engagement after moving the case: the Room 3 GP7 incident demonstrated the value of this check.

---

## 8. Guarded power and future SYSTEM MASTER

The current GP2 Power Toggle issues the configured equipment power action. It does **not** switch the Pico supply or enter deep sleep.

A broader **SYSTEM MASTER** idea could eventually combine a guarded control, battery wake, startup, and equipment commands. The **FILN 19 mm red-ring momentary** and red Start Engine-style guard have been considered and bench-tested as mechanical/electrical candidates. Final integration is not established by that testing.

### 8.1 Deep sleep — design only

A possible sequence is: sleeping Pico → intentional wake → Wi-Fi/application initialization → interpret the initiating control once → dispatch. This needs verification of RP2350/CircuitPython wake support, GPIO restrictions, startup latency, and duplicate-event prevention. A full reboot after wake is acceptable as a design choice but is not yet implemented.

### 8.2 Rechargeable power — open

Battery selection, charging, protection, regulation, runtime, safe access, and power isolation remain to be designed and measured. Do not connect unknown battery voltage or a 12/24 V switch-illumination supply directly to a Pico GPIO. Switch contacts and illumination circuits are separate electrical functions.

---

## 9. OLED, audio, and feedback

### 9.1 Display

A small **SSD1306 64×32, approximately 0.49-inch OLED** was selected for experimentation; a larger approximately **1.3-inch** option has also been considered. Intended information includes room, selected custom action, mode, and short status messages.

**GP4/GP5 are reserved for I²C; the OLED is not yet initialized or driven by the application.** Display failure should not disable basic remote operation. Mounting, readability, I²C addressing, and power draw still need testing. Bivar 907-3MM nylon spacers are among the mounting supplies.

### 9.2 Audible CLONK

Candidate components include an **Adafruit MAX98357A I²S amplifier**, **Adafruit PS1240 piezo**, and **MECCANIXITY 23 mm 8 Ω / 1 W speakers**. The objective is optional audible feedback, not a dependency for dispatch. No audio subsystem is currently implemented.

---

## 10. Parts and procurement register

This is a **design and purchase-history register**, not a verified warehouse inventory. Ordered, received, installed, and operational are different states.

For exact manufacturer part numbers, component identification, and actual drilled/test-fitted mounting-hole sizes, see the [Hardware Parts List](HARDWARE_PARTS_LIST.md). The register below tracks design decisions and implementation status rather than duplicating the detailed parts list.

| Item | Identifying part / type | Purpose | Status |
|---|---|---|---|
| Controller | Raspberry Pi Pico 2 W | Firmware | Operational |
| Earlier controller | Unexpected Maker FeatherS3[D] | Earlier platform | Historical |
| Terminal expansion | Pico Cowbell Terminal | GPIO access | In use |
| Ground bus | WAGO lever connectors | Shared ground | In use |
| SERVICE/DEVICE switch | Maintained toggle | GP17 | Operational |
| CONFIG/RUN switch | Maintained toggle | GP18 | Operational |
| Power Toggle | Momentary button | GP2 | Operational |
| Room selector | Three-position rotary | GP3/6/7 | Operational |
| Volume encoder | Bourns PEC11R-4215F-S0024 | Volume / Mute | Operational GP8/9/10 |
| Action encoder | Bourns PEC11R-4215F-S0024 | Custom actions | Wired/assigned GP11/12/13; software behavior pending |
| Former encoder | Grayhill 62A22-02-040C | Former volume candidate | Superseded |
| Large knob | Kilo OEJNI-90-3-5 | Volume | Fit to verify |
| Small knob | Kilo OEJL-63-4-7 | Custom actions | Fit to verify |
| Navigation buttons | Tactile momentary switches; Adafruit #3347 among candidates | Navigation / shortcuts | Wired/assigned; six hold buttons verified |
| Skip Back replacement | Tactile momentary switch | Playback | Replaced defective switch; operational |
| Guarded momentary | FILN 19 mm red-ring | SYSTEM MASTER concept | Bench contact test; final use pending |
| Guard | Red Start Engine-style cover | Power control | Candidate |
| Slide switches | uxcell three-position DPDT assortment | Earlier selector experiments | Historical candidate |
| Small OLED | SSD1306 64×32 | Status | Not integrated |
| Larger OLED | Approx. 1.3-inch module | Status | Mounting evaluation |
| OLED spacers | Bivar 907-3MM | Mounting | Obtained/ordered |
| Piezo | Adafruit PS1240 | Sound | Ordered candidate |
| I²S amplifier | Adafruit MAX98357A | Sound | Ordered candidate |
| Speakers | MECCANIXITY 23 mm, 8 Ω, 1 W | Sound | Ordered candidate |
| Faceplate | Pre-cut aluminum | Controls | Prototype mounted/fitted |
| Enclosure | Black semi-rigid zippered case | Housing | Prototype |
| Breadboard | Adafruit 830-tie PID 239 | Early testing | Historical use |
| Jumper wires | Dupont assortment | Wiring | In use |
| Solid wire | 22 AWG assortment | Signal wiring | In use |
| Test leads | WG-026 alligator leads | Bench work | Ordered |
| Resistors | ALLECIN assortment | Experiments | Ordered |
| LEDs | 3 mm / 5 mm assortment | Indicators | Ordered |

For newly integrated parts, record exact model, pinout, voltage, dimensions, mounting, received/installed/tested status, and GPIO assignment. Do not promote an unverified candidate to operational merely because it was purchased.

---

## 11. Electrical and firmware boundaries

### 11.1 Active-low inputs

Momentary buttons and room-selector contacts use internal pull-ups and connect the selected input to **GND** when active. Confirm switch contacts with a meter. Encoder A/B/common contacts are distinct from the shaft pushbutton. Disconnect Pico power before rewiring; verify polarity, continuity, shorts, and retention before powering up.

### 11.2 Module responsibilities

| Module | Responsibility |
|---|---|
| `controls/pins.py` | Named GPIO assignments |
| `controls/buttons.py` | Debounced momentary pressed/released events |
| `controls/switches.py` | CONFIG/RUN state and override |
| `controls/selectors.py` | Debounced room context |
| `controls/encoders.py` | Reusable quadrature decoder; used by volume |
| `controls/physical.py` | Initialize/poll controls, map events, capture hold context, dispatch |
| `actions.py` | Shared Dumb Queue™, fundamental and hold admission/execution |
| `device_adapters.py` | Select recognized specialized command execution |
| `devices/denon.py` | Persistent TCP volume and pacing |
| `devices/roku.py` | Encoder held-volume and explicit physical-button key holds |

GPIO code remains protocol-agnostic. A physical hold is not a second command queue; press/release enter the shared queue and are executed by the Roku adapter. Custom-action steps continue to use the shared execution path.

### 11.3 Cooperative timing and limits

The firmware targets frequent physical polling (approximately **1 ms** when the cooperative loop is available). Button debounce is **30 ms**, room-selector debounce **50 ms**, and Denon TCP volume pacing at least **50 ms**. Roku physical-button holds have a **30-second** safety limit. These are not hard real-time guarantees: blocking network operations can delay input sampling or execution.

The queue is bounded and cancels pending work on execution failure. An HTTP acknowledgment is not proof of the equipment's resulting state. Config Mode scheduler adjustments improve browser responsiveness but do not remove synchronous network constraints.

---

## 12. Verification timeline and current status

| Date / phase | Milestone | Result |
|---|---|---|
| Chapter 5 | Optional GPIO initialization, debounce, initial controls | Passed |
| October 28–29 | GP17 SERVICE/DEVICE; GP18 CONFIG/RUN | Passed |
| October 31 | Selector standalone test on GP3/4/5 | Passed; historical wiring |
| November 2 | Selector integrated, reassigned GP3/6/7 | Passed |
| November 2 | Room-aware Power Toggle, Den and Sunroom | Passed on real equipment |
| November 3 / Chapter 6 | Bourns volume encoder GP8/9 and Mute GP10 | Passed |
| November 3 | Persistent Denon TCP, Roku held-volume, mixed-room dispatch | Passed |
| Chapter 7 | Navigation and playback button wiring/mapping | Integrated |
| Chapter 7 | Config Mode scheduler responsiveness tuning | Browser responsiveness improved in observed testing |
| Chapter 7 | Explicit Roku keydown/keyup for Skip Back/Forward | Passed on real equipment |
| Chapter 7 | Explicit Roku keydown/keyup for Up/Down/Left/Right | Passed on real equipment |
| Chapter 7 | Six physical hold buttons: press, sustained hold, release | Passed |
| Chapter 7 | Defective Skip Back switch replacement | Replaced; working |
| November 7 | Installed Config v4 JSON extended to Room 3 | Room 3 present; blank commands |
| November 7 | Room 3 selector failed to register | Loose GP7 Cowbell wire corrected |

**Not yet established:** exhaustive long-uptime behavior; every rapid-input/network-failure edge case; cross-room release regression; blank-command safety for physical hold buttons in Room 3; custom-action encoder application behavior; OLED/audio; final enclosure durability; battery operation; and sleep/wake.

Keep detailed experiments and dated observations in [Development History](DEVELOPMENT_HISTORY.md), not in duplicate technical narratives here.

---

## 13. Next physical development work

1. Add a blank-command no-op guard for explicit physical hold buttons so Room 3 can safely remain unconfigured.
2. Test changing the room selector while a held button is down; verify release targets the original room and endpoint.
3. Complete custom-action encoder rotation, room-specific selection, and push-to-run behavior.
4. Regress Home, Back, Select, Play/Pause, volume, and rapid mixed-input sequences.
5. Integrate the OLED independently; evaluate optional sound feedback without making it mandatory.
6. Finalize wiring retention, strain relief, guarded power, faceplate, and enclosure.
7. Design and measure battery, charging, sleep, and wake before claiming SYSTEM MASTER is an ignition system.
8. Perform longer real-equipment tests with network interruption, receiver restarts, and concurrent browser/physical use.

**One meaningful change at a time. One shared execution path.**

---

## 14. Related documents

- [Architecture](ARCHITECTURE.md) — system boundaries, dispatcher, queue, adapter selection.
- [Configuration & Recovery](CONFIGURATION.md) — Config v4 schema, persistence, revision protection.
- [Firmware, Network & Clock](FIRMWARE_NETWORK.md) — scheduler, Roku/Denon transports, diagnostics, tests.
- [Operating Modes](OPERATING_MODES.md) — GP17 and GP18 behavior.
- [Development & Deployment](DEVELOPMENT.md) — iPad-first workflow, Pico deployment, tests.
- [Development History](DEVELOPMENT_HISTORY.md) — dated decisions, experiments, and evidence.

---

**THE CLONKER 10000**  
*Less sleek. More CLONK.*  
**CLONK! ⚡🔩**
