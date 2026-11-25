# The Clonker 10000 — Firmware, Network & Clock

**Updated:** November 24, 2026  
**Platform:** Raspberry Pi Pico 2 W / CircuitPython 10.3.1  
**Current baseline:** Chapter 12 — The Monster Gets Organized  
**Configuration:** Clonker Config v5

> One Monster. One Dumb Queue™. More than one way to deliver a CLONK.

---

## 1. Purpose and Verified Boundary

This document describes the operational firmware, networking mechanisms, scheduling behavior, transport policies, diagnostics, and known limitations.

Related responsibilities:

- [Architecture](ARCHITECTURE.md) — component boundaries and architectural principles.
- [Configuration](CONFIGURATION.md) — schema, validation, persistence, and recovery.
- [Hardware Design](HARDWARE_DESIGN.md) — physical construction and GPIO assignments.
- [Operating Modes](OPERATING_MODES.md) — filesystem ownership and application modes.
- [Development History](DEVELOPMENT_HISTORY.md) — chronological experiments and engineering decisions.

### 1.1 Operational baseline

Implemented and exercised:

- Wi-Fi networking.
- Config v5 JSON configuration.
- Explicitly typed devices and protocol-aware commands.
- Central device-type registry.
- Browser configuration editor and Test Remote.
- CONFIG-only management HTTP on port 9090.
- Fourteen fundamental actions.
- Room-specific Custom Actions.
- Shared Dumb Queue™.
- Generic outbound HTTP GET/POST.
- Persistent Denon TCP volume control.
- Roku ECP persistent navigation and skip taps.
- Roku ECP physical-button holds.
- Roku ECP encoder-driven volume holds.
- Physical room selection.
- Independent power and mute toggle histories.
- OLED feedback.
- Software sleep and wake.
- Battery-powered operation.
- Flight Recorder diagnostics.
- Revision-protected configuration persistence.
- Configuration recipe import.

### 1.2 Configuration-ready but not operational

Config v5 supports LG webOS device records, client keys, SSAP commands, and pointer commands.

The browser exposes the corresponding configuration fields.

The experimental LG adapter remains disconnected from operational dispatch.

LG pairing and authenticated runtime execution are not yet implemented in the production application.

Apple TV and Amazon Fire TV remain future device types.

### 1.3 Outstanding limitations

- Intermittent management HTTP socket-send stalls.
- Exhaustive interrupted-write recovery testing.
- Long-duration battery endurance.
- Complete reliability under arbitrary network failures.
- Future authenticated protocol integration.

Passing focused regression tests does not establish unlimited operational reliability.

---

## 2. Firmware Layout and Ownership

| Component | Responsibility |
|---|---|
| `firmware/boot.py` | Boot-time filesystem ownership |
| `firmware/code.py` | Application entry |
| `clonker/main.py` | Initialization, modes, cooperative scheduler |
| `clonker/device_config.py` | Config v5 validation, revisions, persistence |
| `clonker/actions.py` | Dumb Queue™, dispatch, sequencing, cancellation |
| `clonker/devices/device_types.py` | Device-type registry |
| `clonker/devices/device_adapters.py` | Adapter selection, execution, lifecycle |
| `clonker/devices/denon.py` | Persistent Denon TCP volume |
| `clonker/devices/roku.py` | Roku ECP transport and held-key behavior |
| `clonker/devices/lg_webos.py` | Experimental LG webOS adapter |
| `clonker/net/http_transport.py` | Generic outbound HTTP |
| `clonker/net/web.py` | Inbound management HTTP |
| `clonker/net/web_diag.py` | Management connection diagnostics |
| `clonker/controls/` | Physical inputs and coordination |
| `clonker/display/oled.py` | OLED feedback and rendering |
| `clonker/system/clock.py` | UTC reference and monotonic timing |
| `clonker/system/logger.py` | Serial logging |
| `clonker/system/perf.py` | Performance measurements |
| `clonker/system/flight_recorder.py` | Diagnostic snapshot capture |
| `clonker/system/sleep_manager.py` | Software sleep and wake policy |
| `clonker/www/` | Embedded browser interfaces |
| `firmware/tests/` | Standalone experiments and regression tests |

Paths beginning with `clonker/` are relative to the firmware root.

Active configuration module filenames no longer contain schema-version suffixes.

The active configuration version is defined by `CONFIG_VERSION` and the persisted JSON.

### 2.1 Separation of responsibilities

```text
Physical input / Browser action
              |
              v
        actions.py
         Dumb Queue™
              |
              v
     Validated configuration
       Typed device record
     Protocol-aware command
              |
              v
 devices/device_adapters.py
              |
       +------+------+ 
       |             |
       v             v
 Device-specific   Generic
    adapter         HTTP
       |             |
       +------+------+
              |
              v
          Equipment
```

Physical drivers do not implement network protocols.

The management web server does not independently execute equipment commands.

The device registry does not establish connections.

The adapter coordinator does not own a second action queue.

---

## 3. Startup, Modes, and Cooperative Scheduling

`code.py` starts `clonker.main.main()`.

The application initializes its services, loads validated configuration, prepares adapter selections, initializes available physical controls, and enters its cooperative event loop.

Missing optional hardware should not prevent the core application from running.

### 3.1 Scheduling targets

The established awake-mode scheduling targets are:

| Responsibility | Target interval |
|---|---:|
| Physical polling | 1 ms |
| Management HTTP polling | 1 ms |
| Action queue polling | 10 ms |
| Main-loop yield | 1 ms |

These are target service intervals, not guaranteed maximum latencies.

The current constants in `main.py` remain authoritative.

The scheduler coordinates:

1. Physical GPIO inputs.
2. Eligible queued action execution.
3. Protocol adapter maintenance.
4. Operating-mode evaluation.
5. Management HTTP when enabled.
6. OLED updates.
7. Memory monitoring.
8. Software sleep policy.
9. Brief cooperative yields.

Adapter maintenance continues even when the action queue is empty.

Roku key releases and Denon receive draining must not depend on the arrival of another user action.

### 3.2 Independent operating modes

| Switch | Open / HIGH | Grounded / LOW |
|---|---|---|
| GP17 | SERVICE | DEVICE |
| GP18 | RUN | CONFIG |

GP17 establishes filesystem ownership at cold boot.

GP18 controls the management HTTP listener during operation.

Changing filesystem ownership requires a full power cycle.

Ctrl+D performs a CircuitPython soft reboot and is not equivalent to a cold boot for filesystem ownership.

| Combination | Behavior |
|---|---|
| SERVICE + CONFIG | Browser inspection and action testing; persistent saves disabled |
| SERVICE + RUN | USB owns filesystem; listener disabled |
| DEVICE + CONFIG | Persistent browser saves permitted |
| DEVICE + RUN | Normal physical remote operation |

The physical equipment Power Toggle is independent of both operating-mode switches.

### 3.3 Physical event polling

The physical coordinator polls:

- Room selector.
- Momentary buttons.
- Volume encoder.
- Custom Action encoder.
- Relevant operating-mode and gesture state.

The room selector requires a valid input and approximately 50 ms stability.

Ordinary momentary buttons use 30 ms debounce.

Navigation and skip buttons use 30 ms press debounce and 10 ms release debounce.

The encoder driver reports completed rotary movements.

The physical coordinator translates those movements into generic actions.

The browser Test Remote's room selection is independent of the physical selector.

### 3.4 Cooperative scheduling limitation

Synchronous network operations can delay subsequent GPIO polling.

A nominal 1 ms physical polling target does not guarantee capture of every electrical transition.

