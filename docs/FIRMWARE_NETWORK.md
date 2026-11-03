# The Clonker 10000 — Firmware, Network & Clock

**Design reference:** Updated November 3, 2026  
**Platform:** Raspberry Pi Pico 2 W / CircuitPython 10.3.1  
**Current baseline:** Chapter 6 — Config v4, Dumb Queue™, physical volume encoder, and Denon TCP adapter  
**Scope:** Firmware behavior, networking, scheduler timing, protocol adapters, diagnostics, tests, and operational limitations.

> One monster. One Dumb Queue™. More than one way to deliver a CLONK.

---

## 1. Purpose and verified boundary

This document describes **how the running firmware operates**, not a proposed design or a complete development diary. Architectural boundaries belong in [Architecture](ARCHITECTURE.md), configuration and recovery in [Configuration](CONFIGURATION.md), GPIO and mechanical details in [Hardware & Physical Controls](HARDWARE_CONTROLS.md), and dated experiments in [Development History](DEVELOPMENT_HISTORY.md).

### Implemented and exercised

- Wi-Fi networking; Config v4 JSON validation, browser editor, and Test Remote.
- CONFIG-only inbound management HTTP on port 9090.
- Fourteen fundamental actions and room-specific ordered custom actions.
- Shared Dumb Queue™ for browser and physical actions.
- Generic bounded blocking HTTP GET/POST for Roku and Denon commands.
- Signature-based adapter selection and an in-memory adapter cache.
- Persistent Denon TCP volume commands (`MVUP`/`MVDOWN`) with 50 ms minimum pacing.
- GP17 SERVICE/DEVICE and GP18 CONFIG/RUN switches.
- GP2 physical Power Toggle, three-position room selector, and Bourns volume encoder rotation.
- Safe no-op for unconfigured Room 3; independent per-room toggle histories.
- Cooperative custom-action waits, mixed-transport ordering, and failure cancellation.

**November 3 milestone:** The Bourns volume encoder drives real Sunroom Denon volume changes. Slow, moderate, and aggressive rotation were exercised. Queue tests covered persistent TCP, pacing, HTTP/TCP ordering, delayed custom steps, and failure handling. A successful TCP socket write is still not an equipment-state acknowledgment; physical observation supplies the stronger evidence.

### Pending or not exhaustively tested

Volume encoder push-to-mute, second encoder custom-action selection, navigation/Back/Home/playback buttons, OLED, audible feedback, battery/sleep, and final enclosure are pending. Apple TV pairing/control, custom destination slots, TCP response parsing, long-uptime tests, and exhaustive outage recovery are also pending.

The management service has **no application-level authentication**. Use only on a trusted LAN; never expose port 9090 to the public internet.

---

## 2. Firmware layout and ownership

| Repository path | Responsibility |
|---|---|
| `firmware/boot.py` | GP17 filesystem ownership at boot |
| `firmware/code.py` | CircuitPython application entry |
| `firmware/clonker/main.py` | Initialization, operating modes, cooperative scheduler |
| `firmware/clonker/device_config_v2.py` | Config v4 validation, active RAM config, revisions, persistence |
| `firmware/clonker/actions.py` | Action admission, Dumb Queue™, command execution, cancellation |
| `firmware/clonker/device_adapters.py` | Command-signature recognition and cached adapter lookup |
| `firmware/clonker/devices/denon.py` | Persistent Denon TCP socket and paced volume sends |
| `firmware/clonker/net/http_transport.py` | Generic bounded blocking outbound HTTP |
| `firmware/clonker/net/web.py` | CONFIG-only inbound HTTP and management APIs |
| `firmware/clonker/controls/pins.py` | GPIO assignments |
| `firmware/clonker/controls/buttons.py` | Debounced momentary inputs |
| `firmware/clonker/controls/selectors.py` | Debounced physical room selection |
| `firmware/clonker/controls/encoders.py` | Reusable quadrature encoder driver |
| `firmware/clonker/controls/physical.py` | Physical polling, event mapping, room-aware dispatch |
| `firmware/clonker/controls/switches.py` | CONFIG/RUN state and development overrides |
| `firmware/clonker/system/clock.py` | Clock reference |
| `firmware/clonker/system/logger.py` | Serial diagnostics |
| `firmware/clonker/www/` | Browser editor and Test Remote |
| `firmware/clonker/legacy/` | Historical XML code |

