
# The Clonker 10000 — Firmware, Network & Clock

**Design reference:** Updated November 3, 2026  
**Platform:** Raspberry Pi Pico 2 W / CircuitPython 10.3.1  
**Current baseline:** Chapter 6 — Config v4, Dumb Queue™, physical controls, and protocol adapters  
**Scope:** Firmware behavior, networking, scheduler timing, protocol adapters, diagnostics, tests, and operational limitations.

> One Monster. One Dumb Queue™. More than one way to deliver a CLONK.

---

## 1. Purpose and verified boundary

This document describes **how the running firmware operates**, not a proposed design or complete development diary.

Related responsibilities:

- [Architecture](ARCHITECTURE.md) — component boundaries and invariants.
- [Configuration](CONFIGURATION.md) — configuration schema, persistence, and recovery.
- [Hardware & Physical Controls](HARDWARE_CONTROLS.md) — GPIO, components, and mechanical integration.
- [Development History](DEVELOPMENT_HISTORY.md) — chronological experiments, decisions, and test evidence.

### Implemented and exercised

- Wi-Fi networking and Config v4 JSON configuration.
- Browser configuration editor and Test Remote.
- CONFIG-only inbound management HTTP on port 9090.
- Fourteen fundamental actions and room-specific custom actions.
- Shared Dumb Queue™ for browser and physical commands.
- Generic bounded blocking HTTP GET/POST.
- Signature-based protocol adapter selection.
- Persistent Denon TCP volume control.
- Roku ECP held-key volume control.
- Roku ECP mute through generic HTTP.
- GP17 SERVICE/DEVICE and GP18 CONFIG/RUN switches.
- GP2 physical Power Toggle.
- GP3/GP6/GP7 three-position room selector.
- GP8/GP9 Bourns volume encoder.
- GP10 volume-encoder push-to-mute.
- Independent per-room power/mute toggle histories.
- Cooperative custom-action waits and failure cancellation.

**November 3 milestone:** One physical volume encoder successfully controlled two rooms using different transport protocols. Den used persistent Denon TCP; Sunroom used Roku ECP held-volume commands, with receiver volume changes observed through HDMI-CEC.

Fast rotation, direction reversal, and approximately three seconds of sustained rotation were exercised. Physical push-to-mute was verified in both rooms.

### Pending or not exhaustively tested

The second encoder for custom-action selection, navigation/Back/Home/playback buttons, OLED, audible feedback, battery/sleep, and final enclosure remain pending.

Apple TV pairing/control, custom destination slots, Denon TCP response parsing, long-uptime operation, and exhaustive outage recovery are also pending.

The management service has **no application-level authentication**. Use only on a trusted LAN; never expose port 9090 to the public internet.

---

## 2. Firmware layout and ownership

| Repository path | Responsibility |
|---|---|
| `firmware/boot.py` | GP17 filesystem ownership at boot |
| `firmware/code.py` | CircuitPython application entry |
| `firmware/clonker/main.py` | Initialization, operating modes, cooperative scheduler |
| `firmware/clonker/device_config_v2.py` | Config v4 validation, active configuration, revisions, persistence |
| `firmware/clonker/actions.py` | Action admission, Dumb Queue™, execution coordination, cancellation |
| `firmware/clonker/device_adapters.py` | Command-signature recognition, cached adapter selection, execution delegation |
| `firmware/clonker/devices/denon.py` | Persistent Denon TCP volume transport |
| `firmware/clonker/devices/roku.py` | Roku ECP held-volume controller |
| `firmware/clonker/net/http_transport.py` | Bounded blocking outbound HTTP |
| `firmware/clonker/net/web.py` | CONFIG-only inbound HTTP and management APIs |
| `firmware/clonker/controls/pins.py` | GPIO assignments |
| `firmware/clonker/controls/buttons.py` | Debounced momentary inputs |
| `firmware/clonker/controls/selectors.py` | Physical room selection |
| `firmware/clonker/controls/encoders.py` | Reusable quadrature encoder driver |
| `firmware/clonker/controls/physical.py` | Physical polling, event mapping, room-aware dispatch |
| `firmware/clonker/controls/switches.py` | CONFIG/RUN state and development overrides |
| `firmware/clonker/system/clock.py` | Clock reference |
| `firmware/clonker/system/logger.py` | Serial diagnostics |
| `firmware/clonker/www/` | Browser editor and Test Remote |
| `firmware/clonker/legacy/` | Historical XML code |

