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

**As of October 19, 2026:**

The Clonker has a working JSON v2 configuration system, browser management interface, persistent storage safeguards, and a Test Remote that exercises fourteen fundamental actions through a shared logging-only dispatcher.

The next major chapter is real outbound HTTP device control.

After that come physical switches, encoders, room selection, and the satisfying mechanical personality that inspired the entire project.

The Clonker isn't finished.

But it has progressed from a collection of beautiful knobs and questionable ambitions into an actual running software system.

**THE CLONKER 10000**

*Designed by David Jacobson.*

**CLONK! ⚡🔩**