The active Pico configuration path is `/clonker/device_config.json`; the repository `firmware/` prefix is not part of that runtime path. The historical filename `device_config_v2.py` does **not** mean the current schema is v2: `CONFIG_VERSION = 4`.

**Separation of concerns:** GPIO drivers report events; physical coordination selects generic actions; configuration defines commands; `actions.py` owns the queue; adapter selection chooses the delivery mechanism; transports perform network operations. There is no second volume queue or manufacturer-specific command code in the GPIO driver.

---

## 3. Startup, modes, and scheduler

`code.py` starts `clonker.main.main()`. The application loads the active validated configuration, logs configured rooms, initializes optional physical controls, and enters a cooperative loop. Missing optional hardware is logged rather than making the brain-only remote unusable.

### 3.1 Current scheduling constants

```python
PHYSICAL_CONTROLS_ENABLED = True
PHYSICAL_POLL_INTERVAL = 0.001
WEB_POLL_INTERVAL = 0.001
ACTION_POLL_INTERVAL = 0.01
```

The main loop also calls `time.sleep(0.001)` to yield. These are **target service intervals**, not threads, interrupts, or hard latency guarantees.

The loop order is physical inputs, at most one eligible queued command, CONFIG/RUN evaluation and listener transitions, inbound management HTTP, then a short yield. The action queue runs in both CONFIG and RUN modes.

### 3.2 Independent operating-mode switches

| Switch | Open/HIGH | Grounded/LOW | Change requires |
|---|---|---|---|
| GP17 | SERVICE (USB owns filesystem writes) | DEVICE (Pico owns writes) | Full power cycle |
| GP18 | RUN (management listener off) | CONFIG (management listener on) | Live switch change |

Ctrl+D is not equivalent to a full power cycle for filesystem ownership. SERVICE + CONFIG can inspect configuration and run Test Remote actions but cannot persist Pico-side configuration changes. DEVICE + CONFIG permits saves. DEVICE + RUN is the normal remote mode. The GP18 implementation also supports development simulation/override; neither switch is a receiver power command.

### 3.3 Physical event polling

The current assignments are GP2 Power Toggle; GP3/GP6/GP7 room selector; GP8/GP9 Bourns volume quadrature; GP17 and GP18 operating switches. GP4/GP5 remain reserved for STEMMA QT/I²C. The volume encoder pushbutton and other planned buttons are not assigned yet.

`physical.poll()` first updates room selection, then polls initialized buttons, then polls the volume encoder. The room selector requires a single valid grounded input and 50 ms stability. Momentary buttons default to 30 ms debounce. Encoder transitions are decoded by `Encoder`, with completed movement mapped to `volume-up` or `volume-down` and dispatched through the selected room.

`physical.dispatch_selected(action_id)` rejects unavailable rooms before queue admission, so selecting reserved Room 3 never silently controls Den or Sunroom. Browser Test Remote room selection remains independent of the hardware selector.

Outbound synchronous network operations can still delay physical polling. The persistent Denon connection avoids the repeated HTTP connection cost that made early volume experiments sluggish, but it is **not** a hardware interrupt or guarantee against every missed transition.

---

## 4. Wi-Fi, endpoints, and socket ownership

CircuitPython `wifi.radio` and `socketpool` provide network access. Wi-Fi credentials belong in private `settings.toml`, not committed examples.

The development installation has used Pico `192.168.50.12`, with management pages such as `http://192.168.50.12:9090/` and `/remote.html`. These addresses are **installation-specific**, not firmware defaults.

Three networking roles must remain distinct:

1. **Inbound management HTTP:** cooperative single-client listener, CONFIG mode only.
2. **Generic outbound HTTP:** one bounded synchronous request per newly created TCP connection.
3. **Denon TCP adapter:** a persistent outbound connection to one receiver at a time, used only for recognized fundamental volume commands.

The generic HTTP transport reuses its SocketPool object but not individual TCP connections. The Denon adapter maintains its own socket/pool state and closes its previous receiver connection when targeting a different receiver.

---

## 5. Inbound management HTTP

**Module:** `clonker/net/web.py`  
**Port:** `9090`  
**Availability:** CONFIG mode only  
**Model:** Nonblocking cooperative listener, one active client.

The listener accepts a connection, receives a bounded request, prepares a response, sends bounded chunks, and closes the client. A single active-client slot is not concurrent request processing.

