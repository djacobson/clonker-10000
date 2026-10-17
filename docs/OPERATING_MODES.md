# Operating Modes — Clonker 10000

**Design reference · 15 October 2026**

The two mode dimensions are independent. **SERVICE (USB) / DEVICE** decides who may write the CircuitPython filesystem; **CONFIG / RUN** decides whether the remote offers the application management interface.

| | SERVICE (USB) / DEVICE | CONFIG / RUN |
|---|---|---|
| Audience | Developer/maintenance | End user |
| Controlled by | Internal GP17-to-GND jumper | Future external maintained switch |
| Evaluated | `boot.py` on full power cycle | `main.py` at runtime |
| Reboot needed | **Yes** | **No** (design intent) |
| Purpose | Filesystem write ownership | Enable/disable configuration service |

## SERVICE (USB) mode — jumper open

- GP17 is pulled HIGH internally; the current `boot.py` prints `CLONKER BOOT: SERVICE (USB) mode (jumper OPEN)`
- Host Windows can write to `CIRCUITPY` for firmware deployment.
- CircuitPython application filesystem is read-only; configuration POST is rejected with HTTP **403**.
- USB serial REPL remains available.

## DEVICE mode — jumper grounded

- GP17 (physical pin 22) connected to GND (physical pin 23).
- `boot.py` calls `storage.remount('/', readonly=False)`.
- CircuitPython may write XML and test files; host Windows has read-only filesystem access.
- USB serial REPL remains available.
- Mode changes require a **full power cycle**, not merely Ctrl+D or soft reload.

## CONFIG mode — simulated today

`controls/switches.py` currently returns simulated `True` while `CONFIG_SWITCH_PIN` is unset. `main.py` starts Clonker HTTP on **port 9090**, allowing clock synchronization and configuration inspection, editing, and saving when the filesystem is writable. CONFIG is **not** equivalent to DEVICE: CONFIG may be active while the filesystem is read-only in SERVICE (USB).

## RUN mode — planned physical behavior

When the simulated or future physical switch returns false, `main.py` calls `web.stop()` and closes the listener; Wi-Fi remains available for eventual theater commands. Input handling must remain active in either mode. A physical CONFIG/RUN switch has not yet been wired or validated.

## Configuration saving

Persistent configuration saves require a writable filesystem and a valid submitted configuration.

In the active JSON v2 implementation:

- DEVICE mode permits firmware filesystem writes.
- SERVICE (USB) mode rejects configuration saves with HTTP 403.
- CONFIG mode enables the browser management service.
- RUN mode disables the browser management service.
- JSON v2 browser saves, backup rotation, no-change detection, and
  stale-revision handling have passed initial on-device tests.

The intended operational combination for browser configuration
saves is **DEVICE + CONFIG**.

The CONFIG/RUN switch is an internal application control. Moving it
does not send an HTTP request to any television, receiver, or
streaming device.

The separate `power-toggle` fundamental action is reserved for
controlling external equipment through its configured command.
Actual device-command execution has not yet been implemented.

The physical CONFIG/RUN switch has not yet been installed or tested;
the current runtime mode is simulated.

## Boot / deployment cautions

Never change the jumper while relying on a soft reload; use a power cycle. Keep private `settings.toml` out of Git. Do not confuse the separate CircuitPython Web Workflow with Clonker's port-9090 application server; Web Workflow is disabled with `CIRCUITPY_WEB_API_PORT = 0`.
