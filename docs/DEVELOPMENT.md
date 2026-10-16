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

**Completed previously:** rename-over-existing behavior, three-generation backup rotation using disposable text files, and basic missing-primary rename recovery. **Not yet completed with latest firmware:** full XML-aware fallback and recovery tests, corrupted-backup scenarios, unexpected reset/power loss, and actual HTTP persistence.

**Next:** use disposable valid XML files in DEVICE mode; inspect each resulting file. Keep `/clonker/device_config.xml` and its backups untouched. Test the current backup logic, then verify `load()` fallback with safely controlled test paths or dedicated fixture functions. Only afterward integrate POST persistence.

## Status language

- **Verified:** observed in the actual Pico REPL/browser.
- **Implemented, unverified:** exists in current source but lacks on-device validation.
- **Planned:** design intent, not operational.

## Debugging principles

One small edit or test at a time. Capture REPL output. Prefer bounded, disposable tests. `KeyboardInterrupt` after manually stopping the app is expected. Avoid interpreting an HTTP 200 `Configuration validated; not saved` as persistence. Record findings in docs after each verified milestone.
