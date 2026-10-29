# The Clonker 10000 — Firmware, HTTP & Clock

**Design reference:** Updated October 29, 2026  
**Platform:** Raspberry Pi Pico 2 W / CircuitPython 10.3.1  
**Current baseline:** Chapter 5 — Clonker Config v4, working HTTP action pipeline and Dumb Queue™, GP17/GP18 physical mode switches, and GP2 debounced input events  
**Scope:** Operational firmware behavior, networking, timing, diagnostics, verified behavior, and limitations.

> One monster. Two directions of HTTP. One deliberately Dumb Queue™ between intentions and equipment.

---

## 1. Purpose and current status

This is the **current firmware reference**, not a chronological development diary. Historical experiments belong in [Development History](DEVELOPMENT_HISTORY.md); design boundaries in [Architecture](ARCHITECTURE.md); schema and recovery details in [Configuration](CONFIGURATION.md); switch procedures in [Operating Modes](OPERATING_MODES.md); and component wiring in [Hardware & Physical Controls](HARDWARE_CONTROLS.md).

**Implemented and exercised:** Wi-Fi; Clonker Config v4 JSON loading, editing, and persistence; browser Test Remote; CONFIG-mode management HTTP; fourteen fundamental action IDs; room-specific custom actions; shared Dumb Queue™; real Denon/Roku GET/POST commands; cooperative compound action waits; and volatile per-room power/mute toggle direction histories.

**Chapter 5 hardware verified October 28–29:** GP17 SERVICE (USB)/DEVICE boot switch; GP18 guarded CONFIG/RUN switch with live HTTP-listener transitions; optional physical GPIO initialization and polling; GP2 debounced button press/release events; and browser/network smoke tests with GPIO polling active.

**Not yet integrated:** physical room selection and button-to-action dispatch, rotary encoders, OLED feedback, audible CLONK, custom device slots, equipment-state polling, and Apple TV protocol support. A logged GP2 press is **not** yet a network command. Stress, power-loss, and long-uptime tests are not exhaustive.

The management interface is intended for a **trusted LAN**, not public internet exposure.

## 2. Firmware ownership and layout

| Repository path | Current responsibility |
|---|---|
| `firmware/boot.py` | GP17 boot-time filesystem ownership selection |
| `firmware/code.py` | CircuitPython application entry point |
| `firmware/clonker/main.py` | Startup and cooperative scheduler |
| `firmware/clonker/device_config_v2.py` | Config v4 validation, RAM state, revision, persistence, recovery |
| `firmware/clonker/device_config.json` | Repository configuration example / deployable configuration |
| `firmware/clonker/actions.py` | Fundamental/custom dispatch, queue, compound steps, failure policy |
| `firmware/clonker/net/web.py` | Inbound CONFIG-mode HTTP management service |
| `firmware/clonker/net/http_transport.py` | Outbound bounded blocking HTTP GET/POST |
| `firmware/clonker/www/index.html` | Configuration editor and clock UI |
| `firmware/clonker/www/remote.html` | Browser Test Remote and custom-action runner |
| `firmware/clonker/controls/pins.py` | GPIO assignments, including GP18 CONFIG and GP2 power-button input |
| `firmware/clonker/controls/switches.py` | Physical GP18 CONFIG/RUN source, simulation fallback, software override |
| `firmware/clonker/controls/physical.py` | Optional GPIO button initialization, polling, and event logging |
| `firmware/clonker/controls/buttons.py` | Reusable button input and debounce handling |
| `firmware/clonker/system/clock.py` | UTC reference and monotonic-based timestamps |
| `firmware/clonker/system/logger.py` | Serial diagnostics |
| `firmware/clonker/legacy/` | Historical XML implementation |

The active Pico configuration path is `/clonker/device_config.json`; the repository's `firmware/` prefix is not part of the runtime path. Do not blindly overwrite a browser-edited Pico configuration when deploying code.

**Naming distinction:** `device_config_v2.py` retains its historical filename, but the active schema is **Clonker Config v4**, with `CONFIG_VERSION = 4`.

Configuration owns validated device mappings. The dispatcher owns action admission and execution. Transport sends requests without knowing rooms or action IDs. Physical controls should eventually feed the same dispatcher as the browser, not duplicate network logic.

## 3. Startup, physical inputs, and cooperative scheduling

