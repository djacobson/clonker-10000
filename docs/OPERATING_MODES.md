# The Clonker 10000 — Operating Modes

**Design reference:** November 3, 2026  
**Platform:** Raspberry Pi Pico 2 W / CircuitPython 10.3.1  
**Baseline:** Chapter 6 — physical controls, room selection, volume encoder, and shared action execution operational  
**Scope:** Boot-time filesystem ownership, runtime management mode, deployment, recovery, and verified behavior.

> Two switches. Two completely different jobs. One appropriately complicated monster.

---

## 1. The two independent switches

Clonker has two operating-mode dimensions. They are independent of each other, the selected room, and the equipment's power state.

| Dimension | Switch | OFF / open / HIGH | ON / grounded / LOW | When evaluated |
|---|---|---|---|---|
| Filesystem ownership | GP17 | **SERVICE (USB):** USB host writes | **DEVICE:** Pico firmware writes | At cold boot |
| Application management | GP18 | **RUN:** management HTTP stopped | **CONFIG:** management HTTP available | During application runtime |

**Normal standalone remote:** DEVICE + RUN.  
**Browser configuration:** DEVICE + CONFIG.  
**USB file deployment:** SERVICE (USB), with CONFIG or RUN as appropriate.

The physical room selector (GP3/GP6/GP7) is a third, unrelated control. The momentary Power Toggle (GP2) sends an equipment action; it does not change either operating mode.

## 2. GP17 — SERVICE (USB) and DEVICE

**Implementation:** `firmware/boot.py`. GP17 is read once at boot using an internal pull-up. The boot switch is physically verified.

### SERVICE (USB): switch OFF

An open GP17 reads HIGH. The default CircuitPython filesystem arrangement lets the connected USB host write CIRCUITPY, while the running Pico application treats the filesystem as read-only.

Expected boot message:

```text
CLONKER BOOT: SERVICE (USB) mode (switch OFF)
```

In SERVICE, the USB host can deploy firmware, tests, and documentation-related files to CIRCUITPY. Serial console and REPL remain available. The application can still load configuration, join Wi-Fi, process physical controls, and send configured commands.

**SERVICE does not mean the remote is disabled.** It means the Pico cannot persist browser configuration changes to its filesystem.

### DEVICE: switch ON

Grounding GP17 selects DEVICE. `boot.py` executes:

```python
storage.remount("/", readonly=False)
```

Expected boot message:

```text
CLONKER BOOT: DEVICE mode (switch ON)
```

The Pico can now save validated configuration and rotate backups. The USB host sees CIRCUITPY as read-only. The serial console and REPL remain available.

On the Pico 2 W, the documented switch wiring uses GP17 (physical pin 22) and adjacent GND (physical pin 23). Verify the board's printed pin labels before changing wiring.

### Changing filesystem ownership

**A full power cycle is required.** Moving GP17 while powered does not change the current filesystem ownership, and Ctrl+D is not a substitute for cold boot.

1. Finish and save host-side edits; allow outstanding writes to complete.
2. Disconnect all Pico power sources, including USB and any external supply.
3. Move GP17 to OFF for SERVICE or ON for DEVICE.
4. Reconnect power and confirm the `CLONKER BOOT` message.
5. Verify expected write permissions before copying files or saving browser configuration.

Do not change GP17 as a live operating control. Never assume that a browser page loading successfully means the Pico has write access.

## 3. GP18 — CONFIG and RUN

**Implementation:** `firmware/clonker/controls/switches.py`, read by `firmware/clonker/main.py`. The maintained GP18 switch uses an internal pull-up and has been physically verified.

| GP18 electrical state | Effective mode | Management HTTP |
|---|---|---|
| Grounded / LOW | CONFIG | Started on port 9090 |
| Open / HIGH | RUN | Stopped |

The switch is evaluated during the application's cooperative loop.

