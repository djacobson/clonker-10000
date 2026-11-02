# The Clonker 10000 — Firmware, HTTP & Clock

**Design reference:** Updated November 2, 2026  
**Platform:** Raspberry Pi Pico 2 W / CircuitPython 10.3.1  
**Current baseline:** Chapter 6 — Clonker Config v4, operational Dumb Queue™, physical room selector, and room-aware Power Toggle  
**Scope:** Operational firmware behavior, networking, timing, diagnostics, verified behavior, and limitations.

> One monster. Two directions of HTTP. One deliberately Dumb Queue™ between intentions and equipment.

---

## 1. Purpose and current status

This is the **current firmware reference**, not a chronological development diary.

Historical experiments belong in [Development History](DEVELOPMENT_HISTORY.md); design boundaries in [Architecture](ARCHITECTURE.md); schema and recovery details in [Configuration](CONFIGURATION.md); switch procedures in [Operating Modes](OPERATING_MODES.md); and component wiring in [Hardware & Physical Controls](HARDWARE_CONTROLS.md).

### Implemented and exercised

- Wi-Fi networking.
- Clonker Config v4 JSON loading, editing, and persistence.
- Browser configuration editor and Test Remote.
- CONFIG-mode management HTTP.
- Fourteen fundamental action IDs.
- Room-specific custom actions.
- Shared Dumb Queue™.
- Real Denon/Roku GET/POST execution.
- Cooperative compound-action waits.
- Volatile per-room power/mute toggle histories.
- GP17 SERVICE (USB)/DEVICE boot switch.
- GP18 guarded CONFIG/RUN switch.
- GP2 debounced momentary Power Toggle.
- Three-position physical room selector on GP3/GP4/GP5.
- Debounced room-selection state.
- Shared physical-event-to-action mapping.
- Room-aware physical action dispatch.
- Safe no-op for an unconfigured selected room.

### Chapter 6 milestone — November 2, 2026

The physical room selector and GP2 Power Toggle now operate together through the running Clonker application.

**Verified against actual equipment:**

| Physical selection | Action | Result |
|---|---|---|
| Room 1 — Den | Power ON | PASS |
| Room 1 — Den | Power OFF | PASS |
| Room 2 — Sunroom | Power ON | PASS |
| Room 2 — Sunroom | Power OFF | PASS |
| Room 3 — Reserved | Power Toggle | PASS — no-op |

Independent per-room toggle histories were observed.

This is the first verified physical hardware-to-equipment command path.

### Not yet integrated

- Rotary encoder drivers and application behavior.
- Physical navigation, Back, Home, and playback buttons.
- OLED feedback.
- Audible CLONK.
- Battery operation and deep-sleep ignition.
- Additional custom destination slots.
- Equipment-state polling.
- Apple TV protocol support.

Stress, power-loss, and long-uptime tests are not exhaustive.

The management interface is intended for a **trusted LAN**, not public internet exposure.

---

## 2. Firmware ownership and layout

| Repository path | Current responsibility |
|---|---|
| `firmware/boot.py` | GP17 boot-time filesystem ownership |
| `firmware/code.py` | CircuitPython application entry point |
| `firmware/clonker/main.py` | Startup, mode transitions, cooperative scheduler |
| `firmware/clonker/device_config_v2.py` | Config v4 validation, RAM state, revision, persistence, recovery |
| `firmware/clonker/device_config.json` | Repository configuration example / deployable configuration |
| `firmware/clonker/actions.py` | Fundamental/custom dispatch, queue, compound steps, failure policy |
| `firmware/clonker/net/web.py` | Inbound CONFIG-mode HTTP management |
| `firmware/clonker/net/http_transport.py` | Outbound bounded blocking HTTP |
| `firmware/clonker/www/index.html` | Configuration editor and clock UI |
| `firmware/clonker/www/remote.html` | Browser Test Remote and custom-action runner |
| `firmware/clonker/controls/pins.py` | Central GPIO assignments |
| `firmware/clonker/controls/buttons.py` | Reusable momentary button class |
| `firmware/clonker/controls/switches.py` | GP18 CONFIG/RUN state and override |
| `firmware/clonker/controls/selectors.py` | Physical room selection and debounce |
| `firmware/clonker/controls/physical.py` | GPIO initialization, polling, event mapping, physical dispatch |
| `firmware/clonker/system/clock.py` | UTC reference and monotonic-based timestamps |
| `firmware/clonker/system/logger.py` | Serial diagnostics |
| `firmware/clonker/legacy/` | Historical XML implementation |

