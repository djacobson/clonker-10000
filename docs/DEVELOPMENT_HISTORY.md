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
| Oct 27, 2026 | 9. Runtime power/mute toggles | Denon/Roku ON/OFF, HDMI-CEC, configuration reset, and independent room histories verified |
| Oct 27, 2026 | 10. Chapter 4 firmware closeout | Toggle negative tests, cooperative scheduler interleaving, and Test Remote regression passed; no code changes required |
| Oct 28, 2026 | 11. Chapter 5 GPIO scheduler foundation | Optional physical-control initialization and polling integrated; both flag settings Pico-tested with successful Roku HTTP execution |
| Oct 28, 2026 | 12. Chapter 5 HTTP scheduler pacing | CONFIG browser responsiveness restored with 1 ms HTTP polling |
| Oct 29, 2026 | 13. Chapter 5 physical switch and button verification | GP17 SERVICE/DEVICE, GP18 CONFIG/RUN, and GP2 debounced events physically verified |
| Oct 31, 2026 | 14. Chapter 5 room selector verification and closeout | Three-position rotary selector mapped, wired to GP3/GP4/GP5, and standalone GPIO-tested; Chapter 6 integration pending |
| Nov 2, 2026 | 15. Chapter 6 physical room selection and Power Toggle | Integrated GP3/GP4/GP5 room selection, safe Room 3 no-op, and GP2 Power ON/OFF verified on actual equipment in Den and Sunroom |
| Nov 2, 2026 | 16. Room selector GPIO reassignment | Moved selector from GP3/GP4/GP5 to GP3/GP6/GP7; all three positions retested successfully; GP4/GP5 reserved for STEMMA QT/I²C |
| Nov 3, 2026 | 17. The Volume Knob Finds Its Voice | Bourns encoder on GP8/GP9 integrated; real Sunroom Denon volume changes verified using persistent TCP and the shared Dumb Queue™ |

**Additional Chapter 4 development records:** Generic-device refactor and the Great Room 3 Eviction are preserved in their original chronological positions between Milestones 8 and 9.

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

# Chapter 4 Development Record — The Clonker Learns to Forget What a TV Is

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

# Chapter 4 Development Record — The Great Room 3 Eviction

**Date:** October 22, 2026  
**Status:** PASS — Chapter 4, Phase 2 complete

### Goal

Make room configuration optional while preserving the existing room identities, fundamental actions, and browser configuration safeguards.

Remove the unused third room from the operational configuration without removing support for it from the firmware.

### Implementation

JSON v3 remains the active schema.

The firmware continues to recognize three stable room IDs:

- `room-1`
- `room-2`
- `room-3`

The configuration validator now accepts any nonempty subset of these IDs.

Named constants define the minimum and maximum room counts.

The operational configuration now contains only:

- `room-1` — Den
- `room-2` — Sunroom

The browser configuration editor renders only rooms present in the active configuration.

The existing fourteen fundamental actions remain required within each configured room.

No dynamic Add Room or Delete Room controls were introduced.

### Startup correction

Initial testing exposed a remaining assumption in `main.py`.

The configuration validator correctly loaded two rooms, but startup diagnostics attempted to access `room-3` unconditionally.

This produced:

```text
KeyError: room-3
```

The diagnostic loop was corrected to skip absent rooms.

The startup message was also updated to report the actual configured-room count instead of assuming three rooms.

The corrected firmware started successfully.

### Regression testing

Live Pico testing confirmed:

- Successful JSON v3 startup with two rooms.
- Correct Den and Sunroom endpoint loading.
- No Room 3 displayed in the browser editor.
- HTTP management service startup.
- Successful Sunroom Denon volume-up command with HTTP 200.
- Successful browser configuration save.
- Configuration persistence across Pico restart.
- Configuration-change queue clearing.
- Successful stale-tab revision rejection after another tab saved a newer configuration.

The Sunroom name was restored after the test.

### Architectural outcome

The change required no redesign of:

- The fourteen fundamental actions.
- The Dumb Queue.
- Outbound HTTP transport.
- Configuration revision protection.
- Existing backup and persistence mechanisms.

Room identities remain stable, but unused rooms no longer occupy operational JSON space.

This establishes a foundation for future dynamic room editing without introducing that feature prematurely.

### Remaining work

Custom devices and compound actions remain the next major development objectives.

Additional optional-room validation edge cases and backup-rotation regression testing may be performed as needed.

The Clonker can still support Room 3.

It simply no longer insists that Room 3 pay rent.

**Chapter 4, Phase 2 passed.**

**The Great Room 3 Eviction is complete.**

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

# Historical Snapshot — Where the Story Stood on October 22, 2026

**As of October 22, 2026 — Chapter 4, Phase 2 Complete**

The Clonker 10000 has crossed two important thresholds.

First, it learned to communicate with real home theater equipment.

Then, it learned that a device doesn't need to be called a television, receiver, or streaming player to receive a command.

What began as a collection of beautiful metallic knobs, ambitious ideas, and a mildly unreasonable desire to reinvent the remote control is now a functioning, configurable network control system.

The Raspberry Pi Pico 2 W is running CircuitPython 10.3.1 with:

- A validated JSON v3 configuration system.
- One to three configured rooms, with three generic built-in device slots per room.
- Fourteen configurable fundamental actions per room.
- Browser-based configuration editing and persistence.
- Revision checking, backup rotation, and recovery safeguards.
- Stale-browser-tab conflict protection.
- A browser Test Remote.
- A cooperative action scheduler.
- The magnificent, deliberately uncomplicated Dumb Queue™.
- Working outbound HTTP communication with Denon and Roku equipment.
- Real-device command execution confirmed through HTTP responses and observed equipment behavior.

Chapter 3 established the complete browser-to-equipment command pipeline.

Chapter 4 began by separating device identity from device category.

The original configuration identifiers:

```text
tv
avr
streaming
```

have become:

```text
device-1
device-2
device-3
```

The browser retains the familiar TV, AVR, and Streaming labels.

The firmware no longer depends on those labels to understand where commands belong.

This refactor was completed without redesigning the queue or outbound transport.

That is exactly the kind of architectural stability we want.

## The Dumb Queue Has Earned Its Name

One of the most important architectural decisions was also one of the simplest.

**The Dumb Queue gives us a place to absorb commands arriving faster than the network can process them.**

It doesn't attempt to understand the home theater.

It doesn't predict what the user wants.

It doesn't maintain an elaborate model of equipment state.

It accepts commands, remembers their order, and executes them when eligible.

Future-dated work does not prevent unrelated immediate commands from executing.

Network failures cancel pending work without permanently disabling the remote.

And future compound actions will use this same queue rather than creating an entirely separate execution system.

Sometimes the smartest component is the one that knows exactly how little it needs to know.

## What Comes Next

The next development phase introduces **user-defined custom devices**.

The objective is to extend each room beyond its three built-in device slots while preserving the existing fundamental-action model.

After that, custom and compound actions will allow named sequences of HTTP commands.

The agreed architecture uses:

- Stable custom-device identities.
- Ordered command steps.
- Post-completion waits.
- Lightweight predecessor dependencies.
- Independent command interleaving.
- All-or-nothing queue admission.
- Existing queue-wide failure cancellation.

The initial implementation will deliberately avoid loops, nested macros, conditional scripting, and unnecessary execution frameworks.

Other important work remains:

- Runtime ON/OFF toggle command history.
- Additional network failure and recovery testing.
- Physical rotary encoder integration.
- Tactile buttons and room selection.
- Hardware CONFIG/RUN switching.
- OLED status feedback.
- Audible CLONK effects.
- Power management and enclosure construction.
- Future Apple TV compatibility.

The Clonker still has no magnificent enclosure.

Its beautiful knobs are still waiting for their moment.

The guarded SYSTEM MASTER switch has yet to receive its ceremonial assignment.

And the marketing department remains permanently disbanded.

But something fundamental has changed.

**The Clonker no longer merely knows what it wants to do.**

**It can actually do it.**

And now we're teaching it how to do more without making it unnecessarily complicated.

---

# Milestone 9 — Runtime Power/Mute Toggles Come Alive

**Date:** October 27, 2026  
**Status:** PASS — implemented and hardware-tested

## Goal

Complete runtime ON/OFF direction selection for the existing `power-toggle` and `mute-toggle` fundamental actions without introducing equipment-state polling or a separate execution framework.

## Implementation

The shared dispatcher in `firmware/clonker/actions.py` now maintains a small, volatile direction-history dictionary keyed by room ID and action ID.

- Unknown history initially selects ON.
- Direction is selected when a queued action executes.
- Successful HTTP execution advances ON → OFF or OFF → ON.
- Failed requests, missing endpoints, and blank selected paths do not advance history.
- Different rooms and toggle actions maintain independent histories.
- A firmware restart resets volatile history.
- A successful changed configuration save clears pending queue work and resets all toggle histories.
- An unchanged configuration save preserves history.

The existing HTTP transport, configuration schema, and Dumb Queue™ remain the execution foundation.

This is deliberately **command history**, not authoritative knowledge of equipment state.

## Hardware verification

The browser Test Remote exercised real equipment through the Pico.

| Test | Result |
|---|---|
| Sunroom Denon X1800H mute ON (`MUON`) | PASS — HTTP 200 |
| Sunroom Denon X1800H mute OFF (`MUOFF`) | PASS — HTTP 200 |
| Repeated mute ON/OFF alternation | PASS |
| Sunroom Roku Home command | PASS — HTTP 200 |
| Sunroom Roku PowerOff command | PASS — HTTP 200 |
| LG G1 / Denon X1800H HDMI-CEC power chain | PASS — observed power ON/OFF |
| Changed configuration save resets histories | PASS |
| First mute after changed save selects ON | PASS |
| Den room history independent of Sunroom | PASS — HTTP 200 |

Observed HTTP transaction times were approximately 100–125 ms for Denon mute and 145–188 ms for Roku power commands.

## Verification boundaries

The following remain untested as deliberate negative scenarios:

- Failed HTTP requests preserving toggle history.
- Blank ON/OFF command paths.
- Missing destination endpoints.
- High-rate physical input during toggle execution.

Successful HTTP execution does not prove the resulting equipment state, especially when external remotes or HDMI-CEC participate.

## Architectural significance

Runtime toggles required no new network protocol, no equipment-state database, and no second command scheduler.

The existing dispatcher now handles ordinary fundamental actions, custom multi-step actions, and power/mute direction selection through the same execution path.

Physical buttons, rotary encoders, and the guarded SYSTEM MASTER remain future hardware work.

**The Clonker can now remember which command direction comes next, without pretending it knows whether the television is actually on.**

---

# Milestone 10 — Chapter 4 Firmware Closeout

**Date:** October 27, 2026  
**Status:** PASS — negative tests, scheduler interleaving, and browser regression verified

## Goal

Complete the remaining focused Chapter 4 firmware tests before beginning physical-control development in Chapter 5.

The existing Pico 2 W / CircuitPython 10.3.1 firmware was tested without introducing new features or changing the execution architecture.

## Toggle failure and no-op verification