The scheduler cannot preempt a socket operation that has already blocked inside CircuitPython or its networking implementation.

Reducing unnecessary validation, logging, and allocation overhead improves scheduler availability without introducing threads or parallel execution.

---

## 4. Wi-Fi, Endpoints, and Socket Ownership

CircuitPython `wifi.radio` and `socketpool` provide network access.

Wi-Fi credentials belong in private `settings.toml`, not public examples.

The development installation has used:

```text
http://192.168.50.12:9090/
http://192.168.50.12:9090/remote.html
```

These addresses are installation-specific.

### 4.1 Networking responsibilities

The operational firmware has four principal networking responsibilities:

1. Inbound management HTTP.
2. Generic outbound HTTP.
3. Persistent Denon TCP.
4. Roku ECP transport and held-key management.

These mechanisms have different requirements and deliberately different transport policies.

### 4.2 Socket ownership

| Component | Socket behavior |
|---|---|
| Management HTTP | Listening socket and one active client |
| Generic HTTP | Fresh TCP connection per request |
| Denon | One persistent receiver connection |
| Roku | Reusable persistent HTTP connection for selected operations |

The generic HTTP transport reuses its SocketPool object rather than its individual TCP connections.

The Denon adapter owns its connection and pacing state.

The Roku adapter owns persistent HTTP resources and logical held-key state.

Management HTTP does not own outbound equipment sockets.

### 4.3 Independent tuning

Management HTTP and outbound equipment communication should be tuned independently.

The management interface prioritizes reliable administrative transactions and bounded resource use.

Physical remote operations prioritize responsiveness and predictable command execution.

Chapter 12 management HTTP changes did not alter the established outbound Roku, Denon, or generic HTTP transport timing policies.

Do not change working outbound transport settings merely to investigate an inbound management failure.

---

## 5. Inbound Management HTTP

**Modules:** `clonker/net/web.py`, `clonker/net/web_diag.py`, `clonker/main.py`  
**Port:** 9090  
**Availability:** CONFIG mode only  
**Model:** Cooperative single-client listener.

The server accepts one client, receives a bounded request, prepares a response, transmits it incrementally, and closes the connection.

It is not a concurrent web server.

### 5.1 Operational limits

| Setting | Value |
|---|---:|
| Maximum request size | 18432 bytes |
| Maximum header size | 2048 bytes |
| Maximum configuration size | 16384 UTF-8 bytes |
| Configuration POST body allowance | 16640 bytes |
| Receive chunk | 128 bytes |
| Send chunk | 512 bytes |
| Silent-client timeout | 200 ms |
| Active-client timeout | 4 seconds |
| Management polling target | 1 ms |
| Listener restart delay | 5 seconds |

The request capacity includes HTTP framing and headers.

Configuration storage capacity and HTTP request capacity are separate limits.

The application-level timeout cannot interrupt a lower-level socket call that is already blocked.

### 5.2 Management routes

| Request | Responsibility |
|---|---|
| `GET /` | Configuration editor |
| `GET /remote.html` | Browser Test Remote |
| `GET /api/config` | Active configuration and response metadata |
| `POST /api/config` | Revision-protected configuration save |
| `GET /api/clock` | Clock source and timestamp |
| `POST /api/clock?utc=...` | Browser-provided UTC reference |
| `POST /api/action?room=...&action=...` | Admit an action to the shared queue |
| `GET /api/flight-recorder` | Download latest diagnostic snapshot |
| `GET /api/flight-recorder?backup=1` | Download previous snapshot |
| `GET /api/flight-recorder?backup=2` | Download older snapshot |
| `GET /api/flight-recorder?backup=3` | Download oldest retained snapshot |

An action response reporting `queued` means admission to the Dumb Queue™.

It does not establish command transmission or actual equipment execution.

### 5.3 Configuration API metadata

The configuration GET response includes:

- Active schema version.
- Configured rooms.
- Current revision.
- Filesystem writability.
- Device-type registry metadata.

The response-only fields are:

```text
revision
filesystem_writable
device_types
```

These fields are not persisted as part of the configuration schema.

The browser submits the proposed configuration and expected revision.

The firmware remains the authoritative validator.

### 5.4 Bounded response streaming

Static HTML is streamed from flash.

The server retains the response header and current file chunk rather than constructing the entire HTML response in RAM.

Dynamic API responses use the existing response-building path.

The connection state tracks:

- Current send buffer.
- Buffer offset.
- Total transmitted bytes.
- Expected response size.
- Connection timing.
- Response construction timing.

Chapter 8 introduced static streaming after observing unnecessary large allocations during HTML response construction.

Chapter 12 increased management send chunks from 128 to 512 bytes.

This reduced the number of socket calls needed for ordinary page delivery.

It did not eliminate the intermittent ten-second socket-send stall.

### 5.5 Connection-level recovery

Expected nonblocking `EAGAIN` conditions are ordinary control flow.

Receive and send errors normally terminate the affected client transaction.

A failed client does not automatically require rebuilding the listening socket.

For allocation failures escaping `web.poll()`:

1. The scheduler catches `MemoryError`.
2. The active HTTP transaction is discarded.
3. Request, response, file, and client references are released.
4. Normal diagnostic formatting is bypassed where appropriate.
5. Garbage collection runs after cleanup.
6. The application continues.

Unexpected listener errors use a separate teardown and delayed-restart mechanism.

### 5.6 Listener lifecycle

Entering CONFIG starts the management listener.

Entering RUN stops it.

Unexpected listener startup or accept failures are logged.

The scheduler retries listener startup after approximately five seconds while CONFIG remains enabled.

Leaving CONFIG resets the retry deadline.

Earlier fault-injection tests verified:

- Recovery from simulated allocation failures.
- Recovery from unexpected accept failures.
- Recovery from an initial listener startup failure.
- Normal CONFIG → RUN → CONFIG transitions.

These tests establish the intended recovery control flow.

They do not guarantee recovery from every underlying Wi-Fi or socket-stack condition.

### 5.7 Connection diagnostics

`net/web_diag.py` records useful connection-level measurements, including:

- Request route.
- Request size.
- Response construction duration.
- Expected response size.
- Bytes transmitted.
- Send attempts.
- Successful sends.
- EAGAIN occurrences.
- Zero-byte sends.
- Longest individual send duration.
- Slow-send count.
- Connection closure reason.
- Total elapsed time.

Representative output:

```text
WEB DIAG: close=complete, route=...
WEB DIAG: send_calls=..., send_ok=..., EAGAIN=...
WEB DIAG: send_max=...ms, send_slow=...
```

A `close=complete` entry establishes completion through the server's socket interface.

It does not prove that the browser rendered the response.

Detailed management diagnostics remain useful while the intermittent socket-send investigation is open.

### 5.8 Security

The management service has no application-level authentication or HTTPS.

It is intended for a trusted LAN.

Do not expose it directly to the public internet.

Future authenticated device credentials stored in configuration increase the importance of protecting management access and exported files.

---

## 6. Configuration Persistence and Memory Management

**Module:** `clonker/device_config.py`

The configuration engine owns:

- Schema validation.
- Canonical serialization.
- Active validated RAM configuration.
- Revision protection.
- Disk consistency checks.
- Verified persistence.
- Backup rotation.
- Configuration activation.

See [Configuration](CONFIGURATION.md) for the complete schema and persistence contract.

### 6.1 Validate at trust boundaries

Full configuration validation constructs normalized configuration objects.

Repeated validation of already trusted configuration creates unnecessary processing and allocation pressure.

