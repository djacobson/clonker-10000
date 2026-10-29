# The Clonker 10000 — Operating Modes

**Design reference:** Updated October 27, 2026  
**Hardware:** Raspberry Pi Pico 2 W  
**Runtime:** CircuitPython 10.3.1  
**Current baseline:** Chapter 4 / Clonker Config v4  
**Status:** SERVICE/DEVICE filesystem selection implemented and tested; CONFIG/RUN application-mode logic implemented with simulated input; physical CONFIG/RUN switch pending.

> Two switches. Two completely different jobs. One appropriately complicated monster.

---

## 1. Purpose and mode boundaries

Clonker has **two independent operating-mode dimensions**:

1. **SERVICE (USB) / DEVICE** decides whether the USB host or the Pico firmware owns filesystem writes. This is selected at boot.
2. **CONFIG / RUN** decides whether the application exposes its management HTTP interface. This is an application-level selection intended to change during runtime.

Neither dimension is an AV equipment power command. Neither selects a room. Neither changes the definition of a configured action.

| Property | SERVICE / DEVICE | CONFIG / RUN |
|---|---|---|
| Responsibility | Filesystem write ownership | Management HTTP availability |
| Mechanism | GP17 boot jumper | Simulated software state; physical switch planned |
| Evaluated by | `firmware/boot.py` | Main loop via `controls/switches.py` |
| Selection time | At boot | During application operation |
| Requires full power cycle to change | **Yes** | **No**, by design |
| Implemented | Yes, tested | Listener logic implemented; physical input not wired |
| Changes external equipment power | No | No |

**Normal eventual operation:** DEVICE + RUN.  
**Normal browser configuration:** DEVICE + CONFIG.  
**USB firmware deployment:** SERVICE, generally with CONFIG available for inspection.

The application can execute configured outbound actions through the shared Dumb Queue™ while CONFIG is enabled. The action poller is not inherently dependent on the management listener. Physical-input operation in RUN remains unverified because physical controls have not been integrated.

## 2. SERVICE (USB): host-owned filesystem

**Status:** Implemented and tested.

`boot.py` configures GP17 with an internal pull-up. With the jumper **open**, GP17 reads HIGH and selects SERVICE mode.

```text
CLONKER BOOT: SERVICE (USB) mode (jumper OPEN)
```

In SERVICE:

- The USB host can write the CIRCUITPY filesystem.
- The Pico application sees that filesystem as read-only.
- Firmware and other files can be deployed from the host.
- The Pico cannot persist browser configuration changes.
- Serial console and REPL access remain available.
- The application may still run, connect to Wi-Fi, and execute configured actions.

### SERVICE + CONFIG browser behavior

With CONFIG enabled, the browser can inspect the active **Config v4** JSON, review room/device/action mappings, synchronize the RAM clock, and use the Test Remote to submit fundamental or custom actions.

A configuration save through `POST /api/config` is rejected with **HTTP 403** when the filesystem is read-only. CONFIG availability does **not** imply write permission.

SERVICE is a filesystem-maintenance state, not an instruction to disable the application or its outbound equipment-control capability.

## 3. DEVICE: Pico-owned filesystem

**Status:** Implemented and tested.

Grounding GP17 at boot selects DEVICE mode. On the Pico 2 W, the documented jumper uses **GP17 physical pin 22** and adjacent **GND physical pin 23**.

```text
CLONKER BOOT: DEVICE mode (jumper GROUNDED)
```

The boot code remounts the filesystem for firmware writes:

```python
storage.remount("/", readonly=False)
```

In DEVICE:

- The Pico application can persist validated configuration changes.
- The USB host sees CIRCUITPY as read-only.
- The configuration engine can perform its guarded save and backup process.
- A successful changed save publishes the new validated configuration into RAM.
- Serial and REPL access remain available.

### DEVICE + CONFIG browser behavior

This is the normal browser-editing combination. The user can edit configured rooms, generic built-in device slots, fundamental mappings, and custom actions; save valid Config v4 data with revision protection; synchronize the clock; and exercise the Test Remote.

