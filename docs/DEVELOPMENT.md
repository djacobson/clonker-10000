# THE CLONKER 10000
## Development, Deployment & Testing

**Updated:** November 8, 2026  
**Platform:** Raspberry Pi Pico 2 W (RP2350) / CircuitPython 10.3.1  
**Baseline:** Chapter 7 — Config v4, three-room physical control, Bourns encoders, navigation/playback buttons, Roku holds, shared Dumb Queue™, and PERF diagnostics  
**Repository:** https://github.com/djacobson/clonker-10000

> Built with modern software, vintage mechanical ambitions, and a development process carefully designed to minimize contact with an aging Windows laptop.

---

## 1. Purpose and rules of evidence

This is the **practical working guide** for editing, deploying, operating, testing, and debugging Clonker firmware. It is not the configuration schema, complete network specification, or chronological history. Those belong in [Configuration](CONFIGURATION.md), [Firmware, Network & Clock](FIRMWARE_NETWORK.md), and [Development History](DEVELOPMENT_HISTORY.md).

A Git commit, a file copied to CIRCUITPY, a queued action, a successful network write, and a visible equipment change are **different levels of evidence**. State exactly which was observed. Prefer one meaningful change and one clear test at a time.

## 2. Source of truth and development workflow

```text
iPad / Working Copy: edit, review, commit, push
              |
              v
GitHub: maintained source and documentation
              |
              v
Windows / GitHub Desktop: fetch and pull
              |
              v
Pico in SERVICE (USB): copy selected changed files
              |
              v
Pico in DEVICE: restart, inspect logs, test
              |
              v
Observe real equipment, record results, update docs
```

GitHub establishes the maintained source. **The actual Pico filesystem establishes the deployed code**, which may differ until copied. Browser-edited configuration on the Pico may also differ from the repository example.

- **iPad:** Working Copy, GitHub review, browser configuration and Test Remote, documentation drafting.
- **Windows laptop:** GitHub Desktop, USB file transfer, and serial diagnostics. PuTTY is useful for sustained serial sessions; the CircuitPython browser console may become unresponsive during long sessions.
- **CircuitPython REPL:** Use for inspection and deliberately scoped tests. Ctrl+C interrupts the running application; Ctrl+D soft-reloads. Neither substitutes for a cold power cycle when changing GP17 filesystem ownership.

The former ESP32-S3 and XML designs are historical. `device_config_v2.py` is the active module despite its historical filename: its schema is **Clonker Config v4**.

## 3. Active firmware map

| Repository path | Role |
|---|---|
| `firmware/boot.py` | GP17 filesystem ownership at boot |
| `firmware/code.py` | Application entry point |
| `firmware/clonker/main.py` | Startup and cooperative scheduler |
| `firmware/clonker/device_config_v2.py` | Config v4 validation, RAM snapshot, revisions, persistence and recovery |
| `firmware/clonker/device_adapters.py` | Specialized adapter selection and cached mapping |
| `firmware/clonker/actions.py` | Shared queue, action dispatch, toggles, compound steps and failure handling |
| `firmware/clonker/devices/denon.py` | Persistent Denon TCP volume connection and pacing |
| `firmware/clonker/net/http_transport.py` | Generic bounded blocking HTTP GET/POST |
| `firmware/clonker/net/web.py` | CONFIG-only inbound HTTP management |
| `firmware/clonker/www/index.html` | Browser configuration editor |
| `firmware/clonker/www/remote.html` | Browser Test Remote |
| `firmware/clonker/controls/pins.py` | GPIO assignment source of truth |
| `firmware/clonker/controls/buttons.py` | Debounced momentary inputs |
| `firmware/clonker/controls/switches.py` | GP18 CONFIG/RUN input and override |
| `firmware/clonker/controls/selectors.py` | Three-position room selector |
| `firmware/clonker/controls/encoders.py` | Reusable quadrature encoder decoder |
| `firmware/clonker/controls/physical.py` | Physical initialization, polling and room-aware action mapping |
| `firmware/clonker/system/clock.py` | Clock reference |
| `firmware/clonker/system/logger.py` | Serial diagnostics |
| `firmware/clonker/system/perf.py` | Shared named performance measurements and statistics |
| `firmware/clonker/display/oled.py` | OLED initialization, polling and display updates |

