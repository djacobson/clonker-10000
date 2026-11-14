# THE CLONKER 10000
## Hardware Design

**Updated:** November 9, 2026  
**Controller:** Raspberry Pi Pico 2 W (RP2350), CircuitPython 10.3.1  
**Baseline:** Chapter 8 — assembled physical controls, operational room selector and both Bourns encoders, room-aware OLED feedback, persistent Custom Action execution acknowledgment, and physical polling optimizations    
**Source of GPIO truth:** [`firmware/clonker/controls/pins.py`](../firmware/clonker/controls/pins.py)

> A gloriously overengineered, tactile Wi-Fi home-theater remote. Real knobs, real buttons, questionable restraint, and absolutely no desire to become another touchscreen.

---

## 1. Purpose and evidence conventions

This document describes the Clonker's physical design, assembled hardware, GPIO assignments, control behavior, electrical boundaries, and remaining hardware development.

The Chapter 7 physical assembly is complete: controls are mounted, soldered, wired, secured, strain-relieved, and connected through the Pico Cowbell Terminal board.

That does not imply battery operation, sleep/wake behavior, audible feedback, or final software reliability testing are complete.

Status terminology:

- **Operational:** Integrated into running firmware and exercised in the application.
- **Integrated:** Implemented in the application; additional uses or testing may remain.
- **Bench verified:** Tested independently, without necessarily completing application integration.
- **Planned:** Not yet implemented.
- **Historical:** Earlier design or component retained for context.

The firmware is authoritative for GPIO assignments and implemented behavior.

Related responsibilities:

- [Configuration](CONFIGURATION.md) — room/device configuration and custom actions.
- [Architecture](ARCHITECTURE.md) — dispatcher, shared queue, adapters.
- [Firmware, Network & Clock](FIRMWARE_NETWORK.md) — transport behavior and performance.
- [Development History](DEVELOPMENT_HISTORY.md) — milestones, experiments, and decisions.

**Hardware detects events. Physical coordination maps intent. The shared Dumb Queue™ executes commands.**

GPIO drivers do not contain Roku or Denon command strings.

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

Logitech Harmony and other universal-remote pioneers tackled a fragmented industry. The Clonker keeps the useful ambition—one configurable controller for multiple devices—without reproducing the old configuration rituals.

Network control is the current path; IR is not implemented.

**We want to watch the movie, not spend Saturday teaching the remote what a movie is.**

### Accessibility is good engineering

Large, distinct controls and operation in the dark benefit everyone. A remote should be usable by feel, without a scavenger hunt for the right button.

### Serviceability, Clonker style

Accessible internals, labeled wires, reasonable maintenance access, and room for experiments matter.

An internal work light or elaborate latches remain concepts. If servicing the remote requires a flashlight in your teeth while chasing microscopic screws, we've failed.

The Clonker isn't retro. It isn't minimalist. It's **selectively maximalist**: maximum attention to what matters, minimum tolerance for what doesn't.

**Less sleek. More CLONK.**

---

## 3. Physical assembly and controller

### 3.1 Chapter 7 assembly milestone

By the end of Chapter 7, the physical controls had progressed beyond breadboard and standalone-component testing into an assembled controller.

Completed physical work includes:

- Mounting the control hardware.
- Soldering the required control connections.
- Connecting both Bourns rotary encoders and their pushbuttons.
- Connecting the three-position room selector.
- Connecting the navigation and playback buttons.
- Connecting the Power Toggle.
- Connecting the SERVICE/DEVICE and CONFIG/RUN switches.
- Installing and connecting the OLED.
- Securing the wiring and providing strain relief.
- Connecting the GPIO wiring through the Pico Cowbell Terminal board.
- Establishing the shared WAGO ground distribution.

The physical control assembly is complete. Subsequent work concerns software behavior, additional feedback, power management, reliability, and future enhancements.

The assembly remains serviceable and may be modified as the project evolves.

### 3.2 Controller and electrical distribution

The active controller is the **Raspberry Pi Pico 2 W**, running **CircuitPython 10.3.1**.

The Pico Cowbell Terminal board provides accessible GPIO terminals.

The assembly uses:

- WAGO connectors for common ground distribution.
- Solid-core and pre-crimped wiring as appropriate.
- Soldered and insulated component connections.
- Secured wiring with strain relief.
- GPIO inputs using internal pull-ups.

The earlier Unexpected Maker FeatherS3[D] controller exploration is historical.

### 3.3 Current GPIO assignments

