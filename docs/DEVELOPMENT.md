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

**Verified on Pico — October 16, 2026:** Configuration v1 XML loading, browser editing, persistent saves, no-change detection, backup rotation, active-memory updates, and persistence after soft reboot.

The original Den configuration was restored after testing.

**Implemented; additional testing pending:** Stale revision rejection, malformed configuration rejection through HTTP, read-only filesystem save protection, and recovery from interrupted writes.

**Next development milestone:** Implement and test the JSON v2 configuration engine while preserving the working XML v1 firmware as a rollback point. Validate the JSON schema and serialization before integrating persistence and browser editing.

The JSON v2 fixture is committed at `firmware/clonker/device_config.json`, but the running firmware does not yet consume it.

See [Configuration & Recovery](CONFIGURATION.md) and [Configuration Test Record](configuration-testing.md).

## Status language

- **Verified:** observed in the actual Pico REPL/browser.
- **Implemented, unverified:** exists in current source but lacks on-device validation.
- **Planned:** design intent, not operational.

## Debugging principles

One small edit or test at a time. Capture REPL output. Prefer bounded, disposable tests. `KeyboardInterrupt` after manually stopping the app is expected.

Avoid confusing successful validation with successful persistence. A successful configuration save must be verified in flash, reflected in active memory, and retained after reboot. Record actual test results in `configuration-testing.md`.

Prefer reasonable validation that protects normal operation and persistent data. The browser is the intended user configuration interface; raw JSON editing is primarily a developer activity. Do not build a general-purpose JSON editor or elaborate compatibility framework.