| Test | Observed result |
|---|---|
| Unreachable Sunroom Denon endpoint | HTTP connection failure reported as `OSError(119,)` |
| Repeated request after failure | Selected `MUON` again; direction history preserved |
| Failure recovery | Dumb Queue accepted the subsequent request |
| Blank toggle ON path | Two successive presses produced `NO-OP` |
| Missing device endpoint | Two successive presses produced `NO-OP` |
| Restore original Denon endpoint and paths | `MUON` and `MUOFF` both returned HTTP 200 |
| Restored direction alternation | ON → OFF → ON confirmed |

The unreachable endpoint was `192.168.50.250:8080`. Both failed connection attempts completed in approximately 500 ms.

The tests demonstrated that unsuccessful requests and unconfigured fundamental toggle actions do not advance volatile command-direction history.

After restoring the Sunroom Denon endpoint to `192.168.50.40:8080`, successful mute ON/OFF requests completed in approximately 109 ms and 106 ms.

## Cooperative scheduler verification

The existing Sunroom **Movie** custom action was used:

1. Roku Home via HTTP POST.
2. Cooperative wait of 3000 ms.
3. Denon Quick Select 1 via HTTP GET.

During the wait, an independent Sunroom Volume Up action was requested.

Observed execution order:

| Event | Approximate REPL timestamp | Result |
|---|---|---|
| Roku Home completed | +6853.0 s | HTTP 200 |
| Independent Volume Up completed | +6854.8 s | HTTP 200 |
| Denon Quick Select 1 completed | +6856.1 s | HTTP 200 |
| Custom action completed | +6856.1 s | PASS |

Volume Up executed during the custom action's wait, approximately 1.3 seconds before Quick Select 1.

This verified that a waiting custom action does not prevent the shared dispatcher from executing another eligible fundamental action.

## Browser Test Remote regression

The Sunroom Movie custom action remained selected and its Run button remained enabled after execution.

Switching from Sunroom to Den and back also left Movie selected and Run enabled.

Because Movie was the first available custom action, these observations do not establish selection preservation among multiple custom actions. No demonstrated defect justified a JavaScript change.

## Chapter 4 outcome

**No firmware changes were required during these closeout tests.**

The verified baseline includes:

- Runtime fundamental HTTP actions.
- Volatile per-room/action power and mute direction history.
- Successful-command-only toggle advancement.
- Failed-request recovery and unconfigured toggle no-ops.
- Executable multi-step custom actions.
- Cooperative queue interleaving during custom waits.
- Working browser Test Remote behavior for the tested configuration.

## Remaining boundaries

The following are not claimed as fully verified:

- Sustained queue pressure and long-duration Wi-Fi outages.
- Malformed device responses across all failure conditions.
- Extended memory and uptime stability.
- High-rate physical encoder and button events.
- Browser selection preservation with multiple custom actions.
- Physical GPIO integration and hardware power management.

These remain future engineering or regression tasks, not Chapter 4 firmware blockers.

**Chapter 4 closes with a working, tested firmware foundation. The next challenge is to give the monster physical controls.**

---

# Milestone 11 — Chapter 5: The Monster Gets Its Nervous System

**Date:** October 28, 2026  
**Status:** PASS — empty physical GPIO subsystem integrated and Pico-tested.

Chapter 5 began with the physical-control framework rather than immediately connecting switches.

### Firmware changes

- Added `firmware/clonker/controls/physical.py` with one-time initialization and an empty polling interface.
- Added `PHYSICAL_CONTROLS_ENABLED` in `firmware/clonker/main.py`.
- Integrated physical initialization into application startup.
- Added physical polling ahead of Dumb Queue execution in the cooperative scheduler.
- Preserved browser CONFIG mode, simulated CONFIG/RUN selection, and outbound HTTP independently of the physical-control flag.

The initial physical polling interval is 10 ms, subject to blocking network operations.

The subsystem does not yet assign GPIO pins, decode encoders, debounce switches, or dispatch physical actions.

### Pico verification

**Platform:** Raspberry Pi Pico 2 W / CircuitPython 10.3.1.

| Test | Observed result |
|---|---|
| `PHYSICAL_CONTROLS_ENABLED = False` | Brain-only startup confirmed |
| CONFIG listener, controls disabled | Operational |
| Sunroom Roku Home, controls disabled | HTTP 200 |
| `PHYSICAL_CONTROLS_ENABLED = True` | Startup successful; no GPIO initialization errors |
| CONFIG listener, controls enabled | Operational |
| Sunroom Roku Home, controls enabled | HTTP 200 |
| Unexpected physical actions | None observed |

Both configurations were deployed to the Pico and tested through the browser Test Remote.

The result establishes the scheduler integration and preserves the working network-action baseline. Actual GPIO input behavior remains untested.

### Next boundary

Physical controls will initialize once at startup. Hot-plug detection and automatic reinitialization are not requirements; changing hardware connections may require an application restart.

Future work includes button events, rotary encoder decoding, debounce handling, room selection, physical CONFIG/RUN switching, and resilience to individual input failures.

**The Monster has a nervous system. Actual nerve endings are still pending.**

---

# Milestone 12 — Chapter 5: HTTP Pacing and Browser Responsiveness

**Date:** October 28, 2026  
**Status:** PASS — scheduler adjustment tested in Chrome and Safari

### Problem

During physical-control development, the CONFIG interface became intermittently slow or incomplete. Windows Chrome exhibited delayed page loading, unfinished requests, `ERR_EMPTY_RESPONSE`, and HTTP response timeouts.

The new GPIO subsystem was initially suspected. Disabling physical controls, however, did not eliminate the symptoms.

### Investigation

The inbound HTTP server advances a bounded amount of work per `web.poll()` call. A large response may require many individual send operations.

With a 512-byte transmission chunk, a roughly 40 KB response requires at least 80 successful send operations. At a 10 ms HTTP polling interval, those operations alone could consume approximately 800 ms of scheduler time, excluding network delays and competing work.

Diagnostics confirmed that some responses began transmitting but timed out before completion.

### Correction

The management HTTP polling interval in `firmware/clonker/main.py` changed from:

```python
WEB_POLL_INTERVAL = 0.01
```

to:

```python
WEB_POLL_INTERVAL = 0.001
```

Physical-input and action-queue polling remained at 10 ms.

### Verification

Repeated CONFIG page refreshes completed promptly in Windows Chrome and iPad Safari. Physical controls were subsequently re-enabled, and GP2 press/release logging continued while the browser interface remained responsive.

The final browser test also passed with inbound HTTP diagnostics disabled.

### Engineering conclusion

The original 10 ms HTTP polling interval was a significant contributor to the observed delays. The 1 ms interval is the tested working baseline, not proof of optimal scheduler design.

The exact reason the issue became prominent during Chapter 5 remains unproven.

**The Monster wasn't necessarily thinking too slowly. We simply weren't letting it answer the door often enough.**

---

# Milestone 13 — Chapter 5: Physical Switches and First Button Events

**Date:** October 29, 2026  
**Status:** PASS — GP17, GP18, and GP2 physically verified; equipment-action dispatch pending

### Goal

Move beyond the empty GPIO framework and demonstrate actual physical inputs without disturbing the working configuration, browser, queue, or HTTP subsystems.

### GP17 — SERVICE / DEVICE

A maintained physical switch was connected to GP17 using the internal pull-up.

| Switch condition | Observed boot mode |
|---|---|
| OFF / open / HIGH | SERVICE (USB) |
| ON / grounded / LOW | DEVICE |

The boot diagnostics confirmed:

```text
CLONKER BOOT: SERVICE (USB) mode (switch OFF)
CLONKER BOOT: DEVICE mode (switch ON)
```

SERVICE allows the USB host to own filesystem writes. DEVICE allows firmware-side writes, including browser configuration persistence.

The selection occurs during `boot.py`; changing it requires a complete power cycle.

### GP18 — CONFIG / RUN

The guarded maintained CONFIG/RUN switch was physically connected to GP18, also using an internal pull-up.

| Switch condition | Application mode | Management listener |
|---|---|---|
| OFF / open / HIGH | RUN | Stopped |
| ON / grounded / LOW | CONFIG | Enabled |

The firmware reported the application-mode source as `PHYSICAL` and logged CONFIG/RUN transitions.

Unlike GP17 filesystem ownership, GP18 application-mode switching operates live without rebooting.

The action queue remains available in both application modes.

### GP2 — First momentary button

The momentary power-toggle button was connected to GP2.

The reusable button-input subsystem initialized the control and produced debounced press/release events in serial diagnostics.

This established physical input detection and event reporting through the cooperative scheduler.

**Important boundary:** The GP2 button did not yet send a power command or invoke `actions.dispatch()`. The physical button name identifies its intended function, not a completed equipment-control integration.

### Firmware responsibilities

The Chapter 5 physical-input implementation now uses:

- `controls/pins.py` for central GPIO assignments.
- `controls/buttons.py` for reusable button handling and debounce.
- `controls/physical.py` for input initialization, polling, and event reporting.
- `controls/switches.py` for CONFIG/RUN selection.
- `main.py` for cooperative scheduling and management-listener lifecycle.
- `boot.py` for SERVICE/DEVICE filesystem ownership.

Unassigned optional buttons are skipped. Individual button initialization failures are logged rather than treated as reasons to abandon the entire application.

### Verified versus pending

**Verified:**

- GP17 boot-time filesystem mode selection.
- GP18 live application-mode selection.
- Management listener responding to CONFIG/RUN state.
- GP2 debounced button press/release reporting.
- Continued operation of the established browser/network action pipeline.

**Pending:**

- Physical room selector integration.
- Mapping GP2 events to room-aware `power-toggle` dispatch.
- Navigation, Home, Back, and other physical buttons.
- Volume and custom-action encoder integration.
- Measurements of input capture during blocking outbound HTTP.
- OLED, audio feedback, battery, and enclosure integration.

### Engineering conclusion

Chapter 5 now has physically verified mode controls and its first working button-input events. These are meaningful hardware milestones, but they do not yet constitute a fully operational physical remote.

**The Monster has nerve endings. Next, we teach them which muscles to move.**

---

# Milestone 14 — Chapter 5 Room Selector Hardware Verification

**Date:** October 31, 2026  
**Status:** PASS — physical hardware and standalone GPIO test

### Goal

Characterize and electrically verify a three-position rotary room selector before integrating it into the Clonker's running application.

### Hardware discovery

The selector arrived without a usable terminal diagram. Its contacts were identified through multimeter continuity testing.

One pole was mapped successfully:

- Common terminal: 9 o'clock, viewed from the rear.
- LEFT position: common connected to 6 o'clock.
- MIDDLE position: common connected to 5 o'clock.
- RIGHT position: common connected to 4 o'clock.

The common terminal was connected to ground through the prototype WAGO distribution.

Three position contacts were wired to the Pico:

| Position | Wire | GPIO |
|---|---|---|
| LEFT | Yellow | GP3 |
| MIDDLE | Green | GP4 |
| RIGHT | Blue | GP5 |

The assignments were added to `firmware/clonker/controls/pins.py`.