The exact schema, limits, validation, backup rotation, and recovery rules belong in [Configuration & Recovery](CONFIGURATION.md).

**DEVICE does not mean RUN.** Filesystem ownership and application management availability remain independent.

## 4. Changing SERVICE / DEVICE safely

The GP17 jumper is a **boot-time selection**. A Ctrl+D soft reload is not a substitute for changing filesystem ownership.

To change ownership:

1. Finish and save any host-side file edits.
2. Disconnect Pico power.
3. Set GP17 **open** for SERVICE or **grounded** for DEVICE.
4. Reconnect power and observe the boot message.
5. Confirm the expected filesystem write ownership before copying files or saving configuration.

Do not change the jumper while powered. Do not attempt host writes while the Pico owns the filesystem. Do not assume a browser's ability to display configuration means that it can save it.

## 5. CONFIG: management interface enabled

**Status:** Implemented at application level; physical mode switch pending.

CONFIG enables the Clonker management HTTP service on **port 9090**. In the documented development network the Pico is normally at `192.168.50.12`:

- Configuration page: `http://192.168.50.12:9090/`
- Test Remote: `http://192.168.50.12:9090/remote.html`

These addresses are development-specific, not firmware defaults.

CONFIG makes available:

- The Config v4 editor and configuration API.
- Revision-aware saves **only** when the filesystem is writable.
- Clock status and browser-supplied UTC synchronization.
- The browser Test Remote.
- Fundamental and custom-action submission through `POST /api/action`.

The Test Remote is **operational**, not a logging-only stub. It can enqueue configured actions which the shared Dumb Queue™ executes using the outbound HTTP transport. An enqueue acknowledgment does not itself prove successful execution or an equipment-state change.

### CONFIG/RUN source selection and software override

The authoritative application-mode interface is `switches.config_enabled()` in `firmware/clonker/controls/switches.py`.

The normal hardware configuration assigns `CONFIG_SWITCH_PIN = 18` in `firmware/clonker/controls/pins.py`.

| `CONFIG_SWITCH_PIN` | Source | Behavior |
|---|---|---|
| `18` | PHYSICAL | Read the maintained GP18 switch |
| `None` | SIMULATED | Use the software state for development |

### Verified GP18 electrical behavior

The physical switch uses an internal GPIO pull-up.

| GP18 state | Switch position | Application mode |
|---|---|---|
| LOW / grounded | ON | CONFIG |
| HIGH / open | OFF | RUN |

**This polarity was physically tested October 29, 2026.** It is no longer provisional.

The physical switch is the normal source for application-mode selection. Changing its position takes effect during runtime without a reboot.

### Simulated mode

For hardware-free development, setting `CONFIG_SWITCH_PIN = None` selects the simulated source.

The simulated state defaults to CONFIG (`True`) and can be changed with `switches.set_simulated_config(enabled)`.

### Software override

A temporary software override can supersede either physical or simulated mode selection.

| `set_config_override()` value | Effective behavior |
|---|---|
| `None` | Follow configured source |
| `True` | Force CONFIG |
| `False` | Force RUN |

For example:

```python
switches.set_config_override(True)   # Force CONFIG
switches.set_config_override(False)  # Force RUN
switches.set_config_override(None)   # Return to normal selection
```

`switches.config_source()` reports `SIMULATED`, `PHYSICAL`, or `OVERRIDE` for diagnostics.

The override is **RAM-only** and resets on application restart. It is a development and troubleshooting facility, not a browser-facing control or a persistent configuration setting.

### Hardware-presence limitations

**Schrödinger's switch:** An ordinary GPIO input cannot reliably distinguish an intentionally open switch from a disconnected wire.

Clonker therefore does not attempt automatic hardware-presence detection.

If the physical switch is unavailable, select simulation explicitly by setting `CONFIG_SWITCH_PIN = None`, or use the software override.

GPIO initialization errors are not silently converted into simulated mode.

CONFIG/RUN selection remains independent of GP17 SERVICE (USB)/DEVICE filesystem ownership, physical room selection, and equipment power-toggle actions.

