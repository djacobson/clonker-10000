# The Clonker 10000 — Architecture

**Design reference · 15 October 2026**  
**Active target:** Raspberry Pi Pico 2 W / CircuitPython 10.3.1  
**Repository:** [djacobson/clonker-10000](https://github.com/djacobson/clonker-10000)

> **Clonker controls actions, not brands. Controlled devices own their own state.**

## Mission

A tactile, Wi-Fi-first home theater remote with real knobs, switches, satisfying buttons, and eventually an audible **CLONK!** Physical controls produce generic actions; room configuration and device adapters resolve those actions to commands. No speculative shadow copy of TV/AVR power, volume, or input state.

**Priority:** responsive physical inputs → reliable device commands → maintained room selector → configuration interface → diagnostics/time → OLED and sound → battery optimization.

## Architecture at a glance

```text
Physical inputs / room selector / CONFIG switch
                  |
          Generic input events        [PLANNED]
                  |
          Action dispatcher           [PLANNED]
                  |
      Room configuration / mappings
                  |
      Network device adapters         [PLANNED]
                  |
          Roku / Denon / LG / ...

Separate low-priority service:
  CONFIG mode -> HTTP :9090 -> clock + room editor
```

**State ownership:** Physical selector and maintained switches are read from GPIO; room names/IPs/preferences come from versioned XML; actual AV state belongs to each device; debounce/queues/clock reference live in RAM. Do not write flash for switch changes or idle status.

## Two independent mode dimensions

- **SERVICE (USB) / DEVICE:** developer filesystem ownership, selected by GP17 jumper **at power-on**; power cycle required.
- **CONFIG / RUN:** user application behavior, eventually controlled by a physical maintained switch **during runtime**; no reboot intended. Currently simulated CONFIG is enabled.

See [Operating Modes](docs/OPERATING_MODES.md) and [Development & Deployment](docs/DEVELOPMENT.md).

## Implemented vs planned

**Verified on Pico:** Wi-Fi connectivity, serial REPL, GP17 filesystem ownership modes, read-only XML configuration loading, browser clock synchronization, HTTP management server on **9090**, configuration GET and POST validation, file rename replacement, disposable-file backup rotation and missing-primary recovery.

**Implemented but not fully qualified:** `.tmp` / `.bak` / `.bak.old` routines, backup validation, startup fallback to valid backup. Newly edited recovery code requires fresh on-device tests. Power-loss durability is **not guaranteed**.

**Not yet implemented:** persistent HTTP Save Configuration, physical CONFIG switch, room selector GPIO, encoder/button events, dispatcher, real AV network commands, OLED, audio, and battery management.

## Current firmware map

| File | Role |
|---|---|
| `firmware/boot.py` | GP17 filesystem ownership at cold boot |
| `firmware/code.py` | CircuitPython entry point |
| `firmware/clonker/main.py` | Loads config, starts/stops web service, cooperative loop |
| `firmware/clonker/controls/switches.py` | Simulated CONFIG switch; GPIO path future |
| `firmware/clonker/controls/pins.py` | Switch pin configuration |
| `firmware/clonker/device_config.py` | XML parser, validator, serializer, revision, backup helpers |
| `firmware/clonker/web.py` | Bounded cooperative HTTP service, port 9090 |
| `firmware/clonker/www/index.html` | Browser clock/config editor |
| `firmware/clonker/clock.py` | Monotonic and browser-synchronized clock |
| `firmware/clonker/logger.py` | Serial logging |

## Design constraints

GPIO sampling and device command responsiveness outrank HTTP management. Network work must be bounded; slow clients or devices must not stall control capture. `web.poll()` handles a limited unit of work per call; the main loop schedules it about every 10 ms when CONFIG is active. This is **not** a proven encoder-latency guarantee.

Wi-Fi management is trusted-LAN-only, not authenticated application security. Do not expose port 9090 to the internet. CircuitPython Web Workflow on port 80 is disabled in private `settings.toml` to avoid suspected socket conflicts.

## Reference documents

- [Operating Modes](docs/OPERATING_MODES.md) — SERVICE (USB), DEVICE, CONFIG, RUN
- [Configuration & Recovery](docs/CONFIGURATION.md) — XML, API, backup safety
- [Firmware & Network](docs/FIRMWARE_NETWORK.md) — cooperative loop, HTTP, clock, logging
- [Hardware & Controls](docs/HARDWARE_CONTROLS.md) — physical design and action model
- [Development & Deployment](docs/DEVELOPMENT.md) — iPad/Windows/Pico workflow and test plan
- [Terminology Audit](docs/TERMINOLOGY_AUDIT.md) — existing USB-mode references to update