The following table reflects `controls/pins.py`.

| Function | GPIO | Status |
|---|---|---|
| Power Toggle | GP2 | Operational |
| Room selector — Room 1 | GP3 | Operational |
| Room selector — Room 2 | GP6 | Operational |
| Room selector — Room 3 | GP7 | Operational |
| Volume encoder A/B | GP8 / GP9 | Operational |
| Volume encoder push / Mute | GP10 | Operational |
| Custom-action encoder A/B | GP11 / GP12 | Operational |
| Custom-action encoder push / Run | GP13 | Operational |
| Navigation Up | GP14 | Integrated |
| Navigation Down | GP15 | Integrated |
| Navigation Left | GP16 | Integrated |
| SERVICE/DEVICE boot switch | GP17 | Operational |
| CONFIG/RUN switch | GP18 | Operational |
| Navigation Right | GP19 | Integrated |
| Select / OK | GP20 | Integrated |
| Back | GP21 | Integrated |
| Home | GP22 | Integrated |
| Skip Back | GP26 / Cowbell A0 | Operational |
| Play/Pause | GP27 / Cowbell A1 | Integrated |
| Skip Forward | GP28 / Cowbell A2 | Operational |
| OLED SDA | GP4 | Integrated |
| OLED SCL | GP5 | Integrated |

All assigned physical controls are connected as part of the completed Chapter 7 assembly.

Individual regression-test coverage varies by control. Physical assembly completion should not be confused with exhaustive software verification.

---

## 4. Operating-mode switches

### 4.1 SERVICE (USB) / DEVICE — GP17

This maintained switch determines filesystem write ownership at boot.

| Electrical state | Mode | Filesystem writer |
|---|---|---|
| Open / pulled HIGH | SERVICE (USB) | USB host |
| Grounded / LOW | DEVICE | Pico firmware |

`boot.py` reads the switch during startup.

Changing filesystem ownership requires a full power cycle. A CircuitPython soft reboot does not necessarily reproduce a cold boot.

Firmware-side persistent configuration saves are rejected when the application does not own filesystem writes.

### 4.2 CONFIG / RUN — GP18

| Electrical state | Mode | Management HTTP |
|---|---|---|
| Open / pulled HIGH | RUN | Disabled |
| Grounded / LOW | CONFIG | Enabled, port 9090 |

The application responds to CONFIG/RUN changes without rebooting.

The command queue remains available in either mode.

SERVICE/DEVICE and CONFIG/RUN are independent controls.

Chapter 7 improved browser responsiveness in CONFIG mode through cooperative scheduler adjustments. This does not make network operations asynchronous.

See [Operating Modes](OPERATING_MODES.md).

---

## 5. Physical Power Toggle

The Power Toggle is a momentary input on GP2.

It dispatches the selected room's `power-toggle` fundamental action through the same shared execution architecture used by the browser Test Remote.

Room-aware ON/OFF behavior has been tested with Den and Sunroom equipment.

The software remembers the last successfully issued command direction, not the actual state of external equipment.

HDMI-CEC, another remote, or direct equipment operation can change that state independently.

**Important distinction:** The Power Toggle currently controls home-theater equipment. It does not power the Pico on or off, enter deep sleep, or wake the controller.

Battery-powered operation was demonstrated in Chapter 9. Sleep/wake integration remains future work.

---

## 6. Three-position room selector

The mounted selector changes the Clonker's active room context.

| Position | Signal wire | GPIO | Room |
|---|---|---|---|
| LEFT | Yellow | GP3 | `room-1` — Den |
| MIDDLE | Green | GP6 | `room-2` — Sunroom |
| RIGHT | Blue | GP7 | `room-3` — Room 3 |

The selector common connects to ground.

The selected contact grounds one GPIO input. Internal pull-ups keep inactive inputs HIGH.

`controls/selectors.py`:

- Reads the three selector inputs.
- Rejects invalid zero-active or multiple-active states.
- Retains the previous valid selection during invalid transitions.
- Requires approximately 50 ms of stable input before accepting a room change.

The operational GPIO assignment is GP3/GP6/GP7, preserving GP4/GP5 for the OLED I²C bus.

### 6.1 Room 3 placeholder

The installed Config v4 configuration includes `room-3` as a placeholder.

It has:

- Three device slots with blank addresses.
- Fourteen defined fundamental actions with blank command paths.
- An empty custom-action list.

The browser configuration editor can populate these fields.

The room selector has three fixed positions; this does not require an Add/Remove Room interface.

