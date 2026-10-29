# THE CLONKER 10000
## Development, Deployment & Testing

**Updated:** October 28, 2026  
**Platform:** Raspberry Pi Pico 2 W (RP2350) / CircuitPython 10.3.1  
**Current baseline:** Chapter 5 — Config v4, fundamental/custom actions, cooperative compound execution, and empty physical GPIO scheduler shell operational  
**Repository:** https://github.com/djacobson/clonker-10000

> Built with modern software, vintage mechanical ambitions, and a development process carefully designed to minimize contact with an aging Windows laptop.

---

## 1. Purpose

This is the **working development and deployment guide** for The Clonker 10000. It explains how to edit, deploy, operate, test, troubleshoot, and document the running firmware. It is not a complete schema specification or a chronological development diary.

Use the other references for their respective jobs:

- [Architecture](ARCHITECTURE.md) — component responsibilities, boundaries, and design rationale.
- [Configuration & Recovery](CONFIGURATION.md) — authoritative Clonker Config v4 schema, validation, revisions, persistence, and recovery.
- [Firmware, HTTP & Clock](FIRMWARE_NETWORK.md) — current scheduler, queue, network behavior, APIs, and transport limits.
- [Operating Modes](OPERATING_MODES.md) — filesystem ownership and application modes.
- [Hardware & Controls](HARDWARE_CONTROLS.md) — physical input plans and component decisions.
- [Development History](DEVELOPMENT_HISTORY.md) — dated experiments, milestones, and observed results.

**Development rule:** A repository commit, a successful deployment, an accepted HTTP request, an HTTP 200 response, and a physical equipment change are **five different kinds of evidence**.

## 2. Source of truth and working workflow

The public repository is `djacobson/clonker-10000`.

```text
Working Copy on iPad
        |
        v
Edit and review a focused change
        |
        v
Commit and push to GitHub
        |
        v
Windows GitHub Desktop: fetch / pull
        |
        v
Copy changed firmware files to CIRCUITPY
        |
        v
Restart or power-cycle the Pico as appropriate
        |
        v
Inspect REPL logs and browser behavior
        |
        v
Verify actual equipment response when relevant
        |
        v
Record evidence and update documentation
```

GitHub is authoritative for **maintained source and documentation**. The deployed Pico is authoritative for **what is actually running**. Neither automatically proves the other is current.

Prefer one meaningful change and one clear test at a time. Preserve useful code comments, avoid speculative refactors, and do not mix unrelated hardware, browser, networking, and schema changes in a single experiment.

### 2.1 Development equipment

**iPad first:** Working Copy for repository editing and commits; browser for GitHub review and Clonker's configuration and Test Remote interfaces; ChatGPT for review and documentation.

**Windows Lenovo Yoga:** GitHub Desktop, File Explorer, USB connection, and the CircuitPython serial console when deployment or low-level debugging requires them. The Windows machine is primarily a deployment bridge.

**CircuitPython console:** https://code.circuitpython.org/ can provide REPL access and startup/exception logs. Connecting or interrupting the console can stop the running application. Use Ctrl+D when a soft reload is appropriate; do **not** treat it as a substitute for a full power cycle when changing boot-time filesystem ownership.

### 2.2 Historical implementations

The repository retains earlier XML configuration code and architecture notes. The older ESP32-S3 hardware plan is also historical. The active target is the Pico 2 W, and the active configuration schema is **Clonker Config v4** serialized as JSON.

The file `device_config_v2.py` retains its historical name; its active constant is `CONFIG_VERSION = 4`. Do not rename it merely to match the schema version, or accidentally deploy legacy code over the current implementation.

---

## 3. Current firmware layout

The repository's `firmware/` tree is copied to corresponding paths on CIRCUITPY. Repository-relative paths are **not** runtime absolute paths.