Chapter 8 demonstrated this problem in physical-control paths.

Chapter 12 demonstrated a related problem during configuration saves.

The architectural rule is:

**Validate at trust boundaries, not repeatedly throughout the application.**

Runtime consumers use controlled, read-only accessors to validated configuration.

They must not reconstruct the entire configuration merely to resolve a device or command.

### 6.2 Optimized save pipeline

The Chapter 12 save pipeline:

1. Reclaims temporary allocations.
2. Validates the incoming configuration.
3. Serializes the validated object.
4. Reclaims temporary validation and serialization allocations.
5. Loads and validates the existing primary.
6. Checks disk consistency.
7. Prepares replacement adapter selections.
8. Writes and verifies the temporary file.
9. Rotates backups and installs the primary.
10. Verifies the installed bytes.
11. Activates the replacement configuration.

An unchanged save exits without rewriting flash or replacing active routing state.

Temporary and installed file verification uses bounded 512-byte comparisons.

Already validated serialized data does not require another full JSON parse and validation merely to establish byte equality.

### 6.3 Intentional garbage collection

Two explicit `gc.collect()` calls remain in the production save pipeline:

- At save entry.
- After incoming validation and serialization, before loading the existing primary.

These are intentional administrative memory-management boundaries.

They are not periodic garbage collection in the latency-sensitive physical-control path.

Do not remove or relocate them without regression testing.

### 6.4 Configuration activation

After a successful changed save:

- Existing adapter sessions are retired.
- Prepared adapter selections become active.
- The validated RAM configuration is published.
- Physical configuration-dependent gesture state is cleared.
- Pending actions are canceled.
- Volatile toggle histories are reset.

Session retirement is best effort.

An unchanged save preserves sessions, queue state, and toggle histories.

### 6.5 Persistence versus acknowledgment

Configuration persistence and HTTP response delivery are separate operations.

The primary file may be successfully installed and activated even if the browser does not receive the save acknowledgment.

The browser must not automatically replay a configuration POST following an uncertain outcome.

Instead, reload the active configuration and revision when management HTTP becomes available.

Determine whether the intended change was persisted before attempting another save.

### 6.6 Chapter 12 memory investigation

Temporary `SAVE MEM` checkpoints measured free heap at selected save-processing boundaries.

One successful save entered the pipeline with only 32160 bytes of free heap.

The first explicit garbage collection increased free heap to 243808 bytes.

The second collection reclaimed a further 39456 bytes before disk validation.

These measurements demonstrated substantial reclaimable temporary allocations.

They did not establish a persistent memory leak in CircuitPython or its JSON implementation.

### 6.7 Repeated-save endurance

Twenty consecutive changed browser saves succeeded without rebooting or manually refreshing.

The test covered Room 3 Save Tests 8 through 27.

Selected free-heap measurements:

| Checkpoint | Save 8 | Save 13 | Save 20 | Save 27 |
|---|---:|---:|---:|---:|
| After GC1 | 243808 | 235072 | 236400 | 236416 |
| After GC2 | 230016 | 221280 | 222608 | 222624 |
| After disk validation | 175376 | 166672 | 167984 | 168016 |
| After activation | 142048 | 133376 | 134752 | 134784 |

The initial reduction in available heap did not continue progressively.

The final two sampled post-collection measurements differed by only 16 bytes.

No progressive heap depletion was evident in these samples.

### 6.8 Save performance

Representative measured save durations:

| Implementation | Save duration |
|---|---:|
| Earlier instrumented implementation | 2361.7 ms |
| Optimized implementation with targeted GC | 1345.1 ms |

The final sampled save was approximately 43% shorter.

Three additional changed saves succeeded after removal of temporary memory diagnostics.

Post-cleanup configuration save durations were approximately 1.3–1.4 seconds.

Subsequent configuration GET requests completed in approximately 0.4 seconds.

Production `CONFIG PERF` timing remains enabled.

Temporary `SAVE MEM` checkpoints were removed.

### 6.9 Evidence limits

The repeated-save allocation failure was substantially improved under the tested conditions.

Heap fragmentation remains a plausible contributor to earlier allocation failures but was not directly measured.

A CircuitPython JSON memory leak has not been demonstrated.

The intermittent management socket-send stall remains unresolved and must not be conflated with the improved save-memory behavior.

---

## 7. The Dumb Queue™

**Module:** `clonker/actions.py`

The Dumb Queue™ is the shared execution mechanism for physical and browser actions.

Its responsibilities include:

- Action admission.
- Bounded pending work.
- Eligibility and ordering.
- Command resolution.
- Adapter readiness.
- Execution.
- Custom Action progression.
- Failure cancellation.

### 7.1 Capacity and identity

The queue holds up to 128 entries.

Ordinary tasks identify the room and action.

Custom Action tasks additionally retain step progression and eligibility timing.

Explicit physical hold events retain their original validated device and command references.

The queue does not persist pending work across reboot.

### 7.2 Eligibility

The first eligible task is selected.

A task waiting for a future deadline does not block immediate eligible work.

If the selected adapter is not ready, the task remains pending rather than allowing later eligible work to overtake it.

At most one eligible queued command executes per action poll.

### 7.3 Fundamental actions

Fundamental actions resolve their typed device and protocol-aware command from active validated configuration.

Blank endpoints and selected blank commands produce intentional no-ops.

Disabled device types must not silently fall back to generic HTTP.

### 7.4 Toggle histories

Power and mute toggles use independent ON and OFF command objects.

The dispatcher tracks next-direction history by room and action.

Successful execution advances the history.

Failure or an intentional no-op does not.

A changed configuration save or reboot resets the history.

The remote does not query actual equipment state to determine toggle direction.

### 7.5 Custom Actions

A Custom Action occupies one queue task while progressing through its ordered steps.

Each step executes one configured command.

After successful completion, a nonfinal step establishes its next monotonic eligibility deadline.

Other eligible work may execute during the wait.

Existing Roku and Denon Custom Action steps retain ordinary single-command HTTP behavior.

They do not implicitly acquire specialized hold or repeat behavior.

### 7.6 Failure policy

An execution exception cancels remaining pending work.

Unfinished Custom Actions are canceled.

New work may subsequently be admitted.

Uncertain commands are not automatically replayed.

Adapter-specific key-release cleanup is a separate safety mechanism.

A failed command may already have reached the equipment.

Blind replay could duplicate the intended action.

### 7.7 Physical hold context

Explicit hold events preserve the device and command associated with the original press.

A later room change must not redirect the release.

When queue capacity temporarily prevents release admission, the physical coordinator retains the necessary release context.

This is gesture bookkeeping, not a second execution queue.

A successful changed configuration save invalidates obsolete gesture state.

---

## 8. Device Registry and Adapter Coordinator

**Modules:**

```text
clonker/devices/device_types.py
clonker/devices/device_adapters.py
```

### 8.1 Device registry

The registry defines device identity, supported command kinds, runtime availability, suggested ports, additional attributes, and pairing capability.

| Type | Command kinds | Runtime |
|---|---|---|
| `generic-http` | HTTP | Enabled |
| `denon` | HTTP | Enabled |
| `roku` | HTTP | Enabled |
| `lg-webos` | SSAP, Pointer | Disabled pending integration |
| `apple-tv` | None | Future |
| `fire-tv` | None | Future |

The registry does not import protocol implementations or establish network connections.

### 8.2 Adapter selection

Config v5 explicitly identifies the device type.

Specialized execution additionally depends on action context and recognized command mappings.

A generic HTTP device does not acquire Denon or Roku specialization solely because its path resembles one of their commands.