Preserve package directories and `__init__.py` files. Remove stale duplicate modules when refactoring; a successful copy does not guarantee Python imported the intended version.

### Preserve the active configuration

`/clonker/device_config.json` is a **runtime asset, not disposable build output**. It may contain newer browser changes than `firmware/clonker/device_config.json`. Back it up before any intentional replacement. Do not overwrite it as part of routine firmware deployment. The sample at [`samples/device_config_roku_denon_sample.json`](../samples/device_config_roku_denon_sample.json) is reference material.

## 4. Private settings and development LAN

Keep credentials in the Pico's private `settings.toml`; never commit them or overwrite a working copy during routine deployment. The documented development addresses are installation-specific:

| Endpoint | Development address |
|---|---|
| Clonker CONFIG UI | `http://192.168.50.12:9090/` |
| Browser Test Remote | `http://192.168.50.12:9090/remote.html` |
| Den AVR-X3700H HTTP | `192.168.50.44:8080` |
| Den Roku ECP | `192.168.50.43:8060` |
| Sunroom AVR-X1800H HTTP | `192.168.50.40:8080` |
| Sunroom Roku ECP | `192.168.50.28:8060` |

The Denon **specialized volume adapter uses TCP port 23** on the configured receiver host; the HTTP endpoint above remains relevant to other Denon commands.

The development setup disables CircuitPython Web Workflow using `CIRCUITPY_WEB_API_PORT = 0` in private settings following observed interference. The precise cause was not established. Clonker's own management server listens on port 9090 and has **no application-level authentication**: trusted LAN only, never public port forwarding.

## 5. Two independent mode switches

| Switch | OFF / open / HIGH | ON / grounded / LOW | Change timing |
|---|---|---|---|
| **GP17** filesystem ownership | SERVICE (USB): host writes | DEVICE: Pico writes | **Cold boot only** |
| **GP18** application mode | RUN: management listener stopped | CONFIG: listener enabled | **Live, no reboot** |

Normal standalone remote: **DEVICE + RUN**. Browser editing and persistent saves: **DEVICE + CONFIG**. USB deployment: **SERVICE (USB)**, regardless of CONFIG/RUN selection.

The action engine and physical controls operate in CONFIG and RUN. SERVICE + CONFIG allows browser inspection and Test Remote commands, but persistent browser saves are rejected (HTTP 403) because firmware cannot write the filesystem.

GP17's boot diagnostics are:

```text
CLONKER BOOT: SERVICE (USB) mode (switch OFF)
CLONKER BOOT: DEVICE mode (switch ON)
```

**Always disconnect power completely before changing GP17.** Ctrl+D is not a replacement. GP18 can be changed while the program runs. The GP2 Power Toggle and GP3/GP6/GP7 room selector are separate from both mode switches.

See [Operating Modes](OPERATING_MODES.md) for the complete mode matrix, override and recovery procedures.

## 6. Standard firmware deployment

1. Edit and review a focused change in Working Copy; commit and push.
2. Fetch/pull the intended commit in Windows GitHub Desktop.
3. Preserve the Pico's current `device_config.json` and private `settings.toml` as appropriate.
4. Disconnect Pico power; set **GP17 OFF** for SERVICE (USB); reconnect and verify the boot message and host-writable CIRCUITPY volume.
5. Copy **only the intended changed firmware files**, maintaining directory structure. Do not casually replace the active configuration, settings, or backups.
6. Verify filenames and paths on CIRCUITPY; remove superseded module copies only when certain they are obsolete.
7. Disconnect power; set **GP17 ON** for DEVICE; reconnect and verify the boot message.
8. Set **GP18 ON** for CONFIG browser tests, or OFF for RUN operation.
9. Inspect serial logs for startup, Wi-Fi, loaded rooms, GPIO initialization, adapter and queue errors.
10. Test the affected feature, including real equipment behavior where relevant. Record observed evidence and update the appropriate documentation.