| Setting | Current firmware value |
|---|---:|
| `MAX_REQUEST_BYTES` | 10,240 |
| `MAX_HEADER_BYTES` | 2,048 |
| `IO_CHUNK_BYTES` | 512 |
| `IDLE_CLIENT_TIMEOUT_SECONDS` | 0.2 s |
| `CLIENT_TIMEOUT_SECONDS` | 4.0 s |
| `HTTP_DIAGNOSTICS` | `False` |

Config's separate maximum serialized size is 8,192 UTF-8 bytes. HTTP headers and framing also consume request capacity.

### 5.1 Management routes

| Request | Responsibility |
|---|---|
| `GET /` | Configuration editor |
| `GET /remote.html` | Browser Test Remote |
| `GET /api/config` | Active validated configuration, revision, writability metadata |
| `POST /api/config` | Revision-protected validated save |
| `GET /api/clock` | Clock source and timestamp |
| `POST /api/clock?utc=...` | Browser-provided UTC reference |
| `POST /api/action?room=...&action=...` | Validate and enqueue an action |

An API response reporting `queued` means admission, **not** network transmission or device execution. The browser and physical controls converge at `actions.dispatch()`.

### 5.2 Silent clients and browser pacing — October 28

Some browser connections arrived without sending request data and occupied the single client slot. A short idle timeout now abandons completely silent connections. The current source uses **0.2 s**; older documentation recorded 0.5 s during an earlier experiment.

During Chapter 5, CONFIG pages sometimes stalled or returned `ERR_EMPTY_RESPONSE`. Disabling GPIO polling did not resolve it. The inbound server transmits bounded 512-byte chunks, and a 10 ms web poll interval imposed substantial delay on large responses. Changing `WEB_POLL_INTERVAL` from 10 ms to **1 ms** substantially improved repeated Chrome and Safari tests. Physical controls were re-enabled and inbound diagnostics disabled. The precise contribution of browser behavior and Wi-Fi remains unproven.

### 5.3 Saves and active state

The configuration engine validates schema, revision, filesystem writability, and persistence safeguards. The active RAM configuration is authoritative. A successful **changed** save publishes the validated configuration, rebuilds adapter selections, clears pending queue work, and resets volatile toggle histories. An unchanged save preserves pending work and toggle state. A rejected save does not publish a new adapter cache.

See [Configuration](CONFIGURATION.md) for exact file rotation, recovery, and revision behavior. The Pico filesystem does not automatically synchronize with GitHub; protect browser-edited device configuration during firmware deployment.

---

## 6. The Dumb Queue™

**Module:** `clonker/actions.py`  
**Capacity:** 128 entries  
**Main interface:** `dispatch(room_id, action_id, delay_seconds=0)`, `poll()`, `clear()`, `status()`.

> One queue. One poller. One shared execution path.

### 6.1 Admission and identity

Admission validates the room, action, delay, and capacity. Fundamental actions use stable IDs; custom actions use room-specific saved IDs. Tasks retain compact identity, step index, and due time, not copied endpoint definitions. The actual command is resolved from active configuration when executed.

A custom action occupies **one queue entry**, advancing one step at a time. Immediate tasks use `due = 0`; delayed tasks use a `time.monotonic()` deadline.

### 6.2 Eligibility, ordering, and pacing

`poll()` scans for the **first eligible** task. A future-dated custom step does not block an immediate action. Among currently eligible tasks, queue order matters; this is not strict FIFO across delayed work.

A recognized Denon TCP volume command must also satisfy the adapter's minimum 50 ms interval. If the selected eligible command is waiting for pacing, it **stays in its queue position** and `poll()` returns without executing a later command. This prevents overtaking. Pacing uses monotonic time, not `sleep()` inside the queue.

The action scheduler targets a 10 ms poll interval, and each poll executes at most one outbound command. It is not a concurrent worker pool.

### 6.3 Fundamental commands and toggle histories

Ordinary fundamental actions resolve configured destination, method, and path. Missing endpoints or blank paths produce logged no-ops. `power-toggle` and `mute-toggle` select configured ON/OFF paths using independent volatile `(room_id, action_id)` direction histories, defaulting to ON. History advances only after successful transmission; failures and no-ops do not advance it.

This is **last-successful-command direction**, not equipment-state discovery. HDMI-CEC, other remotes, and device applications can change actual state without the Clonker knowing.

### 6.4 Custom actions

Config v4 supports up to 16 custom actions per room; each has 1–16 ordered steps. Steps specify a built-in destination, GET/POST, command path, and `wait_after_ms`. Waits range from 0 to 60,000 ms, with zero required on the final step.

