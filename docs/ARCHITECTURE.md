# The Clonker 10000 — System Architecture

**Design reference:** November 3, 2026  
**Platform:** Raspberry Pi Pico 2 W / CircuitPython 10.3.1  
**Repository:** [djacobson/clonker-10000](https://github.com/djacobson/clonker-10000)  
**Current baseline:** Chapter 6 closeout — physical controls and mixed-protocol volume operational  
**Configuration:** Clonker Config v4

> **Clonker controls actions, not brands. Controlled devices own their own state.**

---

## 1. Mission and architectural principles

The Clonker 10000 is a tactile, Wi-Fi-first home-theater remote.

Its purpose is to translate physical or browser input into configured equipment commands without becoming a general-purpose home-automation server.

The intended architecture is deliberately simple:

1. Detect a physical or browser action.
2. Determine the target room.
3. Resolve the generic action identity.
4. Admit work to the shared Dumb Queue™.
5. Resolve the command from active configuration.
6. Select the appropriate device transport.
7. Execute the command.
8. Record the result without pretending to know equipment state.

The design favors predictable behavior, serviceability, and incremental development.

**One queue. One poller. One shared execution path.**

Both physical controls and the browser Test Remote use the same action system.

The remote does not maintain authoritative equipment state. It sends commands and observes transport results.

**Be resilient in our dumbness.**

---

## 2. Architecture at a glance

```text
                   THE CLONKER 10000

     BROWSER TEST REMOTE          PHYSICAL CONTROLS
              |                  Buttons / Encoders
              |                     Room Selector
              |                           |
              |                       physical.py
              |                     Event -> Action
              |                     Selected Room
              |                           |
              |                     Room available?
              |                       /       \
              |                     YES        NO
              |                      |          |
              |                      |        NO-OP
              |                      |
              +-----------+----------+
                          |
                          v
                   actions.dispatch()
                    Validate / Admit
                          |
                          v
                      DUMB QUEUE™
                  Fundamental / Custom
                          |
                          v
                     actions.poll()
                    Eligible command
                          |
                          v
                   ACTIVE CONFIGURATION
                     Clonker Config v4
                          |
                          v
                    COMMAND RESOLUTION
                Ordinary / Toggle / Custom
                          |
                          v
                    device_adapters.py
                Signature / Cache / Execute
                          |
              +-----------+-----------+
              |           |           |
              v           v           v
          Denon TCP    Roku Hold   Generic HTTP
          Persistent   ECP Key     GET / POST
          Port 23      Down / Up
              |           |           |
              v           v           v
          Denon AVR    Roku ECP    Roku / Denon
           Volume      Volume      Other Actions


             COOPERATIVE MAINTENANCE LOOP
                          |
                          v
                 device_adapters.poll()
                          |
                          v
                  Roku Hold Release
                   / Retry Pacing


             CONFIG MANAGEMENT — GP18 CONFIG

                Browser / Port 9090
                          |
                          v
                Validate + Revision
                          |
                          v
                 Verified File Save
                          |
                          v
                 Publish RAM Config
                 Rebuild Adapter Cache
                 Clear Pending Actions
                 Reset Toggle Histories
```

The diagram shows two related but distinct responsibilities:

- The **Dumb Queue™** owns the lifecycle and ordering of requested actions.
- The **adapter layer** owns protocol-specific execution and maintenance.

A Roku key release may occur after the queue becomes empty. Therefore, adapter maintenance is part of the cooperative application scheduler, not a separate action queue.

### 2.1 Architectural invariants

- Physical controls generate generic actions, never manufacturer-specific command paths.
- Configuration owns destination and command definitions.
- `selectors.py` owns physical room-selection state.
- `physical.py` owns physical-event interpretation and room-aware dispatch.
- `actions.py` owns action admission, sequencing, eligibility, and cancellation.
- `device_adapters.py` owns command-signature recognition, cached selection, execution delegation, and adapter lifecycle coordination.
- Individual adapters own protocol-specific behavior.
- Generic HTTP is the fallback transport.
- Browser and physical inputs share the same dispatcher.
- Active validated RAM configuration is authoritative.
- Changed configuration saves invalidate pending work and reset toggle histories.
- External equipment owns actual power, volume, playback, and input state.
- Missing optional physical hardware must not disable the core application.

**No duplicate command pipelines. No second queue. No manufacturer-specific networking logic in GPIO drivers.**

---

## 3. Firmware component ownership

| Component | Responsibility |
|---|---|
| `firmware/boot.py` | GP17 boot-time filesystem ownership |
| `firmware/code.py` | CircuitPython application entry |
| `firmware/clonker/main.py` | Initialization, operating modes, cooperative scheduler |
| `firmware/clonker/device_config_v2.py` | Config v4 validation, RAM state, revisions, persistence |
| `firmware/clonker/actions.py` | Action dispatcher, Dumb Queue™, sequencing, cancellation |
| `firmware/clonker/device_adapters.py` | Adapter recognition, routing, execution, polling, cleanup |
| `firmware/clonker/devices/denon.py` | Persistent Denon TCP volume transport |
| `firmware/clonker/devices/roku.py` | Roku ECP held-volume controller |
| `firmware/clonker/net/http_transport.py` | Generic bounded outbound HTTP |
| `firmware/clonker/net/web.py` | CONFIG-mode management HTTP |
| `firmware/clonker/controls/pins.py` | GPIO assignments |
| `firmware/clonker/controls/buttons.py` | Debounced momentary button driver |
| `firmware/clonker/controls/selectors.py` | Physical room selector |
| `firmware/clonker/controls/encoders.py` | Reusable quadrature encoder driver |
| `firmware/clonker/controls/physical.py` | Physical polling and generic action mapping |
| `firmware/clonker/controls/switches.py` | CONFIG/RUN switch and development overrides |
| `firmware/clonker/system/clock.py` | UTC reference and monotonic timing |
| `firmware/clonker/system/logger.py` | Serial diagnostics |
| `firmware/clonker/www/` | Configuration editor and Test Remote |
| `firmware/clonker/legacy/` | Historical XML implementation |

The historical filename `device_config_v2.py` does not indicate the current configuration schema version.

The active schema is **Config v4**.

Avoid cosmetic renames that could disrupt the working firmware merely to make filenames match current terminology.

### 3.1 Separation of responsibilities

**Hardware drivers** detect electrical changes.

**Physical coordination** translates those changes into generic action IDs and supplies the selected room.

**Configuration** defines destinations and commands.

**Action dispatch** validates and queues work.

**Device adapters** determine how eligible commands are transmitted.

**Transports** perform network communication.

This separation allows the same action to originate from a browser, momentary button, or rotary encoder without duplicating command logic.

### 3.2 Hardware versus application state

Reusable hardware drivers should know only what is necessary to interpret their input.

The `Encoder` class understands quadrature transitions, not volume levels or receiver protocols.

The `Button` class understands debounced press and release events, not power or mute semantics.

The room selector understands its physical position, not the equipment configuration.

Application-level coordination assigns meaning to these events.

The planned custom-action encoder will reuse the quadrature driver while maintaining its own application selection state.

**Reusable hardware mechanisms; simple application-specific state.**

---

## 4. Operating modes

The Clonker has two independent operating-mode dimensions.

### 4.1 SERVICE / DEVICE — GP17

| Electrical state | Mode | Filesystem writer |
|---|---|---|
| Open / HIGH | SERVICE | USB host |
| Grounded / LOW | DEVICE | Pico firmware |

GP17 is evaluated by `boot.py`.

Changing filesystem ownership requires a full power cycle.

A CircuitPython Ctrl+D soft reboot does not reproduce the boot-time ownership decision.

### 4.2 CONFIG / RUN — GP18

| Electrical state | Mode | Management HTTP |
|---|---|---|
| Open / HIGH | RUN | Disabled |
| Grounded / LOW | CONFIG | Enabled, port 9090 |

GP18 is evaluated while the application runs.

The mode can change without rebooting.

The Dumb Queue™ continues operating in both modes.

The switch implementation also supports development simulation and override.

### 4.3 Valid combinations

| GP17 mode | GP18 mode | Behavior |
|---|---|---|
| SERVICE | CONFIG | USB owns filesystem; browser can inspect and test, but cannot persist Pico-side changes |
| SERVICE | RUN | USB owns filesystem; management listener off |
| DEVICE | CONFIG | Pico owns filesystem; browser management and saves enabled |
| DEVICE | RUN | Normal remote operation |

Neither switch is an equipment power command.

See [Operating Modes](OPERATING_MODES.md) for procedures and caveats.

---

## 5. Configuration architecture

The active configuration is **Clonker Config v4**, stored as JSON.

The deployed configuration path is:

`/clonker/device_config.json`

Each configured room contains:

- A stable room ID.
- A display name.
- Three generic built-in device destinations.
- Fourteen fundamental action definitions.
- Optional named custom actions.

The current installation has two configured rooms:

- `room-1` — Den.
- `room-2` — Sunroom.

The physical selector reserves `room-3` for future use.

### 5.1 Generic built-in destinations

| Stable ID | Default label |
|---|---|
| `device-1` | TV |
| `device-2` | AVR |
| `device-3` | Streaming |

These labels are presentation defaults, not enforced protocol types.

A configured action determines which destination and command path are used.

For example, Sunroom volume currently targets its Roku through the Streaming destination, while Den volume targets its Denon receiver.

The physical volume encoder does not need to know this distinction.

### 5.2 Active RAM configuration

At startup, the configuration engine loads and validates the persisted JSON.

Runtime command execution resolves definitions from the active in-memory configuration.

It does not reread the JSON file for every action.

The browser editor is a client of the configuration engine, not a separate source of truth.

### 5.3 Save and recovery boundaries

The configuration engine provides:

- Schema validation.
- Revision checks against stale browser edits.
- Filesystem writability checks.
- Verified temporary writes.
- Backup rotation.
- Recovery handling.

A successful changed save publishes the validated configuration, rebuilds adapter selections, clears pending work, and resets volatile toggle histories.

An unchanged save preserves existing work and toggle histories.

A rejected save must not replace active configuration or adapter routing.

The Pico filesystem does not automatically synchronize with GitHub.

See [Configuration & Recovery](CONFIGURATION.md) for exact persistence behavior.

---

## 6. Fundamental actions and custom actions

### 6.1 Fundamental actions

Each room defines fourteen stable fundamental action IDs.

Examples include:

- Power Toggle.
- Volume Up / Down.
- Mute Toggle.
- Navigation Up / Down / Left / Right.
- Select, Back, Home.
- Play/Pause.
- Skip Back / Forward.

Actions resolve configured destinations, methods, and paths.

Missing ordinary endpoints or blank command paths produce intentional logged no-ops.

The action vocabulary is independent of equipment protocols.

### 6.2 Power and mute toggles

`power-toggle` and `mute-toggle` use independent volatile direction histories keyed by room and action.

Unknown history begins with the configured ON path.

History advances only after successful transmission.

Failures and no-ops do not advance it.

A reboot or successful changed configuration save resets histories.

This is **last-successful-command direction**, not equipment-state discovery.

A receiver, Roku, HDMI-CEC chain, or another remote may change equipment state without Clonker knowing.

### 6.3 Custom actions

Custom actions are named, ordered sequences configured per room.

Each step specifies a destination, method, path, and optional wait.

A custom action occupies one Dumb Queue™ entry while progressing through its steps.

Waits use monotonic deadlines.

Other eligible actions may execute while a custom action is waiting.

Current custom-action steps use generic HTTP, even when a command resembles a specialized fundamental volume command.

There is no branching engine, macro thread, rollback system, or independent custom-action queue.

---

## 7. The Dumb Queue™

**Module:** `clonker/actions.py`

The Dumb Queue™ is the single execution pipeline for browser and physical actions.

Its responsibilities are:

1. Validate and admit requested actions.
2. Maintain bounded pending work.
3. Determine eligible commands.
4. Preserve applicable ordering.
5. Resolve commands from active configuration.
6. Coordinate adapter readiness and execution.
7. Advance custom-action steps.
8. Cancel pending work after failures.

### 7.1 Capacity and representation

The queue holds up to **128 entries**.

Fundamental actions use stable IDs.

Custom actions use room-specific IDs and compact step state.

Commands are resolved when eligible rather than copied into each queue entry.

### 7.2 Eligibility and ordering

The queue scans for the first eligible task.

An action waiting for a future deadline does not block an immediate action.

Among currently eligible tasks, queue order matters.

If an eligible Denon TCP volume command is waiting for its pacing interval, the queue preserves its position rather than allowing later commands to overtake it.

At most one eligible queued command is executed per poll.

### 7.3 Failure policy

An execution exception cancels remaining pending work, including unfinished custom actions.

New work may subsequently be admitted.

The queue does not automatically retry uncertain commands.

This avoids blindly duplicating operations that might already have reached equipment.

Adapter-specific cleanup, including a pending Roku key release, is a separate lifecycle responsibility.

**One failed external command cancels pending work, not the remote itself.**

### 7.4 Queue versus adapter state

The queue owns action state.

An adapter may own transport state.

Examples:

- Denon owns its persistent TCP socket and pacing deadline.
- Roku owns its held-key direction, endpoint, and release deadlines.
- Generic HTTP owns temporary sockets during individual requests.

These states do not constitute separate action queues.

---

## 8. Device adapter architecture

**Module:** `clonker/device_adapters.py`

The adapter layer separates generic command intent from protocol-specific transmission.

Selection is based on recognized command signatures, not room names, manufacturer labels, or fixed device positions.

### 8.1 Current adapter matrix

| Adapter | Recognized command | Delivery |
|---|---|---|
| `denon-tcp` | Denon fundamental volume GET signatures | Persistent TCP port 23 |
| `roku-hold` | Roku fundamental volume POST signatures | ECP keydown/keyup |
| `generic-http` | All other supported configured commands | Bounded HTTP GET/POST |

Only recognized fundamental volume actions select specialized adapters.

Other fundamental actions and current custom-action steps use generic HTTP.

### 8.2 Signature-based selection

Recognized Denon signatures:

```text
GET /goform/formiPhoneAppDirect.xml?MVUP
GET /goform/formiPhoneAppDirect.xml?MVDOWN
```

Recognized Roku signatures:

```text
POST /keypress/VolumeUp
POST /keypress/VolumeDown
```

These signatures identify how a command should be delivered.

They do not require fixed room IDs or hardcoded destination names.

### 8.3 Adapter cache

Specialized selections are cached by `(room_id, action_id)`.

The cache is derived from active validated configuration and is not persisted in Config v4 JSON.

Unrecognized commands use generic HTTP.

The cache is rebuilt when configuration becomes active.

A rejected configuration save retains the previous routing state.

The cache does not contain equipment power or volume state.

### 8.4 Execution and lifecycle

The adapter layer coordinates:

- Readiness checks.
- Protocol-specific execution.
- Maintenance polling.
- Cancellation cleanup.
- Application shutdown cleanup.

A key architectural distinction is that adapter maintenance may continue when the action queue is empty.

For example, Roku held-volume requires a later keyup after the final volume action has completed.

The cooperative scheduler calls adapter maintenance independently of whether another action is eligible.

This is not a second queue or background worker.

---

## 9. Protocol-specific transport responsibilities

### 9.1 Denon TCP

**Module:** `clonker/devices/denon.py`

The Denon adapter:

- Extracts the receiver host from the configured endpoint.
- Uses native TCP port 23.
- Reuses one persistent receiver connection.
- Translates recognized volume signatures to `MVUP` or `MVDOWN`.
- Enforces a minimum 50 ms command interval.
- Closes and resets its connection on appropriate errors or shutdown.

The adapter currently supports one active receiver connection, not a pool of simultaneous connections.

It does not parse receiver status responses or maintain authoritative AVR state.

A successful TCP write does not prove the receiver executed the command.

### 9.2 Roku held-volume

**Module:** `clonker/devices/roku.py`

The Roku adapter uses ECP keydown/keyup operations to turn repeated encoder movements into a temporary held key.

Its responsibilities include:

- Starting a hold on the first detent.
- Extending same-direction holds without additional HTTP requests.
- Releasing after an idle period.
- Releasing before direction reversal.
- Bounding maximum hold duration.
- Retaining unresolved release state after failures.
- Pacing release retries.
- Participating in cancellation and shutdown cleanup.

The current timing parameters are:

| Parameter | Value |
|---|---:|
| Idle release | 250 ms |
| Maximum hold | 2 seconds |
| Failed-release retry interval | 500 ms |

The Roku adapter uses the generic outbound HTTP transport for its ECP requests.

It does not maintain a persistent HTTP socket.

The adapter's release-retry mechanism is a specialized safety measure, not a general action retry system.

Successful HTTP responses do not independently establish receiver volume or guarantee remote key state.

### 9.3 Generic HTTP

**Module:** `clonker/net/http_transport.py`

Generic HTTP provides bounded blocking GET/POST requests.

It is used for:

- Ordinary Roku ECP commands.
- Denon HTTP power and mute.
- Roku VolumeMute.
- Custom-action steps.
- Other configured commands without recognized specialized signatures.

Each request creates and closes its own TCP connection.

The transport is intentionally small and does not provide full HTTP response-body processing, TLS, authentication, redirects, or persistent connections.

### 9.4 Why three paths exist

The transports solve different problems.

Denon volume benefits from a persistent native TCP connection.

Roku volume benefits from minimizing HTTP requests during rapid encoder movement.

Ordinary actions remain well served by bounded HTTP.

The architecture allows these approaches to coexist without modifying the generic action vocabulary or creating new execution pipelines.

Detailed timing, failure semantics, and implementation tests belong in [Firmware, Network & Clock](FIRMWARE_NETWORK.md).

---

## 10. Cooperative scheduler

**Module:** `clonker/main.py`

The firmware uses a cooperative main loop rather than threads or hardware-interrupt-driven command execution.

Current target intervals:

| Responsibility | Target |
|---|---:|
| Physical controls | 1 ms |
| Action queue | 10 ms |
| Management HTTP | 1 ms |

The main loop also yields briefly.

The scheduler services physical inputs, queued actions, adapter maintenance, operating-mode changes, and inbound management requests.

These intervals are targets, not guaranteed maximum latencies.

### 10.1 Physical input responsiveness

Rotary encoders generate electrical transitions that must be sampled.

The reusable encoder driver decodes transitions and reports completed movements.

Physical coordination translates them into generic actions.

Network execution occurs separately through the queue.

The specialized volume adapters reduce the network overhead associated with rapid rotation.

However, synchronous socket operations can still temporarily delay physical sampling.

The queue cannot reconstruct electrical transitions that were never observed.

### 10.2 Adapter maintenance

The Roku held-volume controller requires maintenance after the last encoder detent.

Therefore, the scheduler polls the adapter layer even when no queue command is ready.

The adapter layer may attempt a key release or defer a retry until its deadline.

This preserves a cooperative design without adding another action queue or worker.

### 10.3 Management HTTP

The CONFIG-mode management server uses a cooperative single-client listener.

It is not a concurrent web server.

The application has no management authentication and is intended for a trusted LAN only.

Browser actions and physical actions continue sharing the same queue.

---

## 11. Physical controls

The current physical-control subsystem is operational for room selection, equipment Power Toggle, volume rotation, and push-to-mute.

### 11.1 Current GPIO assignments

| GPIO | Function | Status |
|---|---|---|
| GP2 | Momentary Power Toggle | Operational |
| GP3 | Room selector — Den | Operational |
| GP4/GP5 | STEMMA QT / I²C | Reserved |
| GP6 | Room selector — Sunroom | Operational |
| GP7 | Room selector — reserved Room 3 | Operational selection |
| GP8/GP9 | Bourns volume encoder A/B | Operational |
| GP10 | Bourns encoder push-to-mute | Operational |
| GP17 | SERVICE/DEVICE | Operational |
| GP18 | CONFIG/RUN | Operational |

`controls/pins.py` is the source of truth for assignments.

Optional unassigned inputs are not initialized.

The Pico Cowbell Terminal board provides screw-terminal access, and the wiring uses shared ground distribution.

### 11.2 Physical room selector

The three-position selector uses GP3/GP6/GP7.

It requires exactly one active grounded input and 50 ms of stable selection before accepting a change.

Invalid transitional readings do not replace the last valid room.

The selector changes room context; it does not dispatch a network action.

### 11.3 Reserved Room 3

Room 3 is a valid physical selector position but is not configured.

When selected, physical action dispatch rejects the unavailable room before queue admission.

No command is sent.

There is no fallback to Den or Sunroom.

The third position is not a BOTH mode.

### 11.4 Momentary buttons

`controls/buttons.py` provides active-low, internally pulled-up, debounced momentary inputs.

Stable press events are mapped to generic actions.

Release events are diagnostic.

The current operational buttons are:

- GP2 Power Toggle.
- GP10 volume-encoder push-to-mute.

Navigation, Home, Back, and playback controls remain pending.

### 11.5 Rotary volume control

The operational encoder is a Bourns PEC11R-4215F-S0024.

Its A/B signals use GP8/GP9.

Its independent pushbutton uses GP10 and GND.

Rotation generates `volume-up` or `volume-down`.

Pressing the shaft generates `mute-toggle`.

Both actions pass through the selected room and the shared Dumb Queue™.

The encoder driver does not know whether the destination is Denon or Roku.

### 11.6 Two-room verification

| Room | Volume transport | Mute transport | Observed result |
|---|---|---|---|
| Den | Denon TCP | Denon HTTP | Volume and mute/unmute operational |
| Sunroom | Roku ECP held-volume | Roku ECP generic HTTP | Volume and mute/unmute operational |

The Sunroom Roku controls receiver volume through the equipment's HDMI-CEC path.

Fast and sustained rotation tests demonstrated smooth practical volume response, with slight display lag and very small overshoot.

One transient Roku socket error was observed during earlier reversal testing. Subsequent tests recovered, and operation-specific diagnostics were added.

These results establish tested functionality, not indefinite fault-free operation.

### 11.7 Planned controls and feedback

Remaining hardware work includes:

- Second Bourns encoder for custom-action selection and execution.
- Navigation cluster.
- Home and Back.
- Playback controls.
- OLED display.
- Audible feedback.
- Final enclosure and wiring.
- Battery, charging, sleep, and wake behavior.

The second encoder should reuse the quadrature driver and shared action dispatcher.

The final faceplate and enclosure remain design and construction work, not completed production hardware.

See [Hardware & Physical Controls](HARDWARE_CONTROLS.md).

---

## 12. Future expansion boundaries

### 12.1 Custom destinations

Config v4 currently provides three generic built-in destinations per room.

Additional user-defined destinations are a future extension.

A possible design would store them in a separate optional per-room collection.

Their identity, schema, migration, deletion, and action-reference behavior must be designed before implementation.

A destination has identity and connection information.

Behavior belongs to actions.

Never silently retarget actions when a destination changes.

### 12.2 Apple TV compatibility

Apple TV compatibility is an explicit objective, not an implemented feature.

Discovery, pairing, authentication, session management, and protocol-specific command handling may be required.

The existing generic HTTP, Denon TCP, and Roku ECP adapters do not provide Apple TV pairing or authenticated sessions.

Generic action intentions such as Home, Back, navigation, and Play/Pause should remain independent of device brands.

Do not add a speculative `apple_tv.py` module before concrete requirements and tests justify it.

### 12.3 Clonker Recipe Library

**Status:** Conceptual.

A future recipe library could provide downloadable configuration examples for equipment combinations and named action sequences.

Recipes might be retrieved and loaded into the editor for review before an explicit Save.

They must not bypass schema validation, revision protection, or persistence safeguards.

**Recipes help configure the Clonker; they do not become a runtime dependency.**

---

## 13. Clock, diagnostics, and verification discipline

Browser synchronization supplies a UTC reference for readable timestamps.

Queue deadlines, custom-action waits, Denon pacing, and Roku hold timing use `time.monotonic()`.

Wall-clock adjustments must not shift scheduling deadlines.

Automated NTP synchronization is not established by the current tested baseline.

### 13.1 Evidence vocabulary

Use the following distinctions:

| Term | Meaning |
|---|---|
| Implemented and verified | Observed within a specified test scope |
| Implemented, not exhaustively tested | Working code with remaining untested conditions |
| Planned | Future design or requirement |
| Historical | Earlier implementation superseded by current code |

A commit proves source changed.

Deployment proves files were copied.

HTTP 200 proves a transport acknowledgment.

A successful TCP write proves bytes were handed to the network stack.

Equipment observation supports a physical-behavior claim.

These are different evidence levels.

### 13.2 Development discipline

- Preserve known-good configuration.
- Change one meaningful component at a time.
- Test hardware independently before integration.
- Keep optional inputs optional.
- Record network errors with enough context to diagnose them.
- Avoid unnecessary high-volume serial logging.
- Keep dated experiments in Development History.
- Avoid adding abstractions without a demonstrated need.

---

## 14. Historical architectural milestones

| Milestone | Architectural result |
|---|---|
| XML v1 | Early browser editing and persistence concepts; historical |
| Config v2 | JSON validation, revisions, verified writes, backup rotation |
| Dumb Queue™, October 20 | Bounded admission, eligible-task scheduling, failure cancellation |
| Outbound HTTP, October 21 | Real Denon/Roku GET/POST execution |
| Config v3, October 22 | Stable generic built-in device IDs |
| Config v4, October 2026 | Named custom actions and cooperative ordered steps |
| Chapter 4, October 27 | Verified custom actions, toggles, and interleaving |
| Chapter 5, October 28 | GPIO scheduler foundation and HTTP pacing correction |
| Chapter 5, October 29 | GP17/GP18 modes and GP2 input events verified |
| Chapter 5 closeout, October 31 | Three-position room selector standalone test |
| Chapter 6, November 2 | Physical room selection and shared dispatch operational |
| Chapter 6, November 2 | Power Toggle verified in both rooms; Room 3 safe no-op |
| Chapter 6, November 3 | Bourns physical volume encoder operational |
| Chapter 6, November 3 | Signature-based adapter selection and cache |
| Chapter 6, November 3 | Persistent Denon TCP volume and queue pacing verified |
| Chapter 6, November 3 | Roku ECP held-volume adapter operational |
| Chapter 6, November 3 | Mixed-room volume and physical push-to-mute verified |

The architectural result of Chapter 6 is a working physical control path that can use multiple device protocols without changing the action model or adding another command queue.

---

## 15. Design principles worth remembering

**Less sleek. More CLONK.**

**Smart enough to know when to be dumb.**

**Be resilient in our dumbness.**

**One queue. One poller. One shared execution path.**

**Hardware detects events. Physical coordination maps intent. Actions execute commands.**

**A future task must not hold an immediate button press hostage.**

**One failed external command cancels pending work, not the remote itself.**

**Clonker sends commands. Equipment owns state.**

**A command sequence is not permission to invent a workflow engine.**

**Configuration describes the destination. Actions describe the intention. Transport delivers the message.**

**Do not silently control another room when the selected room is unavailable.**

**A protocol adapter is not permission to invent another action queue.**

> **Do not make the Clonker more complicated merely because we are capable of making it more complicated.**

---

## 16. Reference documents

- [Configuration & Recovery](CONFIGURATION.md) — schema, validation, revisions, persistence, recovery.
- [Firmware, Network & Clock](FIRMWARE_NETWORK.md) — scheduler details, adapters, transports, diagnostics.
- [Operating Modes](OPERATING_MODES.md) — GP17 and GP18 behavior.
- [Hardware & Physical Controls](HARDWARE_CONTROLS.md) — GPIO assignments, components, mechanical plans.
- [Development & Deployment](DEVELOPMENT.md) — deployment workflow and regression tests.
- [Development History](DEVELOPMENT_HISTORY.md) — chronological engineering milestones.
- [Chapter 2 Handoff](CHAPTER_2_HANDOFF.md) — historical reference.
- [Old Architecture](OLD_ARCHITECTURE.md) — historical reference.
- [`samples/device_config_roku_denon_sample.json`](../samples/device_config_roku_denon_sample.json) — readable configuration example.

---

**THE CLONKER 10000**  
*Less sleek. More CLONK.*  
**CLONK! ⚡🔩**