### Verification

A standalone CircuitPython test monitored all three GPIO inputs using internal pull-up resistors.

The test was launched through the REPL:

```python
exec(open("/tests/test_room_selector.py").read())
```

Rotating the selector produced the expected LEFT, MIDDLE, and RIGHT readings, including reverse transitions.

**Result: PASS.**

The selector's electrical behavior and Pico GPIO connections were successfully verified.

### Chapter 5 closeout

Chapter 5 established:

- A working physical GPIO initialization and polling foundation.
- A verified GP2 momentary power-button input.
- A verified GP17 SERVICE/DEVICE boot-mode switch.
- A verified GP18 CONFIG/RUN application-mode switch.
- A verified three-position rotary room selector using GP3, GP4, and GP5.
- Continued browser responsiveness alongside physical-input handling.

The room selector has not yet been integrated into the running Clonker application.

The next chapter will begin with permanent selector-terminal soldering and insulation, followed by application-level room-selection integration.

Detailed wiring and terminal mapping are maintained in [Hardware Design](HARDWARE_DESIGN.md).

### Engineering conclusion

The Monster now has working physical switches, a button, and a three-position sense of direction.

It still needs to learn what to do with that information.

**Chapter 5 complete. Chapter 6 awaits.**

---

# Milestone 15 — Chapter 6 Physical Room Selection and Power Toggle

**Date:** November 2, 2026  
**Status:** PASS — integrated GPIO, shared action dispatch, and actual equipment operation

### Goal

Connect the verified three-position physical room selector and GP2 momentary Power Toggle to Clonker's existing action dispatcher, without introducing device-specific commands into the GPIO subsystem.

Prove that physical input can select a room, enqueue a generic action, and operate real home-theater equipment.

### Room selector integration

A new `firmware/clonker/controls/selectors.py` module was integrated into the application.

The selector uses three active-low inputs with internal pull-ups:

| Position | GPIO | Wire | Room |
|---|---|---|---|
| LEFT | GP3 | Yellow | `room-1` — Den |
| MIDDLE | GP4 | Green | `room-2` — Sunroom |
| RIGHT | GP5 | Blue | `room-3` — Reserved |

The selector's common terminal connects to the WAGO ground distribution.

A valid reading requires exactly one grounded input.

Zero or multiple grounded inputs are treated as transitional or invalid, preserving the last valid selection.

A changed position must remain stable for 50 ms before acceptance.

The module provides initialization, polling, current room selection, and cleanup without performing any network operations.

### Runtime room-selection verification

The integrated application initialized the selector and reported room changes through PuTTY.

Representative diagnostics:

```text
Room selector initialized; selected = room-1
ROOM SELECTED: room-2
ROOM SELECTED: room-3
ROOM SELECTED: room-1
```

All three positions were recognized.

**Result: PASS — physical room selection operational in the running application.**

### Shared physical-action dispatch

`controls/physical.py` was extended to translate debounced physical button presses into generic action IDs.

The GP2 button maps to `power-toggle`.

The shared helper `dispatch_selected(action_id)`:

1. Reads the current physical room selection.
2. Verifies that the room exists in the active configuration.
3. Logs a safe no-op when the room is unavailable.
4. Invokes `actions.dispatch(room_id, action_id)` for configured rooms.
5. Allows the existing Dumb Queue™ and HTTP transport to execute the action.

No Roku or Denon command paths were added to GPIO modules.

The physical controls and browser Test Remote now use the same dispatcher.

### Reserved Room 3 safety test

The physical selector supports a third position even though the current configuration contains only Den and Sunroom.

With Room 3 selected, pressing GP2 produced:

```text
PHYSICAL NO-OP: room-3 / power-toggle (room unavailable)
```

No equipment command was queued or transmitted.

The system did not fall back to another room.

**Result: PASS — unconfigured physical room selection safely ignored.**

### Actual equipment verification

The GP2 Power Toggle was tested with the selector positioned for each configured room.

| Selected room | Physical action | Result |
|---|---|---|
| Room 2 — Sunroom | Power ON | PASS |
| Room 2 — Sunroom | Power OFF | PASS |
| Room 1 — Den | Power ON | PASS |
| Room 1 — Den | Power OFF | PASS |

These were actual equipment observations, not merely HTTP 200 responses.

PuTTY diagnostics confirmed physical button events, action queue admission, execution, and toggle-direction behavior.

Independent volatile power-toggle histories were observed for both rooms.

As established in earlier milestones, these histories represent successfully transmitted command directions, not authoritative equipment-state feedback.

### Architecture verified

```text
Physical room selector
         |
         v
  selectors.py
         |
         v
GP2 Power Toggle press
         |
         v
    buttons.py
         |
         v
    physical.py
         |
         v
dispatch_selected()
         |
         v
 actions.dispatch()
         |
         v
    Dumb Queue
         |
         v
 Outbound HTTP
         |
         v
 Denon / Roku / CEC
         |
         v
 Actual equipment
```

This completed the first verified end-to-end physical hardware-to-equipment command path.

### Hardware and encoder direction

The prototype uses the Pico Cowbell Terminal board for screw-terminal GPIO connections and WAGO connectors for common-ground distribution.

The room selector and Power Toggle are working, but final enclosure wiring, strain relief, and mounting remain ongoing tasks.

The volume and custom-action controls will use two **Bourns PEC11R-4215F-S0024** rotary encoders.

The earlier Grayhill volume-encoder plan was superseded.

The custom-action Bourns encoder has undergone standalone electrical and mechanical testing, but neither encoder is yet integrated into the production physical-control scheduler.

### Remaining technical question

Outbound HTTP remains synchronous and blocking.

The physical scheduler targets approximately 10 ms polling, but this is not a guaranteed maximum interval.

The tested momentary button and maintained selector operate successfully.

Fast quadrature encoder movement may generate transitions while the cooperative loop is blocked by HTTP.

Encoder capture reliability must therefore be measured before selecting a more elaborate polling, buffering, or hardware-assisted strategy.

### Engineering conclusion

Chapter 6 established:

- Integrated physical room selection.
- Debounced, valid-only selector state.
- Room-aware physical action dispatch.
- Safe no-op behavior for reserved Room 3.
- Actual Power ON/OFF operation in both configured rooms.
- Independent per-room power-toggle command histories.
- Reuse of the existing dispatcher, Dumb Queue™, and HTTP transport.

**The Clonker no longer merely senses its physical controls. It uses them to operate real equipment.**

The next development objective is integrating the two Bourns rotary encoders, beginning with reliable movement detection and volume control.

**The Monster has learned which room it's in. And how to turn the lights on. Well, the television, anyway.**

---

# Milestone 16 — Room Selector GPIO Reassignment

**Date:** November 2, 2026  
**Status:** PASS — hardware retested

### Goal

Preserve the Pico Cowbell Terminal board's STEMMA QT/I²C connection for future peripherals, particularly the planned OLED status display, without sacrificing the operational three-position room selector.

### Implementation

The original room-selector assignments were GP3, GP4, and GP5.

The green and blue selector wires were relocated to GP6 and GP7 on the Cowbell screw terminals. The yellow wire remained on GP3, and the black common remained connected to the WAGO ground bus.

The resulting assignments are:

| Position | Wire | GPIO | Room |
|---|---|---|---|
| LEFT | Yellow | GP3 | `room-1` — Den |
| MIDDLE | Green | GP6 | `room-2` — Sunroom |
| RIGHT | Blue | GP7 | `room-3` — Reserved |

`firmware/clonker/controls/pins.py` was updated:

```python
ROOM_SELECTOR_A_PIN = 3
ROOM_SELECTOR_B_PIN = 6
ROOM_SELECTOR_C_PIN = 7
```

No changes were required in `selectors.py`, `physical.py`, or the action dispatcher.

GP4 and GP5 are now reserved for the Cowbell's STEMMA QT/I²C connector. The OLED remains a planned peripheral, not an installed device.

### Verification

After reconnecting the Pico, the room selector was tested with its new GPIO assignments.

**Result: PASS — all three positions operated correctly.**

The reassignment preserved the existing room-selection behavior.

### Engineering conclusion

The working room selector now uses GP3/GP6/GP7, while GP4/GP5 remain available for future I²C peripherals.

This was a small hardware change made early enough to avoid more disruptive rewiring during enclosure assembly.

**Two wires moved. Three rooms still recognized. The Monster barely noticed.**

---

# Milestone 17 — The Volume Knob Finds Its Voice

**Date:** November 3, 2026  
**Chapter:** 6 — Physical controls  
**Status:** PASS — physical volume encoder and real Denon volume control exercised

### Goal

Integrate the first rotary encoder into the production physical-control scheduler and verify that turning a physical knob produces room-aware volume commands on real equipment, without creating a second command execution system.

### Implementation

The volume control uses a **Bourns PEC11R-4215F-S0024** quadrature encoder, replacing the earlier Grayhill volume-encoder plan. Its A/B signals are assigned to **GP8/GP9** in `firmware/clonker/controls/pins.py`.

The encoder is initialized and polled through the existing `clonker/controls/physical.py` integration. Its decoded movement is translated into the configured `volume-up` and `volume-down` fundamental actions for the room selected by the physical three-position selector. The path continues through the existing action dispatcher and shared **Dumb Queue™**, rather than bypassing application action handling.

The existing room selector remains on **GP3/GP6/GP7**, with GP4/GP5 reserved for the Cowbell STEMMA QT/I²C connection. GP2 remains the room-aware momentary Power Toggle. The third selector position remains reserved for an unconfigured room and must not silently fall back to Den or Sunroom.

### Denon transport improvement

Repeated HTTP volume requests exposed a practical performance limitation for rotary control. A dedicated Denon adapter now recognizes configured fundamental volume actions using the standard Denon HTTP volume command signatures and sends the corresponding **`MVUP`** / **`MVDOWN`** commands over a persistent **TCP connection on port 23**.

The adapter enforces a **50 ms minimum command interval**. It is selected through the existing device-adapter resolution mechanism; other commands continue to use the established bounded HTTP GET/POST transport. The queue remains the single command-execution path, even when its work is delivered over different transports.

This is **not** a general replacement of Denon HTTP commands with TCP, nor a new standalone volume queue. See [Firmware, Network & Clock](FIRMWARE_NETWORK.md) for current transport selection, scheduling, and failure semantics.

### Verification

The Bourns encoder was bench-tested, integrated, and then exercised against the **Sunroom Denon AVR-X1800H**. Physical rotation produced actual receiver volume changes through the shared action pipeline and Denon TCP adapter.

**Result: PASS — working physical volume knob on real equipment.**

The earlier Chapter 6 Power Toggle and room-selection tests remain valid: both configured rooms responded to physical Power ON/OFF commands, and the unconfigured third room remained a safe no-op.

These results establish an operational physical volume-control path, **not** an exhaustive stress test of rapid quadrature movement, missed edges, network failures, or long-duration operation. A 1 ms cooperative physical poll target is not a guaranteed worst-case input latency; blocking network operations can still delay polling.

### Remaining boundaries