**Planned:** `controls/encoders.py`, providing reusable quadrature encoder handling.

The active Pico configuration path is:

`/clonker/device_config.json`

The repository's `firmware/` prefix is not part of the runtime path.

Do not blindly overwrite a browser-edited Pico configuration when deploying code.

**Naming distinction:** `device_config_v2.py` retains its historical filename, but the active schema is **Clonker Config v4**, with `CONFIG_VERSION = 4`.

### 2.1 Module ownership

Configuration owns validated device mappings.

`selectors.py` owns the selected physical room.

`buttons.py` owns momentary electrical events.

`physical.py` owns hardware-to-action mapping.

`actions.py` owns action admission, scheduling, and execution.

Transport sends requests without knowing rooms or action IDs.

The browser and physical controls share the same action dispatcher.

**No duplicate command pipeline. No second queue.**

---

## 3. Startup, physical inputs, and cooperative scheduling

`firmware/code.py` invokes `clonker.main.main()`.

Startup loads validated configuration, logs configured rooms and built-in destinations, and initializes optional GPIO controls.

Physical-control initialization is deliberately tolerant.

An unavailable individual button logs a warning rather than preventing the application from starting.

### 3.1 Current scheduler constants

```python
PHYSICAL_CONTROLS_ENABLED = True
PHYSICAL_POLL_INTERVAL = 0.01
WEB_POLL_INTERVAL = 0.001
ACTION_POLL_INTERVAL = 0.01
```

The main loop also yields with:

```python
time.sleep(0.001)
```

| Service | Target interval |
|---|---:|
| Physical controls | 10 ms |
| Action queue | 10 ms |
| CONFIG management HTTP | 1 ms |
| Main-loop yield | 1 ms |

These are **cooperative service boundaries, not separate threads**.

The intervals do not guarantee maximum latency.

### 3.2 Scheduler order

The current cooperative loop services:

1. Physical-control polling.
2. One eligible action-queue operation.
3. CONFIG/RUN mode evaluation and listener management.
4. CONFIG-mode management HTTP.
5. A brief runtime yield.

Physical controls are polled before action execution.

This allows a newly detected physical event to enter the queue before the action poller runs.

The action queue continues operating in both CONFIG and RUN modes.

### 3.3 GP17: filesystem ownership at boot

GP17 is read by `boot.py` at startup using an internal pull-up.

| GP17 switch | Mode | Filesystem writer |
|---|---|---|
| OFF / open / HIGH | SERVICE (USB) | USB host |
| ON / grounded / LOW | DEVICE | Pico firmware |

Changing filesystem ownership requires a cold boot.

Ctrl+D is not a substitute.

Both positions were physically verified October 29, 2026.

See [Operating Modes](OPERATING_MODES.md).

### 3.4 GP18: CONFIG/RUN while operating

The guarded GP18 switch is an active-low application-mode input.

| GP18 switch | Mode | Inbound management HTTP |
|---|---|---|
| OFF / open / HIGH | RUN | Stopped |
| ON / grounded / LOW | CONFIG | Running on port 9090 |

GP18 changes mode **without rebooting**.

The shared queue remains active in both modes.

`switches.py` retains simulated mode selection when no physical pin is assigned and a software override for development.

Serial diagnostics identify the effective source and mode.

CONFIG is not an equipment power command.

### 3.5 Physical controls — operational event routing

`controls/physical.py` initializes assigned buttons and the room selector.

Its poller performs:

1. Poll the room selector.
2. Log accepted room changes.
3. Poll initialized buttons.
4. Log stable press/release events.
5. Map recognized press events to generic action IDs.
6. Dispatch through the selected room.

The reusable `Button` class reports stable `"pressed"` and `"released"` events.