A repository `firmware/clonker/...` path deploys to `/clonker/...` on CIRCUITPY. `firmware/boot.py` and `firmware/code.py` deploy to `/boot.py` and `/code.py`. Newly added modules such as `device_adapters.py`, `devices/denon.py`, and `controls/encoders.py` **must also be copied** when required by the running code.

### Deliberate configuration replacement

Before intentionally replacing `/clonker/device_config.json`, preserve primary and backup files, verify Config v4 schema compatibility, check room/device addresses and custom actions, and test cold-start loading. Do not mix a configuration migration with an unrelated GPIO or transport change.

## 7. Configuration regression in DEVICE + CONFIG

Use a reversible edit and record both browser behavior and cold-start persistence.

- **Save/reload:** Confirm GP17 DEVICE, GP18 CONFIG; make a small change, Save, refresh, cold power-cycle, and verify it persisted. Restore the intended value afterward.
- **Revision conflict:** Open two browser tabs; save from one; confirm a stale save from the other is rejected rather than overwriting newer data.
- **No-change save:** Confirm unchanged data avoids an unnecessary rewrite and preserves pending queue and toggle history.
- **Changed save:** Confirm pending queue work and volatile toggle-direction histories are reset; the active validated configuration and adapter selection cache are rebuilt as designed.
- **Read-only check:** In SERVICE + CONFIG, verify that persistent Save is rejected with HTTP 403 while inspection and Test Remote remain available.
- **Validation:** Exercise supported room IDs, generic device slots, fourteen fundamental actions, custom-action IDs/steps, methods, paths, wait limits and JSON size constraints as appropriate. Verify malformed data cannot replace the active valid configuration.

Backup rotation and recovery are safeguards, **not a promise of atomicity under sudden power loss**. The exact schema, file naming and recovery policy belong in [Configuration](CONFIGURATION.md).

## 8. Action and network regression

### Browser Test Remote

In CONFIG, open `/remote.html`, select a room, then run a fundamental or configured custom action. `POST /api/action?room=room-1&action=volume-up` submits a request to the shared dispatcher.

A response indicating **queued** proves admission, not successful network delivery or equipment state. Watch subsequent serial diagnostics and the actual receiver or streamer.

### Generic HTTP versus Denon TCP

- Generic commands use `net/http_transport.py` with bounded synchronous GET/POST, a new socket per command, and HTTP status-line checking.
- The adapter resolver recognizes **specific configured Denon HTTP volume-up/down command signatures** and routes them to `devices/denon.py` instead.
- The specialized Denon adapter uses a persistent TCP connection on **port 23**, sends native `MVUP`/`MVDOWN` commands, and enforces **50 ms minimum spacing**. It does not parse receiver state or automatically retry failed commands.
- Other Denon commands and Roku ECP remain on generic HTTP. A device's configured endpoint and the exact command path matter to adapter selection; do not assume every volume mapping uses TCP.
- The in-memory specialized adapter selection cache is rebuilt when configuration is loaded or successfully changed.

### Dumb Queue™ and compound actions

The shared queue admits at most **128 entries**. A custom action occupies one entry and advances through ordered steps with cooperative monotonic waits. A future-dated task does not block unrelated eligible work. A paced Denon TCP command that is not ready remains queued and must not be overtaken by later eligible work. One execution failure clears remaining queued work; there are no automatic retries or rollback.

Regression checks should cover:

1. Roku GET/POST and ordinary Denon HTTP requests.
2. Slow and rapid volume movement through the **physical Bourns encoder**.
3. Denon TCP connection reuse and approximately 50 ms minimum command spacing.
4. Mixed TCP/HTTP queue order, including a paced volume command ahead of another eligible action.
5. Custom action with a wait while unrelated immediate work runs.
6. Unreachable endpoints, network errors, queue-wide cancellation, and subsequent recovery.
7. Configuration change while work is pending.

