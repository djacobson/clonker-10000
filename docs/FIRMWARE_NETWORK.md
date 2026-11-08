# The Clonker 10000 — Firmware, Network & Clock

**Updated:** November 8, 2026  
**Platform:** Raspberry Pi Pico 2 W / CircuitPython 10.3.1  
**Current baseline:** Chapter 7 closeout — Config v4, Dumb Queue™, completed physical assembly, both Bourns encoders, Roku holds, initial SH1106 OLED integration, and shared PERF instrumentation  
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
- Physical Power Toggle and three-position room selector.
- Both Bourns encoders, including volume/mute and custom-action selection/execution.
- Physical navigation, Home, Back, Select, and playback input integration.
- Six Roku physical-button holds using keydown/keyup.
- Initial SH1106 OLED integration and custom-action display feedback.
- Independent per-room power/mute toggle histories.
- Cooperative custom-action waits and failure cancellation.
- Three-room Config v4 installation, including a blank Room 3 placeholder.
- Improved browser responsiveness during Chapter 7 CONFIG-mode testing.
- Shared PERF instrumentation for scheduler and subsystem diagnostics.
- Completed physical wiring, mounting, soldering, and strain relief.

**Chapter 7 milestone:** The Clonker now has an assembled physical control interface, room-aware command execution, operational custom-action selection, initial OLED feedback, and performance instrumentation suitable for continued investigation.

### Pending or not exhaustively tested

Further OLED uses, audible feedback, battery/sleep behavior, exhaustive long-uptime operation, and unresolved physical polling performance investigations remain future work.

Apple TV pairing/control, custom destination slots, Denon TCP response parsing, and exhaustive outage recovery are also pending.

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
| `firmware/clonker/device_adapters.py` | Command recognition, cached routing, execution and cleanup |
| `firmware/clonker/devices/denon.py` | Persistent Denon TCP volume transport |
| `firmware/clonker/devices/roku.py` | Roku ECP held-volume and physical-button holds |
| `firmware/clonker/net/http_transport.py` | Bounded blocking outbound HTTP |
| `firmware/clonker/net/web.py` | CONFIG-only inbound HTTP and management APIs |
| `firmware/clonker/controls/pins.py` | GPIO assignments |
| `firmware/clonker/controls/buttons.py` | Debounced momentary inputs |
| `firmware/clonker/controls/selectors.py` | Physical room selection |
| `firmware/clonker/controls/encoders.py` | Reusable quadrature encoder driver |
| `firmware/clonker/controls/physical.py` | Physical polling, action mapping, room-aware dispatch, hold context |
| `firmware/clonker/controls/switches.py` | CONFIG/RUN state and development overrides |
| `firmware/clonker/system/clock.py` | Clock reference |
| `firmware/clonker/system/logger.py` | Serial diagnostics |
| `firmware/clonker/system/perf.py` | Shared named performance measurements and statistics |
| `firmware/clonker/display/oled.py` | SH1106 OLED initialization, deferred rendering, and polling |
| `firmware/clonker/www/` | Browser editor and Test Remote |
| `firmware/clonker/legacy/` | Historical XML code |

The active Pico configuration path is:

`/clonker/device_config.json`

The repository's `firmware/` prefix is not part of that runtime path.

The historical filename `device_config_v2.py` does **not** mean the active schema is v2. The current schema is Config v4.

### Separation of concerns

1. GPIO drivers recognize electrical input events.
2. Physical coordination translates events into generic actions.
3. Configuration supplies destinations, methods, and command paths.
4. `actions.py` owns the shared queue and action lifecycle.
5. `device_adapters.py` selects and invokes the appropriate transport.
6. Transport modules perform network operations.

Physical controls do not contain Denon or Roku protocol implementation.

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

The cooperative scheduler services, in order:

1. Physical GPIO inputs.
2. At most one eligible queued action.
3. Protocol adapter maintenance.
4. CONFIG/RUN mode evaluation.
5. Inbound management HTTP when enabled.
6. A short yield.

