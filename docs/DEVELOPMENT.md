# THE CLONKER 10000
## Development, Deployment & Testing

**Updated:** October 19, 2026  
**Platform:** Raspberry Pi Pico 2 W (RP2350)  
**Runtime:** CircuitPython 10.3.1  
**Development status:** JSON v2 configuration and browser Test Remote operational; outbound equipment control pending.

> The Clonker is built with modern software, vintage mechanical ambitions, and a development process carefully designed to minimize contact with an aging Windows laptop.

---

## 1. Purpose

This document describes how to develop, deploy, test, and troubleshoot The Clonker 10000.

It covers:

- The authoritative source repository.
- The iPad-first development workflow.
- Firmware deployment to the Pico.
- SERVICE/DEVICE filesystem ownership.
- CONFIG/RUN application modes.
- Private settings and Wi-Fi.
- Browser configuration and Test Remote testing.
- Serial diagnostics.
- Safe incremental development.
- Verification and regression testing.
- The next outbound HTTP development milestone.

This is a working development guide, not a record that every planned feature has been implemented.

For the current architecture, see [Architecture](ARCHITECTURE.md).

For dated test evidence, see [Configuration Testing](configuration-testing.md).

---

## 2. Source of Truth

The project repository is:

**https://github.com/djacobson/clonker-10000**

The intended development flow is:

```text
Working Copy on iPad
        |
        v
Edit repository files
        |
        v
Commit and push to GitHub
        |
        v
Windows GitHub Desktop
        |
        v
Fetch / Pull
        |
        v
Copy selected files to CIRCUITPY
        |
        v
Pico power cycle / application startup
        |
        v
Browser and REPL testing
        |
        v
Document observed results
```

### Repository versus running device

GitHub is the source of truth for maintained project code and documentation.

The actual Pico firmware and its runtime behavior are authoritative for what is currently deployed and working.

A file being committed to GitHub does not prove that it has been copied to the Pico.

A file being copied to the Pico does not prove that it has been executed successfully.

A successful browser response does not necessarily prove that the intended external device performed an action.

These are separate verification milestones.

### Historical files

The repository retains earlier XML v1 code and architectural material for historical reference.

Active configuration uses JSON v2.

The earlier ESP32-S3 hardware plan is also historical; the current firmware target is Pico 2 W.

Do not accidentally deploy legacy modules over the current implementation.

---

## 3. Development Equipment and Tools

### Primary development environment

**iPad**

Preferred tools:

- Working Copy for Git repository editing and commits.
- GitHub browser interface for reviewing repository history.
- Safari or another browser for Pico management testing.
- ChatGPT for code review, documentation, and incremental design work.

The iPad is the preferred place for routine development.

### Deployment computer

**Windows 10 Lenovo Yoga**

Used when necessary for USB filesystem deployment.

Relevant tools:

- GitHub Desktop.
- Windows File Explorer.
- USB connection to Pico.
- Browser-based CircuitPython serial console.

The Windows computer is primarily a deployment bridge, not the preferred editing environment.

### CircuitPython serial console

Current browser-based tool:

https://code.circuitpython.org/

Used for:

- REPL access.
- Startup logs.
- Exception diagnostics.
- Observing action-dispatch messages.
- Small, deliberate diagnostic experiments.

Connecting a serial console may interrupt the running application.

After connecting, use Ctrl+D when appropriate to soft-reload and restart the application with logging visible.

**Important:** Ctrl+D does not replace a full power cycle when changing SERVICE/DEVICE filesystem ownership.

---

## 4. Firmware Directory Structure

The active firmware lives under:

`firmware/`

Representative structure:

```text
firmware/
├── boot.py
├── code.py
├── DEPENDENCIES.md
└── clonker/
    ├── main.py
    ├── web.py
    ├── actions.py
    ├── device_config_v2.py
    ├── device_config.json
    ├── clock.py
    ├── logger.py
    ├── controls/
    │   ├── pins.py
    │   └── switches.py
    ├── www/
    │   ├── index.html
    │   └── remote.html
    └── legacy/
        ├── device_config.py
        └── device_config.xml
```

