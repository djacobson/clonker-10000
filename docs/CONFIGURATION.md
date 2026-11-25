
# The Clonker 10000 — Configuration, Persistence & Recovery

**Design reference:** November 24, 2026  
**Platform:** Raspberry Pi Pico 2 W / CircuitPython 10.3.1  
**Active schema:** Clonker Config v5 (JSON)  
**Baseline:** Chapter 12 — The Monster Gets Organized

> Clonker controls intent, not reality. A command can be accepted, transmitted, and acknowledged without proving what the television actually did.

---

## 1. Scope and Sources of Truth

This document is the authoritative reference for configuration schema, validation, persistence, and recovery.

The active implementation is:

- `firmware/clonker/device_config.py`
- `firmware/clonker/devices/device_types.py`
- `firmware/clonker/devices/device_adapters.py`

`CONFIG_VERSION = 5` defines the active schema version. Active Python module filenames no longer carry configuration version suffixes.

The source repository contains maintained firmware and configuration examples. The running Pico's `/clonker/device_config.json` is the active, potentially newer, user-edited configuration.

Never overwrite the active configuration casually during firmware deployment.

### Related documentation

- [Architecture](ARCHITECTURE.md)
- [Configuration Redesign](CONFIGURATION_REDESIGN.md)
- [Firmware, Network & Clock](FIRMWARE_NETWORK.md)
- [Operating Modes](OPERATING_MODES.md)
- [Hardware Design](HARDWARE_DESIGN.md)
- [Development & Deployment](DEVELOPMENT.md)
- [Development History](DEVELOPMENT_HISTORY.md)

### Design commitments

- A fixed vocabulary of fundamental actions with editable room-specific mappings.
- Explicitly typed devices and protocol-aware command objects.
- Stable room, device, and Custom Action identifiers.
- Strict validation at configuration trust boundaries.
- Efficient access to already validated configuration.
- Deterministic serialization and bounded storage.
- Intentional no-ops for blank fundamental commands and endpoints.
- No implicit migration, repair, command replay, or equipment-state inference.
- One shared dispatcher and One Dumb Queue™.

## 2. Files and Ownership

| File | Role |
|---|---|
| `/clonker/device_config.json` | Active primary configuration |
| `/clonker/device_config.json.bak` | Previous primary |
| `/clonker/device_config.json.bak.old` | Older backup generation |
| `/clonker/device_config.json.tmp` | Verified temporary write |
| `firmware/clonker/device_config.json` | Repository configuration copy |
| `firmware/clonker/device_config.py` | Active configuration engine |
| `firmware/clonker/devices/device_types.py` | Central device-type registry |
| `firmware/clonker/devices/device_adapters.py` | Adapter selection and lifecycle coordinator |
| `firmware/clonker/www/index.html` | Embedded configuration editor |
| `firmware/clonker/www/remote.html` | Embedded Test Remote |
| `recipes/` | Hosted configuration recipe library |

Filesystem ownership is established at cold boot.

- SERVICE (USB): USB host owns filesystem writes.
- DEVICE: Pico firmware owns filesystem writes.
- CONFIG: Management HTTP listener enabled.
- RUN: Management HTTP listener disabled.

Persistent browser saves require DEVICE + CONFIG.

SERVICE + CONFIG permits inspection and action testing but rejects persistent configuration saves.

Physical controls and the shared action dispatcher remain operational independently of the management listener.

See [Operating Modes](OPERATING_MODES.md) for switch assignments and operating procedures.

## 3. Config v5 Schema

The root object contains exactly two fields:

```json
{
  "version": 5,
  "rooms": {
    "room-1": {
      "name": "Den",
      "devices": {},
      "actions": {},
      "custom_actions": []
    }
  }
}
```

This fragment illustrates the structure only. It is not a complete deployable configuration.

### 3.1 Rooms

One to three configured rooms are supported.

Reserved room identifiers:

- `room-1`
- `room-2`
- `room-3`

Rooms may be omitted individually, but at least one must exist.