The Roku adapter continues receiving maintenance polls even when the Dumb Queue™ is empty.

A held key may require release after the final queued action has completed.

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
| Room selector — Room 3 | GP7 |
| Volume encoder A/B | GP8/GP9 |
| Volume encoder push-to-mute | GP10 |
| Custom-action encoder A/B | GP11/GP12 |
| Custom-action encoder pushbutton | GP13 |
| Navigation Up | GP14 |
| Navigation Down | GP15 |
| Navigation Left | GP16 |
| SERVICE/DEVICE | GP17 |
| CONFIG/RUN | GP18 |
| Navigation Right | GP19 |
| Select / OK | GP20 |
| Back | GP21 |
| Home | GP22 |
| Skip Back | GP26 |
| Play/Pause | GP27 |
| Skip Forward | GP28 |
| OLED I²C reservation | GP4/GP5 |

`controls/pins.py` remains the authoritative assignment reference.

`physical.poll()` updates room selection, polls initialized buttons, and polls both active Bourns encoders.

The room selector requires a valid grounded input and 50 ms stability.

Momentary buttons use a default 30 ms debounce.

Encoder transitions are decoded by the reusable `Encoder` class.

Completed volume movements become `volume-up` or `volume-down` fundamental actions. The volume encoder's separate pushbutton generates `mute-toggle`.

The custom-action encoder cycles through the selected room's ordered custom actions. Its pushbutton dispatches the selected action through the existing execution path.

The OLED displays custom-action selections through the deferred display interface. Actual I²C updates occur during OLED polling rather than directly inside the selection handler.

Browser Test Remote room selection remains independent of the physical room selector.

Outbound synchronous network operations can delay GPIO polling. Neither the 1 ms target nor the adapter architecture guarantees capture of every electrical transition under all conditions.

### 3.4 Chapter 7 responsiveness work

Chapter 7 investigated slow Config page loads, occasional Test Remote timeouts, and competition between physical polling, diagnostics, and management HTTP.

Changes included reducing unnecessary polling and diagnostic overhead while preserving the cooperative scheduler.

Subsequent Safari and Chrome tests showed substantially improved responsiveness.

This did not introduce threads, a concurrent web server, or nonblocking outbound networking.

The fundamental limitation remains: a synchronous socket operation can temporarily delay other cooperative tasks.

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
4. **Roku ECP adapter:** State-managed keydown/keyup requests for encoder volume and physical-button holds.

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

| Setting | Current documented value |
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

The browser and physical controls converge at the shared action system.

### 5.2 Silent clients and browser pacing

Some browser connections arrived without sending request data and occupied the single client slot.

A short idle timeout abandons completely silent connections.

During Chapter 5, CONFIG pages sometimes stalled or returned `ERR_EMPTY_RESPONSE`.

Disabling GPIO polling did not resolve the issue.

Changing `WEB_POLL_INTERVAL` from 10 ms to 1 ms substantially improved repeated Chrome and Safari tests.

Physical controls were re-enabled and inbound diagnostics disabled.

Chapter 7 continued performance tuning while adding more physical inputs.

The latest browser tests were responsive, although long-term concurrent-load behavior has not been exhaustively established.

### 5.3 Saves and active state

The configuration engine validates schema, revision, filesystem writability, and persistence safeguards.

The active RAM configuration is authoritative.

A successful changed save publishes the validated configuration, rebuilds adapter selections, clears pending queue work, and resets volatile toggle histories.

Adapter lifecycle coordination must account for outstanding Roku held keys when configuration changes.

An unchanged save preserves pending work and toggle state.

A rejected save does not publish a replacement adapter cache.

See [Configuration](CONFIGURATION.md) for exact file rotation, recovery, and revision behavior.

The Pico filesystem does not automatically synchronize with GitHub. Protect browser-edited device configuration during firmware deployment.

---

## 6. The Dumb Queue™