`firmware/code.py` invokes `clonker.main.main()`. Startup loads the validated configuration, logs configured rooms and built-in destinations, and initializes optional GPIO controls. Physical-control initialization is deliberately tolerant: an unavailable individual button logs a warning rather than preventing the remaining application from starting.

Current scheduler constants in `main.py`:

```python
PHYSICAL_CONTROLS_ENABLED = True
PHYSICAL_POLL_INTERVAL = 0.01
WEB_POLL_INTERVAL = 0.001
ACTION_POLL_INTERVAL = 0.01
```

The loop also yields with `time.sleep(0.001)`.

Each iteration gives priority to physical button polling, then one eligible action-queue operation, then CONFIG-mode management HTTP. The CONFIG/RUN state is checked continuously between action polling and web servicing. These are **cooperative service boundaries, not separate threads**; interval settings do not guarantee maximum latency.

### 3.1 GP17: filesystem ownership at boot

GP17 is read by `boot.py` at startup, with an internal pull-up:

| GP17 switch | Mode | Filesystem write owner |
|---|---|---|
| OFF / open / HIGH | SERVICE (USB) | USB host |
| ON / grounded / LOW | DEVICE | Pico firmware |

Changing this ownership requires disconnecting power and performing a cold boot. A Ctrl+D soft reload is not a substitute. Both switch positions were physically verified October 29, 2026. See [Operating Modes](OPERATING_MODES.md) for the procedure and diagnostics.

### 3.2 GP18: CONFIG/RUN while operating

The guarded GP18 switch is a physical, active-low application-mode input:

| GP18 switch | Mode | Inbound management HTTP |
|---|---|---|
| OFF / open / HIGH | RUN | Stopped |
| ON / grounded / LOW | CONFIG | Running on port 9090 |

GP18 changes mode **without a reboot**. The shared action queue is polled in both modes; CONFIG is not an equipment power command. `switches.py` also retains a simulated source when no physical pin is assigned and a software override for development. The running code reports the effective mode source (`PHYSICAL`, `SIMULATED`, or `OVERRIDE`) and mode in serial logs when they change.

Physical GP18 listener transitions were tested October 29, 2026. See [Operating Modes](OPERATING_MODES.md) for the four combinations of filesystem and application mode.

### 3.3 GP2: input events, not yet equipment control

`controls/physical.py` initializes configured momentary buttons using the reusable `Button` implementation, polls them cooperatively, and logs press/release events. GP2 power-button events have been physically tested with debounce. The present `physical.poll()` **logs events only**; it does not yet select a room or call `actions.dispatch()`.

Room-selector input, action mapping, navigation buttons, and encoder integration are subsequent Chapter 5 work. Blocking outbound HTTP can temporarily delay GPIO polling, so event capture during network traffic still requires measurement.

## 4. Wi-Fi, addresses, and socket ownership

The development Pico has used a private 2.4 GHz LAN with a reserved address of `192.168.50.12`. Example URLs:

- `http://192.168.50.12:9090/`
- `http://192.168.50.12:9090/remote.html`

These are **installation-specific**, not firmware defaults. Wi-Fi credentials belong in private `settings.toml`, never committed examples.

Inbound and outbound networking use CircuitPython `wifi.radio` and `socketpool`. The inbound service and outbound transport have their own SocketPool objects. The outbound transport reuses its **pool**, but creates and closes a **new TCP socket for each command**. There is no connection cache, shared persistent connection, or concurrent worker.

## 5. Inbound management HTTP

**Module:** `firmware/clonker/net/web.py`  
**Port:** `9090`  
**Availability:** CONFIG only  
**Model:** Nonblocking listener; one active client serviced cooperatively.

The service accepts a connection, accumulates a bounded request, prepares a response, sends bounded chunks, and closes the connection. One active-client slot does not provide concurrency.

| Limit / setting | Current value |
|---|---:|
| `MAX_REQUEST_BYTES` | 10,240 bytes |
| `MAX_HEADER_BYTES` | 2,048 bytes |
| `IO_CHUNK_BYTES` | 512 bytes |
| `IDLE_CLIENT_TIMEOUT_SECONDS` | 0.5 seconds |
| `CLIENT_TIMEOUT_SECONDS` | 4.0 seconds |
| Inbound `HTTP_DIAGNOSTICS` | `False` |
| Config engine `MAX_CONFIG_BYTES` | 8,192 UTF-8 bytes |

