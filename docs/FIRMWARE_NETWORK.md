# The Clonker 10000 — Firmware, HTTP & Clock

**Design reference:** October 21, 2026  
**Platform:** Raspberry Pi Pico 2 W / CircuitPython 10.3.1  
**Status:** Chapter 3 Phase B validated — real Denon and Roku commands executed through the browser, Dumb Queue™, and outbound HTTP transport.  
**Scope:** Current firmware behavior and operational boundaries. For the development chronology, see [Development History](DEVELOPMENT_HISTORY.md).

> One monster. Two directions of HTTP. A deliberately Dumb Queue™ between the buttons and the network.

---

## 1. Purpose and implementation status

This document describes **the current running firmware**, not the chronological sequence of experiments. It covers startup, the cooperative scheduler, inbound management HTTP, outbound device HTTP, action execution, clock and logging, test evidence, and limitations.

**Working and tested:** Wi-Fi, JSON v2 configuration, browser management and Test Remote, inbound HTTP on port 9090, queued ordinary actions, outbound GET/POST commands to Denon and Roku, and a controlled five-command backlog.

**Not yet implemented:** physical GPIO action inputs, runtime power/mute toggle selection, custom-action execution, device-state polling, and specialized volume-encoder handling. More exhaustive failure, load, and long-duration testing remains pending.

The firmware is intended for a trusted home LAN, not internet exposure.

## 2. Firmware layout and ownership

| Repository path | Responsibility |
|---|---|
| `firmware/code.py` | CircuitPython entry point |
| `firmware/clonker/main.py` | Startup and cooperative scheduling |
| `firmware/clonker/net/web.py` | Inbound CONFIG-mode HTTP server and API |
| `firmware/clonker/net/http_transport.py` | Outbound blocking HTTP client |
| `firmware/clonker/actions.py` | Action validation, Dumb Queue™, execution and failure policy |
| `firmware/clonker/device_config_v2.py` | JSON v2 validation, active configuration, revisions and persistence |
| `firmware/clonker/system/clock.py` | Browser-synchronized UTC reference and timestamps |
| `firmware/clonker/system/logger.py` | Serial logging |
| `firmware/clonker/controls/switches.py` | Simulated CONFIG/RUN selection pending GPIO |
| `firmware/clonker/www/index.html` | Configuration and clock UI |
| `firmware/clonker/www/remote.html` | Browser Test Remote |

The active configuration lives at `/clonker/device_config.json` on CIRCUITPY. The repository's `firmware/` layout is deployed onto the Pico; repository-relative paths are not necessarily runtime absolute paths.

**Separation of responsibilities:** The browser accepts requests; `actions.py` decides what to execute; JSON supplies the endpoint and command; `http_transport.py` handles only the outbound network transaction. Neither physical inputs nor the transport should hardcode room-specific equipment mappings.

## 3. Startup and cooperative scheduling

`firmware/code.py` invokes `clonker.main.main()`. Startup loads and validates the JSON v2 configuration, logs room and device information, and enters the cooperative loop. Successful browser saves publish the new validated configuration to RAM; action execution resolves the current configuration rather than retaining a stale copy.

Current scheduling constants in `main.py`:

```python
WEB_POLL_INTERVAL = 0.01
ACTION_POLL_INTERVAL = 0.01
```

The loop also calls `time.sleep(0.001)` on each iteration. It polls the action queue in both CONFIG and RUN modes, evaluates CONFIG/RUN, and polls the inbound web server only while CONFIG is enabled. Each `actions.poll()` executes at most one eligible queued action.

This is **cooperative scheduling, not multitasking**. The inbound listener is nonblocking and advances one operation per poll. An outbound HTTP request is deliberately blocking and temporarily prevents the main loop from polling other services. The 10 ms poll intervals are scheduling intentions, **not** guaranteed input latency or a promise of uninterrupted GPIO scanning.

