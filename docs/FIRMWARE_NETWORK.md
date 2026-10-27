# The Clonker 10000 — Firmware, HTTP & Clock

**Design reference:** Updated October 27, 2026  
**Platform:** Raspberry Pi Pico 2 W / CircuitPython 10.3.1  
**Current baseline:** Chapter 4 — Clonker Config v4, fundamental actions, executable custom actions, and cooperative compound execution  
**Scope:** Operational firmware behavior, networking, timing, diagnostics, tested behavior, and limitations.

> One monster. Two directions of HTTP. One deliberately Dumb Queue™ between intentions and equipment.

---

## 1. Purpose and current status

This document describes the **current firmware implementation**, not a chronological account of its development. Historical experiments and earlier milestones belong in [Development History](DEVELOPMENT_HISTORY.md). Architectural principles belong in [Architecture](ARCHITECTURE.md); exact configuration schema and recovery rules belong in [Configuration](CONFIGURATION.md).

**Implemented and exercised on hardware:** Wi-Fi, Clonker Config v4 JSON loading and persistence, browser configuration, the browser Test Remote, the CONFIG-mode HTTP management service, fourteen fundamental action IDs, user-defined custom actions, the shared Dumb Queue™, outbound HTTP GET/POST, and real Denon/Roku commands. A compound custom action has successfully executed a Roku command, waited cooperatively, and then executed a Denon command.

**Still deferred:** physical GPIO input integration, custom device slots, specialized volume-encoder behavior, equipment-state polling, and Apple TV protocol support. Runtime power/mute toggle direction selection is implemented and bench-tested. Stress, failure-injection, power-loss, and long-uptime coverage are not exhaustive.

The HTTP management service is intended for a **trusted home LAN**, not direct internet exposure.

## 2. Firmware ownership and layout

| Repository path | Current responsibility |
|---|---|
| `firmware/boot.py` | Boot-time SERVICE/DEVICE filesystem ownership |
| `firmware/code.py` | CircuitPython application entry point |
| `firmware/clonker/main.py` | Startup and cooperative scheduler |
| `firmware/clonker/device_config_v2.py` | Clonker Config v4 validation, active RAM configuration, revision, persistence, recovery |
| `firmware/clonker/device_config.json` | Device configuration in the repository |
| `firmware/clonker/actions.py` | Fundamental/custom dispatch, shared queue, compound steps, failure policy |
| `firmware/clonker/net/web.py` | Inbound CONFIG-mode HTTP service and API |
| `firmware/clonker/net/http_transport.py` | Outbound bounded blocking HTTP GET/POST |
| `firmware/clonker/www/index.html` | Browser configuration editor and clock controls |
| `firmware/clonker/www/remote.html` | Browser Test Remote and custom-action runner |
| `firmware/clonker/controls/switches.py` | Application-mode selection, presently simulated |
| `firmware/clonker/controls/pins.py` | GPIO definitions |
| `firmware/clonker/system/clock.py` | UTC reference and monotonic-based timestamps |
| `firmware/clonker/system/logger.py` | Serial diagnostics |
| `firmware/clonker/legacy/` | Historical XML implementation |

On CIRCUITPY the active configuration path is `/clonker/device_config.json`. The repository's `firmware/` prefix is not part of that runtime path.

**Important naming distinction:** `device_config_v2.py` is a historical module filename. The active configuration schema is **Clonker Config v4**, with `CONFIG_VERSION = 4`. The module has not been renamed merely to match the schema version.

Configuration owns validated definitions. The dispatcher owns action admission, ordering, execution, and failure behavior. The outbound transport knows nothing about rooms or action IDs. Neither GPIO handlers nor HTTP transport should hardcode device-specific mappings.

## 3. Startup and cooperative scheduling

`firmware/code.py` starts `clonker.main.main()`. Startup loads the active configuration, logs configured rooms and built-in destinations, and enters the cooperative main loop.

Current scheduling values in `main.py`:

```python
WEB_POLL_INTERVAL = 0.01
ACTION_POLL_INTERVAL = 0.01
```

The loop also yields with `time.sleep(0.001)`.

The queue is polled in **both CONFIG and RUN modes**. The inbound management server is started and polled only in CONFIG mode; it is stopped in RUN mode. CONFIG/RUN is an application state, not an HTTP action. The physical CONFIG/RUN control is not yet wired.

SERVICE/DEVICE is a separate **boot-time filesystem ownership** decision selected using GP17. See [Operating Modes](OPERATING_MODES.md).