The 8,192-byte configuration limit is separate from the 10,240-byte HTTP request limit. Headers, revision metadata, and framing also consume request space.

### 5.1 Silent connections

Some browser connections supplied no request data. With a single active-client slot, these could stall subsequent navigation. The server now abandons completely silent connections after approximately 0.5 seconds while allowing longer inactivity for an active request/response. This improved observed iPad Safari and Windows Chrome behavior. The origin of every silent connection remains unproven.

### 5.2 HTTP scheduler pacing investigation — October 28, 2026

During early Chapter 5 GPIO integration, the CONFIG page sometimes loaded slowly or incompletely, particularly in Windows Chrome. Symptoms included delayed room configuration, unfinished filesystem-status requests, `ERR_EMPTY_RESPONSE`, and timeouts during response transmission. Disabling physical controls did **not** eliminate the problem.

Diagnostics showed that requests were accepted and responses began transmitting, but some responses timed out before completion. One observed timeout occurred after approximately 16 KB of a roughly 40 KB response had been sent.

**Key finding: HTTP polling cadence mattered.** The server advances a small amount of work per `web.poll()`. With 512-byte chunks, a roughly 40 KB response needs at least 80 successful send operations. At a 10 ms polling interval, those operations alone consume approximately 800 ms of ideal scheduler time, before network delays and competing work.

Changing `WEB_POLL_INTERVAL` in `main.py` from `0.01` to `0.001` produced a dramatic improvement in the observed tests. Repeated CONFIG refreshes completed promptly in Chrome and Safari; physical controls were re-enabled; GP2 still generated clean press/release events; and the final test passed with inbound HTTP diagnostics disabled.

**Conclusion:** The old 10 ms cadence significantly contributed to observed transmission delays. Why the problem surfaced at this stage remains unproven; page size, browser request behavior, Wi-Fi timing, and scheduler workload may have contributed. The **1 ms interval is the current tested baseline**, not a claim of optimal efficiency.

No change to the GPIO button implementation, socket lifecycle, or HTTP timeout was required. A future optimization could prioritize servicing an active response without polling equally often when idle, but should be justified by measurements.

## 6. Management API and browser interfaces

| Request | Current behavior |
|---|---|
| `GET /` | Configuration editor and clock interface |
| `GET /remote.html` | Browser Test Remote |
| `GET /api/config` | Validated active configuration, revision, filesystem-writable metadata |
| `POST /api/config` | Validate revision/configuration; save when writable and changed |
| `GET /api/clock` | Clock source and timestamp |
| `POST /api/clock?utc=...` | Set browser-provided UTC reference |
| `POST /api/action?room=...&action=...` | Validate and enqueue fundamental or custom action |

`actions.dispatch(room_id, action_id)` admits work to the shared queue. A `status: queued` response means **admission**, not completed HTTP execution or physical equipment response.

The browser Test Remote supports room selection, fourteen fundamental actions, and room-specific custom-action selection with a deliberate Run control. The configuration editor manages custom actions and ordered steps. Earlier selection-reset behavior was investigated; do not assume a persistent defect without reproducing it.

### 6.1 Configuration saves and queue consistency

Only DEVICE mode allows Pico-side persistent saves. The engine checks schema, expected revision, disk/RAM consistency, and write safeguards. A **changed successful save** clears pending queue work and resets volatile toggle-direction histories; an unchanged save preserves both. The authoritative validation and recovery rules are in [Configuration](CONFIGURATION.md).

SERVICE (USB) + CONFIG allows inspection and Test Remote actions but rejects configuration saves with HTTP 403 because the filesystem is read-only to firmware.

## 7. The Dumb Queue™ — fundamental and custom actions

**Module:** `firmware/clonker/actions.py`  
**Capacity:** `QUEUE_CAPACITY = 128` entries  
**Public functions:** `dispatch(room_id, action_id, delay_seconds=0)`, `poll()`, `clear(reason=...)`, `status()`.

> One queue. One poller. One shared execution path.

### 7.1 Admission and task identity

`dispatch()` validates room, action ID, nonnegative delay, and queue capacity. Fundamental actions use fixed IDs; custom actions use stable IDs from the selected room. The queued task carries compact identity and scheduling state, not copied device IPs or paths:

```python
{
    "room": "room-1",
    "action": "example-action",
    "kind": "custom",       # or "fundamental"
    "step": 0,
    "due": 0,
}
```

