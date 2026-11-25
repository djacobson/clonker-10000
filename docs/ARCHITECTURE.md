# The Clonker 10000 — System Architecture

**Updated:** November 25, 2026  
**Platform:** Raspberry Pi Pico 2 W / CircuitPython 10.3.1  
**Repository:** [djacobson/clonker-10000](https://github.com/djacobson/clonker-10000)  
**Current baseline:** Chapter 13 — The Monster Learns Another Language  
**Configuration:** Clonker Config v5

> **Clonker controls intent, not reality. Controlled devices own their own state.**

---

## 1. Mission and Architectural Principles

The Clonker 10000 is a tactile, Wi-Fi-first home-theater remote.

Its purpose is to translate physical or browser input into configured equipment commands without becoming a general-purpose home-automation server.

The architecture favors predictable behavior, responsiveness, serviceability, and incremental development.

The basic execution model is:

1. Detect a physical or browser action.
2. Determine the target room.
3. Resolve the generic action identity.
4. Admit work to the shared Dumb Queue™.
5. Resolve the command from active validated configuration.
6. Select the appropriate device adapter and transport.
7. Execute the command.
8. Record the result without pretending to know equipment state.

**One queue. One poller. One shared execution path.**

Both physical controls and the browser Test Remote use the same action system.

The remote does not maintain authoritative equipment state. It sends commands and observes execution and transport results.

**Be resilient in our dumbness.**

For a standalone discussion of cooperative HTTP server design, bounded memory usage, and failure recovery, see [Cooperative HTTP Server](COOPERATIVE_HTTP_SERVER.md).

---

## 2. Architecture at a Glance

```text
                    THE CLONKER 10000

       BROWSER TEST REMOTE       PHYSICAL CONTROLS
                |                Buttons / Encoders
                |                   Room Selector
                |                         |
                |                     physical.py
                |                  Event -> Action
                |                    Selected Room
                |                         |
                +------------+------------+
                             |
                             v
                      ACTION DISPATCH
                         actions.py
                             |
                             v
                        DUMB QUEUE™
                  Fundamental / Custom
                     Physical Holds
                             |
                             v
                       actions.poll()
                       Eligible work
                             |
                             v
                    ACTIVE CONFIGURATION
                      device_config.py
                      Clonker Config v5
                             |
                             v
                     COMMAND RESOLUTION
                    Typed device record
                   Protocol-aware command
                             |
                             v
                 devices/device_adapters.py
                 Selection / Cache / Execute
                             |
       +----------+----------+----------+----------+
       |          |          |          |          |
       v          v          v          v          v
   Denon TCP   Roku ECP   Generic    LG webOS    Wake-on-LAN
   Persistent  Tap/Hold   HTTP       SSAP/Pointer UDP magic
   Port 23     Volume     GET/POST   WebSockets   packet
       |          |          |          |          |
       v          v          v          v          v
   Denon AVR     Roku    Configured    LG TV     Compatible
                         Equipment               Equipment
```

### 2.1 Configuration management

```text
                 CONFIGURATION EDITOR
                     Browser / JSON
                            |
                            v
                        net/web.py
                            |
                            v
                     device_config.py
                  Validate / Revision Check
                            |
                            v
                   Prepare Adapter Cache
                            |
                            v
                    Verified File Save
                     Backup Rotation
                            |
                            v
                   Retire Old Sessions
                   Publish Adapter Cache
                   Publish RAM Config
                            |
                            v
                 Reset Physical Gestures
                   Clear Pending Work
                 Reset Toggle Histories
```

The configuration editor obtains device-type metadata from the firmware registry.

It does not independently define the supported device architecture.

### 2.2 Cooperative maintenance

```text
                    main.py Scheduler
                            |
         +------------------+------------------+
         |                  |                  |
         v                  v                  v
    Physical Poll      Action Queue       Adapter Poll
         |                  |                  |
         v                  v                  v
    GPIO Events       Eligible Command    Session Maintenance
                                          Release Handling
                                          Receive Draining

         +------------------+------------------+
         |                  |                  |
         v                  v                  v
    Management HTTP     OLED Poll         Sleep Manager
    CONFIG only         Display State     Power Policy
```

Adapter maintenance continues independently of queue depth.

For example, a Roku volume key may require release and an LG SSAP request may require response processing after ordinary queued work has completed.

This maintenance is not a second action queue.

### 2.3 Architectural invariants

- Hardware drivers detect electrical events.
- Physical coordination translates events into generic actions.
- Configuration owns device identity, destinations, and command definitions.
- The device-type registry owns protocol compatibility and availability metadata.
- The dispatcher owns action admission, sequencing, eligibility, and cancellation.
- The adapter coordinator owns execution selection and adapter lifecycle coordination.
- Individual adapters own protocol-specific behavior.
- Browser and physical inputs share the same dispatcher and queue.
- Active validated RAM configuration is authoritative.
- Changed configuration saves invalidate obsolete pending work.
- Physical releases retain the context of their original presses.
- External equipment owns actual power, volume, playback, and input state.
- Missing optional hardware must not disable the core application.
- Management HTTP is not required for ordinary physical remote operation.

**No duplicate command pipelines. No second queue. No manufacturer-specific networking logic in GPIO drivers.**

---

## 3. Firmware Component Ownership

| Component | Responsibility |
|---|---|
| `firmware/boot.py` | Boot-time filesystem ownership |
| `firmware/code.py` | CircuitPython application entry |
| `firmware/clonker/main.py` | Initialization, operating modes, cooperative scheduler |
| `firmware/clonker/device_config.py` | Config v5 validation, active RAM state, revisions, persistence |
| `firmware/clonker/actions.py` | Action dispatcher, Dumb Queue™, sequencing, cancellation |
| `firmware/clonker/devices/device_types.py` | Central device-type registry |
| `firmware/clonker/devices/device_adapters.py` | Adapter selection, cache, execution, lifecycle coordination |
| `firmware/clonker/devices/denon.py` | Persistent Denon TCP volume transport |
| `firmware/clonker/devices/roku.py` | Roku ECP persistent taps, button holds, volume holds |
| `firmware/clonker/devices/lg_webos.py` | Authenticated LG control and pointer sessions, bounded asynchronous response tracking |
| `firmware/clonker/net/wake_on_lan.py` | Temporary UDP socket and Wake-on-LAN magic packet transmission |
| `firmware/clonker/net/http_transport.py` | Generic bounded outbound HTTP |
| `firmware/clonker/net/web.py` | CONFIG-mode management HTTP |
| `firmware/clonker/net/web_diag.py` | Management HTTP connection diagnostics |
| `firmware/clonker/controls/pins.py` | GPIO assignments |
| `firmware/clonker/controls/buttons.py` | Debounced momentary button driver |
| `firmware/clonker/controls/selectors.py` | Physical room selector |
| `firmware/clonker/controls/encoders.py` | Reusable quadrature encoder driver |
| `firmware/clonker/controls/physical.py` | Physical coordination, action mapping, hold gestures |
| `firmware/clonker/controls/switches.py` | Operating-mode switch handling |
| `firmware/clonker/system/clock.py` | UTC reference and monotonic timing |
| `firmware/clonker/system/logger.py` | Serial diagnostics |
| `firmware/clonker/system/perf.py` | Shared performance instrumentation |
| `firmware/clonker/system/sleep_manager.py` | Software sleep and wake policy |
| `firmware/clonker/system/flight_recorder.py` | Diagnostic snapshots and registered transport providers |
| `firmware/clonker/display/oled.py` | Deferred OLED rendering, acknowledgment, idle behavior |
| `firmware/clonker/www/index.html` | Embedded configuration editor |
| `firmware/clonker/www/remote.html` | Embedded Test Remote |
| `firmware/clonker/legacy/` | Historical implementations |
| `firmware/tests/` | Standalone experiments and regression tests |
| `recipes/` | Hosted configuration recipe library |

Active configuration module filenames no longer contain schema-version suffixes.

The configuration schema version remains explicit in the JSON and configuration engine.

### 3.1 Separation of responsibilities

Reusable hardware drivers should know only what is necessary to interpret their inputs.

The encoder driver understands quadrature transitions, not receiver volume.

The button driver understands debounced press and release events, not equipment power.

The room selector understands physical position, not device protocols.

Physical coordination assigns application meaning to those events.

Configuration defines the intended command.

The dispatcher schedules it.

The adapter delivers it.

**Reusable hardware mechanisms; simple application-specific state.**

---

## 4. Operating Modes

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

### 4.3 Valid combinations

| Filesystem mode | Application mode | Behavior |
|---|---|---|
| SERVICE | CONFIG | Browser inspection and action testing; persistent browser saves disabled |
| SERVICE | RUN | USB owns filesystem; management listener disabled |
| DEVICE | CONFIG | Browser management and persistent configuration saves enabled |
| DEVICE | RUN | Normal physical remote operation |

Neither switch is an equipment power command.

The physical Power Toggle is a configured fundamental action, not a Pico power switch.

See [Operating Modes](OPERATING_MODES.md) for operating procedures.

---

## 5. Configuration Architecture

The active configuration is **Clonker Config v5**, stored as JSON.

The deployed primary configuration is:

```text
/clonker/device_config.json
```

Each configured room contains:

- A stable room identifier.
- A display name.
- Three typed device records.
- Fourteen fundamental action definitions.
- An ordered collection of optional Custom Actions.

One to three rooms may be configured.

The physical selector recognizes all three room positions independently of configuration availability.

The running Pico's configuration may be newer than the configuration stored in the source repository.

Firmware deployment must not casually overwrite the user's active configuration.

### 5.1 Stable device slots

| Stable ID | Editor role label |
|---|---|
| `device-1` | TV |
| `device-2` | AVR |
| `device-3` | Streaming |

The role labels are organizational conveniences, not device-type restrictions.

Any configurable device type may occupy any of the three slots.

Actions explicitly identify their target device slot.

A room's physical volume encoder does not need to know whether volume is controlled by a Denon receiver, Roku, or LG television adapter.

### 5.2 Typed devices

Config v5 replaces the earlier endpoint-only device representation with explicit typed records.

Example:

```json
{
  "type": "roku",
  "endpoint": "192.168.50.28:8060"
}
```

The device type identifies the intended protocol family.

The endpoint identifies the destination.

Additional attributes may be defined by the device-type registry.

For example, an LG webOS device record includes a client key.

Device identity is no longer inferred solely from command-path signatures.

### 5.3 Central device-type registry

**Module:** `clonker/devices/device_types.py`

The registry defines:

- Stable type identifiers.
- Display labels.
- Runtime availability.
- Suggested default ports.
- Supported command kinds.
- Device-specific attributes.
- Pairing capability.

| Device type | Command kinds | Current status |
|---|---|---|
| `generic-http` | HTTP, Wake-on-LAN | Operational |
| `denon` | HTTP, Wake-on-LAN | Operational |
| `roku` | HTTP, Wake-on-LAN | Operational |
| `lg-webos` | SSAP, Pointer, Wake-on-LAN | Operational on tested equipment |
| `apple-tv` | None | Future |
| `fire-tv` | None | Future |

The registry is lightweight metadata.

It does not import operational adapters, establish connections, or execute commands.

Both firmware validation and browser presentation use this shared metadata.

Command compatibility and runtime availability are separate concepts.

A structurally valid LG device record may contain a blank or placeholder client key; authenticated execution requires a usable key.

### 5.4 Protocol-aware command objects

Every Config v5 command explicitly declares its protocol kind.

HTTP example:

```json
{
  "kind": "http",
  "method": "POST",
  "path": "/keypress/Home"
}
```

LG SSAP example:

```json
{
  "kind": "ssap",
  "uri": "ssap://audio/setMute",
  "payload": {
    "mute": true
  }
}
```

LG pointer example:

```json
{
  "kind": "pointer",
  "button": "HOME"
}
```

SSAP and pointer commands are operational on the tested Sunroom LG G1.

Wake-on-LAN example:

```json
{
  "kind": "wake-on-lan",
  "mac": "02:00:00:00:00:00",
  "broadcast": "192.168.50.255",
  "port": 9
}
```

Wake-on-LAN is available for either Power Toggle direction and Custom Action steps on all operational device types. It requires neither a device endpoint nor an authentication key. The example MAC is a synthetic placeholder.

The dispatcher handles command objects without requiring manufacturer-specific command syntax in physical controls.

### 5.5 Room availability and intentional no-ops

An unconfigured room and a configured room with blank endpoints are distinct conditions.

Neither causes actions to fall back to another room.

Blank fundamental commands and blank device endpoints are valid configuration.

The ordinary action path treats blank commands and missing required endpoints as intentional no-ops. Wake-on-LAN is endpoint-independent.

The physical hold path also checks for blank commands and endpoints before admitting specialized hold work.

Custom Action steps require nonblank commands.

### 5.6 Active RAM configuration

At startup, the configuration engine loads and validates the persisted JSON.

The validated configuration becomes the authoritative active RAM snapshot.

Runtime action execution does not reread or revalidate the entire configuration for every command.

The browser editor is a client of the configuration engine, not a separate source of truth.

### 5.7 Configuration activation

Configuration activation is distinct from configuration validation.

For a changed save:

1. Validate the proposed configuration.
2. Check revision and disk consistency.
3. Prepare the replacement adapter cache.
4. Complete verified persistence.
5. Retire existing adapter sessions.
6. Publish the replacement cache and validated configuration.
7. Reset physical configuration-dependent state.
8. Clear pending actions and reset toggle histories.

Session retirement is best-effort cleanup.

A cleanup warning does not invalidate an otherwise successfully persisted configuration.

Preparing a replacement cache does not publish it prematurely.

A rejected save preserves the active configuration and routing state.

An unchanged save preserves existing sessions, pending work, and toggle histories.

See [Configuration, Persistence & Recovery](CONFIGURATION.md) for exact schema, revision, persistence, and recovery rules.

---

## 6. Validation Boundaries and Memory Discipline

**Validate at trust boundaries, not repeatedly throughout the application.**

This is a fundamental architectural requirement for the memory-constrained CircuitPython platform.

Full configuration validation constructs normalized objects and can create substantial temporary allocation pressure.

Repeated validation of already trusted configuration is neither necessary nor free.

### 6.1 Appropriate validation boundaries

Full validation belongs at boundaries such as:

- Loading configuration from storage.
- Accepting a proposed configuration from the browser.
- Checking an existing primary file for unexpected changes.
- Importing or preparing configuration examples for deployment.

The runtime dispatcher and physical-control paths should consume already validated data.

### 6.2 Efficient runtime access

The configuration engine exposes lightweight accessors, including:

- `has_room()`
- `action_details()`
- `custom_action_details()`
- `custom_actions_for_room()`
- `resolve_device()`
- `resolve_endpoint()`
- `command_is_blank()`

Internal configuration references returned by these accessors must be treated as read-only.

Do not reconstruct an entire validated configuration merely to inspect a room, select a Custom Action, or resolve an equipment command.

Use an independent configuration copy only where the consumer actually requires one.

### 6.3 Serialization and persistence

The configuration engine distinguishes between:

- Validating untrusted configuration.
- Serializing already validated configuration.
- Comparing validated configuration objects.
- Verifying persisted bytes.

These are separate operations.

Exact byte verification of a file containing already validated serialized data does not require reconstructing the entire configuration again.

Temporary and installed file verification therefore uses bounded byte comparisons.

### 6.4 Explicit garbage collection

The production save pipeline includes intentional garbage collection boundaries:

1. At save entry.
2. After incoming validation and serialization, before loading the existing primary.

These boundaries reclaim temporary objects before subsequent allocation-intensive work.

They are production behavior, not temporary debugging instrumentation.

Do not remove them without regression testing.

### 6.5 Lessons from Chapters 8 and 12

Chapter 8 identified repeated configuration validation as the cause of substantial physical polling execution overhead.

Lightweight accessors eliminated unnecessary reconstruction of trusted configuration in those paths.

Chapter 12 identified similar allocation pressure during configuration persistence.

Reducing redundant validation, serialization, and file reconstruction, together with explicit garbage collection, substantially improved repeated-save reliability.

The observed behavior does not establish a memory leak in CircuitPython's JSON library or other system libraries.

The intermittent management socket-send stall remains a separate unresolved issue.

**Correctness does not require repeatedly proving that unchanged, already validated data is valid.**

---

## 7. Fundamental Actions and Custom Actions

### 7.1 Fundamental actions

Each configured room defines fourteen stable fundamental action IDs.

| Category | Actions |
|---|---|
| Volume | `volume-up`, `volume-down`, `mute-toggle` |
| Navigation | `nav-up`, `nav-down`, `nav-left`, `nav-right`, `select` |
| Shortcuts | `back`, `home` |
| Playback | `play-pause`, `skip-back`, `skip-forward` |
| Power | `power-toggle` |

The action vocabulary is independent of equipment protocols.

Each ordinary fundamental action identifies a target device and one protocol-aware command object.

### 7.2 Power and mute toggles

Power and mute toggles define independent ON and OFF command objects.

The dispatcher maintains volatile next-direction histories keyed by room and action.

Unknown history begins with the configured ON command.

History advances after successful execution. For LG SSAP and Wake-on-LAN, this means successful transmission, not confirmation of equipment state.

Immediate failures and intentional no-ops do not advance it. A subsequent asynchronous LG failure does not roll back history already advanced.

A reboot or successful changed configuration save resets the histories.

This is last-successful-command direction tracking, not equipment-state discovery.

External remotes, HDMI-CEC, and manual equipment controls may independently change actual equipment state.

### 7.3 Custom Actions

Custom Actions are named, ordered sequences configured per room.

Each step specifies:

- A target device.
- A protocol-aware command.
- A wait following successful completion.

A Custom Action occupies one Dumb Queue™ task while progressing through its steps.

Waits use monotonic deadlines.

Other eligible actions may execute during those waits.

Custom Action steps resolve through their configured device types.

Existing Denon and Roku HTTP Custom Action steps retain ordinary single-command generic HTTP execution.

They do not implicitly acquire fundamental-action hold or repeat behavior.

LG SSAP and pointer steps use the LG adapter; Wake-on-LAN steps use the shared UDP transport. SSAP step waits begin at successful transmission rather than acknowledgement.

There is no branching engine, macro thread, rollback system, nested workflow engine, or independent Custom Action queue.

### 7.4 Stable Custom Action identity

Custom Action identifiers are independent of their display names and list positions.

Renaming or reordering an action does not change its identity.

The browser generates identifiers for new actions automatically and displays them read-only.

Existing identifiers are preserved.

Firmware validation requires uniqueness within each room.

---

## 8. The Dumb Queue™

**Module:** `clonker/actions.py`

The Dumb Queue™ is the single execution pipeline for physical and browser actions.

Its responsibilities are:

1. Validate action admission.
2. Maintain bounded pending work.
3. Determine eligible commands.
4. Preserve applicable ordering.
5. Resolve commands from active configuration.
6. Coordinate adapter readiness and execution.
7. Advance Custom Action steps.
8. Cancel pending work following execution failures.

### 8.1 Capacity and task representation

The queue holds up to 128 entries.

Supported task categories include:

- Fundamental actions.
- Custom Action sequences.
- Explicit physical-button hold events.

Ordinary fundamental actions use stable room and action identifiers.

Custom Actions use room-specific identifiers and compact step state.

Ordinary commands are resolved when eligible rather than copied into every queue entry.

Explicit hold events preserve their original validated device and command references.

This prevents a release from being redirected by a later room selection.

### 8.2 Eligibility and ordering

The queue scans for the first eligible task.

A task waiting for a future deadline does not block immediate eligible work.

Among currently eligible tasks, queue order matters.

If the selected eligible adapter is not ready, the queue preserves the task rather than allowing later eligible commands to overtake it.

Denon TCP pacing and LG pending-response capacity or session-transition readiness are examples of this behavior.

At most one eligible queued command is executed per action poll.

### 8.3 Custom Action progression

After successful completion of a nonfinal step:

1. Advance the step index.
2. Calculate the next eligible monotonic deadline.
3. Return the task to pending work.

The configured wait begins after successful completion of the preceding step. For LG SSAP and Wake-on-LAN this is successful transmission.

The final step completes the Custom Action.

Other eligible work may execute while a Custom Action waits.

### 8.4 Physical hold events

Explicit physical holds are additional task types within the existing queue.

They are not a separate execution system.

The physical coordinator determines whether a button gesture requires an ordinary tap, hold start, or hold release.

The adapter translates those events into protocol-specific operations.

### 8.5 Failure policy

An execution exception cancels remaining pending work, including unfinished Custom Actions.

An asynchronous LG request failure also cancels remaining pending work through the dispatcher. Commands already transmitted are not replayed or rolled back; some subsequent commands may already have been transmitted before the failure is detected.

New work may subsequently be admitted.

The queue does not automatically replay uncertain commands.

A failed transport operation may already have reached the equipment.

Blind repetition could duplicate the intended action.

Adapter-specific release cleanup is a separate safety responsibility.

**One failed external command cancels pending work, not the remote itself.**

### 8.6 Queue state versus adapter state

The queue owns pending action state.

An adapter may own transport and protocol state.

Examples:

- Denon owns a persistent TCP socket and pacing deadline.
- Roku owns persistent HTTP resources and held-key state.
- Generic HTTP owns temporary request sockets.
- LG owns authenticated control and pointer sockets and bounded pending response metadata.
- Wake-on-LAN owns only a temporary UDP socket during transmission.

Such state does not constitute permission to create another action queue.

---

## 9. Device Adapter Architecture

**Module:** `clonker/devices/device_adapters.py`

The adapter coordinator separates configured command intent from protocol-specific execution.

Adapter selection uses:

- Explicit device type.
- Command kind.
- Action context.
- Recognized command mappings where specialization is appropriate.

A generic HTTP device does not acquire Roku or Denon specialization merely because its command path resembles one of their commands.

### 9.1 Operational adapter matrix

| Execution path | Purpose |
|---|---|
| `generic-http` | Ordinary configured HTTP GET/POST commands |
| `denon-tcp` | Specialized Denon fundamental volume commands |
| `roku-volume-hold` | Encoder-driven Roku volume holds |
| `roku-button-tap` | Persistent Roku navigation and skip taps |
| `roku-button-hold` | Explicit Roku navigation and skip holds |
| `lg-webos` | Authenticated SSAP and pointer commands |
| `wake-on-lan` | UDP magic packets for power and Custom Actions |

The original five paths were exercised on physical equipment during Chapter 12. Chapter 13 hardware-tested LG and Wake-on-LAN on the Sunroom G1.

### 9.2 Specialized command recognition

Recognized Denon fundamental volume mappings:

```text
GET /goform/formiPhoneAppDirect.xml?MVUP
GET /goform/formiPhoneAppDirect.xml?MVDOWN
```

Recognized Roku fundamental volume mappings:

```text
POST /keypress/VolumeUp
POST /keypress/VolumeDown
```

Recognized Roku navigation and skip mappings:

```text
POST /keypress/Up
POST /keypress/Down
POST /keypress/Left
POST /keypress/Right
POST /keypress/Rev
POST /keypress/Fwd
```

Specialization additionally requires the appropriate explicitly configured device type.

Unrecognized compatible HTTP commands use ordinary generic HTTP.

Disabled device types must not silently fall back to generic HTTP.

Wake-on-LAN is selected by command kind before manufacturer-specific routing, after device availability and compatibility checks. LG SSAP and pointer commands select the LG adapter.

### 9.3 Adapter cache

Specialized fundamental selections are cached by:

```text
(room_id, action_id)
```

Physical hold selections use separate keys:

```text
("hold", room_id, action_id)
```

The cache is derived from validated configuration.

It is not persisted in the JSON.

It does not contain authoritative equipment state.

A replacement cache is prepared before changed configuration persistence.

Publication occurs during successful configuration activation.

### 9.4 Execution interface

The coordinator exposes protocol-neutral responsibilities for:

- Resolving an execution path.
- Preparing and publishing adapter selections.
- Checking adapter readiness.
- Executing an ordinary command.
- Executing a supported physical hold event.
- Polling adapter maintenance.
- Canceling active protocol state.
- Closing transport resources.

Ordinary execution receives the typed device record and protocol-aware command object.

The coordinator delegates protocol-specific work to the appropriate adapter or transport.

### 9.5 Adapter lifecycle

Adapter maintenance may continue when no queue command is ready.

Examples include:

- Releasing a Roku volume hold.
- Retrying a failed key release.
- Draining unread Denon TCP data.
- Processing bounded LG SSAP responses and retiring failed or idle LG sessions.
- Retiring idle or obsolete transport resources.

Changed configuration activation retires existing adapter sessions.

This prevents old session state from silently surviving a changed endpoint, device type, or credential update.

Cleanup is best effort.

A network failure can prevent confirmation that a remote key or session was successfully released.

### 9.6 Architectural intent

**Specialize where necessary. Keep the common architecture simple.**

A new protocol should extend the existing adapter architecture rather than require changes to every physical input or introduce another action executor.

---

## 10. Operational Protocol Responsibilities

### 10.1 Denon TCP

**Module:** `clonker/devices/denon.py`

The Denon adapter:

- Extracts the receiver host from the configured endpoint.
- Uses native TCP port 23 for specialized volume operations.
- Reuses one persistent receiver connection.
- Translates recognized volume mappings to `MVUP` or `MVDOWN`.
- Enforces command pacing.
- Drains unread socket data.
- Closes and resets its connection on appropriate errors or lifecycle transitions.

The adapter does not maintain a pool of simultaneous receiver connections.

It does not interpret receiver responses as authoritative equipment state.

Receive draining is important for persistent connection reliability.

A successful TCP write does not prove that the receiver executed the command.

### 10.2 Roku persistent taps

**Module:** `clonker/devices/roku.py`

Recognized Roku navigation and skip taps use persistent HTTP where available.

This reduces connection-establishment overhead during repeated button presses.

The adapter retains responsibility for connection reuse and retirement.

Persistent transport behavior does not change the generic fundamental action vocabulary.

### 10.3 Roku held-volume

The Roku volume adapter converts repeated encoder detents into temporary ECP key holds.

Its responsibilities include:

- Starting a hold on the first detent.
- Extending same-direction holds without additional HTTP requests.
- Releasing after inactivity.
- Releasing before direction reversal.
- Bounding maximum hold duration.
- Retaining unresolved release state after failures.
- Pacing release retries.
- Participating in cancellation and shutdown cleanup.

The release-retry mechanism is a specialized safety measure.

It is not a general command replay policy.

### 10.4 Roku physical-button holds

The six physical navigation and skip buttons support tap and hold gestures.

The physical coordinator owns gesture interpretation.

The Roku adapter owns ECP keydown and keyup execution.

The adapter maintains separate state for encoder-driven volume holds and explicit physical-button holds.

A maximum hold safety limit protects against indefinitely held remote keys.

Network failures can still create uncertainty about remote key state.

### 10.5 Generic HTTP

**Module:** `clonker/net/http_transport.py`

Generic HTTP provides bounded blocking GET/POST requests.

It is used for:

- Ordinary Roku ECP commands.
- Denon HTTP commands.
- Existing Roku and Denon Custom Action steps.
- Other compatible configured HTTP commands.

Each ordinary generic HTTP request creates and closes its own connection.

The transport is intentionally small.

It is not a general browser, TLS client, authentication framework, or full HTTP response-processing library.

### 10.6 LG webOS

**Module:** `clonker/devices/lg_webos.py`

The adapter uses authenticated control WebSockets and a separate pointer WebSocket, with one active endpoint/key identity. Session reuse avoids repeated setup for rapid commands. Endpoint or credential changes retire obsolete sessions.

SSAP requests carry configured URIs and optional JSON payloads. Pointer commands carry configured button names. Native LG hold/release is not implemented.

Successful transmission advances the dispatcher. SSAP request IDs and deadlines remain in bounded adapter metadata until responses arrive. The adapter polls receive data cooperatively; rejection or response timeout retires the session and propagates failure to the dispatcher. Idle transport failures without pending requests do not cancel unrelated queued work.

Connection setup, registration, pointer acquisition and transmission still include bounded blocking operations. This is not a fully nonblocking WebSocket implementation.

### 10.7 Wake-on-LAN

**Module:** `clonker/net/wake_on_lan.py`

The transport sends one 102-byte magic packet to the configured IPv4 broadcast destination and UDP port using a temporary socket. It closes the socket after the attempt. Successful transmission is not a wake acknowledgement. There are no automatic retries, persistent sessions or response tracking.

### 10.8 Why these paths coexist

Denon volume benefits from persistent native TCP.

Roku volume benefits from minimizing HTTP requests during repeated encoder movement.

Roku navigation benefits from persistent taps and explicit keydown/keyup behavior.

Ordinary commands remain well served by bounded generic HTTP.

LG benefits from authenticated session reuse and asynchronous SSAP response processing. Wake-on-LAN provides a separate endpoint-independent wake mechanism.

The architecture allows these approaches to coexist without changing physical controls or creating separate execution pipelines.

See [Firmware, Network & Clock](FIRMWARE_NETWORK.md) for detailed transport behavior and timing parameters.

---

## 11. Physical Controls

The physical interface consists of:

- A three-position room selector.
- A rotary volume encoder with push-to-mute.
- A rotary Custom Action encoder with push-to-run.
- Four directional navigation buttons.
- Select, Home, and Back.
- Skip Back, Play/Pause, and Skip Forward.
- A guarded momentary Power Toggle.
- Operating-mode controls.
- OLED feedback.

### 11.1 GPIO assignments

| GPIO | Function |
|---|---|
| GP2 | Momentary Power Toggle |
| GP3 | Room selector — Room 1 |
| GP4/GP5 | OLED I²C |
| GP6 | Room selector — Room 2 |
| GP7 | Room selector — Room 3 |
| GP8/GP9 | Volume encoder A/B |
| GP10 | Volume encoder push-to-mute |
| GP11/GP12 | Custom Action encoder A/B |
| GP13 | Custom Action encoder pushbutton |
| GP14 | Navigation Up |
| GP15 | Navigation Down |
| GP16 | Navigation Left |
| GP17 | SERVICE/DEVICE |
| GP18 | CONFIG/RUN |
| GP19 | Navigation Right |
| GP20 | Select / OK |
| GP21 | Back |
| GP22 | Home |
| GP26 | Skip Back |
| GP27 | Play/Pause |
| GP28 | Skip Forward |

`controls/pins.py` is the source of truth for assignments.

GPIO assignment, electrical detection, and complete application behavior are separate verification milestones.

See [Hardware Design](HARDWARE_DESIGN.md) for physical construction and wiring.

### 11.2 Room selection

The physical selector recognizes three stable positions.

Invalid transitional readings do not replace the last valid room.

The selector changes room context.

It does not dispatch an equipment command.

Room availability is determined independently by active configuration.

An unavailable room must never silently redirect commands to another room.

### 11.3 Momentary buttons

The reusable button driver provides debounced press and release events.

The physical coordinator maps button identities to generic fundamental actions.

Most ordinary buttons dispatch on press.

The navigation and skip buttons additionally support specialized tap/hold gestures when the configured device and command permit them.

### 11.4 Rotary volume control

Rotation generates `volume-up` or `volume-down`.

Pressing the shaft generates `mute-toggle`.

The selected room and active configuration determine the target equipment.

The encoder driver does not know whether the command uses Denon TCP, Roku ECP, generic HTTP, LG webOS, or another protocol.

### 11.5 Custom Action encoder

Rotation cycles through the selected room's ordered Custom Actions.

The physical coordinator maintains the selected action index.

Changing rooms resets the selection.

An empty Custom Action list is handled without attempting execution.

Pressing the encoder dispatches the selected action through the shared queue.

The selected action name is also sent to the OLED.

### 11.6 Physical tap/hold interpretation

The four navigation buttons and two skip buttons support Roku tap/hold gestures.

With `NAV_PRESS_FIRST = True`:

1. A debounced press immediately queues an ordinary tap.
2. If the button remains pressed for 250 ms, a hold start is queued.
3. Releasing an active hold queues the matching release.
4. Releasing a short press produces no additional command.

With `NAV_PRESS_FIRST = False`, the original release-first behavior remains available.

A short press dispatches on release, while a sustained press uses hold start and release.

Press-first operation can produce an additional initial movement when a sustained press transitions into a hold.

This was accepted as a practical tradeoff for immediate tap responsiveness.

Compatible commands without specialized hold support, including LG pointer commands, receive one ordinary action rather than an invented repeat mechanism.

### 11.7 Press and release ownership

The physical coordinator captures the original:

- Room identifier.
- Action identifier.
- Validated device record.
- Validated command object.
- Adapter selection.
- Press timing and gesture state.

Changing rooms while a button is held must not redirect its release.

Pending releases retain the original destination and command.

When queue capacity temporarily prevents admission, the physical coordinator retains necessary release context for subsequent admission attempts.

This is physical gesture bookkeeping, not a second execution queue.

### 11.8 Configuration changes

A successful changed configuration save calls the physical coordinator's configuration-change reset.

This clears:

- Outstanding hold gesture state.
- Pending physical releases.
- The Custom Action selection index.

The dispatcher separately clears pending actions and resets toggle histories.

Adapter activation retires obsolete sessions.

These responsibilities work together to prevent an old physical gesture from restarting against outdated configuration.

An unchanged configuration save does not require these resets.

### 11.9 OLED feedback

**Module:** `clonker/display/oled.py`

The SH1106 128×64 OLED operates over I²C.

The display driver owns:

- Initialization.
- Text rendering.
- Single-line and two-line layouts.
- Hardware inversion.
- Refresh pacing.
- Activity tracking.
- Idle display-off.

Physical controls request display changes without performing direct I²C operations.

Implemented feedback includes:

- Selected room and room name.
- `UNASSIGNED` for an unavailable room.
- Selected Custom Action name.
- Custom Action dispatch acknowledgment.
- Volume direction.
- Successful mute-toggle direction.
- Navigation and playback labels.
- Power Toggle dispatch feedback.

Custom Action acknowledgment uses persistent hardware inversion until reset, a new message, or idle sleep.

Repeated identical display requests avoid unnecessary framebuffer refreshes.

Display activity and rendering remain cooperative and separate from network execution.

OLED feedback must not be interpreted as independent confirmation of actual equipment state.

---

## 12. Cooperative Scheduler

**Module:** `clonker/main.py`

The firmware uses a cooperative main loop rather than threads or hardware-interrupt-driven network execution.

The scheduler coordinates:

- Physical GPIO polling.
- Eligible queued actions.
- Adapter maintenance.
- Operating-mode evaluation.
- Management HTTP.
- OLED updates.
- Memory monitoring.
- Sleep policy.
- Brief CircuitPython yields.

### 12.1 Scheduling targets

The established awake-mode scheduling targets include:

| Responsibility | Target |
|---|---:|
| Physical controls | 1 ms |
| Action queue | 10 ms |
| Management HTTP | 1 ms |
| Main-loop yield | 1 ms |

These are scheduling targets, not guaranteed maximum latencies.

The current implementation and its constants remain authoritative.

### 12.2 Physical responsiveness

Rotary encoders generate electrical transitions that must be sampled.

The encoder driver decodes transitions and reports completed movements.

Physical coordination converts those movements into generic actions.

Network execution occurs separately through the queue.

Specialized volume adapters reduce network overhead during rapid rotation.

However, synchronous operations can delay the cooperative scheduler.

The queue cannot reconstruct electrical transitions that were never observed.

### 12.3 Adapter maintenance

The scheduler polls the adapter coordinator even when no queued action is ready.

Roku release handling and Denon receive draining are examples of maintenance that must not depend on queue depth.

LG response processing also runs independently of queue depth. The coordinator returns an adapter/error pair on LG asynchronous failure; the main loop forwards it to `actions.fail_async()` to cancel pending work.

This remains cooperative work within the same application loop.

### 12.4 Performance instrumentation

`system/perf.py` provides shared timing measurements and accumulated statistics.

Instrumentation may measure:

- Physical polling gaps.
- Physical execution.
- Queue execution.
- Adapter maintenance.
- Management HTTP.
- OLED polling.
- Main-loop execution.

Detailed diagnostics should be enabled deliberately.

Excessive logging and instrumentation can themselves affect timing and allocation behavior.

Performance measurements must distinguish execution duration from gaps between scheduler opportunities.

### 12.5 Timing reference

Scheduling deadlines use monotonic time.

Readable wall-clock timestamps are a separate concern.

Adjusting the UTC reference must not shift action deadlines, Custom Action waits, hold timing, or transport pacing.

See [Firmware, Network & Clock](FIRMWARE_NETWORK.md) for current timing implementation details.

---

## 13. Management HTTP and Failure Isolation

The management server is a cooperative, single-client HTTP listener.

It is enabled only in CONFIG mode.

It is not a concurrent web server or an operational dependency of the physical remote.

### 13.1 Responsibility boundaries

| Component | Responsibility |
|---|---|
| `net/web.py` | Listener, request handling, client state, bounded response delivery |
| `net/web_diag.py` | Per-connection diagnostics |
| `main.py` | Operating-mode lifecycle, exception boundaries, listener recovery scheduling |
| `device_config.py` | Configuration validation and persistence |
| `actions.py` | Shared action admission and execution |

Static HTML is streamed from flash in bounded chunks.

Management requests are subject to explicit size and timing limits.

The configuration API returns active configuration together with response-only metadata.

### 13.2 Configuration editor

The Config v5 editor supports:

- Adding and removing configured rooms.
- Stable room identifiers.
- Typed device records.
- Registry-driven device selectors.
- Device-specific attributes.
- Protocol-aware command editing.
- Independent toggle command objects.
- Ordered Custom Actions and steps.
- Stable generated Custom Action identifiers.
- Revision-protected saves.
- Configuration recipe browsing and JSON import.
- Clock tools.
- Access to the Test Remote.

The editor does not silently translate incompatible commands when a device type changes.

The user must resolve incompatible mappings before saving.

LG SSAP, pointer and Wake-on-LAN editing and execution are operational. Client keys are manually entered; integrated pairing remains deferred.

### 13.3 Test Remote

The browser Test Remote submits generic room and action identifiers.

It does not independently execute equipment protocols.

Browser actions and physical actions enter the same dispatcher and Dumb Queue™.

An accepted browser action is not proof of equipment execution.

### 13.4 Listener failure handling

Management HTTP failure must not deliberately terminate the physical-control application.

Established recovery behavior includes:

- Discarding a failed client transaction.
- Reclaiming memory following management allocation failures.
- Retiring listener resources following unexpected listener errors.
- Delayed listener restart while CONFIG remains enabled.
- Stopping the listener when switching to RUN.

Expected nonblocking socket conditions do not require listener restart.

These recovery boundaries do not guarantee recovery from every underlying Wi-Fi or socket-stack failure.

### 13.5 Intermittent socket-send stall

Chapter 12 testing reproduced intermittent management HTTP socket sends taking approximately ten seconds despite intended nonblocking operation.

Observed effects included:

- Incomplete configuration GET responses.
- Incomplete HTML responses.
- Delayed or unsuccessful delivery of save acknowledgments.
- Browser reports of uncertain save outcomes.
- Repeated failures across separate browser clients.

The problem also occurred on ordinary GET requests without configuration saves.

A successful configuration persistence operation could precede a stalled HTTP response.

Increasing the send chunk from 128 to 512 bytes improved ordinary response efficiency but did not eliminate the intermittent stall.

Recovery without a reboot was observed.

The precise trigger and recovery mechanism remain unknown.

Chapter 13 observations associate the stall with the configuration page rather than the Test Remote so far. Browser request patterns and CircuitPython socket behavior remain investigation candidates, not established causes.

Physical controls, Roku commands, Denon volume, and Custom Actions remained functional between stalled management requests.

Responsiveness during an individual blocking socket operation has not been established.

The cooperative scheduler cannot preempt a lower-level socket call that has already blocked.

### 13.6 Distinguish persistence from response delivery

Configuration persistence and HTTP response delivery are separate operations.

A successful save does not guarantee that its acknowledgment reaches the browser.

The browser must not automatically replay a configuration POST after an uncertain outcome.

The appropriate recovery is to obtain the current configuration and revision, then determine whether the intended change was persisted.

See [Configuration, Persistence & Recovery](CONFIGURATION.md) for the recovery procedure.

### 13.7 Security boundary

The management service has no application-level authentication or HTTPS.

It is intended for a trusted LAN.

Do not expose it directly to the public internet.

Configuration now contains operational LG credentials. Protect management access and exported configuration files; the configuration API includes stored client keys.

---

## 14. Software Sleep and Power Management

**Primary module:** `clonker/system/sleep_manager.py`

The Clonker supports software-managed inactivity sleep.

This is an application-level power state, not hardware light sleep or deep sleep.

The CPU remains active to monitor physical inputs.

### 14.1 Responsibility boundaries

The sleep manager owns:

- Inactivity tracking.
- Sleep eligibility.
- Sleep state transitions.
- Development dry-run behavior.
- Wake-event policy.
- OLED shutdown coordination.
- Wi-Fi radio shutdown.
- Recovery reboot policy.

The scheduler coordinates ordinary application work with the sleep state.

Physical controls report activity.

They do not independently manage Wi-Fi or display shutdown.

The OLED driver retains ownership of its display and I²C resources.

### 14.2 Sleep eligibility

Software sleep is permitted when:

- Sleep is enabled.
- CONFIG mode is inactive.
- The inactivity timeout has elapsed.
- No queued actions remain.

CONFIG mode inhibits sleep and resets inactivity timing.

Physical activity while awake restarts the inactivity timer.

### 14.3 Sleep entry

When the inactivity timeout expires:

1. The OLED displays `Going Zzzz!`.
2. The OLED is closed and its I²C resources are released.
3. The Wi-Fi radio is disabled.
4. The sleep manager enters its asleep state.

The CPU continues running.

A shutdown exception triggers a recovery reboot rather than deliberately remaining in a partially shut-down state.

### 14.4 Scheduler behavior while asleep

During software sleep:

- Physical GPIO polling continues.
- Action execution is suspended.
- Adapter maintenance is suspended.
- Management HTTP cannot start.
- OLED polling is suspended.
- Memory-monitor polling is suspended.
- The main-loop delay increases to 25 ms.

The longer delay is a polling optimization, not a guaranteed wake latency.

Very short button presses may be missed.

### 14.5 Wake policy

Wake-eligible inputs are:

- Supported momentary pushbutton presses.
- A physical CONFIG/RUN switch transition.

Encoder rotation and room-selector movement do not wake the Clonker.

The wake-triggering input is consumed.

It must not issue an equipment command.

In real sleep mode, wake calls `microcontroller.reset()`.

CircuitPython and Clonker then initialize normally, restoring Wi-Fi and application services.

In dry-run mode, the simulated awake state is restored without rebooting.

### 14.6 Runtime sleep override

The sleep manager owns the startup sleep-enabled default and a volatile runtime override.

The physical coordinator recognizes the room-selector sequence:

```text
1 -> 2 -> 1 -> 2 -> 1 -> 2
```

The sequence must be completed within ten seconds while the physical CONFIG switch is enabled.

Successful recognition toggles the sleep-enabled state and requests OLED confirmation:

```text
SLEEP ON
SLEEP OFF
```

A reboot restores the developer-configured startup default.

The physical coordinator recognizes the gesture.

The sleep manager owns the power-management decision.

### 14.7 Power measurements and limitations

Chapter 9 bench measurements at approximately 5 V established:

| Condition | Approximate current |
|---|---:|
| Awake RUN | 38 mA |
| Initial software sleep | 25 mA |
| Optimized software sleep | 24 mA |

These measurements represent USB-side load, not total battery current.

Battery conversion losses and power-module consumption must be considered separately.

Battery-powered software sleep and physical-button wake have been demonstrated, including an approximately twelve-hour overnight endurance test.

Longer-term endurance and full-discharge behavior remain separate verification tasks.

### 14.8 Future sleep strategies

The sleep manager is intended to remain the central policy owner if hardware-assisted sleep becomes available.

Future strategies may require changes to:

- GPIO wake configuration.
- Peripheral initialization.
- Network session lifecycle.
- Scheduler coordination.

Do not introduce additional sleep modes or lifecycle interfaces until concrete requirements justify them.

---

## 15. Protocol Integration and Future Work

Config v5 establishes the architectural foundation for authenticated and non-HTTP device protocols. Configuration support does not automatically imply runtime support.

### 15.1 LG webOS integration

**Module:** `clonker/devices/lg_webos.py`

Chapter 12 established typed LG records and command objects in direct support of the experimental adapter. Chapter 13 connected the adapter to operational dispatch and verified native control on the Sunroom LG G1.

Standalone pairing remains the method for obtaining a client key. The editor supports manual key entry; its integrated pairing control remains disabled.

### 15.2 LG integration boundaries

Keep these responsibilities distinct:

- Initial pairing.
- Stored credential handling.
- Authenticated control-session establishment.
- Pointer-session establishment.
- Command transmission.
- Response processing.
- Session retirement.

Pairing and authenticated session setup are not ordinary equipment commands. Existing cooperative pairing helpers and separate pairing/runtime manifests are retained. Integrated credential handoff, cancellation and manifest unification remain future work.

### 15.3 Command completion semantics

A transmitted command is not necessarily an acknowledged command. An acknowledged command is not necessarily proof of physical equipment state.

LG uses transmit-and-continue semantics. Successful transmission removes a fundamental task or advances a Custom Action step, starts its configured wait and advances applicable toggle history.

Pending SSAP response metadata belongs to the adapter, not a second execution queue. Readiness prevents additional transmission when pending capacity or session-transition constraints require it.

Asynchronous rejection or timeout cancels remaining queued work. Already transmitted commands are not replayed or rolled back. Live rejection and recovery were verified; an actual response-timeout experiment remains outstanding.

### 15.4 Credential lifecycle and compatibility

Stored credentials must remain associated with the intended device. A changed endpoint or credential must not silently reuse an obsolete authenticated session.

Public recipes must exclude real client keys and equipment-specific MAC addresses. A blank key or published placeholder can be structurally valid without making authenticated execution ready.

The newer Den LG C6H remains experimental. Pico TCP tests reached port 3001 but failed on port 3000; TLS experiments on both televisions failed certificate verification before WebSocket upgrade. These results do not establish that secure WebSockets are required or that the C6H is unsupported.

Future work includes certificate trust, secure WebSockets, upgrade and registration validation, native pointer holds, and longer endurance testing.

### 15.5 Apple TV

Apple TV compatibility remains a research objective.

Potential requirements include:

- Discovery.
- Pairing.
- Authentication.
- Encrypted communication.
- Session management.
- Protocol-specific command handling.

[pyatv](https://github.com/postlund/pyatv), particularly its modular Companion protocol implementation, remains a useful research reference.

Desktop Python dependencies and asynchronous networking are not assumed to work unchanged on CircuitPython.

Prefer small, purpose-built protocol components over importing an entire desktop framework.

Begin with focused experiments before introducing operational firmware modules.

### 15.6 Amazon Fire TV

Fire TV is reserved in the device-type registry as a future type.

No operational protocol support is currently implemented.

The disabled registry entry communicates architectural intent without pretending the capability exists.

### 15.7 Integration rule

New protocol support must preserve:

- Generic fundamental action identities.
- Stable device identifiers.
- Explicit protocol-aware commands.
- Shared queue execution.
- Cooperative scheduling.
- Bounded resource use.
- Deliberate failure handling.
- Configuration validation boundaries.

**A protocol adapter is not permission to invent another action queue.**

---

## 16. Future Device Destinations

Config v5 currently defines exactly three built-in device slots per configured room.

The TV, AVR, and Streaming labels remain useful organizational roles.

They do not constrain the actual configured device types.

Additional named device destinations remain a future extension.

Potential identifiers include:

```text
device-4
device-5
...
```

Additional destinations could primarily serve Custom Actions involving equipment beyond the three built-in roles.

Their schema, creation, deletion, identity, and reference behavior must be designed before implementation.

Removing a destination must not silently redirect existing actions.

A destination has identity and connection information.

Behavior belongs to actions.

---

## 17. Configuration Recipe Library

**Directory:** `recipes/`

The hosted recipe library provides downloadable configuration examples.

The embedded editor provides Browse Recipes and Import JSON controls.

Recipes are configuration resources, not operational dependencies.

The Clonker does not require access to the hosted recipe site to execute ordinary equipment commands.

### 17.1 Import boundary

Import loads configuration into the browser's editable model.

It does not immediately persist anything to the Pico.

The user reviews and modifies the imported configuration before explicitly saving it.

Imported recipes must not bypass:

- Schema validation.
- Device compatibility rules.
- Revision protection.
- Persistence safeguards.

The active editor requires Config v5.

Older recipe versions are rejected rather than silently migrated.

The hosted library's published examples must be maintained independently of firmware deployment.

### 17.2 Publication boundary

Published recipes should preserve stable identifiers, command mappings, protocol payloads, Custom Action ordering, and delays.

Sensitive credentials must be removed or replaced with explicit placeholders.

For example:

```json
"client_key": "PASTE_OR_PAIR_CLIENT_KEY_HERE"
```

A published placeholder is not an operational credential.

Use a synthetic MAC such as `02:00:00:00:00:00` for published Wake-on-LAN commands. Replace it with the intended equipment MAC before use.

The active configuration can be exported via `GET /api/config`; remove response-only metadata and sanitize credentials before publication. This is an active RAM export, not independent disk verification.

Sanitized recipes must be validated before publication.

**Recipes help configure the Clonker; they do not become a runtime dependency.**

---

## 18. Diagnostics and Verification Discipline

The Clonker uses serial logging, performance instrumentation, memory monitoring, and Flight Recorder diagnostics to support incremental development.

Diagnostics should expose useful operational context without unnecessarily increasing allocation pressure or revealing credentials.

### 18.1 Evidence vocabulary

| Term | Meaning |
|---|---|
| Implemented | Code exists |
| Deployed | Code was copied to the target hardware |
| Verified | Behavior was observed within a specified test scope |
| Regression passed | Previously established behavior survived the tested changes |
| Experimental | Research implementation not yet part of the operational baseline |
| Planned | Future capability |
| Historical | Earlier implementation superseded by current code |

A commit proves source changed.

Deployment proves files were copied.

HTTP 200 establishes a transport-level response.

A successful TCP write establishes that bytes were handed to the network stack.

Equipment observation supports a physical-behavior claim.

These are different evidence levels.

### 18.2 Test inventory

Standalone experiments and regression tests live in:

```text
firmware/tests/
```

They are deployed to:

```text
/tests/
```

on the Pico.

A typical standalone test is executed from the CircuitPython REPL:

```python
exec(open("/tests/test_filename.py").read())
```

The test directory includes both Clonker-specific regression tests and independent hardware, CircuitPython, and protocol experiments.

Not every test is intended to run against an active production application.

Some persistence tests require Pico-owned filesystem writes.

### 18.3 Chapter 12 focused regression suites
### 18.3 Focused regression suites

| Test | Chapter 12 | Chapter 13 |
|---|---:|---:|
| `test_config_validation.py` | 49/49 | 71/71 |
| `test_config_persistence.py` | 56/56 | 56/56 |
| `test_typed_adapters.py` | 56/56 | 85/85 |
| `test_config_activation.py` | 54/54 | 54/54 |
| `test_typed_queue.py` | 92/92 | 153/153 |
| `test_typed_physical.py` | 129/129 | 129/129 |
| **Total** | **436/436** | **548/548** |

Chapter 12 results represent implementation-stage runs. All six Chapter 13 suites passed on the physical Pico after LG and Wake-on-LAN integration, before final comment and editor-label cleanup.

Live testing verified LG SSAP volume, pointer navigation, mute toggles, Custom Actions, network failure recovery, asynchronous rejection cancellation and extended-standby Wake-on-LAN. Actual response-timeout testing and longer endurance remain outstanding.

The Flight Recorder registers the LG transport snapshot as `lg_transport`, exposing session, transmission, response and failure statistics without client keys.

### 18.4 Development discipline

- Preserve known-good configurations.
- Change one meaningful component at a time.
- Test hardware independently before integration.
- Keep optional inputs optional.
- Validate at trust boundaries.
- Avoid unnecessary temporary allocations.
- Record network failures with useful context.
- Keep credentials out of diagnostics and public recipes.
- Avoid excessive production logging.
- Preserve regression tests and standalone experiments.
- Record dated findings in Development History.
- Avoid abstractions without demonstrated requirements.

Passing focused tests does not establish exhaustive reliability.

---

## 19. Architectural Milestones

| Milestone | Architectural result |
|---|---|
| XML v1 | Initial configuration and browser editing foundation |
| Config v2 | JSON validation, revisions, verified persistence |
| Config v3 | Stable generic device identifiers |
| Config v4 | Optional rooms, fundamental actions, Custom Actions |
| Chapters 3–4 | Shared Dumb Queue™, real network execution, cooperative sequences |
| Chapters 5–6 | Physical GPIO integration, room selection, specialized volume adapters |
| Chapter 7 | Physical navigation and playback, explicit button holds, OLED integration |
| Chapter 8 | Lightweight validated configuration access, improved physical responsiveness |
| Chapter 9 | Battery operation, software sleep, monotonic timing |
| Chapters 10–11 | Physical tap/hold refinement, persistent transport improvements, receive draining, Flight Recorder |
| Chapter 12 | Typed devices, protocol-aware commands, central registry, redesigned editor |
| Chapter 12 | Configuration activation lifecycle and obsolete gesture invalidation |
| Chapter 12 | Reduced redundant validation and bounded persistence verification |
| Chapter 13 | Operational LG webOS, asynchronous response handling and shared queue failure propagation |
| Chapter 13 | Reusable Wake-on-LAN transport and endpoint-independent power commands |

Chapter 12 reorganized the existing architecture rather than replacing its fundamental execution model.

The shared action vocabulary, Dumb Queue™, physical controls, cooperative scheduler, and operational Roku and Denon transports remain intact.

The principal architectural change is that device identity and command protocol are now explicit configuration data.

Chapter 13 exercised that foundation without changing the schema version or introducing a second execution queue.

Detailed experiments, dated measurements, and historical implementation decisions belong in [Development History](DEVELOPMENT_HISTORY.md).

---

## 20. Current Boundaries and Open Issues

The current baseline includes operational:

- Generic HTTP commands.
- Denon persistent TCP volume.
- Roku persistent button taps.
- Roku explicit button holds.
- Roku encoder-driven volume holds.
- LG webOS SSAP and pointer commands on tested equipment.
- Wake-on-LAN power and Custom Action commands.
- Physical room selection.
- Fundamental and Custom Action execution.
- Config v5 validation and persistence.
- Protocol-aware browser configuration editing.
- Software sleep and wake.
- Flight Recorder diagnostics.

Remaining boundaries include:

- Intermittent management HTTP socket-send stalls.
- Exhaustive interrupted-write recovery testing.
- Longer-term battery endurance and reliability.
- Integrated LG pairing and credential handoff.
- LG runtime/pairing manifest unification.
- Secure WebSocket and certificate-trust research for newer LG televisions.
- Native LG pointer hold/release support.
- WebSocket upgrade and registration validation hardening.
- Actual LG response-timeout testing and longer transport endurance.
- Additional user-defined device destinations.
- Apple TV and Fire TV protocol research.
- Future hardware-assisted sleep.
- Possible audible feedback.

The observed configuration allocation failures were substantially improved through save-pipeline optimization.

The intermittent socket-send stall has not been eliminated.

These are separate engineering findings.

Do not describe the current firmware as universally fault-free.

---

## 21. Design Principles Worth Remembering

**Less sleek. More CLONK.**

**Smart enough to know when to be dumb.**

**Be resilient in our dumbness.**

**One queue. One poller. One shared execution path.**

**Hardware detects events. Physical coordination maps intent. Actions execute commands.**

**A future task must not hold an immediate button press hostage.**

**One failed external command cancels pending work, not the remote itself.**

**Clonker sends commands. Equipment owns state.**

**Configuration describes the destination and command. The dispatcher schedules it. The adapter delivers it.**

**Validate at trust boundaries, not repeatedly throughout the application.**

**Do not reconstruct trusted data merely to inspect it.**

**A successful save and a successfully delivered save acknowledgment are different events.**

**Do not silently control another room when the selected room is unavailable.**

**A button release belongs to the room where its press began.**

**A command sequence is not permission to invent a workflow engine.**

**A protocol adapter is not permission to invent another action queue.**

> **Do not make the Clonker more complicated merely because we are capable of making it more complicated.**

---

## 22. Reference Documents

- [Configuration, Persistence & Recovery](CONFIGURATION.md) — schema, validation, revisions, persistence, recovery.
- [Configuration Redesign](CONFIGURATION_REDESIGN.md) — Chapter 12 design decisions and implementation foundation.
- [Firmware, Network & Clock](FIRMWARE_NETWORK.md) — scheduler, adapters, transports, timing, diagnostics.
- [Cooperative HTTP Server](COOPERATIVE_HTTP_SERVER.md) — reusable cooperative HTTP server design reference.
- [Operating Modes](OPERATING_MODES.md) — filesystem ownership and application modes.
- [Hardware Design](HARDWARE_DESIGN.md) — physical components, GPIO assignments, construction.
- [Development & Deployment](DEVELOPMENT.md) — deployment workflow and regression testing.
- [Development History](DEVELOPMENT_HISTORY.md) — chronological engineering milestones.
- [Recipe Library](../recipes/) — hosted configuration examples.
- [Chapter 2 Handoff](CHAPTER_2_HANDOFF.md) — historical reference.
- [Old Architecture](OLD_ARCHITECTURE.md) — historical reference.

---

**THE CLONKER 10000**  
*Less sleek. More CLONK.*  
**CLONK! ⚡🔩**