The active Pico configuration path is:

`/clonker/device_config.json`

The repository's `firmware/` prefix is not part of that runtime path.

The historical filename `device_config_v2.py` does **not** mean the active schema is v2. The current schema is Config v4.

### Separation of concerns

The application follows these boundaries:

1. GPIO drivers recognize electrical input events.
2. Physical coordination translates events into generic actions.
3. Configuration supplies destinations, methods, and command paths.
4. `actions.py` owns the shared queue and action lifecycle.
5. `device_adapters.py` selects and invokes the appropriate transport.
6. Transport modules perform network operations.

Physical controls do not contain Denon or Roku protocol knowledge.

There is no second volume queue and no independent execution pipeline for specialized adapters.

---

## 3. Startup, modes, and scheduler

`code.py` starts `clonker.main.main()`.

The application loads the active validated configuration, logs configured rooms, initializes available physical controls, and enters a cooperative event loop.

Missing optional hardware is logged rather than preventing the application from running.

### 3.1 Scheduling constants

```python
PHYSICAL_CONTROLS_ENABLED = True
PHYSICAL_POLL_INTERVAL = 0.001
WEB_POLL_INTERVAL = 0.001
ACTION_POLL_INTERVAL = 0.01
```

The main loop also uses a short `time.sleep(0.001)` yield.

These are **target service intervals**, not threads, interrupts, or guaranteed maximum latencies.

The cooperative scheduler services:

- Physical inputs.
- At most one eligible queued action.
- Protocol adapter maintenance, including Roku held-key release.
- CONFIG/RUN mode evaluation.
- Inbound management HTTP when enabled.
- A short yield.

The Roku adapter must continue receiving maintenance polls even when the Dumb Queue™ is empty. A held key may require release after the final encoder detent has already been executed.

### 3.2 Independent operating-mode switches

| Switch | Open/HIGH | Grounded/LOW | Change requires |
|---|---|---|---|
| GP17 | SERVICE — USB owns filesystem writes | DEVICE — Pico owns writes | Full power cycle |
| GP18 | RUN — management listener off | CONFIG — management listener on | Live switch change |

Ctrl+D performs a CircuitPython soft reboot. It is not equivalent to a full power cycle for filesystem ownership.

SERVICE + CONFIG permits configuration inspection and Test Remote operation but not Pico-side persistent configuration saves.

DEVICE + CONFIG permits saves.

DEVICE + RUN is normal remote operation.

The operating-mode switches are independent of receiver power commands.

### 3.3 Physical event polling

Current GPIO assignments:

| Function | GPIO |
|---|---|
| Power Toggle | GP2 |
| Room selector — Den | GP3 |
| Room selector — Sunroom | GP6 |
| Room selector — reserved Room 3 | GP7 |
| Volume encoder A/B | GP8/GP9 |
| Volume encoder push-to-mute | GP10 |
| SERVICE/DEVICE | GP17 |
| CONFIG/RUN | GP18 |
| OLED I²C reservation | GP4/GP5 |

`physical.poll()` updates room selection, polls initialized buttons, and polls the volume encoder.

The room selector requires a valid grounded input and 50 ms stability.

Momentary buttons use a default 30 ms debounce.

Encoder transitions are decoded by the reusable `Encoder` class. Completed movements become `volume-up` or `volume-down` fundamental actions.

The encoder's separate momentary switch generates `mute-toggle`.

`physical.dispatch_selected(action_id)` rejects unavailable rooms before queue admission. Reserved Room 3 must not silently control Den or Sunroom.

Browser Test Remote room selection remains independent of the physical room selector.

Outbound synchronous network operations can still delay GPIO polling. Neither the 1 ms target nor the adapter architecture guarantees capture of every electrical transition under all conditions.

---

## 4. Wi-Fi, endpoints, and socket ownership

CircuitPython `wifi.radio` and `socketpool` provide network access.

Wi-Fi credentials belong in private `settings.toml`, not committed examples.

The development installation has used Pico `192.168.50.12`, with management pages such as:

- `http://192.168.50.12:9090/`
- `http://192.168.50.12:9090/remote.html`

These are installation-specific addresses, not firmware defaults.

### Networking roles

The firmware has four distinct networking responsibilities:

1. **Inbound management HTTP:** Cooperative single-client listener, CONFIG mode only.
2. **Generic outbound HTTP:** Bounded synchronous request using a fresh TCP connection.
3. **Denon TCP adapter:** Persistent outbound TCP connection for recognized fundamental volume commands.
4. **Roku held-volume adapter:** State-managed ECP keydown/keyup requests using the generic outbound HTTP transport.

The generic HTTP transport reuses its SocketPool object but does not reuse individual HTTP TCP connections.

The Denon adapter maintains its own persistent socket state.

The Roku adapter maintains logical held-key state, not a persistent HTTP socket.

---

## 5. Inbound management HTTP

**Module:** `clonker/net/web.py`  
**Port:** `9090`  
**Availability:** CONFIG mode only  
**Model:** Nonblocking cooperative listener, one active client.

The listener accepts a connection, receives a bounded request, prepares a response, sends bounded chunks, and closes the client.

A single active-client slot is not concurrent request processing.

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
| `GET /api/config` | Active configuration, revision, writability metadata |
| `POST /api/config` | Revision-protected validated save |
| `GET /api/clock` | Clock source and timestamp |
| `POST /api/clock?utc=...` | Browser-provided UTC reference |
| `POST /api/action?room=...&action=...` | Validate and enqueue an action |

An API response reporting `queued` means admission, not network transmission or equipment execution.

The browser and physical controls converge at `actions.dispatch()`.

### 5.2 Silent clients and browser pacing

Some browser connections arrived without sending request data and occupied the single client slot.

A short idle timeout now abandons completely silent connections. The current source uses 0.2 seconds.

During Chapter 5, CONFIG pages sometimes stalled or returned `ERR_EMPTY_RESPONSE`.

Disabling GPIO polling did not resolve the issue.

Changing `WEB_POLL_INTERVAL` from 10 ms to 1 ms substantially improved repeated Chrome and Safari tests.

Physical controls were re-enabled and inbound diagnostics disabled.

Occasional browser-client idle timeout messages were still observed during Chapter 6. Their precise cause was not established, and they were not demonstrated to be adapter regressions.

### 5.3 Saves and active state

The configuration engine validates schema, revision, filesystem writability, and persistence safeguards.

The active RAM configuration is authoritative.

A successful changed save publishes the validated configuration, rebuilds adapter selections, clears pending queue work, and resets volatile toggle histories.

Adapter lifecycle coordination must account for any outstanding Roku held key when configuration changes.

An unchanged save preserves pending work and toggle state.

A rejected save does not publish a replacement adapter cache.

See [Configuration](CONFIGURATION.md) for exact file rotation, recovery, and revision behavior.

The Pico filesystem does not automatically synchronize with GitHub. Protect browser-edited device configuration during firmware deployment.

---

## 6. The Dumb Queue™

**Module:** `clonker/actions.py`  
**Capacity:** 128 entries  
**Main interface:** `dispatch(room_id, action_id, delay_seconds=0)`, `poll()`, `clear()`, `status()`.

> One queue. One poller. One shared execution path.

### 6.1 Admission and identity

Admission validates the room, action, delay, and capacity.

Fundamental actions use stable IDs; custom actions use room-specific saved IDs.

Tasks retain compact identity, step index, and due time rather than copied endpoint definitions.

The actual command is resolved from active configuration when executed.

A custom action occupies one queue entry, advancing one step at a time.

Immediate tasks use `due = 0`; delayed tasks use a `time.monotonic()` deadline.

### 6.2 Eligibility, ordering, and pacing

`poll()` scans for the first eligible task.

A future-dated custom step does not block an immediate action.

Among currently eligible tasks, queue order matters. This is not strict FIFO across delayed work.

A recognized Denon TCP volume command must satisfy the adapter's minimum 50 ms interval.

If the selected eligible command is waiting for pacing, it stays in its queue position and `poll()` returns without executing a later command. This prevents overtaking.

Pacing uses monotonic time rather than sleeping inside the queue.

The action scheduler targets a 10 ms poll interval, with at most one queued command executed per poll.

### 6.3 Fundamental commands and toggle histories

Ordinary fundamental actions resolve the configured destination, method, and path.

Missing endpoints or blank paths produce logged no-ops.