Execution resolves the **current validated configuration**. A custom action occupies **one queue entry** for its sequence rather than pre-enqueuing every step.

### 7.2 Eligibility and ordering

Immediate tasks have `due = 0`; delayed tasks have a `time.monotonic()` deadline. The poller selects the first **eligible** entry when scanning the queue, so future-dated work does not block an immediately eligible action behind it. Among eligible entries, queue order determines selection. This is intentionally **not strict FIFO across future-dated work**.

### 7.3 Fundamental execution and toggles

An ordinary fundamental action resolves its configured endpoint, HTTP method, and path, then invokes `http_transport.send()`. Missing endpoints or blank ordinary paths produce logged **NO-OPs**, not network requests.

`mute-toggle` and `power-toggle` select configured `on_path` or `off_path` from independent volatile histories for each room and action. History advances **only after successful HTTP execution**. Missing endpoints, blank selected paths, and failed requests do not advance it. History is command-direction memory, **not authoritative equipment-state detection**.

### 7.4 Custom and compound execution

Custom actions have stable IDs, names, and **1–16 ordered steps**, each with a built-in destination, GET/POST method, path, and `wait_after_ms`. Current limits include **16 custom actions per room**, waits from **0–60,000 ms**, and a required zero wait on the final step. See [Configuration](CONFIGURATION.md) for the authoritative schema.

Each eligible `actions.poll()` executes at most **one outbound command**. If more steps remain, the same task advances its step index and is re-appended with a due time calculated **after the previous HTTP request completes successfully**. Other eligible work can run during that wait. This is cooperative sequencing, not a sleeping macro executor, concurrent HTTP, nested macros, or a second workflow engine. Missing custom destinations are execution errors, not ordinary fundamental no-ops.

### 7.5 Failure and diagnostics

An execution exception clears **all remaining queued tasks**, logs the error, and leaves the dispatcher available for later requests. There are no automatic retries or rollback. A failed custom step cancels its remaining sequence.

`status()` reports queue depth, capacity, historical peak, last result, and last error. `clear()` discards pending work without resetting the historical peak. HTTP 2xx means transport-level success, not confirmed equipment state.

## 8. Outbound bounded blocking HTTP

**Module:** `firmware/clonker/net/http_transport.py`  
**Interface:** `send(endpoint, method, path)`.

The transport accepts dotted IPv4 endpoints with optional `:port` (default 80), GET/POST, and an absolute path. It checks Wi-Fi, creates a TCP socket, sends a complete HTTP/1.1 request with an empty body, reads a bounded **status line**, and closes the socket in `finally`.

2xx is accepted. Non-2xx, invalid requests, connection errors, and timeouts raise exceptions. The transport does **not** parse full response headers or bodies, implement TLS, authentication, redirects, persistent connections, arbitrary POST bodies, or device-specific interpretation.

```python
SOCKET_TIMEOUT = 0.5
TOTAL_TIMEOUT = 1.5
MAX_STATUS_LINE = 128
HTTP_DIAGNOSTICS = True
```

`SOCKET_TIMEOUT` bounds individual blocking operations. `TOTAL_TIMEOUT` is checked between operations, **not a hard asynchronous deadline**; a single socket call may overrun the nominal total. Diagnostics report `connect_ms`, `send_ms`, `response_ms`, and `total_ms` using `time.monotonic()`.

Outbound diagnostics are enabled in this baseline; inbound diagnostics are separately disabled. An outbound request temporarily blocks the entire cooperative scheduler, including inbound HTTP and GPIO polling. Queue buffering cannot recover physical events that were never sampled.

## 9. Why outbound transport is blocking

Earlier nonblocking TCP experiments on this CircuitPython platform did not reliably distinguish connection completion from send readiness. Tests encountered `OSError(119)`, and the expected `getsockopt(SO_ERROR)` inspection path was unavailable in the tested environment.

The project chose **bounded blocking outbound HTTP** with cooperative nonblocking inbound HTTP. This is a tested simplicity tradeoff, not a claim that nonblocking TCP is impossible.

Initial successful ordinary requests often took approximately **86–164 ms**, with connection establishment accounting for much of the time. Unreachable endpoints failed within observed socket-timeout behavior; subsequent requests recovered. Measure encoder responsiveness before adding connection reuse or a more complicated transport.

