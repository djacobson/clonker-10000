# The Clonker 10000 — Configuration, Persistence & Recovery

**Design reference:** Updated October 19, 2026  
**Hardware:** Raspberry Pi Pico 2 W  
**Runtime:** CircuitPython 10.3.1  
**Active configuration:** JSON v2  
**Status:** Configuration engine and browser editor operational; browser action dispatcher tested in logging-only mode; outbound AV commands pending.

> **Clonker controls actions, not brands. Configuration determines where those actions go.**

## 1. Overview

The Clonker 10000 uses a persistent configuration file to define rooms, device endpoints, and remote-control actions.

**JSON v2 is the active configuration format.**

The firmware loads:

`/clonker/device_config.json`

through:

`firmware/clonker/device_config_v2.py`

The browser configuration editor, management HTTP endpoints, and shared action dispatcher all use the active JSON v2 model.

The previous XML v1 implementation remains in the repository as a historical and rollback reference. It is not used by the active firmware or browser endpoints.

JSON was selected primarily to simplify the implementation, not merely to reduce file size. CircuitPython and JavaScript can work with the same data structures without a custom XML parser.

The active configuration system provides:

- Three fixed rooms.
- Three optional device endpoints per room.
- Fourteen fixed fundamental actions per room.
- Editable action targets and HTTP methods.
- Single command paths for ordinary actions.
- Paired ON/OFF command paths for power and mute toggles.
- Strict structural validation.
- Deterministic compact serialization.
- Revision-protected browser saves.
- Detection of unchanged configuration.
- Detection of out-of-band disk changes.
- Verified temporary writes.
- Backup rotation.
- Startup fallback to validated backups.
- Active in-memory configuration publication after successful saves.

These are implemented capabilities, although the complete persistence failure-test matrix remains unfinished.

**Important distinction:** The configuration engine stores commands, and the browser Test Remote can dispatch action requests to a logging stub. Actual HTTP commands to AV equipment have **not** yet been implemented.

See:

- [Architecture](ARCHITECTURE.md)
- [Chapter 2 Handoff](CHAPTER_2_HANDOFF.md)
- [Development History](DEVELOPMENT_HISTORY.md)

## 2. Active Files and Responsibilities

| File | Responsibility |
|---|---|
| `firmware/clonker/device_config.json` | Checked-in JSON v2 configuration |
| `/clonker/device_config.json` | Active configuration path on the Pico |
| `firmware/clonker/device_config_v2.py` | Validation, serialization, revision control, persistence, recovery |
| `firmware/clonker/main.py` | Startup configuration loading |
| `firmware/clonker/web.py` | Configuration HTTP API and browser action routing |
| `firmware/clonker/www/index.html` | Browser configuration editor |
| `firmware/clonker/www/remote.html` | Browser Test Remote |
| `firmware/clonker/actions.py` | Shared action dispatcher; currently logging-only |
| `firmware/clonker/legacy/device_config.py` | Historical XML v1 configuration engine |
| `firmware/clonker/legacy/device_config.xml` | Historical XML v1 configuration |

The configuration checked into GitHub is not automatically synchronized with the active Pico file.

A configuration changed and saved through the browser becomes active in Pico RAM and on the Pico filesystem, but does not automatically create a Git commit.

The deployed configuration should therefore be inspected before assuming it matches the repository example.

## 3. JSON v2 Root Structure

The root configuration object contains exactly:

- `version`
- `rooms`

The `version` value must be the integer `2`.

The `rooms` object must contain exactly:

- `room-1`
- `room-2`
- `room-3`

Room IDs are fixed developer-defined identifiers.

They cannot be renamed, removed, or supplemented by additional room IDs.

The JSON schema version remains `2`, including the October 18 development-stage addition of paired toggle paths.

No automatic migration framework is required for earlier experimental JSON formats.

## 4. Room Structure

Every room contains exactly four properties:

- `name`
- `devices`
- `actions`
- `custom_actions`

### Room name

Room names are editable strings.

Rules:

- Must be a string.
- Must contain at least one non-whitespace character.
- Maximum length: 40 characters.
- Leading and trailing whitespace is removed by validation.