### 8.3 Operational execution paths

| Path | Selection | Transport |
|---|---|---|
| `denon-tcp` | Recognized Denon fundamental volume | Persistent TCP port 23 |
| `roku-volume-hold` | Recognized Roku fundamental volume | Persistent ECP keydown/keyup |
| `roku-button-tap` | Recognized Roku navigation/skip tap | Persistent ECP keypress |
| `roku-button-hold` | Explicit supported physical hold event | Persistent ECP keydown/keyup |
| `generic-http` | Other compatible operational HTTP commands | Fresh bounded HTTP request |

### 8.4 Recognized Denon commands

Method: GET

```text
/goform/formiPhoneAppDirect.xml?MVUP
/goform/formiPhoneAppDirect.xml?MVDOWN
```

The configured device must explicitly be type `denon`.

These mappings select native TCP volume execution.

### 8.5 Recognized Roku volume commands

Method: POST

```text
/keypress/VolumeUp
/keypress/VolumeDown
```

The configured device must explicitly be type `roku`.

These mappings select encoder-driven held-volume execution.

### 8.6 Recognized Roku navigation and skip commands

Method: POST

```text
/keypress/Up
/keypress/Down
/keypress/Left
/keypress/Right
/keypress/Rev
/keypress/Fwd
```

Compatible ordinary actions select persistent taps.

Compatible physical hold events select explicit keydown/keyup execution.

### 8.7 Adapter cache

Specialized fundamental selections are cached by:

```text
(room_id, action_id)
```

Physical hold selections use:

```text
("hold", room_id, action_id)
```

The cache is derived from validated configuration.

It is not persisted as equipment state.

Cache preparation and publication are separate operations.

A replacement cache is prepared before changed configuration persistence and published during activation.

### 8.8 Lifecycle interface

The coordinator provides:

- Execution-path resolution.
- Cache preparation and publication.
- Adapter readiness.
- Ordinary command execution.
- Supported physical hold execution.
- Maintenance polling.
- Active-state cancellation.
- Session retirement.

The coordinator receives typed device records and protocol-aware command objects.

Protocol-specific behavior remains in the appropriate adapter.

---

## 9. Denon Persistent TCP Adapter

**Module:** `clonker/devices/denon.py`  
**Port:** TCP 23  
**Commands:** `MVUP`, `MVDOWN`

### 9.1 Established timing

```python
TCP_PORT = 23
SOCKET_TIMEOUT = 1.0
MIN_COMMAND_INTERVAL = 0.05
```

The configured HTTP endpoint identifies the receiver host.

Specialized volume execution uses native TCP port 23 independently of the configured HTTP port.

### 9.2 Connection lifecycle

The adapter maintains one persistent receiver connection.

Subsequent commands to the same receiver reuse it.

Changing receivers retires the previous connection.

Closing the adapter resets socket, host, and pacing state.

It is not a pool of simultaneous receiver connections.

### 9.3 Pacing

`ready()` checks the monotonic send deadline.

The dispatcher preserves a selected task when the adapter is not ready.

Native volume commands are ASCII strings terminated by carriage return.

Examples:

```text
MVUP\r
MVDOWN\r
```

Successful transmission advances the next allowed send time by at least 50 ms.

An execution exception closes the connection and propagates to the queue failure policy.

Uncertain commands are not automatically retried.

### 9.4 Receive draining

Persistent Denon connections can accumulate unread responses and unsolicited receiver messages.

Earlier firmware did not sufficiently drain this data.

Chapter 11 added receive draining and periodic adapter maintenance following an observed freeze during heavy volume use.

Aggressive subsequent volume testing did not reproduce that freeze.

Receive draining is transport maintenance.

It does not establish an authoritative receiver-state model.

### 9.5 Chapter 12 verification

Live Denon TCP volume execution passed following the typed-adapter redesign.

Representative observations included:

- Initial volume command: approximately 104 ms.
- Subsequent command on the existing connection: approximately 3 ms.

During the later management socket investigation:

- Initial connection and command: approximately 204 ms.
- Subsequent commands: approximately 2.6–2.8 ms.

These measurements are observations, not guaranteed latencies.

### 9.6 Limitations

The adapter does not:

- Maintain authoritative receiver state.
- Interpret every unsolicited Denon message.
- Maintain simultaneous connections to every configured AVR.
- Automatically replay uncertain volume commands.
- Guarantee actual receiver execution after a successful TCP write.

---

## 10. Roku Persistent HTTP Transport

**Module:** `clonker/devices/roku.py`

The Roku adapter uses a code-defined transport policy.

Selected ECP operations use persistent HTTP.

Other compatible commands retain ordinary generic HTTP execution.

### 10.1 Established timing

| Parameter | Value |
|---|---:|
| Per-operation socket timeout | 500 ms |
| Total request deadline | 1.5 seconds |
| Connection reuse window | 1 second |
| Failed-release retry interval | 500 ms |

The current adapter constants remain authoritative.

### 10.2 Persistent connection behavior

A successful request may leave the connection eligible for reuse.

Repeated compatible requests can avoid a new TCP connection.

Idle or obsolete connections are retired.

Endpoint changes require appropriate connection replacement.

Transport failures close or invalidate the affected connection.

The adapter does not automatically replay uncertain navigation taps or keydown commands.

### 10.3 Navigation and skip taps

Recognized navigation and skip commands use persistent ECP keypress requests.

Examples:

```text
POST /keypress/Right
POST /keypress/Left
POST /keypress/Fwd
POST /keypress/Rev
```

Persistent reuse improves repeated button responsiveness without changing the fundamental action vocabulary.

### 10.4 Verified performance

Earlier November 18 testing measured:

- New connection taps: approximately 135–146 ms.
- Reused connection taps: approximately 34–43 ms.

Chapter 12 regression testing measured:

- New connection tap: approximately 141 ms.
- Reused taps: approximately 38–39 ms.

Later testing during the management socket investigation measured reused taps at approximately 36–44 ms.

The typed configuration redesign did not introduce an evident regression in these sampled operations.

---

## 11. Roku Encoder-Driven Volume Holds

**Module:** `clonker/devices/roku.py`

The volume adapter converts encoder movement into temporary Roku ECP key holds.

This avoids one HTTP request per encoder detent.

### 11.1 Established timing

| Parameter | Value |
|---|---:|
| Idle release | 250 ms |
| Maximum continuous volume hold | 2 seconds |
| Failed-release retry | 500 ms |

These are experimentally selected behavior parameters.

They do not guarantee identical volume changes across equipment combinations.

### 11.2 First detent

A new direction starts the appropriate held key.

Example:

```text
POST /keydown/VolumeUp
```

Following successful acknowledgment, the adapter records:

- Endpoint.
- Direction.
- Hold start time.
- Idle-release deadline.

An uncertain keydown is not automatically replayed.

### 11.3 Same-direction movement

Additional same-direction detents extend the idle deadline.

No additional HTTP request is required.

The execution log distinguishes a new `keydown` from a local `extended` operation.

Chapter 12 local extension measurements were commonly approximately 0.7–1.0 ms.

### 11.4 Idle release

When encoder activity stops, the idle deadline eventually expires.

Adapter maintenance attempts the corresponding release:

```text
POST /keyup/VolumeUp
```

This maintenance continues independently of queue depth.

### 11.5 Direction reversal

Reversal requires release of the previous key before starting the opposite hold.

Example:

```text
POST /keyup/VolumeUp
POST /keydown/VolumeDown
```

An unresolved release must not knowingly be bypassed by a new opposing hold.

