# The Clonker 10000 — Architecture

**Design reference · 15 October 2026**  
**Active target:** Raspberry Pi Pico 2 W / CircuitPython 10.3.1  
**Repository:** [djacobson/clonker-10000](https://github.com/djacobson/clonker-10000)

> **Clonker controls actions, not brands. Controlled devices own their own state.**

## Mission

A tactile, Wi-Fi-first home theater remote with real knobs, switches, satisfying buttons, and eventually an audible **CLONK!** Physical controls produce generic actions; room configuration and device adapters resolve those actions to commands. Controlled devices remain authoritative for their actual state.
Clonker does not maintain a speculative model of equipment power, volume, or input status.

A narrow V1 exception exists for the two fundamental toggle
actions: Clonker remembers the last successfully submitted
ON/OFF command for each room and toggle action. This is command
history, not an assertion about the device's actual state.

**Priority:** responsive physical inputs → reliable device commands → maintained room selector → configuration interface → diagnostics/time → OLED and sound → battery optimization.

## Architecture at a glance

```text
Physical inputs / room selector / CONFIG switch
                  |
          Generic input events        [PLANNED]
                  |
          Action dispatcher           [PLANNED]
                  |
      Room configuration / mappings
                  |
      Network device adapters         [PLANNED]
                  |
          Roku / Denon / LG / ...

Separate low-priority service:
  CONFIG mode -> HTTP :9090 -> clock + room editor
```

**State ownership:** Physical selectors and maintained switches will be
read from GPIO; room names, device endpoints, and action mappings come
from persistent JSON v2 configuration. The active firmware loads
`/clonker/device_config.json` through `device_config_v2.py`.
The previous XML v1 engine remains available as a rollback reference.
Actual AV state belongs to the controlled devices; debounce, queues,
and clock reference live in RAM. Do not write flash for switch changes
or idle status.

## Two independent mode dimensions

- **SERVICE (USB) / DEVICE:** developer filesystem ownership, selected by GP17 jumper **at power-on**; power cycle required.
- **CONFIG / RUN:** user application behavior, eventually controlled by a physical maintained switch **during runtime**; no reboot intended. Currently simulated CONFIG is enabled.

See [Operating Modes](OPERATING_MODES.md) and [Development & Deployment](DEVELOPMENT.md).

## Implemented vs planned

**Verified on Pico:** Wi-Fi connectivity, serial REPL, GP17 filesystem
ownership modes, JSON v2 three-room loading, browser clock
synchronization, HTTP management server on port 9090, browser
configuration editing, persistent JSON saves, no-change detection,
backup rotation, and stale-revision conflict rejection.

**Implemented and partially verified:** Strict JSON v2 validation,
revision-protected persistence, detection of out-of-band configuration
changes, verified temporary writes, and startup fallback to validated
backups. The on-device test record documents which cases have been
exercised successfully and which remain untested.

**Additional testing pending:** Interrupted-write and power-loss
scenarios, comprehensive malformed HTTP requests, complete power-cycle
persistence verification, and remaining HTTP-level error cases.
Power-loss durability is not guaranteed.

**Active configuration:** JSON v2 with three fixed rooms, three device
endpoints per room, fourteen fundamental actions per room, and an empty
reserved `custom_actions` array. The browser and firmware both use
JSON v2. The XML v1 implementation is retained for rollback.

**Not yet implemented:** Physical CONFIG/RUN switch, room selector
GPIO, encoder/button event capture, action dispatcher, real AV network
commands, OLED functionality, audio feedback, and battery management.

## Current firmware map

| File | Role |
|---|---|
| `firmware/boot.py` | GP17 filesystem ownership at cold boot |
| `firmware/code.py` | CircuitPython entry point |
| `firmware/clonker/main.py` | Loads config, starts/stops web service, cooperative loop |
| `firmware/clonker/controls/switches.py` | Simulated CONFIG switch; GPIO path future |
| `firmware/clonker/controls/pins.py` | Switch pin configuration |
| `firmware/clonker/device_config_v2.py` | Active JSON v2 validation, serialization, revision protection, persistence, and backup recovery |
| `firmware/clonker/device_config.py` | Retained XML v1 configuration engine for rollback |
| `firmware/clonker/web.py` | Bounded cooperative HTTP service, port 9090 |
| `firmware/clonker/www/index.html` | Browser clock/config editor |
| `firmware/clonker/clock.py` | Monotonic and browser-synchronized clock |
| `firmware/clonker/logger.py` | Serial logging |

## Design constraints

GPIO sampling and device command responsiveness outrank HTTP management. Network work must be bounded; slow clients or devices must not stall control capture. `web.poll()` handles a limited unit of work per call; the main loop schedules it about every 10 ms when CONFIG is active. This is **not** a proven encoder-latency guarantee.

Wi-Fi management is trusted-LAN-only, not authenticated application security. Do not expose port 9090 to the internet. CircuitPython Web Workflow on port 80 is disabled in private `settings.toml` to avoid suspected socket conflicts.

## Reference documents

- [Operating Modes](OPERATING_MODES.md) — SERVICE (USB), DEVICE, CONFIG, RUN
- [Configuration & Recovery](CONFIGURATION.md) — active JSON v2 configuration, legacy XML v1, command model, validation, and backup safety 
- [Firmware & Network](FIRMWARE_NETWORK.md) — cooperative loop, HTTP, clock, logging
- [Hardware & Controls](HARDWARE_CONTROLS.md) — physical design and action model
- [Development & Deployment](DEVELOPMENT.md) — iPad/Windows/Pico workflow and test plan
- [Terminology Audit](TERMINOLOGY_AUDIT.md) — existing USB-mode references to update

---

### Active Configuration in RAM — Existing Implementation

**Status:** IMPLEMENTED IN JSON v2 — ACTION DISPATCH NOT YET TESTED

The existing `device_config_v2.py` module already maintains
one authoritative, validated configuration snapshot in RAM
through its private `_current` dictionary.

No additional key-value table, configuration cache, or
synchronization manager is required for V1.

Existing behavior:

- `load()` initializes the active configuration at startup.
- `current()` returns a validated copy of the active configuration.
- `room(room_id)` returns the requested room configuration.
- `save()` validates and persists changes before publishing
  the new configuration into `_current`.
- A failed save does not publish the proposed configuration.
- A successful no-change save leaves the existing configuration intact.

The future dispatcher should use `room()` or `current()`
when resolving actions rather than retaining the startup
configuration reference from `main.py`.

This allows a successful browser configuration save to become
available to subsequent action lookups without restarting
the Pico or reloading the JSON file.

CONFIG-to-RUN transitions do not require a configuration reload.
The active configuration remains in RAM when the management
HTTP service is stopped.

Manual filesystem changes outside the configuration engine
are not automatically detected or adopted.

For V1, retain the existing validated-copy behavior.
Optimize configuration lookup performance only if actual
encoder testing demonstrates a need.

Do not modify the existing JSON v2 persistence engine
solely to support action dispatch.

### CONFIG/RUN Development and Testing

The JSON v2 browser editor will be used to configure real
device IP addresses and HTTP commands before action testing.

Initial action testing should run with CONFIG mode disabled
to eliminate the management HTTP listener and its polling
overhead.

RUN mode must retain the loaded JSON v2 configuration and
support outbound device commands without the management
HTTP server running.

The CONFIG/RUN switch is currently simulated in firmware.
A temporary development mechanism may be used to select
RUN mode until the physical switch is implemented.

Initial testing should verify:

- JSON v2 configuration survives the CONFIG-to-RUN transition.
- Outbound HTTP commands work with CONFIG mode disabled.
- Management HTTP polling stops in RUN mode.
- Wi-Fi remains available for outbound commands.
- Physical input responsiveness is evaluated without
  management HTTP polling overhead.

Later, CONFIG-enabled and RUN-only responsiveness may be
compared if useful.

### Design Evolution

This section records the initial V1 implementation strategy,
not a permanent architectural requirement.

As hardware testing reveals actual behavior, the design
may be revised, simplified, or completely replaced.

Git history preserves earlier decisions; current documentation
should describe the best-known design rather than retain
obsolete implementation assumptions.

## Action Dispatch and Outbound HTTP — V1 Design Decisions

**Design agreed:** October 17, 2026  
**Status:** APPROVED DESIGN — NOT YET IMPLEMENTED

### Guiding Principle

Implement the simplest reliable action execution path first.

Do not introduce event accumulation, acceleration, sophisticated
queueing, persistent TCP connections, or other optimizations
until actual hardware testing demonstrates a need.

The initial goal is to make physical controls operate real AV
devices through the existing JSON v2 configuration system.

### Basic Action Pipeline

All physical controls will generate generic action events.

The action execution path is:

1. Physical control generates an event.
2. Event identifies a generic action.
3. Dispatcher resolves the selected room.
4. Dispatcher looks up the action in JSON v2 configuration.
5. Outbound transport sends the configured HTTP command.
6. Transport releases the request's network resources.
7. Main loop continues processing controls.

The physical control modules must not know device IP addresses,
HTTP methods, URL paths, or device-specific protocols.

Those details belong to configuration, dispatch, and transport.

### Shared Network Resources

The outbound HTTP implementation should use shared networking
resources rather than independently initializing networking
for every action.

Initial design:

- Wi-Fi connectivity is initialized and managed centrally.
- A socket pool is created once and reused while valid.
- Action execution uses a common outbound transport module.
- Each HTTP request may open and close its own TCP connection.
- Persistent TCP connection caching is NOT required for V1.
- Failed requests must release resources.
- Network operations must have bounded timeouts.
- Subsequent actions should remain possible after failures.

The existing `web.py` is an inbound HTTP management server.
Outbound AV commands are a separate responsibility.

These components may share the Wi-Fi radio but should not
share active client-connection state.

### Buttons and Encoders

For the initial implementation, all controls use the same
basic action execution mechanism.

Examples:

- Button press -> `select`
- Button press -> `mute-toggle`
- Button press -> `home`
- Volume encoder clockwise detent -> `volume-up`
- Volume encoder counterclockwise detent -> `volume-down`

Each generated action initially results in one configured
HTTP request.

Volume events do not receive special treatment in V1.

This deliberately allows the volume encoder implementation
to be replaced or optimized later without changing the
basic HTTP transport or JSON v2 action mappings.

### Volume Encoder — Initial Behavior

The Grayhill volume encoder is a relative control, not an
absolute positional volume control.

For V1:

- One recognized detent generates one volume action.
- No accumulation of pending volume movement.
- No acceleration based on rotation speed.
- No command batching.
- No persistent TCP connection optimization.
- No special volume retry or replay mechanism.
- No separate volume-specific networking implementation.

The first goal is to observe real responsiveness and
behavior when controlling the Denon receiver.

A small amount of lag during network trouble is acceptable.

If network communication fails, failed volume commands
do not need to be replayed after connectivity returns.
The next physical movement can generate fresh actions.

The controlled receiver remains the authority for
its actual volume level.

### Future Optimization — Only If Needed

Potential future improvements include:

- Small bounded event queues.
- Encoder movement accumulation.
- Rotation-speed-based volume acceleration.
- Command batching where supported by a device.
- Outbound HTTP connection reuse.
- Improved scheduling under network congestion.

Accumulation and acceleration are separate concepts and
do not have to be implemented together.

These are possibilities, not V1 requirements.

Do not add complexity without observing an actual problem
or identifying a clear user-experience improvement.

### Implementation Order

1. Implement one manually triggered JSON v2 action.
2. Verify one real HTTP command reaches the Denon AVR.
3. Establish shared outbound networking infrastructure.
4. Implement a physical pushbutton action.
5. Implement basic button debounce.
6. Implement the Grayhill volume encoder using repeated
   ordinary `volume-up` and `volume-down` actions.
7. Observe rapid rotation, latency, and error behavior.
8. Consider optimizations only after testing.

### Architectural Boundary

Keep these responsibilities separate:

- `controls/` — read physical inputs and generate events.
- Dispatcher — resolve room and configured action.
- Outbound transport — perform HTTP requests and handle
  networking resources and errors.
- `device_config_v2.py` — configuration validation,
  persistence, and action mappings.
- `web.py` — inbound CONFIG-mode HTTP management.

Module names and exact interfaces for the dispatcher and
outbound transport remain to be determined during
implementation.

Avoid unnecessary frameworks, class hierarchies, and
general-purpose abstractions.

**V1 rule: One control event, one generic action,
one configured HTTP request.**

CLONK!

---

## Fundamental Toggle Actions — V1 Design

**Design agreed:** October 18, 2026  
**Status:** APPROVED DESIGN — NOT YET IMPLEMENTED

### Scope

The fourteen fundamental action IDs remain unchanged.

Twelve actions use a single configured HTTP command.

Two actions use paired ON/OFF commands:

- `power-toggle`
- `mute-toggle`

Each toggle action has one target device, one HTTP method,
and two paths: `on_path` and `off_path`.

These paths may be identical when the device implements
native toggle behavior.

### RAM State

The dispatcher will maintain independent toggle history
for each room and each toggle action.

Conceptually:

```text
room-1:
    power-toggle: unknown
    mute-toggle: unknown

room-2:
    power-toggle: unknown
    mute-toggle: unknown

room-3:
    power-toggle: unknown
    mute-toggle: unknown
```

This state is initialized at boot and never written to flash.

The first press selects ON.

Subsequent successful presses alternate ON and OFF.

A missing endpoint, blank selected path, or failed request
does not advance the remembered direction.

A successful HTTP response permits advancing the direction,
although HTTP success does not guarantee device-state change.

### Dispatcher Behavior

Ordinary action:

```text
Control event
    -> Resolve room and action
    -> Resolve target endpoint
    -> Send configured HTTP request
```

Toggle action:

```text
Control event
    -> Resolve room and toggle action
    -> Determine next ON/OFF direction from RAM
    -> Select on_path or off_path
    -> Resolve target endpoint
    -> Send configured HTTP request
    -> On success, remember selected direction
```

Only the dispatcher needs to understand the distinction
between ordinary and toggle actions.

The outbound HTTP transport should not maintain toggle
state or contain device-specific power logic.

Physical controls continue to generate generic action IDs.

### Native Toggle Commands

If `on_path` and `off_path` are identical, the same
command is sent on every press.

This supports devices that already provide a native
toggle operation without introducing another action type.

### No State Queries for V1

V1 deliberately does not query actual equipment power
or mute state before choosing a command.

External remotes, HDMI-CEC, and other applications may
change device state without Clonker knowing.

The user may need to press the toggle again to recover
from a mismatch.

This is an accepted V1 limitation.

### Future Device Adapters

Device-specific adapters may eventually implement
state-aware toggles, authenticated protocols, or command
sequences.

Such adapters must preserve the generic action interface.

Do not introduce these features until real device testing
demonstrates a need.

### Updated Action Execution Rule

For ordinary actions:

**One event -> one action -> one HTTP request.**

For V1 toggle actions:

**One event -> choose one ON/OFF path -> one HTTP request.**

The existing simple outbound transport design remains valid.

### Configuration Performance

`device_config_v2.py` already maintains the active
configuration in RAM through `_current`.

The dispatcher must use the current active configuration,
not a stale startup copy.

A small direct read-only action lookup may be added for
frequently generated events such as volume encoder detents.

Such a lookup should return immutable configuration values
without copying or revalidating the entire configuration.

This is an optimization of access to existing RAM data,
not a second configuration cache.

### Scope Discipline

No general-purpose macros, sequence engine, state-query
parser, retry queue, or device-specific power framework
is required for V1.

First make the simple controls work reliably.

Then let actual testing tell us what needs improvement.

CLONK!