The initial rooms are named Den, Sunroom, and a third-room placeholder.

Names are display labels; fixed room IDs are used for dispatch and configuration lookup.

### Device endpoints

Each room contains exactly three endpoint fields:

- `tv`
- `avr`
- `streaming`

Each endpoint is a string containing one of:

1. An empty string.
2. A dotted IPv4 address.
3. A dotted IPv4 address followed by `:port`.

Examples:

```json
{
  "tv": "",
  "avr": "192.168.50.44:8080",
  "streaming": "192.168.50.43:8060"
}
```

A blank endpoint means that device category is not configured.

A nonblank endpoint without an explicit port implies HTTP port 80.

When present, the port must be a decimal integer from 1 through 65535.

The validator accepts four decimal IPv4 octets in the range 0 through 255. It rejects malformed addresses, nondecimal octets, missing octets, and unsupported endpoint formats.

The active endpoint model is IPv4 with optional port.

It does not currently support DNS hostnames, IPv6 addresses, HTTPS URLs, or authentication configuration.

Device endpoints are independent of action mappings. A volume action may target a TV, AVR, or streaming device, subject to the capabilities of the configured equipment.

### Example development endpoints

The current development configuration has used:

| Room | Device | Endpoint |
|---|---|---|
| Den | Denon AVR-X3700H | `192.168.50.44:8080` |
| Den | Roku Ultra 4800X | `192.168.50.43:8060` |
| Sunroom | Denon AVR-X1800H | `192.168.50.40:8080` |
| Sunroom | Roku Ultra 4670X | `192.168.50.28:8060` |

TV endpoints remain optional.

The third room is reserved for future configuration.

These are local development examples, not portable defaults. Confirm actual addresses and device behavior before real-command testing.

## 5. Fundamental Actions

Each room contains exactly fourteen fixed fundamental action IDs.

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
| `play-pause` | Play/pause |
| `skip-back` | Skip backward |
| `skip-forward` | Skip forward |
| `power-toggle` | Toggle power |

These IDs are developer-defined and fixed.

The validator rejects missing actions, unknown actions, and unexpected action properties.

Channel Up, Channel Down, and Guide are not fundamental actions.

They may be considered as custom actions in a later development phase.

### Ordinary actions

Twelve actions use exactly three properties:

- `target`
- `method`
- `path`

Example:

```json
"volume-up": {
  "target": "avr",
  "method": "GET",
  "path": "/goform/formiPhoneAppDirect.xml?MVUP"
}
```

### Toggle actions

Two actions use exactly four properties:

- `target`
- `method`
- `on_path`
- `off_path`

These are:

- `mute-toggle`
- `power-toggle`

Example:

```json
"mute-toggle": {
  "target": "avr",
  "method": "GET",
  "on_path": "/goform/formiPhoneAppDirect.xml?MUON",
  "off_path": "/goform/formiPhoneAppDirect.xml?MUOFF"
}
```

The target and method are shared by both directions.

The active validator and browser editor already support these fields.

**The runtime selection between ON and OFF commands is not yet implemented.**

### Target

Allowed values:

- `tv`
- `avr`
- `streaming`

The target selects the endpoint field used for that action.

There is no hardcoded requirement that volume target an AVR or navigation target a Roku.

### HTTP method

Allowed values:

- `GET`
- `POST`

Methods are stored as uppercase strings.

The configured method applies to the command selected for execution.

### Command paths

Command paths must be strings.

Maximum length: 512 characters per path.

Empty strings are valid.

A blank ordinary `path` means that action has no configured command.

A blank selected toggle path similarly means no command for that direction.

A configured command cannot execute when its target endpoint is blank.

The validator currently enforces path type and length. It does not implement a comprehensive URL/path security parser.

Exact outbound URL construction, escaping, and request framing must be tested when real HTTP execution is implemented.

## 6. Toggle Actions — Agreed V1 Behavior

**Design agreed:** October 18, 2026  
**Configuration fields:** Implemented  
**Runtime ON/OFF execution:** Planned