| Repository path | Runtime responsibility |
|---|---|
| `firmware/boot.py` | GP17 boot-time filesystem ownership |
| `firmware/code.py` | CircuitPython application entry point |
| `firmware/clonker/main.py` | Startup and cooperative scheduling |
| `firmware/clonker/device_config_v2.py` | Config v4 validation, RAM state, revisions, persistence, recovery |
| `firmware/clonker/device_config.json` | Repository configuration example / deployable configuration |
| `firmware/clonker/actions.py` | Fundamental/custom dispatch, Dumb Queue™, execution and failure policy |
| `firmware/clonker/net/web.py` | CONFIG-mode inbound HTTP management service |
| `firmware/clonker/net/http_transport.py` | Outbound bounded blocking HTTP GET/POST |
| `firmware/clonker/www/index.html` | Configuration editor and clock UI |
| `firmware/clonker/www/remote.html` | Browser Test Remote, including custom-action selector |
| `firmware/clonker/controls/physical.py` | Optional physical GPIO initialization and priority-one polling shell |
| `firmware/clonker/controls/switches.py` | Simulated CONFIG/RUN state; future physical input |
| `firmware/clonker/controls/pins.py` | GPIO definitions |
| `firmware/clonker/system/clock.py` | Clock reference and timestamps |
| `firmware/clonker/system/logger.py` | Serial diagnostics |

Preserve Python package directories and their `__init__.py` files. When a module moves, remove obsolete copies from the Pico so imports cannot resolve against stale files.

### 3.1 Runtime configuration is not a disposable build artifact

The Pico's active file is:

`/clonker/device_config.json`

It may contain newer browser edits and a newer revision than the checked-in repository copy. **Never blindly overwrite it during a firmware deployment.** Back it up first, verify schema compatibility, and make any deliberate replacement separately from routine source updates.

The readable two-room example is maintained at [`samples/device_config_roku_denon_sample.json`](../samples/device_config_roku_denon_sample.json). It is an example, not an instruction to overwrite a running device.

---

## 4. Private settings and development network

Environment-specific Wi-Fi credentials and settings belong in the Pico's private `settings.toml`. **Never commit credentials**, and do not replace a working `settings.toml` with a repository example during routine deployment.

Documented development addresses:

| Service | Development address |
|---|---|
| Pico management UI | `http://192.168.50.12:9090/` |
| Browser Test Remote | `http://192.168.50.12:9090/remote.html` |
| Den AVR-X3700H | `192.168.50.44:8080` |
| Den Roku | `192.168.50.43:8060` |
| Sunroom AVR-X1800H | `192.168.50.40:8080` |
| Sunroom Roku | `192.168.50.28:8060` |

These are **specific to the development LAN**, not universal firmware defaults. Endpoint configuration is authoritative for the running device.

CircuitPython's built-in Web Workflow was disabled in this development environment after observed interference with Clonker's own management service. The private setting is:

```toml
CIRCUITPY_WEB_API_PORT = 0
```

The underlying conflict was not conclusively identified. Clonker's own inbound management server uses port **9090**.

**Security:** The management interface has no application-level authentication. Use it on a trusted LAN; do not expose port 9090 through public port forwarding.

---

## 5. Two independent operating-mode dimensions

### 5.1 SERVICE / DEVICE — filesystem ownership

The boot-time GP17 jumper controls who may write CIRCUITPY:

| GP17 jumper | Mode | Writable owner |
|---|---|---|
| Open | SERVICE (USB) | USB host |
| Grounded | DEVICE | Pico firmware |

GP17 is physical Pico pin **22**; the adjacent ground connection is pin **23**. GP17 uses an internal pull-up.

**Change procedure:** Disconnect power, change the jumper, reconnect power, and verify the boot mode. Do not move the jumper while powered. A Ctrl+D soft reload does not reliably reselect boot-time filesystem ownership.

SERVICE mode is for USB deployment and host-side file maintenance. Browser inspection and action testing can still be available if CONFIG is enabled, but browser configuration saves must be rejected when the filesystem is read-only to firmware.

DEVICE mode permits validated browser configuration saves and recovery writes. The USB host sees the filesystem as read-only.

### 5.2 CONFIG / RUN — application management

CONFIG/RUN is independent of SERVICE/DEVICE:

- **CONFIG:** Starts the inbound HTTP management listener, configuration editor, Test Remote, and clock API. Queued action execution continues.
- **RUN:** Stops the management listener. The shared action queue still operates; physical inputs will eventually supply actions.

The application-mode logic exists in `main.py`; the physical CONFIG/RUN switch is **not yet wired**. Development currently uses a simulated switch state. CONFIG/RUN is not an HTTP action and is not the same as an AV device's power toggle.

