# The Clonker 10000 — System Architecture

**Design reference:** Updated November 3, 2026  
**Active platform:** Raspberry Pi Pico 2 W / CircuitPython 10.3.1  
**Repository:** [djacobson/clonker-10000](https://github.com/djacobson/clonker-10000)  
**Current milestone:** Chapter 6 — physical volume control and Denon TCP device adapter operational  
**Configuration:** Clonker Config v4

> **Clonker controls actions, not brands. Controlled devices own their own state.**

---

## 1. Mission and principles

The Clonker 10000 is a tactile, Wi-Fi-first home-theater remote: substantial knobs, satisfying switches, guarded controls, and eventually an audible **CLONK!**

It turns a user intention into a configured command without pretending to be a home-automation server or an authoritative equipment-state tracker.

The operational command path is:

1. Detect a physical input or browser action request.
2. Determine the target room.
3. Resolve the generic fundamental or custom action ID.
4. Validate and admit the action to the shared Dumb Queue™.
5. Execute eligible work using the active configuration.
6. Send the appropriate network command.
7. Record the transmission result without confusing network success with actual equipment state.

**Be resilient in our dumbness.** Favor predictable, recoverable, measurable behavior over unnecessary abstraction.

**One queue. One poller. One shared execution path.**

Both browser and physical actions now use the same dispatcher and execution machinery.

The remote is not a universal protocol engine, equipment-state authority, or general-purpose automation server.

It is a purpose-built command controller.

---

## 2. Architecture at a glance

```text
                  THE CLONKER 10000

       BROWSER TEST REMOTE       PHYSICAL CONTROLS
                |                 Buttons / Encoders
                |                 Room Selector
                |                       |
                |                  physical.py
                |                 Event -> Action
                |                 Selected Room
                |                       |
                |              Room configured?
                |                 /         \
                |               YES         NO
                |                |           |
                |                |         NO-OP
                |                |
                +--------+-------+
                         |
                         v
                  actions.dispatch()
                   Validate / Admit
                         |
                         v
                    DUMB QUEUE™
                Fundamental / Custom
                         |
                         v
                    actions.poll()
                  First eligible task
                         |
                         v
                  ACTIVE CONFIGURATION
                    Clonker Config v4
                         |
                         v
                   COMMAND RESOLUTION
              Ordinary / Toggle / Custom
                         |
                         v
                 ADAPTER SELECTION
                Cached for fundamental
                         |
                +--------+--------+
                |                 |
                v                 v
           Generic HTTP       Denon TCP
             Transport         Adapter
                |                 |
                v                 v
           Roku / Denon        Denon AVR
           HTTP commands       Volume


          CONFIG MANAGEMENT (CONFIG MODE ONLY)

             Browser editor / Port 9090
                         |
                         v
               Validate + Revision Check
                         |
                         v
              Verified Filesystem Write
                         |
                         v
               Publish Active RAM Config
               Rebuild Adapter Cache
               Clear Queue on Changed Save
               Reset Toggle Histories
```

Both input paths converge on the same action dispatcher and Dumb Queue™.

Physical controls generate generic actions using the selected room. The browser Test Remote supplies its own room selection.

The queue resolves configured commands when they become eligible for execution.

Recognized fundamental Denon volume commands use the specialized TCP adapter. Other fundamental commands and all current custom-action steps use generic HTTP.

Adapter selection is derived from command signatures, not room names, device names, or fixed destination positions.

The selection cache is rebuilt when configuration becomes active. It is not stored in the JSON schema.

The Denon adapter maintains a persistent TCP connection, provides pacing eligibility, and sends native volume commands.

The generic queue remains responsible for command ordering, delays, and cancellation. No device adapter owns a separate action queue.

### 2.1 Architectural invariants

- Physical controls express generic actions, never equipment-specific command paths.
- Configuration owns device destinations and command definitions.
- `selectors.py` owns physical room-selection state.
- `physical.py` owns physical-event routing and action mapping.
- `actions.py` owns admission, queueing, eligibility, sequencing, cancellation, and execution.
- `device_adapters.py` owns command-signature recognition and cached adapter selection.
- Device adapters own protocol-specific connection and transmission behavior.
- Generic HTTP remains the fallback for unrecognized commands.
- Browser and physical controls share the same action dispatcher.
- The active validated RAM configuration is authoritative at runtime.
- Changed configuration saves clear pending work and reset volatile toggle histories.
- External devices own actual power, input, playback, and volume state.
- Optional physical hardware must not prevent the core application from operating.

**No duplicate command pipelines. No second queue. No manufacturer-specific networking logic in GPIO drivers.**

---

## 3. Verified implementation boundary — November 3, 2026

### 3.1 Operational and exercised

The following capabilities have been implemented and exercised on the Pico, through the browser, or against actual equipment.

**Core firmware**

- Raspberry Pi Pico 2 W running CircuitPython 10.3.1.
- Wi-Fi networking and serial diagnostics.
- Cooperative application scheduler.
- Clonker Config v4 validation, revision protection, persistence, and recovery.
- Browser configuration editor and Test Remote.
- Fourteen fundamental action IDs.
- Room-specific named custom actions.
- Shared Dumb Queue™.
- Real Denon and Roku HTTP GET/POST execution.
- Independent volatile power/mute toggle histories.
- Cooperative custom-action waits with interleaved independent commands.

**Device adapter architecture**

- Fundamental-command signature recognition without relying on manufacturer names or fixed device slots.
- Generic HTTP fallback for unrecognized commands.
- In-memory adapter selections rebuilt when configuration becomes active.
- Cache replacement after successful saves, including stale-revision protection.
- Persistent Denon TCP transport for recognized volume-up and volume-down commands.
- Native Denon `MVUP` and `MVDOWN` transmission.
- Nonblocking 50 ms command pacing.
- TCP connection reuse and receiver switching.
- No automatic retries after uncertain transmission failures.

**Operating modes**

- GP17 SERVICE (USB)/DEVICE maintained boot switch.
- GP18 CONFIG/RUN maintained switch.
- Live CONFIG/RUN transitions without rebooting.
- Management HTTP enabled only in CONFIG mode.
- Action queue operational independently of management-listener state.

**Physical controls**

- GP2 momentary Power Toggle button.
- Reusable debounced button driver.
- Three-position room selector on GP3, GP6, and GP7.
- Debounced room-selection state.
- Reusable Bourns rotary encoder driver.
- Physical volume encoder on GP8/GP9.
- Shared physical-event-to-action mapping.
- Shared `dispatch_selected()` helper.
- Room-aware physical Power Toggle and volume execution.
- Safe no-op when selecting an unconfigured room.

**Equipment and integration verification**

| Test | Observed result |
|---|---|
| Den Power ON/OFF | PASS |
| Sunroom Power ON/OFF | PASS |
| Reserved Room 3 | PASS — harmless no-op |
| Denon TCP volume commands | PASS |
| Five volume commands UP/DOWN | PASS — returned to starting level |
| Slow physical encoder rotation | PASS |
| Moderate physical encoder rotation | PASS |
| Aggressive encoder rotation | PASS — smooth observed response |
| Mixed HTTP/TCP queue ordering | PASS |
| Denon pacing preserves queue order | PASS |
| Future-dated task scheduling | PASS |
| Delayed custom-action interleaving | PASS |
| Failure cancellation | PASS |
| Adapter cache save/reload lifecycle | PASS |

The receiver's actual volume behavior was observed during physical testing, providing stronger evidence than successful socket writes alone.

### 3.2 Not yet integrated or not exhaustively verified

- Physical navigation, Home, Back, and additional action buttons.
- Volume encoder push-to-mute.
- Second encoder for custom-action selection and execution.
- OLED display and audible CLONK feedback.
- Battery operation, sleep, and wake behavior.
- Final enclosure assembly.
- User-defined custom destinations beyond built-in slots.
- Apple TV discovery, pairing, authentication, and command transport.
- Additional device adapters and configurable adapter overrides.
- Denon TCP response parsing and unsolicited-status handling.
- Comprehensive network-disconnect and receiver-restart recovery.
- Exhaustive malformed-request, power-loss, and long-duration stress testing.

A detected physical event is not necessarily an admitted action.

An admitted action is not necessarily a transmitted network command.

A successful HTTP response or TCP socket write is not authoritative proof of equipment state.

The November 3 physical volume tests provide additional evidence because actual receiver behavior was observed.

---

## 4. Firmware component ownership

| Component | Responsibility |
|---|---|
| `firmware/boot.py` | GP17 boot-time filesystem ownership |
| `firmware/code.py` | CircuitPython application entry point |
| `firmware/clonker/main.py` | Startup, operating-mode transitions, cooperative scheduler |
| `firmware/clonker/device_config_v2.py` | Config v4 validation, RAM state, revisions, persistence, recovery |
| `firmware/clonker/device_config.json` | Device configuration when deployed |
| `firmware/clonker/actions.py` | Fundamental/custom dispatch, Dumb Queue™, execution, cancellation |
| `firmware/clonker/device_adapters.py` | Fundamental-command signature recognition and cached adapter selection |
| `firmware/clonker/devices/denon.py` | Persistent Denon TCP connection, native volume commands, pacing |
| `firmware/clonker/net/http_transport.py` | Bounded synchronous outbound HTTP |
| `firmware/clonker/net/web.py` | CONFIG-mode management HTTP and APIs |
| `firmware/clonker/www/index.html` | Browser configuration editor |
| `firmware/clonker/www/remote.html` | Browser Test Remote |
| `firmware/clonker/controls/pins.py` | Developer-maintained GPIO assignments |
| `firmware/clonker/controls/buttons.py` | Reusable debounced momentary button class |
| `firmware/clonker/controls/encoders.py` | Reusable rotary quadrature encoder driver |
| `firmware/clonker/controls/switches.py` | CONFIG/RUN state, physical input, simulation, override |
| `firmware/clonker/controls/selectors.py` | Physical room selector and selected-room state |
| `firmware/clonker/controls/physical.py` | Hardware initialization, polling, event mapping, dispatch bridge |
| `firmware/clonker/system/clock.py` | UTC reference and monotonic-based timestamps |
| `firmware/clonker/system/logger.py` | Serial diagnostics |
| `firmware/clonker/legacy/` | Historical XML implementation |

The filename `device_config_v2.py` is historical. The active configuration schema uses `CONFIG_VERSION = 4`.

Avoid cosmetic renames that risk disrupting a working deployment.

### 4.1 Separation of concerns

**Hardware drivers** detect electrical events.

**Physical coordination** maps those events to generic action IDs.

**Room selection** provides the current physical room context.

**Configuration** defines destinations and command behavior.

**Action dispatch** validates and queues requested work.

**Adapter selection** recognizes supported fundamental-command signatures and caches the selected transport behavior.

**Device adapters** implement manufacturer-specific communication when necessary.

**Generic HTTP transport** handles commands without specialized adapters.

This separation lets the same fundamental action originate from a browser, pushbutton, or rotary encoder without duplicating network logic.

A device adapter does not create another action queue or independently decide which user action to execute.

### 4.2 Physical event routing

`physical.py` contains a mapping from physical button names to fundamental action IDs.

Examples:

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

When a button generates a stable `"pressed"` event, `physical.py` looks up the corresponding action ID and calls the shared `dispatch_selected()` helper.

Release events are logged but do not dispatch actions.

The helper obtains the selected room, checks whether that room exists in the active configuration, and invokes `actions.dispatch()`.

Unconfigured rooms are rejected before queue admission.

Dispatch exceptions are logged without terminating the physical-control poller.

The mapping is deliberately independent of equipment models and network addresses.

### 4.3 Hardware-specific versus application-specific logic

The room selector is implemented as a small, purpose-specific state module. It owns selected-room state and debounce behavior.

The reusable `Encoder` class in `controls/encoders.py` interprets rotary quadrature transitions without knowing their application meaning.

`physical.py` assigns meaning to encoder movements. The volume encoder generates generic `volume-up` and `volume-down` actions for the selected room.

The second Bourns encoder is planned for custom-action selection and execution. It can reuse the encoder driver while maintaining its own application-specific selection state.

Neither encoder hardware nor physical coordination contains Denon, Roku, or other manufacturer-specific networking logic.

**Reusable hardware mechanisms; simple application-specific state.**

---

## 5. Two independent operating-mode dimensions

### 5.1 GP17: SERVICE (USB) / DEVICE

| Switch | Electrical state | Mode | Filesystem write owner |
|---|---|---|---|
| OFF | Open / pulled HIGH | SERVICE (USB) | USB host |
| ON | Grounded / LOW | DEVICE | Pico firmware |

`boot.py` selects filesystem ownership before the application starts.

**A full power cycle is required** to change ownership. Ctrl+D is not equivalent.

Browser inspection can work in SERVICE + CONFIG, but configuration saves are rejected when the Pico filesystem is read-only.

### 5.2 GP18: CONFIG / RUN

| Switch | Electrical state | Application mode | Management HTTP |
|---|---|---|---|
| OFF | Open / pulled HIGH | RUN | Stopped |
| ON | Grounded / LOW | CONFIG | Enabled, port 9090 |

`switches.py` reads GP18 using an internal pull-up.

The application starts or stops the management listener as the switch changes, without rebooting.

A simulated source and explicit software override remain available for development.

An open circuit is not proof that a switch is physically present.

The queue continues to be polled in both modes.

**DEVICE + RUN** is the intended ordinary remote combination.

**DEVICE + CONFIG** permits persistent browser configuration edits.

Neither operating-mode switch is an equipment power command or a room selector.

See [Operating Modes](OPERATING_MODES.md) for procedures.

---

## 6. Configuration architecture

The active schema is **Clonker Config v4**, stored as JSON.

Each room has:

- A stable room ID.
- A display name.
- Three built-in device slots.
- Fourteen fundamental actions.
- Optional named custom actions.

The current configuration contains two operational rooms: **Den** and **Sunroom**.

The physical selector has a third position reserved for future room expansion.

### 6.1 Generic built-in destinations

| Stable ID | Default browser label |
|---|---|
| `device-1` | TV |
| `device-2` | AVR |
| `device-3` | Streaming |

Labels do not enforce device types.

Configured endpoints and action mappings determine actual behavior.

The browser editor is a client of the validated configuration engine, not an alternative source of truth.

### 6.2 RAM snapshot, revisions, adapter cache, and recovery

Startup loads and validates the active file at:

`/clonker/device_config.json`

Runtime dispatch resolves definitions from the in-memory configuration rather than rereading JSON for each action.

The browser receives revision and filesystem-writability metadata.

Saves validate the submitted schema and expected revision, protect against stale tabs, verify temporary writes, and manage backups.

**Adapter selection is derived from the active validated configuration.**

`device_adapters.py` recognizes supported fundamental-command signatures and builds an in-memory map keyed by `(room_id, action_id)`.

Only specialized selections are stored. Missing entries use the generic HTTP adapter.

The adapter cache:

- Is rebuilt when a configuration is successfully loaded.
- Is rebuilt after a successful changed configuration save.
- Is not persisted to JSON.
- Does not depend on room names or manufacturer labels.
- Remains unchanged when a save is rejected.

The cache is constructed before its replacement is published, avoiding partially rebuilt selections.

The current specialized recognition is limited to fundamental Denon volume-up and volume-down commands using known HTTP command signatures.

Custom-action steps continue to use generic HTTP.

On a successful **changed** save, the management layer clears pending actions and resets volatile toggle histories.

An unchanged save preserves existing queue and toggle state.

Backup rotation reduces risk but does not guarantee recovery from every interrupted write or power-loss scenario.

The Pico filesystem does not automatically synchronize with GitHub.

See [Configuration & Recovery](CONFIGURATION.md).

---

## 7. Fundamental actions and toggles

Each configured room defines fourteen stable fundamental action IDs.

Ordinary actions resolve a destination, HTTP method, and command path.

Missing ordinary endpoints or blank paths produce intentional logged no-ops.

`power-toggle` and `mute-toggle` use configured ON/OFF paths and independent volatile direction histories for each room and action.

An unknown history begins with ON.

History advances only after successful command transmission through the selected transport.

For current power and mute toggles, this means successful HTTP execution.

Failures and no-ops do not advance the history.

A reboot resets the histories.

A changed configuration save also resets them.

This is **last-successful-command direction**, not equipment-state discovery.

HDMI-CEC, other remotes, and device applications may change equipment state without Clonker knowing.

### 7.1 Physical Power Toggle verification

The GP2 physical button now dispatches the existing `power-toggle` fundamental action.

It does not implement separate power-control behavior.

The physical selector supplies the room ID, and the existing action system handles the command.

November 2 testing verified:

- Room 1 ON and OFF.
- Room 2 ON and OFF.
- Independent toggle direction histories.
- Room 3 no-op without command execution.

This is the first completed physical hardware-to-equipment action path.

---

## 8. The Dumb Queue™

**One queue. One poller. One shared execution path.**

`actions.py` owns admission and execution of fundamental and custom actions, regardless of input source.

### 8.1 Admission and representation

`actions.dispatch(room_id, action_id, delay_seconds=0)` validates room, action, delay, and capacity before queue admission.

The queue holds up to **128 entries**.

Tasks carry identifiers and scheduling metadata rather than copies of endpoint definitions.

A compound custom action occupies **one queue entry**, not one entry per step.

### 8.2 Eligibility, ordering, and pacing

The poller scans for the **first eligible** task.

Immediate work can bypass a future-dated task.

Among currently eligible tasks, queue order matters.

This is not strict FIFO across delayed work.

Due times use `time.monotonic()`.

For a recognized Denon TCP volume command, the queue checks adapter pacing eligibility before executing the command.

If the adapter's minimum transmission interval has not elapsed, the eligible task remains in its original queue position and `actions.poll()` returns without executing another command.

This prevents later eligible commands from overtaking a volume command that is waiting for its 50 ms pacing interval.

A future-dated custom-action step remains different: it is not yet eligible, so an unrelated immediate command can execute while that step waits.

Pacing does not use `time.sleep()` inside the action queue.

The queue still executes at most one eligible command per poll.

> **A future task must not hold an immediate button press hostage. A paced eligible task must not be overtaken.**

### 8.3 Compound custom actions

A custom action has a stable ID, name, and one to sixteen ordered steps.

Config v4 supports up to sixteen custom actions per room.

Each step resolves a built-in destination, HTTP method, command path, and `wait_after_ms`.

One eligible `actions.poll()` executes at most one outbound command.

After a successful step, the task is requeued with a due time calculated after that request completes.

Independent eligible actions can execute during the wait.

There is no separate macro thread, nested scripting system, branching engine, or rollback mechanism.

### 8.4 Failure and consistency policy

One execution failure clears the remaining queue, including unfinished compound work.

The dispatcher remains available for new requests.

There are no automatic retries.

A successful changed configuration save clears pending tasks so they cannot silently execute under a new mapping.

A physical action aimed at an unconfigured room is rejected by `dispatch_selected()` before entering the queue.

This prevents the reserved Room 3 position from causing a dispatch error or disrupting existing queued work.

Queue admission is not network completion.

Network completion is not equipment-state verification.

---


## 9. Cooperative scheduler and network execution

`main.py` currently uses:

| Service | Poll interval |
|---|---:|
| Physical controls | 1 ms |
| Action queue | 10 ms |
| CONFIG management HTTP | 1 ms |
| Main-loop yield | 1 ms |

These are target service intervals, **not hard real-time guarantees**.

The main loop performs work cooperatively.

Its order is:

1. Physical-control polling.
2. One eligible action-queue operation.
3. CONFIG/RUN mode evaluation and listener management.
4. CONFIG-mode HTTP servicing.
5. Brief runtime yield.

The queue continues operating in both CONFIG and RUN modes.

### 9.1 Current physical polling design

`main.py` invokes `physical.poll()` at the configured physical polling interval.

Within that call:

1. The room selector is polled.
2. A changed room selection is logged.
3. Each initialized button is polled.
4. Stable press/release events are logged.
5. Mapped button presses are dispatched.
6. The volume encoder is polled and completed movements are dispatched as generic volume actions.

The selector uses a **50 ms software debounce**.

Buttons use their reusable `Button` class debounce, currently 30 ms by default.

The encoder driver interprets quadrature transitions and reports completed movement.

These controls share the physical polling schedule, currently targeting 1 ms.

Debouncing and encoder interpretation do not require blocking sleeps.

### 9.2 Encoder polling and volume-command pacing

The current firmware uses a **1 ms target physical polling interval**.

This is a cooperative scheduling target, not a hardware interrupt or hard real-time guarantee.

The physical volume encoder produces quadrature transitions. The physical coordinator interprets those transitions and dispatches one generic volume action for each recognized movement.

Network execution occurs separately through the Dumb Queue™.

The earlier HTTP-only volume path required a new connection for each command. Those blocking requests interfered with timely encoder polling and made volume control feel sluggish.

Chapter 6 introduced a specialized Denon TCP adapter for recognized fundamental volume commands.

The adapter:

- Maintains one persistent receiver connection.
- Reuses the connection for consecutive commands to the same receiver.
- Closes the previous connection when switching receivers.
- Translates recognized Denon HTTP volume command signatures into native `MVUP` and `MVDOWN` commands.
- Enforces a 50 ms minimum interval between transmissions.
- Reports pacing eligibility without sleeping inside the queue.
- Does not retry commands automatically after uncertain transmission failures.

When the first eligible queue command is a Denon volume command awaiting its pacing interval, `actions.poll()` leaves it queued and returns.

Later commands cannot overtake that eligible command.

Future-dated tasks remain independently scheduled and do not block otherwise eligible immediate work.

TCP connection establishment and socket writes are still synchronous operations. Persistent connection reuse reduces repeated connection overhead; it does not make the entire networking system asynchronous.

The physical encoder was exercised at slow, moderate, and aggressive rotation rates. Observed receiver behavior was responsive and smooth.

No encoder-event batching, artificial acceleration, or separate high-speed command queue is currently implemented or required.

Further testing should address prolonged operation, receiver restarts, network disconnections, and recovery after a stale TCP connection.

### 9.3 Inbound versus outbound network behavior

The inbound management service is a cooperative, nonblocking, single-active-client listener on port 9090.

It services accept, receive, and send work incrementally.

It is available only in CONFIG mode.

Outbound HTTP is **bounded but blocking**.

Each GET/POST uses a fresh TCP socket, with response status inspection and HTTP 2xx acceptance.

A blocking socket operation temporarily pauses browser servicing, queue polling, and physical-input polling.

A queue can buffer admitted work.

It cannot recover GPIO transitions the scheduler never observed.

### 9.4 October 28 browser pacing investigation

The CONFIG page intermittently loaded slowly or incompletely.

Disabling GPIO polling did not eliminate the problem.

HTTP diagnostics showed response transmissions sometimes timing out partway through large pages.

Because the inbound server sends bounded chunks, a 10 ms interval between web polls could introduce substantial delay.

Changing `WEB_POLL_INTERVAL` from `0.01` to `0.001` substantially improved observed Chrome and Safari page loading.

Repeated browser tests succeeded with physical polling re-enabled and diagnostics disabled.

The precise reason the issue surfaced at that development stage remains unproven.

The 1 ms interval is a tested baseline, not a proven optimum.

See [Firmware, HTTP & Clock](FIRMWARE_NETWORK.md).

---

## 10. Browser and management interface

The CONFIG-mode service provides the configuration editor, Test Remote, clock API, and action submission.

| Route | Responsibility |
|---|---|
| `GET /` | Browser configuration editor |
| `GET /remote.html` | Browser Test Remote |
| `GET /api/config` | Validated configuration and revision metadata |
| `POST /api/config` | Revision-protected validated save |
| `GET /api/clock` | Clock source and timestamp |
| `POST /api/clock?utc=...` | Browser UTC reference update |
| `POST /api/action?room=...&action=...` | Admit fundamental or saved custom action |

An accepted action API request acknowledges queue admission only.

The browser Test Remote and physical controls use the same action dispatcher and queue.

The browser's room selection remains independent of the physical room selector.

The management API has **no application-level authentication**.

Keep it on a trusted LAN. Do not expose port 9090 to the public internet.

---

## 11. Physical controls — Chapter 6

### 11.1 Verified GPIO assignments

| GPIO | Physical control | Current status |
|---|---|---|
| GP2 | Momentary Power Toggle | Operational, live action dispatch |
| GP3 | Room selector LEFT | Operational — Room 1 |
| GP4/GP5 | STEMMA QT / I²C | Reserved for future OLED and I²C devices |
| GP6 | Room selector MIDDLE | Operational — Room 2 |
| GP7 | Room selector RIGHT | Operational — Room 3 |
| GP17 | SERVICE/DEVICE boot switch | Operational |
| GP18 | CONFIG/RUN switch | Operational |

All listed selector and button inputs use active-low wiring with internal pull-ups.

The three-position selector connects exactly one of GP3, GP6, or GP7 to common ground.

The current hardware uses the Adafruit Pico Cowbell Terminal board for screw-terminal GPIO connections.

The WAGO ground bus provides a shared ground reference.

On November 2, 2026, the room selector was reassigned from GP3/GP4/GP5 to GP3/GP6/GP7 and successfully retested. This preserves GP4/GP5 for the Cowbell's STEMMA QT/I²C connector.

Other physical-control GPIO assignments remain pending.

### 11.2 Room selector

`controls/selectors.py` owns the physical room-selection state.

The hardware mapping is:

| Mechanical position | GPIO grounded | Selected room |
|---|---|---|
| LEFT | GP3 | `room-1` |
| MIDDLE | GP6 | `room-2` |
| RIGHT | GP7 | `room-3` |

At initialization, the selector captures its current physical position.

During polling, it reads all three GPIO inputs.

A valid reading requires **exactly one grounded input**.

Readings with zero or multiple grounded inputs are considered invalid or transitional.

Such readings do not replace the last valid selection.

A valid changed position must remain stable for 50 ms before being accepted.

The module exposes:

```python
selectors.initialize()
selectors.selected_room()
selectors.poll()
selectors.deinit()
```

`selected_room()` returns the last valid stable room ID, or `None` if no valid selection has been established.

`poll()` returns a new room ID only when a stable selection change occurs.

The selector does not send network commands.

It does not know whether a room is configured.

It maintains physical room-selection state only.

### 11.3 Room 3 — reserved behavior

The third physical position is intentionally reserved for future room expansion.

The current configuration contains only Rooms 1 and 2.

When Room 3 is selected, `physical.dispatch_selected()` checks the active configuration and declines to dispatch room-specific actions.

Expected diagnostic:

```text
PHYSICAL NO-OP: room-3 / power-toggle (room unavailable)
```

No action is queued.

No HTTP command is sent.

The other rooms' toggle histories remain unchanged.

There is no silent fallback to Room 1.

This is deliberate: a physical selector pointing at Room 3 must not unexpectedly control the Den.

When Room 3 becomes a configured room in the future, the selector hardware and state representation can remain unchanged.

### 11.4 Momentary buttons

`controls/buttons.py` provides a reusable `Button` class.

Each button uses an internal pull-up and nonblocking debounce.

A grounded input represents a press.

The driver reports stable `"pressed"` and `"released"` events.

`physical.py` initializes only buttons whose GPIO assignments are present in `pins.py`.

Unassigned optional buttons are skipped.

Individual initialization failures are logged rather than preventing the entire application from starting.

Only stable press events trigger mapped actions.

Release events are diagnostic.

### 11.5 Shared physical action dispatch

The central helper is:

```python
physical.dispatch_selected(action_id)
```

It:

1. Obtains the selected room from `selectors.py`.
2. Checks that the room exists in the active configuration.
3. Logs and returns without dispatching if the room is unavailable.
4. Calls `actions.dispatch(room_id, action_id)` for configured rooms.
5. Logs dispatch exceptions without terminating the physical poller.

This helper is shared by ordinary buttons and the operational volume encoder, and is intended for additional physical controls.

The physical event mapping lives in `physical.py`, not `actions.py`.

`actions.py` remains independent of hardware input types.

### 11.6 Physical Power Toggle

The GP2 momentary button is named `POWER_TOGGLE`.

Its mapping is:

```python
"POWER_TOGGLE": "power-toggle"
```

The physical event passes through the same dispatcher used by the browser Test Remote.

No special Denon or Roku power logic exists in the button driver.

The November 2 tests verified:

- Den ON.
- Den OFF.
- Sunroom ON.
- Sunroom OFF.
- Reserved Room 3 no-op.
- Room selection changes while the application was running.

The hardware-to-equipment command path is operational.

### 11.7 Rotary encoders — Chapter 6

The physical volume encoder is operational.

The current design uses Bourns PEC11R-4215F-S0024 rotary encoders. The earlier Grayhill volume-encoder plan has been superseded; that component is reserved for another project.

| Encoder | Rotation behavior | Pushbutton behavior | Status |
|---|---|---|---|
| Volume | Volume Up / Down | Mute Toggle | Rotation operational; push pending |
| Custom Action | Cycle available custom actions | Execute selected action | Planned integration |

The volume encoder uses GP8 and GP9 for quadrature inputs.

`controls/physical.py` polls the encoder and translates completed movements into generic `volume-up` and `volume-down` actions.

Those actions use the selected room and enter the same dispatcher and Dumb Queue™ as the browser Test Remote.

The encoder does not know the Denon protocol, receiver IP address, or network command syntax.

For recognized Denon fundamental volume commands, the execution layer selects the Denon TCP adapter. That adapter reuses a persistent receiver connection and enforces a minimum 50 ms interval between transmitted commands.

Physical testing confirmed:

- Five slow detents in each direction.
- Moderate rotation in both directions.
- Aggressive rotation with pauses and direction reversals.
- Smooth receiver volume changes and responsive LG volume-bar movement.
- Successful return to the starting receiver volume in controlled tests.

The LG volume overlay can take a moment to appear initially. Once displayed, its movement was observed to follow the encoder smoothly.

These results support retaining the Bourns encoder without adding software acceleration or command batching.

The encoder pushbutton remains to be integrated using the existing momentary-button infrastructure.

The second encoder will require custom-action selection state and push-to-run behavior. It should reuse the established physical-event and action-dispatch architecture rather than creating a separate command execution path.

### 11.8 Mechanical and feedback scope

The physical design includes:

- A substantial aluminum faceplate.
- A protective enclosure with accessible internals.
- Two prominent rotary encoders.
- A three-position room selector.
- Dedicated navigation and shortcut buttons.
- A prominent guarded power control.
- A small OLED display.
- Optional audible CLONK feedback.

The aluminum faceplate and Pico Cowbell mounting have progressed beyond the original breadboard prototype.

Final control placement, power supply, battery operation, display behavior, and audio feedback remain under development.

Do not describe planned feedback mechanisms as implemented.

See [Hardware & Physical Controls](HARDWARE_CONTROLS.md) for detailed component and mechanical records.

---

## 12. Room selection and custom destinations

Stable room IDs belong to configuration.

The physical room selector chooses which configured room receives physical actions.

It does not duplicate device mappings or command definitions.

The current mapping is:

- Room 1 — Den.
- Room 2 — Sunroom.
- Room 3 — Reserved.

The third position is not a BOTH mode.

Multi-room simultaneous dispatch is not implemented.

The existing three built-in destination slots remain stable.

Additional user-defined custom destinations (`device-4` onward) are a future extension, not a Config v4 feature.

The conceptual design places them in an optional per-room collection, separate from built-in slots.

Actual schema, migration, and deletion behavior require concrete implementation decisions.

A destination has identity and connection information.

Behavior belongs to actions.

Never silently retarget actions when a destination changes.

---

## 13. Apple TV and other future protocols

Apple TV compatibility is an explicit objective, **not an implemented feature**.

Discovery, pairing, authentication, session management, and a protocol-specific adapter may be required.

The existing generic HTTP transport and specialized Denon TCP volume adapter do not provide Apple TV pairing or authenticated session management.

Keep generic intentions such as Home, Back, navigation, and Play/Pause independent of equipment brands.

Do not add a speculative `apple_tv.py` module or configuration schema before concrete requirements and tests justify them.

---

## 14. Clock, diagnostics, and verification discipline

Browser synchronization supplies a UTC reference for readable timestamps.

Queue deadlines and compound waits use `time.monotonic()` and do not shift when wall-clock time is adjusted.

Automated NTP synchronization is not established by the tested baseline.

Use evidence labels precisely:

- **Implemented and verified:** Observed on the Pico, browser, or equipment within the specified test scope.
- **Implemented, not exhaustively tested:** Working code with remaining untested conditions.
- **Planned:** A future design or requirement, not a running feature.
- **Historical:** An earlier stage superseded by the current baseline.

A commit proves source changed.

Deployment proves files were copied.

HTTP 200 proves a transport acknowledgment.

Equipment observation supports a physical-behavior claim.

These are different evidence levels.

Keep normal serial logging concise.

Avoid continuous high-volume diagnostics that could affect cooperative scheduling or browser responsiveness.

Preserve known-good configuration and record test conditions before risky changes.

Keep dated experiments in [Development History](DEVELOPMENT_HISTORY.md) rather than duplicating the complete engineering journal here.

---

## 15. Historical milestones

| Milestone | Architectural result |
|---|---|
| XML v1 | Early browser editing and persistence concepts; historical |
| Config v2 | JSON validation, revisions, verified writes, backup rotation |
| Dumb Queue™, October 20 | Bounded admission, eligible-task scheduling, failure cancellation |
| Outbound HTTP, October 21 | Real Denon/Roku GET/POST execution |
| Config v3, October 22 | Stable generic built-in device IDs |
| Config v4, October 2026 | Named custom actions and cooperative ordered steps |
| Chapter 4, October 27 | Verified custom actions, toggles, and interleaving |
| Chapter 5, October 28 | GPIO scheduler foundation and HTTP pacing correction |
| Chapter 5, October 29 | GP17/GP18 mode switches and GP2 input events verified |
| Chapter 5 closeout, October 31 | Three-position room selector standalone GPIO test passed |
| Chapter 6, November 2 | Physical room selection and shared action routing operational |
| Chapter 6, November 2 | Power Toggle ON/OFF verified in Den and Sunroom; Room 3 no-op |
| Chapter 6, November 3 | Bourns physical volume encoder operational |
| Chapter 6, November 3 | Command-signature recognition and adapter caching implemented |
| Chapter 6, November 3 | Persistent Denon TCP volume control and 50 ms pacing verified |
| Chapter 6, November 3 | Mixed-transport queue regression tests passed |

The November 2 milestone established the first operational physical hardware-to-equipment control path.

November 3 extended that path to rotary volume control and introduced specialized device communication without changing the generic action vocabulary or adding another queue.

The architectural result is a reusable foundation for additional physical controls and future device adapters.

---

## 16. Design principles worth remembering

**Less sleek. More CLONK.**

**Smart enough to know when to be dumb.**

**Be resilient in our dumbness.**

**One queue. One poller. One shared execution path.**

**Hardware detects events. Physical coordination maps intent. Actions execute commands.**

**A future task must not hold an immediate button press hostage.**

**One failed external command cancels pending work, not the remote itself.**

**Clonker sends commands. Equipment owns state.**

**A command sequence is not permission to invent a workflow engine.**

**Configuration describes the destination. Actions describe the intention. Transport delivers the message.**

**Do not silently control another room when the selected room is unavailable.**

> **Do not make the Clonker more complicated merely because we are capable of making it more complicated.**

### 16.1 Future objective — Clonker Recipe Library

**Status:** Conceptual, not implemented.

Custom actions are operational; custom destinations and recipe distribution remain future work.

A future recipe library could provide downloadable configuration examples for equipment combinations and named sequences.

A future editor might retrieve a catalog, display compatibility notes, and load a recipe for review before an explicit Save.

Recipes must never bypass validation, revision protection, or persistence safeguards.

**Recipes help configure the Clonker; they do not become a runtime dependency.**

---

## 17. Reference documents

- [Configuration & Recovery](CONFIGURATION.md) — schema, validation, revisions, persistence, recovery.
- [Firmware, HTTP & Clock](FIRMWARE_NETWORK.md) — networking, scheduler details, transport, evidence.
- [Operating Modes](OPERATING_MODES.md) — GP17 and GP18 mode behavior.
- [Hardware & Physical Controls](HARDWARE_CONTROLS.md) — parts, GPIO assignments, mechanical plans.
- [Development & Deployment](DEVELOPMENT.md) — iPad-first workflow and tests.
- [Development History](DEVELOPMENT_HISTORY.md) — chronological engineering milestones.
- [Chapter 2 Handoff](CHAPTER_2_HANDOFF.md) — historical reference.
- [Terminology Audit](TERMINOLOGY_AUDIT.md) — historical terminology reconciliation.
- [Old Architecture](OLD_ARCHITECTURE.md) — historical reference.
- [`samples/device_config_roku_denon_sample.json`](../samples/device_config_roku_denon_sample.json) — readable two-room sample.

---

**THE CLONKER 10000**  
*Less sleek. More CLONK.*  
**CLONK! ⚡🔩**
