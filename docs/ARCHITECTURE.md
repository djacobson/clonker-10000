# The Clonker 10000 — Architecture

**Design reference:** Updated October 20, 2026  

**Active target:** Raspberry Pi Pico 2 W / CircuitPython 10.3.1  

**Repository:** [djacobson/clonker-10000](https://github.com/djacobson/clonker-10000)  

**Current milestone:** Chapter 3, Phase A complete — logging-only Dumb Queue validated; outbound HTTP transport pending.

> **Clonker controls actions, not brands. Controlled devices own their own state.**

---

## 1. Mission and Philosophy

The Clonker 10000 is a tactile, Wi-Fi-first home theater remote with physical knobs, substantial switches, satisfying buttons, and eventually an audible **CLONK!**

Its physical controls express generic actions. Room configuration maps those actions to devices and commands.

The design should remain small, understandable, and maintainable on a microcontroller.

### The fundamental philosophy

Clonker is a remote control, not a home theater state-reconciliation engine.

The receiver, television, and streaming device remain authoritative for their actual state.

Clonker does not attempt to maintain a perfect model of equipment state, HDMI-CEC interactions, other remotes, or user activity.

Instead, it:

1. Accepts control events.

2. Resolves configured commands.

3. Schedules their execution.

4. Sends commands to external equipment.

5. Reports successes and failures.

6. Gets out of the way.

For the two fundamental toggle actions, Clonker will maintain a deliberately limited RAM history of the last successfully sent ON/OFF command.

This is command history, not actual equipment-state detection.

**Design objective: Be resilient in our dumbness.**

### Development priorities

The broad priorities are:

- Responsive physical controls.

- Reliable device commands.

- Simple cooperative scheduling.

- Maintained room selection.

- Configuration and serviceability.

- Useful diagnostics.

- OLED status and audible feedback.

- Rechargeable battery and power optimization.

The browser configuration interface was developed early to establish and test the action model before physical controls were integrated.

---

## 2. Architecture at a Glance

```text

        BROWSER TEST REMOTE          PHYSICAL CONTROLS

         [IMPLEMENTED]                  [PLANNED]

               |                            |

               v                            v

         HTTP /api/action               GPIO EVENTS

               |                            |

               +-------------+--------------+

                             |

                             v

                    GENERIC ACTION REQUEST

                             |

                             v

                       actions.py

                    Validate / Enqueue

                             |

                             v

                      THE DUMB QUEUE

                [IMPLEMENTED — LOGGING ONLY]

                             |

                             v

                       actions.poll()

                  Find next eligible task

                             |

                             v

                    Resolve configuration

                             |

                             v

                   Select command / toggle

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

The browser and eventual physical controls use the same action system.

No separate implementations of Denon, Roku, or television commands belong in the physical input layer.

Device-specific IP addresses, methods, and command paths belong in validated configuration.

The outbound transport knows how to send HTTP commands. It does not know why a command was selected.

---

## 3. Implementation Status

**Status reference: October 20, 2026**

### Implemented and tested

- Raspberry Pi Pico 2 W running CircuitPython.

- Wi-Fi connectivity and serial diagnostics.

- GP17 SERVICE/DEVICE filesystem-ownership jumper.

- JSON v2 configuration with three rooms.

- Validated configuration held in RAM.

- Browser configuration editor on HTTP port 9090.

- Browser clock synchronization.

- Revision-aware configuration saves.

- Configuration backup rotation.

- Stale-browser-tab revision conflict detection.

- Browser Test Remote at `/remote.html`.

- Fourteen fundamental action buttons.

- POST `/api/action` routing to `actions.dispatch()`.

- Logging-only fundamental action dispatcher.

- Fast internal `device_config.action_details()` accessor.

- Browser responses describing accepted dispatcher requests.

The fourteen fundamental action buttons have been exercised through the logging-only dispatcher.

**No real outbound AV equipment commands have been sent by this dispatcher.**

### Implemented with additional testing still appropriate

- Strict JSON v2 validation.

- Expected-revision persistence.

- Disk-versus-RAM configuration change detection.

- Verified temporary-file writes.

- Backup-based configuration recovery.

- Bounded cooperative inbound HTTP service.

These features have been exercised in development, but not every failure scenario has been tested.

Interrupted writes, power-loss behavior, malformed HTTP requests, and other failure-injection cases must not be described as verified without new evidence.

Backup rotation is not a power-loss-atomic transaction.

### Not yet implemented

- The Dumb Queue.

- Scheduled action execution.

- Outbound HTTP GET/POST transport.

- RAM toggle-command history.

- User-defined custom-action execution.

- Physical button and encoder input.

- Physical CONFIG/RUN switch.

- Physical room selector.

- OLED status.

- Audible feedback.

- Battery management and sleep/wake behavior.

### Next development milestone

Implement the Dumb Queue in logging-only mode and test it through the existing browser Test Remote.

After successful queue testing, introduce outbound HTTP transport and perform the first real Denon Volume Up test.

---

## 4. Current Firmware Map

| File | Responsibility |

|---|---|

| `firmware/boot.py` | GP17-selected USB/Pico filesystem ownership |

| `firmware/code.py` | CircuitPython application entry point |

| `firmware/clonker/main.py` | Startup, Wi-Fi initialization, cooperative main loop |

| `firmware/clonker/controls/switches.py` | Simulated CONFIG switch; future physical input |

| `firmware/clonker/controls/pins.py` | Physical GPIO definitions |

| `firmware/clonker/device_config_v2.py` | JSON schema, validation, RAM snapshot, revisions, persistence, recovery |

| `firmware/clonker/device_config.json` | Checked-in example JSON v2 configuration |

| `firmware/clonker/actions.py` | Shared fundamental dispatcher; future queue and toggle history |

| `firmware/clonker/net/web.py` | Inbound CONFIG-mode HTTP service |

| `firmware/clonker/www/index.html` | Browser configuration and clock interface |

| `firmware/clonker/www/remote.html` | Browser Test Remote |

| `firmware/clonker/system/clock.py` | Monotonic and browser-synchronized time services |

| `firmware/clonker/system/logger.py` | Serial diagnostics |

| `firmware/clonker/legacy/device_config.py` | Historical XML v1 engine |

| `firmware/clonker/legacy/device_config.xml` | Historical XML v1 example |


The outbound HTTP transport is planned for `firmware/clonker/net/http_transport.py` during Chapter 3, Phase B. It is not yet implemented.

The `net/` package owns networking services; the `system/` package owns shared clock and logging services.

The deployed Pico configuration may differ from the JSON example committed to GitHub.

---

## 5. Operating Modes

Clonker has two independent mode dimensions.

### SERVICE (USB) / DEVICE

This controls filesystem ownership.

It is selected at boot using GP17.

| Mode | GP17 | Filesystem ownership |

|---|---|---|

| SERVICE | Open | USB host writes |

| DEVICE | Grounded | Pico firmware writes |

Changing this mode requires a full power cycle.

A CircuitPython soft reload is not sufficient to reliably change filesystem ownership.

### CONFIG / RUN

This controls application behavior.

**CONFIG:**

- Browser management interface available.

- Configuration editing and clock synchronization available.

- Browser Test Remote available.

- Device actions remain operational.

**RUN:**

- Management HTTP listener stopped.

- Physical remote-control functions continue operating.

- No configuration reload required merely to change mode.

The physical CONFIG/RUN switch is not yet wired.

The firmware currently simulates CONFIG mode enabled.

SERVICE/DEVICE and CONFIG/RUN must not be confused.

See [Operating Modes](OPERATING_MODES.md).

---

## 6. Configuration Ownership

The active firmware uses JSON v2 configuration through:

`firmware/clonker/device_config_v2.py`

The configuration contains:

- Three fixed rooms.

- Three optional device endpoints per room.

- Fourteen fixed fundamental actions per room.

- A reserved `custom_actions` list per room.

### One authoritative configuration snapshot

The configuration module maintains the active validated configuration in its private `_current` dictionary.

Its responsibilities include:

- Loading the primary configuration or a valid backup.

- Validating configuration structure and values.

- Maintaining the active RAM snapshot.

- Calculating revisions.

- Saving validated configuration.

- Protecting against stale browser saves.

- Managing backup generations.

A failed save must not publish the proposed configuration.

A successful save publishes the new validated configuration.

Manual filesystem edits outside the configuration engine are not automatically adopted into RAM.

### Defensive public access

The existing public functions include:

```python

current()

room(room_id)

```

These provide validated copies for callers that need defensive access.

### Fast internal action access

The implemented internal accessor is:

```python

action_details(room_id, action_id)

```

It returns references to the already-validated room and action dictionaries.

This avoids repeatedly validating and copying the entire configuration for every action request.

**Read-only by contract:**

- Internal action modules may inspect returned data.

- Internal action modules must not modify returned dictionaries.

- Only `device_config_v2.py` may modify or replace the active configuration.

- The returned references are not immutable Python objects.

- No second configuration cache is required.

The current logging-only dispatcher uses this accessor.

Future queued actions should resolve configuration when executed, rather than retain stale configuration references indefinitely.

A successful configuration change should clear pending tasks and invalidate affected toggle history.

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

Each room configures its own action mappings.

### Ordinary actions

Twelve actions have:

- `target`

- `method`

- `path`

Example:

```json

{

  "target": "avr",

  "method": "GET",

  "path": "/goform/formiPhoneAppDirect.xml?MVUP"

}

```

### Toggle actions

Two actions have paired ON/OFF paths:

- `mute-toggle`

- `power-toggle`

They use:

- `target`

- `method`

- `on_path`

- `off_path`

The toggle command selection is handled by `actions.py`, not by the configuration module or HTTP transport.

### Blank commands

A blank command path or unconfigured device endpoint is valid.

It represents an intentional no-op.

A no-op is not an external HTTP failure.

It must not advance toggle history.

### Physical mapping

Physical controls generate generic actions.

Examples:

- Volume encoder clockwise step → `volume-up`.

- Volume encoder counterclockwise step → `volume-down`.

- Navigation button → `nav-up`, `nav-left`, etc.

- Guarded SYSTEM MASTER button → `power-toggle`.

Physical controls must not embed vendor-specific HTTP paths or IP addresses.

---

## 8. The Dumb Queue — Cooperative Action Scheduling

**Design agreed:** October 20, 2026  

**Implementation status:** IMPLEMENTED AND BENCH-TESTED — logging-only Phase A complete; outbound HTTP pending.

### Purpose

The Dumb Queue is a single, lightweight, time-scheduled action queue owned by `actions.py`.

It provides a common execution mechanism for:

- Browser Test Remote actions.

- Physical button actions.

- Volume and selector encoder events.

- Future user-defined custom commands.

- Future startup or ignition actions, where appropriate.

The objective is to avoid separate execution frameworks for immediate actions, delayed commands, and custom sequences.

**One queue. One poller. One shared HTTP transport.**

### Conceptual task representation

A fundamental action task might look like:

```python

{

    "room": "room-1",

    "action": "volume-up",

    "due": 0

}

```

A future custom-command task may contain a resolved endpoint, method, path, and execution deadline.

These are conceptual structures, not committed implementation formats.

The final representation should be compact and inexpensive on the Pico.

### Monotonic scheduling

The queue uses:

```python

time.monotonic()

```

This clock measures elapsed time independently of the browser-synchronized wall clock.

Rules:

- `due = 0` means execute as soon as the poller can.

- A positive `due` is an absolute monotonic deadline.

- A scheduled task becomes eligible when its deadline is reached or passed.

- Deadlines are earliest execution times, not exact timing guarantees.

- Browser clock synchronization does not affect pending deadlines.

The implementation must account for monotonic timer rollover or long-uptime limitations appropriate to CircuitPython.

### Not strict FIFO

The Dumb Queue is deliberately **not strict FIFO**.

A task scheduled for the future does not block an immediate task queued behind it.

The poller looks for an eligible task.

When several tasks are eligible, it processes them in insertion order.

Consider:

```text

1. Roku Home executes immediately.

2. Denon Quick Select 1 is scheduled

   for two seconds later.

3. User turns the volume knob.

4. Volume Up executes immediately.

5. Quick Select 1 executes when due.

```

This interleaving is intentional.

Clonker does not reserve exclusive execution time for custom sequences.

For V1, preserving strict command-chain isolation is not a requirement.

### Small queue, simple selection

The queue will have a bounded maximum size.

The scheduler may scan pending tasks to find the next eligible task.

Maintaining a continuously sorted queue is unnecessary unless measurements demonstrate a benefit.

The implementation should favor simplicity over cleverness.

### One task per poll

The planned scheduler entry point is:

```python

actions.poll()

```

It executes at most one eligible outbound command per invocation.

Then it returns control to the cooperative main loop.

Conceptually:

```python

while True:

    web.poll()

    actions.poll()

    # Future GPIO, display, and other services

```

This is illustrative; the actual implementation must preserve existing main-loop behavior and operating modes.

### Cooperative, not magically asynchronous

The queue scheduler itself must not block while waiting for a task's due time.

However, an outbound HTTP request may block temporarily while connecting, sending, or receiving.

A task queue alone does not make synchronous network I/O nonblocking.

The initial implementation may use short, bounded synchronous HTTP requests.

Every request must:

- Have a finite timeout.

- Release socket resources.

- Report success or failure.

- Avoid indefinite waits.

- Avoid automatic retries that could duplicate commands.

Actual response latency should be measured before introducing asynchronous networking complexity.

---

## 9. Volume Encoder and Queue Behavior

The initial volume encoder strategy remains deliberately simple.

Each recognized encoder step generates one fundamental action.

Clockwise:

```text

volume-up

```

Counterclockwise:

```text

volume-down

```

Every such task is immediately eligible:

```python

due = 0

```

A rapid rotation may enqueue multiple tasks.

The queue works them off as quickly as the poller and outbound HTTP transport permit.

### Initial rules

- No volume acceleration.

- No command accumulation.

- No deduplication.

- No special volume transport.

- No automatic retries.

- No persistent HTTP connection requirement.

- No arbitrary dropping of valid commands while capacity remains.

### Why testing matters

Eight volume events may result in eight HTTP requests.

Their total execution time depends on actual network and receiver behavior.

The initial design accepts this.

If responsiveness proves inadequate, future options include:

- Encoder event accumulation.

- Rotation-speed-dependent acceleration.

- Device-supported command batching.

- Connection reuse.

- Queue capacity adjustments.

These are future optimizations, not V1 requirements.

A queue overflow should reject new work and log the event rather than silently erase existing valid tasks.

---

## 10. Queue Failure and Recovery Policy

**Design principle: One failed external command cancels pending work, not the remote itself.**

Clonker adopts a deliberately severe V1 failure policy.

If an outbound HTTP command fails or times out:

1. Record the failed command.

2. Record the error or timeout.

3. Clear every remaining pending task.

4. Record how many tasks were discarded.

5. Return control to the main loop.

6. Accept new user actions normally.

There are no automatic retries.

There is no deferred replay after connectivity returns.

A failed volume command should not unexpectedly execute several seconds later when Wi-Fi recovers.

### Failure handling table

| Condition | Planned behavior |

|---|---|

| HTTP success | Remove completed task; continue |

| HTTP error | Clear pending queue; log |

| HTTP timeout | Clear pending queue; log |

| Wi-Fi unavailable | Fail promptly; clear queue |

| Invalid action request | Reject request; preserve existing queue |

| Queue at capacity | Reject new task; log overflow |

| Scheduled task not due | Leave pending; consider another eligible task |

| Blank command or endpoint | Safe no-op; no outbound HTTP |

| Successful configuration change | Clear pending tasks |

| Browser clock synchronization | No queue change |

### Recovery philosophy

Clonker does not attempt elaborate automatic equipment-state recovery.

The next user action starts fresh.

A subsequent Home press, Quick Select command, or other user action may naturally restore the desired equipment behavior.

This is a deliberate limitation, not an overlooked requirement.

### Diagnostics

The action system should eventually expose lightweight status information:

- Pending task count.

- Last attempted command.

- Last command result.

- Last failure or timeout.

- Number of discarded tasks.

- Queue overflow events.

Initially these details are reported through serial logging.

A future OLED may display concise failure or status information.

The objective is useful diagnostics, not a continuously synchronized model of every connected device.

---

## 11. Fundamental Toggle Actions

**Design agreed:** October 18, 2026  

**Current status:** JSON ON/OFF fields implemented; RAM history and direction selection planned.

### Scope

Only two fundamental actions require toggle history:

- `power-toggle`

- `mute-toggle`

The configuration schema already supports their paired paths.

### Dumb RAM history

`actions.py` maintains a small dictionary of the last successfully sent direction for each room and toggle action.

Conceptually:

```text

room-1: power-toggle=unknown, mute-toggle=unknown

room-2: power-toggle=unknown, mute-toggle=unknown

room-3: power-toggle=unknown, mute-toggle=unknown

```

### Selection rules

| Last successful direction | Next attempted direction |

|---|---|

| Unknown | ON |

| ON | OFF |

| OFF | ON |

The direction is selected when the queued task executes.

History advances only after a successful outbound command.

If the request fails, times out, or is a no-op, history does not advance.

### Native toggle commands

Some devices provide one native toggle command.

For these devices, the JSON configuration may contain identical `on_path` and `off_path` values.

Clonker may alternate its internal ON/OFF history while sending the same command every time.

### No actual-state detection

The RAM history records commands successfully sent.

It does not prove that equipment changed state.

Other remotes, apps, and HDMI-CEC may alter actual equipment state independently.

This limitation is accepted for V1.

### Configuration changes

Successful configuration changes must not leave old toggle history associated with new command mappings.

The implementation should invalidate affected toggle history.

A simple global history reset on a successful configuration change is acceptable for V1.

### Ownership

Toggle logic belongs in `actions.py`.

It does not belong in:

- `device_config_v2.py`

- Physical GPIO drivers.

- The HTTP transport.

- The browser Test Remote.

No persistent toggle-history fields are required.

---

## 12. Future User-Defined Custom Actions

**Status:** Design direction agreed; schema extension and execution not implemented.

The JSON v2 room structure already reserves:

```json

"custom_actions": []

```

The current validator requires this list to remain empty.

### V1 design philosophy

Custom actions should initially be simple collections of the same HTTP commands already supported by fundamental actions.

Each step may define:

- Target device.

- HTTP method.

- Command path.

- Delay or scheduling offset.

No new vendor-specific command language is required.

### Illustrative custom action

```json

{

  "id": "movie-time",

  "name": "Movie Time",

  "steps": [

    {

      "target": "streaming",

      "method": "POST",

      "path": "/keypress/Home",

      "wait": 0

    },

    {

      "target": "avr",

      "method": "GET",

      "path": "/goform/formiPhoneAppDirect.xml?MSQUICK1",

      "wait": 2

    }

  ]

}

```

**This example is conceptual and is not accepted by the current JSON validator.**

The exact meaning of `wait`, allowed ranges, and step limits remain to be finalized.

### Queue integration

The preferred implementation is to expand a custom action into ordinary scheduled command tasks.

For example:

```text

Roku Home                  due = 0

Denon Quick Select 1       due = start + 2 seconds

```

Unrelated immediate actions may execute while a delayed custom step is waiting.

No separate custom-action execution engine is required.

### Timing semantics

For V1, custom delays are scheduling offsets rather than hard real-time guarantees.

Tasks may execute later than scheduled when the Pico or network is busy.

The design does not require exact deterministic timing.

If future custom commands require strict dependencies or guaranteed minimum intervals after preceding command completion, those requirements can be evaluated separately.

### V1 boundaries

Avoid introducing:

- Arbitrary Python scripting.

- Nested custom-command recursion.

- Loops.

- Conditional branches.

- Complex equipment-state queries.

- Automatic recovery workflows.

- Separate command-chain execution engines.

Custom actions should reuse the same queue and outbound transport as fundamental actions.

### User interface

No browser configuration UI changes are planned during the initial queue and HTTP milestones.

Custom-action schema and UI development will follow after the basic action pipeline is tested.

---

## 13. Outbound HTTP Transport

**Status:** Planned; not implemented.

Outbound device communication is separate from Clonker's inbound management HTTP server.

### Responsibilities

The transport should:

- Accept a configured endpoint.

- Accept GET or POST.

- Accept a configured command path.

- Open the required network connection.

- Send the request.

- Obtain enough response information to determine success or failure.

- Apply bounded timeouts.

- Close resources.

- Return a concise result.

### Architectural separation

The transport must not:

- Know which physical button was pressed.

- Select a room.

- Choose a toggle direction.

- Maintain toggle history.

- Interpret custom-action sequences.

- Modify configuration.

- Automatically retry failed commands.

The transport handles networking, not application policy.

### Network constraints

Both inbound and outbound networking use the Pico's Wi-Fi radio.

The outbound transport must not interfere with the active inbound management client connection.

One TCP connection per outbound command is acceptable initially.

Persistent connections and pooling are optional future optimizations.

### Failure handling

The transport reports an HTTP or network failure to `actions.py`.

`actions.py` applies the Dumb Queue failure policy.

The transport itself does not clear the queue.

---

## 14. Browser Test Remote and Action API

The existing browser Test Remote uses:

```text

POST /api/action?room=room-1&action=volume-up

```

The request currently reaches:

```python

actions.dispatch(room_id, action_id)

```

The dispatcher validates the request, enqueues the action, and returns a queue-acceptance acknowledgment. Actual execution remains logging-only during Phase A.

### Implemented queue integration

The browser request submits an action to the Dumb Queue.

The API response indicates whether the request was accepted for scheduling.

**Queued does not mean executed.**

**Executed does not necessarily mean the external device changed state.**

This distinction must remain clear in logs and browser feedback.

The browser should not need to wait for a scheduled command to finish.

### Compatibility

The existing browser Test Remote should remain usable without unnecessary UI redesign.

Preserve the established API response structure where practical.

If response fields or status meanings change, document the changes and test the existing browser.

---

## 15. Cooperative Main Loop

The firmware uses a cooperative main loop.

Existing services include Wi-Fi operation, configuration handling, clock services, and inbound HTTP polling.

The action scheduler is an implemented polled service, active in both CONFIG and RUN modes.

Conceptually:

```python

while True:

    web.poll()

    actions.poll()

    # Physical input polling

    # Display and other services

```

This is an architectural illustration, not a literal replacement for `main.py`.

### Scheduling goals

- Keep each poll short.

- Avoid blocking waits for scheduled tasks.

- Return control between outbound commands.

- Bound unavoidable network blocking.

- Preserve browser responsiveness in CONFIG mode.

- Preserve action execution in RUN mode.

- Avoid starving future physical input handling.

The existing inbound HTTP service polls approximately every 10 ms under its current configuration.

That is not a proven end-to-end physical-input latency guarantee.

Real hardware and network measurements will guide future optimization.

### Clock responsibilities

The browser-synchronized clock is useful for:

- User-visible date and time.

- Log timestamps.

- Diagnostics.

The monotonic clock is used for:

- Action scheduling.

- Relative delays.

- Timeouts and elapsed-time measurements, where appropriate.

Changing the wall clock must not require clearing the Dumb Queue.

---

## 16. Physical Controls and Hardware Integration

Physical GPIO controls are not yet connected to the action dispatcher.

The intended event path is:

```text

Physical button or encoder

          |

          v

GPIO sampling / decoding

          |

          v

Generic action event

          |

          v

actions.enqueue(...)

          |

          v

The Dumb Queue

          |

          v

actions.poll()

          |

          v

Configured HTTP command

```

### Design requirements

- Reliable button debounce.

- Correct encoder direction decoding.

- No vendor-specific logic in GPIO handlers.

- No unnecessary blocking delays.

- Defined behavior for held controls.

- Bounded queue capacity.

- Responsiveness during normal HTTP activity.

The Grayhill optical volume encoder requires separate electrical verification before GPIO integration.

### Guarded SYSTEM MASTER

The guarded power button will eventually serve both as a normal `power-toggle` control and a possible wake source from deep sleep.

The sleep/wake design is documented in [Hardware & Controls](HARDWARE_CONTROLS.md).

No sleep/wake implementation is part of the current action queue milestone.

---

## 17. Security and Network Boundaries

The browser management interface is intended for a trusted local network.

It currently has no application-level authentication.

Do not expose port 9090 through internet port forwarding.

CircuitPython Web Workflow is disabled in private `settings.toml` because of suspected socket conflicts.

This is separate from Clonker's own management server.

Configuration endpoints and command paths should remain validated before being used by outbound networking.

---

## 18. Development and Test Sequence

### Phase A — Logging-only Dumb Queue

Implement the queue without real outbound HTTP commands.

Preserve the existing browser Test Remote as the primary test interface.

Test:

1. Enqueue one immediate action.

2. Verify the action is accepted and logged.

3. Verify `actions.poll()` executes at most one task per invocation.

4. Enqueue several immediate actions.

5. Verify they are all processed.

6. Schedule an action for a future monotonic deadline.

7. Enqueue an immediate action behind it.

8. Verify the immediate action executes first.

9. Verify eligible tasks execute in insertion order.

10. Simulate an outbound failure.

11. Verify the remaining queue is cleared.

12. Fill the queue and verify overflow handling.

13. Verify invalid requests do not disturb existing tasks.

14. Verify wall-clock synchronization does not change deadlines.

15. Verify a successful configuration change clears pending tasks.

16. Verify logging reports task results and discarded work.

17. Verify the browser request returns after enqueueing rather than waiting for execution.

**Phase A status — October 20, 2026:** Logging-only queue validation completed. Browser submission, delayed-task bypass, simulated failure cancellation, 128-task capacity enforcement, overflow rejection, and post-cleanup execution passed.

Some broader checks listed above, including wall-clock independence and clearing a nonempty queue after configuration changes, have not been individually demonstrated. These remain regression-test items.

See [Development History](DEVELOPMENT_HISTORY.md), Milestone 7, for test evidence and the scheduler/HTTP responsiveness investigation.

### Phase A implementation baseline — October 20, 2026

The logging-only Dumb Queue is implemented and bench-tested.

The current action engine:

- Accepts fundamental actions through `dispatch()`.
- Maintains a bounded 128-task queue.
- Stores room ID, action ID, and monotonic due time.
- Executes at most one eligible task per `poll()`.
- Allows immediate actions to bypass future-dated tasks.
- Resolves current configuration when executing.
- Logs simulated execution without transmitting HTTP.
- Treats blank commands and endpoints as safe no-ops.
- Clears pending tasks after execution failure.
- Rejects overflow rather than discarding existing work.

The temporary diagnostic test functions and HTTP test endpoint were removed after validation.

#### Cooperative scheduling baseline

The current development settings are:

| Parameter | Value |
|---|---|
| Action poll interval | 0.01 seconds |
| Management HTTP poll interval | 0.01 seconds |
| Main-loop idle sleep | 0.001 seconds |
| Silent inbound HTTP client timeout | 0.5 seconds |
| Active inbound HTTP client timeout | 4.0 seconds |

These values improved observed responsiveness during bench testing.

They are implementation settings, not guaranteed real-time performance limits.

#### Inbound HTTP behavior

The CONFIG management server currently supports one active client connection.

Some browsers establish connections that send no HTTP request bytes. Such connections can temporarily prevent another request from being accepted.

A short silent-client timeout limits the resulting delay without imposing the same deadline on active transfers.

Occasional zero-byte timeout warnings may remain during browser navigation.

The management server and outbound equipment transport have separate responsibilities and must remain architecturally independent.

#### Phase B readiness

The queue is ready for initial integration with a minimal outbound HTTP transport.

The following remain pending:

- Actual GET and POST transmission.
- Bounded outbound socket operations.
- HTTP response validation.
- Network failure and timeout tests.
- Toggle history and direction selection.
- RUN-mode execution with physical inputs.
- Measured throughput under real device traffic.

Do not interpret successful queue simulation as proof of outbound networking reliability.

### Phase B — First real outbound command

After logging-only queue validation:

1. Review current Pico networking capabilities.

2. Implement a minimal outbound HTTP transport.

3. Preserve short, bounded timeouts.

4. Connect ordinary fundamental actions to the transport.

5. Verify the configured Denon endpoint and command path.

6. Send one Denon Volume Up command from the browser Test Remote.

7. Confirm the observed equipment response.

8. Verify logs and failure reporting.

9. Test blank commands and missing endpoints as safe no-ops.

10. Test deliberate network failure and queue clearing.

### Phase C — Broader fundamental actions

- Test Denon Volume Down.

- Test Roku navigation commands.

- Test GET and POST.

- Implement RAM toggle history.

- Verify independent room/action toggle behavior.

- Verify configuration changes invalidate affected toggle history.

- Test execution in RUN mode.

### Phase D — Physical inputs

- Establish GPIO allocation.

- Wire one momentary button.

- Test generic action enqueueing.

- Test encoder step generation.

- Measure queue throughput and physical responsiveness.

- Integrate room selection and other controls.

### Phase E — Custom actions

- Extend JSON v2 validation for custom actions.

- Define exact step and delay semantics.

- Expand custom actions into scheduled tasks.

- Test command interleaving.

- Test failure cancellation.

- Add browser configuration UI when ready.

This development sequence is deliberately incremental.

Do not introduce untested complexity merely because a future feature might eventually need it.

---

## 19. Architectural Boundaries

| Component | Owns |

|---|---|

| `device_config_v2.py` | Validated configuration, revisions, persistence, recovery |

| `actions.py` | Action validation, task queue, scheduling, toggle history, command selection |

| Outbound HTTP transport | HTTP requests, socket lifecycle, timeouts, transport results |

| `web.py` | Inbound browser management and action submission |

| `main.py` | Cooperative service polling and application lifecycle |

| `controls/` | Physical input detection and generic events |

| `clock.py` | Clock and synchronization services |

| `logger.py` | Diagnostics |

### Non-negotiable boundaries

- Configuration owns configuration data.

- Actions owns execution policy.

- Transport owns networking.

- Physical controls generate generic events.

- External equipment owns its actual state.

Do not add a second configuration cache.

Do not let physical controls bypass the shared action system.

Do not let the transport own toggle history.

Do not automatically replay failed commands.

Do not make custom commands a separate execution universe.

---

## 20. Design Principles Worth Remembering

**Less sleek. More CLONK.**

**Smart enough to know when to be dumb.**

**One queue. One poller. One transport.**

**A future task must not hold an immediate button press hostage.**

**One failed external command cancels pending work, not the remote itself.**

**Clonker sends commands. Equipment owns state.**

**Clonker does not guarantee when external equipment will respond. It guarantees that it will not wait forever to find out.**

---

## 21. Reference Documents

- [Chapter 2 Handoff](CHAPTER_2_HANDOFF.md) — verified previous milestone and development context.

- [Operating Modes](OPERATING_MODES.md) — SERVICE/DEVICE and CONFIG/RUN.

- [Configuration & Recovery](CONFIGURATION.md) — JSON v2 schema and persistence safeguards.

- [Firmware & Network](FIRMWARE_NETWORK.md) — cooperative loop, inbound HTTP, clock, and logging.

- [Hardware & Controls](HARDWARE_CONTROLS.md) — physical controls, guarded power, battery, and sleep/wake design.

- [Development & Deployment](DEVELOPMENT.md) — iPad/Windows/Pico workflow.

- [Development History](DEVELOPMENT_HISTORY.md) — dated development milestones.

- [Terminology Audit](TERMINOLOGY_AUDIT.md) — historical terminology reconciliation.

- [Old Architecture](OLD_ARCHITECTURE.md) — historical reference, not active implementation.

---

**CLONK! ⚡🔩**

*The Clonker 10000 — because apparently a normal remote control wasn't complicated enough.*