Each `actions.poll()` processes at most **one eligible outbound command**. Each inbound `web.poll()` advances at most one accept, receive, or send operation. These are cooperative service boundaries, **not threads**. Poll intervals do not guarantee response latency, especially during blocking outbound network operations.

## 4. Wi-Fi, addresses, and socket ownership

The development Pico has been used on a private 2.4 GHz LAN with a reserved address of `192.168.50.12`. Example development URLs:

- `http://192.168.50.12:9090/`
- `http://192.168.50.12:9090/remote.html`

These addresses are **installation-specific**, not universal firmware defaults. Wi-Fi credentials belong in private settings, not committed examples or documentation.

Inbound and outbound networking both use CircuitPython `wifi.radio` and `socketpool`. The inbound service and outbound transport maintain their own SocketPool objects. The outbound module reuses its **pool**, but opens and closes a **new TCP socket for each command**. There is no shared connection, connection cache, or concurrent request worker.

## 5. Inbound management HTTP

**Module:** `firmware/clonker/net/web.py`  
**Port:** `9090`  
**Availability:** CONFIG mode only  
**Model:** Nonblocking listener; one active client serviced cooperatively.

The service accepts a connection, accumulates a bounded request, prepares a response, sends bounded chunks, and closes the connection. It does not process multiple active clients simultaneously; a listener backlog is not a multi-client execution engine.

| Limit / setting | Current value |
|---|---:|
| `MAX_REQUEST_BYTES` | 10,240 bytes |
| `MAX_HEADER_BYTES` | 2,048 bytes |
| `IO_CHUNK_BYTES` | 512 bytes |
| `IDLE_CLIENT_TIMEOUT_SECONDS` | 0.5 seconds |
| `CLIENT_TIMEOUT_SECONDS` | 4.0 seconds |
| Inbound `HTTP_DIAGNOSTICS` | `False` |
| Config engine `MAX_CONFIG_BYTES` | 8,192 UTF-8 bytes |

The separate 8,192-byte configuration limit is not interchangeable with the HTTP request limit. Request headers, revision metadata, and transport framing also consume space.

### 5.1 Silent connections and browser responsiveness

During browser testing, accepted connections sometimes supplied no request data. With only one active-client slot, a silent connection could delay subsequent navigation. The server now abandons a completely silent connection after approximately 0.5 seconds, while allowing longer inactivity for an active receive/send operation.

This improved observed browser behavior on iPad Safari and Windows Chrome. The precise origin of every silent connection was not conclusively identified. The timeout adjustment does not make the server concurrent.

## 6. Management API and browser interfaces

| Request | Current behavior |
|---|---|
| `GET /` | Serve configuration editor and clock interface |
| `GET /remote.html` | Serve browser Test Remote |
| `GET /api/config` | Return active validated configuration plus revision and filesystem-writable metadata |
| `POST /api/config` | Validate revision and configuration; save when writable and changed |
| `GET /api/clock` | Return clock source and timestamp |
| `POST /api/clock?utc=...` | Set browser-provided UTC reference |
| `POST /api/action?room=...&action=...` | Validate and enqueue a fundamental **or custom** action ID |

The action route calls `actions.dispatch(room_id, action_id)`. Its JSON response acknowledges **queue admission**, not network completion or physical equipment behavior. A response such as `status: queued` means the task was accepted; it does **not** mean that a receiver changed input or a Roku navigated successfully.

The browser Test Remote supports fundamental actions and room-specific custom actions with a selector and deliberate Run control. The configuration editor supports adding/editing/removing custom actions and their ordered steps. The custom-action selection may reset after execution; this is a small deferred UI refinement, not a limitation of execution.

### 6.1 Configuration saves and queue consistency

A save is permitted only when the Pico filesystem is writable by firmware in DEVICE mode. The configuration engine checks schema, expected revision, disk/RAM consistency, and persistence safeguards. A **changed successful save** causes `web.py` to clear pending queue work **and reset all volatile toggle-direction histories** so commands cannot continue under superseded configuration. An unchanged save preserves both the queue and toggle histories.

The full validation, backup rotation, startup recovery, and stale-browser-tab behavior are specified in [Configuration](CONFIGURATION.md). A browser-visible editor does not imply the filesystem is writable.

## 7. The Dumb Queue™ — fundamental and custom actions

**Module:** `firmware/clonker/actions.py`  
**Capacity:** `QUEUE_CAPACITY = 128` queue entries  
**Public functions:** `dispatch(room_id, action_id, delay_seconds=0)`, `poll()`, `clear(reason=...)`, `status()`.

> One queue. One poller. One shared execution path.

### 7.1 Admission and task identity

