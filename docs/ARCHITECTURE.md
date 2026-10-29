# The Clonker 10000 — System Architecture

**Design reference:** Updated October 29, 2026  
**Active platform:** Raspberry Pi Pico 2 W / CircuitPython 10.3.1  
**Repository:** [djacobson/clonker-10000](https://github.com/djacobson/clonker-10000)  
**Current milestone:** Chapter 5 — physical GP17/GP18 mode switches and GP2 input events verified; physical action dispatch next  
**Configuration:** Clonker Config v4

> **Clonker controls actions, not brands. Controlled devices own their own state.**

---

## 1. Mission and principles

The Clonker 10000 is a tactile, Wi-Fi-first home-theater remote: substantial knobs, satisfying switches, guarded controls, and eventually an audible **CLONK!** It turns a user intention into a configured command without pretending to be a home-automation server or an authoritative equipment-state tracker.

The intended end-to-end path is:

1. Capture an input and determine its selected room.
2. Identify a generic fundamental or custom action.
3. Admit that action to the shared Dumb Queue™.
4. Resolve its destination and command from the active configuration.
5. Execute eligible work through the appropriate transport.
6. Record an outcome, without confusing HTTP success with equipment state.

**Be resilient in our dumbness.** Favor a predictable, recoverable, measurable system over unnecessary abstraction.

**One queue. One poller. One shared execution path.** Browser actions already use this path; physical actions will join it rather than creating a parallel execution system.

## 2. Architecture at a glance

```text
                  THE CLONKER 10000

       BROWSER TEST REMOTE        PHYSICAL CONTROLS
           OPERATIONAL           GPIO INPUTS TESTED
                 |                  |          |
                 |                  |          +-- GP2 press/release
                 |                  |              (dispatch pending)
                 v                  v
           /api/action        room + action event
                 |                  |
                 +---------+--------+
                           |
                           v
                    actions.dispatch()
                     Validate / admit
                           |
                           v
                      DUMB QUEUE™
                  Fundamental / Custom
                           |
                           v
                      actions.poll()
                    First eligible task
                           |
                           v
                 ACTIVE CONFIGURATION
                    Clonker Config v4
                           |
                           v
                 COMMAND RESOLUTION
             Ordinary / toggle / custom step
                           |
                           v
                 HTTP GET / POST
                           |
                           v
                     DENON / ROKU

           CONFIG MANAGEMENT (CONFIG MODE ONLY)

           Browser editor / HTTP port 9090
                           |
                           v
              Validate + revision check
                           |
                           v
             Verified filesystem persistence
                           |
                           v
               Publish active RAM config
               Clear queue on changed save
               Reset toggle histories
```

The physical-control branch is **not yet connected to `actions.dispatch()`**. The diagram shows the intended common interface, not a completed physical remote.

### 2.1 Architectural invariants

- Inputs express generic actions, never Denon/Roku URLs.
- Configuration owns destinations and command definitions.
- The dispatcher owns admission, eligibility, sequencing, cancellation, and execution policy.
- Transport owns the network exchange, not the meaning of an action.
- The active validated RAM configuration is authoritative at runtime.
- Changed saves clear pending work and reset volatile toggle-direction histories.
- External devices, not Clonker, own actual power, input, playback, and volume state.
- New protocols may require adapters; generic action names do not imply a universal wire protocol.

---

## 3. Verified implementation boundary — October 29, 2026

### 3.1 Operational and exercised

- Pico 2 W, CircuitPython 10.3.1, Wi-Fi, serial logging, and cooperative scheduler.
- **GP17 SERVICE (USB)/DEVICE maintained boot switch:** OFF/open selects USB-host filesystem writes; ON/grounded selects Pico firmware writes. Requires a cold power cycle to change.
- **GP18 guarded CONFIG/RUN maintained switch:** OFF/open selects RUN and stops management HTTP; ON/grounded selects CONFIG and enables it. Runtime transitions tested without reboot.
- **GP2 momentary button:** initialized, debounced, and producing logged press/release events.
- Browser configuration editor, Test Remote, Clonker Config v4 validation, revision protection, persistence, and selected recovery cases.
- Fundamental and custom actions through a shared queue, with real Denon/Roku GET/POST execution.
- Volatile per-room power/mute command-direction histories, including success, failure, no-op, and changed-save behavior.
- A Sunroom custom action: Roku Home, cooperative 3000 ms wait, Denon Quick Select 1; both requests returned HTTP 200.
- Independent eligible Volume Up action executed during that compound-action wait.
- CONFIG page responsiveness restored by changing HTTP polling from 10 ms to 1 ms; browser tests succeeded with GPIO polling enabled.

### 3.2 Not yet integrated or not exhaustively verified

- Physical room selector, room-aware GPIO dispatch, and GP2-to-`power-toggle` dispatch.
- Navigation, Back, Home, volume encoder, and custom-action selector wired into action dispatch.
- Physical event capture under blocking outbound HTTP or high-rate encoder input.
- OLED, audio feedback, battery/sleep behavior, and final enclosure.
- User-defined custom destinations beyond the three built-in slots.
- Apple TV discovery, pairing, authentication, and command transport.
- Long-duration load, all malformed HTTP inputs, extended outages, and every sudden-power-loss scenario.

A detected press is **not** an admitted action. An admitted action is **not** an executed HTTP request. HTTP 200 is **not** proof that the equipment reached the desired state.

---

## 4. Firmware component ownership

| Component | Responsibility |
|---|---|
| `firmware/boot.py` | GP17 boot-time filesystem ownership selection |
| `firmware/code.py` | CircuitPython entry point |
| `firmware/clonker/main.py` | Startup, mode transitions, cooperative polling |
| `firmware/clonker/device_config_v2.py` | Config v4 validation, RAM snapshot, revision, persistence, recovery |
| `firmware/clonker/device_config.json` | Active device configuration when deployed |
| `firmware/clonker/actions.py` | Fundamental/custom dispatch, Dumb Queue™, step execution, cancellation |
| `firmware/clonker/net/http_transport.py` | Bounded synchronous outbound HTTP GET/POST |
| `firmware/clonker/net/web.py` | CONFIG-mode management HTTP and browser APIs |
| `firmware/clonker/www/index.html` | Browser configuration editor |
| `firmware/clonker/www/remote.html` | Browser Test Remote and custom-action runner |
| `firmware/clonker/controls/pins.py` | Developer-maintained GPIO assignments |
| `firmware/clonker/controls/switches.py` | GP18 CONFIG/RUN source, physical read, simulated fallback and override |
| `firmware/clonker/controls/physical.py` | Optional physical-button initialization and polling; currently logs events |
| `firmware/clonker/controls/buttons.py` | Reusable debounced button input |
| `firmware/clonker/system/clock.py` | UTC reference and monotonic-based timestamps |
| `firmware/clonker/system/logger.py` | Serial diagnostics |
| `firmware/clonker/legacy/` | Historical XML implementation |

The filename `device_config_v2.py` is historical; the active schema constant is `CONFIG_VERSION = 4`. Avoid cosmetic renames that risk disrupting a working deployment.

### 4.1 Separation of concerns

**Configuration** says where and how to send a command. **Action** says what the user wants. **Queue** decides when eligible work executes. **Transport** performs the exchange. **Physical controls** should only capture intent and room context.

---

## 5. Two independent operating-mode dimensions

### 5.1 GP17: SERVICE (USB) / DEVICE

| Switch | Electrical state | Mode | Filesystem write owner |
|---|---|---|---|
| OFF | Open / pulled HIGH | SERVICE (USB) | USB host |
| ON | Grounded / LOW | DEVICE | Pico firmware |

GP17 is physical Pico pin 22, with adjacent ground at pin 23. `boot.py` selects the mode before the application starts. **A full power cycle is required** to change ownership; Ctrl+D is not equivalent. Browser inspection can work in SERVICE + CONFIG, but configuration saves are rejected when the Pico filesystem is read-only.

### 5.2 GP18: CONFIG / RUN

| Switch | Electrical state | Application mode | Management HTTP |
|---|---|---|---|
| OFF | Open / pulled HIGH | RUN | Stopped |
| ON | Grounded / LOW | CONFIG | Enabled, port 9090 |

`switches.py` reads GP18 with an internal pull-up. The application starts/stops the listener as the switch changes, without rebooting. A simulated source and explicit software override remain available for development. An open circuit is not proof that a switch is physically present.

The queue continues to be polled in both modes. **DEVICE + RUN** is the intended ordinary remote combination; **DEVICE + CONFIG** permits persistent browser edits. Neither switch is an AV equipment power command or a room selector.

For operating procedures, see [Operating Modes](OPERATING_MODES.md).

---

## 6. Configuration architecture

The active schema is **Clonker Config v4**, stored as JSON. A room has a stable ID, display name, three built-in device slots, fourteen fundamental actions, and optional custom actions. The current sample configures **Den and Sunroom**; additional room support may evolve independently of the sample.

### 6.1 Generic built-in destinations

| Stable ID | Default browser label |
|---|---|
| `device-1` | TV |
| `device-2` | AVR |
| `device-3` | Streaming |

Labels do not enforce device types. Endpoints and mappings determine actual behavior. The browser editor is a client of the validated configuration engine, not an alternative source of truth.

### 6.2 RAM snapshot, revision, and recovery

Startup loads and validates the active file at `/clonker/device_config.json`. Runtime dispatch resolves definitions from the in-memory configuration rather than rereading JSON per action.

The browser receives revision and filesystem-writability metadata. Saves validate the submitted schema and expected revision, protect against stale tabs, verify temporary writes, and manage backups. On a successful **changed** save, the management layer clears pending actions and resets toggle histories. An unchanged save preserves both.

Backup rotation is risk reduction, not a guarantee against every interrupted-write or power-loss scenario. The Pico filesystem does not automatically synchronize with the GitHub repository. See [Configuration & Recovery](CONFIGURATION.md) for the authoritative schema, limits, and recovery procedures.

---

## 7. Fundamental actions and toggles

Each configured room defines fourteen stable fundamental action IDs. Ordinary actions resolve a destination, method, and command path. Missing ordinary endpoints or blank paths produce intentional logged no-ops.

`power-toggle` and `mute-toggle` use configured ON/OFF paths and independent volatile direction histories for each room and action. An unknown history starts with ON. History advances **only after successful HTTP execution**; failures and no-ops do not advance it. A reboot resets history; a changed configuration save also resets it.

This is **last-successful-command direction**, not device-state discovery. HDMI-CEC, other remotes, and device applications may change equipment state without Clonker knowing.

---

## 8. The Dumb Queue™

**One queue. One poller. One shared execution path.** `actions.py` owns admission and execution of both fundamental and custom actions.

### 8.1 Admission and representation

`actions.dispatch(room_id, action_id, delay_seconds=0)` validates the room, action, delay, and capacity, then queues a compact task. The queue holds up to **128 entries**. Tasks carry identifiers and scheduling metadata rather than copies of endpoint definitions. A compound custom action occupies **one entry**, not one entry per step.

### 8.2 Eligibility and ordering

The poller scans for the **first eligible** task. Immediate work can bypass a future-dated task; among currently eligible tasks, queue order matters. This is not strict FIFO across delayed work. Due times use `time.monotonic()`.

> **A future task must not hold an immediate button press hostage.**

### 8.3 Compound custom actions

A custom action has a stable ID, name, and one to sixteen ordered steps; up to sixteen custom actions per room are supported in Config v4. Each step resolves a built-in destination, GET/POST method, path, and `wait_after_ms`.

One eligible `actions.poll()` executes at most one outbound command. After a successful step, the task is requeued with a due time calculated **after that request completes**. Independent eligible actions can execute during the wait. No separate macro thread, nested scripts, branching, or rollback exists.

### 8.4 Failure and consistency policy

One execution failure clears the remaining queue, including unfinished compound work; the dispatcher remains available for new requests. There are no automatic retries. A successful changed configuration save also clears pending tasks so they cannot silently execute under a new mapping.

Queue admission is not network completion, and network completion is not equipment-state verification.

---

## 9. Cooperative scheduler and HTTP

`main.py` currently uses:

| Service | Poll interval |
|---|---:|
| Physical input | 10 ms (`0.01` seconds) |
| Action queue | 10 ms (`0.01` seconds) |
| CONFIG management HTTP | 1 ms (`0.001` seconds) |
| Main-loop yield | 1 ms (`time.sleep(0.001)`) |

These are target polling intervals, **not hard real-time guarantees**. Each service performs bounded work and returns to the loop. `physical.poll()` currently logs button events; it does not dispatch actions.

### 9.1 Inbound versus outbound network behavior

The inbound management service is a cooperative, nonblocking, single-active-client listener on port 9090. It services accept, receive, and send work incrementally. It is available only in CONFIG mode.

Outbound HTTP is **bounded but blocking**: one fresh TCP socket per GET/POST, with status-line inspection and HTTP 2xx acceptance. A blocking socket call temporarily pauses browser servicing, queue polling, and physical-input polling. A queue buffers admitted work; it cannot capture GPIO transitions the scheduler never sees.

### 9.2 October 28 browser pacing investigation

The CONFIG page intermittently loaded slowly or incompletely. Disabling GPIO polling did not remove the problem. HTTP diagnostics showed response transmissions sometimes timing out partway through large pages. Because the inbound server sends bounded chunks, 10 ms between web polls could add substantial scheduling delay.

Changing `WEB_POLL_INTERVAL` from `0.01` to `0.001` substantially improved observed Chrome and Safari page loading. Repeated browser tests succeeded with physical polling re-enabled and diagnostics off. The precise reason the problem surfaced at that development stage remains unproven; the 1 ms interval is a tested baseline, not a proven optimum.

Detailed limits, diagnostics, and evidence belong in [Firmware, HTTP & Clock](FIRMWARE_NETWORK.md).

---

## 10. Browser and management interface

The CONFIG-mode service provides the editor, Test Remote, configuration API, clock API, and action submission.

| Route | Responsibility |
|---|---|
| `GET /` | Browser configuration editor |
| `GET /remote.html` | Browser Test Remote |
| `GET /api/config` | Validated configuration, revision, filesystem metadata |
| `POST /api/config` | Revision-protected validated save |
| `GET /api/clock` | Clock source and timestamp |
| `POST /api/clock?utc=...` | Browser UTC reference update |
| `POST /api/action?room=...&action=...` | Admit fundamental or saved custom action |

An accepted action API request acknowledges queue admission only. The Test Remote uses the same dispatcher and queue as the eventual physical controls.

The management API has **no application-level authentication**. Keep it on a trusted LAN; do not forward port 9090 to the public internet.

---

## 11. Physical controls — Chapter 5

### 11.1 Current input foundation

`controls/pins.py` assigns **GP2** to `POWER_TOGGLE_PIN` and **GP18** to `CONFIG_SWITCH_PIN`; the other physical buttons, encoders, and room-selector inputs are currently unassigned (`None`). GP17 is handled separately in `boot.py`.

`physical.initialize()` constructs reusable debounced buttons for assigned inputs, with optional initialization so absent or faulty controls need not prevent the application from starting. `physical.poll()` reports events to serial diagnostics. GP2 press/release detection has been tested; there is no physical event-to-action bridge yet.

`switches.py` owns GP18 separately from the general button poller. This separation preserves CONFIG/RUN mode semantics independently of room-specific commands.

### 11.2 Next integration boundary

The next sequence is to test the room selector, establish room context, and connect a GP2 press to the existing `power-toggle` action. After that, add navigation and shortcut buttons, the custom-action selector, and the volume encoder. Physical input should supply only `(room_id, action_id)` or equivalent generic intent to `actions.dispatch()`.

**Do not put Denon/Roku HTTP paths in GPIO code. Do not add a second queue.**

The Grayhill volume encoder may generate events faster than one new TCP connection per HTTP command can process. Measure capture and responsiveness during actual network activity before designing acceleration, accumulation, coalescing, or connection reuse.

### 11.3 Hardware scope and deferred feedback

The mechanical concept includes substantial encoders, a guarded master control, navigation buttons, room selection, a tiny SSD1306 OLED, and optional sound feedback. Specific enclosure, power, sleep/wake, and display behavior remain hardware-dependent. Do not document speculative OLED behavior as implemented.

See [Hardware & Physical Controls](HARDWARE_CONTROLS.md) for component inventory, verified pin assignments, and mechanical decisions.

---

## 12. Room selection and custom destinations

Stable room IDs belong to configuration. The room selector should choose which configured room receives physical actions without duplicating mappings. Den and Sunroom are the current sample rooms. A future BOTH or multi-room behavior is **not implemented** and must not be inferred from selector hardware.

The existing three built-in destination slots remain stable. Additional user-defined custom destinations (`device-4` onward) are a future extension, not a Config v4 feature. The conceptual design places them in an optional per-room collection, separate from built-in slots; actual schema, migration, and deletion behavior require a concrete implementation decision.

A destination has identity and connection information. Behavior belongs to actions. Never silently retarget actions when a destination changes.

---

## 13. Apple TV and other future protocols

Apple TV compatibility is an explicit objective, **not an implemented feature**. Discovery, pairing, authentication, session management, and a protocol-specific adapter may be required. The present stateless Denon/Roku HTTP transport should not be assumed suitable.

Keep generic intentions such as Home, Back, navigation, and Play/Pause independent of equipment brands. Do not add a speculative `apple_tv.py` module or configuration schema before concrete requirements and tests justify them.

---

## 14. Clock, diagnostics, and verification discipline

Browser synchronization supplies a UTC reference for readable timestamps. Queue deadlines and compound waits use `time.monotonic()` and do not shift when wall-clock time is adjusted. Automated NTP synchronization is not established by the tested baseline.

Use evidence labels precisely:

- **Implemented and verified:** observed on the Pico, browser, or equipment as specified.
- **Implemented, not exhaustively tested:** working code with remaining untested conditions.
- **Planned:** a future design or requirement, not a running feature.
- **Historical:** an earlier stage superseded by the current baseline.

A commit proves source changed; deployment proves files were copied; HTTP 200 proves a transport acknowledgment; equipment observation supports a physical-behavior claim. These are different evidence levels.

Preserve the known-good configuration and record test conditions before risky changes. Keep dated experiments in [Development History](DEVELOPMENT_HISTORY.md) rather than duplicating an entire test diary here.

---

## 15. Historical milestones

| Milestone | Architectural result |
|---|---|
| XML v1 | Early browser editing and persistence concepts; historical |
| Config v2 | JSON validation, revisions, verified writes, backup rotation |
| Dumb Queue™, October 20 | Bounded admission, eligible-task scheduling, failure cancellation |
| Outbound HTTP, October 21 | Real Denon/Roku GET/POST execution |
| Config v3, October 22 | Stable generic `device-1`/`device-2`/`device-3` IDs |
| Config v4, October 2026 | Named custom actions and cooperative ordered steps |
| Chapter 4 completion, October 27 | Verified custom actions, toggles, interleaving |
| Chapter 5, October 28 | GPIO scheduler foundation and HTTP pacing correction |
| Chapter 5, October 29 | GP17/GP18 physical mode switches and GP2 input events verified |

---

## 16. Design principles worth remembering

**Less sleek. More CLONK.**

**Smart enough to know when to be dumb.**

**Be resilient in our dumbness.**

**One queue. One poller. One shared execution path.**

**A future task must not hold an immediate button press hostage.**

**One failed external command cancels pending work, not the remote itself.**

**Clonker sends commands. Equipment owns state.**

**A command sequence is not permission to invent a workflow engine.**

**Configuration describes the destination. Actions describe the intention. Transport delivers the message.**

> **Do not make the Clonker more complicated merely because we are capable of making it more complicated.**

### 16.1 Future objective — Clonker Recipe Library

**Status:** Conceptual, not implemented. Custom actions are operational; custom destinations and recipe distribution remain future work.

A future recipe library could provide downloadable configuration examples for equipment combinations and named sequences. A future editor might retrieve a catalog, display compatibility notes, and load a recipe for review before an explicit Save. Recipes must never bypass validation, revision protection, or persistence safeguards.

**Recipes help configure the Clonker; they do not become a runtime dependency.**

---

## 17. Reference documents

- [Configuration & Recovery](CONFIGURATION.md) — schema, validation, revisions, persistence, recovery.
- [Firmware, HTTP & Clock](FIRMWARE_NETWORK.md) — networking, scheduler details, transport, evidence.
- [Operating Modes](OPERATING_MODES.md) — GP17 and GP18 mode behavior.
- [Hardware & Physical Controls](HARDWARE_CONTROLS.md) — parts, GPIO assignments, mechanical plans.
- [Development & Deployment](DEVELOPMENT.md) — iPad-first workflow and tests.
- [Development History](DEVELOPMENT_HISTORY.md) — chronological engineering milestones.
- [Chapter 2 Handoff](CHAPTER_2_HANDOFF.md) — historical reference.
- [Terminology Audit](TERMINOLOGY_AUDIT.md) — historical terminology reconciliation.
- [Old Architecture](OLD_ARCHITECTURE.md) — historical reference.
- [`samples/device_config_roku_denon_sample.json`](../samples/device_config_roku_denon_sample.json) — readable two-room sample.

---

**THE CLONKER 10000**  
*Less sleek. More CLONK.*  
**CLONK! ⚡🔩**