`power-toggle` and `mute-toggle` select configured ON/OFF paths using independent volatile `(room_id, action_id)` direction histories, defaulting to ON.

History advances only after successful transmission. Failures and no-ops do not advance it.

This is **last-successful-command direction**, not equipment-state discovery.

HDMI-CEC, other remotes, and device applications can change actual state without Clonker knowing.

### 6.4 Custom actions

Config v4 supports up to 16 custom actions per room, each containing 1–16 ordered steps.

Steps specify a built-in destination, GET/POST, command path, and `wait_after_ms`.

Waits range from 0 to 60,000 ms, with zero required on the final step.

After a successful step, the task is requeued with the next due time calculated after the preceding request completes.

Other eligible actions can run during a wait.

Current custom steps always use generic HTTP, even when their paths resemble recognized specialized volume commands.

There is no macro thread, branching engine, or rollback.

### 6.5 Failure policy and status

An execution exception discards remaining queued tasks, including unfinished custom work, and logs the failure.

New actions can subsequently be admitted.

The Dumb Queue™ does not automatically retry failed commands because the remote cannot safely assume whether an uncertain network command reached the equipment.

This queue policy is distinct from the Roku adapter's bounded attempts to release a previously held key.

Adapter cleanup may require additional network work after queue cancellation.

`status()` reports current depth, capacity, peak depth, last result, and last error.

Queue admission, successful network transmission, and confirmed equipment behavior are distinct evidence levels.

---

## 7. Device adapter architecture

**Module:** `clonker/device_adapters.py`

The adapter layer separates **what action was requested** from **how the command reaches the equipment**.

Adapter selection is based on recognized command signatures, not room names, manufacturer labels, or fixed device positions.

### 7.1 Supported execution paths

| Adapter | Selection | Transport |
|---|---|---|
| `denon-tcp` | Recognized Denon fundamental volume commands | Persistent TCP port 23 |
| `roku-hold` | Recognized Roku fundamental volume commands | ECP keydown/keyup over HTTP |
| `generic-http` | Other configured commands | Bounded HTTP GET/POST |

Only fundamental `volume-up` and `volume-down` actions are eligible for specialized adapter selection.

Custom-action steps retain generic HTTP execution.

### 7.2 Recognized Denon signatures

Method: GET

```text
/goform/formiPhoneAppDirect.xml?MVUP   -> MVUP
/goform/formiPhoneAppDirect.xml?MVDOWN -> MVDOWN
```

These signatures select `denon-tcp`.

The configured endpoint identifies the receiver host; the adapter uses native TCP port 23.

### 7.3 Recognized Roku signatures

Method: POST

```text
/keypress/VolumeUp   -> up
/keypress/VolumeDown -> down
```

These signatures select `roku-hold`.

The configured paths are used for recognition. The adapter translates them into held-key operations:

```text
POST /keydown/VolumeUp
POST /keyup/VolumeUp

POST /keydown/VolumeDown
POST /keyup/VolumeDown
```

### 7.4 Adapter cache

Specialized selections are cached by `(room_id, action_id)`.

No adapter identifiers are written into Config v4 JSON.

`device_adapters.rebuild(config)` constructs a replacement routing map for the active configuration.

`lookup(room_id, action_id)` returns a specialized selection or generic HTTP fallback.

The adapter layer also provides execution, readiness, maintenance polling, and cleanup coordination.

The cache is routing metadata, not an equipment-state cache or second queue.

Transport-specific state belongs to the appropriate adapter.

---

## 8. Denon persistent TCP adapter

**Module:** `clonker/devices/denon.py`  
**Port:** TCP 23  
**Supported commands:** `MVUP`, `MVDOWN`

Current constants:

```python
TCP_PORT = 23
SOCKET_TIMEOUT = 1.0
MIN_COMMAND_INTERVAL = 0.05
```

### 8.1 Connection lifecycle

The adapter extracts an IPv4 host from the configured endpoint, which may include an HTTP port.

It connects to the receiver on TCP port 23.

The active socket is reused for subsequent commands to the same host.

Targeting a different receiver closes the old connection before opening the new one.

`close()` resets socket, host, and pacing state.

The adapter maintains at most one active receiver connection.

It is not a pool of connections to all rooms.

Initial connection and socket writes remain synchronous.

### 8.2 Pacing and transmission

`ready()` compares monotonic time with the next allowed send time.