Only press events trigger mapped actions.

The GP2 Power Toggle now uses the same dispatcher as the browser Test Remote.

### 3.6 Room selector state

`controls/selectors.py` owns the physical room-selection state.

| Position | GPIO grounded | Room |
|---|---|---|
| LEFT | GP3 | `room-1` |
| MIDDLE | GP4 | `room-2` |
| RIGHT | GP5 | `room-3` |

Each input uses an internal pull-up.

A valid position requires exactly one grounded input.

Zero or multiple grounded inputs are ignored as invalid or transitional.

The selector requires **50 ms of stable input** before accepting a changed room.

It maintains the last valid selection.

The selector does not know whether a room is configured and does not send network commands.

### 3.7 Shared physical dispatch

`physical.py` provides:

```python
dispatch_selected(action_id)
```

The helper:

1. Reads `selectors.selected_room()`.
2. Checks whether the room exists in the active configuration.
3. Logs a no-op when unavailable.
4. Calls `actions.dispatch(room_id, action_id)` when configured.
5. Logs dispatch exceptions without terminating the poller.

Representative physical mapping:

```python
BUTTON_ACTIONS = {
    "POWER_TOGGLE": "power-toggle",
    "HOME": "home",
    "BACK": "back",
    "UP": "nav-up",
    "DOWN": "nav-down",
    "LEFT": "nav-left",
    "RIGHT": "nav-right",
    "SELECT": "select",
    "VOLUME_MUTE": "mute-toggle",
}
```

Only controls with assigned GPIO pins are initialized.

The currently verified action button is GP2.

Other mappings are prepared for future hardware.

### 3.8 Reserved Room 3

The physical selector supports three positions.

The active configuration currently contains two rooms.

Selecting Room 3 is valid selector state but not a valid configured action destination.

`dispatch_selected()` rejects the action before queue admission.

Representative diagnostic:

```text
PHYSICAL NO-OP: room-3 / power-toggle (room unavailable)
```

No HTTP command is sent.

No fallback room is selected.

This avoids accidentally controlling another room.

### 3.9 Debounce and timing

Current input timing:

| Input | Debounce |
|---|---:|
| Momentary buttons | 30 ms default |
| Room selector | 50 ms |
| Physical scheduler | 10 ms target |

Debounce is nonblocking.

The room selector and buttons currently share the same physical polling schedule.

This design is sufficient for the tested controls.

Rotary encoders may require a different strategy.

### 3.10 Blocking HTTP and encoder implications

Outbound HTTP is synchronous.

While an outbound request blocks, the cooperative loop cannot poll physical inputs.

This is not a significant demonstrated problem for the tested maintained selector or momentary Power Toggle.

It may become important for quadrature encoders, which generate multiple transitions during rotation.

Possible future approaches include:

- Faster encoder polling.
- Separate fast and slow physical polling schedules.
- Hardware-assisted quadrature decoding.
- Lightweight event accumulation.
- Volume-command coalescing.

None of these has been selected or implemented as the final solution.

**Bench-test the actual Bourns encoders before redesigning the scheduler.**

---

## 4. Wi-Fi, addresses, and socket ownership

The development Pico has used a private 2.4 GHz LAN with a reserved address of `192.168.50.12`.

Example URLs:

- `http://192.168.50.12:9090/`
- `http://192.168.50.12:9090/remote.html`

These are **installation-specific**, not firmware defaults.

Wi-Fi credentials belong in private `settings.toml`, never committed examples.

Inbound and outbound networking use CircuitPython `wifi.radio` and `socketpool`.

The inbound service and outbound transport have their own SocketPool objects.

The outbound transport reuses its pool but creates and closes a **new TCP socket for each command**.

There is no connection cache, shared persistent connection, or concurrent worker.

---

## 5. Inbound management HTTP

**Module:** `firmware/clonker/net/web.py`  
**Port:** `9090`  
**Availability:** CONFIG only  
**Model:** Nonblocking listener; one active client serviced cooperatively.

The service accepts a connection, accumulates a bounded request, prepares a response, sends bounded chunks, and closes the connection.

One active-client slot does not provide concurrency.

