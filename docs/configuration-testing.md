
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


---

## JSON v2 Browser Integration — Hardware Test Record

**Date:** October 16, 2026  
**Hardware:** Raspberry Pi Pico 2 W (RP2350)  
**Runtime:** CircuitPython 10.3.1  
**Browser clients:** Chrome on Windows; Safari on iPad  
**Status:** Browser integration and basic persistence PASSED

### 1. Scope

Tested the integration of the previously verified JSON v2 configuration engine with the Clonker's HTTP server and browser configuration interface.

Files involved:

- `firmware/clonker/main.py`
- `firmware/clonker/web.py`
- `firmware/clonker/www/index.html`
- `firmware/clonker/device_config_v2.py`

The integration replaces the operational configuration interface's XML v1 dependency with JSON v2 while retaining the original XML v1 configuration engine and files for rollback.

The HTTP request size limit was increased from 2,048 bytes to 10,240 bytes to accommodate the larger JSON configuration.

### 2. Initial Startup and Socket Compatibility

The first hardware startup successfully loaded the JSON v2 configuration and started the HTTP server on port 9090.

However, the HTTP polling loop crashed with:

`AttributeError: 'module' object has no attribute 'EWOULDBLOCK'`

CircuitPython 10.3.1 does not expose `errno.EWOULDBLOCK`.

The socket error handler was corrected to check `errno.EAGAIN`, matching the previously working XML v1 implementation.

After this correction, the application started and served the browser interface successfully.

**Result: PASS after compatibility correction**

### 3. JSON v2 Browser Rendering

Verified that the browser retrieved and displayed the JSON v2 configuration through `GET /api/config`.

| Test | Result |
|---|---|
| Application starts with JSON v2 | PASS |
| HTTP server listens on port 9090 | PASS |
| Browser loads configuration | PASS |
| Three fixed rooms displayed | PASS |
| Room names displayed correctly | PASS |
| TV, AVR, and streaming IP fields displayed | PASS |
| Expandable fundamental-action sections displayed | PASS |
| Room 1 fundamental-action editors expanded | PASS |
| Target, Method, and Path controls rendered | PASS |
| SERVICE mode disables saving | PASS |
| DEVICE mode enables saving | PASS |
| Clock status displayed | PASS |

The Room 1 editor displayed all 14 fundamental actions.

The initial action assignments were also displayed correctly, including AVR targets for volume and mute, streaming targets for navigation and playback, and TV as the power-toggle target.

Blank device IP addresses and action paths remained valid in the browser interface.

**Result: PASS**

### 4. Disposable Configuration Isolation

To avoid modifying the production JSON configuration during initial browser persistence testing, the Pico's local `main.py` was temporarily changed to load:

`/clonker/test_config_v2.json`

This was a local hardware-testing change only, not a permanent GitHub change.

After restarting the application, the browser displayed:

`ROOM-1 — Den Test 2`

This matched the existing disposable configuration rather than the production configuration, whose Room 1 name was `Den`.

The test confirmed that the browser was reading the intended disposable configuration.

**Result: PASS**

### 5. Browser-to-Flash Save

With the Pico in DEVICE mode and its filesystem writable, changed the Room 1 name in the browser:

`Den Test 2` → `Den Test 3`

Left all other configuration fields unchanged.

Clicked **Save Configuration**.

The browser displayed:

`Configuration saved successfully.`

The browser also completed its post-save configuration refresh.

**Result: PASS**

### 6. Flash Persistence and Backup Verification

Inspected the disposable configuration files directly through the CircuitPython REPL.

Observed:

| File | Room 1 name |
|---|---|
| `test_config_v2.json` | Den Test 3 |
| `test_config_v2.json.bak` | Den Test 2 |

This verified that the browser save installed the new primary configuration and preserved the previous configuration in the backup.

**Result: PASS**

### 7. Configuration Reload and Revision

Entering the REPL restarted the Python runtime, clearing the configuration engine's in-memory state.

An initial call to `cfg.current()` therefore reported:

`RuntimeError: Configuration not loaded`

This was not a persistence failure.

Explicitly loaded the disposable configuration again:

`cfg.load("/clonker/test_config_v2.json")`

Observed:

- **Loaded Room 1:** `Den Test 3`
- **Revision:** `9f3890e8`

The saved configuration successfully reloaded into RAM with a valid revision.

**Result: PASS**

### 8. Production Configuration Protection

All browser persistence writes in this test were directed to the disposable configuration file through the temporary `main.py` configuration path.

No intentional browser save was performed against the production JSON configuration.

The original XML v1 configuration files were not modified as part of this test.

The temporary configuration-path override must be removed after testing to restore normal production operation.

### 9. Not Yet Verified

The following remain outside this browser integration milestone:

- Browser rejection of stale configuration revisions.
- Browser no-change save behavior.
- Browser handling of invalid configuration values.
- Browser recovery after a failed or interrupted save.
- Browser save rejection in SERVICE/read-only mode beyond the disabled-button behavior.
- Browser editing and saving of nonempty HTTP action paths.
- Browser editing and saving of device IP addresses.
- Browser clock synchronization after the JSON v2 integration.
- Complete inspection of all action editors in Rooms 2 and 3.
- Full power-cycle persistence test after browser saving.
- Final production-path restoration and verification.
- Physical control dispatch of configured HTTP actions.

These items should be tested separately rather than assumed to work from the successful basic save.

### 10. Conclusion

The Clonker 10000 successfully completed its first end-to-end JSON v2 browser configuration persistence test on actual Raspberry Pi Pico 2 W hardware.

The verified path was:

**Browser → HTTP server → JSON v2 validation and persistence → Pico flash → backup → reload into RAM**

The disposable primary and backup contained the expected configuration generations, and the reloaded configuration produced a valid revision.

**Milestone: JSON v2 browser integration and basic flash persistence verified.**

**CLONK! The monster remembers.**