The CONFIG/RUN switch is currently simulated; the physical GPIO control is not implemented. SERVICE/DEVICE filesystem ownership is a separate mode described in [Operating Modes](OPERATING_MODES.md).

## 4. Wi-Fi and socket resources

The development Pico uses a private 2.4 GHz Wi-Fi network, with a reserved address of `192.168.50.12`. The management interface is normally available at:

- `http://192.168.50.12:9090/`
- `http://192.168.50.12:9090/remote.html`

These are **development-specific addresses**, not firmware defaults. Wi-Fi credentials are kept in private settings, not in documentation or source-control examples.

Both inbound and outbound networking use CircuitPython `wifi.radio` and `socketpool`. Each module maintains its own `SocketPool` object. The outbound module reuses its pool but **does not reuse individual TCP connections**. Every device command opens a fresh socket and closes it in `finally`.

The inbound server and outbound transport share the same radio, but not a common client socket or a shared request state machine.

## 5. Inbound HTTP server

**Module:** `firmware/clonker/net/web.py`  
**Port:** `9090`  
**Mode:** CONFIG only  
**Architecture:** Nonblocking, single active client, cooperative `poll()`.

The server accepts, receives, parses, builds a response, sends in chunks, and closes a client over successive polls. It does not use a threaded OS or support many simultaneous active requests. Its listener backlog is not the same as concurrent request processing.

Current limits:

| Constant | Value |
|---|---:|
| `MAX_REQUEST_BYTES` | 10,240 bytes |
| `MAX_HEADER_BYTES` | 2,048 bytes |
| `IO_CHUNK_BYTES` | 512 bytes |
| `IDLE_CLIENT_TIMEOUT_SECONDS` | 0.5 s |
| `CLIENT_TIMEOUT_SECONDS` | 4.0 s |
| Inbound `HTTP_DIAGNOSTICS` | `False` |

The configuration engine separately limits serialized JSON to 8,192 UTF-8 bytes.

### Why there are two inbound timeouts

Browser testing exposed connections that were accepted but sent no request bytes. A single four-second timeout could make the browser feel stalled because the server had only one active-client slot. The server now abandons **silent** connections after about 0.5 seconds while allowing up to four seconds of inactivity for an active receive/send operation.

This mitigated observed navigation delays in Chrome on Windows and Safari on iPad. The precise origin of the silent connections was not conclusively established. The timeout change is not a multi-client server redesign.

## 6. Management API and browser interfaces

| Request | Behavior |
|---|---|
| `GET /` | Configuration and clock page |
| `GET /remote.html` | Browser Test Remote |
| `GET /api/config` | Validated current configuration plus revision and filesystem-writable metadata |
| `POST /api/config` | Validate, revision-check and save configuration where permitted |
| `GET /api/clock` | Current clock source and timestamp |
| `POST /api/clock?utc=...` | Set browser-supplied UTC reference |
| `POST /api/action?room=...&action=...` | Validate and **enqueue** a fundamental action |

The action route calls `actions.dispatch(room_id, action_id)` and returns a JSON acknowledgment, including `status: queued` and queue depth. It **does not wait** for network execution. `ok: true` means the request was accepted into the queue, not that the device received or acted upon it.

Configuration saves are blocked when the Pico filesystem is read-only (SERVICE/USB ownership). In writable DEVICE mode, saves are subject to strict JSON validation, revision checks, disk consistency checks, and verified backup rotation. A changed successful save clears pending queue items; an unchanged save does not need to rewrite the file. See [Configuration](CONFIGURATION.md) for the authoritative persistence details.

The browser Test Remote exposes the fourteen fundamental actions for each configured room. Its custom-action selector is illustrative, not an executable custom-action engine.

## 7. The Dumb Queue™ and action execution

**Module:** `firmware/clonker/actions.py`  
**Capacity:** 128 queued tasks  
**Public API:** `dispatch(room_id, action_id, delay_seconds=0)`, `poll()`, `clear(reason=...)`, `status()`.