This is a functional map, not necessarily a complete listing of every file in the repository.

### Important modules

| File | Responsibility |
|---|---|
| `boot.py` | SERVICE/DEVICE filesystem selection |
| `code.py` | CircuitPython application entry point |
| `clonker/main.py` | Main loop and CONFIG server lifecycle |
| `clonker/web.py` | Browser HTTP server and API routing |
| `clonker/actions.py` | Shared fundamental action dispatcher |
| `clonker/device_config_v2.py` | JSON schema, validation, persistence, recovery |
| `clonker/device_config.json` | Configured rooms, endpoints, and actions |
| `clonker/clock.py` | Clock state and synchronization support |
| `clonker/logger.py` | Diagnostic logging |
| `clonker/controls/pins.py` | Developer-defined GPIO placeholders |
| `clonker/controls/switches.py` | CONFIG switch state abstraction |
| `clonker/www/index.html` | Configuration and management interface |
| `clonker/www/remote.html` | Browser Test Remote |

The `legacy/` directory is not part of the active JSON v2 application path.

---

## 5. Private Runtime Settings

Wi-Fi and environment-specific runtime settings belong in:

`settings.toml`

This file must remain private.

**Never commit credentials to GitHub.**

Do not overwrite the Pico's working `settings.toml` with an example file during routine deployment.

### Current development network

The documented development environment uses:

- Wi-Fi SSID: `jrtr`
- Reserved Pico IP: `192.168.50.12`
- Clonker HTTP port: `9090`

Management interface:

`http://192.168.50.12:9090/`

Browser Test Remote:

`http://192.168.50.12:9090/remote.html`

These are environment-specific development addresses, not universal defaults.

### CircuitPython Web Workflow

CircuitPython's built-in Web Workflow is disabled in the current development configuration.

Relevant private setting:

```toml
CIRCUITPY_WEB_API_PORT = 0
```

This was adopted after observed interference with Clonker's own HTTP service.

The exact underlying conflict was not conclusively established.

Clonker's application management server uses port 9090.

### Network security

The Clonker management interface does not currently implement application authentication.

Use it only on a trusted local network.

Do not expose port 9090 through router port forwarding or a public internet endpoint.

---

## 6. SERVICE / DEVICE Filesystem Modes

**Status: Implemented and tested.**

The Pico uses a GP17 jumper to determine filesystem write ownership at boot.

### Electrical connection

| Signal | Pico physical pin |
|---|---|
| GP17 | 22 |
| GND | 23 |

GP17 uses an internal pull-up.

### Mode behavior

| Jumper | Mode | Writable filesystem owner |
|---|---|---|
| Open | SERVICE (USB) | USB host |
| Grounded | DEVICE | Pico firmware |

### SERVICE (USB)

Use this mode to deploy or modify files from Windows.

The host can write CIRCUITPY.

The Pico application cannot persist configuration changes.

Browser configuration inspection and Test Remote access can still work if CONFIG is enabled.

### DEVICE

Use this mode when testing firmware-side configuration persistence.

The Pico application can write its filesystem.

The USB host sees CIRCUITPY as read-only.

Browser configuration saves can succeed when CONFIG is enabled and the submitted data is valid.

### Changing modes

**A full power cycle is required.**

Procedure:

1. Disconnect Pico power.
2. Open or ground the GP17 jumper.
3. Reconnect power.
4. Verify the boot message.
5. Confirm expected filesystem write ownership.

Do not change the jumper while the Pico is powered.

A Ctrl+D soft reload must not be treated as a substitute for the power cycle.

See [Operating Modes](OPERATING_MODES.md) for the full explanation.

---

## 7. CONFIG / RUN Application Modes

SERVICE/DEVICE and CONFIG/RUN are separate operating dimensions.

### CONFIG

Enables the application management HTTP server.

The browser can access:

- Configuration editor.
- Configuration API.
- Clock status and synchronization.
- Browser Test Remote.
- Action-dispatch test endpoint.

### RUN