`dispatch()` checks the room, action ID, nonnegative delay, and available queue capacity. Fundamental actions use the fixed fundamental ID set; custom actions use stable IDs defined in the selected room's configuration. The dispatcher resolves enough configuration to validate admission, then queues a compact task with:

```python
{
    "room": "room-1",
    "action": "example-action",
    "kind": "custom",       # or "fundamental"
    "step": 0,
    "due": 0,
}
```

The task does not copy device IPs, methods, or paths. Execution resolves the **current** validated configuration. A custom action uses **one queue entry** for its sequence, rather than pre-enqueuing a separate task for every step.

### 7.2 Eligibility and ordering

Immediate tasks have `due = 0`; delayed tasks have an absolute `time.monotonic()` deadline. The poller selects the first **eligible** entry when scanning the queue. A future-dated task therefore does not prevent an immediate action behind it from running.

Among eligible entries, queue order determines selection. This is intentionally **not strict FIFO across future-dated work**.

### 7.3 Fundamental execution

For a configured ordinary fundamental action, `poll()` resolves the endpoint, HTTP method, and path, then calls `http_transport.send()`. An ordinary action with a missing endpoint or blank path produces a logged **NO-OP**, not an outbound request.

`mute-toggle` and `power-toggle` execute using the configured `on_path` and `off_path`. The dispatcher selects the direction from independent, volatile histories for each room and toggle action, then sends the selected HTTP command. History advances only after successful HTTP execution. A missing endpoint or blank selected path produces a logged no-op without advancing history.

### 7.4 Custom and compound execution

A custom action has a stable ID, display name, and **1–16 ordered command steps**. Each step supplies a built-in destination, GET/POST method, command path, and `wait_after_ms`. Current limits include **16 custom actions per room**, waits from **0–60,000 ms**, and a required zero wait on the final step. See [Configuration](CONFIGURATION.md) for authoritative schema and validation rules.

At each eligible poll, the dispatcher executes **one step**. If more steps remain, it advances the task's step index and re-appends the **same task** to the queue. The next due time is calculated **after the preceding HTTP command completes successfully**. During that wait, independent eligible tasks can execute.

This is cooperative sequencing, **not** `time.sleep()` inside a macro executor. It does not create parallel HTTP requests, nested custom actions, scripts, or a separate workflow engine. Missing custom destinations are execution errors rather than fundamental-action no-ops.

### 7.5 Failure and diagnostics

An execution exception clears **all remaining queued tasks**, logs the error, and leaves the dispatcher available for later requests. There are no automatic retries or rollback. A failed custom step also cancels its unfinished sequence because that sequence is represented by the same queued task.

`status()` exposes queue depth, capacity, historical peak depth, last result, and last error. `clear()` discards pending work but does not reset the historical peak. HTTP 2xx is a transport-level success, not proof of equipment state.

## 8. Outbound bounded blocking HTTP

**Module:** `firmware/clonker/net/http_transport.py`  
**Interface:** `send(endpoint, method, path)`.

The transport accepts dotted IPv4 addresses with optional `:port` (default 80), HTTP GET or POST, and an absolute command path. It checks Wi-Fi connectivity, creates a new TCP socket, sends a complete HTTP/1.1 request with an empty body, reads the bounded **status line**, and closes the socket in `finally`.

A 2xx status is accepted; non-2xx, invalid requests, connection errors, and timeouts raise exceptions to the dispatcher. The transport does **not** parse full response headers or bodies, implement TLS, authentication, redirects, persistent connections, arbitrary POST bodies, or device-specific response interpretation.

```python
SOCKET_TIMEOUT = 0.5
TOTAL_TIMEOUT = 1.5
MAX_STATUS_LINE = 128
HTTP_DIAGNOSTICS = True
```

`SOCKET_TIMEOUT` bounds individual blocking operations. `TOTAL_TIMEOUT` is a cooperative deadline checked between operations, **not a hard asynchronous wall-clock cutoff**. A single socket call may extend beyond the nominal overall deadline. The module reports `connect_ms`, `send_ms`, `response_ms`, and `total_ms`, measured with `time.monotonic()`.

Outbound diagnostics are enabled in this tested baseline; inbound diagnostics are independently disabled. The outbound request temporarily blocks the main cooperative loop, including inbound servicing and future GPIO polling. The queue buffers work but does not guarantee that physical input events are captured during a blocking request.

## 9. Why the outbound transport is blocking

Earlier nonblocking TCP experiments on this CircuitPython platform did not reliably distinguish connection completion from subsequent send readiness. Tests encountered errors including `OSError(119)`; the anticipated `getsockopt(SO_ERROR)` inspection path was not available in the tested environment.

