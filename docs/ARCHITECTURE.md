# The Clonker 10000 — System Architecture

**Updated:** November 9, 2026  
**Platform:** Raspberry Pi Pico 2 W / CircuitPython 10.3.1  
**Repository:** [djacobson/clonker-10000](https://github.com/djacobson/clonker-10000)  
**Current baseline:** Chapter 8 — assembled physical controls, optimized physical polling, room-aware OLED feedback, and persistent Custom Action execution acknowledgments  
**Configuration:** Clonker Config v4

> **Clonker controls actions, not brands. Controlled devices own their own state.**

---

## 1. Mission and architectural principles

The Clonker 10000 is a tactile, Wi-Fi-first home-theater remote.

Its purpose is to translate physical or browser input into configured equipment commands without becoming a general-purpose home-automation server.

The intended architecture is deliberately simple:

1. Detect a physical or browser action.
2. Determine the target room.
3. Resolve the generic action identity.
4. Admit work to the shared Dumb Queue™.
5. Resolve the command from active configuration.
6. Select the appropriate device transport.
7. Execute the command.
8. Record the result without pretending to know equipment state.

The design favors predictable behavior, serviceability, and incremental development.

**One queue. One poller. One shared execution path.**

Both physical controls and the browser Test Remote use the same action system.

The remote does not maintain authoritative equipment state. It sends commands and observes transport results.

**Be resilient in our dumbness.**

---

## 2. Architecture at a glance

```text
                   THE CLONKER 10000

     BROWSER TEST REMOTE          PHYSICAL CONTROLS
              |                  Buttons / Encoders
              |                     Room Selector
              |                           |
              |                       physical.py
              |                     Event -> Action
              |                     Selected Room
              |                           |
              +-------------+-------------+
                            |
                            v
                     ACTION DISPATCH
                        actions.py
                            |
                            v
                       DUMB QUEUE™
                  Fundamental / Custom
                    Physical Holds
                            |
                            v
                       actions.poll()
                      Eligible command
                            |
                            v
                    ACTIVE CONFIGURATION
                      Clonker Config v4
                            |
                            v
                     COMMAND RESOLUTION
                 Ordinary / Toggle / Custom
                       Held Button
                            |
                            v
                     device_adapters.py
                 Signature / Cache / Execute
                            |
              +-------------+-------------+
              |             |             |
              v             v             v
          Denon TCP      Roku ECP      Generic HTTP
          Persistent     Held Keys      GET / POST
          Port 23        Down / Up
              |             |             |
              v             v             v
          Denon AVR        Roku       Roku / Denon
           Volume       Volume /     Other Actions
                        Navigation


              COOPERATIVE MAINTENANCE LOOP
                            |
                            v
                   device_adapters.poll()
                            |
                            v
                    Roku Hold Release
                     / Retry Pacing


              CONFIG MANAGEMENT — GP18 CONFIG

                   Browser / Port 9090
                            |
                            v
                   Validate + Revision
                            |
                            v
                    Verified File Save
                            |
                            v
                    Publish RAM Config
                    Rebuild Adapter Cache
                    Clear Pending Actions
                    Reset Toggle Histories
```

The diagram represents three related responsibilities:

- The **Dumb Queue™** owns action admission, eligibility, ordering, and cancellation.
- The **adapter layer** owns protocol-specific execution and maintenance.
- The **physical coordinator** owns interpretation of GPIO events, including pairing held-button presses with their releases.

Roku key releases may occur after ordinary queue work has completed. Adapter maintenance therefore continues independently of queue depth.

### 2.1 Architectural invariants

- Physical controls generate generic actions, never manufacturer-specific command paths.
- Configuration owns destination and command definitions.
- `selectors.py` owns physical room-selection state.
- `physical.py` owns physical-event interpretation and room-aware dispatch.
- `actions.py` owns action admission, sequencing, eligibility, and cancellation.
- `device_adapters.py` owns command-signature recognition, cached selection, execution delegation, and lifecycle coordination.
- Individual adapters own protocol-specific behavior.
- Generic HTTP is the fallback transport.
- Browser and physical inputs share the same dispatcher and queue.
- Active validated RAM configuration is authoritative.
- Changed configuration saves invalidate pending work and reset toggle histories.
- External equipment owns actual power, volume, playback, and input state.
- Missing optional physical hardware must not disable the core application.
- A held button must release the endpoint associated with its original press, not whichever room happens to be selected later.

**No duplicate command pipelines. No second queue. No manufacturer-specific networking logic in GPIO drivers.**

---

## 3. Firmware component ownership

| Component | Responsibility |
|---|---|
| `firmware/boot.py` | GP17 boot-time filesystem ownership |
| `firmware/code.py` | CircuitPython application entry |
| `firmware/clonker/main.py` | Initialization, operating modes, cooperative scheduler |
| `firmware/clonker/device_config_v2.py` | Config v4 validation, RAM state, revisions, persistence |
| `firmware/clonker/actions.py` | Action dispatcher, Dumb Queue™, sequencing, cancellation |
| `firmware/clonker/device_adapters.py` | Adapter recognition, routing, execution, polling, cleanup |
| `firmware/clonker/devices/denon.py` | Persistent Denon TCP volume transport |
| `firmware/clonker/devices/roku.py` | Roku ECP volume holds and physical-button holds |
| `firmware/clonker/net/http_transport.py` | Generic bounded outbound HTTP |
| `firmware/clonker/net/web.py` | CONFIG-mode management HTTP |
| `firmware/clonker/controls/pins.py` | GPIO assignments |
| `firmware/clonker/controls/buttons.py` | Debounced momentary button driver |
| `firmware/clonker/controls/selectors.py` | Physical room selector |
| `firmware/clonker/controls/encoders.py` | Reusable quadrature encoder driver |
| `firmware/clonker/controls/physical.py` | Physical polling, action mapping, hold coordination |
| `firmware/clonker/controls/switches.py` | CONFIG/RUN switch and development overrides |
| `firmware/clonker/system/clock.py` | UTC reference and monotonic timing |
| `firmware/clonker/system/logger.py` | Serial diagnostics |
| `firmware/clonker/system/perf.py` | Shared performance measurement and statistics |
| `firmware/clonker/display/oled.py` | SH1106 initialization, one/two-line deferred rendering, hardware inversion acknowledgments, refresh pacing, and idle-off behavior |
| `firmware/clonker/www/` | Configuration editor and Test Remote |
| `firmware/clonker/legacy/` | Historical XML implementation |

The historical filename `device_config_v2.py` does not indicate the current configuration schema version.

The active schema is **Config v4**.

Avoid cosmetic renames that could disrupt working firmware merely to make filenames match current terminology.

### 3.1 Separation of responsibilities

**Hardware drivers** detect electrical changes.

**Physical coordination** translates those changes into generic action IDs and supplies the selected room.

**Configuration** defines destinations and commands.

**Action dispatch** validates and queues work.

**Device adapters** determine how eligible commands are transmitted.

**Transports** perform network communication.

This separation allows the same action to originate from a browser, momentary button, or rotary encoder without duplicating protocol logic.

### 3.2 Hardware versus application state

Reusable hardware drivers should know only what is necessary to interpret their input.

The `Encoder` class understands quadrature transitions, not volume levels or receiver protocols.

The `Button` class understands debounced press and release events, not power or mute semantics.

The room selector understands its physical position, not the equipment configuration.

Application-level coordination assigns meaning to these events.

The physical coordinator additionally maintains temporary state for held buttons, ensuring that releases remain associated with their original press.

**Reusable hardware mechanisms; simple application-specific state.**

---

## 4. Operating modes

The Clonker has two independent operating-mode dimensions.

### 4.1 SERVICE / DEVICE — GP17

| Electrical state | Mode | Filesystem writer |
|---|---|---|
| Open / HIGH | SERVICE | USB host |
| Grounded / LOW | DEVICE | Pico firmware |

GP17 is evaluated by `boot.py`.

Changing filesystem ownership requires a full power cycle.

A CircuitPython Ctrl+D soft reboot does not reproduce the boot-time ownership decision.

### 4.2 CONFIG / RUN — GP18

| Electrical state | Mode | Management HTTP |
|---|---|---|
| Open / HIGH | RUN | Disabled |
| Grounded / LOW | CONFIG | Enabled, port 9090 |

GP18 is evaluated while the application runs.

The mode can change without rebooting.

The Dumb Queue™ continues operating in both modes.

The switch implementation also supports development simulation and override.

### 4.3 Valid combinations

| GP17 mode | GP18 mode | Behavior |
|---|---|---|
| SERVICE | CONFIG | USB owns filesystem; browser can inspect and test, but cannot persist Pico-side changes |
| SERVICE | RUN | USB owns filesystem; management listener off |
| DEVICE | CONFIG | Pico owns filesystem; browser management and saves enabled |
| DEVICE | RUN | Normal remote operation |

Neither switch is an equipment power command.

See [Operating Modes](OPERATING_MODES.md) for procedures and caveats.

---

## 5. Configuration architecture

The active configuration is **Clonker Config v4**, stored as JSON.

The deployed configuration path is:

`/clonker/device_config.json`

Each configured room contains:

- A stable room ID.
- A display name.
- Three generic built-in device destinations.
- Fourteen fundamental action definitions.
- Optional named custom actions.

The current development installation contains three configured rooms:

| Room ID | Name | Status |
|---|---|---|
| `room-1` | Den | Operational equipment configuration |
| `room-2` | Sunroom | Operational equipment configuration |
| `room-3` | Room 3 | Configured placeholder with blank device addresses and commands |

Config v4 permits one to three configured rooms. The presence of Room 3 in the current installation does not make three rooms mandatory for other users.

The physical selector recognizes all three positions independently of whether the corresponding room exists in the active configuration.

### 5.1 Generic built-in destinations

| Stable ID | Default label |
|---|---|
| `device-1` | TV |
| `device-2` | AVR |
| `device-3` | Streaming |

These labels are presentation defaults, not enforced protocol types.

A configured action determines which destination and command path are used.

For example, Sunroom volume currently targets its Roku through the Streaming destination, while Den volume targets its Denon receiver.

The physical volume encoder does not need to know this distinction.

### 5.2 Blank commands and room availability

Config v4 allows blank device addresses and ordinary command paths.

For ordinary fundamental actions, a missing endpoint or blank command path represents an intentional no-op.

An unconfigured room and a configured room containing blank commands are different conditions.

The physical selector can select either one. Command dispatch must respect the selected room without falling back to another room.

**Important Chapter 7 boundary:** Explicit Roku held-button dispatch has stricter requirements than ordinary fundamental actions. It currently requires a valid endpoint, POST method, and recognized Roku key path.

Blank-command no-op handling for this held-button path remains to be completed and verified before Room 3 is treated as fully harmless for every physical button.

### 5.3 Active RAM configuration

At startup, the configuration engine loads and validates the persisted JSON.

Runtime command execution resolves definitions from the active in-memory configuration.

It does not reread the JSON file for every action.

The browser editor is a client of the configuration engine, not a separate source of truth.

### 5.4 Save and recovery boundaries

The configuration engine provides:

- Schema validation.
- Revision checks against stale browser edits.
- Filesystem writability checks.
- Verified temporary writes.
- Backup rotation.
- Recovery handling.

A successful changed save publishes the validated configuration, rebuilds adapter selections, clears pending work, and resets volatile toggle histories.

An unchanged save preserves existing work and toggle histories.

A rejected save must not replace active configuration or adapter routing.

The Pico filesystem does not automatically synchronize with GitHub.

See [Configuration & Recovery](CONFIGURATION.md) for exact persistence behavior.

---

## 6. Fundamental actions and custom actions

### 6.1 Fundamental actions

Each configured room defines fourteen stable fundamental action IDs.

| Category | Actions |
|---|---|
| Volume | `volume-up`, `volume-down`, `mute-toggle` |
| Navigation | `nav-up`, `nav-down`, `nav-left`, `nav-right`, `select` |
| Shortcuts | `back`, `home` |
| Playback | `play-pause`, `skip-back`, `skip-forward` |
| Power | `power-toggle` |

Actions resolve configured destinations, methods, and paths.

The action vocabulary is independent of equipment protocols.

### 6.2 Power and mute toggles

`power-toggle` and `mute-toggle` use independent volatile direction histories keyed by room and action.

Unknown history begins with the configured ON path.

History advances only after successful transmission.

Failures and no-ops do not advance it.

A reboot or successful changed configuration save resets histories.

This is **last-successful-command direction**, not equipment-state discovery.

A receiver, Roku, HDMI-CEC chain, or another remote may change equipment state without Clonker knowing.

### 6.3 Custom actions

Custom actions are named, ordered sequences configured per room.

Each step specifies a destination, method, path, and optional wait.

A custom action occupies one Dumb Queue™ entry while progressing through its steps.

Waits use monotonic deadlines.

Other eligible actions may execute while a custom action is waiting.

Current custom-action steps use generic HTTP, even when a command resembles a specialized fundamental volume command.

There is no branching engine, macro thread, rollback system, or independent custom-action queue.

---

## 7. The Dumb Queue™

**Module:** `clonker/actions.py`

The Dumb Queue™ is the single execution pipeline for browser and physical actions.

Its responsibilities are:

1. Validate and admit requested actions.
2. Maintain bounded pending work.
3. Determine eligible commands.
4. Preserve applicable ordering.
5. Resolve commands from active configuration.
6. Coordinate adapter readiness and execution.
7. Advance custom-action steps.
8. Cancel pending work after failures.

### 7.1 Capacity and representation

The queue holds up to **128 entries**.

Current queued work includes:

- Fundamental actions.
- Custom-action sequences.
- Explicit physical-button hold events.

Fundamental actions use stable IDs.

Custom actions use room-specific IDs and compact step state.

Ordinary commands are resolved when eligible rather than copied into each queue entry.

Explicit hold events preserve their endpoint and command at admission because the matching release must not be redirected by a later room selection.

### 7.2 Eligibility and ordering

The queue scans for the first eligible task.

An action waiting for a future deadline does not block an immediate action.

Among currently eligible tasks, queue order matters.

If an eligible Denon TCP volume command is waiting for its pacing interval, the queue preserves its position rather than allowing later commands to overtake it.

At most one eligible queued command is executed per poll.

### 7.3 Physical hold events

Chapter 7 introduced explicit queued hold events for six physical buttons:

- Navigation Up.
- Navigation Down.
- Navigation Left.
- Navigation Right.
- Skip Back.
- Skip Forward.

Each physical press queues a held-button `pressed` event.

Each corresponding release queues a held-button `released` event.

The adapter translates these events into Roku ECP keydown and keyup operations.

These are not separate action queues. They are additional task types within the existing Dumb Queue™.

### 7.4 Failure policy

An execution exception cancels remaining pending work, including unfinished custom actions.

New work may subsequently be admitted.

The queue does not automatically retry uncertain commands.

This avoids blindly duplicating operations that might already have reached equipment.

Adapter-specific cleanup, including a pending Roku key release, is a separate lifecycle responsibility.

**One failed external command cancels pending work, not the remote itself.**

### 7.5 Queue versus adapter state

The queue owns action state.

An adapter may own transport state.

Examples:

- Denon owns its persistent TCP socket and pacing deadline.
- Roku owns its held-volume direction, endpoint, and release deadlines.
- Roku also owns explicit physical-button hold state.
- Generic HTTP owns temporary sockets during individual requests.

These states do not constitute separate action queues.

---

## 8. Device adapter architecture

**Module:** `clonker/device_adapters.py`

The adapter layer separates generic command intent from protocol-specific transmission.

Selection for ordinary fundamental actions is based on recognized command signatures, not room names, manufacturer labels, or fixed device positions.

Explicit physical-button holds use a dedicated Roku execution path.

### 8.1 Current adapter matrix

| Adapter / path | Recognized command | Delivery |
|---|---|---|
| `denon-tcp` | Denon fundamental volume GET signatures | Persistent TCP port 23 |
| `roku-hold` | Roku fundamental volume POST signatures | ECP held-volume |
| Roku physical-button hold | Six supported navigation/skip signatures | ECP keydown/keyup |
| `generic-http` | Other supported configured commands | Bounded HTTP GET/POST |

Ordinary fundamental volume actions select specialized adapters when their command signatures are recognized.

Other fundamental actions and current custom-action steps use generic HTTP unless explicitly routed through the physical-button hold mechanism.

### 8.2 Signature-based selection

Recognized Denon volume signatures:

```text
GET /goform/formiPhoneAppDirect.xml?MVUP
GET /goform/formiPhoneAppDirect.xml?MVDOWN
```

Recognized Roku volume signatures:

```text
POST /keypress/VolumeUp
POST /keypress/VolumeDown
```

Recognized physical-button hold paths:

```text
POST /keypress/Up
POST /keypress/Down
POST /keypress/Left
POST /keypress/Right
POST /keypress/Rev
POST /keypress/Fwd
```

The explicit physical-button hold path requires these recognized Roku commands.

It should not be confused with generic HTTP dispatch of a fundamental action from the browser.

### 8.3 Adapter cache

Specialized fundamental-volume selections are cached by `(room_id, action_id)`.

The cache is derived from active validated configuration and is not persisted in Config v4 JSON.

Unrecognized ordinary commands use generic HTTP.

The cache is rebuilt when configuration becomes active.

A rejected configuration save retains the previous routing state.

The cache does not contain equipment power or volume state.

### 8.4 Execution and lifecycle

The adapter layer coordinates:

- Readiness checks.
- Protocol-specific execution.
- Maintenance polling.
- Cancellation cleanup.
- Application shutdown cleanup.

A key architectural distinction is that adapter maintenance may continue when the action queue is empty.

For example, Roku held-volume requires a later keyup after the final volume action has completed.

Physical-button holds also require safe release handling.

The cooperative scheduler calls adapter maintenance independently of whether another action is eligible.

This is not a second queue or background worker.

---

## 9. Protocol-specific transport responsibilities

### 9.1 Denon TCP

**Module:** `clonker/devices/denon.py`

The Denon adapter:

- Extracts the receiver host from the configured endpoint.
- Uses native TCP port 23.
- Reuses one persistent receiver connection.
- Translates recognized volume signatures to `MVUP` or `MVDOWN`.
- Enforces a minimum 50 ms command interval.
- Closes and resets its connection on appropriate errors or shutdown.

The adapter currently supports one active receiver connection, not a pool of simultaneous connections.

It does not parse receiver status responses or maintain authoritative AVR state.

A successful TCP write does not prove the receiver executed the command.

### 9.2 Roku held-volume

**Module:** `clonker/devices/roku.py`

The Roku volume adapter uses ECP keydown/keyup operations to turn repeated encoder movements into a temporary held key.

Its responsibilities include:

- Starting a hold on the first detent.
- Extending same-direction holds without additional HTTP requests.
- Releasing after an idle period.
- Releasing before direction reversal.
- Bounding maximum hold duration.
- Retaining unresolved release state after failures.
- Pacing release retries.
- Participating in cancellation and shutdown cleanup.

Current timing parameters:

| Parameter | Value |
|---|---:|
| Idle release | 250 ms |
| Maximum volume hold | 2 seconds |
| Failed-release retry interval | 500 ms |

The Roku adapter uses the generic outbound HTTP transport for its ECP requests.

It does not maintain a persistent HTTP socket.

The adapter's release-retry mechanism is a specialized safety measure, not a general action retry system.

### 9.3 Roku physical-button holds — Chapter 7

The six physical navigation and skip buttons use explicit press/release semantics.

The application sends a Roku keydown when the physical button is pressed and a matching keyup when it is released.

This allows Roku's native held-button behavior, including repeated navigation while a direction is held.

The implementation spans:

| Module | Responsibility |
|---|---|
| `controls/buttons.py` | Detect stable press and release |
| `controls/physical.py` | Identify hold-capable buttons and preserve press context |
| `actions.py` | Queue hold events |
| `device_adapters.py` | Validate and route recognized Roku hold commands |
| `devices/roku.py` | Execute ECP keydown/keyup and maintain hold safety |

#### Press and release ownership

When a hold-capable button is pressed:

1. The physical coordinator reads the selected room.
2. It resolves the configured action and destination.
3. It queues the press event.
4. It remembers the room, endpoint, and command for that button.

When the button is released:

1. The physical coordinator retrieves the original press context.
2. It queues the release against that original endpoint.
3. The adapter sends the matching Roku keyup.

Changing rooms while a button is held must not redirect the release to another room.

This is an important distinction from ordinary fundamental actions, which resolve their commands from active configuration during execution.

#### Safety and limitations

The explicit physical-button hold mechanism has a **30-second maximum hold safety limit**.

The Roku module maintains separate state for encoder-driven volume holds and explicit physical-button holds.

The firmware also attempts best-effort release cleanup during cancellation and shutdown.

A failed network request can leave uncertainty about what the Roku actually received. The implementation reduces that risk but cannot guarantee remote key state after every possible network failure.

The explicit hold path currently recognizes Roku ECP commands only. It is not a general-purpose held-button abstraction for every future device protocol.

**Verified Chapter 7 behavior:** All four navigation directions and both skip buttons were tested with physical press, hold, and release.

### 9.4 Generic HTTP

**Module:** `clonker/net/http_transport.py`

Generic HTTP provides bounded blocking GET/POST requests.

It is used for:

- Ordinary Roku ECP commands.
- Denon HTTP power and mute.
- Roku VolumeMute.
- Custom-action steps.
- Other configured commands without recognized specialized signatures.

Each request creates and closes its own TCP connection.

The transport is intentionally small and does not provide full HTTP response-body processing, TLS, authentication, redirects, or persistent connections.

### 9.5 Why these paths exist

The transports solve different problems.

Denon volume benefits from a persistent native TCP connection.

Roku volume benefits from minimizing HTTP requests during rapid encoder movement.

Physical navigation benefits from explicit keydown/keyup behavior rather than treating every button as a momentary keypress.

Ordinary actions remain well served by bounded HTTP.

The architecture allows these approaches to coexist without changing the generic action vocabulary or creating new execution pipelines.

Detailed timing, failure semantics, and implementation tests belong in [Firmware, Network & Clock](FIRMWARE_NETWORK.md).

---

## 10. Cooperative scheduler

**Module:** `clonker/main.py`

The firmware uses a cooperative main loop rather than threads or hardware-interrupt-driven command execution.

Current target intervals:

| Responsibility | Target |
|---|---:|
| Physical controls | 1 ms |
| Action queue | 10 ms |
| Management HTTP | 1 ms |
| Main-loop yield | 1 ms |

The main loop services physical inputs, queued actions, adapter maintenance, operating-mode changes, and inbound management requests.

These intervals are targets, not guaranteed maximum latencies.

### 10.1 Scheduling priorities

The main loop processes work in this general order:

1. Physical GPIO inputs.
2. One eligible queued action, when due.
3. Stateful device-adapter maintenance.
4. CONFIG/RUN mode evaluation and management HTTP.
5. OLED display polling.
6. Brief CircuitPython yield.

The action queue operates in both CONFIG and RUN modes.

The management listener is active only when CONFIG mode is enabled.

### 10.2 Physical input responsiveness

Rotary encoders generate electrical transitions that must be sampled.

The reusable encoder driver decodes transitions and reports completed movements.

Physical coordination translates them into generic actions.

Network execution occurs separately through the queue.

Specialized volume adapters reduce network overhead during rapid rotation.

However, synchronous socket operations can still temporarily delay physical sampling.

The queue cannot reconstruct electrical transitions that were never observed.

### 10.3 Chapter 7 responsiveness and PERF instrumentation

Chapter 7 investigated slow browser page loads, occasional management HTTP timeouts, and competition between physical polling, diagnostics, and network operations.

Scheduler adjustments and reduced diagnostic overhead substantially improved Config page and Test Remote responsiveness in Safari and Chrome.

The shared `system/perf.py` module now provides named timing measurements and accumulated statistics.

`main.py` instruments physical polling gaps, physical execution, queue execution, adapter maintenance, management HTTP, OLED polling, and main-loop execution.

Optional internal measurements in `controls/physical.py` permit more focused investigation without permanently enabling detailed instrumentation.

Testing identified occasional physical execution spikes around 40–50 ms. Their cause remains unresolved.

These execution spikes must be distinguished from longer physical polling gaps caused by synchronous network operations.

The instrumentation does not change the cooperative execution model, introduce asynchronous networking, or guarantee that every encoder transition will be captured.

Detailed measurements and experiments belong in [Firmware, Network & Clock](FIRMWARE_NETWORK.md) and [Development History](DEVELOPMENT_HISTORY.md).

### 10.4 Adapter maintenance

Roku held-volume requires maintenance after the last encoder detent.

Physical-button holds also require lifecycle maintenance and release safety.

Therefore, the scheduler polls the adapter layer even when no queue command is ready.

The adapter layer may attempt a release or defer a retry until its deadline.

This preserves a cooperative design without adding another action queue or worker.

### 10.5 Management HTTP

The CONFIG-mode management server uses a cooperative single-client listener.

It is not a concurrent web server.

The application has no management authentication and is intended for a trusted LAN only.

Browser actions and physical actions continue sharing the same queue.

---

## 11. Physical controls

Chapter 7 expanded the operational physical interface from room selection, power, and volume into navigation and playback.

### 11.1 Current GPIO assignments

| GPIO | Function |
|---|---|
| GP2 | Momentary Power Toggle |
| GP3 | Room selector — Den |
| GP4/GP5 | STEMMA QT / OLED I²C reserved |
| GP6 | Room selector — Sunroom |
| GP7 | Room selector — Room 3 |
| GP8/GP9 | Bourns volume encoder A/B |
| GP10 | Volume encoder push-to-mute |
| GP11/GP12 | Bourns custom-action encoder A/B |
| GP13 | Custom-action encoder pushbutton |
| GP14 | Navigation Up |
| GP15 | Navigation Down |
| GP16 | Navigation Left |
| GP17 | SERVICE/DEVICE |
| GP18 | CONFIG/RUN |
| GP19 | Navigation Right |
| GP20 | Select / OK |
| GP21 | Back |
| GP22 | Home |
| GP26 | Skip Back |
| GP27 | Play/Pause |
| GP28 | Skip Forward |

`controls/pins.py` is the source of truth for assignments.

GPIO assignment, successful electrical detection, and complete application behavior are separate verification milestones.

The Pico Cowbell Terminal board provides GPIO access, and the wiring uses shared ground distribution.

### 11.2 Physical room selector

The three-position selector uses GP3/GP6/GP7.

It requires exactly one active grounded input and 50 ms of stable selection before accepting a change.

Invalid transitional readings do not replace the last valid room.

The selector changes room context; it does not dispatch a network action.

The selected room is logged when a stable change is detected.

### 11.3 Three-room configuration

The current development configuration contains:

- Room 1: Den.
- Room 2: Sunroom.
- Room 3: Room 3, with blank device addresses and command paths.

Room 3 is an editable configuration placeholder.

It is not a combined-room mode, and it must not silently fall back to another room.

The selector remains independent of configuration availability.

### 11.4 Momentary buttons

`controls/buttons.py` provides active-low, internally pulled-up, debounced momentary inputs.

The default debounce interval is 30 ms.

`physical.py` maps button identities to fundamental action IDs through `BUTTON_ACTIONS`.

Current press-only actions include:

- Power Toggle.
- Home.
- Back.
- Select.
- Play/Pause.
- Volume encoder push-to-mute.

The six navigation/skip buttons use both press and release events.

The physical mapping layer keeps button identity separate from action semantics, allowing future alternative layouts without rewriting the hardware drivers.

### 11.5 Rotary volume control

The operational volume encoder is a Bourns PEC11R-4215F-S0024.

Its A/B signals use GP8/GP9.

Its independent pushbutton uses GP10 and GND.

Rotation generates `volume-up` or `volume-down`.

Pressing the shaft generates `mute-toggle`.

Both actions pass through the selected room and shared Dumb Queue™.

The encoder driver does not know whether the destination is Denon or Roku.

### 11.6 Custom-action encoder

The second Bourns encoder uses GP11/GP12 for rotation and GP13 for its pushbutton.

Rotation cycles through the currently selected room's ordered custom actions, wrapping at the ends of the list.

The physical coordinator maintains the selected action index. Changing rooms resets the selection.

An empty custom-action list is handled without attempting execution.

Pressing the encoder dispatches the selected custom action through the existing `actions.py` execution path.

The selected action name is also sent to the OLED display interface.

The encoder driver itself remains independent of configuration, custom-action semantics, and display hardware.

### 11.7 Two-room verification

| Room | Volume transport | Mute transport | Observed result |
|---|---|---|---|
| Den | Denon TCP | Denon HTTP | Volume and mute/unmute operational |
| Sunroom | Roku ECP held-volume | Roku ECP generic HTTP | Volume and mute/unmute operational |

The Sunroom Roku controls receiver volume through the equipment's HDMI-CEC path.

Fast and sustained rotation tests demonstrated smooth practical volume response, with slight display lag and very small overshoot.

Physical navigation and skip-button holds were also exercised against Roku equipment.

These results establish tested functionality, not indefinite fault-free operation.

### 11.8 OLED feedback and physical coordination

The SH1106 128×64 OLED operates over I²C on GP4/GP5.

`display/oled.py` owns display initialization, text rendering, hardware inversion, refresh pacing, activity tracking, and idle display-off.

`controls/physical.py` requests display changes in response to physical events. It does not perform direct I²C operations.

Implemented feedback includes:

- **Room selection:** Two-line room number and configured name, or `UNASSIGNED`.
- **Custom Action selection:** Normal display of the selected action name.
- **Custom Action execution:** Persistent inverted display after successful dispatch.
- **Volume:** `VOL UP +` or `- VOL DOWN` according to rotation direction.
- **Mute:** `MUTE ON` or `MUTE OFF` following successful toggle-command transmission.

Volume feedback uses `is_showing_or_pending()` and `touch()` to avoid redundant rendering during repeated detents in the same direction.

The OLED provides two text layouts: enlarged single-line text and an optional smaller heading above enlarged text.

`show_text(message, second_line=None, reset_ack=False)` records a request without immediate I²C.

When the requested text is unchanged and the display is awake, no framebuffer refresh is scheduled. Repeated requests still extend the idle activity timer.

`acknowledge()` requests hardware inversion. `poll()` applies `0xA7` or `0xA6` only when the requested inversion state differs from the applied state.

The optional `reset_ack=True` clears an acknowledgment without forcing a framebuffer redraw when the text is unchanged.

The OLED retains its 100 ms minimum framebuffer refresh interval and 15-second idle timeout. Idle sleep restores normal inversion mode before switching off the display.

Display updates remain cooperative and separate from command dispatch. Successful Custom Action dispatch is requested before its OLED acknowledgment.

Mute messages represent the action dispatcher's transmitted toggle direction, not independently queried receiver state.

The physical assembly is mounted, soldered, wired, secured, and strain-relieved through the Pico Cowbell Terminal board.

Future development includes:

- Additional OLED messages where they improve usability.
- Audible CLONK feedback.
- Battery selection, charging, sleep, and wake behavior.
- Possible alternate panel orientation.

The orientation concept would exchange navigation and skip directions through an alternate action mapping rather than rewriting GPIO drivers.

No general panel-orientation feature is currently implemented.

See [Hardware & Physical Controls](HARDWARE_CONTROLS.md).

---

## 12. Future expansion boundaries

### 12.1 Custom destinations

Config v4 currently provides three generic built-in destinations per room.

Additional user-defined destinations are a future extension.

A possible design would store them in a separate optional per-room collection.

Their identity, schema, migration, deletion, and action-reference behavior must be designed before implementation.

A destination has identity and connection information.

Behavior belongs to actions.

Never silently retarget actions when a destination changes.

### 12.2 Apple TV compatibility

Apple TV compatibility is an explicit objective, not an implemented feature.

Discovery, pairing, authentication, session management, and protocol-specific command handling may be required.

The existing generic HTTP, Denon TCP, and Roku ECP adapters do not provide Apple TV pairing or authenticated sessions.

Generic action intentions such as Home, Back, navigation, and Play/Pause should remain independent of device brands.

Do not add a speculative `apple_tv.py` module before concrete requirements and tests justify it.

### 12.3 Clonker Recipe Library

**Status:** Conceptual.

A future recipe library could provide downloadable configuration examples for equipment combinations and named action sequences.

Recipes might be retrieved and loaded into the editor for review before an explicit Save.

They must not bypass schema validation, revision protection, or persistence safeguards.

**Recipes help configure the Clonker; they do not become a runtime dependency.**

---

## 13. Clock, diagnostics, and verification discipline

Browser synchronization supplies a UTC reference for readable timestamps.

Queue deadlines, custom-action waits, Denon pacing, and Roku hold timing use `time.monotonic()`.

Wall-clock adjustments must not shift scheduling deadlines.

Automated NTP synchronization is not established by the current tested baseline.

### 13.1 Evidence vocabulary

| Term | Meaning |
|---|---|
| Implemented and verified | Observed within a specified test scope |
| Implemented, not exhaustively tested | Working code with remaining untested conditions |
| Planned | Future design or requirement |
| Historical | Earlier implementation superseded by current code |

A commit proves source changed.

Deployment proves files were copied.

HTTP 200 proves a transport acknowledgment.

A successful TCP write proves bytes were handed to the network stack.

Equipment observation supports a physical-behavior claim.

These are different evidence levels.

### 13.2 Development discipline

- Preserve known-good configuration.
- Change one meaningful component at a time.
- Test hardware independently before integration.
- Keep optional inputs optional.
- Record network errors with enough context to diagnose them.
- Avoid unnecessary high-volume serial logging.
- Keep dated experiments in Development History.
- Avoid adding abstractions without a demonstrated need.

---

## 14. Historical architectural milestones

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
| Chapter 5, October 29 | GP17/GP18 modes and GP2 input events verified |
| Chapter 5 closeout, October 31 | Three-position room selector standalone test |
| Chapter 6, November 2 | Physical room selection and shared dispatch operational |
| Chapter 6, November 2 | Power Toggle verified in Den and Sunroom |
| Chapter 6, November 3 | Bourns physical volume encoder operational |
| Chapter 6, November 3 | Signature-based adapter selection and cache |
| Chapter 6, November 3 | Persistent Denon TCP volume and queue pacing verified |
| Chapter 6, November 3 | Roku ECP held-volume adapter operational |
| Chapter 6, November 3 | Mixed-room volume and physical push-to-mute verified |
| Chapter 7, November 4–7 | Expanded physical GPIO integration and scheduler responsiveness testing |
| Chapter 7, November 2026 | Physical navigation and playback buttons operational |
| Chapter 7, November 2026 | Six Roku keydown/keyup physical-button holds verified |
| Chapter 7, November 7 | Configured blank Room 3 added to development installation |
| Chapter 7, November 7 | Room-aware custom-action encoder selection and execution operational |
| Chapter 7, November 7 | SH1106 OLED driver and initial custom-action display feedback integrated |
| Chapter 7, November 8 | Shared `system/perf.py` instrumentation operational |
| Chapter 7 closeout, November 8 | Physical assembly complete; unresolved timing spikes documented for further investigation |

Chapter 7 extended the existing architecture rather than replacing it.

Its principal additions were explicit physical-button holds, room-aware custom-action encoder control, initial OLED feedback, and shared performance instrumentation.

Physical-button holds preserve the original destination across press and release events. The custom-action encoder reuses the existing action dispatcher and Dumb Queue™. The OLED receives display requests without requiring direct I²C writes from physical event handlers.

Shared PERF instrumentation measures the existing cooperative scheduler without introducing another execution pipeline.

Chapter 8 resolved recurring physical polling execution spikes by replacing repeated configuration validation with lightweight accessors into the already-validated active configuration.

The same approach was extended to Custom Action lookup and physical hold-button room checks.

Chapter 8 also expanded the event-driven OLED interface:

- Room selection now requests a two-line display containing the room number and configured name, or `UNASSIGNED` for an unavailable room.
- Custom Action rotation displays the selected name and explicitly clears any previous execution acknowledgment.
- Successful Custom Action dispatch requests the action name and persistent hardware inversion.
- Inversion remains active until a new display message, explicit acknowledgment reset, or idle sleep.
- The SH1106 performs inversion through hardware commands without framebuffer redraws or additional timers.

The OLED behavior, including same-text acknowledgment reset without redundant framebuffer refresh, was verified on physical hardware.

The physical assembly is complete. Battery power, sleep/wake behavior, audible feedback, and further reliability testing remain future work.

---

## 15. Design principles worth remembering

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

**A button release belongs to the room where its press began.**

**A protocol adapter is not permission to invent another action queue.**

> **Do not make the Clonker more complicated merely because we are capable of making it more complicated.**

---

## 16. Reference documents

- [Configuration & Recovery](CONFIGURATION.md) — schema, validation, revisions, persistence, recovery.
- [Firmware, Network & Clock](FIRMWARE_NETWORK.md) — scheduler details, adapters, transports, diagnostics.
- [Operating Modes](OPERATING_MODES.md) — GP17 and GP18 behavior.
- [Hardware & Physical Controls](HARDWARE_CONTROLS.md) — GPIO assignments, components, mechanical plans.
- [Development & Deployment](DEVELOPMENT.md) — deployment workflow and regression tests.
- [Development History](DEVELOPMENT_HISTORY.md) — chronological engineering milestones.
- [Chapter 2 Handoff](CHAPTER_2_HANDOFF.md) — historical reference.
- [Old Architecture](OLD_ARCHITECTURE.md) — historical reference.
- [`samples/device_config_roku_denon_sample.json`](../samples/device_config_roku_denon_sample.json) — readable configuration example.

---

**THE CLONKER 10000**  
*Less sleek. More CLONK.*  
**CLONK! ⚡🔩**