### 11.6 Maximum hold

A continuous volume hold is bounded to approximately two seconds.

Continued rotation can require release and a new hold.

This prevents a single local hold from extending indefinitely.

### 11.7 Failed-release safety

If keyup fails, unresolved held-key state is retained.

Release attempts are paced rather than retried on every scheduler iteration.

This is specialized cleanup behavior, not general action replay.

Network failure can still prevent confirmation that a remote key was released.

### 11.8 Chapter 12 verification

Live Sunroom testing verified:

- Initial volume keydown.
- Same-direction local extensions.
- Direction reversal.
- Idle release.
- Responsive physical operation.

During the later management HTTP investigation, initial volume keydowns were approximately 113–114 ms, with local extensions around 0.7 ms.

### 11.9 Limitations

The adapter does not guarantee:

- One receiver volume step per encoder detent.
- A fixed volume-change rate.
- Zero overshoot.
- Actual receiver volume knowledge.
- Successful release when equipment becomes unreachable.

It is a time-based physical control mechanism, not a volume-position controller.

---

## 12. Roku Physical Navigation and Skip Holds

**Modules:**

```text
clonker/controls/physical.py
clonker/actions.py
clonker/devices/device_adapters.py
clonker/devices/roku.py
```

The four navigation buttons and two skip buttons support specialized Roku tap/hold behavior.

### 12.1 Supported controls

| Action | Roku key |
|---|---|
| `nav-up` | Up |
| `nav-down` | Down |
| `nav-left` | Left |
| `nav-right` | Right |
| `skip-back` | Rev |
| `skip-forward` | Fwd |

Specialization requires a compatible explicitly typed Roku device and recognized POST command.

### 12.2 Press-first behavior

With:

```python
NAV_PRESS_FIRST = True
```

The physical coordinator:

1. Queues an ordinary tap immediately after the debounced press.
2. Promotes a sustained press to a hold after 250 ms.
3. Queues the corresponding release when the button is released.
4. Does not issue an additional command for an ordinary short-press release.

A sustained press may produce an initial movement followed by the native held-key behavior.

This was accepted as a practical tradeoff for immediate tap responsiveness.

### 12.3 Release-first alternative

With `NAV_PRESS_FIRST = False`, the original release-first behavior remains available.

Short presses dispatch on release.

Sustained presses use hold start and release.

The choice affects gesture interpretation rather than the underlying Roku protocol.

### 12.4 Ordinary fallback

A compatible HTTP action without specialized hold support receives one ordinary command.

The firmware does not invent repeat behavior for an arbitrary configured HTTP endpoint.

### 12.5 Preserved gesture context

A physical hold retains its original:

- Room.
- Action.
- Typed device.
- Command object.
- Adapter selection.
- Gesture timing.

Changing rooms while holding a button must not redirect its release.

A temporarily full queue does not justify discarding the original release context.

### 12.6 Configuration-change reset

A changed configuration save clears outstanding physical gestures and pending release bookkeeping.

The dispatcher clears obsolete queued work.

Adapter activation retires existing sessions.

This prevents a pre-save gesture from restarting against obsolete configuration.

### 12.7 Protocol execution

The Roku adapter translates supported events into:

```text
POST /keydown/<key>
POST /keyup/<key>
```

Physical-button hold state is separate from encoder-driven volume hold state.

A maximum hold safety limit bounds continuous remote key activity.

Failed releases retain their state and use paced retry behavior.

Uncertain taps and keydowns are not automatically replayed.

### 12.8 Regression evidence

The Chapter 12 typed physical regression suite passed 129 assertions.

Coverage included:

- Immediate tap behavior.
- Hold promotion.
- Release behavior.
- Navigation and skip controls.
- Room changes during holds.
- Ordinary HTTP fallback.
- Blank commands and endpoints.
- Queue capacity handling.
- Pending release ordering.
- Configuration-change reset.

Live Roku navigation tap and hold execution also passed.

The automated suite and live tests are complementary evidence.

---

## 13. Generic Outbound HTTP

**Module:** `clonker/net/http_transport.py`

The generic HTTP transport provides bounded synchronous GET and POST requests.

### 13.1 Responsibilities

It handles:

- Ordinary Roku ECP commands.
- Denon HTTP commands.
- Existing Roku and Denon Custom Action steps.
- Other compatible generic HTTP commands.

Each ordinary request uses a fresh TCP connection.

The transport reuses its SocketPool object.

It does not reuse individual ordinary HTTP connections.

### 13.2 Transport policy

Generic HTTP remains intentionally small.

It is not:

- A general-purpose browser.
- A TLS client.
- A comprehensive HTTP library.
- An authenticated session framework.
- A concurrent execution engine.

Current timeout and request-format constants remain defined in `http_transport.py`.

Management HTTP timeout changes must not silently alter outbound transport behavior.

### 13.3 Verified behavior

Chapter 12 live tests exercised generic HTTP power, mute, Home, and Custom Action commands.

Representative observed durations were approximately 110–150 ms.

During the later management socket failure investigation:

- Roku Home completed in approximately 141 ms.
- The Sunroom Movie Custom Action completed its Roku command, cooperative three-second wait, and Denon command.

These results support continued use of the existing outbound transport.

### 13.4 Failure behavior

Transport exceptions propagate to the dispatcher.

Remaining pending work is canceled.

Uncertain commands are not automatically repeated.

A successful HTTP response is not independent confirmation of physical equipment state.

---

## 14. Development Equipment Configuration

The development installation uses two operational rooms and an optional third test room.

The following addresses describe the Chapter 12 development installation, not firmware defaults.

| Room | Equipment | Endpoint |
|---|---|---|
| Den | Denon AVR | `192.168.50.44:8080` |
| Den | Roku | `192.168.50.43:8060` |
| Sunroom | Denon AVR | `192.168.50.40:8080` |
| Sunroom | Roku | `192.168.50.28:8060` |

### 14.1 Mixed volume control

The Den volume encoder targets Denon.

The Sunroom volume encoder targets Roku.

The same physical encoder therefore exercises different transport mechanisms according to the selected room.

No manufacturer-specific behavior is required in the encoder driver.

### 14.2 Power and mute

The development configuration uses Roku for equipment power commands.

Mute mappings are room-specific.

The Den targets Denon mute.

The Sunroom targets Roku mute.

Toggle histories remain independent by room and action.

### 14.3 Custom Actions

The development configuration includes named actions such as:

- Movie.
- Music.
- Vinyl.
- Audio Cycle.

The available list varies by room.

The verified Sunroom Movie sequence performs:

1. Roku Home.
2. A cooperative 3000 ms wait.
3. Denon Quick Select 1.

This sequence uses the same Dumb Queue™ as ordinary physical commands.

### 14.4 Room 3

Room 3 has been used as a blank configuration placeholder and management persistence test room.

Blank device endpoints are valid.

Changing the test room name during persistence experiments does not require executing equipment commands.

The browser supports removing and recreating room slots without renumbering existing rooms.

---

## 15. Clock and Timing

**Modules:**

```text
clonker/system/clock.py
clonker/system/logger.py
```

### 15.1 UTC reference

Before browser synchronization, the firmware uses `DEFAULTTIME` and monotonic uptime rather than asserting an authoritative wall-clock date.

The browser can provide UTC Unix time through:

```text
POST /api/clock?utc=...
```

Readable timestamps are calculated using that reference and subsequent monotonic elapsed time.

Automated NTP synchronization is not established by the current verified baseline.

### 15.2 Monotonic timing