| Limit / setting | Current value |
|---|---:|
| `MAX_REQUEST_BYTES` | 10,240 bytes |
| `MAX_HEADER_BYTES` | 2,048 bytes |
| `IO_CHUNK_BYTES` | 512 bytes |
| `IDLE_CLIENT_TIMEOUT_SECONDS` | 0.5 seconds |
| `CLIENT_TIMEOUT_SECONDS` | 4.0 seconds |
| Inbound `HTTP_DIAGNOSTICS` | `False` |
| Config engine `MAX_CONFIG_BYTES` | 8,192 UTF-8 bytes |

The configuration limit is separate from the HTTP request limit.

Headers, revision metadata, and framing also consume request space.

### 5.1 Silent connections

Some browser connections supplied no request data.

With a single active-client slot, these could stall subsequent navigation.

The server now abandons completely silent connections after approximately 0.5 seconds while allowing longer inactivity for active request/response work.

This improved observed iPad Safari and Windows Chrome behavior.

The origin of every silent connection remains unproven.

### 5.2 HTTP scheduler pacing investigation — October 28, 2026

During early Chapter 5 GPIO integration, the CONFIG page sometimes loaded slowly or incompletely, particularly in Windows Chrome.

Symptoms included:

- Delayed room configuration.
- Unfinished filesystem-status requests.
- `ERR_EMPTY_RESPONSE`.
- Timeouts during response transmission.

Disabling physical controls did **not** eliminate the problem.

Diagnostics showed requests were accepted and responses began transmitting, but some timed out before completion.

One observed timeout occurred after approximately 16 KB of a roughly 40 KB response had been sent.

**Key finding: HTTP polling cadence mattered.**

The server advances a bounded amount of work per `web.poll()`.

With 512-byte chunks, a roughly 40 KB response requires at least 80 successful send operations.

At a 10 ms polling interval, those operations alone consume approximately 800 ms of ideal scheduler time, before network delays and competing work.

Changing:

```python
WEB_POLL_INTERVAL = 0.01
```

to:

```python
WEB_POLL_INTERVAL = 0.001
```

produced a dramatic improvement.

Repeated CONFIG refreshes completed promptly in Chrome and Safari.

Physical controls were re-enabled.

GP2 continued generating clean press/release events.

The final test passed with inbound HTTP diagnostics disabled.

**Conclusion:** The old 10 ms cadence significantly contributed to observed transmission delays.

Why the problem surfaced at that stage remains unproven.

Page size, browser request behavior, Wi-Fi timing, and scheduler workload may have contributed.

The **1 ms interval is the current tested baseline**, not a claim of optimal efficiency.

No change to the GPIO button implementation, socket lifecycle, or HTTP timeout was required.

Future optimization should be justified by measurements.

---

## 6. Management API and browser interfaces

| Request | Current behavior |
|---|---|
| `GET /` | Configuration editor and clock interface |
| `GET /remote.html` | Browser Test Remote |
| `GET /api/config` | Validated configuration, revision, filesystem metadata |
| `POST /api/config` | Revision-protected configuration save |
| `GET /api/clock` | Clock source and timestamp |
| `POST /api/clock?utc=...` | Set browser-provided UTC reference |
| `POST /api/action?room=...&action=...` | Validate and enqueue fundamental or custom action |

`actions.dispatch(room_id, action_id)` admits work to the shared queue.

A `status: queued` response means **admission**, not completed HTTP execution or physical equipment response.

The browser Test Remote supports:

- Room selection.
- Fourteen fundamental actions.
- Room-specific custom-action selection.
- A deliberate Run control.

The browser's selected room is independent of the physical room selector.

Both interfaces submit to the same action dispatcher.

### 6.1 Configuration saves and queue consistency

Only DEVICE mode allows Pico-side persistent saves.

The engine checks schema, expected revision, disk/RAM consistency, and write safeguards.

A **changed successful save** clears pending queue work and resets volatile toggle histories.

An unchanged save preserves both.

SERVICE (USB) + CONFIG permits inspection and Test Remote actions but rejects configuration saves with HTTP 403 because the filesystem is read-only to firmware.