After a successful step, the task is requeued with the next due time calculated **after** the preceding request completes. Other eligible actions can run during a wait. Current custom steps always use **generic HTTP**, even if a step's path resembles a recognized Denon volume command. There is no macro thread, branching engine, or rollback.

### 6.5 Failure policy and status

An execution exception discards all remaining queued tasks, including unfinished custom work, and logs the failure. New actions can subsequently be admitted. There are **no automatic retries**, since the remote cannot safely assume whether an uncertain network command reached the equipment.

`status()` reports current depth, capacity, peak depth, last result, and last error. Queue admission, successful network transmission, and confirmed equipment behavior are distinct evidence levels.

---

## 7. Device adapter selection and cache

**Module:** `clonker/device_adapters.py`.

Adapter selection is based on **exact recognized command signatures**, not equipment brand labels, room names, or fixed device positions. Only fundamental `volume-up` and `volume-down` actions using method `GET` and the recognized Denon paths currently select the specialized adapter:

```text
/goform/formiPhoneAppDirect.xml?MVUP   -> MVUP
/goform/formiPhoneAppDirect.xml?MVDOWN -> MVDOWN
```

All other commands fall back to `generic-http`. Only specialized selections are stored in the in-memory cache, keyed by `(room_id, action_id)`. No adapter identifiers are written into Config v4 JSON.

`device_adapters.rebuild(config)` constructs a replacement map before publishing it. The configuration engine invokes rebuilding on successful load and save activation; rejected saves retain the previous cache. `lookup(room_id, action_id)` returns a specialized selection or generic HTTP fallback. `denon_command(path)` translates the recognized path to the native command and rejects unsupported paths.

The cache is **routing metadata**, not an open socket, equipment-state cache, or separate queue. Socket lifecycle belongs to the selected transport.

---

## 8. Denon persistent TCP adapter

**Module:** `clonker/devices/denon.py`  
**Port:** TCP `23`  
**Supported native commands:** `MVUP`, `MVDOWN`.

Current constants:

```python
TCP_PORT = 23
SOCKET_TIMEOUT = 1.0
MIN_COMMAND_INTERVAL = 0.05
```

### 8.1 Connection lifecycle

The adapter extracts an IPv4 host from the configured endpoint (which may include an HTTP port), then connects to the receiver on TCP port 23. The active socket is reused for subsequent commands to the **same host**. Targeting a different receiver closes the old connection before opening the new one. `close()` also resets socket, host, and pacing state.

The adapter maintains at most **one active receiver connection**. It is not a pool of connections to all rooms. Initial connect and socket write remain synchronous, with a 1-second socket timeout; repeated commands avoid the cost of opening a fresh HTTP connection for each detent.

### 8.2 Pacing and transmission

`ready()` compares monotonic time with the next allowed send time. The queue checks readiness **before** removing the selected command. `send_volume(endpoint, command)` sends the ASCII native command terminated by carriage return (`\r`) and advances the next allowed send time by at least 50 ms after a successful write.

If pacing is not ready, `send_volume()` can return `False`; the caller preserves the task. An exception closes the adapter connection and propagates to the Dumb Queue™ failure policy. No retry is attempted.

**Important:** A successful `sendall()` means bytes were handed to the TCP stack. It does **not** prove that the AVR processed the command or reached a particular volume.

### 8.3 Not implemented

The adapter does not yet parse CR-terminated Denon status responses, consume unsolicited receiver messages, poll receiver state, maintain multiple simultaneous AVR sockets, or perform automatic reconnect/retry after an uncertain command outcome. Connection recovery and long-duration behavior deserve additional bench testing.

---

## 9. Generic outbound HTTP transport

**Module:** `clonker/net/http_transport.py`  
**Interface:** `send(endpoint, method, path)`.

The transport accepts dotted IPv4 with optional `:port` (default 80), GET or POST, and an absolute path. It creates a TCP socket, sends a minimal HTTP/1.1 request with an empty body, reads a bounded status line, accepts HTTP 2xx, and closes the socket in `finally`.

Current constants:

```python
DEFAULT_PORT = 80
SOCKET_TIMEOUT = 0.5
TOTAL_TIMEOUT = 1.5
MAX_STATUS_LINE = 128
HTTP_DIAGNOSTICS = False
```

