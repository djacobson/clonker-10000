# THE CLONKER 10000 — Development History

**Engineering journal — reconstructed October 19, 2026**  
**Repository:** [djacobson/clonker-10000](https://github.com/djacobson/clonker-10000)  
**Platform:** Raspberry Pi Pico 2 W / CircuitPython 10.3.1

> The Clonker has a memory. Occasionally it remembers the bugs, too.

---

## About This Journal

This document records the development history of The Clonker 10000.

It began as `configuration-testing.md`, a record of XML configuration tests. As the project evolved, it accumulated JSON experiments, browser integration tests, debugging discoveries, and implementation milestones.

It had become an engineering journal without quite realizing it.

This document reorganizes that history chronologically, preserves significant test evidence, and eliminates repetitive explanations better maintained in the project's technical documentation.

### How to interpret historical results

- **PASS:** The described behavior was observed in the Pico REPL, browser, or hardware within the stated test scope.
- **Implemented:** Present in the source code, but not necessarily tested under every condition.
- **Pending:** Not demonstrated at that point in development.
- **Historical:** Correct for that milestone, but possibly superseded by later work.

An earlier statement that JSON v2 was not integrated, for example, remains historically accurate even though integration was completed later.

This journal describes **how we got here**, not necessarily the current state of every feature.

Current documentation:

- [Architecture](ARCHITECTURE.md)
- [Configuration](CONFIGURATION.md)
- [Development & Deployment](DEVELOPMENT.md)
- [Operating Modes](OPERATING_MODES.md)
- [Chapter 2 Handoff](CHAPTER_2_HANDOFF.md)

The original test record and its revisions remain recoverable through Git history.

---

## Milestone Index

| Date | Milestone | Outcome |
|---|---|---|
| Oct 16, 2026 | 1. XML v1 configuration | Browser editing and persistence verified |
| Oct 16, 2026 | 2. JSON v2 persistence engine | Validation, revision, backups, and fallback verified |
| Oct 16, 2026 | 3. JSON v2 browser integration | Browser-to-flash persistence verified |
| Oct 16, 2026 | 4. Defensive browser tests | Stale-revision and no-change behavior verified |
| Oct 16–19, 2026 | 5. Production JSON and toggle schema | Active JSON v2 configuration established |
| Oct 19, 2026 | 6. Browser Test Remote | Fourteen logging-only actions verified |
| Oct 20, 2026 | 7. Dumb Queue and HTTP responsiveness | Logging-only queue validated; HTTP recovery improved |
| Oct 21, 2026 | 8. Outbound HTTP and burst execution | Real Denon/Roku commands verified; five-command burst passed |

Dates are based on the original test records and Chapter 2 handoff. Changes without individually recorded timestamps are grouped into a period rather than assigned an invented date.

---

# Milestone 1 — The XML Configuration System Comes Alive

**Date:** October 16, 2026  
**Status:** PASS — hardware tested

### Goal

Prove that the Pico could load, display, edit, save, back up, and reload a configuration through a browser.

### Implementation

The initial configuration system used XML.

It supported:

- Three rooms.
- Browser configuration editing.
- HTTP POST configuration saving.
- No-change detection.
- Two generations of backups.
- Active-memory configuration updates.
- Persistence across a CircuitPython soft reboot.

The HTTP server operated on port `9090`.

The development workflow already used Working Copy on iPad, GitHub, GitHub Desktop on Windows, and USB deployment to CIRCUITPY.

### Test evidence

| Test | Result |
|---|---|
| Three-room XML load | PASS |
| Browser configuration display | PASS |
| Browser editing | PASS |
| Browser POST save | PASS |
| No-change save detection | PASS |
| Two-generation backup rotation | PASS |
| Active-memory update | PASS |
| Persistence after Ctrl+D | PASS |
| Chrome and Safari display | PASS |

The backup test performed two saves:

1. `Den` → `Den Test`
2. `Den Test` → `Den`

REPL inspection confirmed:

| Location | Room 1 |
|---|---|
| Primary XML | `Den` |
| `.bak` | `Den Test` |
| `.bak.old` | `Den` |
| Active RAM | `Den` |

Reading a backup did not modify active configuration.

The browser reported successful and unchanged saves appropriately and refreshed after saving.

The original `Den` configuration was restored.

### Important architectural foundation

The GP17 jumper established filesystem ownership:

| GP17 | Mode | Write owner |
|---|---|---|
| Open | SERVICE (USB) | USB host |
| Grounded | DEVICE | Pico firmware |

Changing this mode requires a full power cycle.

A Ctrl+D soft reload is not equivalent.

### Remaining limitations

At this milestone, not all defensive browser tests had been completed.

Outstanding areas included:

- Revision-conflict rejection.
- Invalid configuration rejection through HTTP.
- Read-only save enforcement.
- Interrupted-write recovery.

These were historical pending items, not necessarily current limitations.

### Outcome

**XML v1 configuration was operational on the Pico.**

It established the persistence and browser architecture that JSON v2 would inherit.

**CLONK! The monster has a memory.**

---

# Milestone 2 — JSON v2 Persistence Engine

**Date:** October 16, 2026  
**Status:** PASS — standalone Pico testing

### Goal

Replace the growing complexity of XML parsing with a simpler configuration format shared naturally by CircuitPython and browser JavaScript.

JSON v2 was initially tested independently of the running XML application.

### Implementation

The new `device_config_v2.py` engine provided:

- Schema version 2.
- Three fixed rooms.
- Fourteen fundamental actions per room.
- Deterministic serialization.
- Configuration revision checking.
- No-change detection.
- Verified file writes.
- Backup rotation.
- Validated fallback loading.

Tests used a disposable file:

`/clonker/test_config_v2.json`

### Initial test evidence

| Property | Observed |
|---|---|
| Schema version | 2 |
| Rooms | 3 |
| Actions per room | 14 |
| Total actions | 42 |
| JSON round trip | PASS |
| Stable revision | PASS |
| Initial serialized size | 2,754 bytes |
| Initial revision | `3596587d` |

The disposable file was written, flushed, read back, and validated successfully.

### Bug 1 — CircuitPython is not desktop Python

The initial serialization code attempted to use:

`json.dumps(..., ensure_ascii=...)`

CircuitPython 10.3.1 did not support that argument.

The unsupported argument was removed.

Subsequent serialization and revision tests passed.

**Lesson:** Confirm CircuitPython API compatibility rather than assuming full CPython behavior.

### Bug 2 — The accidental production configuration write

This was a particularly useful discovery.

During the first persistence experiment, changing the module's `CONFIG_FILE` variable did not redirect default filename arguments already bound to `load()` and `save()`.

Consequently, the first test unintentionally changed the production JSON fixture:

`Den` → `Den Test`

Fortunately, the persistence engine had created a valid backup.

The original production configuration was restored successfully.

The XML v1 configuration was unaffected.

### Corrective design

The persistence engine was revised so that:

- `load(path)` binds the active configuration to that path.
- `save()` uses the loaded path.
- An explicitly supplied save path must match the loaded path.
- A mismatch raises `ValueError` before writing.

A wrong-path save was deliberately attempted after loading the disposable configuration.

The Pico rejected it.

**Result: PASS**

All subsequent persistence experiments used the disposable path.

**Lesson:** Test isolation must be enforced by the code, not merely assumed by the developer.

### Configuration save and revision tests

Saved:

`Den` → `Den Test`

Verified:

- `save()` returned `True`.
- Primary file contained `Den Test`.
- Backup contained `Den`.
- Active RAM contained `Den Test`.
- Configuration revision changed.

An unchanged save returned `False`.

A deliberately stale revision, `00000000`, was rejected with:

`ValueError: Configuration revision mismatch`

Primary file, active RAM, and revision remained unchanged.

**Result: PASS**

### Backup rotation

Saved a second change:

`Den Test` → `Den Test 2`

Observed:

| File | Room 1 |
|---|---|
| Primary | `Den Test 2` |
| `.bak` | `Den Test` |
| `.bak.old` | `Den` |

**Result: PASS**

### Corrupted-primary recovery

The disposable primary was deliberately overwritten with invalid JSON.

The engine detected the error and loaded the valid `.bak` file.

Observed fallback:

`Den Test`

After restoring the primary, loading returned:

`Den Test 2`

The fallback process did not silently overwrite the corrupted primary.

**Result: PASS**

### Missing-primary recovery

The disposable primary was temporarily renamed to a `.held` filename.

The engine detected the missing primary and loaded `.bak`.

Observed fallback:

`Den Test`

It did not silently recreate the missing primary.

Restoring the original filename allowed the primary to load again.

**Result: PASS**

### Remaining limitations

This milestone did not prove:

- Atomic behavior during unexpected power loss.
- Recovery after interruption at every write stage.
- Explicit repair of the primary from backup.
- Browser integration.
- Full cold-power-cycle persistence.

Backup rotation involves multiple filesystem operations and is not guaranteed atomic.

### Outcome

**JSON v2's core persistence engine passed its standalone hardware tests.**

The production configuration was restored, and the original XML implementation remained operational.

**CLONK! The monster remembers where it put the file. Now.**

---

# Milestone 3 — JSON v2 Browser Integration

**Date:** October 16, 2026  
**Status:** PASS — browser-to-flash integration

### Goal

Connect the new JSON v2 engine to the Clonker's main application and browser configuration editor.

### Files involved

- `firmware/clonker/main.py`
- `firmware/clonker/web.py`
- `firmware/clonker/www/index.html`
- `firmware/clonker/device_config_v2.py`

The HTTP request allowance increased from 2,048 to 10,240 bytes to accommodate the JSON configuration.

The XML implementation was retained as a rollback reference.

### Bug — Missing EWOULDBLOCK

The first JSON-integrated application startup loaded configuration and started the HTTP listener successfully.

The polling loop then crashed with:

`AttributeError: 'module' object has no attribute 'EWOULDBLOCK'`

CircuitPython 10.3.1 exposed `errno.EAGAIN` instead.

The socket handler was corrected.

The application subsequently started and served the browser interface.

**Result: PASS after correction**

### Browser rendering tests

Verified:

- JSON v2 loaded through the application.
- HTTP server listening on port 9090.
- Three fixed rooms displayed.
- Room names displayed correctly.
- TV, AVR, and streaming endpoints displayed.
- Expandable action editors rendered.
- Fourteen Room 1 actions visible.
- Target, method, and path controls rendered.
- SERVICE mode disabled saving.
- DEVICE mode enabled saving.
- Clock status displayed.

Blank endpoints and command paths remained valid.

### Disposable configuration isolation

The Pico's local `main.py` was temporarily redirected to:

`/clonker/test_config_v2.json`

The browser displayed:

`ROOM-1 — Den Test 2`

This confirmed that the disposable file, rather than production `Den`, was being loaded.

The override was local to the hardware test.

### First JSON browser save

In DEVICE mode, the browser changed:

`Den Test 2` → `Den Test 3`

The browser reported:

`Configuration saved successfully.`

REPL inspection confirmed:

| File | Room 1 |
|---|---|
| Primary | `Den Test 3` |
| `.bak` | `Den Test 2` |

**Result: PASS**

### Reload verification

Entering the REPL restarted the Python runtime and cleared the configuration module's active state.

Calling `cfg.current()` initially raised:

`RuntimeError: Configuration not loaded`

This was expected, not a persistence failure.

Explicitly reloading the disposable configuration returned:

- Room 1: `Den Test 3`
- Revision: `9f3890e8`

**Result: PASS**

### Verified end-to-end path

Browser → HTTP server → JSON validation → Pico flash → backup → reload into RAM.

### Remaining limitations

This milestone did not yet verify all defensive browser behavior, including stale-tab rejection, invalid-value handling, or comprehensive recovery from interrupted saves.

### Outcome

**JSON v2 successfully replaced XML in the operational browser configuration path.**

**CLONK! The browser and the flash drive are on speaking terms.**

---

# Milestone 4 — Defensive Browser Testing

**Date:** October 16, 2026  
**Status:** PASS — selected defensive tests

### Goal

Ensure that ordinary browser operations could not casually overwrite newer configuration or create unnecessary flash writes.

Tests used DEVICE mode and the disposable JSON configuration.

### Test 1 — Two-tab stale revision

Two browser tabs loaded the same configuration.

Tab 1 changed Room 1 to:

`Den Test 5`

The save succeeded.

Tab 2 retained the older revision and attempted:

`Den Test STALE`

The browser rejected the save:

`Save failed: Configuration revision mismatch`

Refreshing Tab 2 displayed:

`Den Test 5`

The newer configuration survived the stale-save attempt.

**Result: PASS**

### Test 2 — No-change save

After refreshing the browser, no fields were changed.

The user clicked Save.

The browser reported:

`No changes to save.`

**Result: PASS — browser behavior**

The engine was designed to avoid backup rotation when the configuration was unchanged.

However, backup files were not separately inspected after this specific browser test.

That distinction is preserved.

### Error-message improvement

The revision error was subsequently improved to:

`Configuration revision mismatch. Changes not saved. Refresh page.`

The revised wording was confirmed in GitHub source.

A second browser test of that exact revised message was not recorded in the original test entry.

### Remaining limitations

At this point, the test record still listed:

- Invalid configuration rejection through the browser.
- HTTP-level SERVICE-mode write rejection.
- Editing and saving device endpoints.
- Editing and saving nonempty action paths.
- Browser clock synchronization.
- Full cold-power-cycle persistence.
- Final production-path restoration.

Some of these were addressed in later development. The original list describes the state of verification at this milestone.

### Outcome

**The browser correctly rejected stale configuration and recognized unchanged saves.**

**CLONK! The monster refuses stale instructions and unnecessary saves.**

---

# Milestone 5 — Production JSON v2 and Toggle Schema

**Period:** October 16–19, 2026  
**Status:** Active configuration established; toggle execution pending

### Goal

Complete the transition to production JSON v2 and prepare the configuration model for real device commands.

### Production-path restoration

The temporary disposable configuration override was removed.

The application returned to:

`/clonker/device_config.json`

A final quick check confirmed that the Den room was visible.

**Result: PASS — limited production-path smoke test**

This did not constitute a complete rerun of every persistence and recovery test.

### Configuration model

The active JSON v2 configuration supports:

- Three fixed room IDs.
- Editable room display names.
- Optional TV, AVR, and streaming endpoints.
- IPv4 addresses with optional ports.
- Fourteen fundamental actions per room.
- Configurable target device.
- HTTP GET or POST.
- Configurable command paths.
- Blank endpoints and paths.
- Reserved custom-action structure.

### Toggle redesign

Two fundamental actions were redesigned:

- `mute-toggle`
- `power-toggle`

Instead of a single `path`, these use:

- `on_path`
- `off_path`

The browser editor and JSON validator were updated to support the revised schema.

This permits devices with separate ON and OFF commands as well as devices with a native toggle command.

### Agreed runtime design

The initial toggle execution policy was defined:

1. Maintain RAM-only last-successful-command history.
2. Track each room and toggle action independently.
3. When history is unknown, attempt ON first.
4. After successful execution, alternate direction.
5. Do not advance after failure or no-op.
6. Allow identical ON/OFF paths.
7. Do not persist command history to flash.
8. Do not mistake command history for actual equipment state.

These were **design decisions**, not implemented runtime behavior at this milestone.

### Important distinction

The configuration schema can describe ON/OFF commands.

That does not mean the dispatcher can yet execute them.

No outbound HTTP transport was operational.

### Outcome

**The configuration model was ready for the next action-dispatch development phase.**

**CLONK! Two paths for power. Zero assumptions about reality.**

---

# Milestone 6 — Browser Test Remote

**Date:** October 19, 2026  
**Status:** PASS — logging-only action dispatch

### Goal

Create a browser-based test remote that exercises the same generic action vocabulary intended for future physical controls.

This allows software behavior to be tested before wiring encoders, buttons, or room selectors.

### Implementation

The following components were integrated:

| File | Purpose |
|---|---|
| `clonker/actions.py` | Shared logging-only dispatcher |
| `clonker/web.py` | HTTP action endpoint |
| `clonker/www/remote.html` | Browser Test Remote |
| `clonker/www/index.html` | Management page and Test Remote entry point |

The browser invokes requests such as:

```text
POST /api/action?room=room-1&action=volume-up
```

The HTTP server validates and parses the request.

It then invokes:

```python
actions.dispatch(room_id, action_id)
```

The dispatcher:

- Validates room and action identifiers.
- Resolves the configured room.
- Resolves the target endpoint.
- Inspects configured command paths.
- Reports whether the action is configured.
- Logs the action.
- Returns structured JSON.

**It does not send an HTTP command to the equipment.**

### Representative response

```json
{
  "ok": true,
  "status": "stub",
  "room": "room-1",
  "room_name": "Den",
  "action": "volume-up",
  "configured": true,
  "message": "STUB: Den / volume-up (logged; no command sent)"
}
```

The response is illustrative of a configured Den action.

`ok: true` means the stub processed the request.

It does not mean the Denon received a command.

### Fundamental action tests

All fourteen browser controls were exercised successfully on the physical Pico.

| Group | Actions tested |
|---|---|
| Volume | `volume-up`, `volume-down`, `mute-toggle` |
| Navigation | `nav-up`, `nav-down`, `nav-left`, `nav-right`, `select` |
| Shortcuts | `back`, `home` |
| Playback | `play-pause`, `skip-back`, `skip-forward` |
| Power | `power-toggle` |

**Result: PASS — logging-only dispatch**

### Room tests

The Test Remote was exercised with:

- Den.
- Sunroom.
- The unconfigured third room.

The dispatcher resolved the selected room and action.

Unconfigured actions were reported without sending commands.

**Result: PASS — logging-only dispatch**

### Browser interface milestone

The Test Remote included:

- Room selection.
- Volume and mute controls.
- Directional navigation.
- Back and Home.
- Playback controls.
- Oversized power control.
- Response/status feedback.
- Illustrative custom-action dropdown.

The management page was updated to provide a Test Remote entry point beside the clock controls.

The interface was reviewed and deployed.

A centered designer attribution was added to both browser pages.

### Custom actions

The browser displayed illustrative options including:

- Movie Mode.
- Stereo Mode.
- Next Audio Mode.

These were interface placeholders.

Custom-action execution was not implemented.

### Architectural significance

The verified action path became:

```text
Browser Test Remote
        |
        v
HTTP action endpoint
        |
        v
Shared action dispatcher
        |
        v
Current JSON configuration
        |
        v
Diagnostic logging
        |
        v
JSON stub response
```

The future outbound transport was deliberately excluded from this milestone.

### Remaining limitations

Not yet implemented:

- Real outbound HTTP GET/POST commands.
- Runtime toggle ON/OFF selection.
- RAM toggle history.
- Physical buttons and encoders.
- Physical room selector.
- Physical CONFIG/RUN switch.
- Custom-action execution.
- OLED integration.
- Audible feedback.

### Outcome

**All fourteen fundamental browser actions successfully reached the logging-only dispatcher.**

The browser, HTTP server, configuration model, and shared action interface were connected.

The next milestone would make those actions control actual equipment.

**CLONK! The monster recognizes its buttons. Next it learns to talk.**

---

# Engineering Lessons Worth Keeping

These discoveries shaped the Clonker's implementation.

| Discovery | Lesson |
|---|---|
| `json.dumps()` lacked `ensure_ascii` | CircuitPython is not full desktop Python |
| `errno.EWOULDBLOCK` was unavailable | Test actual embedded networking APIs |
| Production fixture was accidentally modified | Bind saves to the loaded configuration path |
| Disposable JSON fallback tests succeeded | Recovery should be deliberate and non-destructive |
| REPL restart cleared active configuration | RAM reset is not flash-data loss |
| Two browser tabs produced a revision conflict | Protect newer edits from stale clients |
| Unchanged saves returned no-change | Avoid unnecessary flash writes |
| GP17 mode requires a power cycle | Separate boot-time ownership from runtime reload |
| Toggle ON/OFF paths existed before execution | Configuration capability is not runtime capability |
| Browser actions passed as stubs | Test software plumbing before enabling physical effects |

These are not merely historical curiosities.

They are useful constraints for future development.

---

# Outstanding Verification Ledger

This section summarizes work not conclusively completed in the evidence reviewed through October 19, 2026.

It is not a substitute for current firmware inspection or newly recorded tests.

| Area | Remaining verification |
|---|---|
| Interrupted writes | Failure at individual write and backup-rotation stages |
| Recovery | Explicit primary repair from backup |
| Cold power cycle | Complete persistence scenarios after full hardware restart |
| HTTP validation | Comprehensive malformed-request and invalid-value tests |
| Concurrent modifications | External primary-file modification between load and save |
| Outbound networking | Connection timeouts, partial responses, failures, cleanup |
| Device commands | Actual Denon/Roku command transmission and observed effect |
| Toggle behavior | Last-successful-command state and failure/no-op handling |
| Physical controls | GPIO, encoders, switches, room selection |
| User interface | OLED and audible feedback |
| Hardware | Enclosure, service access, power architecture |

Some SERVICE-mode write protection and browser behaviors were reported as tested in later project documentation. A more precise HTTP-level test trace can be recorded if needed.

Do not mark a test PASS merely because a feature is present in source code.


---

# Milestone 7 — The Dumb Queue Comes Alive

**Date:** October 20, 2026  
**Status:** PASS — logging-only action engine; outbound HTTP pending

### Goal

Replace the immediate logging-only action dispatcher with a bounded, cooperative action queue that supports scheduling, failure cancellation, and eventual outbound device commands.

Verify that the queue operates alongside Clonker's existing browser management interface without compromising responsiveness.

### Implementation

Implemented `firmware/clonker/actions.py` as the shared Dumb Queue engine.

The engine provides:

- `dispatch(room_id, action_id, delay_seconds=0)` for validated action submission.
- `poll()` for execution of at most one eligible task per invocation.
- `clear(reason)` for cancellation of pending work.
- `status()` for lightweight diagnostics.
- A fixed queue capacity of 128 tasks.
- Immediate and delayed task scheduling using `time.monotonic()`.
- Current configuration resolution at execution time.
- Safe no-op behavior for unconfigured commands.
- Rejection of invalid action identifiers and queue overflow.
- Failure handling that discards remaining pending tasks without disabling future dispatch.

Queued tasks retain only room ID, action ID, and due time. They do not retain stale references to configuration objects.

An immediate task may bypass an earlier delayed task. Among eligible tasks, insertion order is preserved.

The browser Test Remote submits actions through the existing `/api/action` endpoint.

A successful browser response means the action was queued, not that an external device executed it.

During this milestone, execution remained logging-only. No actual Denon, Roku, or television commands were transmitted.

### Test evidence

| Test | Result |
|---|---|
| Browser Volume Up submission | PASS |
| Queued action executes through `actions.poll()` | PASS |
| Delayed Home followed by immediate Volume Up | PASS |
| Immediate action bypasses delayed action | PASS |
| Simulated execution failure | PASS |
| Failure discards two pending tasks | PASS |
| Queue fills to 128 tasks | PASS |
| 129th task rejected | PASS |
| Queued tasks drain after deadlines | PASS |
| Browser actions after test-code cleanup | PASS |
| Actual outbound HTTP commands | PENDING |
| Real network failure and timeout handling | PENDING |
| Toggle direction history | PENDING |

The failure test produced the expected cancellation message:

`DUMB QUEUE: FAILED; 2 pending tasks discarded`

The capacity test reported:

`DUMB QUEUE: Full; action rejected`

and confirmed:

`overflow_rejected=True`

The delayed-bypass test demonstrated that Volume Up executed before the earlier-enqueued, future-dated Home command.

### Scheduler responsiveness investigation

Initial integration placed `actions.poll()` inside the unrestricted main loop.

The application subsequently exhibited intermittent management-page delays and difficulty reconnecting the CircuitPython serial console.

Temporarily disabling action polling substantially improved responsiveness.

The scheduler was then changed to use a 10 ms polling interval, improving behavior further.

A 1 ms sleep was added at the end of each main-loop iteration to yield execution time to the CircuitPython runtime.

The resulting development baseline is:

| Setting | Value |
|---|---|
| Action polling interval | 10 ms |
| Management HTTP polling interval | 10 ms |
| Main-loop sleep | 1 ms |

These settings improved observed responsiveness. The tests did not isolate a single definitive cause for the original serial-console instability.

The queue's empty-state poll is inexpensive, so the result should not be interpreted as proof that queue processing itself was computationally expensive.

### HTTP responsiveness investigation

A separate intermittent delay remained when navigating between the browser Configuration and Test Remote pages.

The existing inbound HTTP server handles one active client at a time.

Additional diagnostics identified accepted connections that transmitted no request data before timing out:

`HTTP client timed out: phase=RECEIVING, request_bytes=0`

These connections temporarily occupied the server's only active client slot.

The original four-second client timeout was replaced with separate limits:

| Connection condition | Timeout |
|---|---|
| No request bytes received | 0.5 seconds |
| Active receive or send operation | 4.0 seconds |

The shorter silent-client timeout substantially reduced navigation pauses.

The behavior was observed with Chrome on Windows and Safari on iPad.

Additional request tracing confirmed successful handling of:

- `GET /`
- `GET /remote.html`
- `GET /api/clock`
- `GET /api/config`
- `POST /api/action`

Some idle connections continued to time out, but recovery was much faster.

The evidence is consistent with idle or abandoned browser connections. Their precise origin was not conclusively established.

### Cleanup and final validation

After successful queue testing:

- Removed temporary queue-test helper functions.
- Removed simulated failure injection.
- Removed the temporary `/api/test/queue` diagnostic endpoint.
- Preserved production queue failure handling.
- Preserved the browser `/api/action` endpoint.
- Disabled verbose HTTP tracing with `HTTP_DIAGNOSTICS = False`.
- Retained useful timeout warnings.

A final browser Volume Up test confirmed the normal sequence:

`QUEUED: Den / volume-up (depth 1)`

followed by:

`SIMULATED: Den / volume-up -> avr 192.168.50.44:8080 (no HTTP sent)`

The queue continued operating after diagnostic cleanup.

### Remaining limitations

- Outbound HTTP transport has not been implemented.
- No actual equipment command was transmitted.
- HTTP response handling and real network failure recovery remain untested.
- Toggle ON/OFF history is not implemented.
- Physical GPIO input is not connected.
- Long-duration responsiveness and memory stability have not been characterized.
- A nonempty queue-clear operation after a configuration change was not separately demonstrated during this milestone.
- The exact cause of idle browser connections remains unconfirmed.

### Outcome

**Chapter 3, Phase A completed successfully within its logging-only test scope.**

Clonker now has one shared, bounded action queue with cooperative scheduling and explicit failure policy.

The browser management interface remains usable with the revised scheduler and HTTP timeout settings.

The next milestone is real outbound HTTP transport.

The Dumb Queue has learned to take orders, wait its turn, and cancel everybody's plans when something goes wrong.

It has not yet learned to boss around the Denon.

**CLONK! ⚡🔩**


---

# Milestone 8 — The Clonker Learns to Talk Back

**Date:** October 21, 2026  
**Status:** PASS — outbound HTTP and controlled burst testing

### Goal

Extend the logging-only Dumb Queue into a functioning
network-command execution pipeline.

Prove that the Raspberry Pi Pico 2 W can send configured
HTTP commands to actual home theater equipment without
abandoning the simple cooperative architecture.

### Implementation

Chapter 3 Phase B introduced outbound HTTP execution
using CircuitPython socketpool networking.

The execution path is:

Browser Test Remote
    -> POST /api/action
    -> actions.dispatch()
    -> Dumb Queue
    -> actions.poll()
    -> JSON v2 action resolution
    -> Outbound HTTP transport
    -> Configured equipment

The transport supports the GET and POST commands needed
for the initial Denon and Roku integrations.

The action queue remains separate from the network
transport. It accepts commands independently of the
time required to execute them.

Commands are executed sequentially, with one eligible
queue item processed per poll.

### Network Investigation

Before integrating outbound HTTP into the firmware,
several standalone TCP experiments were performed.

Initial experiments with nonblocking socket connections
encountered CircuitPython-specific behavior, including
OSError(119), subsequent connection errors, and unreliable
immediate sends.

Repeated connect calls were not a dependable method for
determining connection completion.

Blocking connections with explicit socket timeouts
proved more predictable.

Observed successful connection times were generally
around 85–125 milliseconds for reachable equipment.

Unreachable endpoints returned errors within bounded
test intervals.

The resulting transport deliberately accepts a small,
bounded blocking interval rather than introducing a
complex asynchronous connection state machine.

This remains a cooperative scheduling tradeoff, not
a claim that outbound networking is nonblocking.

### Real Equipment Tests

Successful commands were sent to the Sunroom system:

- Denon AVR-X1800H: Volume Up.
- Denon AVR-X1800H: Volume Down.
- Roku: Home.
- Roku: Back.

The Denon returned HTTP 200 responses.

The LG television displayed the expected volume-bar
changes, providing independent visible confirmation
that the receiver commands affected the equipment.

The Roku returned HTTP 200 for tested navigation
commands.

Browser Test Remote buttons successfully submitted
commands through the same action dispatcher used by
the production queue.

### Five-Command Burst Test

A controlled REPL experiment submitted five Sunroom
Volume Up actions without polling between submissions.

All five actions were accepted.

Observed queue state before execution:

- Queue capacity: 128.
- Current depth: 5.
- Peak depth: 5.
- Last error: None.

Five successive calls to actions.poll() each executed
one queued command.

All five returned HTTP 200.

Observed individual execution times:

- 117.2 ms.
- 125.0 ms.
- 85.9 ms.
- 85.9 ms.
- 85.9 ms.

Combined reported execution time was approximately
500 milliseconds.

After execution:

- Queue depth: 0.
- Peak depth: 5.
- Last error: None.
- All five poll calls returned True.

The queue preserved the submitted command sequence and
drained successfully.

### Architectural Significance

**The Dumb Queue gives us a place to absorb commands
arriving faster than the network can process them.**

The queue separates command acceptance from command
execution.

This allows short bursts of incoming actions to be
accepted without attempting simultaneous outbound
network operations.

The approach also provides a foundation for future
physical encoders and buttons, which may generate
events faster than individual HTTP transactions finish.

The queue does not make the network faster. It provides
an orderly place for commands to wait.

### Remaining Limitations

This milestone does not establish:

- Sustained high-rate input performance.
- Responsiveness during prolonged network failures.
- Long-duration memory and socket stability.
- Every HTTP failure and timeout scenario.
- Physical encoder or GPIO input behavior.
- Runtime toggle ON/OFF history.
- Custom action execution.
- Actual device-state synchronization.

The browser acknowledgment reports successful queue
acceptance, not confirmed equipment execution.

HTTP 200 indicates a successful HTTP response; it
does not independently prove every device state change.

### Outcome

**Chapter 3 Phase B passed its initial functional and
controlled burst tests.**

The Clonker has moved beyond simulated action logging.

It now accepts browser commands, resolves configured
actions, queues them, sends real HTTP requests, and
receives successful responses from home theater equipment.

The five-command burst confirmed orderly queue
execution under a controlled backlog.

The Dumb Queue has learned to take orders.

The network transport has learned to deliver them.

And somewhere in the Sunroom, a Denon receiver has
discovered that a tiny Raspberry Pi is giving it
instructions.

**CLONK! ⚡🔩**

---

# Milestone 9 — The Clonker Learns to Forget What a TV Is

**Date:** October 22, 2026  
**Status:** PASS — Chapter 4, Phase 1 complete

### Goal

Replace the built-in device-category identifiers with generic, stable device-slot identifiers.

Prepare the configuration architecture for future user-defined devices without changing the fundamental-action model or rewriting the Dumb Queue.

### Implementation

The active JSON schema advanced from version 2 to version 3.

Built-in device identifiers changed:

| Previous ID | New ID | Browser label |
|---|---|---|
| `tv` | `device-1` | TV |
| `avr` | `device-2` | AVR |
| `streaming` | `device-3` | Streaming |

The browser retained familiar labels while using generic IDs internally.

Updated components included:

- JSON configuration validator.
- Operational configuration file.
- Readable configuration sample.
- Browser configuration editor.
- Browser schema-version checks.

The configuration engine retained its historical `device_config_v2.py` filename for import stability.

The Dumb Queue and outbound HTTP transport required no redesign.

### Test evidence

Regression testing confirmed:

- Successful JSON v3 startup.
- Correct room and endpoint loading.
- Browser configuration rendering.
- Correct TV, AVR, and Streaming labels.
- Denon volume-up execution.
- Roku Back and Home execution.
- Successful configuration saves.
- Persistence after Pico restart.
- Backup rotation.
- Stale-tab revision rejection.
- Successful save after refreshing a stale tab.

The refactor preserved the operational fundamental-action pipeline.

### Bugs and corrections

Two browser references to configuration version 2 were identified and corrected during integration.

A subsequent startup diagnostic cleanup accidentally removed the local `settings` assignment in `main.py`.

The Pico reported:

```text
NameError: name 'settings' isn't defined
```

Restoring:

```python
settings = device_config.load()
```

resolved the startup failure.

The correction was tested and pushed.

This was a useful reminder that even a comment-oriented cleanup can introduce an executable-code regression.

### Documentation consolidation

The configuration and architecture references were subsequently updated to describe the active JSON v3 implementation.

The configuration reference now separates current schema rules from historical JSON v2 development.

The architecture reference documents the planned custom-device and compound-action extensions while preserving the existing execution boundaries.

No firmware behavior changes were required for this documentation work.

### Remaining limitations

This milestone did not implement:

- Custom device definitions.
- Custom action execution.
- Compound command sequences.
- Runtime toggle direction history.
- Physical control integration.
- Additional equipment protocols.

The active validator still requires `custom_actions` to be empty and does not accept a `custom_devices` collection.

### Outcome

**Chapter 4, Phase 1 passed.**

The Clonker now identifies its built-in destinations without insisting that they be a television, receiver, or streaming device.

Its browser can still call them TV, AVR, and Streaming.

Its firmware no longer has to believe those labels.

The Dumb Queue remains blissfully indifferent.

**The Clonker has learned an important lesson: a device is a destination, not a personality.**

**CLONK! ⚡🔩**

---

# Maintaining This Journal

Future milestones should be appended using a consistent structure.

```markdown
---

# Milestone N — Descriptive Title

**Date:** YYYY-MM-DD
**Status:** PASS / PARTIAL / FAILED / IMPLEMENTED

### Goal

What we intended to accomplish.

### Implementation

What changed in code, configuration, or hardware.

### Test evidence

What was actually tested and observed.

### Bugs and corrections

Unexpected behavior and how it was resolved.

### Remaining limitations

What this milestone did not prove.

### Outcome

The significance of the completed work.
```

Not every milestone needs an enormous report.

A small, well-tested improvement may deserve only a few paragraphs.

A major architectural change or difficult bug may deserve several pages.

The guiding rules:

- Record meaningful changes.
- Preserve actual observations.
- Preserve significant failures and corrections.
- Include exact error messages when useful.
- Avoid repeating entire specifications.
- Link to the current technical documentation.
- Distinguish completed work from plans.
- Do not retroactively rewrite earlier test outcomes.

Git history preserves the exact evolution of source files.

This journal preserves the engineering reasoning and test evidence that commit messages alone may not capture.

---

# Where the Story Stands

**As of October 21, 2026 — Chapter 3 Complete**

The Clonker 10000 has crossed an important threshold.

What began as a collection of beautiful metallic knobs, ambitious ideas, and a mildly unreasonable desire to reinvent the remote control is now a functioning network control system.

The Raspberry Pi Pico 2 W is running CircuitPython 10.3.1 with:

- A validated JSON v2 configuration system.
- Browser-based configuration editing and persistence.
- Revision checking, backup rotation, and recovery safeguards.
- A browser Test Remote supporting fourteen fundamental actions.
- A cooperative action scheduler.
- The magnificent, deliberately uncomplicated Dumb Queue™.
- Working outbound HTTP communication with Denon and Roku equipment.
- Real-device command execution confirmed through HTTP responses and observed equipment behavior.

Chapter 3 began with a logging-only action dispatcher.

It ended with the Clonker successfully commanding real home theater equipment.

Along the way, we investigated CircuitPython socket behavior, measured connection timing, implemented bounded HTTP operations, and demonstrated that five rapidly queued commands could execute sequentially without errors.

### The Dumb Queue Has Earned Its Name

One of the most important architectural decisions was also one of the simplest.

**The Dumb Queue gives us a place to absorb commands arriving faster than the network can process them.**

It doesn't attempt to understand the home theater.

It doesn't predict what the user wants.

It doesn't maintain an elaborate model of equipment state.

It accepts commands, remembers their order, and executes them when their turn arrives.

Sometimes the smartest component is the one that knows exactly how little it needs to know.

### What Comes Next

The software foundation is now capable of controlling equipment, but the Clonker is still far from its ultimate physical form.

Important work remains:

- Runtime ON/OFF toggle command history.
- Additional network failure and recovery testing.
- Physical rotary encoder integration.
- Tactile buttons and room selection.
- Hardware CONFIG/RUN switching.
- Custom actions and command sequences.
- OLED status feedback.
- Audible CLONK effects.
- Power management and enclosure construction.

The next chapter can build upon an actual working control pipeline rather than a collection of simulated actions.

The Clonker still has no magnificent enclosure.

Its beautiful knobs are still waiting for their moment.

And the marketing department remains permanently disbanded.

But something fundamental has changed.

**The Clonker no longer merely knows what it wants to do.**

**It can actually do it.**

---

**THE CLONKER 10000**

*Less sleek. More CLONK.*

**CLONK! ⚡🔩**