- Test rapid and sustained encoder rotation, including direction reversals, under representative network load.
- Integrate the second Bourns encoder for custom-action selection and press-to-run behavior.
- Integrate remaining navigation, Back, Home, and encoder push-button controls.
- Complete enclosure wiring, strain relief, OLED feedback, audio, and power-management experiments.
- Preserve the distinction between the **GP2 equipment Power Toggle** and any future guarded system ignition/sleep control.

### Engineering conclusion

The Clonker now has two independently useful physical capabilities: it can select a room and toggle its equipment power, and it can turn a real receiver's volume up or down with a real knob. Both use the same application-level action machinery as the browser Test Remote.

**One knob. One queue. Two transports. Still one Monster.**

---

# Milestone 18 — The Monster Learns to Speak Roku

**Date:** November 3, 2026  
**Chapter:** 6 — Physical Controls  
**Status:** PASS — Roku held-volume control, mixed adapters, and physical push-to-mute verified on real equipment

### Goal

Extend the physical volume-control architecture beyond Denon's persistent TCP protocol without hardcoding room identities, introducing a second command queue, or sacrificing the responsiveness of the rotary encoder.

The intended result was a single physical volume control that could operate different equipment through different protocols, based entirely on the configured fundamental actions.

### Device adapter architecture

The device-adapter layer recognizes supported command signatures and selects the appropriate transport.

Three execution paths are now available:

- **Denon TCP:** Recognized Denon fundamental volume commands use persistent TCP port 23 with a 50 ms minimum command interval.
- **Roku held-volume:** Recognized Roku ECP fundamental volume commands use HTTP keydown/keyup with a locally maintained hold.
- **Generic HTTP:** Other configured commands continue through the bounded HTTP GET/POST transport.

Adapter resolution is based on the configured method and path, not room names or fixed device positions.

The existing Dumb Queue™ remains the sole action execution pipeline. Physical controls dispatch fundamental actions without knowing which device protocol will execute them.

The adapter layer owns transport-specific execution and lifecycle coordination.

### Roku held-volume implementation

The new `firmware/clonker/devices/roku.py` module implements time-based volume holds.

The configured fundamental commands are:

| Action | Method | Configured path |
|---|---|---|
| Volume Up | POST | `/keypress/VolumeUp` |
| Volume Down | POST | `/keypress/VolumeDown` |

The adapter recognizes these signatures and substitutes the appropriate Roku ECP keydown/keyup operations.

On the first detent, it sends a keydown request. Additional same-direction detents refresh the hold deadline without additional HTTP requests.

The implemented timing parameters are:

| Parameter | Value |
|---|---|
| Idle release | 250 ms |
| Maximum continuous hold | 2 seconds |
| Failed-release retry interval | 500 ms |

A direction reversal releases the previous key before starting the opposite direction.

A failed release retains local held-key state and blocks new keydowns until release succeeds. Retry attempts are paced rather than repeated continuously.

A held key can also be released during queue cancellation, command failure, configuration replacement, or application shutdown.

Operation-specific HTTP diagnostics now identify the Roku command path, endpoint, and underlying exception representation.

The design does not automatically retry uncertain keydown requests.

### Refactoring and regression

The adapter execution boundary was consolidated in `device_adapters.py`.

The Dumb Queue now delegates device execution to the adapter layer instead of directly implementing individual transport decisions.

An initial refactoring mistake accidentally removed part of the fundamental-action execution branch in `actions.py`, producing a local-variable exception.

The missing fundamental-action handling was restored, including power/mute toggle path selection and unconfigured-command no-op handling.

Subsequent regression testing confirmed:

- Denon volume worked in both configured rooms.
- The physical encoder continued operating correctly.
- The physical Power Toggle worked.
- The CONFIG/RUN switch worked.
- The configuration management interface loaded.
- No queue warnings appeared during the final Denon smoke test.

Occasional browser-client idle timeout messages had been observed during earlier configuration navigation; they were not established as a regression caused by the adapter work.

### Real Roku equipment verification

The Sunroom configuration was changed to route volume through its Roku Ultra using Roku ECP. The Den room retained its Denon TCP volume mapping.

Adapter-cache inspection confirmed:

| Room | Volume adapter |
|---|---|
| Den | `denon-tcp` |
| Sunroom | `roku-hold` |

The Sunroom Roku controlled the connected Denon AVR-X1800H volume through the equipment's HDMI-CEC path.

Observed tests included:

1. A single clockwise detent increased receiver volume by 0.5 dB.
2. Five steady clockwise detents increased volume from -35.0 dB to -33.5 dB.
3. Clockwise/counterclockwise reversals produced commands in both directions.
4. Fast clockwise and counterclockwise twists produced one keydown followed by multiple locally handled hold extensions.
5. Approximately three seconds of continuous clockwise rotation produced a smooth, steady volume increase.
6. The receiver stopped changing volume after rotation stopped, with only very slight observed overshoot.

The sustained-rotation logs showed a fresh keydown after an extended hold, consistent with the two-second maximum-hold restart behavior.

Fast and sustained tests were conducted in RUN mode, with the configuration HTTP server inactive.

The physical feel was reported as smooth, with a small but acceptable delay in the receiver's displayed volume bar.

### Network error and recovery

One transient `OSError(119)` was observed during a direction-reversal experiment.

The exact failing HTTP operation was not identified at the time.

The receiver volume stopped changing, and a subsequent VolumeDown detent worked normally.

Later reversal, fast-rotation, and sustained-rotation tests showed no additional visible errors.

Operation-specific error diagnostics were added afterward to improve future troubleshooting.

This does not establish that all network failure conditions are solved. In particular, a successful HTTP acknowledgment does not independently prove a receiver volume change or confirm every remote key-release state.

### Jason Bourne gets a mute button

The Bourns PEC11R volume encoder's separate momentary pushbutton was connected to GND and GP10.

`VOLUME_ENCODER_BUTTON_PIN = 10` was enabled in `controls/pins.py`.

No changes were required to the generic button driver or physical action dispatcher because `physical.py` already mapped `VOLUME_MUTE` to the `mute-toggle` fundamental action.

Sunroom mute was configured as:

| Field | Value |
|---|---|
| Target | Streaming (`device-3`) |
| Method | POST |
| On path | `/keypress/VolumeMute` |
| Off path | `/keypress/VolumeMute` |

The identical paths are intentional because Roku's VolumeMute command toggles mute.

The mute command uses generic HTTP, not the Roku held-volume adapter.

Physical push-to-mute and push-to-unmute were successfully tested on both rooms:

- **Sunroom:** Roku ECP HTTP VolumeMute controlled the Denon through the Roku equipment path.
- **Den:** Existing Denon HTTP mute commands controlled the Den receiver.

PuTTY confirmed stable button presses, successful command execution, and independent per-room toggle direction history.

### Verified physical controls at Chapter 6 closeout

| Control | GPIO | Status |
|---|---|---|
| Power Toggle | GP2 | Operational |
| Room selector — Den | GP3 | Operational |
| Room selector — Sunroom | GP6 | Operational |
| Room selector — reserved Room 3 | GP7 | Operational selection; safe no-op |
| Bourns volume encoder A/B | GP8/GP9 | Operational |
| Bourns encoder push-to-mute | GP10 | Operational in both rooms |
| SERVICE / DEVICE | GP17 | Operational |
| CONFIG / RUN | GP18 | Operational |
| Custom-action encoder | Unassigned | Pending |
| Navigation, Home, Back | Unassigned | Pending |
| OLED I²C | GP4/GP5 reserved | Pending |

### Remaining boundaries

- Roku held-volume behavior remains dependent on network responsiveness and the connected equipment's CEC implementation.
- One transient socket error was observed; future errors should be evaluated using the new operation-specific diagnostics.
- Slight volume overshoot and display lag were observed but considered acceptable in initial testing.
- Maximum-hold restart behavior was observed indirectly through logs and receiver response, not through a dedicated keyup trace.
- Fast Roku rotation under simultaneous CONFIG-mode browser activity has not been equivalently stress-tested.
- The custom-action encoder, remaining buttons, OLED, audio feedback, enclosure, and power-management work remain ahead.

### Engineering conclusion

Chapter 6 established that one physical rotary encoder and pushbutton can operate two rooms through different device protocols, using the same configured fundamental actions and shared Dumb Queue™.

The system now supports Denon persistent TCP volume, Roku ECP held-volume, and generic HTTP commands without embedding equipment identities in the physical-control drivers.

The result is more than a working command path: the Roku-controlled volume knob demonstrated smooth, practical behavior during fast twists, reversals, and sustained rotation.

**One knob. Two rooms. Three transport strategies. One Dumb Queue™.**

**Jason Bourne is licensed to mute.**

---

# Milestone 19 — The Monster Gets More Fingers

**Date:** November 4–7, 2026  
**Chapter:** 7 — Physical Controls and Performance  
**Status:** PASS — navigation, playback buttons, Roku physical holds, and three-room selection verified

### Goal

Expand the Clonker's physical controls beyond the operational room selector, Power Toggle, volume encoder, and push-to-mute.

Integrate navigation and playback buttons while preserving the existing fundamental-action vocabulary, shared Dumb Queue™, and protocol adapter architecture.

Improve CONFIG-mode browser responsiveness without introducing threads, another command queue, or unnecessary architectural complexity.

### Expanded physical GPIO integration

Chapter 7 assigned and integrated the remaining navigation and playback inputs.

| Control | GPIO |
|---|---|
| Navigation Up | GP14 |
| Navigation Down | GP15 |
| Navigation Left | GP16 |
| Navigation Right | GP19 |
| Select / OK | GP20 |
| Back | GP21 |
| Home | GP22 |
| Skip Back | GP26 |
| Play/Pause | GP27 |
| Skip Forward | GP28 |
| Custom-action encoder A/B | GP11/GP12 |
| Custom-action encoder pushbutton | GP13 |

Existing assignments remained unchanged:

- GP2 — Power Toggle.
- GP3/GP6/GP7 — three-position room selector.
- GP8/GP9 — volume encoder.
- GP10 — volume push-to-mute.
- GP17 — SERVICE/DEVICE.
- GP18 — CONFIG/RUN.
- GP4/GP5 — reserved I²C.

The physical action mapping remains centralized in `controls/physical.py`, with GPIO assignments defined separately in `controls/pins.py`.

The reusable button and encoder drivers remain independent of equipment protocols.

### Physical-button hold architecture

Six physical buttons gained explicit press-and-release behavior:

- Navigation Up.
- Navigation Down.
- Navigation Left.
- Navigation Right.
- Skip Back.
- Skip Forward.

Unlike ordinary momentary actions, these buttons must distinguish a held press from a release.

The implementation extends the existing execution pipeline:

1. `controls/buttons.py` detects debounced press/release events.
2. `controls/physical.py` identifies hold-capable buttons and remembers their press context.
3. `actions.dispatch_hold()` admits hold events to the existing Dumb Queue™.
4. `device_adapters.execute_hold()` validates supported Roku ECP commands.
5. `devices/roku.py` sends `/keydown/` and `/keyup/` requests.