### Listener lifecycle

The main loop checks the selected application mode and starts the management listener on entry to CONFIG, or stops it on entry to RUN. The listener is not recreated every iteration. While CONFIG is enabled, `web.poll()` is scheduled cooperatively at approximately 1 ms intervals.

That interval is **not** a guaranteed browser response time. Outbound HTTP execution is currently blocking and can temporarily pause other cooperative work. See [Firmware, HTTP & Clock](FIRMWARE_NETWORK.md).

### CONFIG/RUN mode diagnostics

The main scheduler announces the effective application-mode source and operating mode at startup and whenever either changes.

Example normal startup with the GP18 physical switch in CONFIG:

```text
App mode source = PHYSICAL
App mode = CONFIG
```

Moving the switch to RUN produces:

```text
App mode = RUN
```

Returning to CONFIG produces:

```text
App mode = CONFIG
```

The source and mode are tracked independently. A source change is logged even when the effective operating mode remains unchanged.

Announcements are transition-based, not emitted on every scheduler iteration.

**Verified October 28, 2026:** Simulated CONFIG startup, responsive browser pages, GP2 button events, and forced-RUN operation using the temporary software override.

**Verified October 29, 2026:** GP18 physical CONFIG/RUN selection and repeated live transitions. Browser refresh tests confirmed that RUN stops the management listener and CONFIG restores it, without restarting the application.

The physical switch is now the normal mode-selection source. Simulation and software override remain available for development and troubleshooting.

## 6. RUN: management interface disabled

**Status:** Physical GP18 CONFIG/RUN switching and management-listener transitions implemented and tested October 29, 2026.

RUN is intended to be the normal operating state of the completed remote.

In RUN:

- The management HTTP listener is stopped.
- The browser editor, configuration API, clock endpoint, and Test Remote are unavailable.
- Wi-Fi and the validated in-memory configuration remain available.
- The shared Dumb Queue™ and action poller continue operating independently of the management listener.
- Physical controls can continue to be polled; their eventual action dispatch does not require the management server.

**Verified:** Switching GP18 to RUN stops the management listener. Returning to CONFIG restores browser access without rebooting.

**Not yet verified:** End-to-end physical button execution against AV equipment in RUN. GP2 press/release events are operational, but physical room selection and event-to-action dispatch remain pending.

Changing CONFIG/RUN does not reload configuration from flash. The application continues using its active validated RAM snapshot, including successfully saved changes made in CONFIG.

The intended final behavior is that ordinary physical controls work in both CONFIG and RUN. CONFIG adds management services rather than disabling the remote.

## 7. Four operating combinations

The GP17 boot-mode switch and GP18 application-mode switch operate independently, providing four possible combinations.

| Filesystem mode | Application mode | Expected behavior |
|---|---|---|
| **SERVICE (USB)** | **CONFIG** | USB host can deploy files; browser can inspect and test actions; configuration writes rejected |
| **SERVICE (USB)** | **RUN** | USB host owns filesystem writes; management listener stopped; action engine remains available |
| **DEVICE** | **CONFIG** | Pico owns filesystem writes; browser configuration, guarded saves, and Test Remote available |
| **DEVICE** | **RUN** | Pico owns filesystem writes; management listener stopped; intended normal physical-remote operating mode |

**Verified October 29, 2026:** The physical GP18 switch changes CONFIG/RUN during runtime without rebooting. Browser refresh tests confirmed management-listener shutdown and restart.

GP17 filesystem ownership remains a boot-time selection requiring a full power cycle.

The action engine and validated RAM configuration are independent of management-listener availability. However, the complete physical-button-to-equipment path in RUN remains untested because room selection and physical action dispatch are not yet connected.

These combinations describe filesystem ownership and management-interface behavior, **not** four different equipment-power states.

## 8. Configuration persistence and mode permissions

Persistent browser configuration saves require **both** a writable Pico filesystem and an available CONFIG management endpoint.