Stops the application management HTTP listener.

The eventual physical remote should continue operating and sending outbound commands without exposing the management interface.

### Current implementation

The CONFIG/RUN listener lifecycle exists in `main.py`.

The physical CONFIG/RUN switch is not wired.

Current simulated switch state:

```python
_simulated_config = True
```

The application therefore starts in CONFIG mode during normal development.

A helper exists for changing the simulated state in RAM, but end-to-end physical mode switching is not yet tested.

### Intended normal modes

- **DEVICE + CONFIG:** Browser configuration and persistence.
- **DEVICE + RUN:** Normal physical remote operation, once implemented.
- **SERVICE + CONFIG:** USB maintenance with browser inspection and testing.
- **SERVICE + RUN:** Possible maintenance combination without browser management.

CONFIG/RUN must not be confused with the external equipment `power-toggle` action.

---

## 8. Standard Firmware Deployment Procedure

Use this procedure for routine code updates.

### Step 1 — Edit on iPad

Open the repository in Working Copy.

Edit the relevant files.

Review the changes before committing.

Prefer small, understandable changes rather than large simultaneous rewrites.

### Step 2 — Commit and push

Commit the changes in Working Copy.

Push to:

`djacobson/clonker-10000`

Verify that the intended commit appears on GitHub.

### Step 3 — Update the Windows checkout

On the Lenovo Yoga:

1. Open GitHub Desktop.
2. Fetch origin.
3. Pull the latest commit.
4. Confirm the local checkout contains the intended files.

Do not deploy from an outdated checkout.

### Step 4 — Enter SERVICE mode

1. Disconnect Pico power.
2. Open the GP17 jumper.
3. Reconnect the Pico to USB.
4. Confirm SERVICE mode.
5. Confirm that CIRCUITPY is host-writable.

### Step 5 — Copy updated files

Copy only the required files from the repository's `firmware/` tree to matching CIRCUITPY paths.

Examples:

| Repository path | Pico destination |
|---|---|
| `firmware/boot.py` | `/boot.py` |
| `firmware/code.py` | `/code.py` |
| `firmware/clonker/main.py` | `/clonker/main.py` |
| `firmware/clonker/web.py` | `/clonker/web.py` |
| `firmware/clonker/actions.py` | `/clonker/actions.py` |
| `firmware/clonker/device_config_v2.py` | `/clonker/device_config_v2.py` |
| `firmware/clonker/www/index.html` | `/clonker/www/index.html` |
| `firmware/clonker/www/remote.html` | `/clonker/www/remote.html` |

Preserve the directory structure.

### Important configuration precaution

Do not blindly overwrite:

`/clonker/device_config.json`

The Pico may contain newer configuration values and revisions than the repository copy.

Replacing the active configuration with an older GitHub version can discard browser edits or invalidate assumptions about the running configuration.

Before deliberately replacing it:

1. Preserve the current working file.
2. Confirm the intended schema.
3. Verify the target room and device endpoints.
4. Deploy compatible firmware and configuration together if necessary.
5. Test loading before making additional changes.

Never overwrite private `settings.toml` during routine deployment.

### Step 6 — Verify startup

Use the CircuitPython serial console as appropriate.

Check for:

- Expected SERVICE boot message.
- Wi-Fi connection.
- JSON v2 configuration load.
- Three configured rooms.
- Management server startup.
- No unexpected exceptions.

If the serial console interrupted the application, restart it appropriately.

### Step 7 — Browser smoke test

Open:

`http://192.168.50.12:9090/`

Confirm:

- Configuration page loads.
- Current rooms appear.
- Device endpoints are populated as expected.
- No unexpected `undefined` values appear.
- Clock and Test Remote controls are visible.
- Test Remote page opens.

At this stage, SERVICE mode is appropriate for read-only inspection and logging-only action tests.

Do not expect browser configuration saves to succeed in SERVICE mode.

---

## 9. DEVICE-Mode Configuration Testing

Use DEVICE mode for tests requiring Pico filesystem writes.

### Procedure