The two toggle actions deliberately support separate ON and OFF commands without creating additional fundamental action IDs.

### Command history, not equipment state

Clonker will maintain a small amount of RAM state identifying the last successfully submitted command direction.

History is independent for each room and each toggle action.

Conceptual initial state:

```text
room-1:
    power-toggle: unknown
    mute-toggle:  unknown

room-2:
    power-toggle: unknown
    mute-toggle:  unknown

room-3:
    power-toggle: unknown
    mute-toggle:  unknown
```

On the first press, Clonker attempts the ON command.

After a successful ON command, the next press attempts OFF.

After a successful OFF command, the next press attempts ON.

A failed request must not advance the remembered direction.

A blank selected path or blank target endpoint is a no-op and must not advance history.

The remembered direction is never persisted to flash.

A reboot resets it to unknown.

### Success does not prove device state

The controlled device remains authoritative for actual power and mute status.

A successful HTTP response may indicate that the command was accepted, but does not prove that the equipment changed state.

Other remotes, HDMI-CEC, and applications may change device state without Clonker knowing.

This is an accepted V1 limitation.

### Native toggle commands

Some devices implement a native toggle command.

For those devices, `on_path` and `off_path` may contain the same command.

Example:

```json
"power-toggle": {
  "target": "tv",
  "method": "POST",
  "on_path": "/example/native-toggle",
  "off_path": "/example/native-toggle"
}
```

The path above is illustrative, not a verified device API.

No separate native-toggle flag is required.

Clonker can send the same command on every press while retaining the normal RAM command-history mechanism.

### No equipment-state queries in V1

The initial implementation will not:

- Query current equipment power or mute state.
- Parse device-specific XML or JSON status responses.
- Synchronize with external remotes.
- Track HDMI-CEC state.
- Persist toggle history.
- Implement device-specific state reconciliation.

These capabilities may be considered later if actual use demonstrates a need.

### Toggle execution boundary

The dispatcher will own toggle direction and history.

The outbound transport will own HTTP communication and errors.

The transport must not decide whether a command represents ON or OFF.

One toggle event selects at most one command path and sends at most one HTTP request.

## 7. Blank Actions and Safe No-Ops

Blank device endpoints and blank command paths are intentional, valid configuration values.

They allow a room or action to remain unconfigured without preventing the rest of the configuration from loading.

For an ordinary action:

- Blank target endpoint: no command.
- Blank path: no command.

For a toggle action:

- Blank target endpoint: no command.
- Blank selected ON/OFF path: no command.
- No-op must not advance toggle history.

The current logging-only dispatcher determines whether an action appears configured using the selected endpoint and the presence of at least one candidate path.

For toggles, this is only a preliminary configured/not-configured indication. It does not yet select the next ON/OFF direction.

A stub result reporting `configured: true` must not be interpreted as evidence that a device command was sent.

## 8. Reserved Custom Actions

Every room contains:

```json
"custom_actions": []
```

This field is reserved for later user-defined commands.

The active validator requires it to be an empty array.

A nonempty array is rejected.

The browser Test Remote currently displays illustrative custom-action selections, including:

- Movie Mode
- Stereo Mode
- Next Audio Mode

These are interface placeholders, not configured executable custom actions.

The future custom-action model should remain practical and simple.

A basic custom action may eventually consist of a user-defined identity, display name, target, method, and path.

Macros, command sequences, conditional execution, and scripting are not part of the current implementation.

## 9. JSON Configuration Example

The following example illustrates the active structure of a single room.

**It is intentionally incomplete and must not be deployed as a complete configuration.**

A valid root configuration must contain all three rooms and all fourteen fundamental actions in each room.