Ordinary fundamental actions with blank mappings are intended to be harmless no-ops.

**Outstanding verification:** Explicit physical Roku held-button dispatch requires additional blank-command safety verification for Room 3.

---

## 7. Rotary encoders

### 7.1 Hardware

Both primary rotary controls use the **Bourns PEC11R-4215F-S0024** mechanical incremental encoder.

The earlier Grayhill 62A22-02-040C volume encoder was superseded.

| Control | Rotation | Shaft press | GPIO |
|---|---|---|---|
| Volume | Volume Up / Down | Mute | GP8/9/10 |
| Custom Actions | Cycle room custom actions | Run selected action | GP11/12/13 |

Both encoders are operational in the application.

Neither is an absolute-position encoder. The physical shaft position does not directly represent a volume level or action index.

### 7.2 Reusable encoder driver

`controls/encoders.py` provides the quadrature decoder.

It:

- Uses GPIO pull-ups.
- Processes quadrature transitions.
- Rejects invalid two-bit transitions.
- Accumulates valid transitions.
- Reports completed detent steps.
- Supports configurable direction reversal.
- Supports configurable steps per detent.

The current default is four transitions per detent.

The physical coordinator owns the meaning of the resulting steps.

### 7.3 Volume encoder

Clockwise rotation means Volume Up; counterclockwise means Volume Down.

The encoder pushbutton dispatches `mute-toggle`.

The selected room determines the target equipment and configured action.

Operational testing includes:

- Denon persistent-TCP volume control in Den.
- Roku ECP held-volume behavior in Sunroom.
- Slow and moderate detent input.
- Rapid rotation and direction changes.
- Push-to-mute operation.

Rapid input reliability remains subject to cooperative polling and synchronous network delays.

### 7.4 Custom-action encoder

The second Bourns encoder is integrated into `controls/physical.py`.

Its implemented behavior:

1. Read the custom-action list for the currently selected room.
2. Rotate to move forward or backward through that ordered list.
3. Wrap the selection index around the available actions.
4. Display the selected action name on the OLED.
5. Press the encoder shaft to dispatch the selected custom action.
6. Reset selection when the active room changes.
7. Handle an empty action list without attempting execution.

The OLED displays `No customs` when the selected room has no custom actions.

Execution reuses the existing action-dispatch architecture. No separate custom-action execution pipeline was introduced.

**Chapter 8 status:** Custom Action selection, shaft-press execution, OLED selection feedback, and persistent inverted execution acknowledgment are operational and hardware verified. Rotation clears previous acknowledgments, including when the displayed action name remains unchanged.

### 7.5 Knobs

The hardware design includes Kilo metal knobs:

| Control | Component |
|---|---|
| Volume | Kilo OEJNI-90-3-5 |
| Custom Actions | Kilo OEJL-63-4-7 |

The earlier Grayhill encoder remains historical rather than part of the active assembly.

---

## 8. Navigation and playback buttons

### 8.1 Button architecture

`controls/buttons.py` provides reusable active-low momentary-button handling with internal pull-ups and a default debounce interval of approximately 30 ms.

`controls/physical.py` maps physical button events to room-aware actions.

The existing shared dispatcher and queue handle execution.

The GPIO driver does not need to know which Roku or Denon command implements an action.

### 8.2 Physical action mappings

| Physical control | Fundamental action |
|---|---|
| Up | `nav-up` |
| Down | `nav-down` |
| Left | `nav-left` |
| Right | `nav-right` |
| Select / OK | `nav-select` |
| Back | `nav-back` |
| Home | `nav-home` |
| Play/Pause | `play-pause` |
| Skip Back | `skip-back` |
| Skip Forward | `skip-forward` |
| Volume encoder press | `mute-toggle` |
| Power Toggle | `power-toggle` |

The custom-action encoder press is handled separately because it executes the currently selected named custom action.

### 8.3 Six Roku hold-capable buttons

Chapter 7 introduced explicit Roku keydown on physical press and keyup on release.

| Physical button | Roku ECP key |
|---|---|
| Up | `Up` |
| Down | `Down` |
| Left | `Left` |
| Right | `Right` |
| Skip Back | `Rev` |
| Skip Forward | `Fwd` |

The handler captures the selected room and command context when the button is pressed.

The release uses the captured context rather than simply consulting the room selector again.

Press and release are separate events executed through the shared queue.

The Roku adapter includes a 30-second safety-release limit for explicit physical-button holds.

This is a fallback, not the expected duration of an ordinary press.

