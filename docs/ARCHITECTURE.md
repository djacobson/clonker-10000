# The Clonker 10000 — System Architecture

**Design reference:** Updated October 27, 2026  
**Active platform:** Raspberry Pi Pico 2 W / CircuitPython 10.3.1  
**Repository:** [djacobson/clonker-10000](https://github.com/djacobson/clonker-10000)  
**Current milestone:** Chapter 4 — Clonker Config v4, executable custom actions, and cooperative compound execution operational  
**Next direction:** Close small Chapter 4 refinements, then advance physical controls and remaining action behavior without prematurely implementing custom devices or new protocols.

> **Clonker controls actions, not brands. Controlled devices own their own state.**

---

## 1. Mission

The Clonker 10000 is a tactile, Wi-Fi-first home-theater remote: substantial knobs, satisfying switches, guarded power controls, and eventually an audible **CLONK!**

Its job is to turn user intentions into configured equipment commands. It is not intended to become a universal home-automation server, a comprehensive equipment-state tracker, or a general-purpose workflow engine.

The essential sequence is:

1. Recognize an action.
2. Identify the selected room.
3. Resolve the configured command and destination.
4. Admit the action to the shared queue.
5. Execute eligible work.
6. Report the outcome.
7. Get out of the way.

External equipment remains authoritative for its actual state. The Clonker does not pretend to know every power, volume, input, playback, or HDMI-CEC change made outside its own commands.

### 1.1 Guiding philosophy

**Be resilient in our dumbness.**

The system should be responsive, predictable, recoverable, small enough to understand, and straightforward to test incrementally.

**One queue. One poller. One shared execution path.**

The architecture favors explicit responsibilities and simple interfaces over abstractions that merely look extensible.

### 1.2 Development priorities

1. Preserve the working configuration and action pipeline.
2. Keep fundamental actions lightweight.
3. Support practical multi-step commands without a separate macro engine.
4. Introduce physical controls with measured responsiveness.
5. Add protocol and device flexibility when real hardware requirements justify it.
6. Preserve a clear distinction between implemented behavior, tested behavior, and future design.

---

## 2. Architecture at a Glance

```text
                  THE CLONKER 10000

          BROWSER TEST REMOTE       PHYSICAL INPUTS
             IMPLEMENTED              PLANNED
                   |                      |
                   v                      v
              /api/action             GPIO EVENTS
                   |                      |
                   +-----------+----------+
                               |
                               v
                         actions.dispatch()
                      Validate and enqueue
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
                     Fundamental: one step
                     Custom: ordered steps
                     Toggles: deferred
                               |
                               v
                       HTTP GET / POST
                               |
                               v
                         DENON / ROKU
                               |
                               v
                     EXTERNAL EQUIPMENT

                 CONFIGURATION MANAGEMENT

                Browser editor / port 9090
                               |
                               v
                     Strict v4 validation
                               |
                               v
                     Revision protection
                               |
                               v
                    Verified file persistence
                               |
                               v
                     Active RAM snapshot
                    (queue cleared on change)
```

The browser action path, shared queue, custom-action steps, and outbound HTTP transport are implemented. Physical GPIO-driven action dispatch is not yet implemented.

### 2.1 Architectural invariants

- Input sources express generic actions rather than device-specific URLs.
- Configuration owns destinations and command definitions.
- The action dispatcher owns acceptance, scheduling, sequencing, and execution policy.
- The transport owns outbound HTTP operations, not action meaning.
- The browser editor is a configuration client, not the runtime source of truth.
- A single validated configuration snapshot is authoritative in RAM.
- A successful changed save clears pending queued work.
- Failed external commands are not automatically retried.
- External devices own their actual state.
- Future protocols may require adapters; generic actions must not assume all equipment speaks HTTP.

---

## 3. Current Implementation Status

**Status reference: October 27, 2026.** This section is the current-state summary. Historical design proposals elsewhere should not override it.

### 3.1 Implemented and tested

- Raspberry Pi Pico 2 W running CircuitPython 10.3.1, with Wi-Fi and serial diagnostics.
- GP17-selected SERVICE/DEVICE filesystem ownership.
- Clonker Config v4 in JSON, with strict validation and an active RAM snapshot.
- One to three supported room IDs, with Den and Sunroom currently configured.
- Three generic built-in device slots per configured room.
- Fourteen fixed fundamental actions per room.
- Up to sixteen custom actions per room, with stable IDs, editable names, and one to sixteen ordered steps.
- GET/POST commands and `wait_after_ms` cooperative post-command delays.
- Browser configuration editor and room-specific custom-action Test Remote controls.
- Revision-protected saves, verified temporary writes, backup rotation, and reboot persistence.
- Shared Dumb Queue™, eligible-task scheduling, bounded capacity, and queue-wide failure cancellation.
- Outbound HTTP commands to real Denon and Roku devices.
- A real two-command Sunroom custom-action sequence: Roku Home, three-second cooperative wait, then Denon Quick Select 1; both commands returned HTTP 200 and the custom action completed.
- Den and Sunroom configurations containing multiple named custom actions.

### 3.2 Implemented but not exhaustively tested

- Recovery across every possible interrupted-write or power-loss point.
- Extended network-failure and timeout behavior under sustained traffic.
- Malformed or fragmented inbound HTTP requests beyond exercised cases.
- Long-uptime scheduling and monotonic-clock edge cases.
- Interleaving of rapid physical encoder input during custom-action waits.
- Physical input capture during a blocking outbound HTTP request.

An HTTP 200 response confirms an HTTP result, **not** the equipment's actual resulting state. Source inspection and browser success messages are not substitutes for physical tests.

### 3.3 Not yet implemented

- Runtime power/mute toggle direction selection and volatile direction history.
- User-defined custom device destinations (`device-4` onward).
- Physical buttons and encoders connected to the dispatcher.
- Physical CONFIG/RUN and room selectors.
- OLED status display and audible feedback.
- Battery management and sleep/wake behavior.
- Apple TV protocol integration, pairing, or authentication.
- General scripting, nested custom actions, conditional branching, or equipment-state reconciliation.

### 3.4 Immediate development direction

Chapter 4 established the generic device slots and operational Config v4 custom actions. The next phase should protect this baseline, address small proven UI/runtime gaps, and progress toward tactile controls. Custom devices and Apple TV remain explicit objectives, not prerequisites for initial physical control work.

---

## 4. Firmware Component Map

| Component | Responsibility |
|---|---|
| `firmware/boot.py` | GP17-selected filesystem ownership at boot |
| `firmware/code.py` | CircuitPython entry point |
| `firmware/clonker/main.py` | Startup and cooperative service scheduling |
| `firmware/clonker/device_config_v2.py` | Config v4 validation, RAM snapshot, revision, persistence, and recovery |
| `firmware/clonker/device_config.json` | Device-side operational configuration |
| `firmware/clonker/actions.py` | Fundamental/custom dispatch, shared queue, step execution, failure policy |
| `firmware/clonker/net/http_transport.py` | Bounded, synchronous outbound HTTP GET/POST |
| `firmware/clonker/net/web.py` | Inbound management HTTP server and action/config APIs |
| `firmware/clonker/www/index.html` | Browser configuration editor |
| `firmware/clonker/www/remote.html` | Browser Test Remote |
| `firmware/clonker/controls/switches.py` | Current simulated application mode; future switches |
| `firmware/clonker/controls/pins.py` | GPIO assignments |
| `firmware/clonker/system/clock.py` | Clock services |
| `firmware/clonker/system/logger.py` | Serial diagnostics |
| `firmware/clonker/legacy/` | Historical XML implementation |

The filename `device_config_v2.py` is historical. **Its active schema constant is `CONFIG_VERSION = 4`.** Renaming the module offers no functional benefit at present.

The configuration, dispatcher, management service, and transport should remain independently understandable and testable.

---

## 5. Operating Modes

Clonker has **two independent mode dimensions**.

### 5.1 SERVICE / DEVICE — filesystem ownership

GP17 selects filesystem ownership at boot:

| Mode | GP17 | Writable filesystem owner |
|---|---|---|
| SERVICE | Open | USB host |
| DEVICE | Grounded | Pico firmware |

Changing filesystem ownership requires a full power cycle; a soft reload is not a reliable substitute.

### 5.2 CONFIG / RUN — application behavior

In **CONFIG**, the management HTTP listener, browser editor, Test Remote, and clock synchronization are available. The action queue continues operating.

In **RUN**, the management listener stops; the loaded configuration and action queue continue operating. Future physical controls must work independently of the browser.

The physical CONFIG/RUN switch has not yet been wired; development currently uses a simulated mode input.

### 5.3 Independent consequences

An accessible configuration editor does not imply that the Pico owns a writable filesystem. Save permission depends on actual filesystem ownership. The browser and server must report and enforce that distinction.

See [Operating Modes](OPERATING_MODES.md).

---

## 6. Configuration Architecture

### 6.1 Versioned schema, JSON storage

The active configuration schema is **Clonker Config v4**. JSON is its storage format, not its product name. The root has `"version": 4` and a `rooms` object.

A room has a stable ID (`room-1` through `room-3`), an editable display name, built-in devices, fundamental actions, and a `custom_actions` array.

The full schema, field validation, size limits, sample, and recovery procedures belong in [Configuration & Recovery](CONFIGURATION.md). This document focuses on component boundaries and behavior.

### 6.2 Stable rooms and generic destinations

Configured rooms are an optional nonempty subset of the three supported IDs. The browser currently renders configured rooms; it does not yet provide general add/remove room controls.

Built-in destination IDs are stable:

| ID | Browser label |
|---|---|
| `device-1` | TV |
| `device-2` | AVR |
| `device-3` | Streaming |

The labels are conveniences, not enforced equipment types. Endpoints and action mappings determine behavior. Renaming a room does not change its identity.

### 6.3 One authoritative RAM snapshot

Startup loads and validates the configuration. Runtime actions resolve against the active in-memory configuration, not repeated JSON file reads.

The browser reads a copy with response-only metadata, including the revision and filesystem-writability state. Those metadata fields are not persisted as schema fields.

### 6.4 Save and recovery boundaries

The configuration engine validates, serializes, verifies temporary writes, manages backups, and publishes a new active configuration. A save is revision-protected to reject stale browser tabs. A changed save clears queued actions through the management server.

Backup rotation reduces risk but is not a fully atomic multi-file transaction against sudden power loss. Recovery requires a schema-compatible backup. The Pico's working filesystem is not automatically synchronized with GitHub.

### 6.5 Why configuration is separate from actions

Configuration says **where and how** a command should be sent. An action says **what the user wants**. The dispatcher decides **when** work is eligible. The transport performs the HTTP exchange.

This separation makes the physical interface independent of particular Denon or Roku URLs and leaves room for future protocol-specific adapters.

---

## 7. Fundamental Action Model

Each configured room contains fourteen fixed fundamental action IDs. Their identities remain stable even when their targets and command paths change.

### 7.1 Ordinary actions

Ordinary actions carry a destination, HTTP method, and command path. The dispatcher queues a compact task and resolves the current command when it executes.

A blank endpoint or path is a safe fundamental-action no-op rather than an attempted request. An HTTP success response is diagnostic, not proof of equipment state.

### 7.2 Power and mute toggles

`power-toggle` and `mute-toggle` store one target and method plus separate `on_path` and `off_path`. The schema and browser editor support both directions.

**Runtime direction selection is not implemented.** The dispatcher currently logs a deferred toggle and does not send either configured ON or OFF path.

### 7.3 Physical mapping

Future buttons and encoders should generate action IDs and room context. GPIO handlers should not contain HTTP paths, device-brand assumptions, JSON parsing, or network requests.

---

## 8. The Dumb Queue™

**Status:** Implemented for both fundamental and custom actions.

**One queue. One poller. One shared execution path.** The queue lives in `firmware/clonker/actions.py` and has a capacity of **128 task entries**.

### 8.1 Admission and task representation

`actions.dispatch(room_id, action_id, delay_seconds=0)` validates the room and either a fixed fundamental ID or a saved custom-action ID. It checks capacity and appends a task.

Current tasks carry the room ID, action ID, kind (`fundamental` or `custom`), step index, and due time. A multi-step custom action occupies **one queue entry**, which is updated and requeued as its steps progress; the dispatcher does not enqueue all steps up front.

Conceptually:

```python
{
    "room": "room-2",
    "action": "movie",
    "kind": "custom",
    "step": 0,
    "due": 0,
}
```

The sample is illustrative; the saved custom-action ID must match an ID in the active configuration.

### 8.2 Eligibility and ordering

Due times use `time.monotonic()`. Zero means immediately eligible; a positive value is an absolute monotonic deadline.

Each `poll()` scans for the **first eligible task**, removes it, and processes at most **one HTTP command or eligible no-op/deferred action**. A future-dated task does not block an immediately eligible task behind it. Among currently eligible tasks, queue order matters.

This is intentionally **not strict FIFO**.

> **A future task must not hold an immediate button press hostage.**

### 8.3 Fundamental execution

A fundamental task resolves its current configuration at execution time. An ordinary configured command is sent through the HTTP transport. A blank ordinary command becomes a no-op. Toggle actions currently return a deferred diagnostic without transmission.

### 8.4 Custom-step execution

A custom task resolves the saved action and its current step. It resolves the step destination and sends one HTTP request.

If more steps remain, the task's step index advances and its next due time is calculated **after the previous HTTP request completes**, using that step's `wait_after_ms`. The task is appended back to the shared queue.

Other eligible tasks may run while this custom task is waiting. There is no second executor, blocking sleep for the post-command wait, nested dispatch, or separate macro thread.

A custom step with an unconfigured destination is an execution failure, unlike the ordinary fundamental no-op rule.

### 8.5 Capacity and diagnostics

Capacity applies to queued task entries, not to the total number of steps represented by those entries. Admission rejects new tasks when the queue is full; it does not evict valid tasks to make room.

Diagnostics expose current depth, peak depth, capacity, last result, and last error.

### 8.6 Configuration consistency

Queued tasks retain identifiers, not copies of HTTP command definitions. Commands resolve against the active configuration at execution time. A successful changed configuration save clears pending work so old intentions are not silently redirected by a new configuration.

---

## 9. Failure Policy

**One failed external command cancels pending work, not the remote itself.**

The dispatcher catches execution errors, records a diagnostic, and discards remaining queued tasks. There is no automatic retry, rollback, or equipment-state reconciliation.

A failure within a custom action prevents its remaining steps from executing. The system remains available to accept new work afterward.

An unconfigured ordinary fundamental action is a safe no-op; an unconfigured custom destination is a failure. These are deliberate, different policies.

### 9.1 Why queue-wide cancellation

After a network or command failure, subsequent queued steps may no longer make sense. Continuing blindly can produce a confusing partial sequence. Clearing the queue favors predictable recovery over speculative completion.

### 9.2 What is not guaranteed

HTTP completion does not guarantee the intended equipment behavior. The Clonker does not verify input selection, volume, power, playback, or HDMI-CEC state after a command. More sophisticated state-aware behavior would require explicit future design.

---

## 10. Cooperative Scheduling and Network Blocking

The main loop polls the action dispatcher and, in CONFIG mode, the inbound management server.

Current development intervals in `main.py` are:

| Setting | Value |
|---|---:|
| Action polling | 0.01 seconds |
| Management HTTP polling | 0.01 seconds |
| Main-loop idle sleep | 0.001 seconds |

These are polling settings, **not guaranteed response latencies**.

### 10.1 Cooperative work

Each service should do bounded work and return. The queue does not sleep until a future deadline; a delayed custom step is requeued with a due time. This allows other eligible actions and the management server to make progress between requests.

### 10.2 Important limitation: outbound HTTP is synchronous

The outbound transport performs a bounded **blocking** HTTP request. While it is in progress, the cooperative main loop cannot service other Python-level tasks. The queue does not magically make network I/O asynchronous.

That distinction matters for rapid rotary encoders. Hardware event capture and any required buffering must be measured on the actual Pico before selecting a more complex solution.

### 10.3 Required responsiveness tests

- Repeated volume commands during normal Denon/Roku traffic.
- Encoder rotation while an outbound HTTP request is in progress.
- Independent action interleaving during a custom-action wait.
- Queue behavior near capacity.
- Endpoint timeout and queue cancellation.
- Long-running monotonic scheduling.

The successful Roku/Denon compound-action test confirms sequential execution and a cooperative wait; it does **not** yet establish physical encoder responsiveness under load.

---

## 11. Volume Encoder Strategy

The initial physical volume implementation should generate ordinary repeated `volume-up` and `volume-down` actions, using the existing dispatcher and queue. It should not introduce a second networking path.

Possible later optimizations include acceleration, coalescing, and bounded accumulation, but these should be driven by measured event loss, latency, or equipment behavior.

The Grayhill volume encoder is part of the planned hardware audition. Electrical behavior, contact bounce, and CircuitPython event capture still require bench testing.

**First make it correct. Then make it feel good. Then optimize only what needs optimizing.**

---

## 12. Toggle Actions and Command History

The agreed initial direction-selection design uses small **volatile command history**, independently for each room and each toggle action.

Proposed initial rules:

1. Unknown history initially selects ON.
2. A successful ON submission makes OFF the next direction.
3. A successful OFF submission makes ON the next direction.
4. Failed, blank, or unconfigured requests do not advance history.
5. History is not persisted; reboot resets it to unknown.

This would track the direction of Clonker commands, **not the equipment's actual state**. Other remotes, HDMI-CEC, apps, and physical controls may change state without Clonker knowing.

**Status:** Agreed future behavior only. The runtime currently defers toggle execution. Do not describe the rules above as implemented.

---

## 13. Custom Devices — Agreed Future Extension

**Status:** Planned, not implemented in Clonker Config v4.

The existing built-in destination IDs remain stable. Additional user-defined destinations are envisioned as `device-4`, `device-5`, and so on, with stable IDs, editable names, and validated endpoints.

The agreed conceptual location is an optional per-room `custom_devices` collection, separate from the existing `devices` object. This preserves the current home-theater editor and avoids unnecessary migration of built-in device definitions.

### 13.1 Identity versus behavior

A destination has an identity, a name, and connection information. Actions contain behavior. Deleting or changing a destination must not silently retarget existing actions.

### 13.2 Scope discipline

Do not implement custom devices solely because the schema is extensible. First preserve the working fundamental/custom action pipeline, then add a concrete custom-device requirement and test it end to end.

**KISS principle:** A destination has an identity and an address. Behavior belongs to actions, not device definitions.

---

## 14. Custom and Compound Actions

**Status:** Implemented in Clonker Config v4 and tested with real Denon/Roku commands.

A custom action is a saved, named action containing one or more ordered command steps. A multi-step custom action is a compound action. The same shared dispatcher and queue execute both fundamentals and custom actions.

### 14.1 Saved structure

Each custom action has a stable `id`, editable `name`, and ordered `steps` array. Each step has:

- `target` — currently one of the three built-in destination IDs.
- `method` — GET or POST.
- `path` — outbound command path.
- `wait_after_ms` — cooperative wait after the command completes.

The validator supports up to sixteen custom actions per room, with one to sixteen steps each. The final step must have a zero wait. Detailed field and size limits belong in [Configuration & Recovery](CONFIGURATION.md).

### 14.2 Execution lifecycle

1. A browser or future physical input dispatches a stable custom-action ID.
2. The dispatcher validates the action and queues one custom task.
3. The poller selects an eligible task.
4. The current step resolves its destination and command.
5. One outbound HTTP request executes.
6. If another step remains, the task advances and is requeued after its post-command wait.
7. After the last successful step, the dispatcher logs `CUSTOM COMPLETE`.

The wait begins **after the preceding HTTP request completes**, not when the overall action was first queued. Actual successor execution can occur later than the requested interval because the scheduler and transport are cooperative.

### 14.3 Interleaving and dependencies

A later step depends on the successful completion of its predecessor and the expiration of that predecessor's wait. The current implementation represents this dependency using a single advancing task, **not** a general-purpose dependency graph.

During a wait, independent eligible tasks may run. A custom action does not own an exclusive queue lock.

### 14.4 Failure and capacity

A failed custom step invokes the queue-wide failure policy. Remaining steps and other pending work are discarded; no automatic retry or rollback occurs.

Because one custom action occupies one queue entry, acceptance is bounded by the normal 128-entry queue capacity. The implementation does not reserve one entry per step.

### 14.5 Verified equipment test

The Sunroom test executed:

```text
Roku:  POST /keypress/Home                -> HTTP 200
       cooperative wait: 3000 ms
Denon: GET /goform/formiPhoneAppDirect.xml?MSQUICK1
                                             -> HTTP 200
CUSTOM COMPLETE
```

This establishes a working two-device, two-step custom-action path. It does not prove every device state change or every failure/interleaving scenario.

### 14.6 Browser configuration and testing

The browser editor can create, rename, edit, and remove custom actions and their steps. It validates and persists them through the same revision-protected configuration pipeline.

The Test Remote loads the saved custom actions for the selected room and exposes an explicit Run control. A minor deferred refinement is preserving the selected custom-action dropdown entry after dispatch.

### 14.7 Deliberate scope limits

The current engine does **not** provide loops, conditions, nested custom actions, arbitrary scripting, automatic retries, rollback, equipment-state queries, or a separate macro executor.

**A command sequence is not permission to invent a workflow engine.**

---

## 15. Outbound HTTP Transport

`firmware/clonker/net/http_transport.py` owns simple GET/POST communication with configured endpoints. It handles the network exchange and reports transport/HTTP diagnostics.

It does not know whether an action means Volume Up, Home, Movie, or Vinyl. It does not infer equipment state from HTTP responses.

Current testing covers real Denon and Roku endpoints. Authentication-heavy or persistent-session protocols may need different future adapters; they should not be forced through this simple transport merely to preserve an abstraction.

---

## 16. Inbound Management HTTP Service

`firmware/clonker/net/web.py` provides the CONFIG-mode browser/API service on port **9090**.

Its responsibilities include serving the editor and Test Remote, returning the active configuration with revision and filesystem metadata, accepting revision-protected configuration saves, handling browser clock synchronization, and dispatching browser action requests.

### 16.1 Relevant routes

| Route | Purpose |
|---|---|
| `GET /` | Browser interface / clock page |
| `GET /api/config` | Active configuration plus response-only metadata |
| `POST /api/config` | Validate and save a submitted configuration |
| `GET /remote.html` | Browser Test Remote |
| `POST /api/action?room=...&action=...` | Dispatch a fundamental or saved custom action |
| `GET /api/clock` | Clock status |
| `POST /api/clock?utc=...` | Browser clock synchronization |

The action API uses stable room/action IDs. It does not embed device-specific command paths in the URL.

### 16.2 Cooperative inbound handling

The server accepts and advances network operations incrementally through its `poll()` function. Request sizes and client timeouts are bounded. This prevents an idle browser connection from intentionally becoming a permanent service dependency.

Outbound HTTP requests remain synchronous, so inbound progress can still pause briefly while the dispatcher transmits.

### 16.3 Browser and filesystem boundaries

CONFIG mode exposes the editor, but persistence requires the Pico to own a writable filesystem. A stale revision must be rejected rather than silently overwriting newer changes. A changed save clears pending queue work.

The iPad browser is an important development client, not a separate configuration authority.

---

## 17. Physical Controls

The long-term identity of the Clonker is tactile: a substantial volume encoder, selector encoder, guarded SYSTEM MASTER control, satisfying buttons, room selection, a tiny OLED, and sound feedback.

Planned or auditioned hardware includes the Grayhill volume encoder, Bourns selector encoder, illuminated momentary switch, slide selector, SSD1306 OLED, piezo, I2S amplifier, and speaker options. Hardware inventory and pin assignments belong in [Hardware & Controls](HARDWARE_CONTROLS.md).

### 17.1 Input requirements

- Produce generic room/action events.
- Keep GPIO handlers free of HTTP and JSON logic.
- Debounce and buffer only as measurements require.
- Preserve useful tactile responsiveness during network activity.
- Allow safe behavior when a destination is unconfigured.
- Avoid letting browser CONFIG mode become a prerequisite for physical operation.

### 17.2 Guarded SYSTEM MASTER

The guarded control is a deliberate, prominent physical interface element. Its exact electrical behavior and semantics remain subject to hardware audition. Do not conflate the guard or illumination with implemented power-toggle state tracking.

---

## 18. Room Selection

Room IDs are stable configuration identities. The physical room selector should choose which room's action mappings apply without duplicating device-specific command logic.

Den and Sunroom are currently configured; a third room ID is supported. Physical room selection and simultaneous/multi-room behavior remain design work, not tested runtime capabilities.

A selector's mechanical positions, software representation, and any future BOTH behavior must be explicitly defined before implementation.

---

## 19. Clock and Timing

Wall-clock time supports display and diagnostics. Browser synchronization may update it.

Action scheduling uses `time.monotonic()` and is therefore independent of wall-clock corrections. Delayed tasks have **earliest eligible** times, not guaranteed precise execution timestamps.

For custom actions, post-command waits start after the previous HTTP request completes. Actual execution may be delayed by other eligible work, blocking HTTP operations, and scheduler timing.

---

## 20. Apple TV and Future Protocols

**Apple TV compatibility is an explicit future objective. It is not implemented.**

Generic intentions such as `nav-up`, `home`, `back`, and `play-pause` should remain independent of equipment brands. However, generic intentions do **not** imply generic wire protocols.

Apple TV may require discovery, pairing, authentication, session management, and protocol-specific command transmission. Those requirements must be investigated against a concrete implementation before introducing adapters or dependencies.

Do not force Apple TV into an unsuitable stateless HTTP GET/POST model. Equally, do not build speculative protocol infrastructure before there is a testable requirement.

No Apple TV protocol module is committed at this stage. The current Denon/Roku HTTP path remains the working baseline.

---

## 21. Security and Network Boundaries

The Clonker is a local-network device. The management interface and action API should be treated as trusted-LAN facilities, **not** as internet-facing services.

Current architecture does not provide a general authentication, authorization, TLS termination, or secure remote-access framework. Do not expose port 9090 directly to the public internet.

Future authenticated protocols must keep credentials and pairing/session handling out of generic action definitions where possible. Any security model change should be designed explicitly rather than inferred from the existence of a browser editor.

---

## 22. Development and Test Discipline

### 22.1 One meaningful change at a time

Preserve a working Pico baseline. Change one architectural concern, test it, document the result, then proceed. Do not simultaneously refactor configuration, transport, and physical input behavior without a compelling reason.

### 22.2 Browser-first functional tests

The browser Test Remote is a valuable bridge before physical hardware is wired. It exercises the real dispatcher and queue, not a separate simulation of command behavior.

Test both ordinary and custom actions against actual equipment where appropriate. Keep the distinction between HTTP success and equipment-state verification.

### 22.3 Configuration regression tests

Verify loading, editing, revision conflict rejection, valid and invalid saves, backup creation, restart persistence, and correct active room/action rendering. Preserve an external copy of a known-good configuration before risky changes.

### 22.4 Queue regression tests

Verify capacity rejection, eligibility ordering, future-task bypass, one eligible command per poll, failure cancellation, changed-save clearing, and normal operation after a failure.

### 22.5 Custom-action tests

Verify single- and multi-step sequences, wait-after-completion semantics, interleaving, missing destinations, network failures, final-step completion, and repeated runs. The verified Sunroom Roku/Denon sequence is the initial baseline, not exhaustive coverage.

### 22.6 Documentation and source discipline

Read current GitHub source before claiming implementation details. Read the latest documentation before editing it. Keep source code, live Pico tests, and historical intentions distinct.

Use exact current line numbers for targeted edits; prefer complete replacement only when extensive drift makes incremental patching more dangerous than rewriting.

---

## 23. Historical Development Milestones

This section records *how the architecture evolved*, not what an older schema currently does. Detailed chronology belongs in [Development History](DEVELOPMENT_HISTORY.md).

### 23.1 XML v1

The original XML implementation established early browser editing and persistence concepts. It remains historical.

### 23.2 Clonker Config v2 — JSON foundation

The JSON transition established strict validation, compact serialization, revision-protected browser saves, verified temporary writes, backup rotation, and a shared configuration model for CircuitPython and JavaScript.

### 23.3 Dumb Queue™ — October 20, 2026

The initial logging-only queue established fixed action dispatch, bounded capacity, eligible-task scheduling, delayed-task bypass, cancellation policy, and cooperative polling.

### 23.4 Outbound HTTP — October 21, 2026

The queue gained real GET/POST execution. Denon and Roku commands were tested, including a five-command volume burst returning HTTP 200 responses.

### 23.5 Clonker Config v3 — October 22, 2026

Built-in device identifiers changed from `tv`, `avr`, and `streaming` to `device-1`, `device-2`, and `device-3`. Browser display labels were retained. Configuration, persistence, and real action execution were regression-tested.

### 23.6 Clonker Config v4 — October 2026

The schema and browser gained user-defined custom actions with stable IDs and ordered command steps. The shared queue gained single-entry custom-task progression and cooperative post-command waits. A real Sunroom Roku/Denon sequence completed successfully.

The firmware module retains the historical `device_config_v2.py` filename; the active schema is v4.

---

## 24. Architectural Ownership

| Component | Owns |
|---|---|
| Configuration engine | Validated configuration, revision, persistence, recovery |
| Action dispatcher / Dumb Queue™ | Acceptance, eligibility, sequencing, execution policy, cancellation, diagnostics |
| HTTP transport | Outbound network exchange, timeout handling, HTTP results |
| Management server | Browser/API requests, save orchestration, listener lifecycle |
| Browser editor | User-facing configuration editing and submission |
| Browser Test Remote | User-facing action submission |
| Physical controls (future) | Input capture and generic action generation |
| External equipment | Actual power, input, playback, and volume state |

### 24.1 Non-negotiable boundaries

- Do not embed Denon/Roku URLs in physical control handlers.
- Do not add a second queue or macro engine for custom actions.
- Do not let a browser tab become the authoritative runtime configuration.
- Do not silently retarget actions when a custom destination changes or disappears.
- Do not treat command history as equipment-state truth.
- Do not make the Clonker more complicated merely because we can.

---

## 25. Design Principles Worth Remembering

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

### 25.1 Future objective — Clonker Recipe Library

**Status:** Conceptual, not implemented. Custom actions are operational; custom devices and the recipe distribution experience remain future work.

A future recipe library may provide downloadable configuration examples for common equipment combinations and named command sequences. Recipes could live on the Clonker website or in a GitHub-hosted catalog.

A future editor workflow could retrieve a catalog, show equipment and compatibility notes, load a selected recipe for review, and require an explicit Save before persistence.

Recipes must never bypass validation, revision protection, or save safeguards. The Pico must remain fully operational without internet access or a recipe catalog.

**Recipes help configure the Clonker; they do not become a runtime dependency.**

---

## 26. Reference Documents

- [Configuration & Recovery](CONFIGURATION.md) — authoritative Clonker Config v4 schema, validation, browser behavior, persistence, and recovery.
- [Firmware & Network](FIRMWARE_NETWORK.md) — networking, clock services, HTTP behavior, and testing.
- [Operating Modes](OPERATING_MODES.md) — filesystem ownership and application modes.
- [Hardware & Controls](HARDWARE_CONTROLS.md) — physical controls, GPIO planning, and power behavior.
- [Development & Deployment](DEVELOPMENT.md) — development workflow and deployment.
- [Development History](DEVELOPMENT_HISTORY.md) — chronological engineering milestones.
- [Chapter 2 Handoff](CHAPTER_2_HANDOFF.md) — historical handoff reference.
- [Terminology Audit](TERMINOLOGY_AUDIT.md) — historical terminology reconciliation.
- [Old Architecture](OLD_ARCHITECTURE.md) — historical reference, not the active architecture.
- [`samples/device_config_roku_denon_sample.json`](../samples/device_config_roku_denon_sample.json) — readable two-room Config v4 example.

---

**CLONK! ⚡🔩**

*The Clonker 10000 — because apparently a normal remote control wasn't complicated enough.*
