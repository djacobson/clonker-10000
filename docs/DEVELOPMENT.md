# Development, Deployment & Testing

**Design reference · 15 October 2026**

## Source of truth and workflow

1. Edit in **Working Copy on iPad**, commit and push to GitHub (`djacobson/clonker-10000`).
2. On Windows 10 Lenovo Yoga, use **GitHub Desktop** → Fetch/Pull.
3. Remove GP17 jumper, **fully power-cycle into SERVICE (USB)** mode.
4. Copy updated files from `firmware/` to the matching `CIRCUITPY` paths with File Explorer. Never overwrite private `settings.toml` with the example.
5. Verify startup and USB serial REPL through `https://code.circuitpython.org/`.
6. To test firmware-side writes, ground GP17 and **fully power-cycle into DEVICE** mode.

A Ctrl+D reload is **not** a substitute for power cycling when switching filesystem ownership.

## Device and credentials

- SSID `jrtr`, reserved IP `192.168.50.12`; address is environment-specific.
- Clonker application UI: `http://192.168.50.12:9090/` while CONFIG is enabled.
- CircuitPython Web Workflow on port 80 is disabled.
- Keep Wi-Fi password and other credentials in private `settings.toml`; never commit it. `settings.example.toml` is illustrative only.

## Current testing checkpoint

**Active baseline — October 16, 2026:** Raspberry Pi Pico 2 W,
CircuitPython 10.3.1, with JSON v2 configuration loaded from
`/clonker/device_config.json`.

**Verified on Pico:** JSON v2 configuration loading and validation,
canonical serialization and revision behavior, disposable-file
persistence tests, backup rotation, fallback from damaged or missing
primary files, browser configuration loading and editing, successful
DEVICE-mode browser saves, no-change detection, SERVICE-mode
read-only browser behavior, and stale-revision conflict rejection
using two browser tabs.

The browser and firmware are now integrated with JSON v2.
The XML v1 implementation remains in the repository as a rollback
reference, but the active firmware does not use it.

**Partially verified:** Persistence and recovery safeguards have
passed selected on-device tests, but not every possible failure
scenario has been exercised.

**Not yet tested or not fully verified:** Interrupted writes and
power-loss recovery, comprehensive malformed HTTP request handling,
some HTTP-level read-only rejection cases, and complete cold
power-cycle persistence verification.

**Production-path checkpoint:** The temporary configuration test
override was removed, and the production JSON configuration path
was restored. The final quick check confirmed the Den room was
visible. Do not treat this as proof that all remaining persistence
tests have passed.

**Next development milestone:** Agree on the physical control and
device-command architecture, then implement and test it incrementally.
Keep JSON v2 configuration and persistence as the working baseline.

See [Configuration & Recovery](CONFIGURATION.md) and
[Configuration Test Record](configuration-testing.md).

## Status language

- **Verified:** observed in the actual Pico REPL/browser.
- **Implemented, unverified:** exists in current source but lacks on-device validation.
- **Planned:** design intent, not operational.

## Debugging principles

One small edit or test at a time. Capture REPL output. Prefer bounded, disposable tests. `KeyboardInterrupt` after manually stopping the app is expected.

Avoid confusing successful validation with successful persistence. A successful configuration save must be verified in flash, reflected in active memory, and retained after reboot. Record actual test results in `configuration-testing.md`.

Prefer reasonable validation that protects normal operation and persistent data. The browser is the intended user configuration interface; raw JSON editing is primarily a developer activity. Do not build a general-purpose JSON editor or elaborate compatibility framework.