Each configured room contains exactly:

| Field | Description |
|---|---|
| `name` | User-visible room name |
| `devices` | Three typed device records |
| `actions` | Fourteen fundamental action definitions |
| `custom_actions` | Ordered array of Custom Actions |

Room names are nonblank strings of at most 40 characters and are trimmed during validation.

Room identifiers are stable. Removing a room does not renumber the remaining rooms.

An unconfigured room and a configured room with blank endpoints are distinct conditions. Neither causes commands to fall back to another room.

### 3.2 Device slots

Each configured room contains exactly three built-in device slots.

| Stable ID | Editor role label |
|---|---|
| `device-1` | TV |
| `device-2` | AVR |
| `device-3` | Streaming |

These labels are organizational conveniences, not device-type restrictions.

A Roku, Denon, generic HTTP device, or other configurable device type may occupy any slot.

Fundamental actions and Custom Action steps explicitly identify their target slot.

### 3.3 Typed device records

Unlike Config v4, device entries are objects rather than endpoint strings.

Example:

```json
"devices": {
  "device-1": {
    "type": "generic-http",
    "endpoint": ""
  },
  "device-2": {
    "type": "denon",
    "endpoint": "192.168.50.44:8080"
  },
  "device-3": {
    "type": "roku",
    "endpoint": "192.168.50.43:8060"
  }
}
```

These addresses are development LAN examples, not permanent defaults.

Every device record contains a `type` and an `endpoint`. Additional fields are determined by the device-type registry.

An endpoint may contain:

- An empty string.
- A dotted IPv4 address.
- A dotted IPv4 address followed by a numeric port from 1 to 65535.

Hostnames, IPv6 literals, and URL schemes are not supported.

Endpoint validation checks syntax, not network reachability.

### 3.4 Device-type registry

`devices/device_types.py` is the central source of device-type metadata.

The registry defines:

- Stable type identifier.
- Display label.
- Runtime availability.
- Suggested default port.
- Supported command kinds.
- Device-specific attributes.
- Pairing capability.

| Type ID | Display label | Suggested port | Command kinds | Status |
|---|---|---:|---|---|
| `generic-http` | Generic HTTP | 80 | HTTP | Operational |
| `denon` | Denon AVR | 8080 | HTTP | Operational |
| `roku` | Roku ECP | 8060 | HTTP | Operational |
| `lg-webos` | LG webOS | 3000 | SSAP, Pointer | Configuration only |
| `apple-tv` | Apple TV | — | — | Future |
| `fire-tv` | Amazon Fire TV | — | — | Future |

The registry is lightweight configuration metadata. It does not import protocol adapters or perform network operations.

Suggested ports are not necessarily the ports used by specialized transports. For example, Denon TCP volume uses port 23.

Command compatibility and runtime availability are separate concepts.

LG webOS configuration is intentionally supported before runtime integration. Apple TV and Fire TV remain unavailable for configuration and execution.

### 3.5 Device-specific attributes

LG webOS device records include a client key:

```json
{
  "type": "lg-webos",
  "endpoint": "192.168.50.100:3000",
  "client_key": ""
}
```

The client key is a string of at most 512 characters.

A blank key is valid configuration data but does not establish an authenticated device session.

The editor exposes an editable client-key field and a pairing control for LG webOS. The pairing control remains disabled pending runtime integration.

A valid LG configuration does not imply that LG commands can currently execute.

Client keys must be treated as credentials and excluded from public configuration recipes.

## 4. Protocol-Aware Commands

Every command object explicitly declares its protocol kind.

The command kind must be compatible with the configured target device type.

### 4.1 HTTP commands

```json
{
  "kind": "http",
  "method": "POST",
  "path": "/keypress/Home"
}
```

Rules:

- Method must be `GET` or `POST`.
- Path must be a string of at most 512 characters.
- A nonblank path must begin with `/`.
- A blank path is permitted for fundamental actions.
- Custom Action steps require nonblank commands.

The HTTP command kind is used by generic HTTP, Denon, and Roku devices.