1. Preserve the current configuration.
2. Disconnect Pico power.
3. Ground GP17.
4. Reconnect power.
5. Confirm DEVICE mode in the boot log.
6. Open the management page.
7. Confirm the filesystem is writable.
8. Make a small, reversible configuration change.
9. Save and verify the reported revision.
10. Refresh and confirm the changed value is visible.

When testing persistence across reboot, perform a separate cold power-cycle check and record the result.

### Revision conflict test

The previously tested two-tab scenario is:

1. Open the configuration page in Tab A.
2. Open the same page in Tab B.
3. Save a change from Tab A.
4. Attempt to save stale data from Tab B.
5. Confirm the revision mismatch is rejected.
6. Refresh Tab B.
7. Verify that the current revision is loaded.

Do not bypass revision protection merely to make a stale save succeed.

### No-change save test

Saving an unchanged configuration should report no change and avoid an unnecessary flash write.

This behavior has been tested in the earlier configuration milestone.

### Backup behavior

The JSON v2 engine supports rotating backups and validated recovery paths.

Selected backup and recovery scenarios have been tested.

Do not claim that every interrupted-write or power-loss failure scenario has been verified.

See [Configuration & Recovery](CONFIGURATION.md).

---

## 10. Browser Test Remote

**Status: Implemented and tested as a logging-only prototype.**

The browser Test Remote is served from:

`/clonker/www/remote.html`

URL:

`http://192.168.50.12:9090/remote.html`

It provides:

- Room selection.
- Volume controls.
- Mute.
- Directional navigation.
- Select.
- Back and Home.
- Playback controls.
- Power Toggle.
- Status feedback.
- An illustrative custom-action selector.

### Action endpoint

The browser invokes:

```text
POST /api/action?room=room-1&action=volume-up
```

The endpoint validates the room and fundamental action identifiers.

It calls:

```python
actions.dispatch(room_id, action_id)
```

### Current dispatcher

`firmware/clonker/actions.py`

The current dispatcher:

- Validates the room ID.
- Validates the action ID.
- Resolves the configured room.
- Resolves the target device endpoint.
- Inspects configured command paths.
- Reports whether the action is configured.
- Logs a diagnostic message.
- Returns a JSON result.

It does **not** currently send HTTP commands to external equipment.

### Example response

Representative structure:

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

The exact response reflects the current configuration.

`ok: true` and `status: "stub"` mean the request was processed by the prototype dispatcher.

They do not mean an external device received a command.

### Verified milestone

On October 19, 2026, all fourteen fundamental browser action buttons were exercised successfully through the stub dispatcher.

This verified the browser-to-Pico request path and logging behavior.

It did not verify outbound AV equipment control.

### Custom actions

The browser's custom-action dropdown is illustrative.

Custom-action execution is not implemented.

Do not report a custom action as operational merely because its name appears in the UI.

---

## 11. Current JSON v2 Configuration

Active file:

`/clonker/device_config.json`

Configuration engine:

`firmware/clonker/device_config_v2.py`

### Room structure

Three fixed room IDs:

- `room-1` — Den.
- `room-2` — Sunroom.
- `room-3` — Placeholder.

Room names are user-editable.

Each room may contain:

- `tv`
- `avr`
- `streaming`

Each device endpoint uses an IPv4 address with an optional HTTP port.

### Fundamental actions

Fourteen action IDs are fixed by firmware.

Ordinary actions use:

```json
{
  "target": "avr",
  "method": "GET",
  "path": "/goform/formiPhoneAppDirect.xml?MVUP"
}
```

Toggle actions use:

```json
{
  "target": "avr",
  "method": "GET",
  "on_path": "/goform/formiPhoneAppDirect.xml?MUON",
  "off_path": "/goform/formiPhoneAppDirect.xml?MUOFF"
}
```

These are examples of command definitions, not evidence that the current dispatcher has transmitted them.

### Toggle implementation boundary

The schema supports separate ON/OFF paths for:

- `mute-toggle`
- `power-toggle`

The dispatcher does not yet select or alternate those paths.

