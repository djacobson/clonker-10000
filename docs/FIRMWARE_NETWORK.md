# The Clonker 10000 — Firmware, HTTP & Clock

**Design reference:** Updated October 19, 2026  
**Hardware:** Raspberry Pi Pico 2 W  
**Runtime:** CircuitPython 10.3.1  
**Status:** Wi-Fi, CONFIG HTTP service, JSON v2 configuration, browser clock, and logging-only action dispatch operational. Outbound device HTTP pending.

> **One monster, two directions of HTTP traffic: inbound management and outbound equipment control.**

## 1. Runtime Overview

The Clonker 10000 currently runs on a Raspberry Pi Pico 2 W using CircuitPython 10.3.1.

Development network:

- Wi-Fi: dedicated 2.4 GHz SSID `jrtr`.
- Reserved Pico IP: `192.168.50.12`.
- Hostname and credentials: configured through private `settings.toml`.
- Management interface: `http://192.168.50.12:9090/`.
- Browser Test Remote: `http://192.168.50.12:9090/remote.html`.

These are local development settings, not universal defaults.

The firmware uses a cooperative main loop rather than a threaded application architecture.

Its current responsibilities are:

- Load the validated JSON v2 configuration.
- Initialize and use Wi-Fi connectivity.
- Log configured rooms and endpoints.
- Evaluate the simulated CONFIG/RUN switch.
- Start and stop the management HTTP listener.
- Service incoming HTTP requests.
- Provide browser clock synchronization.
- Support configuration editing and persistence.
- Route browser Test Remote requests to a logging-only dispatcher.

Physical control scanning, real outbound equipment commands, and periodic background tasks are not yet operational.

## 2. Firmware Entry and Main Loop

CircuitPython starts:

`firmware/code.py`

which invokes:

`clonker.main.main()`

The application entry point is:

`firmware/clonker/main.py`

### Startup sequence

The main application:

1. Logs the Clonker startup banner.
2. Loads JSON v2 configuration through `device_config_v2.load()`.
3. Logs successful three-room configuration loading.
4. Logs each room ID and name.
5. Logs configured TV, AVR, and streaming endpoints.
6. Logs the number of fundamental actions per room.
7. Enters the cooperative application loop.

The active configuration is loaded once at startup.

Successful browser configuration saves update the configuration engine's authoritative in-memory state without requiring a reboot.

The dispatcher reads current configuration through `device_config.room()` rather than retaining a stale startup snapshot.

### Cooperative scheduling

The main loop currently uses:

```python
WEB_POLL_INTERVAL = 0.01
```

When CONFIG is enabled, the loop attempts to poll the management HTTP service approximately every 10 milliseconds.

This is a scheduling interval, **not a guaranteed response time**.

The intended future priority order is:

1. Physical GPIO input capture.
2. Generic action/event dispatch.
3. Timers and periodic tasks.
4. CONFIG management HTTP polling.

The main loop contains placeholders for these future priorities.

The browser dispatcher is already callable through `web.py`, but it is not yet a physical-input event loop.

### CONFIG/RUN transitions

The main loop checks:

```python
switches.config_enabled()
```

When CONFIG becomes enabled, it starts the HTTP listener.

When CONFIG becomes disabled, it stops the listener.

The current switch state is simulated and defaults to CONFIG enabled.

The physical CONFIG/RUN switch is not yet connected.

Future RUN operation must preserve Wi-Fi and the loaded configuration so outbound equipment commands can continue without the management server.

The current implementation does not yet establish end-to-end RUN-mode device control.

## 3. Independent Operating Modes

Clonker has two separate operating-mode dimensions.

### SERVICE (USB) / DEVICE

Selected by GP17 at boot.

- GP17 open: SERVICE (USB), host-writable filesystem.
- GP17 grounded: DEVICE, Pico-writable filesystem.

The selection is implemented in `firmware/boot.py`.

Changing SERVICE/DEVICE requires a full power cycle.

In SERVICE mode, the Pico cannot persist configuration changes to its read-only filesystem.

In DEVICE mode, the Pico can persist configuration changes.

### CONFIG / RUN