Scheduling and elapsed-time measurements use monotonic time.

This includes:

- Queue eligibility.
- Custom Action waits.
- Denon pacing.
- Roku hold deadlines.
- Release retry timing.
- Management connection deadlines.
- Performance measurement.
- Memory-monitor intervals.
- Software sleep inactivity.

Changing the UTC reference must not shift these deadlines.

Human-readable timestamps and scheduling time are separate concerns.

### 15.3 Timebase discipline

Chapter 9 unified application timing around monotonic measurements.

Diagnostic comparisons should use a consistent elapsed-time reference.

Wall-clock synchronization must not introduce discontinuities into protocol state machines or queue scheduling.

---

## 16. Logging and Performance Diagnostics

### 16.1 Serial logging

Serial diagnostics record:

- Startup.
- Configured rooms.
- Operating-mode transitions.
- Physical actions.
- Queue admission.
- Execution results.
- Adapter failures.
- Configuration save timing.
- Memory observations.
- Management connection diagnostics.

Logs should expose useful context without revealing private credentials or unnecessarily dumping protocol payloads.

### 16.2 Shared PERF infrastructure

**Module:** `clonker/system/perf.py`

The reusable performance helper supports:

- Named measurements.
- Start/stop timing.
- Direct elapsed-time recording.
- Accumulated statistics.
- Snapshot generation.
- Reporting interval resets.

The established scheduler-level diagnostic settings include:

```python
PERF_ENABLED = True
PERF_INTERVAL_NS = 30_000_000_000
GC_TEST_ENABLED = False
```

PERF reports are generated approximately every 30 seconds when enabled.

### 16.3 Physical internal instrumentation

The physical coordinator supports focused internal diagnostics.

The established normal baseline is:

```python
PHYSICAL_PERF_ENABLED = False

PERF_SCAN = False
PERF_EVENTS = False
PERF_VOLUME = False
PERF_DISPATCH = False
PERF_HOLD = False
```

Disabling internal physical instrumentation does not disable scheduler-level timing of physical polling.

Enable only the measurements needed for a specific investigation.

### 16.4 Interpreting measurements

Distinguish:

1. Physical polling gap.
2. Physical polling execution duration.
3. Network execution duration.
4. Adapter maintenance duration.
5. Management HTTP duration.
6. Configuration persistence duration.

A blocking network operation can delay the next physical poll without increasing the measured execution duration of the physical poll itself.

Chapter 8 traced physical execution spikes to repeated configuration validation.

Replacing that validation with lightweight configuration access substantially reduced physical execution overhead.

Blocking network operations remain a separate source of scheduler gaps.

### 16.5 Memory measurements

Free heap and allocated heap are useful observations.

They do not independently establish the size of the largest available contiguous allocation.

Temporary allocation growth between garbage collections is not necessarily a memory leak.

Compare equivalent lifecycle checkpoints when evaluating memory trends.

The Chapter 12 repeated-save experiment demonstrated the value of deliberate collection boundaries and reduced temporary allocation.

### 16.6 Production versus experimental diagnostics

Retain useful production diagnostics.

Remove temporary high-volume instrumentation after an investigation concludes.

Chapter 12 retained:

- `CONFIG PERF` timing.
- Management connection diagnostics.
- Memory monitoring.
- Flight Recorder capture.

Temporary `SAVE MEM` checkpoints were removed after successful post-cleanup regression testing.

---

## 17. Flight Recorder

**Module:** `clonker/system/flight_recorder.py`

The Flight Recorder retains recent diagnostic information for deliberate capture before reboot.

### 17.1 RAM history

The recorder retains the most recent 64 logger messages in a bounded ring buffer.

Older messages are overwritten.

Diagnostic providers are registered during application startup and evaluated when a snapshot is requested.

Established providers include:

- Performance statistics.
- Memory statistics.
- RUN-exit memory checkpoint.
- Queue state.
- Physical event and dispatch counters.

Adapter diagnostics can provide additional transport context.

### 17.2 RUN-exit memory checkpoint

Before CONFIG services start, the firmware records a memory checkpoint associated with the RUN → CONFIG transition.

This captures:

- Uptime.
- Free heap.
- Allocated heap.

The checkpoint does not force garbage collection.

It is retained in RAM for inclusion in the next Flight Recorder snapshot.

This distinguishes memory observed during normal RUN operation from memory observed later during CONFIG operation and snapshot capture.

Earlier verification recorded:

- RUN-exit checkpoint at 39 seconds: 214656 bytes free.
- Regular snapshot at 46 seconds: 250960 bytes free.

The difference did not independently establish a leak.

### 17.3 Deliberate snapshot capture

A completed secret manual-reboot handshake requests a synchronous diagnostic snapshot before reboot.

The writer streams a human-readable text file.

Completed snapshots are rotated.

### 17.4 Snapshot files

| File | Purpose |
|---|---|
| `/clonker/flight_recorder.txt` | Latest completed snapshot |
| `/clonker/flight_recorder.txt.1` | Previous snapshot |
| `/clonker/flight_recorder.txt.2` | Older snapshot |
| `/clonker/flight_recorder.txt.3` | Oldest retained snapshot |
| `/clonker/flight_recorder.tmp` | Temporary write |

Rotation is not fully atomic across power loss.

### 17.5 Filesystem ownership

Successful snapshot writes require Pico-owned filesystem writes.

In SERVICE mode, the application normally cannot write these files.

Snapshot failures are caught and do not prevent a deliberate reboot.

### 17.6 Persistence policy

Snapshots are written during the deliberate manual-reboot procedure.

There are no periodic Flight Recorder flash writes in ordinary physical button dispatch.

Earlier snapshot writes took approximately 225–484 ms.

This synchronous work is acceptable during deliberate reboot.

Scheduled or frequent snapshots would require separate evaluation.

### 17.7 HTTP retrieval

In CONFIG mode, the existing management server provides read-only retrieval:

```text
GET /api/flight-recorder
GET /api/flight-recorder?backup=1
GET /api/flight-recorder?backup=2
GET /api/flight-recorder?backup=3
```

Responses use plain text and an appropriate download filename.

Files are streamed in bounded chunks.

Invalid backup parameters return HTTP 400.

Missing snapshots return HTTP 404.

Retrieval does not create, rotate, clear, or modify snapshots.

The original latest-snapshot endpoint was verified on November 19 with an approximately 8 KB response completing in about 398 ms.

Backup selection was implemented; exhaustive retrieval testing of every rotated generation remains a separate verification item.

### 17.8 Limitations

The recorder captures the state at snapshot time.

It does not necessarily preserve the state at the beginning of an earlier malfunction.

The 64-message ring buffer can overwrite earlier evidence.

Unexpected power loss does not automatically trigger a snapshot.

Continuous excessive logging can reduce the useful historical window and distort application timing.

---

## 18. Software Sleep and Wake

**Module:** `clonker/system/sleep_manager.py`

The current power-management mechanism is software sleep.

It is not hardware light sleep or deep sleep.

The CPU continues running to monitor physical wake inputs.

### 18.1 Sleep eligibility

Sleep requires:

- Sleep policy enabled.
- CONFIG mode inactive.
- Inactivity timeout elapsed.
- No pending queued actions.

CONFIG mode inhibits sleep.

Physical activity resets inactivity timing.

### 18.2 Sleep entry

The established sleep sequence:

1. Display `Going Zzzz!`.
2. Close the OLED and release its I²C resources.
3. Disable the Wi-Fi radio.
4. Enter software sleep state.

Shutdown failures use recovery reboot rather than intentionally remaining partially shut down.