The agreed future behavior is RAM-only command history, independently maintained per room and toggle action.

No actual device-state polling is currently implemented.

### No-op behavior

A blank command path or missing device endpoint is allowed by configuration.

Future outbound dispatch should treat these as intentional no-ops.

No-op behavior must not falsely report a device command as sent.

---

## 12. Debugging and Diagnostic Practices

### General rule

**One small change. One clear test. One recorded result.**

Avoid changing firmware, browser JavaScript, GPIO assignments, and configuration schema simultaneously unless the change genuinely requires coordination.

### Useful evidence

When reporting a failure, capture:

- Exact firmware commit or changed files.
- SERVICE/DEVICE jumper position.
- CONFIG/RUN state.
- Browser URL and operation.
- Relevant REPL output.
- HTTP response or displayed error.
- Whether the Pico restarted.
- Whether the active configuration changed.
- Whether the issue reproduces after a cold power cycle.

### Expected interruption

A `KeyboardInterrupt` after manually stopping the application is not necessarily a firmware failure.

Distinguish deliberate interruption from an unexpected exception.

### Browser caching

The HTTP server currently sends:

```text
Cache-Control: no-store
```

Even so, verify that the deployed HTML and JavaScript match the expected repository version before diagnosing a supposed firmware problem.

### Stale configuration files

Earlier development exposed problems caused by stale or legacy configuration files.

When configuration values appear incorrect:

1. Confirm which JSON file the firmware loads.
2. Confirm the Pico has the expected deployed file.
3. Check that legacy modules are not accidentally being used.
4. Inspect current RAM configuration through the browser.
5. Avoid modifying the production JSON file behind the running application's back.

### Storage errors

Do not equate a valid JSON payload with a successful persistent save.

A complete persistence test should distinguish:

- Schema validation.
- Revision validation.
- Filesystem writability.
- Primary-file write success.
- Backup behavior.
- Active RAM publication.
- Persistence after reboot.

Record which stages were actually observed.

---

## 13. Testing Status Vocabulary

Use these labels consistently.

### Verified

Observed in the actual Pico REPL, browser, or physical equipment.

Example:

**Verified:** Browser Test Remote invokes the logging-only dispatcher.

### Implemented, not fully verified

Present in current source but not comprehensively exercised on hardware.

Example:

**Implemented, not fully verified:** All CONFIG/RUN listener transition and network failure paths.

### Planned

Design intent that has not yet been implemented.

Example:

**Planned:** Physical volume encoder sends generic volume actions.

### Historical

Earlier implementation or testing that is no longer the active baseline.

Example:

**Historical:** XML v1 configuration system.

### Important distinctions

- Source code is not proof of deployment.
- Deployment is not proof of execution.
- An HTTP success response is not proof of physical equipment state.
- A simulated action is not a real device action.
- A configuration field is not proof that the behavior it describes exists.

These distinctions should be preserved in documentation and development discussions.

---

## 14. Current Verification Snapshot

**As of October 19, 2026**

### Verified on the Pico

- CircuitPython 10.3.1 application startup.
- Wi-Fi connectivity.
- GP17 SERVICE/DEVICE selection.
- JSON v2 configuration loading.
- Browser configuration interface.
- DEVICE-mode configuration saving.
- Revision conflict handling.
- No-change detection.
- Selected backup and recovery scenarios.
- SERVICE-mode browser save protection.
- Browser Test Remote loading.
- All fourteen fundamental browser actions reaching the logging-only dispatcher.

### Implemented but not comprehensively verified

- Every possible malformed HTTP request case.
- All HTTP client timeout and cleanup conditions.
- All CONFIG/RUN listener transitions.
- Every configuration recovery failure scenario.
- Interrupted-write and power-loss behavior.

### Not yet implemented

- Outbound HTTP commands to Denon, Roku, or LG equipment.
- RAM toggle-state selection.
- Physical buttons and rotary encoders.
- Physical room selector.
- Physical CONFIG/RUN switch.
- Custom-action execution.
- OLED integration.
- Audible feedback.
- Final enclosure and power design.

