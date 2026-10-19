
# The Clonker 10000 — Architecture

**Design reference · updated 19 October 2026**  
**Active target:** Raspberry Pi Pico 2 W / CircuitPython 10.3.1  
**Repository:** [djacobson/clonker-10000](https://github.com/djacobson/clonker-10000)  
**Milestone:** Browser Test Remote and logging-only dispatcher tested; real outbound device control is next.

> **Clonker controls actions, not brands. Controlled devices own their own state.**

## Mission

The Clonker 10000 is a tactile, Wi-Fi-first home theater remote with physical knobs, switches, satisfying buttons, and eventually an audible **CLONK!** Its controls express generic actions; room configuration maps those actions to devices and commands. The design is intentionally small and understandable on a microcontroller.

The receiver, television, and streaming device remain authoritative for their actual state. Clonker must not invent an equipment-state model. One deliberately limited V1 feature is planned: **RAM history of the last successfully sent ON/OFF command** for each room's mute and power actions. That history is *not* a measurement of actual device state.

**Design priority:** responsive physical controls → reliable device commands → maintained room selection → configuration interface → diagnostics/time → OLED and sound → battery optimization. The browser configuration interface was implemented early to establish and test the action model before hardware controls.

## Architecture at a glance

```text
       BROWSER TEST REMOTE             PHYSICAL CONTROLS
       [IMPLEMENTED / TESTED]               [PLANNED]
                 |                              |
                 v                              v
          HTTP /api/action                GPIO EVENTS
                 |                              |
                 +--------------+---------------+
                                |
                                v
                     GENERIC ROOM / ACTION
                                |
                                v
                       actions.dispatch()
                       [LOGGING STUB TESTED]
                                |
                                v
                      JSON v2 CONFIGURATION
                          [IMPLEMENTED]
                                |
                                v
                      OUTBOUND HTTP TRANSPORT
                            [PLANNED]
                                |
                                v
                       DENON / ROKU / LG


       CONFIG MANAGEMENT SERVICES [IMPLEMENTED]
       ----------------------------------------
       HTTP :9090
         |-- Configuration editor
         |-- Clock status / synchronization
         |-- Browser Test Remote
         +-- JSON configuration persistence
```

The browser and eventual physical controls must use **the same dispatcher**, not separate device-control implementations. Device-specific IP addresses, methods, and command paths belong in JSON v2 configuration. The transport handles networking, not room policy or toggle direction.

## Implementation status — October 19, 2026

### Implemented and verified on the physical Pico

- Pico 2 W boot and Wi-Fi connectivity, serial diagnostics, and GP17 filesystem ownership modes.
- JSON v2 three-room configuration loaded into validated RAM state.
- Configuration editor and browser clock synchronization via HTTP port 9090.
- Revision-aware JSON saves, no-change handling, backup rotation, and stale-tab revision conflict rejection in the exercised scenarios.
- Browser Test Remote at `/remote.html` with the fourteen fundamental action buttons.
- POST `/api/action?room=room-1&action=volume-up` (and other valid room/action combinations) routed to `actions.dispatch()`.
- Dispatcher room/action validation, current-config lookup, and **logging-only** JSON response. User exercised the fourteen fundamental button actions; **no outbound AV command was sent**.
- Side-by-side clock and Test Remote panels on the configuration page, matching attribution, and responsive browser presentation.

### Implemented, with remaining edge-case verification

- Strict JSON v2 validation, expected-revision persistence, disk-vs-RAM change detection, verified temporary writes, and startup loading from validated backup generations.
- Bounded cooperative inbound HTTP service. Its implementation limits request size and handles one client at a time, but real-world scheduling guarantees have not been established.

Consult [configuration-testing.md](configuration-testing.md) for the dated, specific tests. Interrupted writes, power-loss behavior, malformed HTTP coverage, and remaining failure-injection cases must **not** be described as passed without new evidence. Backup rotation is not a power-loss-atomic transaction.

### Not yet implemented

- Real outbound HTTP GET/POST commands to Denon, Roku, or LG.
- RAM toggle-command history and ON/OFF selection in `actions.py`.
- Physical CONFIG/RUN switch, room selector, buttons, and encoders.
- GPIO debounce, event handling, physical-control latency measurements.
- User-defined custom action execution, macros, equipment-state queries.
- OLED, audible feedback, battery management, and enclosure integration.

**Next development milestone:** Make one safe, configured HTTP command work from the existing browser Test Remote, then expand ordinary actions and add the agreed toggle behavior. Physical controls follow once the command path is reliable.

## Current firmware map

| File | Responsibility |
|---|---|
| `firmware/boot.py` | GP17-selected USB/Pico filesystem ownership at boot |
| `firmware/code.py` | CircuitPython application entry point |
| `firmware/clonker/main.py` | Startup configuration, Wi-Fi/runtime initialization, cooperative loop |
| `firmware/clonker/controls/switches.py` | Simulated CONFIG switch; future GPIO switch handling |
| `firmware/clonker/controls/pins.py` | Physical switch pin definitions |
| `firmware/clonker/device_config_v2.py` | Active JSON v2 schema, validation, RAM snapshot, revisions, persistence and backup loading |
| `firmware/clonker/device_config.json` | Example/checked-in compact JSON v2 configuration; deployed Pico data may differ |
| `firmware/clonker/actions.py` | Shared fundamental action dispatcher, currently logging-only |
| `firmware/clonker/web.py` | Cooperative inbound CONFIG HTTP service on port 9090 |
| `firmware/clonker/www/index.html` | Browser configuration and clock interface |
| `firmware/clonker/www/remote.html` | Browser Test Remote, fundamental action requests |
| `firmware/clonker/clock.py` | Monotonic and browser-synchronized clock |
| `firmware/clonker/logger.py` | Serial logging |
| `firmware/clonker/legacy/device_config.py` | Historical XML v1 configuration engine; not active |
| `firmware/clonker/legacy/device_config.xml` | Historical XML v1 configuration example |

An outbound transport module has **not** been selected or implemented. Do not document a proposed filename as if it already exists.

## Two independent mode dimensions

### SERVICE (USB) / DEVICE — filesystem ownership

Selected at **boot** by GP17, not by the browser or the future CONFIG switch:

- **SERVICE:** GP17 open; host computer can write CIRCUITPY, firmware cannot persist configuration to the filesystem.
- **DEVICE:** GP17 grounded; Pico can persist configuration, USB host sees the drive read-only.
- Changing this mode requires a **full power cycle**.

### CONFIG / RUN — application behavior

This is an independent runtime switch concept:

- **CONFIG:** management HTTP listener and browser tools available.
- **RUN:** management listener stopped; device actions must continue to operate.
- Physical maintained CONFIG/RUN switch is **not yet wired**; firmware currently simulates CONFIG enabled.
- A future CONFIG/RUN transition should not require a reboot or reload of the validated configuration.

Do not confuse **DEVICE** (filesystem-writable Pico mode) with **RUN** (normal remote-control application behavior). See [OPERATING_MODES.md](OPERATING_MODES.md) and [DEVELOPMENT.md](DEVELOPMENT.md).

## State ownership and active configuration

The active firmware uses `/clonker/device_config.json` and `device_config_v2.py`, not XML v1. JSON v2 defines three fixed room IDs (`room-1`, `room-2`, `room-3`), three optional endpoints per room (`tv`, `avr`, `streaming`), and fourteen fundamental action IDs per room. A reserved `custom_actions` list is currently empty and unsupported for execution.

The configuration module maintains one authoritative validated snapshot in its private `_current` dictionary:

- `load()` selects the primary or a validated backup at startup.
- `current()` returns a validated copy.
- `room(room_id)` returns a current room configuration.
- `save()` validates and persists before publishing the new `_current` value.
- A failed save does not publish the proposed configuration.
- An unchanged save does not rotate files.
- The dispatcher already uses `device_config.room(room_id)` to resolve actions, so it sees successful browser edits without restarting.

A second configuration cache or synchronization manager is unnecessary for V1. `room()` currently copies/validates through `current()`; optimize only if encoder measurements justify a narrower read-only lookup. Do not weaken persistence safeguards just to improve dispatch speed.

Manual edits to Pico files outside the configuration engine are not automatically adopted into RAM. CONFIG-to-RUN transitions should preserve the loaded configuration.

### Device endpoints and action mappings

Each action selects a target device category and HTTP method. Twelve ordinary actions use a single `path`; `mute-toggle` and `power-toggle` use `on_path` and `off_path` with one common target and method. Blank endpoint or command means no outbound request. The configuration schema already supports both toggle paths; **choosing between them is still planned**.

The fourteen fixed IDs are:

```text
volume-up       volume-down      mute-toggle
nav-up          nav-down         nav-left
nav-right       select           back
home            play-pause       skip-back
skip-forward    power-toggle
```

Current development endpoints and example command patterns are described in [CHAPTER_2_HANDOFF.md](CHAPTER_2_HANDOFF.md). Verify the deployed Pico configuration before sending real commands; GitHub sample values are not proof of the active device state.

## Design constraints and scheduling

GPIO capture and command responsiveness must eventually outrank management HTTP traffic. The existing `web.poll()` processes bounded pieces of inbound work in the cooperative loop, approximately every 10 ms when CONFIG is enabled. **This is not a proven encoder-latency guarantee.**

Network operations must have bounded timeouts and release sockets on failures. A stalled receiver must not permanently prevent subsequent actions or hang the management interface. The precise outbound scheduling behavior is a design/testing decision for the next milestone; synchronous network work may still impose measurable latency even with a cooperative inbound server.

Management access is **trusted-LAN-only**, with no application authentication. Never expose port 9090 through internet port forwarding. CircuitPython Web Workflow is disabled in private `settings.toml` because of suspected socket conflicts; this is distinct from Clonker's own management server.

## Action dispatch and outbound HTTP — V1 design

**Design agreed:** October 17, 2026  
**Current status:** Room/action validation and logging stub implemented; outbound transport **not implemented**.

### Guiding principle

Start with the simplest reliable execution path. Avoid event accumulation, acceleration, elaborate queues, connection pooling, and general-purpose device frameworks until measurements reveal a need.

### Shared action pipeline

1. Browser remote (implemented) or physical input (future) produces a generic room/action request.
2. Shared dispatcher validates the room and action IDs.
3. Dispatcher reads the latest validated room configuration.
4. Dispatcher resolves target endpoint, HTTP method, and selected path.
5. Outbound transport sends one configured HTTP request (future).
6. Transport reports a bounded result and releases network resources.
7. Dispatcher returns status to the browser or future physical-input caller.

The first three steps are represented by the current logging-only stub. The stub's `ok: true` and `status: "stub"` mean **dispatch accepted**, not **AV command succeeded**.

### Inbound and outbound networking are separate

`web.py` is the inbound HTTP management server. Outbound AV commands are a separate responsibility. Both can use the same Wi-Fi radio, but must not share active client connection state.

Initial outbound design:

- Initialize and manage Wi-Fi centrally.
- Reuse a valid socket pool or equivalent shared networking resources where practical.
- Allow one TCP connection per command; persistent TCP connections are not required for V1.
- Support the configured GET and POST methods.
- Bound connection, send, and response-reading operations.
- Distinguish no-op, transport error, HTTP error, and success in results/logging.
- Close resources after success or failure; later actions must still be possible.
- Do not add automatic retries that could duplicate state-changing commands.

Exact module names and transport interfaces remain open pending source/library review and on-device testing.

### First real-command test sequence

1. Inspect `actions.py`, `web.py`, `main.py`, `device_config_v2.py`, and installed CircuitPython networking capabilities.
2. Agree on the minimal transport interface and error handling.
3. From the **working browser Test Remote in CONFIG mode**, trigger one low-risk Denon or Roku action; avoid power at first.
4. Confirm serial output, HTTP result, and observed equipment response.
5. Extend ordinary action dispatch; test missing endpoint/path as safe no-op.
6. Implement and test RAM toggle history only after ordinary commands work.
7. Later test outbound commands in RUN mode without the management listener, then integrate physical GPIO controls and measure responsiveness.

The earlier recommendation to begin with CONFIG disabled applied to future physical-control latency isolation. It is **not** the first real-command test procedure now that the browser Test Remote exists.

### Buttons and encoders

Physical controls must emit generic actions, never embed IP addresses or vendor command syntax:

- Button press → `select`, `home`, or `mute-toggle`.
- Grayhill volume encoder clockwise detent → `volume-up`.
- Grayhill volume encoder counterclockwise detent → `volume-down`.

For initial V1 behavior, one recognized event yields one action and (when configured) one HTTP request. No volume-specific transport, accumulation, acceleration, batching, retries, or persistent-connection optimization. This keeps encoder hardware and HTTP transport independently replaceable.

A small amount of lag during network trouble may be tolerable, but failed volume commands should **not** be replayed after connectivity returns. Fresh movement produces fresh actions. The Denon remains the authority for its volume level.

### Possible future optimization — only if measured

- Bounded event queue for short bursts.
- Encoder movement accumulation.
- Rotation-speed-dependent volume acceleration.
- Device-supported batching.
- Outbound HTTP connection reuse.
- Scheduling improvements under congestion.

Accumulation and acceleration are different features; neither is a V1 requirement. Avoid speculative complexity.

### Architectural boundaries

- `controls/`: read physical inputs and generate generic events.
- `actions.py`: resolve current room/action mapping, choose toggle direction, interpret transport result.
- Outbound transport (future): perform HTTP requests, manage sockets/timeouts/errors; no equipment-state assumptions.
- `device_config_v2.py`: schema, active validated config, revision control, persistence, recovery.
- `web.py`: inbound CONFIG-mode HTTP service and browser request routing.

**Ordinary V1 rule:** One control event → one generic action → at most one configured HTTP request.

## Fundamental toggle actions — V1 agreed design

**Design agreed:** October 18, 2026  
**Current status:** ON/OFF JSON fields implemented; direction-selection and command-history behavior **not implemented**.

### Scope and configuration

The fourteen fundamental action IDs do not change. Twelve actions have a single `path`. Two actions have paired paths:

- `power-toggle`
- `mute-toggle`

Each toggle has one target, one HTTP method, and both `on_path` and `off_path`. Identical paths are valid for a device with its own native toggle command.

### Per-room, per-action RAM command history

Conceptual startup state:

```text
room-1: power-toggle=unknown, mute-toggle=unknown
room-2: power-toggle=unknown, mute-toggle=unknown
room-3: power-toggle=unknown, mute-toggle=unknown
```

- On first press, attempt **ON**.
- After successful ON, the next press attempts OFF; after successful OFF, the next attempts ON.
- Missing endpoint, blank *selected* path, or failed request **does not advance** remembered direction.
- History is independent for every `(room_id, action_id)` pair.
- History is initialized in RAM and never written to flash.
- A successful HTTP exchange may justify recording the command sent; it does **not** prove the equipment actually changed state.

For native toggles, identical ON/OFF paths result in the same HTTP command on every press, while Clonker's internal direction still alternates after successful sends.

### Toggle dispatch sequence

```text
Generic room/action event
    -> validate and resolve current configuration
    -> read last successful command direction from RAM
    -> select next on_path or off_path
    -> if endpoint/path missing: no-op; history unchanged
    -> send exactly one HTTP request
    -> if successful: remember selected direction
    -> otherwise: retain previous history
```

The outbound transport does not own toggle state and must not include Denon/Roku-specific power logic. The physical controls remain unaware of toggle semantics beyond emitting `power-toggle` or `mute-toggle`.

### Accepted limitation: no equipment-state polling

V1 deliberately does not query real power or mute state before choosing ON/OFF. Other remotes, HDMI-CEC, and apps can change equipment state without Clonker knowing. A second press may be needed to recover from divergence. State-aware adapters or queries may be considered later, only if real use justifies them.

### Configuration access and scope discipline

The dispatcher must use the current validated configuration, not a stale copy captured at startup. A targeted immutable read-only lookup can be considered if performance measurements justify it; that would not be a second cache.

Do **not** add a general macro engine, sequence framework, persistent state model, polling parser, retry queue, or complex device-specific power framework for V1.

**Toggle V1 rule:** One event → choose one ON/OFF path → at most one HTTP request → update RAM history only on success.

## Reference documents

- [Chapter 2 Handoff](CHAPTER_2_HANDOFF.md) — verified milestone and next steps.
- [Operating Modes](OPERATING_MODES.md) — SERVICE/DEVICE and CONFIG/RUN.
- [Configuration & Recovery](CONFIGURATION.md) — JSON v2 schema and persistence safeguards.
- [Firmware & Network](FIRMWARE_NETWORK.md) — cooperative loop, inbound HTTP, clock and logging.
- [Hardware & Controls](HARDWARE_CONTROLS.md) — physical design and input plans.
- [Development & Deployment](DEVELOPMENT.md) — iPad/Windows/Pico workflow.
- [Configuration Testing](configuration-testing.md) — dated verification record.
- [Terminology Audit](TERMINOLOGY_AUDIT.md) — historical terminology reconciliation.
- [Old Architecture](OLD_ARCHITECTURE.md) — historical reference, not active implementation.

---

**CLONK! ⚡🔩**
