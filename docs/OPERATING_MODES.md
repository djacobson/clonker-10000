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

- GP17 pulled HIGH internally; boot message should read `CLONKER BOOT: SERVICE (USB) mode (jumper OPEN)` **after the planned string update**.
- Host Windows can write to `CIRCUITPY` for firmware deployment.
- CircuitPython application filesystem is read-only; configuration POST is rejected with HTTP **403**.
- USB serial REPL remains available.
- **Current source still prints `USB mode`**; see terminology audit. The proposed name is a documentation convention until code strings are changed.

## DEVICE mode — jumper grounded

- GP17 (physical pin 22) connected to GND (physical pin 23).
- `boot.py` calls `storage.remount('/', readonly=False)`.
- CircuitPython may write XML and test files; host Windows has read-only filesystem access.
- USB serial REPL remains available.
- Mode changes require a **full power cycle**, not merely Ctrl+D or soft reload.

## CONFIG mode — simulated today

`controls/switches.py` currently returns simulated `True` while `CONFIG_SWITCH_PIN` is unset. `main.py` starts Clonker HTTP on **port 9090**, allowing clock synchronization and configuration inspection/validation. CONFIG is **not** equivalent to DEVICE: CONFIG may be active while the filesystem is read-only in SERVICE (USB).

## RUN mode — planned physical behavior

When the simulated or future physical switch returns false, `main.py` calls `web.stop()` and closes the listener; Wi-Fi remains available for eventual theater commands. Input handling must remain active in either mode. A physical CONFIG/RUN switch has not yet been wired or validated.

## Intended save gate

Persistent configuration saves should require **DEVICE + CONFIG** and server-side validation, not merely an enabled browser button. Currently POST `/api/config` **validates but does not persist**. The backend currently checks filesystem writability; full save authorization and revision conflict behavior must be verified during integration.

## Boot / deployment cautions

Never change the jumper while relying on a soft reload; use a power cycle. Keep private `settings.toml` out of Git. Do not confuse the separate CircuitPython Web Workflow with Clonker's port-9090 application server; Web Workflow is disabled with `CIRCUITPY_WEB_API_PORT = 0`.
