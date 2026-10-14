# Clonker 10000 — Firmware Dependencies

## Target hardware
- Raspberry Pi Pico 2 W
- CircuitPython 10.3.1

## Built-in CircuitPython modules

No separate installation required.

| Module | Used by |
|—|—|
| time | clock.py, main.py |
| os | web.py |
| json | Planned HTTP API |
| wifi | Planned application HTTP server |
| socketpool | Planned application HTTP server |

## External CircuitPython libraries

None currently required.

Future dependencies will be listed here with
their versions and installation locations.

## Application modules

| Module | Depends on |
|—|—|
| clock.py | time |
| logger.py | clonker.clock |
| web.py | clonker.clock, clonker.logger, os |
| main.py | time |

## CircuitPython Development Notes

**Web Workflow conflict:** CircuitPython’s built-in Web Workflow appeared to interfere with Clonker’s HTTP server, causing intermittent hangs and crashes. Disabling Web Workflow with `CIRCUITPY_WEB_API_PORT = 0` in `settings.toml` and running Clonker on port `9090` resolved the crashes observed during testing. The exact underlying conflict remains unconfirmed.

**USB serial console:** Connecting the CircuitPython Web Editor’s serial console appears to interrupt an already-running Clonker (similar to Ctrl+C). Clonker auto-starts normally on cold boot. After connecting the console, press **Ctrl+D** to soft-reboot and restart Clonker with serial logging enabled.

## Deployment notes

Application modules live under /clonker/.

Web interface files live under /clonker/www/.

External libraries, when required, belong
under /lib/ on CIRCUITPY.

Do not overwrite the Pico’s private settings.toml
during deployment.

CircuitPython libraries must be compatible with
the installed CircuitPython major version.