The intended normal physical-remote combination is **DEVICE + RUN**. Browser configuration with persistence uses **DEVICE + CONFIG**.

See [Operating Modes](OPERATING_MODES.md) before changing hardware or mode behavior.

---

## 6. Standard firmware deployment

Use this procedure for ordinary source changes. Do not combine it with unplanned configuration migration.

1. **Edit on iPad.** Review the diff in Working Copy; keep changes focused.
2. **Commit and push.** Confirm the intended files appear on GitHub.
3. **Update Windows checkout.** In GitHub Desktop, fetch and pull; verify the local checkout is current.
4. **Enter SERVICE mode.** Power down, open GP17, reconnect, and verify host-writable CIRCUITPY.
5. **Copy only changed files.** Preserve the `clonker/` package tree and its `__init__.py` files. Do not overwrite `settings.toml` or the active `device_config.json` by default.
6. **Verify deployed files.** Confirm file names, paths, and intended versions on CIRCUITPY. Remove stale module copies when appropriate.
7. **Restart appropriately.** Use a soft reload for suitable code changes; perform a full power cycle for boot-time mode changes or when the test explicitly requires cold startup.
8. **Inspect serial logs.** Confirm Wi-Fi, Config v4 loading, configured rooms, expected CONFIG/RUN behavior, and no unexpected exceptions.
9. **Smoke-test the browser.** Open the configuration editor and Test Remote in CONFIG mode; confirm actual current data, not stale UI assets.
10. **Test the changed behavior.** Verify queued actions, HTTP results, and equipment behavior as relevant. Record observations.

### 6.1 Typical copy map

| From repository | To CIRCUITPY |
|---|---|
| `firmware/boot.py` | `/boot.py` |
| `firmware/code.py` | `/code.py` |
| `firmware/clonker/main.py` | `/clonker/main.py` |
| `firmware/clonker/actions.py` | `/clonker/actions.py` |
| `firmware/clonker/device_config_v2.py` | `/clonker/device_config_v2.py` |
| `firmware/clonker/net/web.py` | `/clonker/net/web.py` |
| `firmware/clonker/net/http_transport.py` | `/clonker/net/http_transport.py` |
| `firmware/clonker/www/index.html` | `/clonker/www/index.html` |
| `firmware/clonker/www/remote.html` | `/clonker/www/remote.html` |

### 6.2 Configuration replacement requires a separate decision

Before deliberately replacing `/clonker/device_config.json`:

1. Preserve the current Pico file and relevant backups.
2. Confirm that the replacement is **Clonker Config v4** and within the configured size limit.
3. Confirm room identities, device addresses, and custom actions.
4. Ensure the firmware and configuration schema are compatible.
5. Perform a cold-start load check and inspect the browser configuration.
6. Confirm any expected revision changes and persistence behavior.

Do not confuse a successful copy with successful validation, recovery, or persistence.

---

## 7. DEVICE-mode configuration regression testing

Use **DEVICE + CONFIG** for tests requiring writes from the Pico.

### 7.1 Basic edit/save/reload

1. Preserve the working configuration.
2. Power down, ground GP17, and cold-start in DEVICE mode.
3. Confirm firmware filesystem writability in the browser.
4. Make a small reversible change, then Save.
5. Verify the response reports the appropriate revision and whether the file changed.
6. Refresh the editor and confirm the saved value.
7. Cold power-cycle when testing persistence and verify the value again.
8. Restore the intended setting if the edit was only a test.

### 7.2 Revision-conflict regression

1. Open the editor in Tab A and Tab B.
2. Save a change from Tab A.
3. Attempt to save stale data from Tab B.
4. Confirm the stale save is rejected rather than silently overwriting the newer revision.
5. Refresh Tab B and verify it loads the current configuration.

### 7.3 No-change and backup checks

Saving unchanged data should report no change without unnecessary flash writes. A changed successful save clears pending action work; an unchanged save should not need to do so.

The configuration engine validates saves, checks revisions and disk consistency, writes verified temporary content, and maintains rotating backups. **These safeguards are not a guarantee against every sudden-power-loss failure.** Test recovery separately and record exactly which failure scenarios were exercised.

Do not delete backup files casually. See [Configuration & Recovery](CONFIGURATION.md) for authoritative file naming and recovery details.

### 7.4 Schema regression checklist