### 8.4 Verification

The six hold-capable controls were exercised against the Sunroom Roku for:

- Short presses.
- Sustained holds.
- Repeated navigation or playback behavior.
- Release.

Observed individual Roku keydown/keyup network requests were approximately 105–121 ms in one documented test.

The following still merit dedicated regression testing:

- Changing rooms during a held button.
- Rapid alternating inputs.
- Network interruptions during holds.
- Blank command mappings in Room 3.
- Long-running mixed physical and browser activity.

### 8.5 Other physical controls

Home, Back, Select, Play/Pause, Power Toggle, and Mute use ordinary press-based dispatch.

These are integrated into the physical application.

A possible future 180-degree control-orientation mode could reverse navigation or playback direction mappings. This is not implemented.

---

## 9. OLED display and visual feedback

### 9.1 Current integrated display

The active display driver is:

`firmware/clonker/display/oled.py`

It implements a **128×64 SH1106 OLED** over I²C.

| Property | Current implementation |
|---|---|
| Controller | SH1106 |
| Resolution | 128×64 |
| I²C address | `0x3C` |
| SDA | GP4 |
| SCL | GP5 |
| Bus speed | 400 kHz |
| Minimum refresh interval | 100 ms |
| Idle display-off | 15 seconds |
| Text layouts | Centered single line or optional two-line layout |
| Hardware inversion | Supported and operational |

Earlier references to a 64×32 SSD1306 are historical. The integrated display is the 128×64 SH1106.

### 9.2 Display architecture

The OLED uses an event-driven design to minimize work in the physical control path.

`show_text(message, second_line=None, reset_ack=False)` records a display request without performing I²C communication.

`poll()` performs the actual display operations.

The driver supports:

- Single-line text using the enlarged font.
- Optional two-line text with a smaller heading and enlarged second line.
- Partial SH1106 page updates.
- A 100 ms minimum interval between framebuffer refreshes.
- Automatic display-off after 15 seconds without display activity.
- Hardware inversion without framebuffer redraw.
- Explicit acknowledgment reset.
- Refresh-count diagnostics.
- Display initialization and cleanup.

Identical text requests do not trigger redundant framebuffer updates while the display is awake.

A repeated `show_text()` call extends the idle timeout, even when no redraw is required.

The driver does not require a third-party display library.

### 9.3 Room-selector feedback

Chapter 8 integrated the physical room selector with the OLED.

Changing the selector displays:

- A small heading identifying the room number.
- The configured room name in the enlarged font.

For example:

    ROOM 2
    SUNROOM

An unconfigured selector position displays:

    ROOM 3
    UNASSIGNED

The display request occurs only when the debounced room selection changes. It does not require continuous configuration lookups or display updates.

Room selection resets the Custom Action selection index but does not execute an action.

### 9.4 Custom Action selection and execution feedback

The Custom Action encoder provides two distinct interactions.

**Rotation — selection**

- Cycles through the selected room's Custom Actions.
- Displays the selected action name normally.
- Displays `No customs` when the room has no Custom Actions.
- Clears any previous execution acknowledgment.

**Shaft press — execution**

- Dispatches the currently selected Custom Action through the existing action system.
- Requests the action name on the OLED.
- Requests hardware inversion after successful dispatch.
- Leaves the display inverted until another display message or idle timeout.

Hardware inversion uses the SH1106 commands:

- `0xA7` — inverted display.
- `0xA6` — normal display.

Inverted mode displays dark text against an illuminated background.

The acknowledgment is persistent rather than a timed flash. It requires no additional timer or blocking delay.

The OLED can wake from its idle state to display an execution acknowledgment.

Repeated execution acknowledgments do not toggle the display back to normal.

Selection and execution remain separate concepts:

- **Normal display:** Selected action.
- **Inverted display:** Execution acknowledgment.

### 9.5 Acknowledgment reset and efficiency

The driver exposes:

`oled.acknowledge()`

This requests hardware inversion without immediately performing I²C.

The optional `reset_ack=True` argument to `show_text()` explicitly clears an acknowledgment, even if the requested text is identical to the current text.

For example:

    oled.show_text("MOVIE", reset_ack=True)

This restores normal display mode without requiring a framebuffer redraw when `MOVIE` is already displayed.

That distinction handles cases where the user rotates the Custom Action encoder but returns to the same displayed action name.

The driver tracks requested and applied inversion states. `poll()` sends an inversion command only when those states differ.

Idle timeout restores normal display mode before switching off the panel.