**Known-good Chapter 6 evidence:** A Sunroom physical Bourns volume encoder drove the Denon X1800H through TCP. Five slow detents each direction returned to the starting level; moderate and aggressive twisting were also exercised. A ten-command Denon queue test and five mixed-queue regression scenarios were reported passing. These are observed test results, not exhaustive long-uptime certification.

### Timing and limitations

The main scheduler targets **1 ms physical polling**, **1 ms CONFIG web polling**, **10 ms action polling**, and a **1 ms loop yield**. These are cooperative targets, not guaranteed latencies. Synchronous HTTP and TCP operations temporarily interrupt GPIO polling; fast encoder transitions may be missed during a blocking call. Queue buffering cannot recover a physical transition never sampled.

See [Firmware, Network & Clock](FIRMWARE_NETWORK.md) for precise transport, pacing, ordering and diagnostic behavior.

## 9. Physical-control verification

The Chapter 7 implementation expanded physical input support beyond the original Chapter 6 power and volume controls.

| Control | Current status |
|---|---|
| SERVICE/DEVICE boot switch | Operational |
| CONFIG/RUN switch | Operational |
| Power Toggle | Operational |
| Three-position room selector | Operational; Room 3 configured as placeholder |
| Bourns volume encoder | Operational in Den and Sunroom |
| Volume encoder push-to-mute | Integrated |
| Custom-action encoder | Rotation and selection integrated; further experience testing pending |
| Navigation, Select/OK, Back, Home | Integrated |
| Play/Pause and Skip Back/Forward | Integrated, including Roku held-key behavior |
| OLED | Integration and feedback work ongoing |
| Audible CLONK, battery, final enclosure | Planned or in progress |

GPIO assignments are maintained in `controls/pins.py` and documented in [Hardware & Physical Controls](HARDWARE_CONTROLS.md).

Physical inputs use room-aware generic actions routed through the shared dispatcher and queue. Roku held-button behavior uses explicit keydown/keyup handling.

The configured Room 3 placeholder has blank command mappings. Ordinary fundamental actions treat blank mappings as no-ops; held-button safety requires additional verification.

### Physical polling performance

Chapter 7 introduced shared PERF instrumentation in `system/perf.py`.

The scheduler records physical polling gaps, execution durations, queue and adapter activity, and other timing measurements.

`controls/physical.py` supports optional internal diagnostics controlled by `PHYSICAL_PERF_ENABLED` and individual measurement flags.

The current baseline has internal physical diagnostics disabled while scheduler-level PERF remains enabled.

Idle polling is consistently fast. During sustained volume activity, occasional physical execution spikes around 40–50 ms remain unexplained.

Blocking Roku network operations also produce longer cooperative scheduler gaps. These are distinct measurements and should not be conflated.

The full investigation, test results, and unsuccessful experiments are recorded in [Development History](DEVELOPMENT_HISTORY.md).

### The Clonker Test Kitchen Sink™

Development and experimental test scripts live in:

`firmware/tests/`

This directory intentionally sits outside `firmware/clonker/`.

It's our kitchen sink of experiments: some scripts test Clonker modules, while others investigate the Pico, CircuitPython, GPIO, hardware peripherals, networking, and other platform behavior independently of the application.

Some are regression tests. Some are diagnostic tools. Others are historical experiments that answered a question once and may never need to run again.

**Before inventing another test, look in the kitchen sink.**

When troubleshooting or developing a subsystem:

1. Inspect `firmware/tests/` in the current GitHub repository.
2. Read existing relevant scripts before proposing new ones.
3. Reuse or extend existing tests when practical.
4. Check Git history or `DEVELOPMENT_HISTORY.md` when historical context matters.
5. Verify a script's assumptions and dependencies before running it on the Pico.

Git is the authoritative test inventory. Do not maintain a duplicate file list in documentation.

Tests are development tools, not necessarily part of the normal Clonker runtime deployment.

**Less reinventing. More CLONK.**