- Clonker Config v4 version and required root keys.
- One to three configured rooms with supported stable IDs.
- Generic built-in slots `device-1`, `device-2`, and `device-3`.
- Fourteen fundamental actions per room.
- Optional custom actions with stable IDs and ordered steps.
- Valid target, method, path, and `wait_after_ms` fields.
- Custom-action and step-count limits, wait limits, and total JSON byte limit.
- Missing or malformed fields rejected without corrupting active RAM configuration.
- Revision conflicts and filesystem read-only saves rejected.

Do not replicate the entire schema here; use [Configuration & Recovery](CONFIGURATION.md) as the specification.

---

## 8. Browser Test Remote and real action execution

**Status:** Operational for fundamental and custom actions. It is **not** a logging-only stub.

Open `http://192.168.50.12:9090/remote.html` while CONFIG is enabled.

The page supports room selection, fourteen fixed fundamental controls, and selection/execution of configured custom actions for the selected room. Room and action identifiers are submitted through the shared action endpoint:

```text
POST /api/action?room=room-1&action=volume-up
```

The server calls `actions.dispatch(room_id, action_id)`. A successful response reports **queue acceptance**, typically `status: "queued"`; it does not wait for outbound network completion.

```json
{
  "ok": true,
  "status": "queued",
  "room": "room-1",
  "room_name": "Den",
  "action": "volume-up",
  "configured": true,
  "queue_depth": 1,
  "message": "QUEUED: Den / volume-up (depth 1)"
}
```

This is an **illustrative** response. Names, queue depth, and configured state depend on the running configuration.

### 8.1 Fundamental actions

The dispatcher validates the room and action, admits an eligible task, and resolves the current configuration when the task executes. Configured ordinary actions use outbound HTTP GET/POST. Missing endpoints or blank ordinary paths are intentional logged no-ops.

**Power and mute toggles are operational:** the dispatcher selects configured ON/OFF paths using independent, volatile histories for each room and toggle action. Direction advances only after successful HTTP execution. Changed configuration saves reset all histories. October 27, 2026 bench tests verified Sunroom mute and power toggles, configuration-reset behavior, independent Den/Sunroom histories, failed-request direction preservation, and repeatable no-ops for blank paths and missing endpoints. This is command-direction history, not authoritative equipment-state detection.

### 8.2 Custom and compound actions

Clonker Config v4 supports up to **16 custom actions per room**, each with **1–16 ordered steps**. Steps use a built-in destination, GET/POST, path, and `wait_after_ms`.

A custom action is admitted as **one queue entry**. Each successful step sends one HTTP command. If another step remains, the task is requeued with a due time calculated **after** the completed HTTP request. Other eligible work can run during that wait. One `actions.poll()` executes at most one eligible HTTP command.

A verified Sunroom custom action:

```text
Roku: POST /keypress/Home
    -> HTTP 200
Wait 3000 ms cooperatively
Denon: GET /goform/formiPhoneAppDirect.xml?MSQUICK1
    -> HTTP 200
CUSTOM COMPLETE
```

The custom-action engine does **not** provide nested macros, branching, rollback, automatic retries, or a second execution thread. Custom actions currently target the three built-in device slots, not user-defined custom devices.

### 8.3 Queue and error semantics

- Queue capacity is **128 entries**.
- Future-dated work does not block an unrelated immediately eligible action.
- A failed outbound execution clears the remaining queue; the Clonker remains available for later commands.
- Configuration changes clear pending work.
- HTTP 2xx means an HTTP-level acknowledgment, **not guaranteed physical equipment state**.
- Outbound HTTP is bounded but synchronous; it temporarily pauses the cooperative scheduler.

See [Firmware, HTTP & Clock](FIRMWARE_NETWORK.md) for exact transport and scheduler behavior.

---

## 9. Verification snapshot — October 28, 2026

### 9.1 Implemented and exercised