The project therefore adopted **bounded blocking outbound HTTP**, while retaining cooperative nonblocking inbound management HTTP. This is a deliberate, tested simplicity tradeoff, not a claim that nonblocking TCP is inherently impossible.

Initial successful ordinary requests often took approximately **86–164 ms**, with connection establishment accounting for much of the time. An unreachable endpoint failed within the observed socket-timeout behavior, and later requests recovered. These observations justify measuring encoder responsiveness before introducing connection reuse or a more complicated network engine.

## 10. Device mappings and verified equipment behavior

Config v4 supports one to three configured rooms, each with generic built-in destinations `device-1`, `device-2`, and `device-3`. Their usual UI labels are TV, AVR, and Streaming. Each room has fourteen fundamental actions and optional custom actions. Custom device slots beyond the built-ins are **not implemented**.

**Development-specific endpoints and observations:**

| Equipment | Endpoint | Evidence |
|---|---|---|
| Den AVR-X3700H | `192.168.50.44:8080` | Denon HTTP control endpoint accepted commands; HTTP 200 in standby did not demonstrate physical wake |
| Den Roku Ultra | `192.168.50.43:8060` | Configured Roku endpoint; not the Sunroom endpoint used in the original navigation tests |
| Sunroom AVR-X1800H | `192.168.50.40:8080` | Volume GET requests produced observed receiver volume changes |
| Sunroom Roku | `192.168.50.28:8060` | Roku ECP POST navigation commands produced observed navigation |

A Denon status-query path returned HTTP 403 in an earlier test while a separate control path returned HTTP 200. This is **endpoint-specific evidence**, not a general statement about the Denon API.

### 10.1 Verified Config v4 compound-action sequence

A real Sunroom custom action executed:

```text
1. Roku:  POST /keypress/Home                    -> HTTP 200
2. Wait:  3000 ms after step 1 completed
3. Denon: GET /goform/formiPhoneAppDirect.xml?MSQUICK1 -> HTTP 200
4. Dispatcher: CUSTOM COMPLETE
```

This verifies an actual ordered, cooperative, cross-device sequence using the shared queue. It does not, by itself, prove physical-input capture during the wait or every possible failure scenario. The Den and Sunroom configurations also contain named custom actions for common listening/viewing scenarios.

## 11. Clock and logging

**Modules:** `clonker/system/clock.py` and `clonker/system/logger.py`.

Before browser synchronization, the clock uses `DEFAULTTIME` and monotonic uptime rather than claiming an authoritative date. The browser can submit UTC Unix time through `/api/clock`. The clock retains the reference and computes subsequent timestamps from elapsed monotonic time.

The logger emits timestamped serial diagnostics with severity thresholds. It does not maintain a persistent flash log or background network logging service. An `NTP` source may exist in the clock interface, but automated NTP synchronization is **not established by the tested firmware baseline**.

**Separate clock domains:** UTC is for readable diagnostic timestamps; `time.monotonic()` is for elapsed time, queue deadlines, and compound waits. Browser clock adjustments must not shift pending action deadlines.

## 12. Verification evidence and limits

### 12.1 Earlier outbound HTTP and queue tests — October 21, 2026

The Chapter 3 Phase B bench work demonstrated Roku GET/POST behavior, Denon volume requests, bounded unreachable-endpoint failures, and recovery without resetting the socket pool. Two reliability runs recorded **24/24 successful reachable requests**, two expected unreachable failures, and two successful post-failure recoveries.

A controlled five-command queue burst reached a peak depth of five and drained through five HTTP 200 responses. Reported times were **117.2, 125.0, 85.9, 85.9, and 85.9 ms**. This established sequential backlog handling, not concurrent HTTP execution or high-rate physical encoder performance.

### 12.2 Config v4 custom-action tests — October 2026

Browser configuration, persistence, and actual multi-step execution were exercised using the Pico and Denon/Roku equipment. The Roku Home → 3000 ms wait → Denon Quick Select 1 sequence returned HTTP 200 for both steps and completed. This supersedes earlier statements that custom actions were merely planned or illustrative.

These are **verified functional scenarios**, not exhaustive coverage of malformed responses, extended network outages, simultaneous user inputs, interrupted writes, long uptime, or all power/mute behaviors. Preserve dated raw evidence in [Development History](DEVELOPMENT_HISTORY.md).

### 12.3 Runtime toggle bench tests — October 27, 2026

The browser Test Remote exercised the implemented `mute-toggle` and `power-toggle` actions against real Sunroom equipment.