```json
{
  "version": 2,
  "rooms": {
    "room-1": {
      "name": "Den",
      "devices": {
        "tv": "",
        "avr": "192.168.50.44:8080",
        "streaming": "192.168.50.43:8060"
      },
      "actions": {
        "volume-up": {
          "target": "avr",
          "method": "GET",
          "path": "/goform/formiPhoneAppDirect.xml?MVUP"
        },
        "volume-down": {
          "target": "avr",
          "method": "GET",
          "path": "/goform/formiPhoneAppDirect.xml?MVDOWN"
        },
        "mute-toggle": {
          "target": "avr",
          "method": "GET",
          "on_path": "/goform/formiPhoneAppDirect.xml?MUON",
          "off_path": "/goform/formiPhoneAppDirect.xml?MUOFF"
        },
        "nav-up": {
          "target": "streaming",
          "method": "POST",
          "path": "/keypress/Up"
        },
        "nav-down": {
          "target": "streaming",
          "method": "POST",
          "path": "/keypress/Down"
        },
        "nav-left": {
          "target": "streaming",
          "method": "POST",
          "path": "/keypress/Left"
        },
        "nav-right": {
          "target": "streaming",
          "method": "POST",
          "path": "/keypress/Right"
        },
        "select": {
          "target": "streaming",
          "method": "POST",
          "path": "/keypress/Select"
        },
        "back": {
          "target": "streaming",
          "method": "POST",
          "path": "/keypress/Back"
        },
        "home": {
          "target": "streaming",
          "method": "POST",
          "path": "/keypress/Home"
        },
        "play-pause": {
          "target": "streaming",
          "method": "POST",
          "path": "/keypress/Play"
        },
        "skip-back": {
          "target": "streaming",
          "method": "POST",
          "path": "/keypress/InstantReplay"
        },
        "skip-forward": {
          "target": "streaming",
          "method": "POST",
          "path": "/keypress/Fwd"
        },
        "power-toggle": {
          "target": "avr",
          "method": "GET",
          "on_path": "/goform/formiPhoneAppDirect.xml?PWON",
          "off_path": "/goform/formiPhoneAppDirect.xml?PWSTANDBY"
        }
      },
      "custom_actions": []
    }
  }
}
```

These command paths are examples of the intended Denon and Roku mappings.

Their presence does not mean they have been executed successfully by Pico firmware.

A complete readable configuration example is maintained separately at:

`samples/device_config_roku_denon_sample.json`

The active Pico configuration is stored in compact form.

## 10. Strict Validation

The active `device_config_v2.py` module validates the complete configuration after JSON parsing.

Validation rejects:

- Missing or unknown root fields.
- Incorrect schema version.
- Missing or extra rooms.
- Missing or unknown room properties.
- Invalid room names.
- Missing or extra device endpoint fields.
- Invalid nonblank IPv4 addresses.
- Invalid port suffixes.
- Missing or unknown fundamental actions.
- Missing or extra action properties.
- Invalid targets.
- Invalid HTTP methods.
- Non-string command paths.
- Paths longer than 512 characters.
- Nonempty custom-action arrays.
- Unexpected value types.
- Serialized configurations exceeding the byte limit.

The validator creates an ordered copy rather than trusting arbitrary input dictionaries.

### Centralized limits

Current firmware constants:

| Constant | Value |
|---|---:|
| `CONFIG_VERSION` | `2` |
| `MAX_CONFIG_BYTES` | `8192` |
| `MAX_ROOM_NAME_LENGTH` | `40` |
| `MAX_PATH_LENGTH` | `512` |
| Number of rooms | `3` |
| Device endpoints per room | `3` |
| Fundamental actions per room | `14` |

The byte limit applies to UTF-8 encoded JSON.

### Duplicate JSON object keys

The active engine uses standard `json.loads()`.

Standard JSON parsing does not independently reject duplicate object keys.

The project deliberately does not implement a custom duplicate-key parser for V1.

The browser editor is the normal configuration interface; direct hand-editing is primarily a developer activity.

This is an accepted limitation, not a claim of perfect JSON input validation.

### Validation versus transport safety

Configuration validation does not itself establish that a command path is safe or executable against a device.

Outbound HTTP execution must separately handle endpoint parsing, request construction, response processing, timeouts, and network failures.

The current schema supports only the simple HTTP command model agreed for V1.

## 11. Active Configuration in RAM

The configuration engine maintains a single authoritative validated configuration snapshot in the private `_current` dictionary.

Important functions:

| Function | Behavior |
|---|---|
| `load(path=None)` | Load primary or validated backup and bind the save path |
| `current()` | Return a validated copy of active configuration |
| `room(room_id)` | Return a room from the current configuration |
| `validate_config(config)` | Validate and normalize configuration |
| `to_json(config)` | Produce deterministic compact JSON |
| `from_json(contents)` | Parse and validate bounded JSON input |
| `revision(config=None)` | Calculate deterministic revision |
| `save(config, expected_revision, path=None)` | Revision-protected persistence |
| `_recover_missing_file(path)` | Explicit missing-primary recovery helper |

The dispatcher currently uses `device_config.room(room_id)`.

This ensures that successful browser configuration saves become available to subsequent action lookups without restarting the Pico.

A separate configuration cache is unnecessary for V1.

A narrower read-only lookup may be considered if future encoder performance testing demonstrates that repeated validated copies are too expensive.

Do not introduce a second authoritative configuration state.

## 12. Deterministic Serialization and Revisions

The engine serializes validated configuration using compact JSON with stable room, device, and action ordering.

Serialization uses UTF-8 encoding.

A deterministic 32-bit FNV-1a hash of canonical JSON bytes produces the configuration revision.

The revision is represented as an eight-character hexadecimal string.

The revision is a concurrency and change-detection token, not a cryptographic authentication mechanism.

The browser receives the revision separately from the persisted configuration.

Browser-only metadata includes:

- `revision`
- `filesystem_writable`

These values are returned by the API but are not stored inside `device_config.json`.

### Stale browser protection

The browser submits the revision associated with the configuration it originally loaded.

If another tab or client successfully changes the configuration, an older tab's save is rejected.

The user must refresh and review the current configuration before saving again.

This behavior was exercised with two browser tabs on the Pico.

### Out-of-band changes

Before saving, the engine reloads and validates the primary file on disk.

It rejects a save if the on-disk configuration differs from the active in-memory snapshot.

This prevents silently overwriting changes made outside the active configuration engine.

## 13. Persistence and Backup Rotation

Configuration saves are designed to minimize unnecessary writes and preserve recoverable generations.

The active engine:

1. Requires a previously loaded configuration.
2. Checks the save path against the path bound by `load()`.
3. Checks the expected revision.
4. Validates the proposed configuration.
5. Produces deterministic compact JSON.
6. Loads and validates the existing primary file.
7. Rejects out-of-band changes.
8. Detects an unchanged configuration.
9. Writes changed JSON to a temporary file.
10. Flushes the temporary file.
11. Reopens and verifies the temporary file.
12. Validates the temporary contents.
13. Rotates backup generations.
14. Installs the replacement primary file.
15. Reads back and validates the installed primary.
16. Publishes the successfully saved configuration to RAM.

A failed save must not publish the proposed configuration as active state.

An unchanged save returns without rotating backups.

### Backup generations

| File | Purpose |
|---|---|
| `device_config.json` | Current primary |
| `device_config.json.bak` | Previous generation |
| `device_config.json.bak.old` | Older generation |
| `device_config.json.tmp` | Temporary write file during replacement |

The oldest backup is rolling, not permanent.

Backups are recovery generations, not a substitute for external backups or Git history.

### Rotation safeguards

The engine verifies the existing primary before rotating backups.

It does not deliberately rotate a known-invalid primary into the backup chain during an ordinary save.

The temporary file is written and verified before the primary is replaced.

After installation, the primary is read back and validated before the new configuration is published to RAM.

### Power-loss limitation

The sequence of filesystem renames is **not a fully atomic transaction**.

Unexpected power loss can interrupt backup rotation or replacement.

These safeguards reduce risk, but do not guarantee durability during power interruption.

Do not describe the persistence engine as power-loss-proof.

## 14. Startup Loading and Recovery

On startup, the loader attempts these candidates in order:

1. `device_config.json`
2. `device_config.json.bak`
3. `device_config.json.bak.old`

Each candidate must parse and pass validation.

The first valid candidate becomes the active in-memory configuration.

If none is valid, loading fails.

### Backup fallback does not repair the primary

Loading a backup into RAM does not automatically overwrite or recreate the primary configuration.

