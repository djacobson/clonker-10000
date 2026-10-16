# Firmware, HTTP & Clock

**Design reference · 15 October 2026**

## Runtime

Raspberry Pi Pico 2 W, CircuitPython 10.3.1, dedicated 2.4 GHz Wi-Fi SSID `jrtr`, reserved IP **192.168.50.12**, hostname configuration in `settings.toml`. The observed standalone connectivity test is encouraging but not a reliability guarantee.

`code.py` starts `clonker.main.main()`. `main.py` loads XML, logs three rooms, then repeatedly checks the simulated CONFIG switch and services HTTP when enabled. Priority placeholders exist for GPIO, dispatcher, and timers; these are **not implemented control paths**.

## Management HTTP server

Application server: **`http://192.168.50.12:9090/`** on trusted LAN. CircuitPython Web Workflow (port 80) is **disabled** with `CIRCUITPY_WEB_API_PORT = 0` due to suspected socket conflicts. Do not expose management port through router port forwarding.

`web.py` uses `wifi`, `socketpool`, and `json`, with one client at a time, nonblocking socket attempts, bounded request buffer (**2048 bytes**), I/O chunk (**512 bytes**), and idle client timeout (**4 seconds**). `main.py` schedules web polls at **0.01 seconds** when CONFIG is active. These settings are implementation facts, **not latency guarantees**.

| Route | Current behavior |
|---|---|
| `GET /` | HTML/JS UI from `/clonker/www/index.html` |
| `GET /api/clock` | Clock source and timestamp JSON |
| `POST /api/clock?utc=...` | Browser UTC synchronization, RAM only |
| `GET /api/config` | Current rooms, revision, filesystem writable flag |
| `POST /api/config` | DEVICE: validate only; SERVICE (USB): 403 |

A client timeout/stall has been observed during tests; HTTP tracing is available with `HTTP_DIAGNOSTICS` and normally disabled. Keep web service low priority when physical input code arrives.

## Clock and logs

Clock fallback: monotonic `DEFAULTTIME` uptime. Browser button sets UTC reference in RAM (`BROWSER`); it does not write configuration. NTP is planned but not implemented. Logger emits serial DEBUG/INFO/WARNING/ERROR; no persistent logging or flash writes.

## Planned control pipeline

GPIO sampling and debounce → generic input events → dispatcher → room/action lookup → bounded device adapter commands. Prefer Denon for AVR speaker volume, Roku for navigation, LG for TV-specific commands. Controlled devices remain authoritative; a successful network send does not prove the action occurred. Group/BOTH semantics remain unfinalized.