Specialized adapter selection is based on the explicitly configured device type, action context, and recognized command mapping.

### 4.2 LG SSAP commands

```json
{
  "kind": "ssap",
  "uri": "ssap://audio/setMute",
  "payload": {
    "mute": true
  }
}
```

Rules:

- URI must be a string of at most 512 characters.
- A nonblank URI must begin with `ssap://`.
- The URI must contain a command after the prefix.
- Whitespace is not permitted within a nonblank URI.
- `payload` is optional.
- When present, the payload must be a JSON object.
- A blank URI cannot have a payload.
- Nested JSON objects and arrays are supported.
- Nonfinite numeric values are rejected.

Payload object keys are normalized into deterministic order.

The schema does not maintain a fixed inventory of supported SSAP commands. Users may configure protocol-compatible commands as needed.

### 4.3 LG pointer commands

```json
{
  "kind": "pointer",
  "button": "HOME"
}
```

The button field supports up to 64 characters using uppercase letters, digits, underscores, and hyphens.

A blank button is permitted for fundamental actions.

The validator checks the command representation, not whether a particular television implements the requested button.

SSAP and pointer commands are configuration-ready but are not yet connected to the operational dispatcher.

## 5. Fundamental Actions

Every configured room defines all fourteen fundamental action IDs.

```text
volume-up     volume-down     mute-toggle
nav-up        nav-down        nav-left        nav-right
select        back            home            play-pause
skip-back     skip-forward    power-toggle
```

### 5.1 Ordinary fundamental actions

Twelve fundamental actions use a target and a single command object.

```json
"volume-up": {
  "target": "device-2",
  "command": {
    "kind": "http",
    "method": "GET",
    "path": "/goform/formiPhoneAppDirect.xml?MVUP"
  }
}
```

An LG configuration example:

```json
"volume-up": {
  "target": "device-1",
  "command": {
    "kind": "ssap",
    "uri": "ssap://audio/volumeUp"
  }
}
```

The second example illustrates future LG execution configuration, not currently operational LG control.

### 5.2 Toggle actions

`mute-toggle` and `power-toggle` use separate ON and OFF command objects.

```json
"power-toggle": {
  "target": "device-3",
  "on_command": {
    "kind": "http",
    "method": "POST",
    "path": "/keypress/PowerOn"
  },
  "off_command": {
    "kind": "http",
    "method": "POST",
    "path": "/keypress/PowerOff"
  }
}
```

Both commands target the same device but are independently configurable.

Their methods, paths, payloads, or compatible command kinds need not be identical.

### 5.3 Toggle direction history

Toggle commands do not query actual equipment state.

The dispatcher maintains independent volatile next-direction histories for each room and toggle action.

A successful execution advances the history.

Failed execution, missing endpoints, and selected blank commands do not advance it.

A changed configuration save resets all toggle histories. An unchanged save preserves them.

History is lost on reboot.

External remotes, HDMI-CEC, and manual equipment controls may independently change actual equipment state.

The physical Power Toggle controls configured room equipment; it does not turn the Pico itself on or off.

### 5.4 Intentional no-ops

Blank fundamental commands and blank device endpoints are valid.

A selected blank command or missing endpoint produces an intentional no-op rather than an invented substitute command.

Physical hold handling also checks blank commands and endpoints before admitting specialized hold work.

## 6. Custom Actions

Custom Actions are room-specific, ordered, user-named command sequences.

They supplement the fourteen fundamental actions rather than replacing them.

Example:

```json
{
  "id": "custom-action-1",
  "name": "Movie",
  "steps": [
    {
      "target": "device-3",
      "command": {
        "kind": "http",
        "method": "POST",
        "path": "/keypress/Home"
      },
      "wait_after_ms": 3000
    },
    {
      "target": "device-2",
      "command": {
        "kind": "http",
        "method": "GET",
        "path": "/goform/formiPhoneAppDirect.xml?MSQUICK1"
      },
      "wait_after_ms": 0
    }
  ]
}
```

