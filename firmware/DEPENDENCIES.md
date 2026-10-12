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

## Deployment notes

Application modules live under /clonker/.

Web interface files live under /clonker/www/.

External libraries, when required, belong
under /lib/ on CIRCUITPY.

Do not overwrite the Pico’s private settings.toml
during deployment.

CircuitPython libraries must be compatible with
the installed CircuitPython major version.