- **Mute:** Sunroom Denon X1800H accepted explicit `MUON` and `MUOFF` GET requests with HTTP 200 responses. Repeated presses alternated ON/OFF successfully, with observed HTTP transaction times of approximately 100–125 ms.
- **Power:** Sunroom Roku accepted `Home` and `PowerOff` POST requests with HTTP 200 responses. The Roku Home command successfully powered on the LG G1 and Denon X1800H through HDMI-CEC; the PowerOff command shut down the chain. Observed HTTP transactions were approximately 145–188 ms.
- **Configuration reset:** A changed configuration save logged `TOGGLE: All direction histories reset` and cleared the pending queue. The next Sunroom mute request selected ON and completed successfully.
- **Room independence:** After exercising Sunroom mute, the Den room independently selected ON for its first mute request, returning HTTP 200.

These tests confirm working direction selection, successful-command advancement, changed-save reset, and independent room histories.

The tests do **not** establish automatic equipment-state detection, nor do they exhaustively verify failure-path history preservation, blank toggle paths, or high-rate input behavior.

## 13. Known limitations and operational boundaries

- **Blocking outbound requests:** temporarily pause the cooperative scheduler; GPIO responsiveness remains to be measured.
- **One active inbound client:** short silent-client timeout mitigates stalls but does not add concurrency.
- **Queue-wide cancellation:** one execution failure discards pending tasks; no automatic retries or rollback.
- **Power/mute toggles:** volatile per-room/action direction history is implemented and bench-tested. It tracks successful commands, not authoritative equipment state; failed HTTP requests and blank toggle paths remain to be deliberately tested.
- **HTTP result interpretation:** status 2xx does not establish that the physical equipment changed state.
- **No response-body interpretation:** the transport reads the status line only.
- **No connection persistence or TLS:** a new plain-HTTP TCP connection is used per command.
- **LAN-only management boundary:** no authentication; do not expose port 9090 publicly.
- **Filesystem safety:** verified writes and backups reduce risk but do not guarantee atomic recovery from every power interruption.
- **Future protocols:** Apple TV pairing, authentication, sessions, and adapters are not implemented.
- **Testing coverage:** sustained traffic, prolonged outages, malformed-device responses, memory stability, and real encoder event capture need further testing.

## 14. Next firmware investigations

The immediate priority is to **preserve the working Config v4 baseline** while measuring behavior that could justify more complexity.

1. Integrate a small physical input path and verify ordinary action dispatch.
2. Measure encoder event capture during actual outbound HTTP requests and compound waits.
3. Explore volume-event accumulation, acceleration, or coalescing only if measurements show a need.
4. Deliberately test toggle failure handling and blank/unconfigured paths, confirming that direction history does not advance.
5. Refine the Test Remote's custom-action selection persistence when convenient.
6. Evaluate custom device slots and additional protocols as separate, explicit design changes.

### 14.1 Apple TV — explicit future objective

Apple TV compatibility remains an objective, **not an implemented feature**. Discovery, pairing, authentication, session management, and protocol-specific control may be required. The current Roku/Denon HTTP transport should not be assumed sufficient.

Preserve generic action intentions such as Home, Back, navigation, and Play/Pause, while allowing future protocol-specific implementations where actual requirements demand them. Do not introduce an `apple_tv.py` module or speculative configuration schema merely to imply progress.

### 14.2 The volume encoder and the Dumb Queue™

The Grayhill encoder may produce events faster than one fresh TCP connection per volume command can process. The current queue provides bounded buffering and eligibility scheduling, but it **cannot capture events that the cooperative loop never observes**. Test the physical behavior before choosing event coalescing, rate limits, or persistent connections.

**The Dumb Queue™ buffers traffic. It does not repeal the laws of TCP.**

## 15. Related documents

- [Architecture](ARCHITECTURE.md) — system boundaries, ownership, and design rationale.
- [Configuration](CONFIGURATION.md) — authoritative Clonker Config v4 schema, validation, persistence, and recovery.
- [Operating Modes](OPERATING_MODES.md) — SERVICE/DEVICE and CONFIG/RUN behavior.
- [Hardware & Physical Controls](HARDWARE_CONTROLS.md) — physical controls, component selection, and GPIO plans.
- [Development & Deployment](DEVELOPMENT.md) — iPad-first editing, deployment, and test workflow.
- [Development History](DEVELOPMENT_HISTORY.md) — dated engineering milestones and test evidence.
- [`samples/device_config_roku_denon_sample.json`](../samples/device_config_roku_denon_sample.json) — readable operational Config v4 example.

---

**THE CLONKER 10000**  
*Less sleek. More CLONK.*  
**CLONK! ⚡🔩**
