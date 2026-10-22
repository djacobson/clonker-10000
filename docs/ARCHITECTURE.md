# The Clonker 10000 — System Architecture

**Design reference:** Updated October 22, 2026  
**Active platform:** Raspberry Pi Pico 2 W / CircuitPython 10.3.1  
**Repository:** [djacobson/clonker-10000](https://github.com/djacobson/clonker-10000)  
**Current milestone:** Chapter 4, Phase 1 complete — JSON v3 generic built-in device identifiers implemented and regression-tested.  
**Next milestone:** User-defined custom devices, followed by compound actions.

> **Clonker controls actions, not brands. Controlled devices own their own state.**

---

## 1. Mission

The Clonker 10000 is a tactile, Wi-Fi-first home-theater remote with substantial knobs, satisfying switches, guarded power controls, and eventually an audible **CLONK!**

Its purpose is to turn physical user intentions into configured equipment commands.

The Clonker is not intended to become a universal home-automation server or a comprehensive equipment-state reconciliation system.

Its core job is straightforward:

1. Recognize an action.
2. Identify the selected room.
3. Resolve the configured destination and command.
4. Schedule the command.
5. Transmit it.
6. Report the result.
7. Get out of the way.

External equipment remains authoritative for its actual state.

Clonker does not attempt to maintain a perfect representation of power, volume, input selection, playback, HDMI-CEC behavior, or changes made by other remotes.

### 1.1 Guiding philosophy

**Be resilient in our dumbness.**

The system should be:

- Responsive to physical controls.
- Predictable during normal operation.
- Resistant to malformed configuration.
- Recoverable after network or filesystem failures.
- Small enough to understand.
- Easy to test incrementally.
- Extensible without prematurely building a general-purpose automation framework.

The design favors explicit responsibilities and simple interfaces over clever abstractions.

### 1.2 Development priorities

The broad priorities are:

1. Reliable generic action execution.
2. Validated, persistent configuration.
3. Responsive physical controls.
4. Practical multi-room operation.
5. User-defined devices and actions.
6. Useful diagnostics.
7. OLED status and audible feedback.
8. Rechargeable power and sleep/wake behavior.
9. Additional equipment protocols where justified.

The browser editor and Test Remote were intentionally developed before physical input integration.

This allowed the configuration and command pipeline to be tested against real Denon and Roku equipment without introducing GPIO and encoder complications.

---

## 2. Architecture at a Glance

```text
                  THE CLONKER 10000

        BROWSER TEST REMOTE      PHYSICAL CONTROLS
           IMPLEMENTED               PLANNED
                |                        |
                v                        v
          HTTP ACTION API          GPIO EVENTS
                |                        |
                +-----------+------------+
                            |
                            v
                       actions.py
                     Validate event
                       Enqueue task
                            |
                            v
                      DUMB QUEUE
                       IMPLEMENTED
                            |
                            v
                      actions.poll()
                   Select eligible task
                            |
                            v
                  RESOLVE CONFIGURATION
                    JSON v3 / CURRENT
                            |
                            v
                    COMMAND SELECTION
                  Ordinary: implemented
                   Toggles: deferred
                            |
                            v
                   HTTP TRANSPORT
                       IMPLEMENTED
                            |
                            v
                   DENON / ROKU / ...
                            |
                            v
                       EQUIPMENT


             CONFIGURATION MANAGEMENT
                       IMPLEMENTED

                Browser editor / :9090
                          |
                          v
                   JSON validation
                          |
                          v
                  Revision protection
                          |
                          v
                   Verified persistence
                          |
                          v
                    Active RAM config
```

This is the implemented fundamental-action path.

Future custom actions will enter the same shared queue rather than creating a separate execution system.

### 2.1 Architectural invariants

The following boundaries should remain true as the project grows:

- Physical controls generate generic events.
- Browser controls use the same action pipeline.
- Configuration owns command definitions.
- Actions own scheduling and execution policy.
- The transport owns HTTP communication.
- Device-specific paths do not belong in GPIO handlers.
- External equipment owns its actual state.
- Failed commands are not automatically retried.
- One authoritative active configuration exists in RAM.

---

## 3. Current Implementation Status

**Status reference: October 22, 2026**

### 3.1 Implemented and tested

- Raspberry Pi Pico 2 W running CircuitPython 10.3.1.
- Wi-Fi connectivity and serial logging.
- GP17 SERVICE/DEVICE filesystem-ownership selection.
- JSON v3 configuration.
- Three fixed rooms.
- Three generic built-in device slots per room.
- Fourteen fundamental actions per room.
- Strict configuration validation.
- Active configuration held in RAM.
- Browser configuration editor.
- Browser Test Remote.
- Inbound HTTP management service on port 9090.
- Browser clock synchronization.
- Revision-protected configuration saves.
- Stale-tab conflict rejection.
- Verified temporary configuration writes.
- Configuration backup rotation.
- Startup fallback to valid backups.
- Shared Dumb Queue™.
- Queue capacity and overflow rejection.
- Immediate and future-dated action scheduling.
- Eligible-task ordering.
- Queue-wide failure cancellation.
- Outbound HTTP GET/POST transport.
- Real Denon volume commands.
- Real Roku navigation commands.
- Multi-command queue execution.
- JSON v3 persistence after reboot.

The Chapter 4 generic-device refactor was regression-tested against the actual equipment and browser editor.

### 3.2 Implemented with further testing appropriate

- Recovery from interrupted configuration writes.
- Backup behavior during power loss.
- Extended network failure scenarios.
- Malformed HTTP request handling.
- Sustained command traffic.
- Physical input responsiveness under outbound network load.
- Long-uptime monotonic scheduling behavior.

Existing successful tests should not be described as exhaustive failure-injection coverage.

### 3.3 Not yet implemented

- User-defined custom devices.
- Executable custom actions.
- Compound action scheduling.
- Runtime toggle direction history.
- Physical buttons and encoders connected to dispatch.
- Physical CONFIG/RUN selection.
- Physical room selector.
- OLED status.
- Audible feedback.
- Battery management.
- Sleep/wake behavior.
- Apple TV integration.

### 3.4 Immediate development direction

Chapter 4 proceeds in controlled phases:

1. Generic built-in device IDs — **complete**.
2. Custom-device schema and browser support — **next**.
3. Custom and compound action configuration.
4. Compound action execution using the shared queue.
5. Further action behavior and physical input integration.

This order may be adjusted based on testing, but new capabilities should be introduced one at a time.

---

## 4. Firmware Component Map

| Component | Responsibility |
|---|---|
| `firmware/boot.py` | Filesystem ownership selected by GP17 |
| `firmware/code.py` | CircuitPython application entry point |
| `firmware/clonker/main.py` | Startup and cooperative service scheduling |
| `firmware/clonker/device_config_v2.py` | JSON v3 validation, RAM configuration, revisions, persistence |
| `firmware/clonker/device_config.json` | Checked-in configuration |
| `firmware/clonker/actions.py` | Fundamental dispatch, Dumb Queue™, execution policy |
| `firmware/clonker/net/http_transport.py` | Outbound HTTP GET/POST |
| `firmware/clonker/net/web.py` | Inbound browser/API service |
| `firmware/clonker/www/index.html` | Configuration editor |
| `firmware/clonker/www/remote.html` | Browser Test Remote |
| `firmware/clonker/controls/switches.py` | Simulated application mode and future switches |
| `firmware/clonker/controls/pins.py` | GPIO definitions |
| `firmware/clonker/system/clock.py` | Clock services |
| `firmware/clonker/system/logger.py` | Serial diagnostics |
| `firmware/clonker/legacy/` | Historical XML v1 implementation |

The `net/` package owns networking.

The `system/` package owns shared services.

The configuration module retains its historical `device_config_v2.py` filename while implementing JSON v3.

Renaming the module is not required for the current milestone.

---

## 5. Operating Modes

Clonker has two independent mode dimensions.

### 5.1 SERVICE / DEVICE

This controls filesystem ownership.

It is selected during boot using GP17.

| Mode | GP17 | Writable filesystem owner |
|---|---|---|
| SERVICE | Open | USB host |
| DEVICE | Grounded | Pico firmware |

Changing this mode requires a full power cycle.

A CircuitPython soft reload is not sufficient to reliably change filesystem ownership.

### 5.2 CONFIG / RUN

This controls application behavior.

**CONFIG mode:**

- Management HTTP service available.
- Browser configuration editor available.
- Browser Test Remote available.
- Clock synchronization available.
- Device actions remain operational.

**RUN mode:**

- Management HTTP listener stopped.
- Action execution continues.
- Future physical controls remain available.
- Configuration remains loaded in RAM.

The physical CONFIG/RUN switch has not yet been wired.

Current development uses simulated CONFIG mode.

### 5.3 Independence of modes

SERVICE/DEVICE and CONFIG/RUN are separate concepts.

A device may be in CONFIG mode while the filesystem remains read-only to CircuitPython.

The browser must not assume that an available editor implies permission to save.

For detailed operating procedures, see [Operating Modes](OPERATING_MODES.md).

---

## 6. Configuration Architecture

The active schema is JSON v3.

Its detailed rules are documented in [Configuration, Persistence & Recovery](CONFIGURATION.md).

This section covers architectural responsibilities rather than duplicating the full schema.

### 6.1 Fixed rooms

The firmware has three fixed room IDs:

```text
room-1
room-2
room-3
```

Room names are editable.

Room IDs remain stable and are used for configuration lookup and dispatch.

### 6.2 Generic built-in devices

Each room has three built-in device slots:

```text
device-1
device-2
device-3
```

The browser currently displays them as:

```text
device-1 = TV
device-2 = AVR
device-3 = Streaming
```

These labels are not enforced device-type restrictions.

A fundamental action may target any of the three built-in slots.

The firmware does not infer equipment type from the slot ID.

### 6.3 Why generic IDs matter

The original JSON v2 schema used:

```text
tv
avr
streaming
```

Those identifiers combined a device's role with its internal identity.

JSON v3 separates those concepts.

This gives Clonker a more flexible foundation for future custom devices without requiring a brand-aware action dispatcher.

### 6.4 One authoritative RAM snapshot

The configuration engine owns the active validated configuration.

The private `_current` dictionary is authoritative.

Public accessors return defensive copies.

The internal `action_details()` accessor returns references to already-validated configuration objects for fast action resolution.

Those references are read-only by contract.

No other module may mutate the active configuration.

### 6.5 Configuration changes

A successful changed save:

1. Validates the submitted configuration.
2. Verifies the expected revision.
3. Checks disk-versus-RAM consistency.
4. Persists the configuration.
5. Publishes the new active RAM snapshot.
6. Causes the HTTP layer to clear pending queued actions.

A failed save does not publish a new active configuration.

The checked-in GitHub JSON is not automatically synchronized with the Pico's active file.

### 6.6 Persistence and recovery

The engine uses:

```text
device_config.json
device_config.json.bak
device_config.json.bak.old
```

Startup may load a valid backup if the primary is unavailable or invalid.

Backup fallback does not silently repair the primary.

Backup rotation uses individual filesystem operations and is not a fully atomic power-loss transaction.

Detailed safeguards and recovery procedures belong in [Configuration, Persistence & Recovery](CONFIGURATION.md).

---

## 7. Fundamental Action Model

Clonker defines fourteen fixed fundamental action IDs.

```text
volume-up       volume-down      mute-toggle

nav-up          nav-down         nav-left

nav-right       select           back

home            play-pause       skip-back

skip-forward    power-toggle
```

Every room contains all fourteen actions, including those not yet configured.

### 7.1 Ordinary actions

Twelve fundamental actions contain:

- Target device ID.
- HTTP method.
- Command path.

Example:

```json
{
  "target": "device-2",
  "method": "GET",
  "path": "/goform/formiPhoneAppDirect.xml?MVUP"
}
```

### 7.2 Toggle actions

Two fundamental actions contain paired ON/OFF paths:

- `mute-toggle`
- `power-toggle`

They share one target and HTTP method.

The configuration and browser support the fields.

Runtime direction selection remains pending.

### 7.3 Blank actions

Blank endpoints and command paths are valid.

They represent intentional no-ops.

An unconfigured ordinary action may be queued, but it does not transmit an HTTP request.

A blank action is not an external transport failure.

### 7.4 Physical mapping

Physical controls should generate generic action IDs.

Examples:

```text
Volume encoder clockwise      -> volume-up
Volume encoder counterclockwise -> volume-down
Navigation up button          -> nav-up
Select button                 -> select
Guarded power control         -> power-toggle
```

Physical controls must not contain Denon, Roku, or other vendor-specific command paths.

---

## 8. The Dumb Queue™

**Status:** Implemented and tested.

The Dumb Queue™ is the single shared scheduling mechanism for fundamental actions and planned custom command steps.

It lives in:

`firmware/clonker/actions.py`

Its design goal is simple:

**One queue. One poller. One shared execution path.**

### 8.1 Why a queue exists

Browser and physical control events can arrive faster than outbound network requests complete.

The queue separates action acceptance from execution.

It provides:

- Bounded buffering.
- Consistent command ordering.
- Future-dated scheduling.
- A shared failure policy.
- A common path for different input sources.

It does not make the network faster.

It does not make blocking HTTP operations asynchronous.

### 8.2 Current fundamental task representation

A queued fundamental action contains:

```python
{
    "room": "room-1",
    "action": "volume-up",
    "due": 0
}
```

The task stores identifiers rather than copied configuration.

The command is resolved when the task executes.

### 8.3 Queue capacity

The current capacity is:

```python
QUEUE_CAPACITY = 128
```

When full, the queue rejects a new action.

It does not silently discard existing valid tasks to make room.

The dispatcher logs overflow.

### 8.4 Monotonic scheduling

The queue uses `time.monotonic()`.

A `due` value of zero means the task is immediately eligible.

A positive due time is an absolute monotonic deadline.

Wall-clock synchronization does not affect queue scheduling.

Due times are earliest eligible execution times, not guarantees of exact execution.

### 8.5 Not strict FIFO

The queue deliberately allows an immediately eligible task to bypass an earlier future-dated task.

Example:

```text
1. Denon command scheduled for two seconds later.
2. User turns volume knob.
3. Volume Up is immediately eligible.
4. Volume Up executes first.
5. Scheduled Denon command executes when eligible.
```

Among eligible tasks, insertion order determines which is selected first.

This behavior is intentional.

A future command must not hold an immediate button press hostage.

### 8.6 One eligible task per poll

`actions.poll()` executes at most one eligible task per invocation.

The poller returns after processing that task.

It does not wait for future deadlines.

### 8.7 Current configuration resolution

The queue does not retain references to mutable configuration.

At execution time, the dispatcher reads the active configuration through the configuration module.

This prevents queued tasks from retaining stale endpoint or command definitions.

A successful changed configuration save clears pending work.

---

## 9. Queue Failure Policy

**Design principle: One failed external command cancels pending work, not the remote itself.**

### 9.1 Current behavior

When an executing command raises an exception:

1. The executing task has already been removed.
2. All remaining queued tasks are discarded.
3. The error is recorded.
4. The discarded task count is recorded.
5. The queue remains usable for future actions.

There are no automatic retries.

### 9.2 Why queue-wide cancellation

After a network failure, pending commands may no longer make sense.

Continuing a sequence could produce unexpected equipment behavior.

A simple queue-wide cancellation is preferable to attempting automatic recovery without knowing the equipment's state.

### 9.3 Failure examples

| Situation | Expected behavior |
|---|---|
| Invalid room/action ID | Reject dispatch |
| Queue full | Reject new task |
| Blank ordinary action | Safe no-op |
| Future-dated task | Remain queued until eligible |
| Successful HTTP command | Record result and continue |
| HTTP/network exception | Clear remaining queue |
| Changed configuration saved | Clear pending queue |
| Failed configuration save | Preserve active configuration |

### 9.4 Recovery

Queue cancellation does not permanently disable the dispatcher.

The next valid action can be accepted normally.

The system does not automatically replay discarded commands.

### 9.5 Diagnostics

The current queue maintains a small diagnostic snapshot containing:

- Current depth.
- Capacity.
- Peak depth.
- Last result.
- Last error.

Serial logs provide additional execution details.

A future OLED may display a concise status or failure indication.

---

## 10. Cooperative Scheduling and Network Blocking

The main application uses a cooperative loop.

Existing polling includes the management HTTP service in CONFIG mode and the action dispatcher.

Current development intervals are approximately:

| Setting | Value |
|---|---:|
| Action polling | 0.01 seconds |
| Management HTTP polling | 0.01 seconds |
| Main-loop idle sleep | 0.001 seconds |

These are scheduler settings, not guaranteed response latencies.

### 10.1 Cooperative responsibilities

Each service should perform bounded work and return control.

The scheduler should avoid:

- Blocking waits for future queue deadlines.
- Unbounded network operations.
- Busy-wait loops.
- Unnecessary repeated configuration parsing.
- Excessive serial output during normal operation.

### 10.2 The important limitation

Outbound HTTP execution is currently synchronous.

While an outbound request is in progress, the cooperative loop may be temporarily blocked.

The Dumb Queue buffers work but does not guarantee physical input capture during that blocking interval.

This distinction becomes important when integrating encoders.

### 10.3 Future responsiveness testing

The first physical-input tests should measure:

- Button responsiveness during ordinary HTTP traffic.
- Encoder event capture during network requests.
- Queue growth during rapid rotation.
- Recovery after endpoint timeouts.
- Responsiveness while compound steps are waiting.

Only introduce more complex networking or event buffering if measurements demonstrate a real problem.

---

## 11. Volume Encoder Strategy

The initial volume encoder implementation should remain simple.

Each recognized step generates one fundamental action.

```text
Clockwise        -> volume-up
Counterclockwise -> volume-down
```

Every generated action is immediately eligible.

### 11.1 Initial behavior

- One event per recognized step.
- No acceleration.
- No event accumulation.
- No deduplication.
- No automatic retries.
- No special volume-specific transport.
- No persistent connection requirement.

Eight recognized volume steps may produce eight HTTP requests.

That is acceptable for initial testing.

### 11.2 Potential future optimizations

If measurements justify changes, possible options include:

- Accumulating encoder steps.
- Rotation-speed acceleration.
- Device-supported batching.
- Connection reuse.
- Improved event capture during blocking HTTP.
- Queue tuning.

These are future optimizations, not prerequisites for initial hardware integration.

### 11.3 Hardware dependency

The Grayhill optical encoder requires electrical and GPIO verification before integration.

Its actual event behavior must be measured rather than assumed.

See [Hardware & Controls](HARDWARE_CONTROLS.md).

---

## 12. Toggle Actions

**Configuration fields:** Implemented  
**Runtime direction history:** Planned

The two toggle actions are:

```text
power-toggle
mute-toggle
```

### 12.1 Planned RAM history

The dispatcher will maintain a small command-direction history for each room and toggle action.

Conceptually:

```text
room-1:
    power-toggle: unknown
    mute-toggle:  unknown

room-2:
    power-toggle: unknown
    mute-toggle:  unknown

room-3:
    power-toggle: unknown
    mute-toggle:  unknown
```

### 12.2 Selection rules

| Last successful direction | Next attempted direction |
|---|---|
| Unknown | ON |
| ON | OFF |
| OFF | ON |

The dispatcher selects the direction when the queued action executes.

History advances only after successful command submission.

Failed requests and no-ops do not advance history.

### 12.3 Native toggles

Some devices use the same command for both directions.

Their `on_path` and `off_path` may be identical.

No special native-toggle configuration flag is required.

### 12.4 Equipment state remains external

Command history does not establish actual power or mute state.

Other remotes, HDMI-CEC, applications, and device controls may change equipment state independently.

This is an accepted limitation.

### 12.5 Configuration changes

A successful configuration change should invalidate relevant toggle history.

A simple global toggle-history reset is acceptable initially.

### 12.6 Ownership

Toggle direction selection belongs in `actions.py`.

It does not belong in:

- The configuration validator.
- The HTTP transport.
- GPIO handlers.
- The browser Test Remote.

---

## 13. Custom Devices — Next Milestone

**Status:** Planned, not implemented.

The next architectural extension is support for additional user-defined device destinations.

### 13.1 Built-in versus custom devices

Built-in devices are the three fixed slots:

```text
device-1
device-2
device-3
```

Custom devices are additional named destinations defined by the user.

The two categories must remain distinguishable.

### 13.2 Proposed model

Each room will eventually contain a separate collection of custom devices.

A custom device is expected to have:

- Stable internal ID.
- User-editable name.
- Configured endpoint.

Example conceptual IDs:

```text
custom-1
custom-2
custom-3
```

These are proposed conventions, not currently accepted JSON.

### 13.3 Fundamental-action boundary

Fundamental actions will continue targeting built-in device slots.

Custom action steps may target either built-in or custom devices.

This avoids broadening the fundamental-action model unnecessarily.

### 13.4 Centralized destination resolution

The action system should resolve device destinations through a common helper or clearly defined shared mechanism.

The rest of the execution pipeline should not need to know whether an endpoint came from a built-in or custom device.

Avoid scattering separate built-in/custom lookup rules throughout the codebase.

### 13.5 Stable references

Deleting a custom device must not silently retarget an action to another device.

Device IDs should not be renumbered merely because an earlier device was removed.

Configuration validation must reject or explicitly handle references to missing destinations.

### 13.6 Scope boundaries

The first implementation should use the existing HTTP endpoint model.

Do not add:

- DNS support.
- HTTPS.
- Authentication.
- Device discovery.
- Protocol plug-ins.
- Complex device capabilities.

Those features require separate justification and testing.

---

## 14. Custom and Compound Actions

**Status:** Architecture agreed in principle; implementation pending.

Custom actions are named user-defined actions.

A custom action may contain one or more command steps.

A multi-step custom action is a compound action.

### 14.1 Shared execution architecture

Compound actions should use the existing Dumb Queue™ and outbound HTTP transport.

They should not introduce a second macro executor.

The queue will need a small extension to represent command steps and dependencies.

Ordinary fundamental actions should retain their lightweight representation.

### 14.2 Proposed custom-action structure

A custom action will eventually contain:

- Stable action ID.
- Display name.
- Ordered command steps.

Each command step is expected to contain:

- Destination.
- HTTP method.
- Command path.
- Optional post-command wait in milliseconds.

The exact JSON schema is not yet committed.

### 14.3 Post-completion timing

The agreed timing semantics are important.

A step's wait begins **after its HTTP command completes successfully**.

It is not simply an offset from the time the custom action was originally queued.

Example:

```text
MOVIE NIGHT

Step 1: AVR input command
        HTTP completes
        Wait 250 ms

Step 2: TV command
        HTTP completes
        Wait 500 ms

Step 3: Streaming command
        HTTP completes
        Action complete
```

This preserves meaningful command spacing even when network latency varies.

### 14.4 Predecessor dependencies

A dependent step must not execute before its predecessor finishes successfully and its post-command wait expires.

The proposed queue representation uses lightweight predecessor references.

A successor becomes eligible when its dependency is satisfied.

This does not require a full workflow engine.

### 14.5 Independent command interleaving

Compound actions should not monopolize the queue.

While one sequence is waiting, an unrelated eligible action may execute.

Example:

```text
Movie Night step 1 executes.
Movie Night waits 500 ms.
User turns volume knob.
Volume Up executes.
Movie Night step 2 becomes eligible.
Movie Night step 2 executes.
```

The exact order depends on eligibility and insertion order.

A compound action is not an exclusive execution lock.

### 14.6 Queue capacity

A compound action must not partially enqueue when insufficient capacity exists.

The queue should check capacity for all required tasks before accepting the compound action.

Acceptance should be all-or-nothing.

### 14.7 Failure behavior

A failed compound step follows the existing queue-wide failure policy.

Remaining queued work is discarded.

There is no automatic retry or rollback.

The system remains available for new commands afterward.

### 14.8 No unnecessary overhead on fundamentals

Fundamental actions should not need compound-action IDs, predecessor fields, or extra dependency bookkeeping.

Their existing compact queue entries should remain unchanged unless testing demonstrates a concrete need.

### 14.9 Initial scope limits

Avoid:

- Loops.
- Conditional branches.
- Nested custom actions.
- Arbitrary scripting.
- Automatic retries.
- Rollback.
- Complex state queries.
- Separate execution threads.
- A general-purpose dependency graph engine.

The goal is a practical remote-control sequence mechanism, not a miniature automation platform.

### 14.10 Browser configuration

The browser will eventually need simple controls for:

- Adding and removing custom actions.
- Editing action names.
- Adding and removing steps.
- Selecting destinations.
- Choosing GET or POST.
- Editing paths.
- Configuring post-step waits.

The UI should remain compact and understandable on an iPad.

---

## 15. Outbound HTTP Transport

**Status:** Implemented and tested.

The outbound transport is:

`firmware/clonker/net/http_transport.py`

It is separate from the inbound management server.

### 15.1 Responsibilities

The transport:

1. Receives an endpoint, HTTP method, and path.
2. Parses the IPv4 endpoint and optional port.
3. Opens a TCP connection.
4. Sends an HTTP request.
5. Reads enough response information to determine status.
6. Applies bounded timeouts.
7. Releases socket resources.
8. Returns a concise result or raises an error.

### 15.2 Non-responsibilities

The transport does not:

- Choose rooms.
- Interpret physical buttons.
- Select toggle directions.
- Resolve fundamental action IDs.
- Schedule compound steps.
- Maintain command history.
- Modify configuration.
- Clear the queue.
- Automatically retry commands.

### 15.3 Current limitations

The current transport uses simple HTTP GET/POST.

It does not support arbitrary request bodies, custom authentication, TLS, or persistent connection pooling.

A fresh TCP connection per command is acceptable for the current development stage.

### 15.4 Failure ownership

The transport reports failure.

The action dispatcher applies the queue cancellation policy.

This separation is important.

A future transport implementation must not silently change execution policy.

---

## 16. Inbound Management HTTP Service

**Status:** Implemented.

The inbound management server is:

`firmware/clonker/net/web.py`

It listens on port 9090 while CONFIG mode is active.

### 16.1 Responsibilities

The server provides:

- Browser configuration editor.
- Browser Test Remote.
- Configuration GET/POST.
- Action submission.
- Clock status and synchronization.

### 16.2 Cooperative operation

The server processes one active client connection at a time.

Each `web.poll()` advances a bounded accept, receive, or send operation.

Current limits include:

| Setting | Value |
|---|---:|
| Maximum request size | 10240 bytes |
| Maximum header size | 2048 bytes |
| I/O chunk size | 512 bytes |
| Silent-client timeout | 0.5 seconds |
| Active-client timeout | 4.0 seconds |

### 16.3 Browser action API

Example:

```text
POST /api/action?room=room-1&action=volume-up
```

The request reaches:

```python
actions.dispatch(room_id, action_id)
```

The dispatcher validates and queues the action.

The HTTP response acknowledges scheduling, not completed equipment execution.

### 16.4 Browser configuration API

`GET /api/config` returns the active configuration plus revision and filesystem-writability metadata.

`POST /api/config` delegates validation and persistence to the configuration engine.

A successful changed save clears pending queue tasks.

### 16.5 Browser compatibility

Future changes should preserve the current browser action interface where practical.

Changes to response fields or status meanings must be documented and tested.

---

## 17. Physical Controls

**Status:** Planned.

Physical controls will use the same fundamental-action dispatcher as the browser Test Remote.

```text
Physical control
       |
       v
GPIO decoding / debounce
       |
       v
Generic action ID
       |
       v
actions.dispatch()
       |
       v
Dumb Queue
       |
       v
Configured command
```

### 17.1 Planned hardware

The current hardware direction includes:

- Grayhill optical volume encoder.
- Bourns mechanical selector encoder.
- Navigation buttons.
- Guarded SYSTEM MASTER control.
- Side-mounted room selector.
- Small OLED display.
- Audible feedback hardware.

The exact GPIO assignments and physical layout remain subject to testing.

### 17.2 Input requirements

The input layer must:

- Debounce switches.
- Decode encoder direction.
- Avoid unnecessary blocking.
- Generate generic actions.
- Respect selected-room behavior.
- Avoid vendor-specific HTTP logic.
- Handle queue rejection gracefully.

### 17.3 Guarded SYSTEM MASTER

The guarded power control may eventually serve as both a power action and a wake source.

Sleep/wake behavior is outside the current action-dispatch milestone.

See [Hardware & Controls](HARDWARE_CONTROLS.md).

---

## 18. Room Selection

**Status:** Planned for physical controls.

The configuration model supports three rooms.

The physical interface will eventually determine which room or rooms receive actions.

The current side-switch concept includes Den, Both, and Sunroom positions.

This is a hardware interaction design, not an additional configuration room ID.

### 18.1 Selection versus configuration

Room selection should not mutate the stored configuration.

It determines the destination room for a user action.

### 18.2 Multiple-room behavior

A Both selection may result in dispatching corresponding fundamental actions to two rooms.

The exact behavior for queue capacity, partial acceptance, and simultaneous-room actions must be defined before implementation.

Do not silently assume atomic multi-room dispatch exists today.

---

## 19. Clock and Timing

Clonker uses different time concepts for different purposes.

### 19.1 Wall clock

Browser-synchronized time supports:

- Human-readable timestamps.
- Logging.
- Diagnostics.
- Future display functions.

### 19.2 Monotonic clock

Monotonic time supports:

- Queue deadlines.
- Relative delays.
- Execution timing.
- Timeout measurements.

Changing the wall clock must not shift queued action deadlines.

### 19.3 Timing guarantees

The queue provides earliest eligibility times.

It does not guarantee exact execution times.

Outbound HTTP, other cooperative work, and hardware limitations can delay execution.

Compound-action waits should be measured from predecessor completion, but actual successor execution may occur later than the requested interval.

---

## 20. Apple TV and Future Protocols

Apple TV compatibility is an explicit future objective.

The generic fundamental-action model should remain independent of equipment brands and transport protocols.

For example:

```text
nav-up
play-pause
home
back
```

These represent user intentions, regardless of whether the destination is a Roku or Apple TV.

### 20.1 Current boundary

The existing transport supports simple HTTP GET/POST commands and has been tested with Denon and Roku equipment.

Apple TV may require:

- Discovery.
- Pairing.
- Authentication.
- Session management.
- Protocol-specific command transmission.

Those requirements are not yet established in the Clonker implementation.

### 20.2 Design guidance

Do not force Apple TV into an unsuitable HTTP configuration model merely to avoid future architectural changes.

Equally, do not add speculative protocol abstractions before evaluating a concrete implementation.

The current generic action and destination model should provide a useful foundation.

No Apple TV protocol module is committed at this stage.

---

## 21. Security and Network Boundaries

The management HTTP service is intended for a trusted local network.

It currently has no application-level authentication or HTTPS.

Do not expose port 9090 directly to the public internet.

CircuitPython Web Workflow is disabled in the current private development setup because of suspected socket conflicts.

Clonker's own management service is separate from CircuitPython Web Workflow.

Configuration validation protects structure and basic values, but does not make arbitrary device commands safe.

The system assumes the operator controls the configured local equipment and endpoints.

---

## 22. Development and Test Discipline

The Clonker is developed incrementally.

### 22.1 One meaningful change at a time

Prefer:

1. Define the behavior.
2. Identify affected modules.
3. Make the smallest coherent change.
4. Deploy to the Pico.
5. Observe startup.
6. Test representative behavior.
7. Test failure behavior when appropriate.
8. Push the working change.
9. Update documentation.

Avoid combining unrelated refactors with new functionality.

### 22.2 Browser-first testing

The Browser Test Remote remains the preferred way to validate action dispatch before physical controls are integrated.

It provides repeatable inputs without hardware debounce or encoder variables.

### 22.3 Configuration regression tests

After a schema change, verify:

- Startup.
- Editor loading.
- Room/device rendering.
- Fundamental action execution.
- Save behavior.
- Restart persistence.
- Backup generation.
- Stale-tab rejection.
- Configuration version agreement.

### 22.4 Queue regression tests

After dispatcher changes, verify:

- Immediate execution.
- Delayed-task bypass.
- Eligible-task ordering.
- Capacity rejection.
- Network failure cancellation.
- Post-failure recovery.
- Blank-action no-op.
- Configuration-change queue clearing.

### 22.5 Compound-action tests

When implemented, add:

- Single-step custom action.
- Multi-step sequence.
- Post-completion waits.
- Independent action interleaving.
- Predecessor failure cancellation.
- Queue-capacity all-or-nothing acceptance.
- Deleted-device reference rejection.
- Configuration save/restart persistence.

### 22.6 No unverified success claims

Successful HTTP responses, queue acceptance, and observed equipment changes are different facts.

Documentation should distinguish them.

Similarly, source inspection is not a substitute for actual Pico execution testing.

---

## 23. Historical Development Milestones

This section summarizes completed architectural milestones.

Detailed chronological notes belong in [Development History](DEVELOPMENT_HISTORY.md).

### 23.1 XML v1

The original XML configuration system established browser editing and persistence concepts.

It remains in the repository as a historical implementation.

### 23.2 JSON v2

JSON v2 replaced XML with a configuration model shared naturally by CircuitPython and JavaScript.

It established:

- Strict validation.
- Compact serialization.
- Revision protection.
- Verified saves.
- Backup rotation.
- Browser configuration editing.

### 23.3 Dumb Queue — October 20, 2026

The initial logging-only queue established:

- Fixed action dispatch.
- Capacity enforcement.
- Eligible-task scheduling.
- Delayed-task bypass.
- Failure cancellation.
- Cooperative polling.

The logging-only implementation was a stepping stone, not the current execution model.

### 23.4 Outbound HTTP — October 21, 2026

The queue was connected to real outbound HTTP GET/POST execution.

Denon and Roku commands were tested successfully.

A five-command volume burst completed with HTTP 200 responses.

### 23.5 JSON v3 — October 22, 2026

The built-in device IDs changed from:

```text
tv        -> device-1
avr       -> device-2
streaming -> device-3
```

The browser retained the original display labels.

Configuration loading, editing, persistence, queue execution, and real Denon/Roku commands were regression-tested.

The refactor did not require rewriting the Dumb Queue or outbound transport.

This established the baseline for custom devices.

---

## 24. Architectural Ownership

| Component | Owns |
|---|---|
| Configuration engine | Validated configuration, revisions, persistence, recovery |
| Action dispatcher | Action acceptance, scheduling, execution policy, toggle history |
| Dumb Queue | Pending work, eligibility, capacity, cancellation |
| HTTP transport | Outbound requests, sockets, timeouts, HTTP results |
| Management server | Browser/API requests and responses |
| Main loop | Application lifecycle and cooperative polling |
| Physical controls | Input detection and generic action events |
| Clock service | Time sources and synchronization |
| Logger | Diagnostics |
| External equipment | Actual device state |

### 24.1 Non-negotiable boundaries

- Do not create a second authoritative configuration cache.
- Do not put device-specific HTTP commands in GPIO handlers.
- Do not let the transport own toggle direction.
- Do not let the browser bypass the shared action dispatcher.
- Do not introduce a separate compound-action execution engine.
- Do not automatically retry failed commands.
- Do not silently retarget actions when custom devices are deleted.
- Do not make physical input behavior depend on the configuration editor being open.
- Do not claim equipment state from command history alone.

---

## 25. Design Principles Worth Remembering

**Less sleek. More CLONK.**

**Smart enough to know when to be dumb.**

**One queue. One poller. One shared execution path.**

**A future task must not hold an immediate button press hostage.**

**One failed external command cancels pending work, not the remote itself.**

**Clonker sends commands. Equipment owns state.**

**A command sequence is not permission to invent a workflow engine.**

**Configuration describes the destination. Actions describe the intention. Transport delivers the message.**

And perhaps the most important development rule:

> **Do not make the Clonker more complicated merely because we are capable of making it more complicated.**

---

## 25.1 Future Objective — Clonker Recipe Library

**Status:** Conceptual; deferred until after custom devices and compound actions.

A future Clonker Recipe Library may provide downloadable
configuration examples for common equipment combinations
and custom action sequences.

Recipes could be hosted on the Clonker website or in a
GitHub-hosted sample catalog.

The browser configuration editor may eventually offer a
recipe selector that:

1. Retrieves a catalog of available recipes.
2. Displays descriptive titles and equipment information.
3. Loads a selected recipe into the editor.
4. Allows the user to review and modify the configuration.
5. Requires an explicit Save action before persistence.

Recipes may include external documentation describing
equipment compatibility, command behavior, setup
requirements, and custom action examples.

Detailed descriptions and attribution belong with the
recipe catalog, not in the operational device configuration.

The Pico must remain fully operational without internet
access or access to the recipe library.

Recipe loading must not bypass configuration validation,
revision protection, or the existing save safeguards.

**Design principle:** Recipes help users configure the
Clonker; they do not become a runtime dependency.

---

## 26. Reference Documents

- [Configuration & Recovery](CONFIGURATION.md) — active JSON v3 schema, validation, persistence, and recovery.
- [Firmware & Network](FIRMWARE_NETWORK.md) — networking, clock services, HTTP behavior, and testing.
- [Operating Modes](OPERATING_MODES.md) — filesystem ownership and application modes.
- [Hardware & Controls](HARDWARE_CONTROLS.md) — physical controls, GPIO planning, and power behavior.
- [Development & Deployment](DEVELOPMENT.md) — development workflow and deployment.
- [Development History](DEVELOPMENT_HISTORY.md) — chronological engineering milestones.
- [Chapter 2 Handoff](CHAPTER_2_HANDOFF.md) — historical handoff reference.
- [Terminology Audit](TERMINOLOGY_AUDIT.md) — historical terminology reconciliation.
- [Old Architecture](OLD_ARCHITECTURE.md) — historical reference, not the active architecture.

---

**CLONK! ⚡🔩**

*The Clonker 10000 — because apparently a normal remote control wasn't complicated enough.*