- **SERVICE + CONFIG:** `POST /api/config` is rejected with HTTP 403 because the Pico filesystem is read-only.
- **DEVICE + CONFIG:** A save can proceed if schema validation, revision checks, disk consistency checks, and persistence safeguards pass.
- **Either RUN combination:** The browser save endpoint is unavailable because the management listener is stopped.

A successful **changed** save updates persistent configuration, performs the engine's backup safeguards, publishes the new validated RAM configuration, **clears pending queue work, and resets all volatile toggle-direction histories** to avoid carrying stale requests or command history across a configuration change. An **unchanged** save avoids an unnecessary flash rewrite and preserves the existing queue and toggle histories.

Do not infer that backup rotation is a fully atomic transaction under sudden power loss. See [Configuration & Recovery](CONFIGURATION.md) for exact guarantees and remaining limits.

## 9. Operating modes are not equipment power controls

Three different concepts must remain separate:

1. **GP17 SERVICE (USB)/DEVICE boot-mode switch:** Selects filesystem write ownership at startup. A full power cycle is required to change modes.
2. **GP18 CONFIG/RUN application-mode switch:** Enables or disables the management HTTP listener during runtime, without rebooting.
3. **GP2 momentary power button / SYSTEM MASTER concept:** Intended to request the selected room's configured `power-toggle` action. Physical button events are verified, but room-aware action dispatch and future sleep/wake behavior are not yet implemented.

The Config v4 schema supports `on_path` and `off_path` for power/mute toggles. Runtime direction selection is **IMPLEMENTED**: the dispatcher maintains independent, volatile ON/OFF command histories per room and action. A successful HTTP request advances the next direction; a changed configuration save resets all histories.

This command history is **not authoritative equipment state**. External remotes, HDMI-CEC, and manual device controls can change equipment independently. October 27, 2026 bench tests confirmed that failed HTTP requests, blank selected command paths, and missing endpoints do not advance toggle direction history. Broader failure-condition and physical-input testing remains outstanding.

**Changing GP17 or GP18 must never transmit an equipment power command merely because an operating mode changed.**

## 10. Physical controls and GPIO integration

The current application GPIO assignments are maintained in `firmware/clonker/controls/pins.py`. Boot-time GP17 handling is separate, in `firmware/boot.py`.

### GP17 — SERVICE (USB)/DEVICE boot switch

**Implemented and tested.**

A maintained physical switch selects filesystem ownership at boot:

- OFF/open/high = SERVICE (USB), host-owned filesystem writes.
- ON/grounded/low = DEVICE, Pico-owned filesystem writes.
- A full power cycle is required to change ownership.

This switch does not change the application's CONFIG/RUN state.

### GP18 — CONFIG/RUN application switch

**Implemented and tested.**

A guarded maintained switch uses GP18 with an internal pull-up:

- OFF/open/high = RUN.
- ON/grounded/low = CONFIG.

The application polls this switch during runtime. Mode transitions start or stop the management HTTP listener without rebooting.

Repeated browser tests confirmed that CONFIG restores management access and RUN disables it.

The active validated configuration remains in RAM. Switching modes does not itself execute an AV command.

### GP2 — momentary power-button input

**Input implemented and tested; action dispatch pending.**

The GP2 momentary button produces debounced press/release events through the physical-control subsystem.

These events are currently logged, not dispatched as `power-toggle` commands.

The next dependency is physical room selection, so the dispatcher knows which configured room should receive the action.

### Room selection

The physical room selector is not yet wired or implemented.

Den and Sunroom are the current operational rooms. A possible BOTH selection remains a design question, not an implemented command-broadcast feature.

Room selection is independent of SERVICE/DEVICE and CONFIG/RUN.

### Guarded SYSTEM MASTER

The guarded SYSTEM MASTER concept is distinct from both operating-mode switches.

Its intended awake behavior is to invoke the selected room's `power-toggle` action. Its possible deep-sleep wake/ignition behavior remains experimental and unimplemented.

The underlying `power-toggle` software action is already implemented and bench-tested through the browser Test Remote.