This is intentional.

A damaged primary should not be silently replaced merely because a backup was available.

### Explicit missing-primary recovery

The engine includes `_recover_missing_file()` for an explicit recovery operation when the primary file is missing.

It may restore a valid backup into the primary path.

It does not overwrite an existing primary.

This recovery helper is separate from ordinary startup loading.

### Save behavior after backup fallback

If the primary is missing or invalid, ordinary saving does not treat the backup-loaded configuration as permission to overwrite that damaged primary.

The primary must pass the normal disk validation and consistency safeguards.

This prevents an otherwise successful fallback from silently destroying evidence of a configuration problem.

## 15. Filesystem Ownership and Browser Saving

The Pico has two independent mode dimensions:

- SERVICE (USB) / DEVICE — filesystem ownership.
- CONFIG / RUN — application behavior.

### SERVICE (USB)

GP17 is open at boot.

The USB host can write the CIRCUITPY filesystem.

The Pico application cannot persist configuration changes to its read-only filesystem.

The browser editor may load configuration, but `POST /api/config` rejects writes with HTTP 403.

### DEVICE

GP17 is grounded at boot.

The Pico can write its filesystem.

The USB host sees CIRCUITPY as read-only.

The browser editor can save configuration, subject to validation, revision checking, and persistence safeguards.

Switching SERVICE/DEVICE requires a full power cycle.

### CONFIG / RUN

CONFIG is currently simulated enabled.

The physical CONFIG/RUN switch has not yet been implemented.

CONFIG controls management HTTP availability.

It does not determine which side owns the filesystem.

See [Operating Modes](OPERATING_MODES.md).

## 16. Browser Configuration Editor

The active browser editor is served at:

`http://192.168.50.12:9090/`

It provides:

- System clock status and browser synchronization.
- Test Remote access.
- Three-room configuration editing.
- Room name editing.
- Three device endpoint fields per room.
- Fourteen fundamental action editors per room.
- Target selection.
- GET/POST method selection.
- Ordinary Path fields.
- Toggle ON Path and OFF Path fields.
- Save status and error reporting.
- Revision-aware configuration submission.

The clock and Test Remote panels appear side by side on suitable screen widths and stack on narrower displays.

The page includes a small centered designer attribution.

### Save behavior

The browser receives the active configuration and revision.

It submits the edited configuration with the expected revision.

The server validates and attempts persistence.

If the filesystem is read-only, saving is rejected.

If the revision is stale, saving is rejected and the user is directed to refresh.

If no configuration values changed, the engine reports an unchanged configuration rather than writing a new generation.

A successful changed save updates both the active file and RAM configuration.

### Browser Test Remote

The Test Remote is served at:

`http://192.168.50.12:9090/remote.html`

It presents all fourteen fundamental action buttons and a room selector.

Each fundamental button sends a POST request to `/api/action` with room and action identifiers.

The shared dispatcher currently validates and logs the request.

It does not yet send commands to the configured AV device.

The illustrative custom-action dropdown is not an executable custom-action system.

## 17. Management HTTP API

The application HTTP server runs on port 9090.

Current relevant routes:

| Request | Behavior |
|---|---|
| `GET /` | Browser configuration and clock page |
| `GET /remote.html` | Browser Test Remote |
| `GET /api/config` | Current JSON v2 configuration, revision, filesystem writability |
| `POST /api/config` | Validate and save configuration |
| `GET /api/clock` | Clock status |
| `POST /api/clock?utc=...` | Synchronize clock from browser |
| `POST /api/action?room=...&action=...` | Validate and log a fundamental action |

The action route is implemented, but outbound device control is not.

### HTTP limits

Current inbound HTTP constants:

| Constant | Value |
|---|---:|
| `MAX_REQUEST_BYTES` | `10240` |
| `MAX_HEADER_BYTES` | `2048` |
| `IO_CHUNK_BYTES` | `512` |
| `CLIENT_TIMEOUT_SECONDS` | `4.0` |

The JSON configuration size limit is independently enforced at 8192 UTF-8 bytes.

