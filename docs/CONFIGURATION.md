# Configuration, Persistence & Recovery

**Design reference:** October 16, 2026  
**Hardware:** Raspberry Pi Pico 2 W  
**Runtime:** CircuitPython 10.3.1  
**Status:** JSON v2 operational in firmware and browser; initial on-device tests passed; additional failure testing pending. XML v1 retained for rollback.

## 1. Overview

The Clonker 10000 uses a persistent configuration file to define
rooms, device endpoints, and remote-control actions.

**JSON v2 is the active configuration format.** The firmware loads
`/clonker/device_config.json` through
`firmware/clonker/device_config_v2.py`. The browser configuration
editor and management HTTP endpoints also use JSON v2.

The previous XML v1 implementation remains in the repository as a
rollback reference. The XML configuration engine is not used by the
active firmware or browser configuration endpoints.

The transition to JSON was primarily an architectural simplification,
not a storage optimization.

JSON v2 preserves revision checking, validated configuration data,
verified writes, backup rotation, and startup recovery safeguards.
Initial on-device tests have passed, but the complete failure and
power-loss test matrix is not finished.

See [Configuration Test Record](configuration-testing.md) for
observed test results.

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

The active JSON v2 HTTP server uses `MAX_REQUEST_BYTES = 10240`, with a separate maximum header size of 2,048 bytes. These limits accommodate the JSON v2 configuration editor while bounding incoming requests.

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

## Current JSON v2 Implementation Status — October 17, 2026

This section records the implemented configuration baseline.
Earlier sections preserve the design and implementation plan,
including historical references to work that was pending when
those sections were written.

### Active Files

| File | Purpose |
|---|---|
| `/clonker/device_config.json` | Active JSON v2 configuration on the Pico |
| `firmware/clonker/device_config_v2.py` | Active JSON validator, serializer, revision, persistence, and recovery engine |
| `firmware/clonker/web.py` | JSON v2 configuration HTTP endpoints |
| `firmware/clonker/www/index.html` | Browser JSON v2 configuration editor |
| `firmware/clonker/main.py` | Application startup and configuration loading |
| `firmware/clonker/device_config.py` | Legacy XML v1 engine retained for rollback |

### Implemented Configuration Model

- Schema version `2`.
- Exactly three rooms: `room-1`, `room-2`, and `room-3`.
- Editable room names, maximum 40 characters.
- Three optional IPv4 endpoints per room: `tv`, `avr`, and `streaming`.
- Fourteen fixed fundamental actions per room.
- Configurable action target, HTTP method (`GET` or `POST`),
  and command path.
- Maximum command path length of 512 characters.
- Empty IP addresses and command paths are valid.
- `custom_actions` is reserved and must remain an empty array.
- Maximum JSON configuration size of 8,192 UTF-8 bytes.

The initial production configuration includes a Den room, a
Sunroom, and a third room placeholder. Device addresses and
command paths may remain blank until device-command execution
is implemented.

### Validation and Serialization

The active engine validates the complete configuration structure,
including required and unknown fields, room identities, device
addresses, fundamental action identities, action properties,
and supported value types.

It creates a consistently ordered configuration representation
and compact JSON serialization. Revisions are calculated using
a deterministic 32-bit FNV-1a hash of canonical serialized data.

The browser receives the revision separately from the persisted
configuration. Browser-only metadata is not stored in the JSON file.

Standard JSON parsing is used. A custom duplicate-object-key
parser has not been implemented.

### Persistence and Recovery

The active JSON v2 engine implements:

1. Validation before persistence.
2. Expected-revision checking.
3. Verification that the primary file has not changed outside
   the active configuration engine.
4. Binding of saves to the configuration path selected by load.
5. No-change detection to avoid unnecessary flash writes.
6. Temporary-file writing, flushing, and read-back verification.
7. Rotation of `.bak` and `.bak.old` backups.
8. Installation and verification of the new primary file.
9. Publication of successfully saved configuration into memory.
10. Startup fallback to validated backups when the primary
    cannot be loaded.

Loading a backup does not silently overwrite or repair the
primary configuration.

The multi-file rename sequence is not fully atomic. These
protections reduce risk but do not guarantee durability through
an unexpected power interruption.

### Browser and HTTP Integration

