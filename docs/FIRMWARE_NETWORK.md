# Firmware, HTTP & Clock

**Design reference · 15 October 2026**

## Runtime

Raspberry Pi Pico 2 W, CircuitPython 10.3.1, dedicated 2.4 GHz Wi-Fi SSID `jrtr`, reserved IP **192.168.50.12**, hostname configuration in `settings.toml`. The observed standalone connectivity test is encouraging but not a reliability guarantee.

`code.py` starts `clonker.main.main()`. `main.py` loads the active
JSON v2 configuration from `/clonker/device_config.json`, logs the
three rooms and their device endpoints, then repeatedly checks the
simulated CONFIG switch and services HTTP when enabled.

Priority placeholders exist for GPIO, dispatcher, and timers; these
are **not yet implemented control paths**.

## Management HTTP server

Application server: **`http://192.168.50.12:9090/`** on trusted LAN. CircuitPython Web Workflow (port 80) is **disabled** with `CIRCUITPY_WEB_API_PORT = 0` due to suspected socket conflicts. Do not expose management port through router port forwarding.

`web.py` uses `wifi`, `socketpool`, and `json`, with one client at a
time, nonblocking socket operations, a bounded total request buffer
(**10,240 bytes**), a maximum HTTP header size (**2,048 bytes**),
an I/O chunk size (**512 bytes**), and an idle client timeout
(**4 seconds**). Configuration POST bodies are separately limited
relative to the JSON v2 configuration maximum of **8,192 bytes**.

`main.py` schedules web polls approximately every **0.01 seconds**
when CONFIG is active. These settings are implementation facts,
**not latency guarantees**.

CircuitPython's `errno.EAGAIN` is used for nonblocking socket
operations; `errno.EWOULDBLOCK` is not available in the tested runtime.

| Route | Current behavior |
|---|---|
| `GET /` | HTML/JavaScript UI from `/clonker/www/index.html` |
| `GET /api/clock` | Clock source and timestamp JSON |
| `POST /api/clock?utc=...` | Browser UTC synchronization, RAM only |
| `GET /api/config` | Active JSON v2 configuration, revision, and filesystem writable flag |
| `POST /api/config` | DEVICE: validate and persist JSON v2 configuration; SERVICE (USB): HTTP 403 |

JSON v2 browser loading, editing, saving, no-change detection, and
stale-revision conflict handling have been tested on the Pico.
The backend checks filesystem writability, validates the submitted
configuration, checks its expected revision and the active configuration
file path, detects out-of-band disk changes, and performs verified
replacement with rotating backups.

The JSON v2 browser integration and expanded HTTP request limits are
implemented. Additional malformed-request and power-interruption
testing remains pending. The older XML v1 configuration engine remains
in the repository for rollback but is not used by the active HTTP
configuration endpoints.

The management server is a configuration service, not the eventual device-command dispatcher. The CONFIG/RUN switch enables or disables that service internally and does not issue an HTTP action.

A client timeout/stall has been observed during tests; HTTP tracing is available with `HTTP_DIAGNOSTICS` and normally disabled. Keep web service low priority when physical input code arrives.

## Clock and logs

Clock fallback: monotonic `DEFAULTTIME` uptime. Browser button sets UTC reference in RAM (`BROWSER`); it does not write configuration. NTP is planned but not implemented. Logger emits serial DEBUG/INFO/WARNING/ERROR; no persistent logging or flash writes.

## Planned control pipeline

GPIO sampling and debounce → generic input events → dispatcher → room/action lookup → bounded device adapter commands. Prefer Denon for AVR speaker volume, Roku for navigation, LG for TV-specific commands. Controlled devices remain authoritative; a successful network send does not prove the action occurred.

GPIO sampling and debounce → generic input events → action dispatcher → selected room's fundamental or user-defined command → bounded HTTP request to the configured target device.

A fundamental command has a fixed action ID and configurable target, HTTP method, and path. An empty path or unconfigured target IP produces a valid no-op. User-defined commands will extend this simple command model without requiring a scripting language or graphical shortcut editor.

Controlled devices remain authoritative for their actual state. A successful network request does not prove the requested action occurred. Group/BOTH semantics remain unfinalized.
