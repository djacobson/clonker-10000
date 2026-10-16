# Configuration, Persistence & Recovery

**Design reference:** October 16, 2026  
**Hardware:** Raspberry Pi Pico 2 W  
**Runtime:** CircuitPython 10.3.1  
**Status:** Configuration v1 operational; Configuration v2 JSON design approved, implementation pending.

## 1. Overview

The Clonker 10000 uses a persistent configuration file to define rooms, devices, and remote-control actions.

Configuration v1 uses XML and has been successfully tested on real hardware.

Configuration v2 will use JSON to simplify CircuitPython parsing, validation, serialization, and browser integration.

The transition to JSON is primarily an architectural simplification, not a storage optimization.

The existing revision checking, verified writes, backup rotation, and recovery protections must be preserved.

## 2. Configuration v1 — Verified Implementation

Current configuration file:

`/clonker/device_config.xml`

Current firmware module:

`/clonker/device_config.py`

Configuration v1 supports:

- Three fixed rooms: `room-1`, `room-2`, `room-3`.
- Editable room names.
- Optional TV and AVR IPv4 addresses.
- A `volume_device` preference selecting TV or AVR.
- Browser configuration editing.
- Persistent configuration saves.
- Configuration revision checking.
- Detection of unchanged configurations.
- Verified temporary file writes.
- Backup rotation.
- Configuration reload into active memory.
- Persistence across reboot.

These capabilities were successfully tested on the Raspberry Pi Pico 2 W on October 16, 2026.

See [Configuration Test Record](configuration-testing.md).

### Browser API

| Request | Behavior |
|---|---|
| `GET /api/config` | Returns configuration, revision, and filesystem writability |
| `POST /api/config` in DEVICE mode | Validates and persists configuration |
| `POST /api/config` in SERVICE (USB) mode | Rejects writes with HTTP 403 |
| `GET /` | Serves browser configuration interface |

The POST handler calls `device_config.save()`.

Successful saves update the active in-memory configuration after persistence has been verified.

## 3. Existing Persistence and Recovery Protections

Configuration v2 must preserve the established protections.

### Revision Checking

Each configuration has a revision derived from its serialized contents.

The browser submits the revision associated with the configuration it originally loaded.

The firmware rejects stale submissions.

Before saving, the firmware also checks that the primary configuration on disk matches the active configuration.

### Verified Writes

The save process:

1. Validates the submitted configuration.
2. Checks the expected revision.
3. Verifies the existing primary configuration.
4. Detects unchanged configurations and avoids unnecessary flash writes.
5. Serializes the validated configuration.
6. Writes a temporary file.
7. Flushes the temporary file.
8. Reopens and verifies its contents.
9. Rotates existing backups.
10. Installs the verified replacement.
11. Reads back and verifies the installed configuration.
12. Publishes the new configuration to active memory.

### Backup Rotation

The configuration maintains three generations:

| File | Purpose |
|---|---|
| `device_config.json` | Current primary configuration |
| `device_config.json.bak` | Previous configuration |
| `device_config.json.bak.old` | Older configuration |

The filenames above describe the planned v2 format. Configuration v1 currently uses the equivalent XML filenames.

The oldest backup is rolling, not permanent.

### Startup Recovery

On startup, the loader attempts:

1. Primary configuration.
2. `.bak`.
3. `.bak.old`.

Only successfully parsed and validated configurations may be loaded.

Loading a backup into memory does not automatically restore the primary file.

An explicit recovery operation may restore a validated backup when the primary is missing and the filesystem is writable.

### Limitations

The multi-step rename sequence is not a fully atomic transaction.

An unexpected power loss can interrupt the replacement process.

The existing protections reduce risk but do not guarantee power-loss durability.

Configuration v2 must not weaken these protections.

## 4. Configuration v2 — JSON Architecture

### Design Decision

Configuration v2 will replace XML with JSON.

Reasons:

- CircuitPython provides built-in JSON parsing and serialization.
- JavaScript supports JSON natively.
- Python dictionaries and browser objects can share the same configuration structure.
- Custom XML parsing and escaping can be eliminated.
- Strict structural validation can be implemented independently of parsing.
- Future macros and command sequences fit naturally into JSON arrays and objects.
- Compact JSON can reduce configuration file size.

Configuration v2 is a coordinated format change.

No complex v1-to-v2 migration framework is required at this early development stage.

### File Location

`/clonker/device_config.json`

### Schema Version

The root configuration object contains:

- `version`: integer `2`.
- `rooms`: object containing exactly three fixed rooms.

## 5. Room Structure

Exactly three rooms are required:

- `room-1`
- `room-2`
- `room-3`

Room IDs are fixed and cannot be renamed or removed.

Each room contains exactly:

- `name`
- `devices`
- `actions`
- `custom_actions`

### Room Name

Room names are editable strings between 1 and 40 characters.

### Device Endpoints

Each room contains exactly three device endpoint fields:

- `tv`
- `avr`
- `streaming`

Each field contains an IPv4 address or an empty string.

Empty addresses are valid.

An empty address means that device endpoint is not configured.