See [Configuration](CONFIGURATION.md) for authoritative recovery rules.

---

## 7. The Dumb Queue™ — fundamental and custom actions

**Module:** `firmware/clonker/actions.py`  
**Capacity:** `QUEUE_CAPACITY = 128` entries  
**Public functions:** `dispatch(room_id, action_id, delay_seconds=0)`, `poll()`, `clear(reason=...)`, `status()`.

> One queue. One poller. One shared execution path.

### 7.1 Admission and task identity

`dispatch()` validates:

- Room.
- Action ID.
- Nonnegative delay.
- Queue capacity.

Fundamental actions use fixed IDs.

Custom actions use stable IDs from the selected room.

Queued tasks carry compact identity and scheduling state rather than copied device endpoints.

Representative task:

```python
{
    "room": "room-1",
    "action": "example-action",
    "kind": "custom",
    "step": 0,
    "due": 0,
}
```

Execution resolves the current validated configuration.

A custom action occupies **one queue entry** for its sequence.

### 7.2 Eligibility and ordering

Immediate tasks have `due = 0`.

Delayed tasks use a `time.monotonic()` deadline.

The poller selects the first **eligible** entry.

Future-dated work does not block an immediately eligible action behind it.

Among eligible entries, queue order determines selection.

This is intentionally **not strict FIFO across future-dated work**.

### 7.3 Fundamental execution and toggles

Ordinary fundamental actions resolve their configured endpoint, HTTP method, and path.

Missing endpoints or blank ordinary paths produce logged **NO-OPs**, not network requests.

`mute-toggle` and `power-toggle` select configured `on_path` or `off_path` from independent volatile histories for each room and action.

History advances **only after successful HTTP execution**.

Missing endpoints, blank selected paths, and failed requests do not advance it.

History is command-direction memory, **not authoritative equipment-state detection**.

### 7.4 Custom and compound execution

Custom actions have stable IDs, names, and **1–16 ordered steps**.

Each step has:

- A built-in destination.
- GET/POST method.
- Command path.
- `wait_after_ms`.

Current limits include:

- 16 custom actions per room.
- Waits from 0–60,000 ms.
- Required zero wait on the final step.

Each eligible `actions.poll()` executes at most **one outbound command**.

If more steps remain, the task advances its step index and is re-appended with a due time calculated after the previous HTTP request completes successfully.

Other eligible work can run during the wait.

This is cooperative sequencing, not concurrent HTTP or a second workflow engine.

Missing custom destinations are execution errors, not ordinary fundamental no-ops.

### 7.5 Failure and diagnostics

An execution exception clears **all remaining queued tasks**, logs the error, and leaves the dispatcher available for later requests.

There are no automatic retries or rollback.

A failed custom step cancels its remaining sequence.

`status()` reports queue depth, capacity, historical peak, last result, and last error.

`clear()` discards pending work without resetting the historical peak.

HTTP 2xx means transport-level success, not confirmed equipment state.

---

## 8. Outbound bounded blocking HTTP

**Module:** `firmware/clonker/net/http_transport.py`  
**Interface:** `send(endpoint, method, path)`.

The transport accepts dotted IPv4 endpoints with optional `:port`, defaulting to port 80.

It supports GET/POST and an absolute path.

It checks Wi-Fi, creates a TCP socket, sends an HTTP/1.1 request with an empty body, reads a bounded status line, and closes the socket in `finally`.

HTTP 2xx is accepted.

Non-2xx responses, invalid requests, connection errors, and timeouts raise exceptions.

The transport does **not** implement:

- Full response-header or body parsing.
- TLS.
- Authentication.
- Redirects.
- Persistent connections.
- Arbitrary POST bodies.
- Device-specific interpretation.

Current constants:

```python
SOCKET_TIMEOUT = 0.5
TOTAL_TIMEOUT = 1.5
MAX_STATUS_LINE = 128
HTTP_DIAGNOSTICS = True
```

`SOCKET_TIMEOUT` bounds individual blocking operations.

`TOTAL_TIMEOUT` is checked between operations, **not enforced as a hard asynchronous deadline**.