The queue checks readiness before removing the selected command.

`send_volume(endpoint, command)` sends the ASCII native command terminated by carriage return (`\r`).

After a successful write, the next allowed send time is advanced by at least 50 ms.

If pacing is not ready, the caller preserves the task.

An exception closes the connection and propagates to the queue failure policy.

No automatic retry is attempted.

A successful `sendall()` means bytes were handed to the TCP stack. It does not prove that the AVR processed the command or reached a particular volume.

### 8.3 Not implemented

The adapter does not yet:

- Parse CR-terminated Denon status responses.
- Consume unsolicited receiver messages.
- Poll receiver state.
- Maintain multiple simultaneous AVR sockets.
- Automatically retry uncertain commands.

Stale connections and long-duration recovery remain subjects for additional testing.

---

## 9. Roku ECP held-volume adapter

**Module:** `clonker/devices/roku.py`  
**Transport:** Roku ECP over bounded HTTP POST  
**Supported directions:** `up`, `down`

### 9.1 Design objective

Ordinary Roku ECP volume commands can be sent as individual keypresses.

However, one HTTP request per encoder detent introduces noticeable overhead during fast rotation.

The held-volume adapter instead treats encoder movement as a temporary key hold.

The first detent starts a hold. Additional same-direction detents extend it locally.

This reduces network traffic while allowing Roku to repeat the held volume command.

### 9.2 Current timing

| Parameter | Value | Purpose |
|---|---:|---|
| Idle release | 250 ms | Release after rotation stops |
| Maximum hold | 2 seconds | Bound continuous hold duration |
| Failed-release retry | 500 ms | Avoid tight retry loops |

These are experimental values retained after successful physical testing.

They are not guaranteed to produce identical volume changes across Roku models, CEC implementations, or receivers.

### 9.3 First detent

For a new direction, the adapter sends the appropriate keydown request.

Example:

```text
POST /keydown/VolumeUp
```

After successful acknowledgment, the adapter records:

- Endpoint.
- Direction.
- Hold start time.
- Idle-release deadline.

The adapter does not mark a key as held before the initial request is acknowledged.

An uncertain keydown outcome is not automatically retried.

### 9.4 Same-direction movement

While the same key remains held, additional detents refresh the idle deadline.

No additional HTTP request is required.

The execution log distinguishes a new `keydown` from a local `extended` operation.

A local extension normally completes in approximately 0 ms because it performs no network I/O.

This is the principal performance advantage over one HTTP request per detent.

### 9.5 Idle release

The main scheduler continues calling adapter maintenance even when the action queue is empty.

When the idle deadline expires, the adapter attempts the corresponding keyup:

```text
POST /keyup/VolumeUp
```

The remote should then stop repeating volume changes.

A small amount of visible volume overshoot may occur because the command passes through Roku and potentially HDMI-CEC before reaching the receiver.

### 9.6 Direction reversal

When the encoder changes direction, the adapter must release the previous key before beginning the opposite hold.

Example:

```text
POST /keyup/VolumeUp
POST /keydown/VolumeDown
```

The opposite keydown is not allowed to bypass an unresolved release.

This avoids knowingly leaving opposing volume commands active.

The two HTTP requests still introduce some reversal latency.

### 9.7 Maximum-hold behavior

A hold is limited to approximately two seconds.

Continued rotation beyond that boundary releases the previous hold and can begin a new one.

This prevents one uninterrupted local hold from extending indefinitely.

The physical tests showed a new keydown after an extended series of local hold operations, consistent with maximum-hold restart behavior.

The precise keyup sequence was not independently traced during that experiment.

### 9.8 Failed-release safety

If a keyup request fails, the adapter retains the unresolved held-key state.

New keydowns must not proceed until the prior release has been resolved.

Retry attempts are paced at approximately 500 ms rather than occurring on every fast scheduler poll.

This is a specialized cleanup mechanism, not a general queue retry policy.

Network failure can still prevent confirmation that the remote received a release. Software cannot guarantee remote key state when the network is unavailable.

### 9.9 Lifecycle coordination

The adapter exposes maintenance and cleanup operations for the application lifecycle.

Held-key cleanup is relevant when:

- Rotation stops.
- Direction changes.
- The maximum hold is reached.
- Queued work is canceled.
- Configuration is replaced.
- The application shuts down.

Cleanup is best effort and remains subject to network availability.

