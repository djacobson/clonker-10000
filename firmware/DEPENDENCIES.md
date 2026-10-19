# THE CLONKER 10000 — Firmware Dependencies

**Updated:** October 19, 2026  
**Target:** Raspberry Pi Pico 2 W (RP2350)  
**Runtime:** CircuitPython 10.3.1  
**Status:** Current browser configuration and logging-only action dispatcher operational

> Minimal dependencies. Maximum CLONK.

---

## 1. Purpose

This document identifies the runtime, built-in CircuitPython modules, project modules, and external libraries required by the current firmware.

It also records compatibility and deployment considerations for future development.

The dependency inventory describes the current implementation, not every feature planned for the finished remote.

---

## 2. Target Hardware and Runtime

| Component | Current selection |
|---|---|
| Microcontroller | Raspberry Pi Pico 2 W |
| Processor family | RP2350 |
| Firmware runtime | CircuitPython 10.3.1 |
| Network interface | Built-in Wi-Fi |
| Management HTTP port | 9090 |
| Configuration format | JSON v2 |
| Application directory | `/clonker/` |
| Web assets | `/clonker/www/` |
| External library directory | `/lib/` |

The earlier ESP32-S3 design is historical.

Current firmware is developed and tested for the Pico 2 W.

---

## 3. Built-in CircuitPython Modules

**No separate installation required.**

The following built-in modules are imported by the current firmware.

| Module | Used by | Purpose |
|---|---|---|
| `board` | `boot.py` | GP17 pin reference |
| `digitalio` | `boot.py` | Jumper input and pull-up |
| `storage` | `boot.py`, `web.py` | Filesystem ownership and write-capability checks |
| `time` | `main.py`, `web.py`, `clock.py` | Cooperative timing, timeouts, clock functions |
| `wifi` | `web.py` | Wi-Fi radio and network information |
| `socketpool` | `web.py` | Application HTTP server sockets |
| `json` | `web.py`, `device_config_v2.py` | API payloads and JSON configuration |
| `os` | `device_config_v2.py` | Filesystem operations |
| `errno` | `web.py` | Nonblocking socket error handling |

This table reflects imports observed in the October 19 repository.

Standard built-in modules should not be copied into `/lib/`.

---

## 4. External CircuitPython Libraries

**None currently required.**

The existing firmware uses built-in CircuitPython facilities and local project modules.

The management HTTP server is implemented in project code rather than through an installed web framework.

The JSON configuration engine also uses built-in modules.

### Future libraries

If future hardware or networking features require external libraries:

1. Identify the exact library and version.
2. Verify compatibility with the installed CircuitPython major version.
3. Document the required files.
4. Install them under `/lib/` on CIRCUITPY.
5. Record the reason for adding the dependency.
6. Test on the actual Pico before declaring support.

Prefer the smallest practical dependency set.

Do not add libraries merely because they are commonly used in other CircuitPython projects.

---

## 5. Project Module Dependencies

The Clonker's own Python modules live under:

`/clonker/`

They are deployed from the repository's `firmware/clonker/` directory.

| Module | Local dependencies | Responsibility |
|---|---|---|
| `code.py` | `clonker.main` | Application entry point |
| `clonker/main.py` | `logger`, `web`, `controls.switches`, `device_config_v2` | Main application loop |
| `clonker/web.py` | `clock`, `logger`, `device_config_v2`, `actions` | HTTP server and APIs |
| `clonker/actions.py` | `logger`, `device_config_v2` | Logging-only fundamental action dispatcher |
| `clonker/device_config_v2.py` | None | Configuration validation and persistence |
| `clonker/clock.py` | None | Clock support |
| `clonker/logger.py` | `clock` | Timestamped diagnostics |
| `clonker/controls/switches.py` | `controls.pins` | CONFIG/RUN switch abstraction |
| `clonker/controls/pins.py` | None | Hardware pin placeholders |

The table lists local project imports; built-in imports are described in Section 3.

### Current action dispatcher

`clonker/actions.py` currently validates and logs browser action requests.

It does not yet make outbound HTTP requests to receivers, televisions, or streaming devices.

Therefore, the current dependency inventory does not include a dedicated outbound HTTP client library.

That decision should be revisited when the real device-command transport is implemented.

---

## 6. Application Architecture

The current application path is:

```text
CircuitPython startup
        |
        v
boot.py
        |
        v
code.py
        |
        v
clonker.main
        |
        +--> device_config_v2
        |
        +--> clock / logger
        |
        +--> controls.switches
        |
        +--> web
               |
               +--> JSON configuration API
               |
               +--> Clock API
               |
               +--> Browser Test Remote
                         |
                         v
                    actions.dispatch
                         |
                         v
                    Logging-only result
```

The planned next step extends `actions.dispatch()` with outbound HTTP transport.

Physical controls will eventually invoke the same shared action dispatcher.

---

## 7. CircuitPython Compatibility Notes