While Clonker is awake, **CONFIG ↔ RUN transitions do not require
rebooting**. A mode transition does not reload the active configuration,
alter room selection, or issue an equipment power command.

During software sleep, moving the CONFIG switch in either direction
requests a wake and reboot. The switch position after reboot determines
the operating mode. This is a sleep/wake behavior, not a change to
normal CONFIG/RUN operation.

### CONFIG

CONFIG enables the Clonker browser management service on the trusted local network. The development installation has used these addresses:

- `http://192.168.50.12:9090/` — configuration editor
- `http://192.168.50.12:9090/remote.html` — Test Remote

The IP address is installation-specific, not a firmware default.

CONFIG exposes validated Config v4 inspection, revision-protected saves when the Pico filesystem is writable, browser clock synchronization, and the Test Remote. The browser can enqueue fundamental and custom actions; the shared Dumb Queue™ executes them using the appropriate transport. **Queued is not the same as executed**, and a network acknowledgment does not establish actual equipment state.

Physical controls continue operating in CONFIG. Enabling the browser does not disable the remote.

### RUN

RUN stops the Clonker management HTTP listener. The editor, Test Remote, and management APIs are unavailable while RUN is selected.

The active validated configuration stays in RAM. Wi-Fi, physical room selection, the GP2 Power Toggle, the GP8/GP9 volume encoder, and the shared action queue remain part of the running application. The action poller operates in both CONFIG and RUN.

**The management listener is not the command engine.** Turning off the browser does not turn off the remote.

### Listener lifecycle and diagnostics

`main.py` starts the listener on entry to CONFIG and stops it on entry to RUN; it does not recreate the listener every iteration. CONFIG-mode `web.poll()` targets a 1 ms service interval, subject to cooperative scheduling and blocking outbound operations.

Representative serial messages:

```text
App mode source = PHYSICAL
App mode = CONFIG
App mode = RUN
App mode = CONFIG
```

Source and effective mode are logged on startup and on changes, not on every poll.

### Software sleep and wake — Chapter 9

Clonker supports software-managed inactivity sleep while operating
in RUN mode.

This is not hardware deep sleep. The CPU remains active to monitor
physical controls.

When the configured inactivity timeout expires and no queued actions
remain:

1. The OLED briefly displays `Going Zzzz!`.
2. The OLED shuts down.
3. Wi-Fi is disabled.
4. The application enters its software-sleep state.

The CONFIG management service is unavailable during sleep.

**Wake controls:**

| Control | While sleeping |
|---|---|
| Momentary pushbutton | Wake and reboot |
| CONFIG/RUN switch movement | Wake and reboot |
| Volume encoder rotation | Ignored |
| Custom-action encoder rotation | Ignored |
| Room selector movement | Ignored |

The first wake-eligible input is consumed and does not dispatch an
equipment action.

After reboot, Clonker restores its normal startup sequence, including
Wi-Fi connectivity and OLED initialization.

CONFIG mode prevents inactivity sleep. Returning to RUN restarts
the inactivity countdown.

The sleep implementation currently uses a 25 ms scheduler delay
while asleep, compared with 1 ms during normal awake operation.

The inactivity timeout is a developer setting in
`clonker/system/sleep_manager.py`; it is not yet exposed in the
browser configuration interface.

For implementation details, see
[Architecture](ARCHITECTURE.md).
For measurements and verification, see
[Development History](DEVELOPMENT_HISTORY.md).

## 4. Simulation and development override

`controls/pins.py` normally sets:

```python
CONFIG_SWITCH_PIN = 18
```

The application-mode source is selected as follows:

| Condition | Source | Meaning |
|---|---|---|
| `CONFIG_SWITCH_PIN = 18` and no override | `PHYSICAL` | Follow the GP18 switch |
| `CONFIG_SWITCH_PIN = None` and no override | `SIMULATED` | Follow RAM-only simulated state |
| Override explicitly set | `OVERRIDE` | Force CONFIG or RUN |