- Pico 2 W / CircuitPython 10.3.1 startup and Wi-Fi connectivity.
- GP17 SERVICE/DEVICE selection and firmware-side DEVICE persistence.
- Config v4 loading, browser editing, revision protection, verified saves, and selected recovery scenarios.
- Optional configured rooms and generic built-in device identifiers.
- Browser Test Remote and management API on port 9090.
- Shared Dumb Queue™ admission, capacity, scheduling, and real outbound execution.
- Denon volume and Roku navigation through HTTP GET/POST.
- Configured custom actions and cooperative compound steps using the shared queue.
- Verified Sunroom Roku Home → 3000 ms wait → Denon Quick Select 1 sequence.
- Chapter 5 physical-control scheduler shell: verified startup with `PHYSICAL_CONTROLS_ENABLED` both disabled and enabled, CONFIG listener operational, and Sunroom Home returning HTTP 200 in both modes (October 28, 2026).
 
### 9.2 Implemented but not exhaustively tested

- Interrupted-write and sudden-power-loss recovery paths.
- Every malformed inbound HTTP request and network cleanup case.
- Sustained queue pressure and extended Wi-Fi failure scenarios.
- Long-duration monotonic scheduling and memory stability.
- Physical input responsiveness during synchronous outbound HTTP.
- All possible CONFIG/RUN listener transitions and operational combinations.

### 9.3 Not yet implemented

- Physical buttons and rotary encoders connected to action dispatch.
- Physical CONFIG/RUN switch and room selector.
- User-defined custom device slots beyond `device-1` through `device-3`.
- Apple TV discovery, pairing, authentication, and command protocol.
- OLED feedback, audible CLONK, battery management, and final enclosure.
- Specialized volume-encoder event accumulation, acceleration, or transport optimization.

These lists are a development snapshot, **not** a certification or exhaustive regression report. Preserve dated evidence in [Development History](DEVELOPMENT_HISTORY.md).

---

## 10. Debugging and diagnostic discipline

**One small change. One clear test. One recorded result.**

When reporting a failure, capture the source commit or changed files, actual deployed version, jumper and application modes, browser URL and request, relevant REPL logs, response/error, and observed equipment behavior. Note whether a cold power cycle changes the result.

### 10.1 Common traps

| Symptom | First checks |
|---|---|
| Browser page stale | Confirm current `index.html` or `remote.html` was deployed; refresh and inspect version/content |
| Editor loads but Save fails | Check SERVICE/DEVICE ownership, revision conflict, schema validation, and filesystem status |
| Action reports `queued` but nothing happens | Check queue logs, configured endpoint/path, later execution result, and equipment state |
| Toggle does not change equipment state | Check selected room, ON/OFF path, endpoint, HTTP execution result, and volatile direction history; HTTP success does not prove physical equipment state |
| Fundamental action reports `NO-OP` | Blank path or endpoint may be intentional |
| Custom action fails | Check every destination endpoint and step; one failure clears pending queue work |
| Browser feels slow | Consider the single-client inbound listener, silent connections, and blocking outbound calls |
| Wrong device responds | Confirm active Pico configuration, selected room, generic device slot, and command path |
| Changes vanish after reboot | Confirm DEVICE mode, save success, revision, active file, and cold-start recovery logs |
| Unexpected import behavior | Check stale or duplicate Pico modules and preserve package `__init__.py` files |

A deliberate `KeyboardInterrupt` from stopping the application is not necessarily a firmware crash.

The inbound HTTP service sends `Cache-Control: no-store`, but still verify deployed assets when debugging browser behavior.

### 10.2 Understand HTTP success

The outbound transport reads the HTTP status line and accepts 2xx results. It does **not** parse a device's response body or prove the receiver, television, or streamer changed state. An accepted queue request proves even less: it only proves admission.

For physical behavior claims, observe the equipment directly. For failure claims, capture the relevant serial logs and distinguish expected unreachable-endpoint tests from regressions.

### 10.3 Preserve configuration during diagnosis

Avoid editing the JSON file behind the running application's back. Prefer browser changes through the validated save path in DEVICE mode. Before recovery experiments, preserve the primary file and backups. Never casually delete the current configuration or private settings while troubleshooting.

---

## 11. Testing vocabulary

Use precise labels in documentation and conversation:

- **Verified on hardware:** Observed on the actual Pico, browser, and/or external equipment, with the observation stated.
- **Implemented, not exhaustively verified:** Code exists but some relevant conditions remain untested.
- **Planned:** An objective or design proposal, not working firmware.
- **Historical:** An earlier implementation, test, or decision superseded by the current baseline.
- **Deferred:** Intentionally not active, even if some configuration or UI support already exists.