For component inventory, GPIO assignments, and mechanical design, see [Hardware & Controls](HARDWARE_CONTROLS.md).

## 11. Deployment, recovery, and security cautions

- Preserve the Pico's current `device_config.json` before replacing it from a repository copy; the running device may contain newer browser edits.
- Keep private Wi-Fi credentials in `settings.toml`; do not commit them or overwrite them during routine firmware deployment.
- Confirm the intended GP17 mode before copying files or testing persistence.
- Refresh stale browser tabs after a revision conflict rather than bypassing the conflict protection.
- Treat a successful HTTP action acknowledgment as queue admission, not proof that equipment changed state.
- CircuitPython Web Workflow is separate from Clonker's management service. The documented development setup disables Web Workflow with `CIRCUITPY_WEB_API_PORT = 0` following observed networking interference; the precise cause was not conclusively established.
- The Clonker management service has no application-level authentication. Use it on a trusted LAN only; do not expose port 9090 through internet-facing port forwarding.

For the full deployment checklist, see [Development & Deployment](DEVELOPMENT.md).

## 12. Verification status and remaining work

**Current reference date:** October 29, 2026.

### Implemented and exercised

- GP17 physical boot-mode switch: OFF/open selects SERVICE (USB); ON/grounded selects DEVICE.
- Boot-time filesystem ownership, DEVICE-mode browser saves, and SERVICE (USB)-mode rejection of persistent writes.
- Config v4 validation, revision protection, and selected backup/recovery behavior.
- GP18 physical CONFIG/RUN switch: grounded selects CONFIG; open selects RUN.
- Live CONFIG → RUN → CONFIG transitions without rebooting.
- Management HTTP listener stops in RUN and restarts in CONFIG, confirmed through repeated browser refresh tests.
- Serial diagnostics identifying `App mode source = PHYSICAL` and the effective application mode.
- GP2 momentary power-button input, debounce, and press/release event logging.
- Browser responsiveness with physical button polling enabled.
- Fundamental action dispatch through the shared Dumb Queue™ to real Denon/Roku equipment.
- Config v4 custom actions and cooperative multi-step execution, including a tested Roku command, wait, and Denon command.
- Runtime power/mute ON/OFF direction selection through the shared dispatcher, bench-tested October 27, 2026 using the browser Test Remote.
- Sunroom Denon mute ON/OFF and Roku Home/PowerOff execution, including the LG G1 and Denon X1800H HDMI-CEC power chain.
- Changed-configuration toggle-history reset and independent Den/Sunroom histories.

### Implemented, not exhaustively verified

- CONFIG/RUN listener behavior under unusual network failures and extended operation.
- Configuration availability across every operating-mode combination and transition.
- All interrupted-write and power-loss recovery cases.
- Extended load and long-uptime behavior.

### Not yet implemented or end-to-end tested

- Physical room selection and room-context propagation to action dispatch.
- GP2 physical power-button event-to-action dispatch.
- Complete physical DEVICE + RUN equipment-control operation.
- Navigation buttons, volume encoder, and custom-action selector encoder.
- SYSTEM MASTER sleep/wake and ignition behavior.
- OLED and audible feedback integration.
- Custom device slots and Apple TV protocol support.

Historical October 19 mode tests and subsequent Chapter 3/4 networking milestones remain in [Development History](DEVELOPMENT_HISTORY.md). They should not be mistaken for the current implementation status.

## 13. Related documents

- [Architecture](ARCHITECTURE.md) — overall design boundaries and ownership.
- [Configuration & Recovery](CONFIGURATION.md) — authoritative Config v4 schema, persistence, and recovery.
- [Firmware, HTTP & Clock](FIRMWARE_NETWORK.md) — current networking, scheduler, queue, and transport.
- [Hardware & Controls](HARDWARE_CONTROLS.md) — physical design and GPIO planning.
- [Development & Deployment](DEVELOPMENT.md) — iPad-first development and deployment workflow.
- [Development History](DEVELOPMENT_HISTORY.md) — dated engineering milestones and tests.

---

**CLONK! ⚡🔩**