### 6.1 Constraints

| Constraint | Rule |
|---|---|
| Custom Actions per room | 0–16 |
| ID length | 1–40 characters |
| ID characters | Lowercase letters, digits, hyphens |
| ID boundaries | Cannot begin or end with a hyphen |
| ID uniqueness | Within each room |
| Name | Nonblank, maximum 60 characters |
| Steps | 1–16 |
| Target | Existing built-in device slot |
| Command | Nonblank, compatible with target device type |
| Wait | Integer 0–60000 milliseconds |
| Final step wait | Exactly zero |

Boolean values are not accepted as integer waits.

Custom Action names are trimmed during validation.

### 6.2 Stable identifiers

The browser generates identifiers for new Custom Actions automatically.

Identifiers are displayed read-only and remain unchanged when an action is renamed or reordered.

New identifiers are generated with the intent of avoiding collisions across the configuration.

Existing identifiers are preserved, and firmware validation requires uniqueness within each room.

### 6.3 Execution semantics

A Custom Action enters the shared queue as one task.

Each step executes one configured command.

After successful completion of a nonfinal step, the task is rescheduled using that step's `wait_after_ms`.

Other eligible queue work may execute during the delay.

A failed step clears remaining pending work according to normal dispatcher failure policy.

There are no nested macros, loops, branches, parallel executors, automatic retries, or rollback operations.

Custom Action steps resolve through the configured device type.

Existing Roku and Denon HTTP Custom Action steps retain single-command generic HTTP execution. They do not implicitly acquire fundamental-action hold or repeat behavior.

The physical Custom Action encoder selects an action and runs it when pressed. The browser Test Remote uses the same dispatcher.

The Sunroom Movie action has been verified with:

1. Roku Home.
2. Cooperative 3000 ms wait.
3. Denon Quick Select 1.

## 7. Validation and Storage Limits

| Constraint | Value |
|---|---:|
| `CONFIG_VERSION` | 5 |
| `MAX_CONFIG_BYTES` | 16384 UTF-8 bytes |
| Room name | 40 characters |
| HTTP path | 512 characters |
| SSAP URI | 512 characters |
| Pointer button | 64 characters |
| LG client key | 512 characters |
| Custom Action ID | 40 characters |
| Custom Action name | 60 characters |
| Custom Actions per room | 16 |
| Steps per Custom Action | 16 |
| Maximum step wait | 60000 ms |
| Configured rooms | 1–3 |
| Device slots per room | Exactly 3 |
| Fundamental actions per room | Exactly 14 |

`validate_config()` returns a new normalized, ordered configuration object.

It rejects missing and unknown fields, unsupported versions, malformed endpoints, invalid identifiers, incompatible command kinds, unavailable future device types, and invalid Custom Action definitions.

It preserves canonical room, device, and fundamental action ordering, together with the declared order of Custom Actions and their steps.

The input object is not modified in place.

`to_json()` validates and serializes compact canonical JSON.

`from_json()` bounds the incoming byte count before parsing and validating.

`_serialize_validated()` serializes an already validated object without repeating full validation.

The standard CircuitPython JSON parser is used. There is no separate duplicate-key detector.

Pretty-printed JSON may exceed the byte limit even when its compact equivalent fits.

The 16 KiB limit is a storage and parsing boundary, not a guarantee that every theoretically valid configuration can be processed within available heap memory.

Validation does not establish network reachability, equipment compatibility with a specific command, authentication success, or actual equipment state.

## 8. Validation Boundaries and Memory Management

### 8.1 Engineering principle

**Validate at trust boundaries, not repeatedly throughout the application.**

Once configuration data has been validated, use it directly through controlled, read-only accessors.

Do not reconstruct validated configuration objects merely to inspect a room, resolve a device, select a Custom Action, or execute a command.

When verifying persisted data that has already been validated, verify the actual bytes rather than repeatedly parsing and reconstructing the same configuration.

This principle is particularly important on a memory-constrained CircuitPython microcontroller.

### 8.2 Runtime access

