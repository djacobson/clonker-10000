
# Clonker 10000 — Configuration Test Record

**Status:** Configuration v1 core operational  
**Test date:** October 16, 2026  
**Hardware:** Raspberry Pi Pico 2 W  
**Firmware:** CircuitPython 10.3.1

## Verified Capabilities

| Capability | Status |
|---|---|
| Three-room XML configuration loading | PASS |
| Browser configuration display and editing | PASS |
| Browser POST saves XML to flash | PASS |
| No-change save detection | PASS |
| Two-generation backup rotation | PASS |
| Configuration reload into active memory | PASS |
| Configuration persistence across soft reboot | PASS |

## Backup Rotation Verification

Following two consecutive browser saves:

1. `Den` → `Den Test`
2. `Den Test` → `Den`

The following values were verified directly in the CircuitPython REPL:

| File / State | Room 1 Name |
|---|---|
| Primary XML | Den |
| `.bak` | Den Test |
| `.bak.old` | Den |
| Active configuration | Den |

## Additional Verified Behavior

- Reading backup XML does not modify the active configuration.
- A no-change browser save reports “No changes to save.”
- A successful browser save reports “Configuration saved successfully.”
- The browser refreshes its configuration after saving.
- The configuration survives a Ctrl+D soft reboot.
- The configuration page displays successfully in Chrome and Safari.
- The HTTP server operates on port 9090.

## Implemented — Additional Testing Pending

The following protections are implemented but have not all been verified through end-to-end browser testing:

- Revision-conflict rejection
- Invalid configuration rejection through HTTP
- Read-only filesystem save protection
- Interrupted-write recovery under simulated failure conditions

These should be included in a future configuration hardening pass.

## Development Notes

### Filesystem Modes

| Mode | GP17 Jumper | Pico Filesystem |
|---|---|---|
| DEVICE | Installed (GP17 to GND) | Writable by Pico |
| SERVICE (USB) | Removed | Writable by USB host |

A full power cycle is required when switching filesystem modes.

### Development Workflow

- Edit firmware using Working Copy on iPad.
- Commit and push changes to GitHub.
- Pull changes to Windows using GitHub Desktop.
- Deploy updated files to CIRCUITPY in SERVICE mode.
- Return to DEVICE mode for configuration write testing.
- Use Ctrl+D for a reliable CircuitPython soft reboot.

### Web Interface

Development URL:

`http://192.168.50.12:9090/`

The configuration page supports viewing and editing three rooms, including room names, TV IP addresses, AVR IP addresses, and volume-control selections.

## Milestone Conclusion

**Clonker Configuration v1 core functionality is operational and hardware-tested.**

The Pico 2 W can load, display, validate, save, back up, and reload its XML configuration through the browser interface.

The original `Den` configuration was restored and verified after testing.

Remaining defensive tests are deferred to a future hardening pass.

**Next planned subsystem:** HTTP action definitions and browser-based command testing against network-connected Denon receivers, followed by GPIO control integration.

—

*CLONK! The monster has a memory.*

---

## JSON v2 Configuration and Persistence — Hardware Test Record

**Date:** October 16, 2026  
**Hardware:** Raspberry Pi Pico 2 W (RP2350)  
**Runtime:** CircuitPython 10.3.1  
**Status:** Main JSON v2 configuration and persistence tests PASSED

### Scope

Tested the new `device_config_v2.py` module independently of the operational XML v1 configuration engine.

The JSON v2 module is not yet integrated with `main.py`, `web.py`, or the browser configuration interface.

Testing used the CircuitPython REPL and, for persistence tests, the Pico's writable DEVICE filesystem mode.

### 1. JSON Loading and Serialization

| Test | Result |
|---|---|
| Load JSON v2 configuration | PASS |
| Schema version | 2 |
| Fixed rooms | 3 |
| Fundamental commands per room | 14 |
| Total fundamental commands | 42 |
| JSON serialization/deserialization round-trip | PASS |
| Stable configuration revision | PASS |
| Compact serialized size | 2,754 bytes |
| Baseline revision | `3596587d` |

The initial hardware test revealed that CircuitPython's `json.dumps()` does not support the `ensure_ascii` keyword argument.

The unsupported argument was removed, and subsequent serialization and revision tests passed.

### 2. Filesystem Write and Read-Back