CircuitPython is intentionally smaller than desktop Python.

Do not assume that every CPython module, function, keyword argument, or constant is available.

### JSON compatibility

During JSON v2 development, the firmware encountered an unsupported `ensure_ascii` argument to `json.dumps()`.

The implementation was corrected and subsequently tested.

### Socket error compatibility

During browser integration, the application encountered:

```text
AttributeError: 'module' object has no attribute 'EWOULDBLOCK'
```

The current CircuitPython environment provided `errno.EAGAIN`.

The socket handling code was corrected.

### General rule

Before introducing a new networking or serialization dependency:

- Check CircuitPython support.
- Check the installed runtime version.
- Test the exact API on the Pico.
- Avoid relying on desktop-only functionality.
- Keep memory use and blocking operations bounded.

These compatibility discoveries are recorded in [Development History](../docs/DEVELOPMENT_HISTORY.md).

---

## 8. CircuitPython Web Workflow

The built-in CircuitPython Web Workflow was disabled after apparent interference with the Clonker application HTTP server.

The current private `settings.toml` includes:

```toml
CIRCUITPY_WEB_API_PORT = 0
```

The Clonker application server operates on port `9090`.

Disabling Web Workflow resolved the observed instability during testing.

The exact underlying cause was not conclusively established.

Do not describe the suspected conflict as a proven CircuitPython defect.

---

## 9. USB Serial Console

The CircuitPython browser-based serial console is useful for:

- Startup diagnostics.
- Exception traces.
- Configuration inspection.
- Action-dispatch logging.
- REPL experiments.

Connecting the console may interrupt the running application.

After connecting, Ctrl+D can soft-reload the application and restart logging.

**Important:** Ctrl+D does not re-evaluate boot-time GP17 filesystem ownership.

Changing SERVICE/DEVICE mode requires a full power cycle.

See [Operating Modes](../docs/OPERATING_MODES.md).

---

## 10. Firmware Deployment

Repository source:

`firmware/`

Pico filesystem destination:

`/`

Examples:

| Repository | CIRCUITPY |
|---|---|
| `firmware/boot.py` | `/boot.py` |
| `firmware/code.py` | `/code.py` |
| `firmware/clonker/main.py` | `/clonker/main.py` |
| `firmware/clonker/web.py` | `/clonker/web.py` |
| `firmware/clonker/actions.py` | `/clonker/actions.py` |
| `firmware/clonker/device_config_v2.py` | `/clonker/device_config_v2.py` |
| `firmware/clonker/www/index.html` | `/clonker/www/index.html` |
| `firmware/clonker/www/remote.html` | `/clonker/www/remote.html` |

Deploy through SERVICE (USB) mode when the host needs to write CIRCUITPY.

Do not blindly overwrite the Pico's working configuration or private settings.

### Private settings

`settings.toml` contains network credentials and runtime settings.

Never commit real credentials to the repository.

Never overwrite the Pico's private settings during routine firmware deployment.

### External libraries

If future dependencies are added, place the appropriate CircuitPython-compatible library files under:

`/lib/`

Use versions compatible with the installed CircuitPython runtime.

---

## 11. Upcoming Outbound HTTP Dependencies

The next development milestone requires real HTTP commands to network-connected equipment.

Current requirements include:

- HTTP GET.
- HTTP POST.
- Configurable IPv4 endpoint and port.
- Configurable command path.
- Connection timeout.
- Response timeout.
- Explicit success/failure reporting.
- Safe socket cleanup.
- Nonblocking or tightly bounded execution appropriate for the cooperative main loop.

The initial implementation should favor a small, understandable transport.

Possible approaches include direct `socketpool` usage or a compatible HTTP client library.

**No transport choice has been finalized in this document.**

The actual choice should be made after reviewing the current firmware and testing a minimal device command.

Connection reuse, request queues, retries, and caching should be added only when demonstrated requirements justify them.

---

## 12. Dependency Maintenance Policy

Update this document whenever:

- The CircuitPython runtime changes.
- A built-in module is added or removed.
- An external library is introduced.
- An external library version changes.
- A new hardware driver is integrated.
- The networking implementation changes.
- A previously planned dependency becomes operational.

For each external dependency, record:

- Library name.
- Version.
- Source.
- Installation path.
- Modules using it.
- Compatibility requirements.
- Actual Pico test status.

Do not label a dependency operational merely because it has been proposed or copied to the filesystem.

---

## References

- [Development & Deployment](../docs/DEVELOPMENT.md)
- [Architecture](../docs/ARCHITECTURE.md)
- [Firmware & Networking](../docs/FIRMWARE_NETWORK.md)
- [Operating Modes](../docs/OPERATING_MODES.md)
- [Development History](../docs/DEVELOPMENT_HISTORY.md)

---

**THE CLONKER 10000**

*Designed by David Jacobson.*

**CLONK! ⚡🔩**