The socket timeout bounds individual blocking operations. The total deadline is checked between operations and is not an asynchronous hard stop for a single socket call. Non-2xx responses, malformed requests, connection errors, and timeouts raise exceptions for the queue to handle.

The transport does **not** provide full response-body parsing, TLS, authentication, redirects, persistent HTTP connections, arbitrary POST bodies, or device-specific semantics. It is deliberately small.

Timing diagnostics can report connect, send, response, and total durations using `time.monotonic()`. Outbound diagnostics are **disabled in the current source**, as are inbound diagnostics; earlier experiments used verbose output.

### 9.1 Why generic HTTP remains bounded and blocking

Earlier nonblocking TCP experiments on the tested CircuitPython platform encountered `OSError(119)` and lacked a usable `getsockopt(SO_ERROR)` inspection path. Bounded blocking HTTP was selected for predictable behavior and simplicity. This does not prove that nonblocking outbound networking is impossible.

Historical ordinary HTTP requests often took roughly 86–164 ms, with connection establishment a substantial contributor. A new connection per volume detent made rapid physical rotation sluggish. The specialized Denon TCP adapter solves that specific problem without replacing the working generic HTTP path for other actions.

**Any synchronous outbound socket operation temporarily pauses the cooperative loop**, including GPIO and management HTTP polling. A queue can buffer admitted actions; it cannot reconstruct electrical transitions that were never sampled.

---

## 10. Equipment mapping and observed behavior

The current installation has two configured rooms, Den and Sunroom. Config v4 permits one to three rooms and three generic built-in destinations (`device-1`, `device-2`, `device-3`) per room. Browser labels commonly read TV, AVR, and Streaming, but those labels do not enforce protocols.

Historical development endpoints included:

| Equipment | Installation-specific endpoint | Observation |
|---|---|---|
| Den AVR-X3700H | `192.168.50.44:8080` | HTTP control accepted; standby wake not established by HTTP 200 |
| Den Roku Ultra | `192.168.50.43:8060` | Roku ECP commands |
| Sunroom AVR-X1800H | `192.168.50.40:8080` | HTTP and later native TCP volume control |
| Sunroom Roku | `192.168.50.28:8060` | ECP POST navigation |

These are records of the development installation, **not defaults or configuration requirements**. For recognized Denon volume actions, the adapter extracts the IP from the configured HTTP endpoint and uses TCP port 23 instead of the endpoint's HTTP port.

### 10.1 Custom-action equipment test

The Sunroom *Movie* action used Roku `POST /keypress/Home`, a 3,000 ms wait after the first step completed, and Denon `GET /goform/formiPhoneAppDirect.xml?MSQUICK1`. Both HTTP requests returned 200, and the queue logged custom completion. An independent volume command was also observed executing during the custom wait in earlier tests.

### 10.2 Physical Power Toggle — November 2

GP2 Power Toggle successfully controlled Den and Sunroom ON/OFF via the selected room and shared queue. The reserved Room 3 position produced a safe no-op. Independent per-room toggle direction histories were observed. These tests verified actual equipment behavior, not automatic equipment-state detection.

### 10.3 Physical volume — November 3

The Bourns PEC11R-4215F-S0024 encoder on GP8/GP9 generated generic volume actions through `physical.py`. Recognized Sunroom Denon commands used the persistent TCP adapter. Five slow steps up and down returned to the initial receiver volume; moderate and aggressive twisting produced smooth observed changes. The earlier Grayhill volume-encoder plan was superseded; the Grayhill is reserved for another project.

The encoder pushbutton remains unassigned and push-to-mute is not yet integrated. The second Bourns custom-action encoder is also pending.

---

## 11. Clock and diagnostics

**Modules:** `clonker/system/clock.py` and `clonker/system/logger.py`.

Before browser clock synchronization, the firmware uses `DEFAULTTIME` and monotonic uptime rather than asserting an authoritative wall-clock date. The browser can submit UTC Unix time through `/api/clock`. Readable timestamps are calculated from that reference and subsequent monotonic elapsed time.

Queue deadlines, custom waits, and Denon pacing use `time.monotonic()`; browser clock changes must not shift them. Automated NTP synchronization is **not established** by the current verified baseline.

Serial logging records action admission, execution, failures, room changes, and operating-mode transitions. There is no persistent flash log or background logging server. Keep routine logging modest: continuous diagnostics can distort timing and browser responsiveness.

---

## 12. Verification record and evidence limits

### October 21 — outbound HTTP and queue