## 10. Device mappings and verified equipment behavior

The default sample currently configures **two rooms: Den and Sunroom**. Config v4 documents one to three configured rooms with built-in destinations `device-1`, `device-2`, and `device-3` (usually labeled TV, AVR, Streaming). Each room has fourteen fundamental actions and optional custom actions. Additional device slots are not implemented; future room expansion should not be presumed operational merely from a schema limit.

**Development-specific endpoints and evidence:**

| Equipment | Endpoint | Observation |
|---|---|---|
| Den AVR-X3700H | `192.168.50.44:8080` | HTTP control accepted commands; HTTP 200 in standby did not prove physical wake |
| Den Roku Ultra | `192.168.50.43:8060` | Configured Roku endpoint; distinct from original Sunroom navigation tests |
| Sunroom AVR-X1800H | `192.168.50.40:8080` | Volume GET commands produced observed receiver volume changes |
| Sunroom Roku | `192.168.50.28:8060` | Roku ECP POST navigation produced observed navigation |

A Denon status-query path returned HTTP 403 in an earlier test while a separate control path returned HTTP 200. This is endpoint-specific evidence, not a universal Denon API rule.

### 10.1 Verified compound action

```text
1. Roku:  POST /keypress/Home                         -> HTTP 200
2. Wait:  3000 ms after step 1 completed
3. Denon: GET /goform/formiPhoneAppDirect.xml?MSQUICK1 -> HTTP 200
4. Dispatcher: CUSTOM COMPLETE
```

This verifies an ordered cross-device sequence using the shared queue. It does not establish physical-input capture during the wait or every possible failure scenario.

## 11. Clock and logging

**Modules:** `clonker/system/clock.py` and `clonker/system/logger.py`.

Before browser synchronization, the clock uses `DEFAULTTIME` and monotonic uptime rather than claiming an authoritative date. The browser can submit UTC Unix time through `/api/clock`; subsequent timestamps are calculated from the saved reference plus elapsed monotonic time.

The logger emits timestamped serial diagnostics with severity thresholds. It has no persistent flash log or background network logging service. An `NTP` source may exist in the interface, but automated NTP synchronization is **not established** by this tested baseline.

**Separate clock domains:** UTC is for readable diagnostic timestamps; `time.monotonic()` is for queue deadlines and elapsed waits. Browser clock adjustments must not move pending action deadlines.

## 12. Verification evidence and limits

### 12.1 Outbound HTTP and queue tests — October 21, 2026

Chapter 3 bench tests demonstrated Roku GET/POST, Denon volume, bounded unreachable-endpoint failure, and recovery without resetting the socket pool. Two reliability runs recorded **24/24 successful reachable requests**, two expected unreachable failures, and two successful post-failure recoveries.

A five-command burst peaked at queue depth five and drained through five HTTP 200 responses. Reported times: **117.2, 125.0, 85.9, 85.9, and 85.9 ms**. This proves sequential backlog handling, not concurrent execution or high-rate encoder performance.

### 12.2 Config v4 compound actions — October 2026

The Sunroom Roku Home → 3000 ms wait → Denon Quick Select 1 action returned HTTP 200 for both steps and completed.

**October 27 interleaving test:** During the custom action's 3000 ms wait, an independent Sunroom Volume Up command executed successfully (HTTP 200) before the delayed Denon command (HTTP 200). The custom action then completed. This verifies eligible-task bypass during a cooperative wait, not simultaneous HTTP or physical encoder responsiveness.

### 12.3 Runtime toggle tests — October 27, 2026

- **Mute:** Sunroom Denon X1800H accepted explicit `MUON`/`MUOFF` GET requests with HTTP 200. Repeated presses alternated ON/OFF; observed HTTP times were approximately 100–125 ms.
- **Power:** Sunroom Roku accepted `Home` and `PowerOff` POST requests with HTTP 200. Home woke the LG G1 and Denon X1800H through HDMI-CEC; PowerOff shut down the chain. Observed times were approximately 145–188 ms.
- **Configuration reset:** A changed save cleared pending work and reset toggle histories; the next Sunroom mute selected ON.
- **Room independence:** Den mute independently selected ON after Sunroom mute had been exercised.
- **Negative paths:** Repeated unreachable failures, blank selected paths, and missing endpoints did not advance toggle direction.

These tests verify command-direction logic, not automatic equipment-state detection or exhaustive failure handling.