Device addresses are independent of action assignments.

## 6. Fundamental Actions

Each room contains exactly fourteen fundamental actions.

| Action ID | Purpose |
|---|---|
| `volume-up` | Increase volume |
| `volume-down` | Decrease volume |
| `mute-toggle` | Toggle mute |
| `nav-up` | Navigate up |
| `nav-down` | Navigate down |
| `nav-left` | Navigate left |
| `nav-right` | Navigate right |
| `select` | Select / OK |
| `back` | Navigate back |
| `home` | Return home |
| `play-pause` | Toggle playback |
| `skip-back` | Skip backward |
| `skip-forward` | Skip forward |
| `power-toggle` | Toggle device power |

Fundamental action IDs are developer-defined and fixed.

They cannot be renamed, deleted, or duplicated.

Unknown action IDs are rejected.

Missing fundamental actions are rejected.

Channel Up, Channel Down, and Guide are not fundamental actions.

### Action Properties

Each action contains exactly three editable properties:

- `target`
- `method`
- `path`

#### Target

Allowed values:

- `tv`
- `avr`
- `streaming`

The target identifies which device endpoint receives the command.

Targets are independent of action IDs.

For example, Volume Up may target either a TV or an AVR.

#### HTTP Method

Allowed values:

- `GET`
- `POST`

#### Command Path

The command path is an editable string.

Empty command paths are valid.

An empty command path disables command execution for that action.

A configured command path cannot execute unless the selected target also has a configured IP address.

Maximum path length will be defined by a centralized constant in `device_config.py`.

Command-path syntax and escaping requirements must be finalized before HTTP command execution is implemented.

## 7. JSON Configuration Example

The following illustrates one room. A complete configuration must contain all three rooms with the same fourteen fundamental action IDs.

```json
{
  "version": 2,
  "rooms": {
    "room-1": {
      "name": "Den",
      "devices": {
        "tv": "",
        "avr": "",
        "streaming": ""
      },
      "actions": {
        "volume-up": {
          "target": "avr",
          "method": "GET",
          "path": ""
        },
        "volume-down": {
          "target": "avr",
          "method": "GET",
          "path": ""
        },
        "mute-toggle": {
          "target": "avr",
          "method": "GET",
          "path": ""
        },
        "nav-up": {
          "target": "streaming",
          "method": "GET",
          "path": ""
        },
        "nav-down": {
          "target": "streaming",
          "method": "GET",
          "path": ""
        },
        "nav-left": {
          "target": "streaming",
          "method": "GET",
          "path": ""
        },
        "nav-right": {
          "target": "streaming",
          "method": "GET",
          "path": ""
        },
        "select": {
          "target": "streaming",
          "method": "GET",
          "path": ""
        },
        "back": {
          "target": "streaming",
          "method": "GET",
          "path": ""
        },
        "home": {
          "target": "streaming",
          "method": "GET",
          "path": ""
        },
        "play-pause": {
          "target": "streaming",
          "method": "GET",
          "path": ""
        },
        "skip-back": {
          "target": "streaming",
          "method": "GET",
          "path": ""
        },
        "skip-forward": {
          "target": "streaming",
          "method": "GET",
          "path": ""
        },
        "power-toggle": {
          "target": "tv",
          "method": "GET",
          "path": ""
        }
      },
      "custom_actions": []
    }
  }
}
```

The example is intentionally incomplete and must not be deployed as the active configuration.

The complete file will contain `room-1`, `room-2`, and `room-3`.


## 8. Reserved User-Defined Commands

Each room contains:

```json
"custom_actions": []
```

Configuration v2 requires this array to remain empty until user-defined commands are implemented.

Fundamental commands have fixed developer-defined identities. User-defined commands will have user-supplied identities and names.

Both categories are intended to remain simple. The basic command model is an HTTP target, method, and path.

We are not building a scripting language, automation programming environment, or graphical shortcut editor.

Compound commands or sequencing may be considered later if a practical use case justifies them. They are not requirements of the initial command model.

The initial v2 validator rejects nonempty `custom_actions` arrays.

## 9. Physical Control Separation

The guarded physical switch controls the Clonker's internal CONFIG/RUN operating mode.

It does not execute an HTTP power command.

The separate `power-toggle` fundamental action will be assigned to a physical momentary pushbutton.

The CONFIG/RUN switch and Power Toggle action must remain logically independent.

SERVICE (USB) / DEVICE filesystem ownership remains a separate operating-mode dimension.

## 10. Strict Validation

Configuration v2 will enforce structural validation after JSON parsing.

Validation must reject:

- Incorrect schema versions.
- Missing or extra room IDs.
- Missing or unknown room properties.
- Invalid room names.
- Missing or extra device endpoints.
- Invalid nonblank IPv4 addresses.
- Missing fundamental actions.
- Unknown fundamental action IDs.
- Incorrect action property names.
- Invalid targets.
- Invalid HTTP methods.
- Non-string command paths.
- Command paths exceeding the configured maximum.
- Nonempty custom action arrays.
- Unexpected data types.
- Configuration files exceeding the configured byte limit.