## 10. Debugging and serial discipline

**Record:** commit/deployed version, GP17 and GP18 positions, selected room, GPIO mapping, exact test action, queue/transport logs, and observed equipment behavior. If a cold power cycle changes the result, note it.

| Symptom | First checks |
|---|---|
| Browser unavailable | GP18 CONFIG, Wi-Fi, port 9090, listener diagnostics |
| Browser stalls | Single-client listener, silent connections, blocking outbound operations, web polling cadence |
| Save rejected | GP17 DEVICE, stale revision, schema/size validation, filesystem state |
| Action queued but equipment unchanged | Actual queue execution, configured endpoint/path, adapter choice, transport result, equipment state |
| Volume turns but nothing changes | GP8/GP9 wiring, detent events, selected room, Denon path signature, TCP connection/pacing |
| Wrong room responds | GP3/GP6/GP7 selection, active configuration, room-aware dispatch |
| No-op logged | Unconfigured room or deliberately blank ordinary mapping |
| Unexpected import behavior | Stale Pico files, missing `__init__.py`, incomplete deployment |
| Serial console seems frozen | Verify application state; consider PuTTY or a fresh serial session |
| Ctrl+C / `KeyboardInterrupt` | Often intentional interruption, not a firmware crash |

For a narrowly scoped test file on CIRCUITPY, a REPL invocation may look like:

```python
exec(open("/tests/test_room_selector.py").read())
```

Only run tests that **actually exist on the Pico**. Test filenames and results should be documented as observed, not assumed from the repository. If importing the running application holds resources, interrupt it deliberately before a standalone GPIO test, and restore normal operation afterward.

**Network success is not equipment-state confirmation.** An HTTP 2xx or completed TCP write proves only its respective communication boundary. Clonker does not currently query authoritative power, mute, or volume state.

## 11. Verification vocabulary and handoff

- **Verified on hardware:** Observed on the actual Pico and, where relevant, actual AV equipment.
- **Implemented, not exhaustively verified:** Code exists and works in some conditions; broader cases remain untested.
- **Planned:** Proposed design or integration not yet working.
- **Historical:** Superseded design, test or implementation; keep the dated record without presenting it as current.
- **Deferred:** Deliberately outside the present implementation scope.

After meaningful work, record the date, changed files, deployed version if known, exact test and observed outcome. Update the current reference document and add dated milestones to [Development History](DEVELOPMENT_HISTORY.md) without repeatedly duplicating entire technical specifications.

### Remaining work

- Investigate the unresolved 40–50 ms physical execution spikes during sustained volume activity; distinguish runtime pauses from input-processing overhead.
- Complete the individual `PERF_DISPATCH` and `PERF_HOLD` diagnostic switches when needed.
- Continue physical control reliability testing, particularly rapid encoder input during blocking Roku network operations.
- Complete the custom-action encoder experience and OLED status feedback.
- Integrate audible CLONK feedback, battery management, sleep/wake behavior, and final enclosure wiring.
- Verify blank-command safety for physical held-button actions in Room 3.
- Expand regression coverage for network failures, long uptime, and interrupted writes.
- Pursue custom destination slots and Apple TV discovery/pairing/authentication later.

### Reference map

- [Architecture](ARCHITECTURE.md)
- [Configuration & Recovery](CONFIGURATION.md)
- [Firmware, Network & Clock](FIRMWARE_NETWORK.md)
- [Operating Modes](OPERATING_MODES.md)
- [Hardware & Physical Controls](HARDWARE_CONTROLS.md)
- [Development History](DEVELOPMENT_HISTORY.md)
- [Chapter 2 Handoff](CHAPTER_2_HANDOFF.md) — historical.

---

**Readable beats clever. One queue. One poller. One shared execution path.**

> Do not spend three hours engineering a solution to save four seconds unless the resulting mechanism makes an exceptionally satisfying CLONK.

Actually, scratch that last part. That's probably the entire reason this project exists.

**THE CLONKER 10000 — Less sleek. More CLONK.** ⚡🔩