**Module:** `clonker/actions.py`  
**Capacity:** 128 entries

Main interfaces include:

```python
dispatch(room_id, action_id, delay_seconds=0)
dispatch_hold(room_id, action_id, event, destination=None, command=None)
poll()
clear()
status()
```

> One queue. One poller. One shared execution path.

### 6.1 Admission and identity

Admission validates the room, action, delay, and capacity.

Fundamental actions use stable IDs; custom actions use room-specific saved IDs.

Ordinary tasks retain compact identity, step index, and due time rather than copied endpoint definitions.

The actual command is resolved from active configuration when executed.

A custom action occupies one queue entry, advancing one step at a time.

Immediate tasks use `due = 0`; delayed tasks use a `time.monotonic()` deadline.

### 6.2 Eligibility, ordering, and pacing

`poll()` scans for the first eligible task.

A future-dated custom step does not block an immediate action.

Among currently eligible tasks, queue order matters. This is not strict FIFO across delayed work.

A recognized Denon TCP volume command must satisfy the adapter's minimum 50 ms interval.

If the selected eligible command is waiting for pacing, it stays in its queue position and `poll()` returns without executing a later command.

This prevents overtaking.

Pacing uses monotonic time rather than sleeping inside the queue.

The action scheduler targets a 10 ms poll interval, with at most one queued command executed per poll.

### 6.3 Fundamental commands and toggle histories

Ordinary fundamental actions resolve the configured destination, method, and path.

Missing endpoints or blank paths produce logged no-ops.

`power-toggle` and `mute-toggle` select configured ON/OFF paths using independent volatile `(room_id, action_id)` direction histories, defaulting to ON.

History advances only after successful transmission.

Failures and no-ops do not advance it.

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

### 6.5 Physical-button hold events

Chapter 7 added a new queued task type:

```python
{
    "kind": "hold",
    "room": room_id,
    "action": action_id,
    "event": "pressed",  # or "released"
    "endpoint": endpoint,
    "method": method,
    "path": path,
    "due": 0,
}
```

This example illustrates the relevant fields; the implementation also retains its target information.

Supported fundamental actions are:

```text
nav-up
nav-down
nav-left
nav-right
skip-back
skip-forward
```

Unlike ordinary fundamental actions, hold tasks preserve their resolved endpoint and command at admission.

This is essential because a physical button may remain held while the user changes rooms.

The release must return to the original destination.

The queue processes these events through the existing execution loop.

There is no separate button-hold queue.

### 6.6 Failure policy and status

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

Ordinary adapter selection is based on recognized command signatures, not room names, manufacturer labels, or fixed device positions.

Explicit physical-button holds use a dedicated Roku execution path.

### 7.1 Supported execution paths

| Adapter / execution path | Selection | Transport |
|---|---|---|
| `denon-tcp` | Recognized Denon fundamental volume commands | Persistent TCP port 23 |
| `roku-hold` | Recognized Roku fundamental volume commands | ECP keydown/keyup |
| Roku physical-button hold | Explicit supported press/release event | ECP keydown/keyup |
| `generic-http` | Other configured commands | Bounded HTTP GET/POST |

Only fundamental `volume-up` and `volume-down` actions are eligible for cached specialized adapter selection.

Custom-action steps retain generic HTTP execution.

Physical-button holds bypass ordinary signature-based adapter selection and use `execute_hold()`.

### 7.2 Recognized Denon signatures

Method: GET

```text
/goform/formiPhoneAppDirect.xml?MVUP   -> MVUP
/goform/formiPhoneAppDirect.xml?MVDOWN -> MVDOWN
```

These signatures select `denon-tcp`.

The configured endpoint identifies the receiver host; the adapter uses native TCP port 23.

### 7.3 Recognized Roku volume signatures

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

### 7.4 Physical-button hold signatures

`device_adapters.execute_hold()` recognizes these Roku ECP paths:

```text
/keypress/Up    -> Up
/keypress/Down  -> Down
/keypress/Left  -> Left
/keypress/Right -> Right
/keypress/Rev   -> Rev
/keypress/Fwd   -> Fwd
```

The configured method must be POST.

A `pressed` event becomes Roku keydown.

A `released` event becomes Roku keyup.

Unsupported methods, paths, or empty endpoints raise execution errors.

These restrictions distinguish explicit physical holds from ordinary generic HTTP actions.

### 7.5 Adapter cache

Specialized fundamental-volume selections are cached by `(room_id, action_id)`.

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
| Maximum volume hold | 2 seconds | Bound continuous hold duration |
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

A volume hold is limited to approximately two seconds.

Continued rotation beyond that boundary releases the previous hold and can begin a new one.

This prevents one uninterrupted local hold from extending indefinitely.

The physical tests showed a new keydown after an extended series of local hold operations, consistent with maximum-hold restart behavior.

The precise keyup sequence was not independently traced during that experiment.

### 9.8 Failed-release safety

If a keyup request fails, the adapter retains the unresolved held-key state.

New keydowns must not proceed until the prior release has been resolved.

Retry attempts are paced at approximately 500 ms rather than occurring on every fast scheduler poll.

This is a specialized cleanup mechanism, not a general queue retry policy.

Network failure can still prevent confirmation that the remote received a release.

### 9.9 Lifecycle coordination

Held-key cleanup is relevant when:

- Rotation stops.
- Direction changes.
- Maximum hold is reached.
- Queued work is canceled.
- Configuration is replaced.
- Application shuts down.

Cleanup is best effort and remains subject to network availability.

### 9.10 Diagnostics

The Roku adapter wraps outbound HTTP failures with operation-specific context.

A diagnostic can identify keydown or keyup, direction, endpoint, and original exception.

Example:

```text
ROKU /keyup/VolumeUp -> 192.168.50.28:8060 failed: OSError(119,)
```

This is illustrative; actual exception formatting depends on CircuitPython and the failure path.

One transient `OSError(119)` occurred during early reversal testing before these diagnostics were added.

The precise failing operation was not established.

Subsequent tests recovered successfully.

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

## 10. Roku physical-button holds — Chapter 7

**Modules:** `controls/physical.py`, `actions.py`, `device_adapters.py`, `devices/roku.py`

Physical navigation and skip buttons require different behavior from the encoder's held-volume mechanism.

A button remains logically pressed for as long as the user holds it, subject to the safety limit.

### 10.1 Supported buttons

| Physical button | Fundamental action | Roku ECP key |
|---|---|---|
| Up | `nav-up` | `Up` |
| Down | `nav-down` | `Down` |
| Left | `nav-left` | `Left` |
| Right | `nav-right` | `Right` |
| Skip Back | `skip-back` | `Rev` |
| Skip Forward | `skip-forward` | `Fwd` |

These six buttons use explicit press/release events.

Other physical buttons continue using ordinary fundamental-action dispatch.

### 10.2 Press handling

When a supported button is pressed:

1. The button driver reports a debounced press.
2. `physical.py` determines the selected room.
3. The configured endpoint and action command are resolved.
4. The press context is retained in physical coordination state.
5. `actions.dispatch_hold()` admits the event.
6. The queue executes the event through `device_adapters.execute_hold()`.
7. The Roku module sends the appropriate ECP keydown.

Example:

```text
Physical NAV_UP pressed
    |
    v
actions.dispatch_hold(..., "pressed")
    |
    v
Dumb Queue
    |
    v
device_adapters.execute_hold()
    |
    v
POST /keydown/Up
```

The button driver itself does not send HTTP.

### 10.3 Release handling

On physical release:

1. The button driver reports a debounced release.
2. `physical.py` retrieves the saved press context.
3. The release is queued using the original endpoint and command.
4. The adapter sends the corresponding Roku ECP keyup.

Example:

```text
Physical NAV_UP released
    |
    v
Original room / endpoint / command
    |
    v
actions.dispatch_hold(..., "released")
    |
    v
Dumb Queue
    |
    v
POST /keyup/Up
```

The original context is important.

If the user changes the room selector while holding a button, the release must still go to the Roku that received the original keydown.

### 10.4 Why hold tasks preserve commands

Ordinary queued fundamental actions resolve their commands from active configuration when eligible.

Hold tasks are different.

They preserve:

- Room ID.
- Endpoint.
- Target.
- Method.
- Path.
- Press/release event.

This prevents a later room selection from redirecting the release.

It also avoids having the release depend on newly selected room state.

### 10.5 Hold safety

The physical-button hold mechanism has a maximum hold duration of approximately **30 seconds**.

The Roku module maintains this separately from the two-second encoder-volume hold.

The two mechanisms share the adapter and HTTP transport infrastructure but have distinct hold lifecycles.

Cancellation and shutdown attempt best-effort release cleanup.

A failed keyup may require later cleanup attempts, and complete recovery cannot be guaranteed if the Roku or network becomes unreachable.

### 10.6 Configuration requirements

The explicit physical-button hold adapter requires:

- A configured endpoint.
- POST method.
- One of the six recognized Roku ECP keypress paths.

Unsupported paths or blank endpoints are execution errors in the current hold path.

This matters for the current Room 3 placeholder, which contains blank device addresses and command paths.

Ordinary fundamental actions already support blank-command no-ops.

**The physical hold path still needs equivalent blank-command protection before Room 3 can be considered fully safe for all buttons.**

This is a genuine execution boundary, not merely a documentation distinction.

### 10.7 Verification

Chapter 7 testing exercised all six supported physical hold buttons.

The tests established:

- Debounced physical press detection.
- Queued hold admission.
- Roku keydown execution.
- Physical release detection.
- Roku keyup execution.
- Practical held-button behavior.

The tests do not establish guaranteed release after every possible network outage or application interruption.

---

## 11. Generic outbound HTTP transport

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

### 11.1 Generic HTTP remains necessary

Generic HTTP handles:

- Ordinary Roku navigation and ECP keypresses.
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

### 11.2 Why HTTP remains bounded and blocking

Earlier nonblocking TCP experiments on the tested CircuitPython platform encountered `OSError(119)` and lacked a usable `getsockopt(SO_ERROR)` inspection path.

Bounded blocking HTTP was selected for predictable behavior and simplicity.

This does not prove that nonblocking outbound networking is impossible.

Historical ordinary HTTP requests often took approximately 86–164 ms, with connection establishment contributing substantially.

A fresh HTTP connection for every volume detent made rapid physical rotation sluggish.

The specialized Denon and Roku volume adapters address this specific problem in different ways.

Any synchronous outbound socket operation temporarily pauses the cooperative scheduler, including GPIO and management HTTP polling.

The queue can buffer admitted actions. It cannot reconstruct electrical transitions that were never sampled.

---

## 12. Equipment mapping and observed behavior

The current development installation contains three configured rooms:

- `room-1` — Den.
- `room-2` — Sunroom.
- `room-3` — Room 3, blank placeholder.

Config v4 permits one to three rooms and three generic built-in destinations per room:

- `device-1`
- `device-2`
- `device-3`

Browser labels commonly read TV, AVR, and Streaming, but those labels do not enforce protocols.

### 12.1 Development installation endpoints

| Equipment | Installation-specific endpoint | Observation |
|---|---|---|
| Den AVR-X3700H | `192.168.50.44:8080` | Denon HTTP and persistent TCP volume |
| Den Roku Ultra | `192.168.50.43:8060` | Roku ECP commands |
| Sunroom AVR-X1800H | `192.168.50.40:8080` | Denon HTTP and earlier TCP volume |
| Sunroom Roku Ultra | `192.168.50.28:8060` | Roku ECP navigation, volume, and mute |