The configuration engine owns the active validated RAM snapshot.

Internal accessors include:

- `has_room()`
- `action_details()`
- `custom_action_details()`
- `custom_actions_for_room()`
- `resolve_device()`
- `resolve_endpoint()`
- `command_is_blank()`

These provide efficient access to already validated configuration.

Returned internal object references must be treated as read-only.

`current()` provides a validated copy for consumers requiring an independent configuration object, including management API response construction.

Do not use full configuration copies in frequently executed physical-control or dispatcher paths.

### 8.3 Chapter 12 save optimization

Repeated full validation and serialization previously created substantial temporary allocation pressure during configuration saves.

Observed failures included HTTP memory allocation errors, unsuccessful saves, and uncertain browser save outcomes.

The save pipeline was refactored to:

- Validate the incoming configuration once.
- Serialize the validated object directly.
- Validate the existing primary once for disk consistency.
- Compare validated configuration objects directly.
- Verify temporary and installed files using bounded byte comparisons.
- Avoid reconstructing validated objects during file verification.

Two intentional `gc.collect()` calls remain in the save pipeline:

1. At save entry, before validation and other allocation-intensive work.
2. After incoming validation and serialization, before loading the existing primary.

These collection boundaries reclaim temporary objects before subsequent allocation-intensive operations.

They are intentional production behavior, not leftover debugging instrumentation.

Do not remove or relocate them without regression testing.

### 8.4 Observed results

Following the save refactoring and explicit garbage collection boundaries:

- Twenty consecutive changed browser saves succeeded, covering Save Tests 8 through 27.
- Three additional changed saves succeeded after removal of temporary memory diagnostics.
- Post-cleanup configuration save times were approximately 1.3–1.4 seconds.
- Subsequent configuration GET requests completed in approximately 0.4 seconds.

These tests provide evidence that the observed allocation-failure problem was substantially improved.

They do not establish that CircuitPython's JSON implementation contains a memory leak.

The intermittent HTTP socket-send stall remains a separate unresolved issue.

## 9. Active RAM State and Revisions

`load()` validates a configuration candidate, prepares its adapter cache, activates the cache, and publishes the configuration to module-owned RAM.

A successful load binds the primary file path for subsequent saves.

`revision()` computes a deterministic 32-bit FNV-1a hash over canonical UTF-8 JSON, represented as eight lowercase hexadecimal digits.

The revision is a stale-editor concurrency token, not cryptographic authentication or a globally unique identifier.

The browser obtains the current revision with `GET /api/config` and submits the expected revision with `POST /api/config`.

A revision mismatch rejects the save.

The engine also reads and validates the existing primary and compares it against the active RAM configuration.

An out-of-band disk change rejects the save rather than silently overwriting unexpected data.

### 9.1 Unchanged saves

If the incoming validated configuration equals the active validated configuration, `save()` returns `False`.

An unchanged save does not:

- Rewrite flash.
- Rotate backups.
- Replace the adapter cache.
- Retire adapter sessions.
- Clear pending actions.
- Reset toggle histories.

### 9.2 Changed saves

A changed successful save returns `True`.

The new validated configuration and prepared adapter cache become active.

Existing adapter sessions are retired on a best-effort basis.

The HTTP management save path then resets physical configuration-dependent gesture state, clears pending queue work, and resets toggle histories.

This prevents previously captured physical gestures from continuing to use obsolete device mappings.

Saving configuration does not itself execute configured equipment actions.

## 10. Exact Save and Backup Behavior

`save(config, expected_revision, path=None)` requires a previously successful load.

Saving is permitted only to the primary path bound by that load.

The changed-save pipeline is:

1. Reclaim temporary allocations at save entry.
2. Check the bound path and expected revision.
3. Validate the incoming configuration.
4. Serialize the validated configuration into canonical UTF-8 bytes.
5. Reclaim temporary validation and serialization allocations.
6. Read and validate the existing primary.
7. Compare the existing primary against active RAM.
8. Return without writing if the incoming configuration is unchanged.
9. Prepare the replacement adapter cache.
10. Write and flush the temporary file.
11. Verify the temporary file against the validated serialized bytes.
12. Rotate the existing backup to `.bak.old` when present.
13. Rename the primary to `.bak`.
14. Rename the verified temporary file to the primary filename.
15. Verify the installed primary against the validated serialized bytes.
16. Retire old adapter sessions and publish the prepared cache.
17. Publish the new validated RAM configuration.

Temporary and installed file verification uses bounded 512-byte reads and checks for unexpected trailing data.

The temporary and installed files are not redundantly parsed and validated after exact byte equality has been established.

Individual filesystem renames do not constitute a single power-loss-atomic transaction.

Verified writes and two backup generations reduce risk but do not guarantee recovery from every possible interruption.

The complete interrupted-write matrix remains untested.

### 10.1 Save performance diagnostics

Production `CONFIG PERF` logging reports:

- Validation.
- Disk consistency check and cache preparation.
- Persistence.
- Activation.
- Total configuration save time.

HTTP POST performance logging provides additional management-path timing.

Temporary `SAVE MEM` checkpoints used during Chapter 12 troubleshooting were removed after successful regression testing.

## 11. Startup Loading and Deliberate Recovery

Normal loading attempts candidates in this order:

```text
/clonker/device_config.json
/clonker/device_config.json.bak
/clonker/device_config.json.bak.old
```

Each candidate must parse and validate under the active schema version.

If all candidates fail, startup raises an error rather than fabricating a default configuration.

Loading a valid backup does not automatically overwrite, delete, or repair a damaged primary.

Ordinary saves refuse to overwrite an absent, invalid, or unexpectedly changed primary.

The private `_recover_missing_file()` helper is a separate, explicit operation for a missing primary.

It may rename a valid backup into place but does not replace an existing damaged primary.

It is not part of ordinary automatic loading.

### Recommended recovery procedure

1. Capture the serial error.
2. Preserve the primary and both backup generations externally.
3. Confirm the active firmware schema version.
4. Determine whether the primary is missing, malformed, truncated, or incompatible.
5. Identify a compatible backup or known-good exported configuration.
6. Enter SERVICE through a full power cycle before host-side restoration.
7. Restore the intended primary.
8. Return to DEVICE and cold boot.
9. Confirm loaded rooms, browser configuration, and a harmless real action.

Older schema backups do not become valid Config v5 files merely because they contain valid JSON.

Automatic schema migration is not implemented.

Preserve compatible firmware and configuration pairs when experimenting with schema changes.

## 12. Browser Editor and Management API

The management HTTP service listens on port 9090 in CONFIG mode.

It has no application-level authentication or HTTPS.

Use it only on a trusted LAN. Do not expose the management service to the public internet.

| Request | Purpose |
|---|---|
| `GET /` | Configuration editor |
| `GET /remote.html` | Test Remote |
| `GET /api/config` | Configuration and response-only metadata |
| `POST /api/config` | Revision-protected configuration save |
| `POST /api/action?room=...&action=...` | Enqueue an action |
| `GET /api/clock` | Clock status |
| `POST /api/clock?utc=...` | Browser-provided UTC synchronization |
| `GET /api/flight-recorder` | Flight Recorder download |

Configuration GET response metadata includes:

- `revision`
- `filesystem_writable`
- `device_types`

These are API metadata, not persisted configuration schema fields.

The browser constructs the persisted configuration from `version` and `rooms`.

It includes the expected revision when submitting a save.

The POST handler removes the revision before passing the configuration to the validator.

A read-only filesystem rejects persistent saves.

Action acceptance indicates admission to the shared queue, not completion or equipment-state confirmation.

### 12.1 Editor capabilities

The Config v5 editor supports:

- Adding and removing configured rooms.
- Stable room identifiers.
- Compact typed device rows.
- Registry-driven device-type selectors.
- Device-specific attributes.
- Protocol-aware fundamental command editors.
- Independent toggle command objects.
- Ordered Custom Actions and steps.
- Automatically generated Custom Action identifiers.
- Revision-aware configuration saves.
- Configuration recipe browsing and JSON import.
- Clock tools and access to the Test Remote.