A single socket operation may overrun the nominal total.

Diagnostics report:

- `connect_ms`.
- `send_ms`.
- `response_ms`.
- `total_ms`.

All use `time.monotonic()`.

Outbound diagnostics are enabled in this baseline.

Inbound diagnostics are separately disabled.

**An outbound request temporarily blocks the entire cooperative scheduler, including GPIO and management HTTP polling.**

Queue buffering cannot recover physical transitions that were never sampled.

---

## 9. Why outbound transport is blocking

Earlier nonblocking TCP experiments on this CircuitPython platform did not reliably distinguish connection completion from send readiness.

Tests encountered `OSError(119)`.

The expected `getsockopt(SO_ERROR)` inspection path was unavailable in the tested environment.

The project therefore chose **bounded blocking outbound HTTP** with cooperative nonblocking inbound HTTP.

This is a tested simplicity tradeoff, not a claim that nonblocking TCP is impossible.

Initial successful ordinary requests often took approximately **86–164 ms**, with connection establishment accounting for much of the time.

Unreachable endpoints failed within observed timeout behavior.

Subsequent requests recovered.

Measure encoder responsiveness before adding connection reuse or more complicated transport.

---

## 10. Device mappings and verified equipment behavior

The current sample configures **two rooms: Den and Sunroom**.

Config v4 supports one to three configured rooms.

Each room has built-in destinations:

- `device-1`.
- `device-2`.
- `device-3`.

These are usually labeled TV, AVR, and Streaming.

Each room has fourteen fundamental actions and optional custom actions.

Additional custom destination slots are not implemented.

### 10.1 Development-specific endpoints

| Equipment | Endpoint | Observation |
|---|---|---|
| Den AVR-X3700H | `192.168.50.44:8080` | HTTP commands accepted; standby wake not proven by HTTP 200 |
| Den Roku Ultra | `192.168.50.43:8060` | Configured Roku endpoint |
| Sunroom AVR-X1800H | `192.168.50.40:8080` | Volume GET produced observed receiver changes |
| Sunroom Roku | `192.168.50.28:8060` | ECP POST navigation produced observed navigation |

These addresses are installation-specific.

A Denon status-query path returned HTTP 403 in an earlier test while a separate control path returned HTTP 200.

That is endpoint-specific evidence, not a universal Denon API rule.

### 10.2 Verified compound action

```text
1. Roku:  POST /keypress/Home
   Result: HTTP 200

2. Wait:  3000 ms after step 1 completed

3. Denon: GET /goform/formiPhoneAppDirect.xml?MSQUICK1
   Result: HTTP 200

4. Dispatcher: CUSTOM COMPLETE
```

This verifies an ordered cross-device sequence using the shared queue.

It does not establish physical-input capture during the wait or every possible failure scenario.

### 10.3 Verified physical Power Toggle

The GP2 button dispatches the generic `power-toggle` action for the selected room.

The same action logic handles browser and physical requests.

November 2 testing verified:

- Den ON.
- Den OFF.
- Sunroom ON.
- Sunroom OFF.
- Reserved Room 3 no-op.

Actual equipment responded in both configured rooms.

Independent room-specific toggle histories were observed.

This confirms the physical-event-to-equipment pipeline, not automatic equipment-state discovery.

---

## 11. Clock and logging

**Modules:** `clonker/system/clock.py` and `clonker/system/logger.py`.

Before browser synchronization, the clock uses `DEFAULTTIME` and monotonic uptime rather than claiming an authoritative date.

The browser can submit UTC Unix time through `/api/clock`.

Subsequent timestamps are calculated from the saved reference plus elapsed monotonic time.

The logger emits timestamped serial diagnostics with severity thresholds.

It has no persistent flash log or background network logging service.

An `NTP` source may exist in the interface, but automated NTP synchronization is **not established** by this tested baseline.

### Separate clock domains

UTC is used for readable diagnostic timestamps.

`time.monotonic()` is used for queue deadlines and elapsed waits.

Browser clock adjustments must not move pending action deadlines.

---

## 12. Verification evidence and limits

### 12.1 Outbound HTTP and queue tests — October 21, 2026

