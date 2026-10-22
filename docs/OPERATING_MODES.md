# The Clonker 10000 — Operating Modes

**Design reference:** Updated October 19, 2026  
**Hardware:** Raspberry Pi Pico 2 W  
**Runtime:** CircuitPython 10.3.1  
**Status:** SERVICE/DEVICE filesystem selection implemented and tested; CONFIG/RUN application logic implemented with simulated switch; physical CONFIG/RUN switch pending.

> **Two switches. Two completely different jobs. One appropriately complicated monster.**

## 1. Overview

The Clonker 10000 has two independent operating-mode dimensions:

1. **SERVICE (USB) / DEVICE** — determines who can write the CircuitPython filesystem.
2. **CONFIG / RUN** — determines whether the application management HTTP interface is available.

These modes serve different purposes and must not be confused.

SERVICE/DEVICE is a boot-time maintenance selection.

CONFIG/RUN is an application-level operating selection intended to change during normal runtime.

Neither mode directly controls the power state of a television, receiver, or streaming device.

### Mode comparison

| Property | SERVICE (USB) / DEVICE | CONFIG / RUN |
|---|---|---|
| Purpose | Filesystem write ownership | Management interface availability |
| Audience | Developer / maintenance | End user |
| Control | Internal GP17 jumper | Future external maintained switch |
| Evaluated by | `boot.py` | `main.py` |
| When evaluated | At boot | Continuously during runtime |
| Reboot required | Yes, full power cycle | No, by design |
| Implemented | Yes | Logic implemented; switch simulated |
| Physical control tested | Yes, GP17 jumper | No |
| Changes AV equipment state | No | No |

The intended normal operating combination is **DEVICE + RUN**.

The intended browser configuration combination is **DEVICE + CONFIG**.

## 2. SERVICE (USB) Mode

**Status:** Implemented and tested.

SERVICE mode is selected when the GP17 jumper is open during boot.

`boot.py` configures GP17 as an input with an internal pull-up resistor.

With the jumper open, GP17 reads HIGH.

The boot message is:

```text
CLONKER BOOT: SERVICE (USB) mode (jumper OPEN)
```

### Filesystem behavior

In SERVICE mode:

- The USB host can write the CIRCUITPY filesystem.
- The Pico application sees the filesystem as read-only.
- Firmware files can be deployed from the host computer.
- Configuration files can be copied or replaced from the host.
- The Pico cannot persist browser configuration changes.
- USB serial and REPL access remain available.

This is the preferred mode for firmware deployment and maintenance.

### Browser behavior in SERVICE + CONFIG

The management interface can still run while the filesystem is read-only.

The browser can:

- Open the configuration page.
- Read the active JSON v2 configuration.
- Inspect room and action mappings.
- View clock status.
- Synchronize the RAM clock.
- Open the browser Test Remote.
- Submit configured actions to the shared dispatcher and outbound execution queue.

However, attempting to save configuration through `POST /api/config` is rejected with HTTP 403.

The HTTP server checks actual filesystem writability rather than assuming that CONFIG implies write permission.

### Important distinction

SERVICE does not mean the application must stop running.

It means the USB host owns filesystem writes.

The application can continue operating with its loaded configuration, subject to the capabilities currently implemented.

## 3. DEVICE Mode

**Status:** Implemented and tested.

DEVICE mode is selected when GP17 is connected to GND during boot.

On the current Pico 2 W:

- GP17 is physical pin 22.
- The adjacent GND connection used for the jumper is physical pin 23.

With the jumper grounded, GP17 reads LOW.

The boot message is:

```text
CLONKER BOOT: DEVICE mode (jumper GROUNDED)
```

`boot.py` executes:

```python
storage.remount("/", readonly=False)
```

### Filesystem behavior

In DEVICE mode:

- The Pico application can write its filesystem.
- The USB host sees CIRCUITPY as read-only.
- The browser configuration engine can persist valid changes.
- Configuration backups can be rotated.
- The active configuration can be updated in RAM after successful persistence.
- USB serial and REPL access remain available.

DEVICE mode is the intended normal operating filesystem mode.

### Browser behavior in DEVICE + CONFIG