The physical coordinator preserves the room, endpoint, and command associated with each press.

A release therefore targets the original device even if the room selector changes while the button is held.

No separate hold queue, background thread, or independent command pipeline was introduced.

### Roku ECP button holds

The recognized physical hold commands are:

| Fundamental action | Roku key |
|---|---|
| `nav-up` | `Up` |
| `nav-down` | `Down` |
| `nav-left` | `Left` |
| `nav-right` | `Right` |
| `skip-back` | `Rev` |
| `skip-forward` | `Fwd` |

The configured command paths use Roku's ordinary `/keypress/` form, while physical hold execution translates press/release events into `/keydown/` and `/keyup/`.

Physical-button holds have a 30-second maximum-hold safety limit.

This is separate from the two-second maximum used by encoder-driven Roku held-volume.

Adapter cancellation and shutdown paths attempt best-effort cleanup of outstanding holds.

The implementation cannot guarantee key release when network connectivity is unavailable.

### Physical verification

All six Roku hold-capable buttons were exercised using actual physical controls.

Testing covered:

- Button press detection.
- Queue admission.
- Roku keydown execution.
- Physical hold behavior.
- Button release detection.
- Roku keyup execution.

A defective Skip Back tactile switch was identified during testing and replaced.

The completed tests established practical operation of the six held-button controls.

They do not establish exhaustive recovery from every possible network interruption or application shutdown.

### CONFIG-mode responsiveness

Chapter 7 also investigated slow browser page loads and occasional Test Remote timeouts.

The investigation focused on competition among:

- Frequent GPIO polling.
- Cooperative HTTP management.
- Synchronous outbound network operations.
- Diagnostic logging.
- Other scheduler work.

Adjustments reduced unnecessary polling and diagnostic overhead while retaining the cooperative scheduler.

Subsequent Safari and Chrome tests showed substantially improved Config page and Test Remote responsiveness.

The firmware remains cooperative and uses synchronous outbound network operations.

The improvements do not guarantee a fixed maximum input latency during blocking socket calls.

### Three-room configuration and selector repair

The development installation was expanded from two configured rooms to three using Config v4.

The rooms are:

| Room | Configuration |
|---|---|
| `room-1` | Den — operational equipment |
| `room-2` | Sunroom — operational equipment |
| `room-3` | Room 3 — configured placeholder with blank endpoints and command paths |

No Config v4 schema change was required.

The third selector position was already supported electrically and logically.

During initial testing, moving the selector to Room 3 did not produce the expected `ROOM SELECTED: room-3` log.

Inspection revealed that the GP7 wire had pulled out of the Pico Cowbell terminal.

Reseating the connection restored normal room-selection behavior.

**Result: PASS — Room 3 selector operation verified after correcting the loose connection.**

The failure was physical wiring, not a firmware mapping defect.

### Blank-command execution boundary

Config v4 permits blank device addresses and ordinary fundamental command paths.

Ordinary fundamental actions treat these as intentional no-ops.

Explicit physical-button holds currently require a valid endpoint, POST method, and recognized Roku command path.

Consequently, the configured blank Room 3 placeholder is not yet guaranteed to be harmless for every held-button action.

Blank-command protection for physical holds remains a small but important follow-up.

This distinction should not be confused with the earlier Chapter 6 behavior, when Room 3 was unconfigured and rejected before queue admission.

### Documentation consolidation

Following the Chapter 7 implementation work, the documentation was updated to reflect the current baseline.

The updated references include:

- `HARDWARE_DESIGN.md` — physical wiring, controls, GPIO assignments, and verification.
- `ARCHITECTURE.md` — action routing, shared queue, physical holds, and adapter responsibilities.
- `FIRMWARE_NETWORK.md` — execution mechanics, Roku holds, scheduler behavior, and diagnostics.
- `CONFIGURATION.md` — three-room installation and blank-command semantics.

The README remains the public-facing introduction; detailed implementation and historical evidence belong in the dedicated documents.

### Engineering conclusion

Chapter 7 expanded the Clonker from a physical power-and-volume controller into a substantially more complete tactile remote.

The same fundamental actions now support browser commands, rotary volume, momentary buttons, and physical Roku holds.

The existing queue and adapter architecture accommodated the new behavior without requiring a second execution system.

CONFIG-mode responsiveness improved, and the three-position selector now operates with three configured room entries.

The remaining work includes completing the custom-action rotary experience, OLED feedback, enclosure integration, and additional reliability testing.

**One Monster. Two knobs. Three rooms. More buttons than good judgment.**

**Less sleek. More CLONK.**

## Chapter 7 Addendum — Physical Polling Performance Investigation

**Date:** November 8, 2026  
**Status:** Investigation ongoing; Chapter 8 handoff pending  
**Platform:** Raspberry Pi Pico 2 W / CircuitPython 10.3.1

### Objective

Investigate occasional 40–50 ms execution spikes inside `physical.poll()` during sustained volume encoder activity.

The goal was to distinguish ordinary blocking network delays from unexpected time spent executing the physical input coordinator, without unnecessarily redesigning the cooperative scheduler or the working control system.

### PERF infrastructure

Introduced `clonker/system/perf.py` as a shared performance measurement helper.

The helper supports named measurements, elapsed-time recording, sample counts, average and maximum durations, slow-operation counts, snapshots, and resets.

Scheduler instrumentation was consolidated around this helper, replacing much of the earlier ad hoc performance bookkeeping.

Relevant measurements include:

- `physical.gap` — elapsed time between physical polling opportunities.
- `physical.exec` — complete physical polling execution.
- `queue.exec` — shared action queue processing.
- `adapter.exec` — device adapter maintenance.
- `loop.exec` — overall cooperative scheduler iteration.
- Optional internal physical measurements for scanning, events, volume handling, and dispatch.

Periodic reports retain useful context such as free memory, OLED refresh count, and management HTTP polling.

### Physical instrumentation refactor

Detailed measurements were added to `controls/physical.py` to isolate input scanning, event handling, and action dispatch.

Initial instrumentation measured individual GPIO operations. This was subsequently simplified to reduce repeated statistics updates.

A module-level diagnostic switch was then introduced:

`PHYSICAL_PERF_ENABLED = False`

The physical polling routine was refactored so that scan, event, and volume timing are conditionally bypassed when diagnostics are disabled.

Individual diagnostic flags were also introduced for future targeted investigation.

**Current baseline:** Internal physical instrumentation disabled; scheduler-level PERF remains enabled.

The dispatch and hold diagnostic flags are declared but are not yet independently wired into their respective helpers.

### Observed idle behavior

Repeated RUN-mode tests demonstrated consistently fast physical polling while idle.

In the latest Sunroom baseline:

| Measurement | Result |
|---|---:|
| GPIO gap average | 2.34 ms |
| GPIO gap maximum | 7.93 ms |
| Physical execution average | 0.82 ms |
| Physical execution maximum | 5.66 ms |
| Physical executions over 20 ms | 0 |

This establishes that the normal idle GPIO polling path is responsive.

### Observed volume activity

Sustained Sunroom volume encoder tests produced intermittent physical execution spikes.

Latest results after simplifying the physical instrumentation:

| Measurement | Result |
|---|---:|
| GPIO gap average | 2.77 ms |
| GPIO gap maximum | 237.00 ms |
| Physical execution average | 1.02 ms |
| Physical execution maximum | 46.68 ms |
| Physical executions over 20 ms | 55 |
| Queue executions over 20 ms | 10 |
| Adapter executions over 20 ms | 7 |
| Main loop maximum | 235.93 ms |

The Roku held-volume implementation includes blocking HTTP keydown operations, observed around 115–117 ms in this test.

These network operations explain substantial cooperative scheduler gaps, but do not by themselves explain why an individual `physical.poll()` call sometimes measures approximately 45 ms.

### Diagnostic experiments and findings

**Physical event logging**

Disabled detailed physical event logging during performance testing.

The physical execution spikes persisted.

**Internal PERF instrumentation**

Disabled the physical module's detailed statistics collection, initially through a no-op PERF interface and subsequently through conditional timing paths.

The spikes persisted near their previous magnitude.

A representative earlier maximum was 46.02 ms; the latest refactored implementation reached 46.68 ms.

This weakens the hypothesis that internal PERF bookkeeping is the primary cause.

**Explicit garbage collection**

An earlier controlled explicit-GC experiment was performed. Its diagnostic switch remains available in `main.py` as `GC_TEST_ENABLED`, currently set to `False`.

The investigation did not establish garbage collection as the cause of the spikes.

Automatic CircuitPython garbage collection remains a possible contributor, but has not been conclusively isolated.

Do not repeat the existing explicit-GC experiment without identifying what additional evidence a new test would provide.

**Source review**

Reviewed the scheduler, physical coordinator, button handling, encoder decoding, and PERF helper.

The scheduler's `physical.exec` measurement correctly surrounds `physical.poll()` and does not intentionally include subsequent queue or adapter execution.

The encoder and button drivers are nonblocking.

Previously measured individual dispatch operations were substantially shorter than the observed 40–50 ms physical execution spikes.

No obvious blocking 45 ms operation was identified in the normal volume input path.

### Conclusions

**Confirmed:**

- Idle physical polling is fast and consistent.
- Volume input and real equipment control remain operational.
- Blocking network operations contribute to long GPIO polling gaps.
- Physical execution spikes persist after disabling logging and most internal instrumentation.
- The outer scheduler timing boundary is correctly placed.

**Not established:**

- The exact cause of the 40–50 ms physical execution spikes.
- Whether automatic garbage collection accounts for some or all of the unexplained duration.
- Whether event-path allocations, runtime scheduling, or another interaction is responsible.
- Whether the spikes materially affect user-perceived input responsiveness.

The investigation should distinguish measured facts from hypotheses.

### Chapter 8 investigation guidance

Begin by reviewing the latest source and this diagnostic history before proposing changes.

Recommended priorities:

1. Preserve the working physical controls, action queue, and network adapters.
2. Avoid repeating previously inconclusive experiments.
3. Identify the remaining unmeasured portions of the active volume event path.
4. Investigate allocation pressure and automatic runtime pauses only with a clearly defined diagnostic hypothesis.
5. Prefer one reversible change and one controlled test at a time.
6. Avoid adding substantial instrumentation overhead to the hot GPIO polling loop.
7. Consider whether the remaining spikes warrant further optimization based on actual missed detents or responsiveness problems.

Do not confuse long cooperative scheduler gaps during blocking Roku requests with the separate physical execution spike investigation.

### Engineering status

The PERF helper and scheduler diagnostics are operational.

The physical coordinator has a lean production polling path and optional targeted diagnostics.

The approximately 45 ms physical execution anomaly remains unresolved.

**Chapter 7 leaves a working Clonker, a substantially cleaner diagnostic system, and one stubborn gremlin for Chapter 8.**

Less guessing. More measuring. More CLONK.

## Chapter 7 Closeout — November 8, 2026

Chapter 7 concludes with the Clonker's physical controls assembled, connected, and operational.

### Completed