The shared action queue does not wait for OLED operations.

### 9.6 Hardware verification

Chapter 8 hardware testing confirmed:

| Test | Result |
|---|---|
| Two-line room display | PASS |
| Return to single-line display without ghost text | PASS |
| Room selector positions, including unconfigured room | PASS |
| Automatic OLED idle-off | PASS |
| Hardware inversion | PASS |
| Restore normal mode | PASS |
| Reset acknowledgment with identical text | PASS |
| Reset without redundant framebuffer refresh | PASS |
| Custom Action shaft press and OLED acknowledgment | PASS |

The no-redraw test confirmed that the successful framebuffer refresh count remained at one after inversion and restoration.

### 9.7 Future display work

Potential enhancements include:

- CONFIG/RUN indication where useful.
- Network and battery status.
- Additional application status messages.
- Larger custom icons for expressive or status feedback.
- Further user-interface edge-case testing.

All primary physical controls now provide OLED feedback, including navigation, Home, Back, Select, playback, Power, volume, mute, room selection, and Custom Actions. These messages were verified on the assembled controller.

Not every button requires inversion. Persistent inversion is currently reserved for the two-stage Custom Action selection/execution interaction.

The OLED is a feedback component, not a requirement for command execution.

---

## 10. Enclosure and faceplate

### 10.1 Mechanical construction

The Clonker uses a black semi-rigid zippered electronics enclosure and aluminum faceplate.

The faceplate provides the mounting surface for the tactile controls.

The completed Chapter 7 assembly includes mounted controls, secured wiring, and strain relief.

The enclosure is serviceable, allowing access to the Pico, Cowbell, wiring, and control hardware.

Earlier dimensional targets were approximately 4.5 × 6.5 inches for the faceplate and 1.5–2 inches of enclosure depth. These were design targets rather than authoritative final measurements.

### 10.2 Control arrangement

The established design places:

- Volume encoder toward the upper left.
- Custom-action encoder toward the upper right.
- Back and Home controls above the navigation cluster.
- Five-button navigation cluster near the center.
- OLED below the navigation cluster.
- Playback controls near the OLED.
- Guarded Power Toggle toward the lower right.
- Three-position room selector accessible on the assembly.
- Maintained operating-mode switches in accessible positions.

The exact mounted arrangement and physical assembly take precedence over earlier conceptual diagrams.

### 10.3 Wiring and serviceability

The physical wiring is complete, secured, and strain-relieved.

Future changes should preserve:

- Insulated connections.
- Mechanical retention.
- Clear access for service.
- Protection from sharp panel edges.
- Adequate clearance around moving controls.
- Reliable Cowbell terminal connections.
- Safe separation of future battery and charging circuitry.

Routine assembly repairs are not maintained as individual milestones in this hardware reference.

---

## 11. Guarded power and battery operation

### 11.1 Equipment power versus controller power

The guarded Power Toggle is a momentary input on GP2.

It dispatches the selected room's `power-toggle` fundamental action. It does not electrically switch power to the Pico, control battery charging, or currently initiate sleep/wake.

The broader **SYSTEM MASTER** concept remains a future power-management design.

### 11.2 Battery power architecture — Chapter 9

The Clonker's portable power system uses a DFRobot DFR0969 module containing two rechargeable 18650 lithium-ion cells.

The initial bench-tested power path is:

    Two 18650 cells
          |
          v
    DFRobot DFR0969
    Battery / power module
          |
          | USB-A, regulated ~5 V
          v
    Inline USB power tester
          |
          | USB-A to Micro-USB cable
          v
    Raspberry Pi Pico 2 W
          |
          v
    Clonker application and controls

This arrangement powers the existing controller through its normal USB power input without changing the GPIO wiring or application architecture.

The module's HOLD/NORMAL selector was placed in HOLD during battery testing.

The module remains external to the Clonker enclosure while its operation and physical installation are evaluated.

### 11.3 Initial electrical measurements

Bench testing on November 12, 2026 established successful standalone battery operation.

| Measurement | Observed result |
|---|---|
| Individual cell voltage before testing | Approximately 3.560 V |
| Regulated USB output | Approximately 5.12 V |
| Typical idle USB current | Approximately 33–37 mA |
| Typical idle USB power | Approximately 0.17–0.19 W |
| CircuitPython and application startup | Approximately 10–12 seconds |

The measured current is the USB load seen by the inline tester, not the current drawn directly from the 18650 cells.

Battery-side conversion losses, usable capacity, and total runtime have not yet been characterized.