The active browser provides room, device, and fundamental-action
editing through the management server on port 9090.

`GET /api/config` returns the current JSON v2 configuration,
revision, and filesystem writable status.

`POST /api/config` validates and attempts to save the submitted
JSON v2 configuration. The endpoint rejects writes when the
filesystem is read-only.

The HTTP implementation uses a 10,240-byte total request limit,
a 2,048-byte header limit, and 512-byte I/O chunks.

### Verification Status

**PASS — observed on Pico:** Initial JSON v2 loading and
validation tests, disposable-file save and backup tests, browser
configuration loading, DEVICE-mode browser saves, no-change
handling, and stale-revision rejection using two browser tabs.

**PASS — selected recovery tests:** Fallback from corrupted or
missing primary configuration files without automatic primary
repair.

**PARTIALLY VERIFIED:** Overall persistence and recovery
resilience. Selected tests have passed, but the complete
failure matrix has not been exercised.

**NOT TESTED or not fully verified:** Unexpected power loss during
writes, comprehensive malformed HTTP requests, remaining HTTP
error cases, and complete cold power-cycle persistence testing.

These status labels describe observations, not merely intended
behavior. See the detailed
[Configuration Test Record](configuration-testing.md).

### Next Development Boundary

The JSON v2 configuration system is the current working
foundation. Actual physical input handling, action dispatch,
and HTTP commands to AV equipment remain separate future
milestones.

The existence of a configured action does not mean that the
action can already be executed against a device.

## 14. Design Principles

**Clonker controls actions, not brands.**

Fundamental action IDs describe what the user wants to accomplish.

The target, HTTP method, and command path describe how Clonker accomplishes that action.

No fixed assumption is made that volume requires an AVR or navigation requires a streaming device.

Physical operating-mode controls remain separate from device commands.

Configuration data must be strictly validated before persistence.

Proven recovery protections must be retained throughout development.

**JSON v2 is the active operational configuration baseline. XML v1 is retained for rollback. Additional persistence and failure testing remains outstanding.**

---

## October 18, 2026 — Device Endpoints and Fundamental Toggle Actions

**Status: APPROVED DESIGN — TOGGLE SCHEMA AND RUNTIME NOT YET IMPLEMENTED**

This section records the latest configuration decisions for
The Clonker 10000.

The project is still in active development. Backward compatibility
with earlier experimental JSON configuration files is not required.
Existing configurations may be replaced deliberately when the
firmware and browser editor are updated together.

### Device Endpoints — Optional HTTP Ports

Each room continues to define three device endpoints:

- `tv`
- `avr`
- `streaming`

Each endpoint is a string containing either:

- An empty string, indicating an unconfigured device.
- A dotted IPv4 address, implying HTTP port 80.
- A dotted IPv4 address followed by `:port`.

Examples:

```json
{
  "tv": "",
  "avr": "192.168.50.44:8080",
  "streaming": "192.168.50.43:8060"
}
```

The port suffix is optional. When supplied, it must be a decimal
integer between 1 and 65535.

The existing JSON v2 configuration structure is unchanged.

**Implementation status:** The updated Python validator and browser
address labels are implemented. The browser changes have been
observed on the Pico. Actual outbound HTTP connection handling
has not yet been implemented.

The outbound transport will split the endpoint into its IPv4
address and port, using port 80 when no port is specified.

### Fundamental Action Categories

Clonker retains fourteen fundamental action IDs.

Twelve ordinary actions continue using:

- `target`
- `method`
- `path`

Two actions have special toggle semantics:

- `power-toggle`
- `mute-toggle`

These two actions will instead use:

- `target`
- `method`
- `on_path`
- `off_path`

The target device and HTTP method are shared between the ON and
OFF directions.

No additional fundamental action IDs are introduced.

### Toggle Configuration Example

A Denon mute toggle:

```json
"mute-toggle": {
  "target": "avr",
  "method": "GET",
  "on_path": "/goform/formiPhoneAppDirect.xml?MUON",
  "off_path": "/goform/formiPhoneAppDirect.xml?MUOFF"
}
```

The corresponding Denon power commands, if chosen as the target:

```json
"power-toggle": {
  "target": "avr",
  "method": "GET",
  "on_path": "/goform/formiPhoneAppDirect.xml?PWON",
  "off_path": "/goform/formiPhoneAppDirect.xml?PWSTANDBY"
}
```

These are configuration examples, not proof that Denon power
commands will control the entire HDMI-CEC system.

### Devices With Native Toggle Commands

Some devices implement a toggle operation themselves.

For these devices, `on_path` and `off_path` may contain the
same command.

Example:

```json
"power-toggle": {
  "target": "tv",
  "method": "POST",
  "on_path": "/example/native-toggle",
  "off_path": "/example/native-toggle"
}
```

The example path is illustrative, not a verified device API.

Clonker will send the configured command on every press.
No special native-toggle flag or checkbox is required.

### Toggle Runtime Behavior — V1

Toggle state is maintained in RAM.

Each room has independent state for each toggle action.

The initial state is unknown.

On the first press:

- `power-toggle` selects ON.
- `mute-toggle` selects ON.

On subsequent presses, the selected direction alternates
between ON and OFF.

The remembered state represents the last successfully
submitted command, not the actual device state.

The controlled equipment remains authoritative for its
real power and mute status.

The initial implementation will not query device state,
parse XML status responses, or synchronize with other
remotes or HDMI-CEC activity.

If a network request fails, Clonker should not advance
its remembered toggle state.

A successful HTTP response does not guarantee the device
actually performed the command.

Toggle state is not persisted to flash. A reboot resets
the remembered state to unknown.

### Blank Paths and Unconfigured Devices

Blank device endpoints remain valid.

For ordinary actions, a blank `path` remains a no-op.

For toggle actions, the selected ON or OFF path may also
be blank. A blank selected path is a no-op.

A toggle no-op must not advance the remembered state.

A configured action targeting a blank device endpoint
must not open a network connection or advance toggle state.

### Browser Configuration Editor

The existing browser editor will retain:

- Room names.
- Three device address fields.
- Fundamental action editors.
- Target selection.
- GET/POST method selection.

For ordinary actions, the editor will display one Path field.

For `power-toggle` and `mute-toggle`, it will display:

- ON Path
- OFF Path

No state-query field, native-toggle checkbox, macro editor,
or additional configuration mode is required for V1.

### Configuration Cutover

The toggle schema is an intentional breaking change to the
current experimental JSON v2 format.

No automatic migration from the old toggle `path` field
is required.

The strict validator will reject obsolete toggle entries.

Before deploying the updated validator:

1. Preserve a copy of the current configuration.
2. Prepare a replacement JSON file using the new toggle fields.
3. Coordinate deployment of the firmware, browser editor,
   and configuration file.
4. Verify configuration loading and saving on the Pico.
5. Verify backup behavior and active RAM publication.

The JSON version number remains `2` for this development-stage
schema refinement.

### Real Device Testing

Initial configured devices:

- Den Roku Ultra: `192.168.50.43:8060`
- Den Denon AVR-X3700H: `192.168.50.44:8080`
- Sunroom Roku Ultra: `192.168.50.28:8060`
- Sunroom Denon AVR-X1800H: `192.168.50.40:8080`

These endpoint values were supplied and tested independently
using iOS Shortcuts. They are local environment examples.

Initial command paths include:

- Roku Home: `POST /keypress/Home`
- Roku Back: `POST /keypress/Back`
- Roku Play/Pause: `POST /keypress/Play`
- Denon Volume Up: `GET /goform/formiPhoneAppDirect.xml?MVUP`
- Denon Volume Down: `GET /goform/formiPhoneAppDirect.xml?MVDOWN`

Roku's Play command provides native play/pause behavior.

The Roku power-off command remains a provisional configuration.
The final system-power strategy has not been verified.

For V1, Roku POST requests may use the form-style convention
already tested with iOS Shortcuts. Exact Pico request framing
and compatibility must be verified during outbound HTTP testing.

### Future Possibilities

If simple remembered-command toggles prove inadequate, future
device adapters may support:

- Reading actual device power or mute state.
- Choosing discrete commands based on that state.
- Device-specific authentication.
- HDMI-CEC-related behavior where available.
- Compound command sequences.

None of these capabilities is required for the initial
toggle implementation.

Keep the first implementation small.

CLONK!