These addresses are records of the development installation, not defaults or configuration requirements.

### 12.2 Current mixed-volume configuration

| Room | Volume action configuration | Selected adapter |
|---|---|---|
| Den | Denon HTTP command signatures | `denon-tcp` |
| Sunroom | Roku ECP VolumeUp/VolumeDown signatures | `roku-hold` |

The Sunroom Roku controls the Denon receiver's volume through the equipment's HDMI-CEC path.

This demonstrates that adapter selection is based on configured command signatures rather than room identity.

### 12.3 Physical Power Toggle

GP2 Power Toggle successfully controlled Den and Sunroom ON/OFF through the selected room and shared queue.

Independent per-room toggle direction histories were observed.

Earlier Room 3 tests produced a safe no-op when the room was unconfigured.

The current Room 3 is configured but contains blank commands, a different condition.

These tests verified equipment behavior, not automatic equipment-state detection.

### 12.4 Physical volume

The Bourns PEC11R-4215F-S0024 encoder on GP8/GP9 generates generic volume actions through `physical.py`.

The Den room uses persistent Denon TCP.

The Sunroom uses Roku held-volume ECP.

The encoder remains a relative control; its shaft position does not encode an absolute volume value.

### 12.5 Physical push-to-mute

The Bourns encoder's separate momentary pushbutton is wired to GND and GP10.

The existing button driver maps `VOLUME_MUTE` to the generic `mute-toggle` fundamental action.

Observed results:

- Sunroom: Roku ECP `VolumeMute`, HTTP 200, receiver mute/unmute confirmed.
- Den: Denon HTTP mute commands, HTTP 200, receiver mute/unmute confirmed.

No separate mute execution system was required.

### 12.6 Physical navigation and playback

Chapter 7 added the navigation cluster, Back, Home, Select, and playback button integration.

Six buttons use explicit Roku held-key behavior:

- Up.
- Down.
- Left.
- Right.
- Skip Back.
- Skip Forward.

Their press and release events are delivered through the same action queue used by the existing physical and browser controls.

### 12.7 Custom-action equipment test

The Sunroom *Movie* action used:

1. Roku `POST /keypress/Home`.
2. A 3,000 ms wait after the first step completed.
3. Denon `GET /goform/formiPhoneAppDirect.xml?MSQUICK1`.

Both HTTP requests returned 200, and the queue logged custom completion.

An independent volume command was also observed executing during the custom wait in earlier tests.

---

## 13. Clock, logging, and performance diagnostics

### 13.1 Clock

**Modules:** `clonker/system/clock.py` and `clonker/system/logger.py`.

Before browser clock synchronization, firmware uses `DEFAULTTIME` and monotonic uptime rather than asserting an authoritative wall-clock date.

The browser can submit UTC Unix time through `/api/clock`.

Readable timestamps are calculated from that reference and subsequent monotonic elapsed time.

Queue deadlines, custom waits, Denon pacing, and Roku hold timing use monotonic time.

Browser clock changes must not shift these deadlines.

Automated NTP synchronization is not established by the current verified baseline.

### 13.2 Logging

Serial logging records action admission, execution, failures, room changes, and operating-mode transitions.

There is no persistent flash log or background logging server.

Keep routine logging modest. Continuous diagnostics can distort timing and browser responsiveness.

### 13.3 Shared PERF infrastructure

**Module:** `clonker/system/perf.py`.

Chapter 7 introduced a reusable performance measurement helper supporting:

- Registration of named measurements.
- Start/stop timing.
- Direct elapsed-time recording.
- Accumulated statistics and snapshots.
- Resetting measurements between reporting intervals.

The main scheduler registers and collects measurements for physical polling, queue activity, adapter activity, management HTTP, OLED polling, and overall loop execution.

The current scheduler-level diagnostic configuration in `main.py` includes:

```python
PERF_ENABLED = True
PERF_INTERVAL_NS = 30_000_000_000
GC_TEST_ENABLED = False
```