> **The Dumb Queue gives us a place to absorb commands arriving faster than the network can process them.**

A queued task stores only the room ID, action ID, and due time. It does not capture an IP address, HTTP method, or command path. At execution, `actions.poll()` resolves the **current** JSON configuration.

Immediate actions are eligible immediately. Delayed actions use `time.monotonic()` and do not block eligible immediate actions queued behind them. Among eligible tasks, insertion order is preserved. This is **not strict FIFO across future-dated tasks**.

One poll executes **at most one** eligible task. A blank endpoint or ordinary command path produces a logged no-op and no outbound connection. For a configured ordinary action, the queue calls `http_transport.send(endpoint, method, path)` and logs its result.

**Current toggle boundary:** `mute-toggle` and `power-toggle` are accepted into the queue but execution is deliberately marked `DEFERRED`. No ON/OFF HTTP command is transmitted until state-direction selection is implemented. The JSON schema already supports `on_path` and `off_path`.

### Queue failure policy

A transport or execution exception is caught by `actions.poll()`. The executing item has already been removed; the queue **discards all remaining pending items**, logs the failure, and remains available for later submissions. There are **no automatic retries**. The transport itself does not clear the queue.

`status()` reports current depth, capacity, historical peak depth, last result, and last error. Peak depth is historical within the running process; `clear()` does not reset it.

**Important distinction:** A failed device command can cancel pending work. It does not permanently disable Clonker.

## 8. Outbound blocking HTTP transport

**Module:** `firmware/clonker/net/http_transport.py`  
**Interface:** `send(endpoint, method, path)`.

The transport validates a dotted IPv4 endpoint with optional `:port` (default 80), accepts GET and POST, requires an absolute command path, checks Wi-Fi connectivity, and constructs an HTTP/1.1 request with `Host`, `Connection: close`, and `Content-Length: 0`.

It then:

1. Opens a new TCP socket from its shared SocketPool.
2. Sets a bounded socket timeout and connects.
3. Sends the complete request, handling partial sends.
4. Reads and parses the HTTP **status line**, bounded to 128 bytes.
5. Accepts 2xx status codes; raises on non-2xx or transport errors.
6. Returns endpoint, method, path, status and timing fields.
7. Closes the socket in `finally`, including on failure.

The current implementation **does not read the complete response headers or body**. It is intentionally minimal and suitable only for commands whose success can be judged sufficiently from the HTTP status. It does not implement TLS, redirects, authentication, arbitrary POST bodies, connection persistence, or device-specific response parsing. Apple TV control is not implemented by this transport.

Current transport constants:

```python
SOCKET_TIMEOUT = 0.5
TOTAL_TIMEOUT = 1.5
MAX_STATUS_LINE = 128
HTTP_DIAGNOSTICS = True
```

`SOCKET_TIMEOUT` bounds an individual blocking socket operation. `TOTAL_TIMEOUT` is a **cooperative deadline checked between operations**, not an asynchronous hard wall-clock limit. A single operation may extend beyond the nominal total deadline; the total also depends on the CircuitPython stack's actual timeout behavior. Neither setting proves uninterrupted GPIO responsiveness.

Timing results include `connect_ms`, `send_ms`, `response_ms`, and `total_ms`, measured with `time.monotonic()`. Observed readings can be quantized; a displayed `0.0 ms` phase is not proof of literally zero elapsed time.

Inbound and outbound `HTTP_DIAGNOSTICS` are separate module settings. Outbound diagnostics are currently **enabled** for integration testing.

## 9. CircuitPython TCP findings and design rationale

Initial nonblocking outbound socket experiments were attractive because console calls appeared responsive. However, connection completion and subsequent sends were not reliably distinguishable using the APIs available in this tested CircuitPython environment. Observed errors included `OSError(119)` and later connection errors; an expected `getsockopt(SO_ERROR)` inspection path was unavailable.