The server handles one client at a time using a cooperative polling design.

These bounds are not a guarantee of responsiveness under every network failure.

### Security boundary

The management interface is intended for a trusted local network.

It does not implement application authentication.

Do not expose port 9090 through internet port forwarding.

The CircuitPython Web Workflow service is separately disabled in the private runtime configuration because of suspected socket conflicts.

## 18. Command Examples and Device Considerations

The configuration model intentionally does not hardcode brands.

Nevertheless, initial development focuses on Denon and Roku devices.

### Denon examples

```text
GET /goform/formiPhoneAppDirect.xml?MVUP
GET /goform/formiPhoneAppDirect.xml?MVDOWN
GET /goform/formiPhoneAppDirect.xml?MUON
GET /goform/formiPhoneAppDirect.xml?MUOFF
GET /goform/formiPhoneAppDirect.xml?PWON
GET /goform/formiPhoneAppDirect.xml?PWSTANDBY
```

A Quick Select example discussed during development:

```text
GET /goform/formiPhoneAppDirect.xml?MSQUICK2
```

The exact supported command set and effects must be verified against each target receiver.

### Roku examples

```text
POST /keypress/Home
POST /keypress/Back
POST /keypress/Play
POST /keypress/Up
POST /keypress/Down
POST /keypress/Left
POST /keypress/Right
POST /keypress/Select
POST /keypress/InstantReplay
POST /keypress/Fwd
```

Roku's Play command has been used as a native play/pause control.

Roku power-on and power-off mappings remain subject to real-device verification.

The final whole-system power strategy, including HDMI-CEC interactions, is not settled.

### POST request framing

Roku commands have been exercised independently using iOS Shortcuts.

The initial plan is to use compatible form-style POST requests where appropriate.

Actual Pico outbound HTTP framing and device responses remain to be tested.

Configuration examples are not proof of successful execution from the Pico.

## 19. Historical XML v1 Implementation

**Historical milestone:** October 16, 2026  
**Current status:** Retained for reference and rollback; not active.

The original XML configuration engine provided:

- Three fixed rooms.
- Editable room names.
- Optional TV and AVR IPv4 addresses.
- A `volume_device` preference selecting TV or AVR.
- Browser configuration editing.
- Persistent saves.
- Revision checking.
- No-change detection.
- Verified temporary writes.
- Backup rotation.
- Configuration reload into active memory.
- Persistence across reboot.

These capabilities were tested on the Pico before the JSON transition.

The historical implementation is retained at:

- `firmware/clonker/legacy/device_config.py`
- `firmware/clonker/legacy/device_config.xml`

Historical XML runtime paths included:

- `/clonker/device_config.py`
- `/clonker/device_config.xml`

Those paths are **not** the active JSON v2 configuration paths.

The original browser API used the same general GET/POST configuration pattern, but the current firmware uses the JSON v2 engine.

See [Development History](DEVELOPMENT_HISTORY.md) for dated observations.

### Why JSON replaced XML

JSON was selected because:

- CircuitPython includes JSON parsing and serialization.
- JavaScript handles JSON natively.
- Python dictionaries and browser objects can share a structure.
- Custom XML parsing and escaping are unnecessary.
- Validation can be separated from parsing.
- Future custom commands fit naturally into arrays and objects.
- Compact JSON can reduce storage requirements.

No complex automatic XML-to-JSON migration framework was required during this experimental development phase.

## 20. Historical Serialization Comparison

A representative complete configuration with three rooms, fourteen actions per room, blank endpoints, and blank paths was compared in several serialization formats.

| Representation | UTF-8 size |
|---|---:|
| Pretty-printed JSON | 5,338 bytes |
| Readable XML | 3,736 bytes |
| Compact JSON | 2,754 bytes |

These figures describe historical representative fixtures, not the current live configuration file.

Compact JSON was approximately 26% smaller than the compared readable XML representation.

Pretty-printed JSON can be larger than XML.

The primary reason for choosing JSON remained implementation simplicity.

The production configuration is serialized compactly.

A readable sample is kept separately for documentation and editing.

## 21. Historical JSON v2 Development Sequence