Simulation defaults to CONFIG (`True`) and can be changed using `switches.set_simulated_config(enabled)` when the pin is unassigned.

The temporary override accepts:

```python
switches.set_config_override(True)   # Force CONFIG
switches.set_config_override(False)  # Force RUN
switches.set_config_override(None)   # Follow normal source
```

`switches.config_enabled()` returns the effective mode; `switches.config_source()` reports its source. Overrides are RAM-only and reset with the application. They do not change GP17 filesystem ownership.

**Schrödinger's switch:** A GPIO reading HIGH cannot distinguish a deliberately open switch from a disconnected wire. Clonker does not pretend to detect physical switch presence. For hardware-free testing, explicitly select simulation or an override; GPIO initialization failures are not silently treated as simulation.

## 5. The four operating combinations

| GP17 filesystem mode | GP18 application mode | USB host writes | Pico configuration saves | Management HTTP | Action engine |
|---|---|---|---|---|---|
| SERVICE (USB) | CONFIG | Yes | No — HTTP 403 | Available | Active |
| SERVICE (USB) | RUN | Yes | No | Stopped | Active |
| DEVICE | CONFIG | No | Yes, if validation and revision checks pass | Available | Active |
| DEVICE | RUN | No | Not through browser | Stopped | Active |

This table describes permissions and service availability, **not four different equipment-power states**.

The physical GP17 and GP18 behavior was verified October 29, 2026. Chapter 6 subsequently verified room-aware Power Toggle operation on actual Den and Sunroom equipment and the physical volume encoder through the shared dispatcher. Do not infer that every combination, failure mode, or extended-duration workload has been exhaustively tested.

## 6. Configuration persistence and safe saves

The active schema is **Clonker Config v4**, despite the historical implementation filename `device_config_v2.py`.

Browser saves require DEVICE + CONFIG. In SERVICE + CONFIG, inspection and Test Remote actions remain possible, but `POST /api/config` rejects persistence with HTTP 403 because the Pico filesystem is read-only.

A valid changed save checks the expected revision, validates the configuration, performs guarded filesystem writes and backup handling, publishes the new RAM configuration, rebuilds the in-memory specialized adapter selection cache, clears pending queued actions, and resets volatile power/mute direction histories. An unchanged save avoids unnecessary persistence and preserves pending work and toggle histories.

A revision conflict should be resolved by refreshing the editor and reconciling changes, not bypassing the check. Backup rotation reduces risk; it does not promise recovery from every interrupted write or sudden power loss.

**Deployment caution:** The Pico's browser-edited `/clonker/device_config.json` may be newer than the repository example. Do not overwrite it blindly while copying firmware in SERVICE mode. Likewise, keep private `settings.toml` credentials out of GitHub.

See [Configuration & Recovery](CONFIGURATION.md) for detailed validation, revision, and backup semantics.

## 7. Physical controls are not operating-mode controls

| Control | Current purpose | Status |
|---|---|---|
| GP17 maintained switch | SERVICE (USB) / DEVICE filesystem ownership | Operational |
| GP18 guarded maintained switch | CONFIG / RUN management mode | Operational |
| GP3/GP6/GP7 three-position selector | Den, Sunroom, reserved Room 3 | Operational |
| GP2 momentary Power Toggle | Selected room's `power-toggle` action | Operational; real equipment verified |
| GP8/GP9 Bourns encoder rotation | Selected room's `volume-up` / `volume-down` | Operational; real equipment verified |
| Volume encoder shaft press | `mute-toggle` | Not yet wired/integrated |
| Second Bourns encoder | Custom-action selection and press-to-run | Planned integration |
| Navigation, Back, Home, playback | Generic physical actions | Pending |
| Guarded ignition / sleep-wake | Future power-management concept | Not implemented |