The team therefore chose **bounded blocking outbound HTTP for ordinary buttons**, while retaining nonblocking inbound HTTP where cooperative service is essential. This is a deliberate simplicity/performance tradeoff, not a claim that nonblocking TCP cannot be made to work.

The tested blocking implementation repeatedly succeeded on reachable Roku and Denon endpoints. A deliberately unreachable LAN address failed predictably and a subsequent Roku request succeeded. Under a 0.5-second socket timeout, one unreachable-address test failed after approximately 539 ms; other measured failures depended on the configured timeout and socket behavior.

Successful ordinary commands generally completed in approximately **86–164 ms** in the initial bench tests. Most measured time was often spent establishing a fresh TCP connection. These measurements motivate, but do not yet justify implementing, persistent connections for high-rate volume control.

## 10. Device mappings and command examples

The JSON v2 configuration supports three fixed room IDs, each with editable names and optional `tv`, `avr`, and `streaming` endpoints. Each room contains fourteen fixed fundamental action mappings. A non-toggle mapping identifies target, HTTP method and path. Toggle mappings have paired ON/OFF paths.

**Verified development endpoints (October 21, 2026):**

| Equipment | Endpoint | Tested example |
|---|---|---|
| Den AVR-X3700H | `192.168.50.44:8080` | `GET /goform/formiPhoneAppDirect.xml?MVUP` returned HTTP 200 while receiver was in standby; no wake was observed |
| Sunroom AVR-X1800H | `192.168.50.40:8080` | `GET /goform/formiPhoneAppDirect.xml?MVUP` and `?MVDOWN` changed the volume |
| Sunroom Roku | `192.168.50.28:8060` | `POST /keypress/Right`, `/keypress/Home`, `/keypress/Back` |

The Den Roku has also been configured at `192.168.50.43:8060`, but that is **not** the Roku endpoint used for the documented Sunroom tests.

A Denon status query to `/goform/formMainZone_MainZoneXml.xml` returned HTTP 403 during testing. That did not prevent a different Denon control endpoint from returning HTTP 200. Do not generalize the 403 to the whole receiver API.

The Den AVR-X3700H accepted a volume-up HTTP request while in standby without visibly waking the receiver or LG TV. An HTTP 200 acknowledges an HTTP-level result, **not necessarily a physical state change**.

These addresses and behaviors are local test observations, not universal manufacturer defaults.

## 11. Clock synchronization and logging

**Clock module:** `clonker/system/clock.py`  
**Logger module:** `clonker/system/logger.py`.

The clock initially uses `DEFAULTTIME`, showing monotonic uptime rather than pretending to know the date. The browser can submit a UTC Unix timestamp through `/api/clock`; the clock stores the reference UTC and monotonic time, then derives later timestamps from elapsed monotonic time. `NTP` is an accepted clock source in the module interface but automated NTP synchronization is not established by this milestone.

The logger prints timestamped serial messages with DEBUG, INFO, WARNING and ERROR severity thresholds. It does not persist logs to flash or run background network tasks.

**Clock domains must remain distinct:** browser UTC is for readable timestamps and diagnostics; `time.monotonic()` is for queue delays and elapsed-time measurements. Adjusting the wall-clock reference must not shift scheduled queue deadlines.

## 12. Verification record — Chapter 3 Phase B

**Date:** October 21, 2026. **Scope:** Controlled bench and browser tests, not production qualification.