The JSON v2 implementation was introduced through a coordinated firmware and browser cutover.

The original development plan included:

1. Finalize schema and fourteen fundamental action IDs.
2. Implement JSON loading and validation.
3. Implement deterministic serialization and revisions.
4. Preserve verified writes and backup rotation.
5. Integrate the browser editor.
6. Test saving, recovery, and stale revisions.
7. Deploy matching firmware and JSON configuration.
8. Preserve the working XML implementation in Git.

These phases were substantially completed.

The October 18 toggle-field change was an intentional breaking change within the experimental JSON v2 format.

The original toggle entries contained a single `path`.

The active schema instead requires `on_path` and `off_path`.

The schema version remains `2`.

No automatic migration of obsolete toggle entries is provided.

The strict validator rejects old-style toggle objects.

The coordinated cutover required updated firmware, browser editor, and JSON data.

### Development principle

During this early stage, coordinated replacement of experimental configuration files is acceptable.

Once the configuration format is considered stable for broader deployment, migration and compatibility requirements should be reconsidered explicitly.

## 22. Verification Status — October 19, 2026

The following summarizes observed development progress.

The detailed dated record remains authoritative for individual test cases.

### Passed in reported Pico testing

- JSON v2 configuration loading.
- Initial validation tests.
- Disposable-file save and backup exercises.
- Browser configuration loading.
- DEVICE-mode browser saves.
- No-change detection.
- Stale-revision rejection with two browser tabs.
- Selected backup fallback cases.
- Browser Test Remote fundamental button dispatch to logging stub.
- Configuration changes remaining available to the active application.
- Paired toggle fields accepted by the active configuration model and browser editor.

### Implemented but not comprehensively verified

- All malformed JSON and schema rejection cases.
- Out-of-band modification detection under every failure scenario.
- Verified temporary-file installation under storage faults.
- Every backup rotation and fallback permutation.
- All malformed HTTP requests and timeout cases.
- Behavior during unexpected power interruption.

### Not yet implemented or tested as real AV control

- Outbound Denon HTTP commands from Pico.
- Outbound Roku HTTP commands from Pico.
- Toggle ON/OFF direction selection.
- Toggle history updates after successful commands.
- Physical button and encoder action dispatch.
- Physical CONFIG/RUN transitions.
- End-to-end system power behavior.

Do not conflate implementation, a successful isolated test, and complete reliability verification.

See [Development History](DEVELOPMENT_HISTORY.md).

## 23. Next Development Boundary

The configuration engine is now the operational foundation for the next phase.

The next milestone is real HTTP action execution.

Recommended sequence:

1. Review the current `actions.py` logging dispatcher.
2. Inspect available CircuitPython socket and HTTP capabilities.
3. Implement a minimal bounded outbound HTTP request path.
4. Test one low-risk Denon or Roku command from the browser Test Remote.
5. Verify the result using serial logs and observed device behavior.
6. Expand ordinary action execution.
7. Confirm blank endpoints and paths produce safe no-ops.
8. Implement independent per-room toggle command history.
9. Test failed commands without advancing toggle history.
10. Later integrate physical controls and RUN-only operation.

The active JSON v2 schema should not require another redesign merely to begin ordinary command execution.

Avoid premature abstractions, general macro engines, complex state tracking, or unnecessary persistence changes.

## 24. Design Principles

**Clonker controls actions, not brands.**

Fundamental action IDs describe user intent.

The target, HTTP method, and command path describe how to execute that intent.

Room IDs remain stable while room names are editable.

Blank actions are valid and safe.

Physical operating-mode controls are separate from device commands.

Configuration must be validated before persistence.

Successful browser saves must become available to subsequent action dispatch without rebooting.

Stale browser edits must not silently overwrite newer configuration.

Backup recovery must not silently destroy a damaged primary.

The controlled devices own their actual state.

Clonker's planned toggle history records commands, not equipment truth.

The existing persistence safeguards must not be weakened during HTTP action development.

**JSON v2 is operational. Browser action dispatch is operational in logging-only form. Real device commands are next.**

---

**CLONK! ⚡🔩**