Controls application behavior, not filesystem ownership.

- CONFIG: management HTTP service enabled.
- RUN: management HTTP service disabled.

CONFIG/RUN is currently simulated in firmware.

The future physical maintained switch should change this mode during runtime without requiring a reboot.

**DEVICE is not synonymous with RUN.**

See [Operating Modes](OPERATING_MODES.md).

## 4. Management HTTP Server

The inbound HTTP server is implemented in:

`firmware/clonker/web.py`

It listens on TCP port:

`9090`

The server is intended for a trusted local network.

It does not implement application-level authentication.

Do not expose this port through internet port forwarding.

CircuitPython Web Workflow on port 80 is disabled in private `settings.toml` using:

```toml
CIRCUITPY_WEB_API_PORT = 0
```

This was adopted because of suspected socket conflicts during development.

The Clonker management server is separate from CircuitPython Web Workflow.

### Server implementation

The management server uses:

- `wifi`
- `socketpool`
- `json`
- `errno`
- `storage`

It accepts one active client at a time.

Its `poll()` function advances a limited unit of work per call:

- Accept a client.
- Receive a request chunk.
- Prepare a response.
- Send a response chunk.
- Close the completed or failed connection.

The implementation retains connection state between polls.

It uses nonblocking socket operations to avoid waiting indefinitely for an idle browser client.

A slow or stalled client can still consume server capacity until timeout.

The server does not provide concurrent request processing.

### HTTP limits

Current firmware constants:

| Constant | Value |
|---|---:|
| `PORT` | `9090` |
| `MAX_REQUEST_BYTES` | `10240` |
| `MAX_HEADER_BYTES` | `2048` |
| `IO_CHUNK_BYTES` | `512` |
| `CLIENT_TIMEOUT_SECONDS` | `4.0` |
| `HTTP_DIAGNOSTICS` | `False` |

The JSON configuration engine separately limits serialized configuration to 8192 UTF-8 bytes.

Configuration POST requests require a valid Content-Length and a complete body before JSON parsing.

The server bounds request accumulation before processing.

### CircuitPython nonblocking sockets

The tested runtime uses:

```python
errno.EAGAIN
```

for would-block conditions.

The implementation does not assume that `errno.EWOULDBLOCK` is available.

The helper `_socket_would_block()` recognizes `EAGAIN`.

This is a CircuitPython compatibility decision based on earlier testing.

### HTTP response behavior

The server generates responses with:

- HTTP status.
- Content-Type.
- Content-Length.
- Cache-Control: no-store.
- Connection: close.

Responses are sent incrementally using bounded chunks.

Connections are closed after completion or failure.

These are implementation characteristics, not a guarantee that every malformed request or network failure has been tested.

## 5. Management HTTP Routes

The active server supports the following routes.

| Request | Behavior |
|---|---|
| `GET /` | Serve configuration and clock page |
| `GET /remote.html` | Serve browser Test Remote |
| `GET /api/clock` | Return clock source and timestamp |
| `POST /api/clock?utc=...` | Synchronize clock from browser |
| `GET /api/config` | Return active JSON v2 configuration and metadata |
| `POST /api/config` | Validate and save JSON v2 configuration |
| `POST /api/action?room=...&action=...` | Dispatch a fundamental action to logging stub |

Unknown routes return HTTP 404.

### GET /api/config

Returns the active configuration along with:

- `revision`
- `filesystem_writable`

These are response metadata, not persisted JSON configuration fields.

The configuration engine returns a validated copy of active data.

### POST /api/config

The endpoint:

1. Rejects writes when the Pico filesystem is read-only.
2. Parses the submitted JSON.
3. Extracts the expected configuration revision.
4. Validates the configuration.
5. Checks revision and on-disk consistency.
6. Detects unchanged configuration.
7. Performs verified persistence when changed.
8. Returns save status and the current revision.

In SERVICE (USB) mode, write attempts receive HTTP 403.

In DEVICE mode, valid writes may proceed.

A stale revision is rejected and the browser directs the user to refresh.

### POST /api/action

Example:

```text
POST /api/action?room=room-1&action=volume-up
```