- Physical controls mounted, soldered, wired, secured, and strain-relieved.
- Both Bourns encoders integrated: volume/mute and room-aware custom-action selection/execution.
- Navigation, playback, and Roku physical-button holds operational.
- SH1106 OLED integrated with initial custom-action feedback.
- Shared PERF instrumentation implemented for scheduler and physical polling diagnostics.
- CONFIG-mode browser responsiveness substantially improved.
- Architecture, hardware, and firmware documentation updated.

### Remaining work

- Investigate occasional 40–50 ms `physical.exec` spikes if further testing establishes a meaningful responsiveness problem.
- Continue OLED interface and feedback improvements.
- Evaluate battery packs, charging, and power management.
- Address remaining blank-command safety behavior for the unused third room.
- Preserve working network adapters and the Dumb Queue™ while refining performance.

**Chapter 7 status: COMPLETE.**

The Monster has buttons, knobs, a screen, and a nervous system.

Chapter 8 gets to teach it some manners.

Less sleek. More CLONK.

## Chapter 8 — Physical Polling Performance Resolution — November 8, 2026

### Investigation

Chapter 8 continued the investigation of recurring 40–50 ms `physical.exec` spikes during volume encoder activity.

Targeted PERF instrumentation separated GPIO scanning, complete physical polling, volume event handling, and action dispatch. Additional experiments included explicit garbage collection at 30-second and 2-second intervals.

The spikes persisted during those GC experiments. GPIO scanning and measured action dispatch remained comparatively fast.

### Root cause

Source inspection revealed that `controls/physical.py` checked room availability using:

```python
room_id not in device_config.current()["rooms"]
```

However, `device_config.current()` calls `validate_config(_current)`, constructing a validated configuration copy on every invocation.

This expensive operation ran for each physical action and occurred **before** the `physical.dispatch` timer started.

The existing dispatch measurements therefore excluded the very operation responsible for the delay.

### Fix

Added `device_config.has_room(room_id)`, a lightweight internal convenience function that checks room membership directly against the already-validated `_current` configuration.

Updated `dispatch_selected()` to use this function.

The implementation follows the established fast-access pattern of `action_details()` and `custom_action_details()`.

The public `current()` behavior remains unchanged. No changes were required to the action queue, network adapters, or physical control mappings.

### Verification

After deploying the fix, a controlled idle/volume test showed:

| Measurement | Before fix | After fix |
|---|---|---|
| Maximum physical execution | Approximately 48 ms | Approximately 8 ms |
| Physical polls exceeding 20 ms | Approximately 50 during activity | 0 during activity |
| GPIO scanning | Fast | Fast |
| Action dispatch | Fast | Fast |

The result strongly implicates repeated configuration validation as the cause of the previously observed physical polling spikes.

The observed worst-case physical execution time improved by approximately 84%. Additional repetitions may further establish consistency.

Longer cooperative scheduler gaps associated with blocking network requests remain a separate architectural consideration.

### Lessons learned

- Measure complete operations, including preparation, lookups, and cleanup.
- Treat unexplained time between nested timers as an investigation priority.
- Inspect inexpensive-looking convenience functions for hidden validation, copying, allocation, or I/O.
- Revisit previously identified architectural risks before expanding experimental instrumentation.
- Use already-validated internal configuration accessors on frequent execution paths, without exposing mutable configuration unnecessarily.
- Preserve historical test results while clearly documenting later resolutions.

### Closeout

The fast room-membership check is retained as a permanent optimization.

Performance instrumentation remains available for future diagnostics, with normal-operation flags disabled after testing.

**Chapter 8 performance investigation: RESOLVED, with strong initial before-and-after verification.**

The Dumb Queue™ was innocent. The configuration paperwork department was not.

Less validation. More CLONK.

## Chapter 8 — OLED Feedback and Configuration Access Improvements — November 8, 2026

### Configuration access improvements

Following the physical polling performance investigation, additional configuration lookups were reviewed for unnecessary validation overhead.

Added `device_config.custom_actions_for_room(room_id)` to provide fast, read-only access to the ordered Custom Actions of an already-validated room configuration.

Updated `controls/physical.py` to use this accessor rather than repeatedly calling `device_config.current()`.

The custom-action encoder previously triggered configuration validation during selection and execution, potentially more than once per detent.

Also replaced the remaining `device_config.current()` room-membership check in the physical hold-button path with `device_config.has_room()`.

These changes preserve the existing configuration safety model without repeatedly copying and validating the active configuration during physical interactions.

### OLED volume feedback

Extended the existing SH1106 OLED integration to provide simple volume-direction feedback.

The volume encoder now displays:

- `VOL UP +` for clockwise rotation.
- `- VOL DOWN` for counterclockwise rotation.

The messages intentionally indicate direction rather than attempting to track receiver volume levels.

The OLED module gained two lightweight helpers:

- `is_showing_or_pending(message)` checks whether a message is already displayed or awaiting refresh.
- `touch()` extends the display activity timeout without rendering text or performing I2C operations.

Repeated detents in the same direction therefore do not request additional text rendering. Direction changes, display wakeups, and replacement of another message trigger normal deferred updates.

The existing OLED refresh limiter and 15-second idle timeout remain in place.

### OLED mute feedback

Added `MUTE ON` and `MUTE OFF` messages after successful mute command transmission.

Mute feedback is generated in `actions.py`, using the toggle direction already maintained by the action dispatcher.

No independent mute-state tracking was added to the physical controls or OLED module.

The displayed state represents Clonker's successfully transmitted command, not independently queried receiver state.

Failed or pending commands do not generate a completed mute message.

### Display design principles

The OLED remains a lightweight, event-driven output device.

- The SH1106 controller maintains displayed pixels without continuous framebuffer updates.
- Text requests do not perform immediate I2C transfers.
- Actual display updates occur through the existing cooperative OLED poller.
- Repeated volume events extend activity without requesting redraws.
- The latest relevant interaction replaces the previous display message.
- The OLED automatically switches off after approximately 15 seconds of inactivity.
- No continuous blinking, animation, or additional periodic display workload was introduced.

Standalone experiments in `firmware/tests/test_oled.py` remain the reference for SH1106 hardware capabilities, including display persistence, inversion, contrast, and display on/off behavior.

Future display ownership or notification-priority features may be considered if additional requirements justify them.

### Hardware verification

The updated firmware was deployed to the Pico 2 W and tested with the physical controls.

All reported functional tests passed:

- Clockwise volume rotation displayed `VOL UP +`.
- Counterclockwise volume rotation displayed `- VOL DOWN`.
- Volume encoder press displayed `MUTE ON`.
- Subsequent mute press displayed `MUTE OFF`.
- Custom-action encoder selection correctly displayed the selected Custom Action.
- Custom-action messages replaced previous volume or mute messages.
- The OLED switched off after approximately 15 seconds of inactivity.

The custom-action encoder remained operational following the fast configuration accessor changes.

The display implementation avoids repeated same-direction text requests by design. Additional I2C instrumentation was not required for this functional verification.

### Chapter 8 checkpoint

The physical polling performance investigation is resolved.

Additional unnecessary configuration validation has been removed from physical control paths.

Volume, mute, and custom-action OLED feedback are operational and hardware-tested.

The Dumb Queue™, network adapters, and existing physical control behavior remain intact.

**Chapter 8 OLED feedback checkpoint: COMPLETE.**

The Monster has learned to speak, without becoming a chatterbox.

Less rendering. More CLONK.

## Chapter 8 — Room-Aware OLED and Custom Action Acknowledgment — November 9, 2026

### Objective

Extend the operational SH1106 OLED beyond volume, mute, and basic Custom Action selection while preserving the cooperative scheduler's responsiveness.

The design goals were:

- Provide useful room-selection feedback.
- Support both single-line and two-line text layouts.
- Distinguish Custom Action selection from execution.
- Avoid unnecessary framebuffer redraws and I2C traffic.
- Reuse existing display timing and idle behavior.

### Room-selector integration

The physical room selector now requests a two-line OLED message when the selected room changes.

The first line identifies the room position. The second line displays the configured room name or `UNASSIGNED`.

The two-line layout uses a smaller heading and enlarged main text.

Room changes continue to reset the Custom Action selection index without executing an action.

Physical hardware testing confirmed the room display, including the unconfigured third selector position.

### Custom Action execution acknowledgment

The Custom Action encoder now has two visually distinct states:

1. Rotation selects an action and displays its name normally.
2. Pressing the shaft dispatches the action and requests an inverted OLED acknowledgment after successful dispatch.

The SH1106 supports hardware inversion through controller commands `0xA7` and `0xA6`.

This avoids modifying or retransmitting the framebuffer merely to change the visual acknowledgment state.

The acknowledgment remains inverted until another message, an explicit reset, or the existing idle timeout.

No additional timer, animation, or blocking delay was introduced.

### Same-text acknowledgment reset

A subtle case was identified: selecting an action again may need to clear an acknowledgment even when the displayed action name is unchanged.

The OLED API therefore gained:

    show_text(message, second_line=None, reset_ack=False)

The optional `reset_ack=True` clears the inversion acknowledgment independently of text rendering.

Hardware testing verified that resetting acknowledgment for identical text restored normal display mode without incrementing the framebuffer refresh count.

### Deferred execution and display behavior

The physical Custom Action handler now:

1. Dispatches the selected action through the existing action system.
2. Requests the selected name on the OLED after successful dispatch.
3. Requests hardware inversion through `oled.acknowledge()`.

The OLED poller remains responsible for actual I2C operations.

The acknowledgment is visual feedback for successful dispatch, not proof that every step of a potentially asynchronous Custom Action has completed.

The shared Dumb Queue™ and network adapters were not modified.

### Hardware verification

The following behaviors were successfully exercised on the Pico 2 W:

| Test | Result |
|---|---|
| Two-line room display | PASS |
| Unconfigured room indication | PASS |
| Single-line display after two-line message | PASS |
| Automatic OLED idle-off | PASS |
| Hardware inversion and restoration | PASS |
| Same-text acknowledgment reset | PASS |
| Reset without framebuffer redraw | PASS |
| Physical Custom Action execution acknowledgment | PASS |

The complete Custom Action encoder acknowledgment interaction was reported to work beautifully during live hardware testing.

Additional unusual-state and rapid-interaction testing remains ongoing.

### Chapter 8 checkpoint

Room-aware OLED feedback and persistent Custom Action execution acknowledgment are operational.

The design retains deferred display updates, hardware-assisted inversion, the existing refresh limiter, and automatic idle-off.

Further physical-button feedback will be evaluated individually. Persistent inversion is particularly appropriate for the Custom Action encoder's two-stage select-and-execute interaction; ordinary navigation and playback controls may require only brief messages or no display feedback.

**Chapter 8 OLED acknowledgment milestone: COMPLETE.**

The Monster now knows the difference between *choosing* something and *CLONKing* it into action.

Less redraw. More CLONK.

### Chapter 8 — Complete Physical-Control OLED Feedback — November 9, 2026

OLED feedback was extended to the remaining physical controls and verified on the assembled Clonker.