PERF reports are generated approximately every 30 seconds.

The reports include physical polling-gap statistics, execution-duration measurements, and contextual information such as memory availability and OLED refresh activity.

The instrumentation is operational and intended for continued targeted extension.

### 13.4 Physical internal diagnostics

`controls/physical.py` provides optional internal instrumentation.

The current baseline is:

```python
PHYSICAL_PERF_ENABLED = False

PERF_SCAN = False
PERF_EVENTS = False
PERF_VOLUME = False
PERF_DISPATCH = False
PERF_HOLD = False
```

The master flag controls whether internal physical instrumentation is active. Individual flags allow more focused measurements.

Disabling internal physical instrumentation does not disable scheduler-level timing of `physical.poll()`.

Use focused measurements rather than enabling every diagnostic indiscriminately.

### 13.5 Interpreting performance measurements

Three distinct concepts must not be conflated:

1. **Physical polling gap:** Time between opportunities to poll physical controls.
2. **Physical execution duration:** Time spent executing `physical.poll()`.
3. **Network execution duration:** Time consumed by a blocking transport or adapter operation.

A long network request can delay the next physical poll without necessarily increasing the measured execution duration of `physical.poll()` itself.

Chapter 7 observed occasional physical execution spikes around 40–50 ms during sustained volume activity, even after disabling detailed internal instrumentation.

Blocking Roku HTTP operations also produced substantially longer cooperative scheduler gaps.

The source of the physical execution spikes remains unresolved.

### 13.6 Garbage-collection experiment

An explicit garbage-collection diagnostic was tested during Chapter 7.

`main.py` retains the optional `GC_TEST_ENABLED` switch, currently disabled.

The experiment did not conclusively explain the physical execution spikes.

Do not repeat it without identifying what additional evidence a new experiment would provide.

See [Development History](DEVELOPMENT_HISTORY.md) for the recorded investigation.

---

## 14. Verification record and evidence limits

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

Den and Sunroom Power Toggle ON/OFF passed.

At that time, Room 3 was unconfigured and rejected before queue admission.

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

### November 4–7 — Chapter 7 physical integration

Chapter 7 expanded the GPIO subsystem to include the navigation cluster, playback buttons, and second Bourns encoder wiring.

The physical mapping table associates button identities with the existing fundamental action vocabulary.

The six navigation/skip buttons gained explicit press/release handling.

The Roku adapter gained physical-button hold operations, separate from encoder-driven volume holds.

Physical tests exercised all six held buttons.

A defective Skip Back tactile switch was replaced during hardware verification.

### November 4–7 — browser responsiveness

Additional Config Mode tests examined scheduler competition, diagnostics, and HTTP responsiveness.

After adjustments, Safari and Chrome were both observed loading the Config page and Test Remote responsively.

This supports the current practical behavior, not a guarantee under all network conditions.

### November 7 — Room 3 configuration

The development configuration was extended to include `room-3` with blank device addresses and command paths.

The physical selector initially failed to log Room 3 selection.

Inspection identified a GP7 wire that had pulled out of the Cowbell terminal.

Reseating the wire restored selector operation.

The problem was physical connectivity, not the selector's software mapping.

### November 7–8 — Custom-action encoder and OLED integration

The second Bourns encoder was integrated into the physical coordinator.

Rotation cycles through the currently selected room's ordered custom actions, wrapping around the available entries. Pressing the encoder executes the selected action through the existing dispatcher.

Room changes reset the selection. Empty custom-action lists are handled without attempting execution.

The OLED integration introduced `display/oled.py`, implementing a 128×64 SH1106 display over I²C on GP4/GP5.

The display uses deferred text requests, rate-limited polling, partial updates, and idle display-off. The custom-action selector displays the selected action name or `No customs`.

The initial encoder and OLED implementations are operational. Further user-interface integration remains planned.

### November 8 — Shared performance instrumentation