Confirmed that the Pico's root filesystem was writable in DEVICE mode.

Created a disposable configuration file:

`/clonker/test_config_v2.json`

The file was successfully written, flushed, read back, and validated.

The configuration revision matched the original baseline.

**Result: PASS**

### 3. Test-Path Safety Correction

During the first persistence test, changing the module's `CONFIG_FILE` variable did not redirect the default filename already bound to `load()` and `save()`.

Consequently, the first save changed the production JSON fixture's room name from `Den` to `Den Test`.

The persistence engine created a valid backup containing the original `Den` configuration.

The original configuration was restored successfully through the persistence engine.

The XML v1 configuration was unaffected.

The module was subsequently revised so that:

- `load(path)` binds the active configuration to that path.
- `save()` uses the loaded configuration path.
- An explicitly supplied save path must match the loaded path.
- A mismatched save path raises `ValueError` before writing.

The Pico rejected an attempted save to the production path after loading the disposable test configuration.

**Wrong-file save protection: PASS**

All subsequent persistence tests used the disposable configuration path.

### 4. Configuration Save and Active Memory

Saved a change to the disposable configuration:

`Den` → `Den Test`

| Check | Result |
|---|---|
| Save returned `True` | PASS |
| Primary file contained `Den Test` | PASS |
| Backup contained `Den` | PASS |
| Active RAM contained `Den Test` | PASS |
| Configuration revision changed | PASS |

**Result: PASS**

### 5. No-Change and Stale-Revision Protection

Attempted to save an unchanged configuration using its current revision.

The save returned `False`, as expected.

Attempted another save using an intentionally stale revision (`00000000`).

The engine rejected it with:

`ValueError: Configuration revision mismatch`

The primary configuration, active RAM configuration, and revision remained unchanged.

**Result: PASS**

### 6. Backup Rotation

Saved a second change:

`Den Test` → `Den Test 2`

Verified three generations on Pico flash:

| File | Room 1 name |
|---|---|
| `test_config_v2.json` | Den Test 2 |
| `test_config_v2.json.bak` | Den Test |
| `test_config_v2.json.bak.old` | Den |

**Result: PASS**

### 7. Corrupted-Primary Fallback

Preserved the disposable primary configuration in memory.

Overwrote the disposable primary with deliberately invalid JSON.

The engine detected the JSON syntax error and loaded the valid `.bak` configuration.

Observed fallback value:

`Den Test`

The original primary file was then restored and reloaded successfully.

Observed restored value:

`Den Test 2`

Ordinary fallback did not silently overwrite the corrupted primary.

**Result: PASS**

### 8. Missing-Primary Fallback

Temporarily renamed the disposable primary file to a `.held` filename.

The engine detected that the primary was missing and successfully loaded the `.bak` configuration.

Observed fallback value:

`Den Test`

Verified that ordinary loading did not recreate the missing primary.

Restored the original primary filename and reloaded it.

Observed restored value:

`Den Test 2`

**Result: PASS**

### 9. Final Configuration State

At the conclusion of these tests:

- The production JSON configuration had been restored to its original `Den` room name.
- The disposable primary contained `Den Test 2`.
- The disposable `.bak` contained `Den Test`.
- The disposable `.bak.old` contained `Den`.
- The original XML v1 configuration engine remained operational.
- JSON v2 had not yet been integrated into the main firmware or browser.

### 10. Not Yet Verified

The following remain outside the completed hardware tests:

- Explicit recovery that recreates a missing primary from a backup.
- Recovery from simulated interruptions during individual write or backup-rotation steps.
- Filesystem read-only rejection of a JSON v2 save.
- External modification of the primary between load and save.
- Browser HTTP editing and persistence using JSON v2.
- Integration with `main.py` and the eventual action dispatcher.
- Persistence across a full hardware power cycle using the new JSON v2 engine.

Backup rotation uses multiple filesystem operations and is not guaranteed to be atomic during unexpected power loss.

### Conclusion

The JSON v2 configuration engine has passed its principal loading, serialization, validation, save, revision, backup-rotation, and fallback tests on actual Pico 2 W hardware.

The implementation is ready to proceed toward firmware and browser integration, subject to the remaining integration and defensive tests.

**Milestone: JSON v2 persistence baseline verified.**

**CLONK!**