- Navigation: directional labels with custom arrowhead glyphs.
- Home, Back, and Select: direct button labels.
- Skip Back / Forward: directional playback labels.
- Play/Pause: `PLAY/PAUSE`, without assuming playback state.
- Power toggle: `POW!`, without assuming equipment power state.
- Volume and Mute: existing feedback retained, including `MUTE ON` and `MUTE OFF`.
- Room selection and Custom Actions: existing two-line display and execution acknowledgment retained.

Physical testing confirmed the new button messages displayed correctly. The navigation group was also tested for normal hold behavior.

The OLED font gained custom arrowheads, an exclamation mark, and experimental `:)` / `:(` glyphs. The emoticons were tested on hardware but proved insufficiently legible at 5×7 resolution. Their temporary button messages were reverted; larger icons remain a possible future enhancement.

All primary physical controls now provide OLED feedback. Display requests remain nonblocking, and persistent inversion remains reserved for Custom Action execution.

**Chapter 8 physical-control OLED feedback milestone: COMPLETE.**

Less guessing. More `POW!`.

### Chapter 8 — CONFIG HTTP Resilience and Recovery — November 10, 2026

Chapter 8 returned to the CONFIG management server after intermittent Chrome stalls and a real `MemoryError` exposed weaknesses in its handling of large responses and exceptional network conditions.

The objective was not to build a more elaborate web server. It was to make the existing cooperative, single-client server more predictable, reduce memory pressure, and prevent management HTTP failures from terminating the physical remote.

The work proceeded in four stages.

#### B1 — Bounded static HTML streaming

The original static-page response path could temporarily hold several large copies of an HTML response in memory: the file contents, encoded response body, and combined HTTP response.

A previously observed allocation failure involved a 13,824-byte allocation.

Static HTML delivery was changed to stream directly from flash in 512-byte chunks. The implementation retains a small response header and one file chunk instead of constructing the complete response in RAM.

Dynamic API response construction was left unchanged.

Live Chrome testing included repeated Configuration ↔ Test Remote navigation and aggressive refreshes.

Observed successful responses included:

| Request | Response size |
|---|---:|
| Configuration HTML | 40,679 bytes |
| Test Remote HTML | 13,806 bytes |
| Configuration API | Approximately 5,399 bytes |
| Clock API | Approximately 181 bytes |

The tested requests completed without observed zero-byte sends or browser stalls.

A memory-monitor checkpoint showed approximately 321,744 bytes free initially and 307,984 bytes after extended navigation, a decrease of 13,760 bytes. This was not sufficient evidence to establish a memory leak.

**B1 result:** Streaming implementation operational and verified under repeated browser navigation. The original cause of every historical stall was not conclusively established.

#### B2 — MemoryError recovery

The main scheduler gained a `MemoryError` exception boundary around `web.poll()`.

The recovery path uses `web.abort_low_memory()` to discard active request, response, file, client, and diagnostic state without ordinary diagnostic formatting, followed by garbage collection.

A temporary `MemoryError` injection on the Test Remote route exercised this path.

The application logged the allocation failure, discarded the affected client, and continued serving subsequent Configuration and API requests without restarting the Pico.

The temporary injection was removed after testing.

**B2 result:** Simulated allocation-failure recovery passed. Genuine severe heap exhaustion remains a distinct condition that was not deliberately reproduced.

#### B3 — Unexpected network OSError recovery

The inbound HTTP exception boundary was extended to handle unexpected `OSError` conditions escaping `web.poll()`.

Client cleanup was hardened so that connection state is cleared before resource closure, and ordinary diagnostic failures do not prevent cleanup.

A temporary `OSError(104)` injection on the Test Remote route exercised the recovery path.

The application logged the injected `ECONNRESET`, discarded the affected connection, and subsequently served Configuration and API requests successfully.

The temporary injection was removed.

**B3 result:** Simulated unexpected network-error recovery passed.

The later B4 implementation refined the policy for an `OSError` escaping `web.poll()`: such errors now trigger listener teardown and delayed restart, rather than only discarding the client.

#### B4 — Listener failure detection and restart

Listener cleanup was hardened to clear listener state before closing the socket.

Unexpected `accept()` errors now propagate to the main scheduler, while expected nonblocking `EAGAIN` conditions remain normal control flow.

The scheduler gained a configurable listener-retry interval:

```python
WEB_LISTENER_RETRY_NS = 5_000_000_000  # 5 seconds
```

Startup failures are logged and retried after the configured interval while CONFIG mode remains selected.

Unexpected errors escaping management polling cause listener teardown and a delayed restart.

Switching to RUN stops the listener and resets the retry deadline, allowing the next CONFIG entry to attempt startup immediately.

Normal Chrome navigation and physical CONFIG → RUN → CONFIG switching passed before fault injection.

Two separate controlled failures were then tested:

| Failure injected | Observed recovery |
|---|---|
| `OSError(104)` during listener accept | Listener stopped, restarted approximately 5.0 seconds later, and served both browser pages |
| `OSError(104)` during first listener startup | Startup failure logged, listener started approximately 5.0 seconds later, and subsequent browser/API requests completed |

Both temporary injections were removed and the production `web.py` was verified clean in GitHub.

**B4 result:** Listener startup and accept-failure recovery passed simulated-failure tests.

#### Diagnostics and conclusions

`web_diag.py` provided connection-level measurements including request and response sizes, response preparation time, send attempts, `EAGAIN` events, zero-byte sends, and connection closure reasons.

Successful responses consistently reported `close=complete` in the observed post-change tests, with `send_zero=0`.

The work preserved the existing cooperative scheduler, single-client management model, shared Dumb Queue™, and CONFIG/RUN operating modes. No threads, second queue, or general-purpose HTTP framework were introduced.

The distinction between demonstrated recovery and guaranteed recovery remains important:

- Controlled fault injection verified application exception handling, cleanup, and retry timing.
- It did not establish recovery from every genuine Wi-Fi radio failure, persistent socket-stack fault, or severe heap-exhaustion condition.
- Long-uptime behavior and concurrent high-rate physical/network activity remain worthwhile future investigations.

**Chapter 8 CONFIG HTTP resilience milestone: COMPLETE.**

The Monster can now lose a browser connection, discard a failed HTTP transaction, and resurrect its CONFIG listener without deliberately taking the physical remote down with it.

*Less panic. More CLONK.*

---

## Chapter 9 — Portable Power Comes Alive

**November 12, 2026 — Battery-powered operation demonstrated**

Chapter 9 continued the reliability work with a practical question:

Could THE CLONKER 10000 operate independently of a computer, powered by its own rechargeable batteries?

The first bench tests answered that question: **yes**.

### Battery hardware

The portable power configuration used:

- DFRobot DFR0969 dual-18650 battery module.
- Two rechargeable 18650 lithium-ion cells.
- Inline Color TFT USB power tester.
- USB-A to Micro-USB cable connecting the module to the Pico 2 W.

Both new cells measured approximately **3.560 V** individually before installation.

The DFRobot module was tested with its HOLD/NORMAL selector in HOLD.

### Establishing the USB power baseline

Before switching to battery power, the Clonker was operated from a Lenovo laptop through the inline USB tester.

The USB tester passed through the USB data connection successfully:

- Windows recognized the Pico.
- The CircuitPython filesystem remained accessible.
- PuTTY serial communication worked.
- The Clonker application started normally.

This established that the tester could be used for electrical measurements without preventing the normal USB development workflow.

Typical observed current consumption was approximately 34–35 mA at 5.01 V.

The tester's current graph also responded to physical and software activity:

- Volume encoder detents produced visible current changes.
- Operating the CONFIG/RUN switch produced a current transient.
- Loading the Configuration and Test Remote browser pages produced visible current peaks.

These observations demonstrated that the tester could reveal small changes in the controller's electrical load.

### First battery-powered operation

The laptop was disconnected from the Clonker power path.

The DFRobot battery module supplied the Pico through its regulated USB output, with the USB tester remaining inline.

The Clonker booted and operated successfully.

Initial observed measurements:

| Measurement | Approximate result |
|---|---:|
| USB output voltage | 5.12 V |
| Typical idle current | 33–37 mA |
| Typical idle power | 0.17–0.19 W |
| CircuitPython and application startup | 10–12 seconds |

The physical controls and OLED continued operating normally.

The measurements represent USB-side electrical consumption, not direct battery-cell current. Battery conversion efficiency and practical runtime remain unmeasured.

### Startup READY feedback

A small application enhancement was introduced during testing.

After initialization, the OLED displays a brief READY indication and then clears it automatically.

This provides confirmation that the Clonker has started successfully even when no computer or serial console is attached.

During battery testing, the READY indication appeared approximately 10–12 seconds after power was applied.

The behavior was successfully tested after deploying the updated application.

### Results and next steps

**Established:**

- The battery module can power the complete Clonker prototype.
- CircuitPython and the application start successfully.
- The OLED and physical controls remain operational.
- The USB tester provides useful voltage, current, power, and activity measurements.
- The existing USB development workflow works through the inline tester.

**Not yet established:**

- Total battery runtime.
- Discharge behavior near battery depletion.
- Charging and simultaneous charging/load behavior.
- Long-term reliability under battery power.
- Permanent module mounting and internal cable routing.
- Future sleep/wake implementation.

An extended battery-powered observation period was started, but its final endurance result had not yet been recorded at this milestone.

**Chapter 9 portable-power milestone: INITIAL BENCH TEST PASSED.**

The Monster has officially learned to roam without its USB umbilical cord.

*Less tethered. More CLONK.*

## Chapter 9 — Software Sleep and Wake

**November 13, 2026 — Software-managed sleep operational**

Following the first successful battery-powered operation, Chapter 9 introduced an inactivity-based software sleep state.

The objective was to reduce battery consumption without sacrificing reliable physical wake controls, while preserving an architecture that could eventually support hardware light sleep or deep sleep.

### Sleep architecture

CircuitPython 10.3.1 on the Raspberry Pi Pico 2 W does not provide the required `alarm` support for the planned hardware sleep experiments.

The initial implementation therefore uses **software-managed sleep**:

- The CPU remains running.
- Physical controls continue being polled.
- Wi-Fi is disabled.
- The OLED is shut down and its I²C interface released.
- Action-queue processing is suspended.
- Device-adapter maintenance is suspended.
- OLED polling and periodic memory monitoring are suspended.
- The CONFIG web listener is prevented from starting during sleep.
- The scheduler uses a longer delay between iterations.

This is not hardware deep sleep. Its power savings come from disabling peripherals and reducing application activity.

### Sleep manager

`firmware/clonker/system/sleep_manager.py` owns inactivity tracking, sleep transitions, hardware shutdown, and wake policy.

Developer settings include:

- `SLEEP_ENABLED`
- `SLEEP_DRY_RUN`
- `SLEEP_IDLE_TIMEOUT_S`
- `SLEEP_FAREWELL_S`

The implementation was first validated in dry-run mode before enabling actual Wi-Fi and OLED shutdown.

The sleep manager also tracks physical CONFIG-switch transitions.

### Entering sleep

Clonker enters software sleep when:

- Sleep is enabled.
- The application is in RUN mode.
- The inactivity timeout has elapsed.
- No queued actions remain.

CONFIG mode inhibits sleep.

During real sleep entry, the OLED briefly displays:

**Going Zzzz!**

The farewell remains visible for approximately 1.5 seconds before the OLED closes and Wi-Fi is disabled.

If hardware shutdown raises an exception, Clonker attempts a recovery reboot rather than continuing with an uncertain hardware state.

### Wake behavior

While sleeping:

| Input | Behavior |
|---|---|
| Momentary pushbutton | Wake and reboot |
| CONFIG switch transition | Wake and reboot |
| Volume encoder rotation | Ignored |
| Custom-action encoder rotation | Ignored |
| Room selector movement | Ignored |

The first wake-eligible input is consumed; it must not dispatch an equipment command.

Wake uses `microcontroller.reset()` to restore normal CircuitPython initialization and Wi-Fi connectivity.

The CONFIG switch is transition-sensitive: movement in either direction is considered wake-eligible. Following reboot, its current position determines the operating mode.

The existing CONFIG/room-selector reboot handshake remains separate from ordinary sleep/wake behavior.

### Scheduler optimization

The normal application scheduler retains its existing responsiveness.

During software sleep, the main-loop delay increases from 1 ms to 25 ms.

This reduces scheduler activity without altering normal awake-mode timing.

Physical controls remain polled during sleep. Short presses, including the volume encoder's MUTE pushbutton, were successfully tested.

### Power-management experiments and design decisions

Several experiments informed the Chapter 9 software-sleep design.

#### Wi-Fi shutdown and recovery

Disabling the Wi-Fi radio using `wifi.radio.enabled = False`
provided a way to reduce power consumption while sleeping.

However, experiments with turning the radio off and back on
did not consistently restore stable network operation.

Wi-Fi reconnection also required approximately four seconds,
making this an unattractive recovery mechanism for a physical
remote control.

The chosen solution is to disable Wi-Fi when entering sleep
and perform a full `microcontroller.reset()` on wake.

This sacrifices a few seconds of wake-up time in exchange for
a predictable initialization path through the existing startup
logic. The triggering wake input is consumed rather than sent
to the controlled equipment.

#### CircuitPython Wi-Fi power management

Experiments with `wifi.radio.power_management` did not produce
the expected reduction in current consumption.

Observed Wi-Fi behavior instead appeared less favorable, with
the radio seemingly operating hotter rather than saving power.

These were experimental observations, not a quantified thermal
study or proof of a CircuitPython defect.

The final implementation does not rely on this API.

#### Hardware sleep and future CircuitPython versions

CircuitPython 10.3.1 on the Raspberry Pi Pico 2 W does not
provide the `alarm` module needed for the planned hardware
sleep/wake implementation.

RP2350 alarm support has appeared in CircuitPython 11.x alpha,
making a future stable release worth investigating.

Hardware sleep could potentially reduce consumption beyond
the current software-sleep implementation, which continues
running the CPU and polling physical inputs.

Actual sleep current, supported wake sources, wake latency,
and network recovery will all require testing on the eventual
stable CircuitPython release.

The current software-sleep implementation remains the
functional baseline until a better approach is demonstrated.

#### Awake current observations

Additional measurements showed that normal idle RUN current
often settles around 33–35 mA, although approximately 38 mA
was also observed.

Control actions can briefly increase current into the
50 mA range before it settles again.

The approximately 24 mA software-sleep measurement therefore
represents a reduction of roughly 27–37% compared with the
observed 33–38 mA awake range.

All measurements were taken at the Pico's USB input, not at
the battery cells. DFRobot converter losses, indicator LEDs,
and other module consumption are not included.

### Electrical measurements

Measurements were taken using an inline Color TFT USB tester at approximately 5 V.

| Operating condition | Approximate current |
|---|---:|
| Normal RUN, awake | 38 mA |
| Software sleep, original scheduler | 25 mA |
| Software sleep, 25 ms scheduler delay | 24 mA |
| Software sleep, OLED and memory polling suspended | 24 mA |

The final measured reduction was approximately **14 mA, or 37%**, relative to the observed awake baseline.

The 1 mA difference between the initial and optimized sleep readings is small enough that repeated measurements would be needed to establish its significance.

These are USB-side measurements. They do not include the DFRobot boost converter's losses or its own indicator and control circuitry when powered separately.

### Battery-powered verification

The DFRobot DFR0969 module, using two 18650 cells, successfully powered Clonker independently of the laptop.

Tests confirmed:

- Entry into software sleep while battery-powered.
- Continued power availability after the inactivity timeout.
- Successful wake using the HOME pushbutton.
- Reboot and OLED READY feedback.
- Successful recognition of a subsequent HOME press.

The DFRobot module was operated in HOLD mode.

Four illuminated LEDs remained visible during battery operation. The module's double-click power-button behavior was also investigated; this controls board output power rather than providing a documented LED-only shutdown feature.

### Overnight endurance test

An overnight battery-powered software-sleep endurance test began
on November 13, 2026.

Test configuration:

- Two rechargeable 18650 cells.
- DFRobot DFR0969 module in HOLD mode.
- No external charging or laptop power.
- No inline USB power meter.
- 60-second inactivity timeout (development setting).
- 25 ms software-sleep scheduler delay.
- Real Wi-Fi and OLED shutdown.
- Wake by physical pushbutton.

**Result: PASSED — November 14, 2026.**

After approximately 12 hours on battery power, the DFRobot
indicated three solid battery LEDs out of four.

A physical pushbutton successfully woke Clonker, triggering
the expected microcontroller reboot. The OLED subsequently
displayed `CLONKER READY!`.

One battery cell measured approximately 3.814 V after the test.

This established that the software-sleep implementation could
remain battery-powered and wake-responsive overnight.

The test was deliberately ended so the cells could be recharged
and enclosure work could continue.

It was not a full-discharge endurance test. The battery LEDs
are approximate indicators, not calibrated runtime measurements.

A longer, fully charged battery-runtime test remains future work.

### Practical sleep settings and secret override

Following the initial power-management experiments, the default
inactivity timeout was increased from 60 seconds to 600 seconds
(10 minutes).

The developer setting in
`firmware/clonker/system/sleep_manager.py` remains:

`SLEEP_ENABLED = True`

Changing this flag to `False` disables automatic sleep at startup.

A runtime sleep toggle was also implemented using the existing
physical room selector.

With the physical CONFIG switch enabled, the sequence:

`1 -> 2 -> 1 -> 2 -> 1 -> 2`

completed within 10 seconds toggles sleep availability.

The OLED confirms the resulting state with:

- `SLEEP OFF`
- `SLEEP ON`

Both toggle directions were successfully tested on the assembled
Clonker on November 14, 2026.

The override is volatile: rebooting restores the developer's
configured startup default.

Re-enabling sleep resets the inactivity timer, providing a fresh
10-minute interval.

The existing secret reboot handshake remains separate:

`2 -> 3 -> 2 -> 3 -> 2 -> 3`

Both handshakes require the physical CONFIG switch.

The sleep override is useful when Clonker is being operated
continuously, particularly while connected to external charging
power, without repeatedly entering software sleep.

### DFRobot charging and power-transition experiments

The DFRobot DFR0969 battery module was evaluated with two
rechargeable 18650 cells and an inline Color TFT USB tester,
informally nicknamed "SparkFun."

The module was tested both while powering Clonker and separately
with only the USB tester connected to its USB-A output.

#### Battery to external charging power

Connecting the USB-C charging input while Clonker was operating
on battery power did not interrupt normal operation.

Clonker remained awake and responsive.

This established a successful battery-to-charger transition
under the tested conditions.

#### External charging power to battery

Disconnecting the USB-C charging cable while Clonker was
operating caused the Pico to restart.

The normal startup sequence subsequently completed, taking
approximately 11 seconds.

To isolate the cause, Clonker was disconnected and the USB
tester was attached directly to the DFRobot's USB-A output.

Removing external charging power caused the USB tester itself
to reboot.

The behavior was reproduced after the battery module indicated
four solid charge LEDs.

The experiment was then repeated in NORMAL mode rather than
HOLD mode, with the same result.

| Mode | Charger connected | Battery-only output | Charger removal |
|---|---:|---:|---|
| HOLD | 5.040 V | 5.129 V | USB tester rebooted |
| NORMAL | 4.999 V | 5.121 V | USB tester rebooted |

These are representative steady-state readings taken with no
external load beyond the USB tester.

In NORMAL mode, another charger-connected reading of 5.050 V
was observed before the charging indicator settled.

The four battery indicator LEDs remained solid after the
charger was disconnected in the fully charged tests.

**Conclusion:** Under the tested conditions, the DFRobot
supports an uninterrupted battery-to-charger transition,
but removing charging power produces an interruption or
sufficiently deep voltage dip to restart the connected device.

This behavior occurs in both HOLD and NORMAL modes and does
not originate in Clonker's application software.

The exact transient voltage and interruption duration have
not been measured with an oscilloscope.

HOLD remains the intended operating mode because it has
already supported the low-current software-sleep experiments.

The brief reboot on charger removal is considered acceptable
for the current design.

#### Charging-input observations

Charging-input measurements were also made with the USB
tester placed between the external 5 V supply and the
DFRobot's USB-C charging input.

Observed examples included:

- Approximately 4.780 V at 1.221 A using a 5 V / 1 A adapter,
  exceeding that adapter's rated output current.
- Approximately 4.864 V at 1.624 A using a power-strip USB port.
- Approximately 4.895 V at 1.824 A during another charging
  observation.

These are charging-input measurements, not direct battery-cell
charging currents.

A suitably rated, reputable 5 V supply is preferred for
continued charging tests.

The USB-C PD charger compatibility experiment was inconclusive:
one USB-C charger did not power the inline tester through the
tested cable arrangement.

### Enclosure and charging integration

A panel-mounted USB-C charging port was fitted to the side
of Clonker's enclosure.

The DFRobot battery module and two 18650 cells remain part
of the planned internal power installation.

Final internal mounting, wiring, cable strain relief, and
thermal verification remain to be completed.

### Remaining work

- Verify CONFIG-switch wake during real battery-powered sleep.
- Conduct a longer fully charged battery-runtime test.
- Complete safe internal mounting of the DFRobot module and cells.
- Verify charging and power transitions after final assembly.
- Update architectural, operating-mode, and hardware documentation.
- Revisit hardware light/deep sleep when suitable stable
  CircuitPython support becomes available.

**Chapter 9 software-sleep milestone: FUNCTIONAL TESTS PASSED.**

Overnight battery-powered sleep and wake have been demonstrated.
The manual sleep override works in both directions, and the
DFRobot's asymmetric charging-power behavior has been isolated.

The Monster can now decide when bedtime is appropriate.

*Less awake. More Zzzz. Still CLONK.*

The Monster can now turn off its radio, close its eyes, and wait for someone to wake it.

*Less awake. More Zzzz. Still CLONK.*

---

**THE CLONKER 10000**

*Less sleek. More CLONK.*

**CLONK! ⚡🔩**