- Roku read-only GET returned HTTP 200.
- Sunroom Denon GET Volume Up and Volume Down returned HTTP 200, with visible LG volume-bar changes.
- Sunroom Roku POST navigation commands returned HTTP 200 and produced observed navigation.
- Den AVR-X3700H returned HTTP 200 for a volume command while in standby, without observed wake behavior.
- A deliberately unreachable endpoint generated a bounded error; later requests recovered without resetting the socket pool.
- Reliability runs at 1.0-second and 0.5-second socket timeouts reported **24/24 successful reachable requests**, **two expected unreachable failures**, and **two successful post-failure recoveries**.
- Browser Test Remote commands successfully traversed `/api/action` → Dumb Queue → outbound transport → equipment.
- A controlled REPL burst enqueued **five** Sunroom Volume Up commands before polling. Peak depth reached **5**. Five polls executed five HTTP 200 responses, with reported times of **117.2, 125.0, 85.9, 85.9 and 85.9 ms**. Queue depth returned to **0**, with no recorded error.

The burst demonstrated bounded backlog acceptance and sequential drain. It did **not** demonstrate five simultaneous HTTP transactions, high-rate browser request handling, or uninterrupted GPIO event capture.

The earlier logging-only Phase A tests remain documented in [Development History](DEVELOPMENT_HISTORY.md). Do not confuse historical stub responses with the current live execution path.

## 13. Known limitations and safety boundaries

- **Blocking outbound requests:** pause the cooperative scheduler; physical encoder responsiveness is untested.
- **Single active inbound client:** idle-browser mitigation is useful but not equivalent to concurrent HTTP handling.
- **Failure policy:** one failed execution clears the remaining queue; that is intentional but may be revisited for special controls.
- **Toggle actions:** queue acceptance is implemented; ON/OFF execution is deferred.
- **Response interpretation:** HTTP 2xx does not guarantee the device physically changed state; response bodies are not parsed.
- **No retries:** avoids duplicate button effects but leaves transient failures to the user or later policy.
- **No persistent TCP:** each command incurs connection establishment overhead.
- **No authentication:** the management service is designed for a trusted LAN; do not forward port 9090 to the internet.
- **Persistence safeguards:** backup rotation is not a fully atomic power-loss transaction.
- **Incomplete coverage:** sustained load, extended Wi-Fi outages, malformed-device responses, memory stability, physical RUN-mode operation, and comprehensive failure injection remain to be tested.

## 14. Future networking and volume-encoder work

The **Grayhill optical volume encoder** inspired the project and may require a different policy from ordinary slow button presses. The v1 transport is intentionally simple: one blocking request, one TCP connection, one HTTP status acknowledgment.

Possible future investigations, **not implemented or committed design requirements**, include:

- Measure actual encoder event rates and physical input capture during network operations.
- Consider accumulation, coalescing, acceleration, or bounded backpressure for rapid volume changes.
- Test whether the Denon API supports persistent HTTP connections and whether connection reuse meaningfully improves throughput.
- Consider configurable per-device or per-action connection behavior only if evidence supports it.
- Avoid assuming Roku, Apple TV, LG, and Denon have identical networking capabilities.
- Keep custom-action sequences on the shared queue rather than inventing a second execution engine.
- Implement per-room power/mute command-direction history separately from transport logic.

A future optimized volume path must preserve the ability to operate ordinary buttons and must not pretend that the current queue automatically captures events while blocking.

**The Dumb Queue™ buffers the traffic. It does not repeal the laws of TCP.**

## 15. Related documents

- [Architecture](ARCHITECTURE.md) — system boundaries and design rationale.
- [Configuration](CONFIGURATION.md) — JSON v2 schema, revision control, backups, and recovery.
- [Operating Modes](OPERATING_MODES.md) — SERVICE/DEVICE and CONFIG/RUN behavior.
- [Hardware & Physical Controls](HARDWARE_CONTROLS.md) — knobs, switches, and future GPIO integration.
- [Development & Deployment](DEVELOPMENT.md) — editing and deployment workflow.
- [Development History](DEVELOPMENT_HISTORY.md) — dated experiments, failures, and verified milestones.

---

**THE CLONKER 10000**  
*Less sleek. More CLONK.*  
**CLONK! ⚡🔩**
N