### 12.4 Physical input and mode switches — October 28–29, 2026

- The optional GPIO scheduler was smoke-tested with physical controls both disabled and enabled; CONFIG management and outbound actions remained operational.
- GP2 generated debounced press/release diagnostics during physical button testing. These were **input events only**, not queued equipment commands.
- GP17 physical switch selected SERVICE (USB) versus DEVICE filesystem ownership at cold boot.
- GP18 physical guarded switch selected CONFIG versus RUN, starting and stopping the management listener during runtime without reboot.
- After reducing web polling to 1 ms, repeated Chrome/Safari CONFIG page refreshes completed promptly while GPIO polling remained enabled.

Preserve raw dates, logs, and experiments in [Development History](DEVELOPMENT_HISTORY.md). This is a **functional verification snapshot**, not a complete regression certification.

## 13. Known limitations and operational boundaries

- **Physical input dispatch pending:** GP2 events are logged, not yet mapped to room-specific actions; room selector and encoders are not integrated.
- **Blocking outbound HTTP:** temporarily pauses GPIO and web polling; input responsiveness under load is unmeasured.
- **One active inbound client:** short silent-client timeout mitigates stalls, not concurrency.
- **Queue-wide cancellation:** one execution failure discards pending work; no automatic retries or rollback.
- **Power/mute histories:** volatile per-room/action command-direction state, not actual device-state detection.
- **HTTP acknowledgment:** status 2xx does not prove physical equipment state.
- **Response handling:** outbound transport reads the status line, not the body.
- **Connections:** new plain-HTTP TCP connection per command; no TLS or persistence.
- **LAN management:** no application-level authentication; do not expose port 9090 publicly.
- **Filesystem recovery:** safeguards reduce risk but do not guarantee recovery from every power interruption.
- **Future protocols:** Apple TV pairing, authentication, and sessions are not implemented.
- **Coverage:** sustained traffic, long outages, malformed device responses, long uptime, and high-rate encoder capture need more testing.

## 14. Next firmware investigations

Preserve the known-good Config v4 baseline while extending the physical remote in measured steps:

1. Integrate and verify the room selector and its selected-room context.
2. Route GP2 power-button press events through the existing room-aware `power-toggle` dispatcher and Dumb Queue™; verify actual equipment response.
3. Add navigation, Back, and Home physical actions incrementally through the same dispatcher.
4. Integrate the custom-action selector encoder and verify selection/run behavior.
5. Verify Grayhill volume encoder electrical behavior and measure event capture during blocking HTTP and compound waits.
6. Consider volume-event accumulation, coalescing, acceleration, or transport optimization **only if measurements justify them**.
7. Expand queue-pressure, outage, malformed-response, and long-uptime regression tests as useful.

### 14.1 Apple TV — explicit future objective

Apple TV compatibility remains **planned**, not implemented. Discovery, pairing, authentication, sessions, and protocol-specific control may require an adapter beyond stateless HTTP GET/POST. Preserve generic intentions (Home, Back, navigation, Play/Pause), but do not create an `apple_tv.py` module or speculative schema merely to imply progress.

### 14.2 Volume encoder versus the Dumb Queue™

The Grayhill encoder may produce events faster than the network can complete a new TCP request per volume step. The queue buffers admitted tasks but **cannot capture GPIO transitions missed while the cooperative loop is blocked**. Measure before choosing an event-accumulation or connection strategy.

**The Dumb Queue™ buffers traffic. It does not repeal the laws of TCP.**

## 15. Related documents

- [Architecture](ARCHITECTURE.md) — system boundaries and design rationale.
- [Configuration](CONFIGURATION.md) — Config v4 schema, validation, persistence, recovery.
- [Operating Modes](OPERATING_MODES.md) — GP17/GP18 behavior and transitions.
- [Hardware & Physical Controls](HARDWARE_CONTROLS.md) — GPIO, components, and hardware integration.
- [Development & Deployment](DEVELOPMENT.md) — iPad-first workflow and test procedures.
- [Development History](DEVELOPMENT_HISTORY.md) — dated experiments and evidence.
- [`samples/device_config_roku_denon_sample.json`](../samples/device_config_roku_denon_sample.json) — readable Config v4 example.

---

**THE CLONKER 10000**  
*Less sleek. More CLONK.*  
**CLONK! ⚡🔩**