The selected physical room is independent of both operating-mode switches. Room 3 is a valid physical position but not currently a configured room; attempts to dispatch there are safe no-ops rather than commands redirected to Den or Sunroom.

Power and mute toggles maintain **volatile last-successful-command direction**, not verified receiver state. Other remotes, HDMI-CEC, and equipment controls may change actual state independently. A mode switch must never transmit an equipment power command simply because its position changed.

For wiring, layout, parts, and mechanical plans, see [Hardware Design](HARDWARE_DESIGN.md).

## 8. Deployment and recovery checklist

### To update firmware from USB

1. Confirm which files changed and preserve the current Pico configuration and private settings.
2. Complete any pending browser configuration work.
3. Disconnect Pico power, set GP17 **OFF / SERVICE**, and reconnect.
4. Verify `CLONKER BOOT: SERVICE (USB)` and host write access.
5. Copy only the intended firmware files to CIRCUITPY; avoid replacing `device_config.json` or `settings.toml` unintentionally.
6. Allow writes to finish. Disconnect power completely.
7. Set GP17 **ON / DEVICE**, reconnect, and verify the DEVICE boot message.
8. Use GP18 CONFIG to inspect the editor and Test Remote; verify expected configuration and action behavior.
9. Return GP18 to RUN for ordinary standalone use.

### If a browser configuration save fails

Check GP18 first: RUN disables the endpoint. If CONFIG is active, check GP17 ownership: SERVICE makes the filesystem read-only to the Pico. Then inspect validation, revision, and filesystem diagnostics. Do not treat a rejected save as a successful deployment.

### If browser pages are unavailable

Check that GP18 selects CONFIG, that the Pico has booted and joined Wi-Fi, and that the correct local IP/port is being used. RUN intentionally stops the listener. CONFIG-mode management is a cooperative single-client service; network failures can still affect availability.

### If a physical action does nothing

Confirm the selected room is configured, its destination and action mapping are present, and the device is reachable. Room 3 currently rejects actions intentionally. Inspect queue and transport logs before assuming the GPIO input is defective. A successful TCP write or HTTP response does not guarantee equipment-state change.

## 9. Security, timing, and verification limits

- The management HTTP service has no application-level authentication. Keep port 9090 on a trusted LAN; do not forward it to the public internet.
- CircuitPython Web Workflow is separate from Clonker management HTTP. The development configuration disabled Web Workflow with `CIRCUITPY_WEB_API_PORT = 0` after observed interference; the exact cause was not conclusively established.
- Outbound generic HTTP remains bounded but blocking. Recognized fundamental Denon volume commands use a persistent TCP adapter with nonblocking 50 ms pacing eligibility, but socket connection and transmission still involve synchronous operations.
- The physical poller targets 1 ms, the action queue 10 ms, and CONFIG management HTTP 1 ms. These are target intervals, not hard real-time deadlines.
- Physical Power Toggle, room selector, and Bourns volume encoder have passed scoped real-equipment tests. Long uptime, disconnected hardware, network recovery, and all mode combinations have not been exhaustively certified.
- A commit proves source changed; deployment proves files were copied; a transport acknowledgment is not the same as observed equipment response.

## 10. Related documents

- [Architecture](ARCHITECTURE.md) — ownership boundaries, shared action path, adapter architecture.
- [Firmware, Network & Clock](FIRMWARE_NETWORK.md) — scheduler, HTTP/TCP transports, queue pacing, and tests.
- [Hardware Design](HARDWARE_DESIGN.md) — GPIO, wiring, mechanical design, and inventory.
- [Configuration & Recovery](CONFIGURATION.md) — schema, persistence, revision protection, backups.
- [Development & Deployment](DEVELOPMENT.md) — development workflow and deployment procedures.
- [Development History](DEVELOPMENT_HISTORY.md) — dated experiments and verification records.

---

**THE CLONKER 10000 — Less sleek. More CLONK.**  
**CLONK! ⚡🔩**