Chapter 3 tests demonstrated Roku GET/POST, Denon HTTP volume, bounded unreachable-endpoint failures, and post-failure recovery without resetting the socket pool. Two reliability runs recorded **24/24 successful reachable requests**, two expected unreachable failures, and two successful recoveries. A five-command burst drained sequentially with HTTP 200 responses and reported times of **117.2, 125.0, 85.9, 85.9, and 85.9 ms**.

These were HTTP-era measurements, not persistent TCP performance numbers.

### October 27 — custom actions and toggles

The Sunroom Roku Home → 3-second wait → Denon Quick Select 1 sequence completed. An independent Sunroom Volume Up command ran during the wait. Power and mute histories alternated configured ON/OFF paths; changed saves reset histories; missing paths and failures did not advance them. Observed equipment behavior and HTTP acknowledgment were recorded separately.

### October 28–29 — modes and inbound pacing

GP2 press/release events, GP17 filesystem mode, and GP18 live CONFIG/RUN changes were exercised. Changing inbound web polling from 10 ms to 1 ms substantially improved Chrome/Safari CONFIG loading. The physical polling system remained enabled during successful browser tests.

### October 31–November 2 — room selector and Power Toggle

The three-position selector first passed a standalone electrical test and was later integrated on GP3/GP6/GP7, preserving GP4/GP5 for I²C. Den and Sunroom Power Toggle ON/OFF passed, with Room 3 safely rejected before queue admission.

### November 3 — Denon TCP, mixed queue, and volume encoder

The Denon TCP test exercised ten volume commands over a persistent connection, reporting approximately **606 ms** overall and multiple pacing waits. Queue regression cases covered mixed TCP/HTTP ordering, pacing preservation, future-dated tasks, custom-action waits with interleaved volume, and queue cancellation after simulated HTTP failure. The physical Bourns encoder was exercised at slow, moderate, and aggressive rotation rates against the Sunroom AVR.

These results are **bounded test evidence**, not certification of indefinite connection stability, exhaustive fault recovery, or guaranteed encoder transition capture under every blocking operation. See [Development History](DEVELOPMENT_HISTORY.md) for the dated engineering record and test context.

---

## 13. Operational limitations and next investigations

- **Physical controls:** Volume rotation, room selection, and Power Toggle work; volume push-to-mute, custom-action encoder, other buttons, display, and audio remain pending.
- **Denon TCP:** Persistent single-receiver socket; no response parser, status polling, or retry of uncertain sends.
- **Generic HTTP:** Bounded but synchronous, fresh TCP connection per command, no TLS/authentication/body parser.
- **Input capture:** The 1 ms target poll helps, but blocking network operations can still hide encoder transitions.
- **Queue:** One execution failure cancels remaining work; no retries or rollback.
- **Room 3:** Selector position works, but no room is configured and no fallback occurs.
- **State:** Power/mute histories track commands, not equipment reality.
- **Management:** Single-client, trusted-LAN-only interface; no application authentication.
- **Configuration:** Verified writes and backups reduce risk but cannot guarantee recovery from every power loss.
- **Future protocols:** Apple TV discovery, pairing, authenticated sessions, and commands are not implemented.

Priorities for further measured tests include stale Denon TCP connections after AVR restart, switching receivers during bursts, network interruptions, high-rate encoder capture while other HTTP requests execute, queue pressure, malformed responses, and long uptime.

The next physical work should reuse the existing encoder/button drivers, physical coordinator, adapter selection, and shared queue. Do not introduce speculative protocol modules or a second action execution path merely because it is possible.

**The Dumb Queue™ buffers traffic. It does not repeal the laws of TCP.**

---

## 14. Related documents

- [Architecture](ARCHITECTURE.md) — component boundaries and system invariants.
- [Configuration & Recovery](CONFIGURATION.md) — Config v4 schema, revisions, persistence, recovery.
- [Operating Modes](OPERATING_MODES.md) — GP17/GP18 procedures.
- [Hardware & Physical Controls](HARDWARE_CONTROLS.md) — components, GPIO, mechanical integration.
- [Development & Deployment](DEVELOPMENT.md) — iPad-first workflow and tests.
- [Development History](DEVELOPMENT_HISTORY.md) — chronological experiments and evidence.
- [`samples/device_config_roku_denon_sample.json`](../samples/device_config_roku_denon_sample.json) — readable Config v4 example.

---

**THE CLONKER 10000**  
*Less sleek. More CLONK.*  
**CLONK! ⚡🔩**