### 18.3 Asleep scheduling

While asleep:

- Physical GPIO polling continues.
- Action execution is suspended.
- Adapter maintenance is suspended.
- Management HTTP cannot start.
- OLED polling is suspended.
- Memory-monitor polling is suspended.
- Main-loop delay increases to 25 ms.

Very short wake-button presses may be missed.

### 18.4 Wake behavior

Wake-eligible inputs include supported momentary button presses and a physical CONFIG/RUN switch transition.

Encoder rotation and room-selector movement do not wake the Clonker.

The wake-triggering input is consumed rather than dispatched as an equipment command.

Real wake calls `microcontroller.reset()`.

Normal application initialization restores networking and services.

Dry-run sleep restores simulated awake state without rebooting.

### 18.5 Runtime override

The physical coordinator recognizes the room-selector sequence:

```text
1 -> 2 -> 1 -> 2 -> 1 -> 2
```

The sequence must occur within ten seconds while the physical CONFIG switch is enabled.

The sleep manager toggles its volatile enabled state.

OLED confirmation reports:

```text
SLEEP ON
SLEEP OFF
```

A reboot restores the configured startup default.

### 18.6 Earlier power measurements

Approximate USB-side measurements at 5 V:

| Condition | Current |
|---|---:|
| Awake RUN | 38 mA |
| Initial software sleep | 25 mA |
| Optimized software sleep | 24 mA |

These measurements do not include all battery conversion losses or power-module consumption.

Battery-powered sleep and wake have been demonstrated.

Earlier overnight testing covered approximately twelve hours.

Full-discharge endurance and hardware-assisted sleep remain separate investigations.

---

## 19. The Intermittent Ten-Second Socket Gremlin

**Status: OPEN**

This issue predates Config v5 and remains unresolved after Chapter 12.

It must be distinguished from the configuration-save allocation failures that were substantially improved through save-pipeline optimization.

### 19.1 Observed behavior

Individual management socket sends occasionally take approximately ten seconds to return despite intended nonblocking operation.

Symptoms include:

- Partial HTML responses.
- Partial JSON responses.
- Browser timeouts.
- Uncertain save outcomes.
- Repeated failures across new client connections.
- Successful byte counts returned after unusually long send calls.

The duration is remarkably consistent, often close to 10005 ms.

This is suggestive of an internal timeout mechanism but does not identify the responsible implementation layer.

### 19.2 Earlier investigation

November 15–16 experiments investigated:

- Management chunk size.
- Web polling frequency.
- Adapter polling interaction.
- Filesystem ownership.
- Battery versus USB power.
- Attached serial console.
- Flash writes and backup rotation.

No reliable trigger was established.

The standalone `socket_send_stall.py` experiment did not reproduce the production failure.

### 19.3 Chapter 12 production observations

The failure occurred during ordinary GET requests as well as configuration saves.

Representative observations with 128-byte send chunks included:

- Configuration responses stalling after approximately 1664 transmitted bytes.
- HTML responses stalling after approximately 1662 or 2046 transmitted bytes.
- Individual send durations around 10005 ms.
- No corresponding EAGAIN events.

Small clock responses sometimes continued working.

Both Safari and Chrome experienced failures.

Stopping and restarting the management listener did not reliably clear the condition.

### 19.4 Standalone socket pacing laboratory

**Test:**

```text
firmware/tests/socket_send_pacing.py
```

The laboratory uses a separate HTTP listener on port 9091.

It allows adjustment of:

- Response body size.
- Send chunk size.
- Send delay.
- Connection cooldown.
- Repeated request count.

The laboratory is independent of the production configuration editor and does not perform configuration flash writes.

### 19.5 Laboratory results

| Body size | Chunk | Delay | Requests | Result |
|---|---:|---:|---:|---|
| 8700 bytes | 128 | 0 ms | 20 | 20/20 |
| 37500 bytes | 128 | 0 ms | 20 | 20/20 |
| 37500 bytes | 128 | 5 ms | 20 | 20/20 |
| 37500 bytes | 128 | 0 ms | 40, two browsers | 40/40 |

One concurrent-client test produced 384 EAGAIN events during a successful response.

The response completed in approximately 882 ms without a slow-send event.

This demonstrates successful handling of substantial nonblocking backpressure within the laboratory.

It does not establish that the laboratory reproduces every relevant production condition.

The server still processes one active client at a time.

Across the explicitly counted batches, 100 requests succeeded.

The production ten-second stall was not reproduced.

### 19.6 Management chunk-size change

Production management send chunks were increased from 128 to 512 bytes.

Ordinary page delivery became more efficient.

The original intermittent stall nevertheless returned.

Chunk size alone is therefore not a demonstrated solution.

No artificial send delays or connection cooldowns were introduced into the production management server.

### 19.7 Distinguishing the two failures

Following the configuration-save memory improvements, twenty consecutive changed saves succeeded.

After normal physical operation and a CONFIG → RUN → CONFIG transition, Save Test 28 encountered another management HTTP failure.

The serial log established:

- Configuration validation succeeded.
- Disk consistency checks succeeded.
- Persistence succeeded.
- Installed file verification succeeded.
- Configuration activation succeeded.
- Physical and queue resets succeeded.

The subsequent HTTP acknowledgment stalled.

A single send of only 188 bytes took approximately 10004 ms.

This establishes that a large response is not necessary for the failure to occur.

### 19.8 Persistent failure state

Subsequent requests showed:

| Request | Expected bytes | Sent bytes | Longest send |
|---|---:|---:|---:|
| POST `/api/config` | 188 | 188 | 10004.2 ms |
| GET `/` | 37578 | 638 | 10004.7 ms |
| GET `/api/config` | 8773 | 1024 | 10004.2 ms |
| GET `/api/config` | 8773 | 1024 | 10004.3 ms |

The failure persisted across multiple management client connections.

No configuration allocation failure accompanied this incident.

### 19.9 Outbound operation during investigation

Browser tabs were closed.

Without rebooting or changing operating modes, physical controls were exercised.

Observed successful operations included:

- Generic HTTP Roku Home.
- Persistent Roku navigation taps.
- Roku volume holds.
- Denon persistent TCP volume.
- Sunroom Movie Custom Action.

Representative measurements:

| Operation | Observed duration |
|---|---:|
| Roku Home | 141.3 ms |
| New Roku navigation connection | 140.5 ms |
| Reused navigation connection | 35.8–44.4 ms |
| Roku volume keydown | 113–114 ms |
| Local volume extension | 0.7 ms |
| Initial Denon connection | 203.8 ms |
| Subsequent Denon volume | 2.6–2.8 ms |

The physical controls remained responsive during these tests.

This establishes healthy outbound operation between failed management requests.

It does not establish physical responsiveness during an individual ten-second blocking send.

### 19.10 Recovery without reboot

Following the physical-control tests, management HTTP recovered.

Successful responses included:

| Request | Bytes | Total duration |
|---|---:|---:|
| GET `/` | 37578 | 575.1 ms |
| GET `/api/clock` | 180 | 32.2 ms |
| GET `/api/config` | 8773 | 406.5 ms |
| GET `/api/config` | 8773 | 420.0 ms |

No slow sends or EAGAIN events were reported in these successful responses.

The recovered configuration confirmed that Save Test 28 had persisted.

Save Test 29 subsequently succeeded.

No reboot, explicit listener restart, or manual REPL garbage collection was required.

### 19.11 What remains unknown

The recovery mechanism was not isolated.

Possible contributors include:

- Expiration of TCP connection state.
- Closing browser tabs.
- Elapsed time without management requests.
- Outbound socket activity.
- Production socket lifecycle behavior.
- CircuitPython or underlying networking-stack behavior.

None has been established as the root cause.

The experiments do not prove a CircuitPython, CYW43, or lwIP defect.

### 19.12 Next recurrence procedure

If the failure returns:

1. Preserve serial diagnostics.
2. Avoid immediately repeating an uncertain configuration POST.
3. Close Clonker browser tabs.
4. Leave CONFIG mode unchanged.
5. Avoid physical equipment commands for two minutes.
6. Attempt one direct GET of `/api/config`.
7. Record whether recovery occurred.

This proposed passive-recovery experiment separates elapsed time and browser disconnection from outbound equipment activity.

If passive recovery fails, repeat the previously successful outbound-control experiment.

Do not introduce speculative networking changes until the evidence justifies them.

### 19.13 Engineering conclusion

The observed configuration allocation failures and intermittent socket stalls are distinguishable failure mechanisms.

A shared underlying contributor has not been ruled out.

The optimized persistence pipeline should remain intact.

Working outbound transport policies should remain intact.

The socket pacing laboratory and useful production connection diagnostics should be preserved.

**The Monster has two gremlins. One has been substantially addressed. The other remains under investigation.**

---

## 20. Future LG webOS Networking

**Experimental module:**

```text
clonker/devices/lg_webos.py
```

The draft adapter remains outside operational dispatch.

Config v5 was designed in direct support of its eventual integration.

### 20.1 Configuration foundation

The current schema supports:

- Explicit `lg-webos` device type.
- Endpoint.
- Client key.
- SSAP URI.
- Optional JSON payload.
- Pointer button command.

The browser provides corresponding editing fields.

The pairing control remains disabled.

### 20.2 Experimental responsibilities

The draft adapter explores:

- WebSocket communication.
- Pairing.
- Client-key registration.
- Authenticated control sessions.
- Pointer sessions.
- Bounded response tracking.
- Cooperative response processing.
- Session cleanup.

These are experimental mechanisms, not established production behavior.

### 20.3 Integration requirements

Future operational integration must define:

- Session readiness.
- Credential handling.
- Command completion semantics.
- Response deadlines.
- Asynchronous error propagation.
- Configuration-change session retirement.
- Custom Action timing.
- Pairing lifecycle.

A transmitted command is not necessarily acknowledged.

An acknowledged command does not establish actual television state.

### 20.4 Shared execution requirement

The LG adapter must integrate with the existing dispatcher and Dumb Queue™.

Protocol response metadata may belong to the adapter.

It must not become a second independent command execution queue.

Uncertain commands must not be automatically replayed.

### 20.5 Memory discipline

LG introduces additional JSON processing and authenticated session state.

The Chapter 12 lessons concerning temporary allocations and redundant validation apply directly.

Avoid reconstructing trusted configuration in the runtime command path.

Bound protocol buffers and pending response metadata.

Protect credentials from logs and public configuration recipes.

### 20.6 Future Apple TV and Fire TV

Apple TV and Fire TV remain reserved future device types.

Authenticated or encrypted protocol requirements should first be investigated using standalone experiments.

Do not import a large desktop protocol framework into the Pico without establishing its resource requirements.

---

## 21. Regression Tests and Verification

Standalone experiments and regression tests live in:

```text
firmware/tests/
```

They are deployed to:

```text
/tests/
```

on the Pico.

A typical test is launched from the CircuitPython REPL:

```python
exec(open("/tests/test_filename.py").read())
```

The directory includes application regression tests and independent hardware, protocol, and CircuitPython experiments.

Not every test should be run against an active production application.

Persistence tests may require Pico-owned filesystem writes.

### 21.1 Chapter 12 automated suites

| Test | Initial result |
|---|---:|
| `test_config_validation.py` | 49/49 |
| `test_config_persistence.py` | 56/56 |
| `test_typed_adapters.py` | 56/56 |
| `test_config_activation.py` | 54/54 |
| `test_typed_queue.py` | 92/92 |
| `test_typed_physical.py` | 129/129 |
| **Total** | **436/436** |

These are implementation-stage results.

They do not establish that every suite was rerun after the subsequent persistence optimization.

### 21.2 Live Chapter 12 regression

Live equipment testing exercised:

- Generic HTTP.
- Denon persistent TCP volume.
- Roku persistent taps.
- Roku explicit button holds.
- Roku encoder-driven volume holds.
- Room selection.
- Independent mute histories.
- Custom Actions.
- Configuration editor operations.
- Repeated configuration saves.
- Management mode transitions.

The five operational execution paths remained functional in the observed tests.

### 21.3 Browser editor verification

Browser tests exercised:

- Registry-driven device selectors.
- Disabled future device types.
- LG configuration-only fields.
- Protocol-aware command editing.
- Independent toggle commands.
- Custom Action creation and renaming.
- Stable Custom Action identifiers.
- Step ordering and delays.
- Room removal and recreation.
- Minimum room count.
- Obsolete recipe rejection.
- Valid Config v5 import.
- Persistent changed saves.

Configuration editing support does not establish operational LG command execution.

### 21.4 Persistence endurance

Twenty consecutive changed saves succeeded after the memory-management improvements.

Five consecutive manual page refreshes also succeeded.

A subsequent save completed internally but encountered the unresolved management socket stall.

Management operation recovered without reboot.

Three further changed saves succeeded after temporary memory diagnostics were removed.

### 21.5 Remaining regression boundaries

Further testing remains appropriate for:

- Persistence and activation suites against the final optimized implementation.
- Interrupted-write recovery scenarios.
- Failures occurring after primary installation.
- Long-duration battery operation.
- Repeated management failure and recovery.
- Exhaustive rotated Flight Recorder retrieval.
- Future LG runtime integration.

Record the scope of each completed test.

Do not convert partial regression coverage into a claim of exhaustive reliability.

---

## 22. Operational Rules Worth Preserving

- Keep management HTTP and outbound equipment transport policies independent.
- Use one shared Dumb Queue™.
- Preserve monotonic timing.
- Validate configuration at trust boundaries.
- Trust already validated configuration through controlled accessors.
- Avoid unnecessary full configuration copies.
- Verify persisted bytes without redundant reconstruction.
- Retain intentional administrative garbage collection boundaries.
- Preserve physical press/release ownership.
- Do not redirect an unavailable room.
- Do not automatically replay uncertain commands.
- Distinguish successful persistence from successful acknowledgment.
- Keep adapter maintenance independent of queue depth.
- Keep credentials out of logs and public recipes.
- Preserve useful standalone experiments.
- Do not confuse temporary allocations with a proven memory leak.
- Do not declare an unresolved socket defect fixed merely because it has temporarily recovered.

**Clonker controls intent. Equipment owns state.**

**One Monster. One Dumb Queue™.**

---

## 23. Related Documents

- [Architecture](ARCHITECTURE.md)
- [Configuration, Persistence & Recovery](CONFIGURATION.md)
- [Configuration Redesign](CONFIGURATION_REDESIGN.md)
- [Cooperative HTTP Server](COOPERATIVE_HTTP_SERVER.md)
- [Operating Modes](OPERATING_MODES.md)
- [Hardware Design](HARDWARE_DESIGN.md)
- [Development & Deployment](DEVELOPMENT.md)
- [Development History](DEVELOPMENT_HISTORY.md)
- [Configuration Recipes](../recipes/)

---

**THE CLONKER 10000**  
*Less sleek. More CLONK.*  
**CLONK! ⚡🔩**