Physical controls, Wi-Fi application operation, and OLED feedback were successfully exercised during battery-powered testing.

### 11.4 Application startup feedback

The OLED now displays a brief READY message after the Clonker application initializes.

The message clears automatically.

This provides visual confirmation that the controller has completed startup, particularly when operating from battery power without an attached computer or serial console.

The observed startup time is approximately 10–12 seconds from power application to the READY indication.

The READY message confirms application initialization, not necessarily successful communication with every configured external device.

### 11.5 Remaining battery integration work

- Complete extended runtime testing.
- Measure discharge behavior and practical operating life.
- Verify charging and power-path behavior.
- Confirm battery cell specifications and compatibility.
- Determine permanent battery module placement.
- Provide appropriate access to charging and power controls.
- Secure internal USB wiring and provide strain relief.
- Evaluate low-battery indication and shutdown behavior.

### 11.6 Sleep/wake — design only

A possible future sequence is:

1. Controller enters a supported low-power state.
2. User operates an intentional wake control.
3. Pico resumes or reboots.
4. Firmware initializes the required subsystems.
5. The initiating action is interpreted safely.
6. Normal operation resumes.

RP2350 and CircuitPython wake capabilities, GPIO limitations, and actual low-power consumption require testing before implementation.

A reboot-based wake sequence remains an acceptable design option.

### 11.7 Electrical safety

Do not connect raw lithium-ion cell voltage directly to Pico GPIO.

Use the battery module's regulated output and verify voltage, polarity, current capacity, and charging behavior before permanent installation.

Any switch illumination circuit must be evaluated separately from its mechanical contacts.

Battery protection, charging, and mechanical mounting remain important parts of the final electrical design.

---

## 12. Audible CLONK and additional feedback

Audible feedback remains planned.

Candidate hardware includes:

| Component | Intended role |
|---|---|
| Adafruit MAX98357A | I²S audio amplifier |
| Adafruit PS1240 | Piezo sounder |
| MECCANIXITY 23 mm, 8 Ω / 1 W | Small speaker |

Potential uses include tactile-event confirmation, short status tones, and the occasional appropriately theatrical CLONK.

Audio should remain optional and must not become a dependency for command dispatch.

No production audio subsystem is currently implemented.

---

## 13. Parts and implementation register

This table describes the current design and major components. For detailed part numbers, purchasing history, and dimensions, see [Hardware Parts List](HARDWARE_PARTS_LIST.md).

| Component | Purpose | Current status |
|---|---|---|
| Raspberry Pi Pico 2 W | Controller | Operational |
| Pico Cowbell Terminal | GPIO terminal expansion | Installed |
| WAGO connectors | Common ground distribution | Installed |
| SERVICE/DEVICE switch | Filesystem ownership | Operational |
| CONFIG/RUN switch | Application mode | Operational |
| Power Toggle | Equipment power action | Operational |
| Three-position room selector | Room selection | Operational |
| Bourns volume encoder | Volume and Mute | Operational |
| Bourns custom-action encoder | Selection and execution | Operational |
| Navigation controls | Directional navigation and OK | Integrated |
| Back and Home | Navigation shortcuts | Integrated |
| Playback controls | Play/Pause and Skip | Integrated |
| SH1106 OLED, 128×64 | Visual feedback | Initially integrated |
| Aluminum faceplate | Physical control mounting | Assembled |
| Semi-rigid enclosure | Housing | In use |
| Soldered and strain-relieved wiring | Electrical interconnect | Complete |
| Grayhill encoder | Earlier volume candidate | Superseded |
| Small SSD1306 concept | Earlier OLED candidate | Historical |
| Piezo / amplifier / speaker | Audible feedback | Planned |
| Rechargeable battery system | Portable power | Bench-tested; installation pending |
| Sleep/wake implementation | Power management | Planned |

Installed and operational components should not be confused with future software features.

---

## 14. Firmware module responsibilities

| Module | Responsibility |
|---|---|
| `controls/pins.py` | GPIO assignments |
| `controls/buttons.py` | Debounced momentary-button events |
| `controls/switches.py` | Maintained switch state |
| `controls/selectors.py` | Three-position room selection |
| `controls/encoders.py` | Reusable quadrature decoding |
| `controls/physical.py` | Physical coordination and dispatch |
| `display/oled.py` | OLED initialization, rendering, and polling |
| `system/perf.py` | Shared performance measurements |
| `actions.py` | Shared Dumb Queue™ and action execution |
| `device_adapters.py` | Specialized command selection |
| `devices/denon.py` | Denon transport and persistent TCP volume |
| `devices/roku.py` | Roku transport and held-button behavior |