Chapter 3 bench tests demonstrated:

- Roku GET/POST.
- Denon volume.
- Bounded unreachable-endpoint failure.
- Recovery without resetting the socket pool.

Two reliability runs recorded:

- **24/24 successful reachable requests**.
- Two expected unreachable failures.
- Two successful post-failure recoveries.

A five-command burst peaked at queue depth five and drained through five HTTP 200 responses.

Reported times:

**117.2, 125.0, 85.9, 85.9, and 85.9 ms.**

This proves sequential backlog handling, not concurrent execution or high-rate encoder performance.

### 12.2 Config v4 compound actions — October 2026

The Sunroom Roku Home → 3000 ms wait → Denon Quick Select 1 action returned HTTP 200 for both steps and completed.

**October 27 interleaving test:**

During the custom action's 3000 ms wait, an independent Sunroom Volume Up command executed successfully before the delayed Denon command.

Both returned HTTP 200.

The custom action then completed.

This verifies eligible-task bypass during a cooperative wait, not simultaneous HTTP or physical encoder responsiveness.

### 12.3 Runtime toggle tests — October 27, 2026

**Mute:** Sunroom Denon X1800H accepted explicit `MUON`/`MUOFF` GET requests with HTTP 200.

Repeated presses alternated ON/OFF.

Observed HTTP times were approximately 100–125 ms.

**Power:** Sunroom Roku accepted Home and PowerOff POST requests with HTTP 200.

Home woke the LG G1 and Denon X1800H through HDMI-CEC.

PowerOff shut down the chain.

Observed times were approximately 145–188 ms.

**Configuration reset:** A changed save cleared pending work and reset toggle histories.

**Room independence:** Den mute independently selected ON after Sunroom mute had been exercised.

**Negative paths:** Repeated unreachable failures, blank selected paths, and missing endpoints did not advance toggle direction.

These tests verify command-direction logic, not automatic equipment-state detection.

### 12.4 Physical input and mode switches — October 28–29, 2026

- Optional GPIO scheduler smoke-tested with controls disabled and enabled.
- CONFIG management and outbound actions remained operational.
- GP2 generated debounced press/release events.
- GP17 selected SERVICE (USB) versus DEVICE at cold boot.
- GP18 selected CONFIG versus RUN without reboot.
- Reducing web polling to 1 ms improved repeated Chrome/Safari CONFIG refreshes.
- GPIO polling remained enabled during successful browser tests.

At this stage, GP2 events were logged but not yet dispatched.

That limitation was subsequently resolved in Chapter 6.

### 12.5 Standalone room-selector test — October 31, 2026

A three-position selector was connected to GP3, GP4, and GP5.

Each input used an internal pull-up.

The selector common was grounded.

The standalone test:

```python
exec(open("/tests/test_room_selector.py").read())
```

reported:

```text
SELECTED: LEFT
SELECTED: MIDDLE
SELECTED: RIGHT
```

Reverse transitions also succeeded.

**Result: PASS — selector electrical mapping and GPIO inputs verified.**

### 12.6 Integrated room selection — November 2, 2026

`selectors.py` was integrated into the physical-control subsystem.

The application successfully:

- Initialized the selector.
- Detected Room 1.
- Detected Room 2.
- Detected Room 3.
- Logged accepted room transitions.
- Preserved valid selection state.
- Rejected unavailable room actions.

Representative diagnostics:

```text
Room selector initialized; selected = room-1
ROOM SELECTED: room-2
ROOM SELECTED: room-3
ROOM SELECTED: room-1
```

**Result: PASS — physical room-selection state operational.**

### 12.7 Physical Power Toggle — November 2, 2026

The GP2 Power Toggle was connected to the existing action dispatcher through `physical.dispatch_selected()`.

The tests exercised actual hardware, queue execution, network commands, and real equipment.

| Test | Result |
|---|---|
| Room 3 Power Toggle | PASS — safe no-op |
| Room 2 Power ON | PASS |
| Room 2 Power OFF | PASS |
| Room 1 Power ON | PASS |
| Room 1 Power OFF | PASS |
| Independent room histories | PASS |

