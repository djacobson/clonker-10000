# Clonker 10000 — Configuration Test Record

**Status:** Configuration v1 core operational  
**Test date:** October 16, 2026  
**Hardware:** Raspberry Pi Pico 2 W  
**Firmware:** CircuitPython 10.3.1

## Verified Capabilities

| Capability | Status |
|—|—|
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
|—|—|
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
|—|—|—|
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