The browser Test Remote uses this route to request a generic action.

The route:

1. Parses the room and action parameters.
2. Rejects malformed parameter structures.
3. Calls `actions.dispatch(room_id, action_id)`.
4. Returns the dispatcher's JSON result.

The parser uses fixed ASCII identifiers rather than `urllib.parse`, which was unsuitable for the tested CircuitPython environment.

The dispatcher independently validates room and action IDs.

**This endpoint does not currently send an HTTP request to AV equipment.**

## 6. Browser Test Remote

The Test Remote is implemented in:

`firmware/clonker/www/remote.html`

It provides a browser interface for all fourteen fundamental actions.

The user can select a room and trigger actions without physical hardware.

This gives Clonker a working development harness for the next stage.

### Current request flow

```text
Browser Test Remote
        |
        | POST /api/action
        v
web.py
        |
        v
actions.dispatch()
        |
        v
device_config.room(room_id)
        |
        v
Validate action configuration
        |
        v
Serial log + JSON stub response
```

The current response indicates that a valid action was accepted by the logging stub.

Example status fields include:

```json
{
  "ok": true,
  "status": "stub",
  "room": "room-1",
  "room_name": "Den",
  "action": "volume-up",
  "configured": true,
  "message": "STUB: Den / volume-up (logged; no command sent)"
}
```

This is an illustrative response for a configured Den volume action.

`ok: true` means the stub accepted the request.

It does **not** mean a network command was transmitted or that the equipment responded.

### Verification milestone

On October 19, 2026, the browser Test Remote and logging-only dispatcher were exercised on the Pico.

All fourteen fundamental action buttons were reported working in the stub test.

This established the browser-to-dispatcher path without risking unintended AV commands.

The next milestone is to extend that shared dispatcher to perform real outbound HTTP requests.

## 7. Shared Action Dispatcher

The current dispatcher is implemented in:

`firmware/clonker/actions.py`

It currently:

- Validates the room ID.
- Validates the action ID.
- Reads the current room configuration.
- Resolves the action's target category.
- Checks whether the target endpoint is configured.
- Checks whether command paths are present.
- Logs the action.
- Returns a JSON-serializable stub result.

For ordinary actions, it checks the configured `path`.

For toggles, it considers `on_path` and `off_path` as candidate paths.

It does not yet choose an ON/OFF direction.

### Current limitations

The dispatcher does not:

- Open outbound network connections.
- Send HTTP GET or POST commands.
- Parse device responses.
- Maintain toggle command history.
- Query actual device state.
- Queue or retry failed commands.

These capabilities must not be inferred from the presence of configured command paths.

### Shared dispatcher principle

Future physical buttons and encoders should call the same dispatcher used by the browser Test Remote.

Physical control code must not contain Denon, Roku, or LG command syntax.

The dispatcher resolves generic actions against current JSON v2 configuration.

The outbound transport handles HTTP communication.

This preserves the core principle:

**Clonker controls actions, not brands.**

## 8. JSON v2 Configuration and Persistence

The active configuration engine is:

`firmware/clonker/device_config_v2.py`

It provides:

- Three fixed rooms.
- Three optional device endpoints per room.
- Fourteen fundamental actions per room.
- GET/POST method configuration.
- Ordinary command paths.
- Paired ON/OFF toggle paths.
- Strict structural validation.
- Compact deterministic JSON serialization.
- Revision checking.
- Verified writes.
- Backup rotation.
- Startup backup fallback.

The active configuration file is:

`/clonker/device_config.json`

Successful browser saves publish the new validated configuration into RAM after persistence.

The dispatcher reads the current configuration for each request, avoiding a stale startup snapshot.

### Persistence boundaries

The active configuration engine maintains:

```text
device_config.json
device_config.json.bak
device_config.json.bak.old
```

Temporary writes use:

```text
device_config.json.tmp
```

The multi-file replacement sequence is not power-loss-atomic.

Unexpected power interruption can still cause data loss or leave files requiring recovery.

Loading a backup does not silently overwrite a damaged primary.

See [Configuration & Recovery](CONFIGURATION.md) for full details.

## 9. Clock Service

The central clock service is:

`firmware/clonker/clock.py`

It supports two current behaviors:

- Default monotonic uptime reference.
- Browser-provided UTC reference stored in RAM.

### DEFAULTTIME

Before browser synchronization, the clock reports monotonic uptime using a format similar to:

```text
[DEFAULTTIME +001234.5s]
```

This requires no external time service.

### BROWSER

The browser can submit a UTC Unix timestamp through:

```text
POST /api/clock?utc=...
```

The clock stores:

- Reference UTC seconds.
- Reference monotonic time.
- Source name.

Later timestamps are calculated from elapsed monotonic time.

Example:

```text
2026-10-19T20:00:00Z
```

The browser synchronization is stored only in RAM.

It does not modify JSON configuration or write flash.

A restart returns the clock to its default state until synchronized again.

### NTP

The clock module recognizes `NTP` as a possible source name.

Automatic NTP synchronization is **not implemented**.

NTP remains a future enhancement.

### Clock limitations

The browser reference is approximate.

There is no current guarantee of clock accuracy over long periods, during network disruptions, or across restarts.

The clock is primarily a diagnostic timestamp service.

## 10. Serial Logging

The logging module is:

`firmware/clonker/logger.py`

It supports four severity levels:

| Level | Numeric value |
|---|---:|
| DEBUG | 10 |
| INFO | 20 |
| WARNING | 30 |
| ERROR | 40 |

The default logging level is INFO.

The logger writes timestamped messages to serial output.

It does not write log files to flash.

It does not require network connectivity.

It does not create background tasks.

### Example

```text
2026-10-19T20:00:00Z INFO    STUB: Den / volume-up (logged; no command sent)
```

The exact timestamp depends on clock synchronization.

### HTTP diagnostics

`web.py` contains:

```python
HTTP_DIAGNOSTICS = False
```

Setting this to `True` enables additional HTTP trace logging.

This is a development diagnostic feature.

It should normally remain disabled unless troubleshooting a specific issue.

Detailed tracing can add overhead and increase serial output.

## 11. Outbound Device HTTP — Agreed V1 Design

**Design agreed:** October 17–18, 2026  
**Status:** Approved architecture; transport not implemented.

The inbound management HTTP server and outbound device HTTP client have separate responsibilities.

The inbound server receives browser requests.

The outbound transport will send configured commands to Denon, Roku, LG, or other supported HTTP devices.

### Intended request flow

```text
Browser Test Remote or physical control
                  |
                  v
          Generic room/action
                  |
                  v
          actions.dispatch()
                  |
                  v
        Current JSON v2 mapping
                  |
                  v
         Resolve target endpoint
                  |
                  v
         Resolve command path
                  |
                  v
         Outbound HTTP transport
                  |
                  v
          Configured AV device
```

The outbound transport should not contain room-selection policy or equipment-specific toggle state.

### Networking requirements

The initial implementation should:

- Use the existing Wi-Fi connection.
- Reuse shared networking resources where practical.
- Support configured HTTP GET and POST methods.
- Support IPv4 endpoints with optional ports.
- Default to port 80 when omitted.
- Use bounded connection and response timeouts.
- Release network resources after success or failure.
- Return useful success/failure information.
- Permit subsequent actions after a failed request.
- Avoid automatic retries that could duplicate commands.

Persistent TCP connection caching is not required for V1.

Connection pooling, batching, and complex queues should be deferred until testing shows a need.

### Ordinary action behavior

For an ordinary action:

1. Resolve current room and action.
2. Resolve configured target endpoint.
3. Read method and path.
4. If endpoint or path is blank, perform a no-op.
5. Otherwise send one HTTP request.
6. Report the result.

A blank action must not open a network connection.

### Toggle behavior

The JSON v2 configuration already stores:

- `on_path`
- `off_path`

for:

- `power-toggle`
- `mute-toggle`

The planned dispatcher will maintain independent RAM command history for each room and toggle action.

Initial history is unknown.

The first request selects ON.

After a successful ON request, the next selects OFF.

After a successful OFF request, the next selects ON.

A failed request, blank endpoint, or blank selected path does not advance history.