This is the combination used for browser configuration editing.

The user can:

- Edit room names.
- Configure TV, AVR, and streaming endpoints.
- Edit the fourteen fundamental actions per room.
- Save valid JSON v2 configuration.
- Receive stale-revision protection.
- Exercise the browser Test Remote.
- Synchronize the clock.

Configuration saves use the safeguards documented in [Configuration & Recovery](CONFIGURATION.md).

### DEVICE does not mean RUN

DEVICE only determines filesystem ownership.

It does not disable the browser management interface.

A Pico can be in DEVICE mode while CONFIG is active.

This distinction is essential to the current development workflow.

## 4. Changing SERVICE / DEVICE

SERVICE/DEVICE selection is made by `firmware/boot.py`.

The relevant logic is:

```python
jumper = digitalio.DigitalInOut(board.GP17)
jumper.direction = digitalio.Direction.INPUT
jumper.pull = digitalio.Pull.UP

if jumper.value:
    print("CLONKER BOOT: SERVICE (USB) mode (jumper OPEN)")
else:
    print("CLONKER BOOT: DEVICE mode (jumper GROUNDED)")
    storage.remount("/", readonly=False)

jumper.deinit()
```

The jumper is read during boot and then released.

Changing its position while the application is running does not change filesystem ownership.

### Required procedure

1. Disconnect Pico power.
2. Set the GP17 jumper to the desired position.
3. Reconnect power.
4. Confirm the boot message.
5. Verify expected filesystem ownership before editing or saving files.

A full power cycle is required.

A soft reload, including Ctrl+D from the REPL, must not be relied upon to apply a new jumper selection.

Do not change the jumper while the Pico is powered.

## 5. CONFIG Mode

**Status:** Application logic implemented; switch currently simulated.

CONFIG mode enables Clonker's application management HTTP server.

The server listens on port 9090.

Current development address:

`http://192.168.50.12:9090/`

Browser Test Remote:

`http://192.168.50.12:9090/remote.html`

### CONFIG services

When CONFIG is enabled, the application provides:

- Browser configuration editor.
- JSON v2 configuration inspection.
- Revision-aware configuration saving when the filesystem is writable.
- System clock status.
- Browser UTC clock synchronization.
- Browser Test Remote.
- Fundamental action dispatch through the shared queue and outbound HTTP transport.

The browser Test Remote submits actions to the shared Dumb Queue.
Ordinary configured actions can execute real outbound HTTP
commands. Power and mute toggles remain deferred until runtime
direction selection is implemented.

### Current simulated switch

The implementation is in:

`firmware/clonker/controls/switches.py`

Current behavior:

```python
_simulated_config = True


def config_enabled():
    if pins.CONFIG_SWITCH_PIN is None:
        return _simulated_config

    raise NotImplementedError("CONFIG GPIO not implemented")
```

`CONFIG_SWITCH_PIN` is currently `None` in `controls/pins.py`.

Therefore, the normal startup behavior is CONFIG enabled.

A development helper also exists:

```python
switches.set_simulated_config(enabled)
```

This changes the simulated state in RAM.

It is not a browser-facing operating-mode control and is not connected to physical hardware.

### Listener lifecycle

`main.py` checks `switches.config_enabled()` during each main-loop iteration.

When CONFIG becomes enabled, it calls:

```python
web.start()
```

When CONFIG becomes disabled, it calls:

```python
web.stop()
```

The listener is started or stopped on transitions rather than recreated on every loop iteration.

While CONFIG is enabled, `web.poll()` is scheduled approximately every 10 milliseconds.

This interval is not a guaranteed HTTP response time.

## 6. RUN Mode

**Status:** Listener transition logic implemented; physical switch and real equipment-control operation pending.

RUN is intended to be Clonker's normal remote-control mode.

When RUN is selected:

- The management HTTP listener is stopped.
- The configuration editor is unavailable.
- The browser Test Remote is unavailable.
- Wi-Fi remains available for future outbound equipment commands.
- The validated configuration remains in RAM.
- Physical inputs should continue producing generic actions.
- Outbound HTTP device commands should remain operational.

### Current implementation

The application already contains the transition logic:

```python
elif not config_mode and web_running:
    web.stop()
    web_running = False
    logger.info("RUN mode enabled")
```

However, the current firmware does not yet implement physical button or encoder input processing.

It also does not yet implement outbound HTTP commands to AV equipment.

Therefore, RUN-mode remote-control functionality is **design intent**, not a completed end-to-end feature.

### No configuration reload required

CONFIG/RUN transitions should not reload the configuration file.

The application should continue using the validated in-memory configuration.

Successful browser saves already publish updated configuration into that state.

The future RUN implementation should preserve this behavior.

### Physical controls in either mode

The eventual physical remote should continue accepting normal control input in both CONFIG and RUN modes.

CONFIG enables additional management services; it should not turn off the remote's core control capabilities.

This requirement has not yet been hardware-tested.

## 7. The Four Mode Combinations

The two dimensions produce four possible combinations.

| Filesystem mode | Application mode | Intended behavior |
|---|---|---|
| SERVICE (USB) | CONFIG | Host firmware maintenance; browser inspection and testing; no browser config saves |
| SERVICE (USB) | RUN | Host owns filesystem; management server off; future physical control may operate |
| DEVICE | CONFIG | Browser configuration, persistence, clock, and Test Remote |
| DEVICE | RUN | Normal remote operation; management server off |

### SERVICE + CONFIG

Useful during development.

The USB host can update firmware.

The browser can inspect configuration and exercise the logging stub.

Browser configuration writes are rejected because the Pico filesystem is read-only.

### SERVICE + RUN

A possible maintenance or diagnostic combination.

The host retains filesystem write ownership.

The management listener is disabled.

Future physical controls may operate using the configuration already loaded in RAM.

This combination is not yet verified for actual AV control.

### DEVICE + CONFIG

The currently established browser configuration workflow.

The Pico owns filesystem writes.

The management interface is available.

Valid browser configuration changes can be saved and activated.

This is the combination used for JSON v2 persistence testing.

### DEVICE + RUN

The intended normal end-user combination.

The Pico owns filesystem writes.

The management listener is disabled.

Physical controls and outbound AV commands will eventually operate without requiring browser management services.

This is the target operating arrangement, not a completed hardware milestone.

## 8. Configuration Saving Rules

Persistent configuration saves require both:

1. A writable Pico filesystem.
2. An available CONFIG management endpoint.

The normal combination is DEVICE + CONFIG.

### SERVICE + CONFIG

`POST /api/config` returns HTTP 403 because the filesystem is read-only.

### DEVICE + CONFIG

The save may proceed if:

- The submitted configuration is valid.
- The expected revision matches.
- The primary file passes consistency checks.
- The save path matches the loaded configuration path.
- Persistence succeeds.

Successful changed saves update the primary file, rotate backups, and publish the new configuration into RAM.

Unchanged saves avoid unnecessary flash writes.

### RUN mode

The browser configuration endpoint is unavailable because the management HTTP listener is stopped.

RUN is not a separate permission to write or deny writes.

Filesystem ownership remains determined by SERVICE/DEVICE.

See [Configuration & Recovery](CONFIGURATION.md) for persistence and recovery details.

## 9. CONFIG/RUN Is Not System Power

The physical CONFIG/RUN switch is an internal application control.

Moving it must not issue a power command to any television, receiver, or streaming device.

Clonker also defines a separate fundamental action:

`power-toggle`

This action is intended for a physical momentary control.

Its configuration contains:

- `target`
- `method`
- `on_path`
- `off_path`

The ON/OFF fields are implemented in JSON v2.

Actual command execution and RAM toggle history are not yet implemented.

### Future guarded controls

The hardware concept includes a prominent guarded system-power control.

That is separate from the CONFIG/RUN switch and the GP17 maintenance jumper.

The final physical arrangement is still under development.

The application operating-mode switch must never be mistaken for the external equipment power control.

## 10. Hardware Integration Plan

The current pin definitions are in:

`firmware/clonker/controls/pins.py`

Relevant placeholders:

```python
CONFIG_SWITCH_PIN = None
ROOM_SELECTOR_A_PIN = None
ROOM_SELECTOR_B_PIN = None

VOLUME_ENCODER_A_PIN = None
VOLUME_ENCODER_B_PIN = None

SELECT_ENCODER_A_PIN = None
SELECT_ENCODER_B_PIN = None
```

These pins are not assigned yet.

### CONFIG/RUN switch requirements

The future physical switch should:

- Be a maintained two-position control.
- Be readable by the Pico at runtime.
- Have a defined electrical default state.
- Use appropriate debounce or stable-state detection.
- Avoid interfering with GP17 filesystem ownership.
- Start or stop the management listener only when the state changes.
- Leave active configuration in RAM.
- Avoid generating an AV equipment command.

The final GPIO pin and electrical implementation remain undecided.

### Room selector

The proposed physical room selector is a separate control.

It may select Den, Both, or Sunroom, subject to the final hardware design.

The meaning of Both and any group-command behavior remain to be finalized.

Room selection is not an operating-mode dimension.

### Power button

The proposed guarded momentary power button will emit the `power-toggle` fundamental action.

It is not a substitute for the CONFIG/RUN switch.

See [Hardware & Controls](HARDWARE_CONTROLS.md).

## 11. Deployment and Recovery Cautions

### Before changing filesystem ownership

- Save and close host-side file edits.
- Disconnect power.
- Move the GP17 jumper.
- Reconnect power.
- Confirm the boot message.
- Verify the expected read/write ownership.

### During browser configuration

- Use DEVICE + CONFIG for persistent saves.
- Confirm the current configuration revision.
- Refresh stale browser tabs before retrying a save.
- Do not manually modify the primary JSON file while assuming the running application will automatically reload it.
- Preserve external backups before deliberate schema or deployment changes.

### Private runtime settings

Keep `settings.toml` out of Git.

It contains environment-specific Wi-Fi and runtime settings.

### CircuitPython Web Workflow

CircuitPython Web Workflow is distinct from Clonker's management server.

It is currently disabled using:

```toml
CIRCUITPY_WEB_API_PORT = 0
```

This was adopted because of suspected socket conflicts.

Clonker's own management service uses port 9090.

### Trusted LAN only

The management server has no application authentication.

Do not expose it through router port forwarding.

## 12. Verification Status — October 19, 2026

> **Historical snapshot:** This section preserves the
> October 19 verification status. Outbound HTTP execution
> was subsequently implemented and verified on October 21.
> See [Firmware, HTTP & Clock](FIRMWARE_NETWORK.md) for
> current networking status.

### Implemented and tested

- GP17 boot-time SERVICE/DEVICE selection.
- SERVICE host-writable filesystem behavior.
- DEVICE Pico-writable filesystem behavior.
- DEVICE-mode browser configuration saves.
- SERVICE-mode rejection of browser configuration writes.
- JSON v2 revision protection and selected backup behavior.
- CONFIG-enabled browser management service.
- Browser Test Remote logging-only action dispatch.

### Implemented but not fully exercised

- Runtime CONFIG-to-RUN and RUN-to-CONFIG listener transitions using the simulated switch.
- HTTP listener cleanup under all network failure conditions.
- Configuration availability through every possible mode transition.

### Not yet implemented

- Physical CONFIG/RUN switch.
- GPIO-based mode detection and debounce.
- Physical room selector.
- Physical power button.
- Physical volume and selector encoders.
- Real outbound AV device commands.
- End-to-end DEVICE + RUN remote operation.

## 13. Reference Documents

- [Architecture](ARCHITECTURE.md) — overall system architecture and action dispatcher.
- [Configuration & Recovery](CONFIGURATION.md) — JSON v2 schema and persistence.
- [Firmware, HTTP & Clock](FIRMWARE_NETWORK.md) — main loop, management HTTP, and clock.
- [Hardware & Controls](HARDWARE_CONTROLS.md) — physical control design.
- [Development & Deployment](DEVELOPMENT.md) — firmware deployment workflow.
- [Development History](DEVELOPMENT_HISTORY.md) - development milestones.
- [Chapter 2 Handoff](CHAPTER_2_HANDOFF.md) — current milestone and next phase.

---

**CLONK! ⚡🔩**