Historical tests and dated results are maintained in `configuration-testing.md`.

---

## 15. Next Milestone: Real Outbound HTTP Actions

The next major development chapter connects the working browser Test Remote to actual AV equipment commands.

The architecture should remain small and understandable.

### Intended request path

```text
Browser Test Remote
        |
        v
POST /api/action
        |
        v
actions.dispatch()
        |
        v
Current validated JSON config
        |
        v
Minimal outbound HTTP transport
        |
        v
Denon / Roku / future devices
```

### Recommended development sequence

1. Review current firmware and dependencies.
2. Define a minimal HTTP transport suitable for CircuitPython.
3. Add bounded connection and response timeouts.
4. Support the configured GET and POST methods.
5. Start with one low-risk Denon or Roku command.
6. Confirm both HTTP response and physical equipment behavior.
7. Implement ordinary fundamental action dispatch.
8. Verify Den and Sunroom independently.
9. Test missing endpoint and blank-path no-ops.
10. Implement independent RAM toggle history.
11. Test Denon mute ON/OFF behavior.
12. Evaluate power and HDMI-CEC behavior separately.
13. Measure responsiveness and resource usage.
14. Record actual tests before expanding functionality.

### Toggle design

The agreed initial behavior is:

- Track last successful command direction per room and toggle action.
- Unknown at boot means attempt ON first.
- Alternate only after successful command execution.
- Do not advance after a failed request or no-op.
- Allow identical ON/OFF paths for native device toggles.
- Do not persist toggle history to flash.
- Do not claim this history represents actual device state.

Actual device state may differ because of other remotes, HDMI-CEC, or manual controls.

### Safety

Real HTTP actions may change receiver volume, mute state, or equipment power.

Start with a safe listening level.

Test one action at a time.

Avoid power and group-control commands until ordinary actions are reliable.

### Out of scope for the first transport milestone

- Complex macros.
- Device-state polling.
- Automatic retries and queues.
- Connection pooling without measured need.
- Physical GPIO integration.
- OLED and sound effects.
- Final enclosure construction.

The first goal is to prove one reliable network command from the existing browser action path.

---

## 16. Documentation and Test Record Maintenance

After each meaningful milestone:

1. Record the date.
2. Identify changed files.
3. State what was tested.
4. Include the actual observed result.
5. Note any failures or unresolved questions.
6. Distinguish tests from proposed behavior.
7. Update architecture documentation when implementation changes.
8. Preserve historical test records.

### Documentation references

- [Architecture](ARCHITECTURE.md)
- [Configuration & Recovery](CONFIGURATION.md)
- [Firmware, HTTP & Clock](FIRMWARE_NETWORK.md)
- [Operating Modes](OPERATING_MODES.md)
- [Hardware & Physical Controls](HARDWARE_CONTROLS.md)
- [Configuration Testing](configuration-testing.md)
- [Chapter 2 Handoff](CHAPTER_2_HANDOFF.md)

### Documentation philosophy

The documents should make it possible to start a fresh development conversation without reconstructing the entire project's history.

Current firmware is authoritative for behavior.

Current architecture documents describe intended structure and known limitations.

Dated test records preserve what was actually observed.

Historical files remain historical.

---

## 17. Development Principles

- Prefer simple, readable code.
- Preserve useful comments and indentation.
- Keep firmware modules focused.
- Keep device-specific commands in configuration.
- Use one shared action dispatcher for browser and future physical controls.
- Avoid premature caching and networking optimizations.
- Keep the cooperative main loop responsive.
- Protect persistent configuration data.
- Minimize unnecessary flash writes.
- Test changes incrementally.
- Prefer iPad development whenever practical.
- Use Windows only when necessary.
- Never confuse a successful stub test with a working remote.

And finally:

**Do not spend three hours engineering a solution to save four seconds unless the resulting mechanism makes an exceptionally satisfying CLONK.**

Actually, scratch that last part. That's probably the entire reason this project exists.

---

**THE CLONKER 10000**

*Designed by David Jacobson.*

**CLONK! ⚡🔩**