### 9.10 Diagnostics

The Roku adapter wraps outbound HTTP failures with operation-specific context.

A diagnostic can identify:

- Keydown or keyup.
- Volume direction.
- Destination endpoint.
- Original exception representation.

For example:

```text
ROKU /keyup/VolumeUp -> 192.168.50.28:8060 failed: OSError(119,)
```

This is illustrative; the actual exception formatting depends on CircuitPython and the failure path.

One transient `OSError(119)` occurred during early reversal testing before these diagnostics were added.

The precise failing operation was not established.

Subsequent tests recovered successfully and showed no further visible socket errors.

### 9.11 What the adapter does not guarantee

The adapter does not guarantee:

- Exactly one receiver volume step per encoder detent.
- A fixed volume-change rate.
- Zero display lag or overshoot.
- Delivery confirmation beyond HTTP acknowledgment.
- Recovery from every network failure.
- Accurate knowledge of the receiver's actual volume.
- Guaranteed key release when the remote becomes unreachable.

It is a time-based physical-control mechanism, not a volume-position controller.

---

## 10. Generic outbound HTTP transport

**Module:** `clonker/net/http_transport.py`  
**Interface:** `send(endpoint, method, path)`

The transport accepts dotted IPv4 with optional `:port` (default 80), GET or POST, and an absolute path.

It creates a TCP socket, sends a minimal HTTP/1.1 request with an empty body, reads a bounded status line, accepts HTTP 2xx, and closes the socket in `finally`.

Current constants:

```python
DEFAULT_PORT = 80
SOCKET_TIMEOUT = 0.5
TOTAL_TIMEOUT = 1.5
MAX_STATUS_LINE = 128
HTTP_DIAGNOSTICS = False
```

The socket timeout bounds individual blocking operations.

The total deadline is checked between operations and is not an asynchronous hard stop for a single socket call.

Non-2xx responses, malformed requests, connection errors, and timeouts raise exceptions for the caller to handle.

The transport does not provide full response-body parsing, TLS, authentication, redirects, persistent HTTP connections, arbitrary POST bodies, or device-specific semantics.

### 10.1 Generic HTTP remains necessary

Generic HTTP handles:

- Roku navigation and ordinary ECP keypresses.
- Roku mute.
- Denon HTTP power and mute commands.
- Custom-action steps.
- Other configured GET/POST actions without specialized signatures.

Roku mute is deliberately **not** a held-volume operation.

The Sunroom mute configuration uses:

```text
POST /keypress/VolumeMute
```

for both ON and OFF paths.

This works because the Roku command itself toggles mute.

The Clonker's per-room toggle history still records which logical toggle direction was last successfully sent.

### 10.2 Why HTTP remains bounded and blocking

Earlier nonblocking TCP experiments on the tested CircuitPython platform encountered `OSError(119)` and lacked a usable `getsockopt(SO_ERROR)` inspection path.

Bounded blocking HTTP was selected for predictable behavior and simplicity.

This does not prove that nonblocking outbound networking is impossible.

Historical ordinary HTTP requests often took approximately 86–164 ms, with connection establishment contributing substantially.

A fresh HTTP connection for every volume detent made rapid physical rotation sluggish.

The specialized Denon and Roku volume adapters address this specific problem in different ways.

Any synchronous outbound socket operation temporarily pauses the cooperative scheduler, including GPIO and management HTTP polling.

The queue can buffer admitted actions. It cannot reconstruct electrical transitions that were never sampled.

---

## 11. Equipment mapping and observed behavior

The current installation has two configured rooms: Den and Sunroom.

Config v4 permits one to three rooms and three generic built-in destinations per room:

- `device-1`
- `device-2`
- `device-3`

Browser labels commonly read TV, AVR, and Streaming, but those labels do not enforce protocols.

### 11.1 Development installation endpoints

| Equipment | Installation-specific endpoint | Observation |
|---|---|---|
| Den AVR-X3700H | `192.168.50.44:8080` | Denon HTTP and persistent TCP volume |
| Den Roku Ultra | `192.168.50.43:8060` | Roku ECP commands |
| Sunroom AVR-X1800H | `192.168.50.40:8080` | Denon HTTP and earlier TCP volume |
| Sunroom Roku Ultra | `192.168.50.28:8060` | Roku ECP navigation, volume, and mute |