The last configured room cannot be removed.

Changing a device type or command target may make existing commands incompatible. Existing commands are not silently translated into another protocol.

The user must resolve incompatible mappings before saving.

LG SSAP and pointer editing are implemented. LG runtime execution and operational pairing remain deferred.

Apple TV and Fire TV appear as unavailable future device types.

### 12.2 HTTP implementation limits

| Setting | Value |
|---|---:|
| Listener port | 9090 |
| Maximum request bytes | 18432 |
| Maximum header bytes | 2048 |
| Configuration POST body limit | 16640 bytes |
| Receive chunk | 128 bytes |
| Send chunk | 512 bytes |
| Silent-client timeout | 200 ms |
| Active-client timeout | 4 seconds |

The cooperative management server handles one client at a time.

The application-level timeout cannot interrupt a lower-level socket operation that has already blocked.

Chapter 12 testing observed individual socket sends taking approximately ten seconds despite the intended nonblocking operation.

See [Firmware, Network & Clock](FIRMWARE_NETWORK.md) for investigation details.

### 12.3 Save and refresh uncertainty

A successful persistence operation does not guarantee successful delivery of the HTTP response or subsequent configuration refresh.

The browser does not automatically repeat configuration POST requests.

If a save outcome is reported as uncertain:

1. Do not immediately repeat the save.
2. Allow the current HTTP operation to finish.
3. Reload the configuration when the management service responds.
4. Verify whether the intended change was persisted.
5. Continue editing only after obtaining the current configuration and revision.

The intermittent socket-send stall can temporarily affect ordinary GET requests as well as save responses.

Recovery without a reboot was observed during Chapter 12 testing, but the precise trigger and recovery mechanism remain unknown.

Physical controls and outbound Roku and Denon operations were verified to remain functional between stalled management requests.

Responsiveness during an individual blocking socket call has not been established.

## 13. Configuration Recipes

The top-level [recipes/](../recipes/) directory contains maintainer-curated configuration examples.

The hosted recipe browser provides descriptions, JSON previews, and downloads.

The embedded configuration editor provides Browse Recipes and Import JSON controls.

Import replaces the browser's editable configuration contents but does not immediately persist anything to the Pico.

The user reviews and edits the imported configuration before explicitly saving it.

The active device registry and current revision remain management metadata rather than imported recipe data.

### 13.1 Compatibility

The active editor requires Config v5 recipes.

Older Config v4 recipes are rejected rather than silently migrated.

The hosted recipe library is maintained separately from the Pico firmware.

Existing published recipes must be updated to Config v5 before they can be imported into the current editor.

### 13.2 Publishing recipes

A published recipe should preserve:

- Schema version.
- Stable room and device identifiers.
- Device types.
- Fundamental command mappings.
- Custom Action identifiers and names.
- Custom Action and step ordering.
- Protocol payloads.
- Step delays.

Remove or replace sensitive credentials before publication.

For example:

```json
"client_key": "PASTE_OR_PAIR_CLIENT_KEY_HERE"
```

A placeholder may be structurally valid configuration data, but it is not an operational authentication credential.

Do not publish live client keys, passwords, or other private authentication material.

Review device endpoints and replace private information as appropriate for the intended example.

Validate the sanitized recipe against the active schema before publication.

Readable, pretty-printed recipes are preferred for human inspection. The Pico persists compact canonical JSON.

## 14. Configuration and Execution Boundaries

Configuration describes what command is associated with an action.

The dispatcher and One Dumb Queue™ decide when to execute it.

Device adapters and transports decide how to deliver it.

The central device-type registry establishes command compatibility and availability.

The adapter coordinator resolves operational execution behavior using the declared device type and command context.

The queue remains shared by physical controls and browser actions.

### Current operational execution paths