JSON parsing alone does not provide these guarantees.

In particular, standard `json.loads()` does not reject duplicate object keys.

Duplicate-key handling must be explicitly resolved during implementation if strict rejection is required.

Validation should be practical and proportional to the application. Normal users configure Clonker through the browser; direct JSON editing is primarily a developer activity. Validate the structure and values needed for safe, predictable operation without attempting to detect every conceivable hand-edited JSON discrepancy.

Standard JSON parsing is sufficient for the initial implementation. A custom duplicate-key parser is not required.

### Configuration Limits

Centralized limits will be defined in `device_config.py`.

These include:

- Maximum serialized configuration bytes.
- Maximum command path length.
- Room name length.
- Fixed room and action definitions.

The HTTP request limit remains independently configurable in `web.py`.

The current `MAX_REQUEST_BYTES = 2048` is insufficient for the proposed full three-room configuration and must be increased based on measured request sizes.

Incoming requests must be bounded before parsing.

## 11. Serialization and Revisions

JSON serialization must be deterministic.

The firmware should use:

- Stable room ordering.
- Stable action ordering.
- Compact JSON formatting.
- UTF-8 encoding.
- Consistent representation of values.

Deterministic serialization supports:

- Stable revision hashes.
- Reliable no-change detection.
- Repeatable file comparisons.
- Verified persistence.

Revision identifiers are derived from canonical serialized configuration contents.

Browser-only metadata such as `revision` and `filesystem_writable` must not be persisted inside the configuration file.

## 12. XML Versus JSON Comparison

A representative complete configuration with three rooms, fourteen actions per room, blank device addresses, and blank command paths was compared using different serialization styles.

| Representation | UTF-8 File Size |
|---|---:|
| Pretty-printed JSON | 5,338 bytes |
| Readable XML | 3,736 bytes |
| Compact JSON | 2,754 bytes |

These measurements describe representative v2 fixtures, not the existing v1 XML configuration.

Compact JSON is approximately 26% smaller than the compared XML representation.

Pretty-printed JSON can be larger than compact XML.

The principal reason for selecting JSON remains implementation simplicity and compatibility between CircuitPython and the browser.

## 13. Configuration v2 Implementation Plan

Development will proceed in small, testable steps.

### Phase 1 — Finalize Schema

- Approve JSON structure.
- Confirm all fourteen action IDs.
- Finalize validation rules.
- Define command path limits.
- Decide duplicate-key handling.
- Create a complete three-room JSON fixture.
- Verify serialized file sizes.

### Phase 2 — Implement JSON Configuration Engine

Update `firmware/clonker/device_config.py`.

Implement:

- JSON loading.
- Strict structural validation.
- Deterministic serialization.
- Revision calculation.
- No-change detection.
- Verified temporary writes.
- Backup rotation.
- Startup fallback.
- Explicit missing-primary recovery.

Preserve the proven v1 safety behavior.

### Phase 3 — Browser and HTTP Integration

Update:

- `firmware/clonker/web.py`
- `firmware/clonker/www/index.html`

Implement:

- Three-device room editing.
- Fourteen fundamental action editors per room.
- Target dropdowns.
- GET/POST method dropdowns.
- Editable command paths.
- JSON configuration submission.
- Revision checking.
- Save status and error reporting.
- Appropriate HTTP request size limits.

Firmware, browser, and configuration format must be upgraded together.

### Phase 4 — Validation and Testing

Test:

- Valid configuration loading.
- Invalid schema rejection.
- Missing and extra action rejection.
- Invalid target and method rejection.
- Blank device addresses.
- Blank command paths.
- Browser configuration editing.
- Successful saves.
- Unchanged configuration detection.
- Stale revision rejection.
- Backup rotation.
- Corrupt backup handling.
- Missing primary recovery.
- Persistence after reboot.
- SERVICE (USB) write rejection.
- DEVICE mode persistence.

Test host-side where practical before deploying to the Pico.

### Phase 5 — Controlled Deployment

1. Preserve an external backup of the working v1 XML configuration.
2. Preserve the working v1 firmware revision in Git.
3. Deploy matching v2 firmware, browser, and JSON configuration.
4. Verify startup loading.
5. Verify browser editing and saves.
6. Verify backup rotation.
7. Verify reboot persistence.
8. Confirm that v1 protections remain functional.

No automatic v1-to-v2 migration framework is required.

### Phase 6 — HTTP Command Execution

Actual device command execution is a separate future milestone.

The initial Configuration v2 milestone establishes the configuration data model, persistence, and browser editing.

It does not implement the action dispatcher or device HTTP command execution.

## 14. Design Principles

**Clonker controls actions, not brands.**

Fundamental action IDs describe what the user wants to accomplish.

The target, HTTP method, and command path describe how Clonker accomplishes that action.

No fixed assumption is made that volume requires an AVR or navigation requires a streaming device.

Physical operating-mode controls remain separate from device commands.

Configuration data must be strictly validated before persistence.

Proven recovery protections must be retained throughout development.

**Configuration v1 remains the operational baseline until Configuration v2 has been implemented and successfully tested.**