These addresses are records of the development installation, not defaults or configuration requirements.

### 11.2 Current mixed-volume configuration

| Room | Volume action configuration | Selected adapter |
|---|---|---|
| Den | Denon HTTP command signatures | `denon-tcp` |
| Sunroom | Roku ECP VolumeUp/VolumeDown signatures | `roku-hold` |

The Sunroom Roku controls the Denon receiver's volume through the equipment's HDMI-CEC path.

This demonstrates that adapter selection is based on configured command signatures rather than room identity.

### 11.3 Physical Power Toggle

GP2 Power Toggle successfully controlled Den and Sunroom ON/OFF through the selected room and shared queue.

The reserved Room 3 position produced a safe no-op.

Independent per-room toggle direction histories were observed.

These tests verified equipment behavior, not automatic equipment-state detection.

### 11.4 Physical volume

The Bourns PEC11R-4215F-S0024 encoder on GP8/GP9 generates generic volume actions through `physical.py`.

The Den room uses persistent Denon TCP.

The Sunroom uses Roku held-volume ECP.

The encoder remains a relative control; its shaft position does not encode an absolute volume value.

### 11.5 Physical push-to-mute

The Bourns encoder's separate momentary pushbutton is wired to GND and GP10.

The existing button driver maps `VOLUME_MUTE` to the generic `mute-toggle` fundamental action.

Observed results:

- Sunroom: Roku ECP `VolumeMute`, HTTP 200, receiver mute/unmute confirmed.
- Den: Denon HTTP mute commands, HTTP 200, receiver mute/unmute confirmed.

No separate mute execution system was required.

### 11.6 Custom-action equipment test

The Sunroom *Movie* action used:

1. Roku `POST /keypress/Home`.
2. A 3,000 ms wait after the first step completed.
3. Denon `GET /goform/formiPhoneAppDirect.xml?MSQUICK1`.

Both HTTP requests returned 200, and the queue logged custom completion.

An independent volume command was also observed executing during the custom wait in earlier tests.

---

## 12. Clock and diagnostics

**Modules:** `clonker/system/clock.py` and `clonker/system/logger.py`.

Before browser clock synchronization, firmware uses `DEFAULTTIME` and monotonic uptime rather than asserting an authoritative wall-clock date.

The browser can submit UTC Unix time through `/api/clock`.

Readable timestamps are calculated from that reference and subsequent monotonic elapsed time.

Queue deadlines, custom waits, Denon pacing, and Roku hold timing use `time.monotonic()`.

Browser clock changes must not shift these deadlines.

Automated NTP synchronization is not established by the current verified baseline.

Serial logging records action admission, execution, failures, room changes, and operating-mode transitions.

There is no persistent flash log or background logging server.

Keep routine logging modest. Continuous diagnostics can distort timing and browser responsiveness.

---

## 13. Verification record and evidence limits

### October 21 — outbound HTTP and queue

Chapter 3 tests demonstrated Roku GET/POST, Denon HTTP volume, bounded unreachable-endpoint failures, and post-failure recovery without resetting the socket pool.

Two reliability runs recorded 24/24 successful reachable requests, two expected unreachable failures, and two successful recoveries.

A five-command burst drained sequentially with HTTP 200 responses and reported times of 117.2, 125.0, 85.9, 85.9, and 85.9 ms.

These were HTTP-era measurements, not specialized adapter performance numbers.

### October 27 — custom actions and toggles

The Sunroom Roku Home → 3-second wait → Denon Quick Select 1 sequence completed.

An independent Sunroom Volume Up command ran during the wait.

Power and mute histories alternated configured ON/OFF paths.

Changed saves reset histories; missing paths and failures did not advance them.

Observed equipment behavior and HTTP acknowledgment were recorded separately.

### October 28–29 — modes and inbound pacing

GP2 press/release events, GP17 filesystem mode, and GP18 live CONFIG/RUN changes were exercised.

Changing inbound web polling from 10 ms to 1 ms substantially improved Chrome/Safari CONFIG loading.

The physical polling system remained enabled during successful browser tests.

### October 31–November 2 — room selector and Power Toggle

The three-position selector first passed a standalone electrical test and was later integrated on GP3/GP6/GP7, preserving GP4/GP5 for I²C.

Den and Sunroom Power Toggle ON/OFF passed, with Room 3 safely rejected before queue admission.