A browser stub from October 19 was **historical**. The current browser action pipeline is operational. A future Apple TV adapter remains **planned**. Runtime power/mute direction execution, negative-path direction preservation, and cooperative custom-action interleaving were bench-tested October 27, 2026. Broader stress and physical-input verification remain incomplete.

Never turn an intended design into a success claim just because its schema fields or UI controls exist.

---

## 12. Next development work

The working Config v4 baseline should be protected while proceeding in measured steps.

### 12.1 Small refinements

- Expand queue-capacity, malformed-request, prolonged-network-failure, and long-uptime regression coverage where useful.
- Revisit Test Remote selection persistence if a reproducible issue appears with multiple custom actions in one room.
- Avoid speculative performance changes without measurements.

### 12.2 Physical-control integration

**Completed and Pico-tested October 28–29, 2026:**

- Optional physical-control initialization and cooperative GPIO polling.
- GP2 momentary button input, debounce, and press/release event logging.
- GP17 physical SERVICE (USB)/DEVICE boot-mode switch.
- GP18 guarded CONFIG/RUN application-mode switch, including live management-listener transitions without reboot.
- Browser and network-action smoke tests with physical-control polling enabled.

**Next implementation steps:**

1. Wire and test the physical room selector.
2. Establish reliable selected-room context for physical input events.
3. Connect GP2 power-button presses to the existing room-specific `power-toggle` dispatcher.
4. Verify real equipment response, debounce behavior, and repeated presses.
5. Add navigation, Back, and Home controls incrementally.
6. Integrate the Bourns custom-action selector encoder.
7. Electrically verify the Grayhill volume encoder before implementing volume steps.
8. Measure physical-input responsiveness during outbound HTTP requests and compound waits.

Keep GPIO handlers device-independent. All physical actions must use the same dispatcher and Dumb Queue™ as the browser Test Remote.

See [Hardware & Physical Controls](HARDWARE_CONTROLS.md) for verified GPIO assignments, component status, and remaining mechanical decisions.

### 12.3 Deferred action and protocol capabilities

- Add user-defined custom device slots only when the working baseline and requirements justify the extension.
- Pursue Apple TV compatibility as an explicit objective, recognizing that discovery, pairing, authentication, and session management may require an adapter beyond stateless HTTP GET/POST.
- Continue OLED, audio feedback, power, and enclosure work according to hardware readiness.

Do not create a separate macro executor or a general-purpose home automation framework merely because the Clonker can run a command sequence.

---

## 13. Documentation and handoff discipline

After a meaningful change:

1. Record the date and changed source files.
2. State the test environment and deployed firmware version when known.
3. Describe what was actually tested and what was observed.
4. Note failures, deferred items, and untested assumptions.
5. Update the current reference document if runtime behavior changed.
6. Append dated evidence to [Development History](DEVELOPMENT_HISTORY.md) rather than rewriting old milestones.
7. Keep cross-references accurate and avoid duplicating entire schema or transport specifications across documents.

A new development conversation should be able to reconstruct the working baseline by reading the current repository documentation and relevant firmware, without relying on undocumented memory or inventing results.

### Reference map

- [Architecture](ARCHITECTURE.md)
- [Configuration & Recovery](CONFIGURATION.md)
- [Firmware, HTTP & Clock](FIRMWARE_NETWORK.md)
- [Operating Modes](OPERATING_MODES.md)
- [Hardware & Physical Controls](HARDWARE_CONTROLS.md)
- [Development History](DEVELOPMENT_HISTORY.md)
- [Chapter 2 Handoff](CHAPTER_2_HANDOFF.md) — historical.

---

## 14. Development principles worth keeping

**Readable beats clever.**

**One queue. One poller. One shared execution path.**

**The configuration describes equipment; the action describes intent; the transport delivers the command.**

**A successful HTTP response is not proof of physical equipment state.**

**Never sacrifice a known-good configuration to save a minute of deployment work.**

**Be resilient in our dumbness.**

And finally:

> Do not spend three hours engineering a solution to save four seconds unless the resulting mechanism makes an exceptionally satisfying CLONK.

Actually, scratch that last part. That's probably the entire reason this project exists.

---

**THE CLONKER 10000**  
*Less sleek. More CLONK.*  
**CLONK! ⚡🔩**