The physical coordinator interprets control events and uses existing application services.

The OLED module performs display work independently of network command execution.

The shared queue remains the central command execution mechanism.

---

## 15. Timing and performance

### 15.1 Cooperative polling

The firmware targets frequent physical polling, approximately 1 ms when the cooperative scheduler is available.

Relevant timing behavior includes:

| Mechanism | Timing |
|---|---|
| Button debounce | Approximately 30 ms |
| Room selector debounce | Approximately 50 ms |
| Denon TCP volume pacing | At least 50 ms |
| OLED minimum refresh interval | 100 ms |
| OLED idle display-off | 15 seconds |
| Roku physical hold safety limit | 30 seconds |

These are application timing policies, not hard real-time guarantees.

### 15.2 Chapter 7 performance instrumentation

Chapter 7 introduced shared PERF instrumentation in `system/perf.py`.

The scheduler and selected subsystems use named timing measurements to investigate:

- Physical polling intervals.
- Physical execution duration.
- Queue execution.
- Adapter execution.
- Main-loop timing.
- Other scheduler and application activity.

The instrumentation is implemented and operational, with continued extension planned.

Optional internal physical diagnostics can be controlled separately from scheduler-level measurements.

### 15.3 Outstanding performance investigation

Idle physical polling is generally fast.

Sustained volume activity has exposed occasional physical execution spikes around 40–50 ms.

Blocking Roku network operations can also create substantially longer cooperative scheduler gaps.

These are different measurements and should not be treated as interchangeable explanations.

Chapter 7 tested multiple diagnostic approaches, including instrumentation changes and an explicit garbage-collection experiment, without conclusively identifying the source of the physical execution spikes.

The investigation continues in Chapter 8.

See [Development History](DEVELOPMENT_HISTORY.md) for detailed test results and prior experiments.

---

## 16. Chapter 7 verification summary

| Milestone | Status |
|---|---|
| SERVICE/DEVICE switching | Operational |
| CONFIG/RUN switching | Operational |
| Three-position room selection | Operational |
| Room-aware Power Toggle | Operational |
| Volume encoder and push-to-mute | Operational |
| Denon persistent-TCP volume | Operational |
| Roku encoder held-volume | Operational |
| Navigation and playback controls | Integrated |
| Six Roku physical hold buttons | Tested on real equipment |
| Custom-action encoder selection | Operational |
| Custom-action encoder push-to-run | Operational |
| OLED initial application integration | Complete |
| Physical soldering and wiring | Complete |
| Mounting and strain relief | Complete |
| Pico Cowbell connections | Complete |
| Shared PERF instrumentation | Operational |
| Battery power | Bench-tested; overnight software-sleep endurance and wake verified in Chapter 9; permanent installation pending |
| Sleep/wake | Software sleep and physical-button wake operational; 10-minute timeout and secret sleep toggle verified in Chapter 9 |
| Audible CLONK | Not implemented |

### Verification boundaries

Chapter 7 established a working physical controller, but did not exhaustively establish:

- Lossless encoder capture under every network-blocking condition.
- Long-uptime behavior under continuous mixed activity.
- All cross-room held-button release edge cases.
- Blank-command safety for explicit holds in Room 3.
- All network-failure and receiver-restart scenarios.
- Final battery runtime and power-management behavior.

These remain legitimate engineering work rather than unfinished physical assembly.

---

## 17. Chapter 8 hardware priorities

Chapter 8 begins with the assembled physical controller as its baseline.

Priorities include:

1. Continue targeted physical polling and performance investigation.
2. Refine custom-action selection and OLED feedback where useful.
3. Extend OLED use into additional application status paths.
4. Verify held-button safety and cross-room edge cases.
5. Continue rapid-input and long-uptime reliability testing.
6. Evaluate rechargeable battery packs after the initial software iterations.
7. Design charging, regulation, protection, and sleep/wake behavior.
8. Consider audible feedback and additional physical refinements.

**The remaining work is primarily software refinement, power management, and future capability—not completion of the basic control wiring.**

**One meaningful change at a time. One shared execution path.**

---

## 18. Chapter 9 — Rechargeable power and charging

### Battery and power hardware

Clonker's rechargeable power system uses:

- DFRobot DFR0969 dual-18650 charging and 5 V boost module.
- Two rechargeable 18650 lithium-ion cells.
- USB-A 5 V output to power the Raspberry Pi Pico 2 W.
- USB-C input for external charging power.
- Panel-mounted USB-C charging connector on the enclosure.
- DFRobot HOLD/NORMAL operating-mode switch.

The module has successfully powered Clonker independently of
a laptop or external USB supply.

On November 14, 2026, the DFRobot module and both 18650
cells were installed inside the enclosure. The permanent
external USB-C charging cable interface was also installed.

The enclosure is roomy, with an open mesh partition
separating and securing the battery system from the
remaining electronics.

Post-installation charging, temperature, and power-transition
testing is underway.

### Physical weight

| Configuration | Weight |
|---|---:|
| Clonker without batteries | 1.4 lb |
| Clonker with batteries | 1.8 lb |

**The Monster is chunky.**

### Charging and power transitions

The DFRobot's behavior is asymmetric under the tested
conditions.

| Transition | Observed result |
|---|---|
| Battery to external charging power | Seamless; Clonker continues operating |
| External charging power to battery | Output interruption; Clonker reboots |
| Charger removal in HOLD mode | USB power tester reboots |
| Charger removal in NORMAL mode | USB power tester reboots |

The charger-removal behavior was reproduced with the Pico
disconnected and only the inline USB power tester connected
to the DFRobot USB-A output.

This isolates the interruption from Clonker firmware.

The exact voltage transient and interruption duration have
not been measured.

Clonker's normal startup takes approximately 11 seconds
following the observed charger-removal reset.

HOLD remains the intended operating mode for battery use.

### Software sleep and battery operation

Chapter 9 introduced software-managed inactivity sleep.

After 10 minutes of inactivity in RUN mode, Clonker can
disable its OLED and Wi-Fi while continuing to poll
physical wake controls.

A physical pushbutton wakes Clonker through a
microcontroller reboot.

Measured current at the Pico USB input was approximately:

| Condition | Current |
|---|---:|
| Awake, idle RUN | 33–35 mA |
| Software sleep | 24 mA |

These measurements exclude DFRobot conversion losses and
the module's own power consumption. They must not be
interpreted as battery-cell current.

An approximately 12-hour battery-powered overnight test
successfully demonstrated continued power availability
and physical-button wake.

This was not a full battery-discharge test.

### Charging and assembly considerations

The charging system should use a suitably rated external
5 V USB supply.

Charging-input current measurements have reached
approximately 1.8 A during testing.

Final enclosure integration should verify:

- Secure mounting of the DFRobot module and cells.
- Insulation and protection against accidental shorts.
- Appropriate cable routing and strain relief.
- Safe cell retention and clearance from other components.
- Charging behavior and component temperatures.
- Continued operation when charging power is connected.
- Expected reboot behavior when charging power is removed.
- Battery-powered sleep and wake after final assembly.

Avoid placing pressure on the 18650 cells or exposing
their terminals to conductive enclosure hardware.

### Remaining power-system work

The DFRobot module, both 18650 cells, and permanent USB-C
charging interface are installed in the enclosure.

Remaining validation:

- Verify the installed USB-C charging connection.
- Monitor cell and DFRobot temperatures during charging.
- Verify insulation, wiring clearance, and strain relief.
- Repeat charging and power-transition tests after assembly.
- Verify battery-powered sleep and wake after assembly.
- Measure practical battery runtime over a longer period.
- Investigate hardware sleep when supported by a suitable
  stable CircuitPython release.

Detailed experiments and measured results are recorded in
[Development History](DEVELOPMENT_HISTORY.md).

---

## 19. Related documents

- [Architecture](ARCHITECTURE.md) — system boundaries, dispatcher, queue, adapters.
- [Configuration & Recovery](CONFIGURATION.md) — Config v4 schema, persistence, revision protection.
- [Firmware, Network & Clock](FIRMWARE_NETWORK.md) — scheduler, Roku/Denon transports, diagnostics.
- [Operating Modes](OPERATING_MODES.md) — SERVICE/DEVICE and CONFIG/RUN behavior.
- [Development & Deployment](DEVELOPMENT.md) — development workflow, deployment, tests.
- [Development History](DEVELOPMENT_HISTORY.md) — milestones, experiments, and performance evidence.
- [Hardware Parts List](HARDWARE_PARTS_LIST.md) — detailed component identification and procurement.

---

**THE CLONKER 10000**  
*Less sleek. More CLONK.*  
**CLONK! ⚡🔩**