PuTTY logs showed button events, queue admission, execution, and toggle-direction behavior.

The equipment visibly responded.

**Result: PASS — first fully operational physical hardware-to-equipment command path.**

Preserve raw dated experiments in [Development History](DEVELOPMENT_HISTORY.md).

This is a functional verification snapshot, not complete regression certification.

---

## 13. Known limitations and operational boundaries

- **Rotary encoders:** Not yet integrated into the running application.
- **Blocking outbound HTTP:** Temporarily pauses GPIO and web polling.
- **Fast input capture:** Encoder responsiveness under network load remains unmeasured.
- **Physical controls:** Navigation, playback, and custom-action selection are pending.
- **Room 3:** Physical selection works, but the room is not configured.
- **One active inbound client:** Silent-client timeout mitigates stalls, not concurrency.
- **Queue-wide cancellation:** One execution failure discards pending work.
- **Retries:** No automatic retries or rollback.
- **Power/mute histories:** Volatile command-direction state, not actual equipment-state detection.
- **HTTP acknowledgment:** Status 2xx does not prove equipment state.
- **Response handling:** Outbound transport reads the status line, not the body.
- **Connections:** New plain-HTTP TCP connection per command.
- **TLS/authentication:** Not supported by the current outbound transport.
- **LAN management:** No application-level authentication; do not expose port 9090 publicly.
- **Filesystem recovery:** Safeguards reduce risk but cannot guarantee recovery from every interruption.
- **Future protocols:** Apple TV pairing, authentication, and sessions are not implemented.
- **Coverage:** Sustained traffic, outages, malformed responses, long uptime, and high-rate encoder capture require further testing.

The physical Power Toggle and room selector are no longer listed as pending features.

They are implemented and verified.

---

## 14. Next firmware investigations

Preserve the known-good Config v4 baseline while extending the physical remote in measured steps.

### 14.1 Bourns encoder integration

The current design uses two **Bourns PEC11R-4215F-S0024** rotary encoders.

The earlier Grayhill volume-encoder plan has been superseded.

The next work should:

1. Review the current Bourns wiring and prior standalone tests.
2. Implement a reusable `controls/encoders.py` class.
3. Test one encoder independently.
4. Establish reliable rotation direction and movement events.
5. Reuse the `Button` class for encoder pushbuttons.
6. Integrate volume up/down and mute.
7. Measure responsiveness during real HTTP execution.
8. Integrate custom-action selection and Run behavior.

The hardware decoder should not know which application action it controls.

`physical.py` should interpret generic encoder events.

### 14.2 Volume encoder versus the Dumb Queue™

A Bourns encoder may produce events faster than the network can complete a new TCP request per volume step.

The queue buffers admitted tasks.

It **cannot capture GPIO transitions missed while the cooperative loop is blocked**.

Potential future strategies include:

- Hardware-assisted quadrature decoding.
- Faster dedicated encoder polling.
- Event accumulation.
- Volume-command coalescing.
- Network transport optimization.

These should be evaluated only after measurements.

**The Dumb Queue™ buffers traffic. It does not repeal the laws of TCP.**

### 14.3 Additional physical controls

After encoder integration, add:

- Navigation cluster.
- Back.
- Home.
- Playback controls.
- OLED status feedback.
- Optional audio feedback.

Reuse the established physical-event-to-action architecture.

Avoid introducing separate network command paths.

### 14.4 Apple TV — explicit future objective

Apple TV compatibility remains **planned**, not implemented.

Discovery, pairing, authentication, sessions, and protocol-specific control may require an adapter beyond stateless HTTP GET/POST.

Preserve generic intentions such as Home, Back, navigation, and Play/Pause.

Do not create an `apple_tv.py` module or speculative schema merely to imply progress.

### 14.5 Reliability and regression

Future testing should include:

- Rapid repeated input.
- Queue pressure.
- Encoder capture during outbound HTTP.
- Unreachable endpoints.
- Malformed responses.
- Configuration changes with pending work.
- Long uptime.
- Power interruption and recovery.

The guiding principle remains:

**One meaningful change at a time, followed by real Pico verification.**

---

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