### November 3 — Denon TCP and mixed queue

The Denon TCP test exercised ten volume commands over a persistent connection, reporting approximately 606 ms overall and multiple pacing waits.

Queue regression cases covered:

- Mixed TCP/HTTP ordering.
- Pacing preservation.
- Future-dated tasks.
- Custom-action waits with interleaved volume.
- Queue cancellation after simulated HTTP failure.

The physical Bourns encoder was exercised at slow, moderate, and aggressive rotation rates against the receiver.

### November 3 — Roku held-volume

The Sunroom configuration was changed to use Roku ECP volume commands.

Adapter inspection confirmed Den `denon-tcp` and Sunroom `roku-hold`.

Observed physical tests:

| Test | Observation |
|---|---|
| Single clockwise detent | Receiver increased 0.5 dB |
| Five steady clockwise detents | -35.0 dB to -33.5 dB |
| Direction reversal | Commands executed in both directions |
| Fast clockwise rotation | One keydown followed by local extensions |
| Fast counterclockwise rotation | One keydown followed by local extensions |
| Approximately three seconds clockwise | Smooth, steady volume increase |
| Stop after rotation | Very slight overshoot; volume stopped |
| Transient socket error recovery | Subsequent VolumeDown worked |
| Later fast/sustained testing | No additional visible errors |

Fast and sustained tests were performed in RUN mode.

The receiver's volume bar lagged physical movement slightly but was considered acceptably responsive.

A later keydown during sustained rotation was consistent with the two-second maximum-hold restart.

These tests establish practical functionality, not exhaustive timing guarantees.

### November 3 — physical push-to-mute

GP10 was assigned to the Bourns encoder pushbutton.

The existing `VOLUME_MUTE` physical mapping dispatched `mute-toggle`.

Physical mute and unmute passed in both rooms:

- Sunroom through Roku ECP.
- Den through Denon HTTP.

The logs showed successful command execution and independent per-room toggle histories.

---

## 14. Operational limitations and next investigations

### Physical controls

The room selector, Power Toggle, volume encoder, and volume push-to-mute are operational.

The second encoder, navigation, Home, Back, playback, display, and audio remain pending.

### Denon TCP

The adapter maintains one persistent receiver socket.

There is no response parser, state polling, or automatic retry of uncertain sends.

### Roku held-volume

The adapter is time-based rather than detent-count-based.

Behavior depends on HTTP responsiveness, Roku repeat behavior, and potentially HDMI-CEC.

Slight display lag and volume overshoot have been observed.

One transient `OSError(119)` occurred during early reversal testing. Later tests recovered and completed without additional visible errors.

Operation-specific diagnostics are now available.

The maximum-hold release sequence was inferred from behavior and logs rather than independently traced.

Fast rotation with simultaneous CONFIG-mode browser activity has not been equivalently stress-tested.

### Generic HTTP

The transport is bounded but synchronous, with a fresh TCP connection per request.

It does not implement TLS, application authentication, or full response-body parsing.

### Input capture

The 1 ms physical poll target helps responsiveness, but blocking network operations can still hide encoder transitions.

### Queue

One execution failure cancels remaining queued work.

There is no general retry or rollback mechanism.

### Room 3

The selector position works, but no room is configured.

No fallback to another room occurs.

### Equipment state

Power/mute histories track successfully transmitted commands, not equipment reality.

### Management

The CONFIG interface is single-client and trusted-LAN-only.

It has no application-level authentication.

### Configuration

Validated writes and backups reduce risk but cannot guarantee recovery from every power loss.

### Future protocols

Apple TV discovery, pairing, authenticated sessions, and commands are not implemented.

### Further investigations

Useful future tests include:

- Stale Denon TCP connections after AVR restart.
- Switching receivers during bursts.
- Network interruption during Roku keydown or keyup.
- Roku held-volume under simultaneous CONFIG-mode browser activity.
- High-rate encoder capture during other HTTP operations.
- Queue pressure and malformed responses.
- Long-uptime operation and repeated reconnects.

The next physical work should reuse the existing encoder/button drivers, physical coordinator, adapter selection, and shared queue.

Do not introduce speculative protocol modules or a second action execution path merely because it is possible.

**The Dumb Queue™ buffers traffic. It does not repeal the laws of TCP.**

---

## 15. Related documents

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