The history records the last successfully sent command direction, **not actual equipment state**.

The outbound transport receives a selected path and sends one request.

It does not own toggle history.

No device-state polling is required for V1.

## 12. Initial Device Command Examples

### Denon AVR

Example configured commands:

```text
GET /goform/formiPhoneAppDirect.xml?MVUP
GET /goform/formiPhoneAppDirect.xml?MVDOWN
GET /goform/formiPhoneAppDirect.xml?MUON
GET /goform/formiPhoneAppDirect.xml?MUOFF
```

Development endpoints:

```text
Den:     192.168.50.44:8080
Sunroom: 192.168.50.40:8080
```

### Roku

Example configured commands:

```text
POST /keypress/Home
POST /keypress/Back
POST /keypress/Play
POST /keypress/Up
POST /keypress/Down
POST /keypress/Left
POST /keypress/Right
```

Development endpoints:

```text
Den:     192.168.50.43:8060
Sunroom: 192.168.50.28:8060
```

These are known development command patterns, not evidence of successful Pico outbound execution.

Roku POST requests may initially follow the form-style convention previously exercised with iOS Shortcuts.

Actual request framing and device response handling must be verified on the Pico.

The final system-power strategy remains unverified.

## 13. Next Development and Test Sequence

The browser Test Remote provides the preferred initial test harness for outbound HTTP work.

Recommended sequence:

1. Review the current `actions.py` logging dispatcher.
2. Review the current networking capabilities available in CircuitPython 10.3.1.
3. Agree on a minimal outbound transport interface.
4. Implement one bounded HTTP GET request to a low-risk Denon command.
5. Trigger the action from the browser Test Remote in CONFIG mode.
6. Confirm serial logs, transport result, and actual equipment response.
7. Implement and test Roku POST requests.
8. Test blank endpoints and paths as no-ops.
9. Test invalid endpoints, connection failures, and timeouts.
10. Expand ordinary action execution.
11. Implement per-room toggle command history.
12. Verify that failed toggle requests do not advance history.
13. Test RUN mode without the management HTTP listener.
14. Integrate physical buttons and encoders.
15. Measure responsiveness before considering optimization.

### CONFIG-mode testing first

The earlier plan suggested disabling CONFIG before initial command tests to remove management HTTP overhead.

That recommendation was written before the browser Test Remote existed.

The preferred initial test is now:

**Browser Test Remote → shared dispatcher → outbound transport → AV device.**

RUN-only testing remains important, but comes later when physical controls or another direct action trigger are available.

### Performance priorities

The initial goal is reliable functionality, not maximum command throughput.

Avoid introducing:

- Volume acceleration.
- Event accumulation.
- Persistent TCP caching.
- General macro engines.
- Automatic command retries.
- Speculative device-state synchronization.

Actual hardware measurements should determine whether these features are needed.

## 14. Security and Reliability Boundaries

Clonker currently assumes a trusted home LAN.

The management server has no application authentication.

Configured HTTP endpoints are intended for local AV equipment.

Do not expose the management server to the public internet.

Do not treat HTTP success as proof that a device changed state.

Do not treat a successful stub dispatch as proof that a command was transmitted.

Do not treat backup rotation as a fully atomic storage transaction.

Do not assume cooperative polling guarantees physical encoder responsiveness until hardware tests have been performed.

These distinctions should remain explicit in future implementation and documentation.

## 15. Reference Documents

- [Architecture](ARCHITECTURE.md) — system boundaries and action execution design.
- [Configuration & Recovery](CONFIGURATION.md) — JSON v2 schema, revisions, persistence, and recovery.
- [Operating Modes](OPERATING_MODES.md) — SERVICE/DEVICE and CONFIG/RUN.
- [Hardware & Controls](HARDWARE_CONTROLS.md) — physical input plans.
- [Development & Deployment](DEVELOPMENT.md) — repository, Pico, and iPad workflow.
- [Development History](DEVELOPMENT_HISTORY.md) - development milestones.
- [Chapter 2 Handoff](CHAPTER_2_HANDOFF.md) — current milestone and next development phase.

---

**CLONK! ⚡🔩**