- Generic HTTP.
- Denon persistent TCP volume.
- Roku persistent button taps.
- Roku native button holds.
- Roku volume holds.

The Denon TCP optimization uses recognized fundamental volume commands on port 23.

Roku specialized execution requires the explicitly configured Roku device type and compatible command mapping.

A generic HTTP device does not acquire Roku or Denon specialization merely because its command path resembles one of their commands.

Custom Action steps retain single-command semantics.

LG webOS runtime integration will extend this architecture rather than introduce a separate action executor.

See [Firmware, Network & Clock](FIRMWARE_NETWORK.md) for transport behavior, timing, and failure policy.

## 15. Regression Testing

The test inventory lives in the repository's `firmware/tests/` directory and is deployed to `/tests/` on the Pico.

Chapter 12 introduced the following focused regression suites:

| Test | Purpose | Initial result |
|---|---|---:|
| `test_config_validation.py` | Config v5 validation | 49/49 |
| `test_config_persistence.py` | Persistence and recovery | 56/56 |
| `test_typed_adapters.py` | Typed adapter selection | 56/56 |
| `test_config_activation.py` | Configuration and adapter activation lifecycle | 54/54 |
| `test_typed_queue.py` | Dispatcher and typed command execution | 92/92 |
| `test_typed_physical.py` | Physical gesture and queue integration | 129/129 |
| **Total** | **Initial automated assertions** | **436/436** |

These results represent the individual implementation-stage test runs. They are not a claim that every suite was rerun after every subsequent optimization.

Additional live testing verified Roku, Denon, generic HTTP, room selection, Custom Actions, toggle behavior, editor operations, and repeated browser saves.

### Regression checklist

- Reject malformed and incompatible configuration data.
- Verify serialized size limits and UTF-8 handling.
- Reject stale revisions.
- Preserve state during unchanged saves.
- Verify changed-save persistence and backup rotation.
- Verify adapter activation and session retirement.
- Reject unexpected disk changes.
- Verify backup fallback without implicit repair.
- Confirm SERVICE mode rejects persistent browser saves.
- Confirm DEVICE + CONFIG permits valid saves.
- Exercise repeated saves without rebooting.
- Verify room addition and removal without renumbering.
- Verify stable Custom Action identifiers.
- Verify protocol-aware editor behavior.
- Reject obsolete recipe versions.
- Verify blank endpoint and command behavior.
- Exercise physical and browser action paths.
- Verify Custom Action ordering and delays.
- Verify queue failure cancellation.
- Confirm physical gesture state is reset after configuration changes.
- Verify configuration reload after a cold boot.
- Monitor memory behavior during repeated management operations.

Record what was actually exercised.

Passing focused tests does not establish exhaustive long-duration reliability or compatibility with every possible equipment configuration.

## 16. History and Future Compatibility

| Schema | Historical significance |
|---|---|
| XML v1 | Original configuration foundation |
| JSON v2 | Fixed JSON command mappings |
| JSON v3 | Generic built-in device identifiers |
| JSON v4 | Optional rooms, fourteen fundamental actions, Custom Actions, revision-protected persistence |
| JSON v5 | Typed devices, protocol-aware commands, centralized registry, redesigned editor |

Config v5 is the active schema.

Historical implementation details belong in [Development History](DEVELOPMENT_HISTORY.md).

The original Chapter 12 design and architectural decisions are preserved in [Configuration Redesign](CONFIGURATION_REDESIGN.md).

### Deferred capabilities

- Operational LG webOS adapter integration.
- LG pairing and authenticated session management.
- Additional user-defined device destinations.
- `device-4` and subsequent stable destination identifiers.
- Apple TV protocol integration.
- Amazon Fire TV protocol integration.
- Further investigation of intermittent management socket stalls.

Additional device destinations are not part of the active Config v5 schema.

Future extensions must preserve stable identifiers, explicit device typing, protocol-aware commands, validation boundaries, and the shared action execution architecture.

---

**THE CLONKER 10000**  
*Less sleek. More CLONK.*  
**CLONK! ⚡🔩**