Performance measurement was consolidated into `system/perf.py`, replacing much of the earlier ad hoc timing bookkeeping.

Scheduler-level measurements now cover physical polling gaps, physical execution, queue execution, adapter execution, management HTTP activity, OLED polling, and main-loop execution.

Optional internal measurements in `controls/physical.py` support more focused investigations.

During sustained volume testing, occasional physical execution spikes around 40–50 ms remained unresolved. Blocking Roku operations also produced longer scheduler gaps, but these represent different timing measurements.

The investigation included instrumentation-overhead changes, logging changes, and an explicit garbage-collection experiment. None conclusively isolated the physical execution spikes.

Detailed results, unsuccessful experiments, and the Chapter 8 diagnostic handoff are preserved in [Development History](DEVELOPMENT_HISTORY.md).

---

## 15. Operational limitations and next investigations

### Physical controls

The Chapter 7 physical assembly is complete: controls are mounted, soldered, wired, secured, strain-relieved, and connected through the Pico Cowbell Terminal board.

Power Toggle, room selection, volume, mute, navigation, playback, and both Bourns rotary encoders are integrated.

The custom-action encoder supports room-specific selection, OLED display of the selected action, and push-to-run execution. Its initial implementation is largely complete.

All six Roku physical-button holds have been exercised on real equipment.

The SH1106 OLED has completed initial application integration. Additional status and feedback uses remain future work.

PERF instrumentation is operational and continues to be extended for targeted investigations.

Audible feedback, rechargeable battery operation, and sleep/wake behavior remain future development.

### Denon TCP

The adapter maintains one persistent receiver socket.

There is no response parser, state polling, or automatic retry of uncertain sends.

### Roku held-volume

The adapter is time-based rather than detent-count-based.

Behavior depends on HTTP responsiveness, Roku repeat behavior, and potentially HDMI-CEC.

Slight display lag and volume overshoot have been observed.

One transient `OSError(119)` occurred during early reversal testing. Later tests recovered and completed without additional visible errors.

The maximum-hold release sequence was inferred from behavior and logs rather than independently traced.

### Roku physical-button holds

The six recognized Roku hold paths require valid endpoints, POST methods, and recognized ECP paths.

The 30-second safety limit reduces the risk of an indefinitely held physical key.

Network failures can still prevent guaranteed key release.

### Generic HTTP

The transport is bounded but synchronous, with a fresh TCP connection per request.

It does not implement TLS, application authentication, or full response-body parsing.

### Input capture

The 1 ms physical poll target helps responsiveness, but blocking network operations can still hide encoder transitions.

### Queue

One execution failure cancels remaining queued work.

There is no general retry or rollback mechanism.

### Room 3

The third selector position and configured Room 3 placeholder are operational.

Ordinary blank fundamental commands produce no-ops.

The explicit physical hold path still needs blank-command protection to avoid execution errors when Room 3 is selected.

No fallback to another room should occur.

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

- Isolate the occasional 40–50 ms `physical.exec` spikes observed during sustained volume activity.
- Distinguish delays occurring inside `physical.poll()` from cooperative scheduler gaps caused by blocking network operations.
- Extend targeted PERF measurements only when they can answer a specific diagnostic question.
- Stale Denon TCP connections after AVR restart.
- Switching receivers during bursts.
- Network interruption during Roku keydown or keyup.
- Physical-button release after room changes and failures.
- Blank-command safety for physical held buttons in Room 3.
- Roku held-volume under simultaneous CONFIG-mode browser activity.
- High-rate encoder capture during other HTTP operations.
- Queue pressure and malformed responses.
- Long-uptime operation and repeated reconnects.
- Additional OLED feedback integration and display-performance testing.

Future physical features should reuse the existing encoder/button drivers, physical coordinator, adapter selection, and shared queue.

Do not introduce speculative protocol modules or a second action execution path merely because it is possible.

**The Dumb Queue™ buffers traffic. It does not repeal the laws of TCP.**

---

## 16. Related documents

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
