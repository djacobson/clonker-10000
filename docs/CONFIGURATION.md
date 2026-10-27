
# The Clonker 10000 — Configuration, Persistence & Recovery

**Design reference:** Updated October 22, 2026  
**Hardware:** Raspberry Pi Pico 2 W  
**Runtime:** CircuitPython 10.3.1  
**Active configuration:** JSON v3  
**Status:** Generic built-in device slots, fundamental actions, browser configuration, revision-protected persistence, Dumb Queue™, and outbound HTTP execution operational.

> **Clonker controls actions, not brands. Configuration determines where those actions go.**

---

## 1. Purpose and Scope

This document describes the active Clonker configuration model, its validation rules, browser interface, persistence safeguards, and recovery procedures.

It is the authoritative reference for the current JSON configuration implementation.

The Clonker currently provides:

- One to three configured rooms, using three supported room IDs.
- Three generic built-in device slots per room.
- Fourteen fixed fundamental actions per room.
- Editable HTTP targets, methods, and command paths.
- Separate ON/OFF paths for power and mute actions.
- Strict JSON validation.
- Compact, deterministic serialization.
- Revision-protected browser configuration saves.
- Verified temporary writes and backup rotation.
- Startup fallback to valid configuration backups.
- An in-memory configuration snapshot.
- Shared action scheduling through the Dumb Queue™.
- Real outbound HTTP GET/POST execution.

Custom devices and custom actions are planned but are not yet implemented.

Runtime power/mute toggle direction selection also remains pending.

The active firmware loads:

`/clonker/device_config.json`

through:

`firmware/clonker/device_config_v2.py`

The Python module retains its historical filename. Its `CONFIG_VERSION` constant determines the active schema version.

The previous XML v1 implementation remains in the repository as a historical reference and possible rollback component when paired with compatible older firmware.

### 1.1 Design principles

The configuration system follows several deliberate principles:

1. Configuration describes commands, not equipment brands.
2. Fundamental action identities remain fixed.
3. Device endpoints are independent of action identities.
4. Blank configuration values are valid and intentional.
5. Invalid configurations are rejected rather than partially accepted.
6. Saving configuration must not silently repair or overwrite damaged data.
7. The active configuration in RAM changes only after successful validation and persistence.
8. Execution belongs to the action dispatcher and transport, not the configuration validator.
9. New features should reuse existing mechanisms where practical.
10. Complexity must be justified by demonstrated requirements.

**KISS is an architectural constraint, not merely a preference.**

---

## 2. Active Files and Responsibilities

| File | Responsibility |
|---|---|
| `firmware/clonker/device_config.json` | Checked-in operational configuration example |
| `/clonker/device_config.json` | Active configuration on the Pico |
| `firmware/clonker/device_config_v2.py` | Schema validation, serialization, revisions, persistence, recovery |
| `firmware/clonker/main.py` | Startup configuration loading and cooperative scheduler |
| `firmware/clonker/actions.py` | Shared Dumb Queue™ and fundamental-action execution |
| `firmware/clonker/net/http_transport.py` | Outbound HTTP GET/POST requests |
| `firmware/clonker/net/web.py` | Inbound browser/API HTTP service |
| `firmware/clonker/www/index.html` | Browser configuration editor |
| `firmware/clonker/www/remote.html` | Browser Test Remote |
| `firmware/clonker/legacy/device_config.py` | Historical XML configuration engine |
| `firmware/clonker/legacy/device_config.xml` | Historical XML configuration |

### 2.1 Repository versus Pico configuration

The checked-in JSON and the configuration currently stored on the Pico are separate copies.

Saving through the browser updates the Pico's filesystem and active RAM configuration. It does not create a Git commit.

Conversely, changing the repository JSON does not automatically update the Pico.

Developers must not assume these copies are synchronized.

### 2.2 Schema version versus module filename

The active schema is JSON v3.

The active Python implementation is still named:

`device_config_v2.py`

This is intentional for now. Renaming the module would require updating its imports without adding functionality.

The firmware's authoritative schema constant is:

```python
CONFIG_VERSION = 3
```

The browser editor defines its corresponding constant:

```javascript
const CONFIG_VERSION = 3;
```

These constants must agree.

The startup log reads the Python constant rather than embedding a separate numeric version.

---

## 3. JSON v3 Structure

### 3.1 Root object

The root contains exactly two properties:

- `version`
- `rooms`

The version must be the integer `3`.


The `rooms` object must contain at least one and no more than three rooms.

Supported room IDs are:

- `room-1`
- `room-2`
- `room-3`

Any nonempty subset of these IDs is valid.

Unknown room IDs, duplicate JSON keys, and an empty room collection are not permitted by the intended schema. The current validator explicitly rejects unknown IDs and an empty collection; duplicate-key detection is not currently implemented.

Room IDs remain stable and are used internally for lookup and dispatch. Room names are editable display labels.

The operational configuration currently contains only `room-1` (Den) and `room-2` (Sunroom).

The browser renders only configured rooms. Adding and removing rooms through the editor is not yet implemented.

The firmware constants `MIN_ROOMS`, `MAX_ROOMS`, and `ROOM_IDS` define the supported room count and identities.

### 3.2 Room object

Each room contains exactly:

- `name`
- `devices`
- `actions`
- `custom_actions`

No additional room properties are currently accepted.

### 3.3 Room names

A room name:

- Must be a string.
- Must contain non-whitespace characters.
- May contain at most 40 characters.
- Is trimmed during validation.

The development rooms are Den, Sunroom, and Room 3.

Renaming a room does not change its internal ID or action mappings.

---

## 4. Generic Built-In Devices

### 4.1 The three built-in slots

JSON v3 replaced the original device-category identifiers with generic device-slot identifiers.

| Internal ID | Fixed browser label | Original JSON v2 ID |
|---|---|---|
| `device-1` | TV | `tv` |
| `device-2` | AVR | `avr` |
| `device-3` | Streaming | `streaming` |

These are **built-in device slots**, not enforced equipment types.

The labels describe the original home-theater application.

Nothing in the current endpoint validator or outbound HTTP transport requires `device-1` to be a television, `device-2` to be a receiver, or `device-3` to be a streaming player.

The firmware does not inspect device brands or capabilities.

The browser currently presents the original labels for convenience. They are not user-editable at this stage.

### 4.2 Device collection

Each room's `devices` object contains exactly three entries:

```json
{
  "device-1": "",
  "device-2": "192.168.50.44:8080",
  "device-3": "192.168.50.43:8060"
}
```

All three keys must exist.

An endpoint may be blank.

### 4.3 Endpoint formats

The supported formats are:

- Empty string.
- IPv4 address.
- IPv4 address followed by `:port`.

Examples:

```text
""
192.168.50.44
192.168.50.44:8080
192.168.50.43:8060
```

A blank endpoint means no HTTP destination is configured for that slot.

An endpoint without an explicit port uses HTTP port 80.

When specified, a port must be a decimal integer from 1 through 65535.

IPv4 addresses require four decimal octets, each in the range 0 through 255.

The current endpoint model does not support:

- DNS hostnames.
- IPv6 addresses.
- HTTPS URLs.
- Authentication credentials.
- Device discovery.
- Protocol-specific connection parameters.

These restrictions reflect the current simple HTTP transport, not a permanent restriction on the Clonker's goals.

### 4.4 Development equipment

The October 2026 test configuration uses:

| Room | Slot | Equipment | Endpoint |
|---|---|---|---|
| Den | `device-2` | Denon AVR-X3700H | `192.168.50.44:8080` |
| Den | `device-3` | Roku Ultra 4800X | `192.168.50.43:8060` |
| Sunroom | `device-2` | Denon AVR-X1800H | `192.168.50.40:8080` |
| Sunroom | `device-3` | Roku Ultra 4670X | `192.168.50.28:8060` |

The TV endpoints are currently blank.

Room 3 is a supported but currently unconfigured room ID.

These addresses are development examples, not guaranteed permanent network assignments.

### 4.5 Future custom devices — agreed design

**Status:** Design agreed; not implemented in JSON v3.

The three built-in destinations remain:

```text
device-1 — TV
device-2 — AVR
device-3 — Streaming
```

Their identities and home-theater-oriented fundamental-action interface are reserved. Their endpoints and action mappings remain editable.

Additional user-defined destinations will use the same ID namespace, beginning with `device-4`.

Examples:

```text
device-4 — Joey's PS5
device-5 — Lighting Controller
```

Custom destinations will be stored in an optional, separate `custom_devices` object within each configured room. This avoids restructuring the existing `devices` object or the current home-theater editor.

Conceptual future JSON fragment:

```json
"custom_devices": {
  "device-4": {
    "name": "Joey's PS5",
    "endpoint": "192.168.50.70:80"
  }
}
```

The example is illustrative only. It is not accepted by the current validator and does not imply that a PS5 exposes a compatible HTTP API.

Agreed rules:

- `custom_devices` may be omitted when unused.
- Custom IDs begin at `device-4` and remain stable.
- Removing one custom destination must not renumber another.
- Names are editable display strings, never execution identifiers.
- Each custom destination has a configured endpoint.
- Fundamental actions continue targeting only built-in destinations.
- Custom action steps may target built-in or custom destinations.
- All destinations share the existing HTTP transport and a common resolution mechanism.
- No device-type registry, capability model, discovery system, or device-specific execution behavior is required.

A future custom-device editor may provide add, edit, and remove controls without changing the existing TV/AVR/Streaming editing interface.

The exact capacity limit and detailed validation rules will be settled when custom destinations are implemented, using named constants.

**Implementation order:** Custom/compound actions first, using existing built-in destinations for live tests. Custom destinations follow when needed.

No JSON schema change is required until the feature is implemented.

---

## 5. Fundamental Actions

Each room contains exactly fourteen fundamental actions.

| Action ID | Meaning |
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
| `play-pause` | Play / Pause |
| `skip-back` | Skip backward |
| `skip-forward` | Skip forward |
| `power-toggle` | Toggle power |

These IDs are fixed.

The validator rejects missing, extra, or unknown fundamental actions.

Channel Up, Channel Down, Guide, and equipment-specific functions are not fundamental actions. They may eventually be represented as custom actions.

### 5.1 Ordinary action structure

Twelve fundamental actions use exactly:

- `target`
- `method`
- `path`

Example:

```json
"volume-up": {
  "target": "device-2",
  "method": "GET",
  "path": "/goform/formiPhoneAppDirect.xml?MVUP"
}
```

### 5.2 Toggle action structure

The remaining two actions are:

- `mute-toggle`
- `power-toggle`

They use exactly:

- `target`
- `method`
- `on_path`
- `off_path`

Example:

```json
"mute-toggle": {
  "target": "device-2",
  "method": "GET",
  "on_path": "/goform/formiPhoneAppDirect.xml?MUON",
  "off_path": "/goform/formiPhoneAppDirect.xml?MUOFF"
}
```

Both directions share one target and HTTP method.

The schema and browser editor support these fields.

Runtime ON/OFF direction selection is not yet implemented.

### 5.3 Targets

Fundamental actions may currently target only:

- `device-1`
- `device-2`
- `device-3`

There are no action-specific device-type restrictions.

For example, the validator does not require volume actions to target `device-2`.

The target simply selects an endpoint.

### 5.4 HTTP methods

Allowed methods:

- `GET`
- `POST`

Methods must be uppercase.

The current outbound transport uses simple HTTP requests. It does not support arbitrary request bodies, custom authentication, TLS, or user-configurable headers.

### 5.5 Command paths

Paths must be strings.

Maximum length: 512 characters.

An empty path is valid.

The validator enforces type and length, but does not implement comprehensive URL or command-path security validation.

A configured path is not evidence that the target device supports the command.

---

## 6. Blank Actions and No-Op Behavior

Blank endpoints and paths are deliberate configuration features.

They allow partially configured rooms and actions without requiring dummy commands.

For ordinary fundamental actions:

- Blank endpoint: no HTTP request.
- Blank path: no HTTP request.
- Both blank: no HTTP request.

The dispatcher logs an unconfigured no-op when the queued action executes.

A valid but unconfigured action may still be accepted into the queue.

Therefore:

**Queued does not mean transmitted.**

And:

**HTTP success does not prove equipment state changed.**

For toggle actions, runtime direction selection remains deferred. They currently do not transmit ON/OFF commands.

---

## 7. Toggle Direction — Agreed Future Behavior

**Schema:** Implemented  
**Browser fields:** Implemented  
**Runtime direction selection:** Pending

The intended initial toggle implementation uses small, volatile command-direction history.

History is independent for each room and each toggle action.

Conceptually:

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

Agreed behavior:

1. Unknown history initially selects ON.
2. Successful ON submission makes OFF the next direction.
3. Successful OFF submission makes ON the next direction.
4. Failed requests do not advance history.
5. Blank paths and endpoints do not advance history.
6. History is not persisted.
7. Restart resets history to unknown.

This is command history, not equipment-state detection.

Other remotes, HDMI-CEC, applications, or physical controls may change equipment state without Clonker knowing.

Devices with a native toggle command may use the same path for both `on_path` and `off_path`.

The first implementation will not query equipment state or reconcile external changes.

The dispatcher owns direction selection; the HTTP transport owns transmission and errors.

---


## 8. Custom Actions and Compound Actions

### 8.1 Current implementation

Clonker Config v4 supports executable, user-defined custom actions.

Each configured room contains a `custom_actions` array. The array may be empty or contain up to sixteen custom actions.

Custom actions are independent of the fourteen fixed fundamental actions.

Each custom action has:

- A stable, room-local action ID.
- An editable display name.
- One to sixteen ordered command steps.

A custom action containing multiple command steps is also called a compound action.

A single-step custom action remains a valid custom action.

The browser configuration editor supports creating, editing, deleting, validating, and saving custom actions.

The browser Test Remote loads the selected room's saved custom actions and provides a dropdown and separate Run button.

### 8.2 Terminology

| Term | Meaning |
|---|---|
| Fundamental action | One of the fourteen fixed remote-control actions |
| Custom action | A user-defined, named action |
| Compound action | A custom action containing multiple ordered command steps |
| Command step | One HTTP operation within a custom action |
| Destination | A configured device endpoint |
| Post-command wait | Delay before the next step becomes eligible |

Custom actions currently target built-in device slots. Optional user-defined custom devices remain future work.

### 8.3 Configuration structure

A custom action is represented as an object in the room's `custom_actions` array.

Example:

```json
{
    "name": "Movie",
    "id": "custom-action-1",
    "steps": [
        {
            "target": "device-3",
            "path": "/keypress/Home",
            "method": "POST",
            "wait_after_ms": 3000
        },
        {
            "target": "device-2",
            "path": "/goform/formiPhoneAppDirect.xml?MSQUICK1",
            "method": "GET",
            "wait_after_ms": 0
        }
    ]
}
```

The example sends Roku Home, waits three seconds, and then invokes Denon Quick Select 1.

The fields are:

| Field | Purpose |
|---|---|
| `id` | Stable identifier used to dispatch the custom action |
| `name` | Human-readable display name |
| `steps` | Ordered list of command-step objects |
| `target` | Built-in device ID |
| `method` | HTTP `GET` or `POST` |
| `path` | HTTP command path |
| `wait_after_ms` | Nonnegative delay after the step, in milliseconds |

The active field name is `wait_after_ms`, not the earlier proposed `wait_ms`.

### 8.4 Validation and limits

Clonker Config v4 enforces:

- A maximum of sixteen custom actions per room.
- One to sixteen steps per custom action.
- Custom-action IDs of no more than forty characters.
- Custom-action names of no more than sixty characters.
- Valid, configured built-in device targets.
- HTTP `GET` or `POST` methods.
- Required command paths.
- Post-command waits from 0 through 60,000 milliseconds.
- A zero wait on the final command step.
- Unique custom-action IDs within each room.
- The overall 8,192-byte configuration limit.

Custom-action IDs are stable after their first successful save. Names and steps remain editable.

The firmware validator is authoritative. Browser-side validation provides earlier feedback but must remain aligned with firmware rules.

### 8.5 Runtime execution

Custom actions reuse the existing Dumb Queue™ and outbound HTTP transport.

The implementation does not introduce a separate macro executor.

When a custom action is submitted:

1. The dispatcher resolves the selected room and custom-action ID.
2. The custom action enters the shared action queue.
3. The executor processes command steps in their configured order.
4. Each step sends its configured HTTP request.
5. Any configured post-command wait delays eligibility of the next step.
6. The action completes after its final step.

Waiting is cooperative rather than a blocking sleep.

The design allows unrelated eligible actions to be processed while a compound action is waiting. Additional live interleaving regression testing remains on the development checklist.

The queue and transport retain responsibility for command execution, errors, and cancellation behavior.

### 8.6 Verified live execution

During Chapter 4, the Sunroom Movie custom action successfully controlled two different network devices.

The recorded execution was:

```text
QUEUED: Sunroom / custom-action-1
Roku Home: HTTP 200
Next step after 3000 ms
Denon Quick Select 1: HTTP 200
CUSTOM COMPLETE: Sunroom / custom-action-1
```

The Roku returned to Home and the Denon selected its configured Quick Select 1 settings.

This established successful end-to-end execution of a persisted, browser-configured, multi-device custom action.

### 8.7 Deliberate limitations

The initial custom-action implementation does not include:

- Loops.
- Conditional branches.
- Nested custom actions.
- Arbitrary scripting.
- Automatic rollback or undo.
- Complex dependency graphs.
- User-defined custom-device destinations.

These omissions are intentional. The implementation favors predictable, bounded command sequences.

### 8.8 Future custom-device integration

Custom actions currently reference `device-1`, `device-2`, or `device-3`.

Future custom-device support may introduce additional stable destination IDs without changing the fundamental-action identities.

Fundamental actions remain associated with the three built-in device slots.

Custom-device deletion and reference validation must prevent accidental retargeting of existing custom actions.

The generic destination architecture is intended to support future protocols, including Apple TV, without assuming that every protocol can use the existing HTTP GET/POST transport.

---

## 9. Example JSON v3 Configuration

The following example illustrates the current structure of one room.

**This is an incomplete example, not a deployable configuration.**

A valid operational configuration requires at least one configured room and all fourteen fundamental actions within each configured room.

```json
{
  "version": 3,
  "rooms": {
    "room-1": {
      "name": "Den",
      "devices": {
        "device-1": "",
        "device-2": "192.168.50.44:8080",
        "device-3": "192.168.50.43:8060"
      },
      "actions": {
        "volume-up": {
          "target": "device-2",
          "method": "GET",
          "path": "/goform/formiPhoneAppDirect.xml?MVUP"
        },
        "home": {
          "target": "device-3",
          "method": "POST",
          "path": "/keypress/Home"
        },
        "mute-toggle": {
          "target": "device-2",
          "method": "GET",
          "on_path": "/goform/formiPhoneAppDirect.xml?MUON",
          "off_path": "/goform/formiPhoneAppDirect.xml?MUOFF"
        }
      },
      "custom_actions": []
    }
  }
}
```

The full operational JSON is maintained in:

`firmware/clonker/device_config.json`

Readable samples are maintained separately under `docs/samples/`.

The operational file is normally stored in compact form.

---

## 10. Strict Validation

The configuration engine validates the entire object before publishing it.

Validation rejects:

- Missing or unknown root fields.
- Unsupported schema versions.
- Missing or extra rooms.
- Missing or unknown room properties.
- Invalid room names.
- Missing or extra built-in device keys.
- Invalid endpoint types or formats.
- Missing or unknown fundamental actions.
- Missing or extra action properties.
- Invalid action targets.
- Unsupported HTTP methods.
- Invalid command-path types.
- Paths exceeding the length limit.
- Nonempty custom-action arrays.
- Oversized serialized configurations.

The validator returns a normalized, ordered copy.

It does not modify the submitted object in place.

### 10.1 Active limits

| Constant | Value |
|---|---:|
| `CONFIG_VERSION` | `3` |
| `MAX_CONFIG_BYTES` | `8192` |
| `MAX_ROOM_NAME_LENGTH` | `40` |
| `MAX_PATH_LENGTH` | `512` |
| Fixed rooms | `3` |
| Built-in device slots per room | `3` |
| Fundamental actions per room | `14` |

The byte limit applies to UTF-8 JSON.

The October 22 compact development configuration was approximately 3.7 KB, leaving room for future schema extensions.

The 8 KB limit must be reconsidered when implementing custom devices and compound actions.

### 10.2 Duplicate JSON keys

The engine uses CircuitPython's standard JSON parser.

It does not implement a custom duplicate-key detector.

Hand-edited JSON containing duplicate keys should not be treated as reliably validated input.

This is an accepted limitation of the current implementation.

### 10.3 Validation boundaries

Schema validation is not a device capability check.

It does not establish that:

- An IP address is reachable.
- A command exists on the target device.
- A command path is safe for arbitrary equipment.
- A request will succeed.
- A successful request will change equipment state.

These concerns belong to transport execution, equipment behavior, and future protocol-specific integrations.

---

## 11. Active Configuration in RAM

The configuration engine maintains one authoritative validated snapshot:

`_current`

The module also records the primary path selected by the successful load:

`_current_path`

### 11.1 Public and internal access

| Function | Purpose |
|---|---|
| `load(path=None)` | Load primary or valid backup and bind save path |
| `current()` | Return a validated copy of active configuration |
| `room(room_id)` | Return a copy of a configured room |
| `action_details(room_id, action_id)` | Fast internal access to active room/action references |
| `validate_config(config)` | Validate and normalize configuration |
| `to_json(config)` | Produce canonical compact JSON |
| `from_json(contents)` | Parse and validate bounded JSON |
| `revision(config=None)` | Calculate configuration revision |
| `save(config, expected_revision, path=None)` | Revision-protected save |

### 11.2 Read-only internal references

`action_details()` returns references into the active configuration.

This avoids repeatedly copying the entire configuration for every queued command.

Callers must treat these references as read-only.

Only the configuration module may publish or replace the authoritative configuration.

### 11.3 Current configuration at execution time

Queued fundamental actions contain identifiers, not copied endpoint or command definitions.

The dispatcher resolves the active configuration when an action executes.

This keeps queued tasks small and avoids stale configuration references.

A successful configuration change clears pending queue entries.

---

## 12. Canonical JSON and Revision Protection

### 12.1 Canonical serialization

`to_json()` validates and serializes configuration using compact separators and a deterministic field order.

Whitespace differences in submitted JSON do not create meaningful configuration changes.

### 12.2 Revision calculation

The revision is an eight-character hexadecimal value derived from a 32-bit FNV-1a hash over canonical UTF-8 JSON.

The browser receives this revision with the configuration.

A save must submit the revision originally loaded by that browser tab.

### 12.3 Stale-tab protection

If another tab saves a different configuration first, the original tab's revision becomes stale.

Its subsequent save is rejected with:

```text
Configuration revision mismatch.
Changes not saved. Refresh page.
```

The stale tab must refresh before saving again.

This prevents accidental overwriting of newer browser changes.

### 12.4 Unchanged configurations

If the submitted canonical configuration equals the active configuration, `save()` returns `False`.

An unchanged configuration does not require another file rotation.

Merely adding and removing a space in the browser does not constitute a persistent configuration change if the final values are identical.

### 12.5 Revision limitations

The revision is a lightweight change detector, not an authentication token or cryptographic integrity guarantee.

It does not replace filesystem ownership controls or trusted-network assumptions.

---

## 13. Configuration Saving

Configuration saves are allowed only when the Pico filesystem is writable by CircuitPython.

The browser reports filesystem writability and disables its Save control when the filesystem is read-only.

### 13.1 Save sequence

The engine performs these checks and operations:

1. Confirm configuration was previously loaded.
2. Confirm the save path matches the path bound by `load()`.
3. Verify the submitted revision matches the active revision.
4. Validate the submitted configuration.
5. Serialize and check the byte limit.
6. Re-read and validate the primary configuration on disk.
7. Confirm disk contents still represent the active configuration.
8. Detect unchanged configuration.
9. Write a temporary configuration file.
10. Flush and read back the temporary file.
11. Verify temporary-file bytes and parsed contents.
12. Rotate backup generations.
13. Install the new primary configuration.
14. Verify the installed primary.
15. Publish the new validated configuration in RAM.

The HTTP layer clears the Dumb Queue™ after a successful changed save.

### 13.2 Why the disk comparison matters

The engine does not assume that the file on disk still matches what was loaded.

If the primary configuration has been modified outside the browser, a normal browser save must not overwrite it silently.

This protects against conflicting USB edits and other out-of-band changes.

### 13.3 Filesystem ownership

The browser reports two operational conditions:

- **Service/USB mode:** Pico filesystem read-only to CircuitPython; browser saving unavailable.
- **Device mode:** Pico filesystem writable to CircuitPython; browser saving available.

These filesystem modes are distinct from the application CONFIG/RUN switch that controls whether the HTTP management server is active.

Changing application mode does not automatically grant filesystem write access.

---

## 14. Backup Rotation

The configuration engine maintains up to three generations:

```text
device_config.json
device_config.json.bak
device_config.json.bak.old
```

On a changed save:

```text
Existing .bak       -> .bak.old
Existing primary    -> .bak
Verified temporary  -> primary
```

A missing previous backup is acceptable.

The current primary must validate before the engine rotates backups.

### 14.1 Important limitations

The rotation uses individual filesystem rename operations.

It is not a fully atomic multi-file transaction against sudden power loss.

The engine reduces risk through validation and verified temporary writes, but cannot guarantee recovery from every interruption.

The complete power-loss failure matrix has not been exhaustively tested.

### 14.2 Version compatibility

JSON v3 validation rejects JSON v2 configuration files.

An old `.bak` from v2 is not a valid fallback under the active v3 firmware.

During schema transitions, retain external backups of the previous working firmware/configuration pair.

Do not assume that a historical backup is compatible merely because it contains valid JSON.

---

## 15. Startup Loading and Recovery

### 15.1 Load order

At startup, `load()` attempts:

1. `device_config.json`
2. `device_config.json.bak`
3. `device_config.json.bak.old`

Each candidate must pass the active schema validation.

If a candidate fails, the engine reports the failure and tries the next one.

If no valid candidate exists, startup raises an error rather than silently creating a replacement configuration.

### 15.2 Backup fallback is not automatic repair

Loading a backup makes that validated configuration available in RAM.

It does not overwrite, delete, or silently repair the primary file.

This distinction is deliberate.

The normal save path also refuses to overwrite a missing or invalid primary merely because startup succeeded using a backup.

### 15.3 Explicit recovery

The module includes a separate recovery helper for a missing primary file.

Recovery is intentionally distinct from normal loading and saving.

A damaged existing primary is not silently replaced.

Manual intervention remains appropriate when a primary file is corrupted or incompatible.

### 15.4 Recommended recovery procedure

If configuration loading fails:

1. Inspect the serial console for the rejected file and reason.
2. Preserve the current primary and backups before changing them.
3. Verify the firmware's `CONFIG_VERSION`.
4. Check whether the JSON uses the corresponding schema.
5. Inspect the primary file for truncation or malformed JSON.
6. Check backup compatibility.
7. Restore a known-good matching configuration if necessary.
8. Restart and verify successful validation.
9. Test a harmless fundamental action before resuming normal use.

Avoid deleting all configuration generations before identifying the failure.

---

## 16. Browser Configuration Editor

The configuration editor is served from:

`/clonker/www/index.html`

It operates through the Pico's HTTP management service.

### 16.1 Current capabilities

The editor supports:

- Display of one to three configured rooms; unused room slots are omitted.
- Editable room names.
- Built-in device endpoint addresses.
- Fourteen fundamental actions per room.
- Target selection.
- GET/POST selection.
- Ordinary command paths.
- Separate toggle ON/OFF paths.
- Configuration loading.
- Revision-aware saving.
- Filesystem writability reporting.
- Save error messages.
- Configuration refresh.

### 16.2 Fixed device labels

The browser internally uses:

```javascript
const DEVICE_IDS = [
    "device-1",
    "device-2",
    "device-3"
];
```

And currently displays:

```javascript
const DEVICE_LABELS = {
    "device-1": "TV",
    "device-2": "AVR",
    "device-3": "Streaming"
};
```

The labels are presentation-only.

They do not appear as device-type restrictions in the firmware.

### 16.3 Browser version checking

The browser defines one `CONFIG_VERSION` constant.

It uses that constant when:

- Validating a configuration response.
- Constructing a configuration save request.

This prevents separate hardcoded load and save versions from drifting apart.

The Python and JavaScript constants must still be updated together during a future schema change.

### 16.4 Browser limitations

The current editor does not support:

- Adding custom devices.
- Editing custom actions.
- Constructing compound action sequences.
- Editing built-in device labels.
- Adding rooms.
- Adding fundamental action IDs.

These capabilities are not implied by the existing placeholders.

---

## 17. HTTP Management API

The management server is implemented in:

`firmware/clonker/net/web.py`

The current listening port is:

`9090`

The server is intentionally small and cooperative.

It services one client at a time and advances accept, receive, or send work through repeated `poll()` calls.

### 17.1 Endpoints

| Request | Purpose |
|---|---|
| `GET /` | Browser configuration editor |
| `GET /remote.html` | Browser Test Remote |
| `GET /api/config` | Active configuration, revision, filesystem status |
| `POST /api/config` | Validate and save configuration |
| `POST /api/action?room=...&action=...` | Enqueue a fundamental action |
| `GET /api/clock` | Current clock status |
| `POST /api/clock?utc=...` | Synchronize clock from browser |

### 17.2 Configuration GET

`GET /api/config` returns the active configuration plus response-only metadata:

- `revision`
- `filesystem_writable`

These metadata fields are not stored in `device_config.json`.

The browser uses them to decide whether saving is available and which revision to submit.

### 17.3 Configuration POST

`POST /api/config` submits the configuration plus its expected revision.

The HTTP layer removes the request-only revision before passing the configuration to the persistence engine.

The response indicates whether the configuration changed and supplies the current revision.

Schema and revision failures return error responses rather than silently accepting invalid data.

A changed save clears pending queued actions.

### 17.4 Action POST

Example:

```text
POST /api/action?room=room-2&action=volume-up
```

The server validates the request shape and delegates action validation to the dispatcher.

The action response reports queue acceptance and configuration information.

It does not wait for physical equipment-state confirmation.

### 17.5 Request limits

Current HTTP limits include:

| Limit | Value |
|---|---:|
| Management port | `9090` |
| Maximum request bytes | `10240` |
| Maximum header bytes | `2048` |
| I/O chunk bytes | `512` |
| Silent-client timeout | `0.5` seconds |
| Active-client timeout | `4.0` seconds |

These are implementation limits, not public protocol guarantees.

### 17.6 Security boundary

The current management server is intended for a trusted local development network.

It does not provide general-purpose web authentication or HTTPS.

It should not be exposed directly to the public internet.

---

## 18. Dumb Queue™ and Execution

The shared action dispatcher is implemented in:

`firmware/clonker/actions.py`

The queue operates independently of the browser configuration editor.

### 18.1 Fundamental action dispatch

A fundamental action request:

1. Validates room and action IDs.
2. Reads the active action configuration.
3. Determines whether the action appears configured.
4. Enqueues a small task containing identifiers and due time.
5. Returns queue acceptance information.

The queue does not store copies of the configured HTTP endpoint or command path.

### 18.2 Execution

During `poll()`:

1. Find the first eligible queued task.
2. Remove it from the queue.
3. Resolve the current room and action configuration.
4. Determine the endpoint and command.
5. Skip blank/unconfigured commands safely.
6. Send configured ordinary actions through the HTTP transport.
7. Record a small diagnostic result.

A poll executes at most one eligible task.

Future-dated tasks do not block independent eligible tasks.

### 18.3 Current queue behavior

| Property | Behavior |
|---|---|
| Capacity | 128 tasks |
| Scheduling | Monotonic due times |
| Execution | At most one eligible task per poll |
| Configuration resolution | At execution time |
| Automatic retries | None |
| Network failure | Clear remaining queue |
| Configuration change | Clear remaining queue |
| Toggle execution | Deferred |

The queue's name is deliberately descriptive.

It does not need to know whether a destination is a Denon, Roku, television, or future custom device.

### 18.4 Outbound HTTP transport

The transport sends simple GET or POST requests to configured IPv4 endpoints.

It opens a fresh TCP connection per request.

It uses bounded network timeouts and reports HTTP status and elapsed time.

Connection reuse and advanced protocol support are deferred until actual requirements justify them.

### 18.5 HTTP success versus equipment success

An HTTP 200 response establishes that the remote HTTP endpoint responded successfully.

It does not necessarily establish that:

- The device changed volume.
- The requested input changed.
- Playback started.
- Power state changed.
- The equipment remains in the requested state.

Where practical, equipment behavior should be observed during testing.

---

## 19. Tested Milestones

### 19.1 JSON v2 foundation — October 2026

The earlier JSON v2 work established:

- Strict configuration validation.
- Compact serialization.
- Revision calculation.
- Browser configuration editing.
- Save-path binding.
- Verified temporary writes.
- Backup rotation.
- Startup fallback.
- Out-of-band disk-change detection.
- Stale-tab save rejection.

The October 18 toggle-field extension was an intentional breaking change during the experimental v2 period.

These are historical implementation milestones, not descriptions of the active schema version.

### 19.2 Real HTTP execution — October 21, 2026

Chapter 3 established working outbound HTTP commands from the Pico.

Verified tests included:

- Denon volume commands.
- Roku navigation commands.
- A five-command volume burst.
- Dumb Queue™ scheduling.
- HTTP 200 responses.
- Failure handling and queue recovery.

The command dispatcher and transport became operational before the v3 device-ID refactor.

### 19.3 JSON v3 generic-device refactor — October 22, 2026

Chapter 4 Phase 1 changed the built-in device identifiers:

```text
tv        -> device-1
avr       -> device-2
streaming -> device-3
```

The browser retained the original fixed display labels.

The schema version advanced to 3.

No changes were required to the Dumb Queue™ or outbound HTTP transport.

Regression testing verified:

- Successful JSON v3 startup.
- Correct room and device diagnostics.
- Configuration editor loading and rendering.
- Fixed TV/AVR/Streaming labels.
- Denon volume command execution.
- Roku Back and Home command execution.
- Successful browser configuration saves.
- Configuration persistence after restart.
- Version 3 backup creation.
- Stale-tab revision rejection.
- Successful refresh and subsequent save.

The initial refactor exposed two browser version-2 references, both corrected.

A subsequent startup-log cleanup exposed a missing `settings` assignment, which was restored and successfully retested.

These findings reinforce the project's incremental test discipline.

**Result:** The generic built-in device-ID refactor is operational and regression-tested.

---

## 20. Planned Development


### 20.1 Custom devices — deferred implementation

The design is agreed in Section 4.5.

Implementation is deferred until custom destinations are useful for testing or real operation.

The future implementation will introduce optional named destinations using `device-4` onward, with stable identities, validated endpoints, and shared destination resolution.

The existing home-theater editor and fundamental-action model will remain intact.

### 20.2 Custom and compound actions — implemented

Custom and compound actions were implemented during Chapter 4 as part of Clonker Config v4.

Each custom action has a stable ID, editable display name, and ordered command steps targeting configured built-in devices.

Each step specifies an HTTP GET/POST operation and may include a post-command wait.

Execution reuses the existing Dumb Queue™ and outbound HTTP transport. No separate macro executor was introduced.

The browser configuration editor supports creating, editing, deleting, validating, and saving custom actions.

The browser Test Remote supports room-specific custom-action selection and explicit execution.

Real Roku and Denon compound-action execution has been verified.

Additional regression testing remains desirable, particularly command interleaving during waits and negative validation cases.

Custom-device targets remain deferred until optional custom devices are implemented.

### 20.3 Runtime toggles

Implement the agreed volatile ON/OFF command-direction history.

Avoid treating command history as authoritative equipment state.

### 20.4 Physical controls

Connect the existing fundamental-action dispatcher to physical buttons, encoders, and room-selection hardware.

Keep hardware input handling separate from HTTP command construction.

### 20.5 Future protocols

Apple TV compatibility remains an explicit objective.

Its eventual implementation may require protocol-specific authentication, connection management, and command handling beyond the current simple HTTP transport.

Do not invent Apple TV configuration requirements before selecting and testing an actual control implementation.

The generic destination architecture should make future integrations easier without requiring all devices to share one protocol.

---

## 21. Historical Compatibility Notes

### XML v1

The original XML implementation established important ideas around configuration editing, persistence, and recovery.

It is no longer the active configuration format.

### Clonker Config v2

Clonker Config v2 established the JSON-based configuration engine and browser integration.

Its original built-in device identifiers were:

```text
tv
avr
streaming
```

Those identifiers are historical and are not accepted as built-in device keys or fundamental-action targets by the active Clonker Config v4 validator.

### Clonker Config v3

Clonker Config v3 introduced generic built-in device identifiers while retaining the fundamental-action structure.

It became operational on October 22, 2026, during Chapter 4 Phase 1.

The built-in identifiers changed to:

```text
device-1
device-2
device-3
```

No automatic v2-to-v3 migration was implemented. During development, the configuration was intentionally replaced with a matching v3 file.

### Clonker Config v4

Clonker Config v4 introduced executable custom actions and ordered HTTP command steps.

Each configured room retains its fourteen fundamental actions and may additionally define named custom actions in the `custom_actions` array.

Custom actions have stable IDs, editable names, and ordered command steps with optional post-command waits.

Execution reuses the existing Dumb Queue™ and outbound HTTP transport.

The browser configuration editor supports creating, editing, deleting, validating, and saving custom actions. The Test Remote supports room-specific selection and execution.

Clonker Config v4 became operational and was successfully tested during Chapter 4 in October 2026.

It is the active configuration schema as of October 27, 2026.

JSON remains the serialization format. The root `"version"` field identifies the Clonker Config schema version, independently of firmware and CircuitPython versions.

No automatic v3-to-v4 migration was introduced.

Earlier configurations remain recoverable through Git history and separately preserved backups when paired with compatible firmware.

---

## 22. Developer Checklist

Before changing the configuration schema:

- Identify every affected Python constant and validation rule.
- Identify browser load and save assumptions.
- Update the operational JSON and readable samples.
- Check whether backups from the previous schema remain compatible.
- Confirm the active module and browser agree on `CONFIG_VERSION`.
- Preserve a known-good firmware/configuration pair.
- Avoid introducing migration machinery without a real requirement.

After changing the schema:

- Restart the Pico.
- Confirm the configuration loads.
- Inspect room and device diagnostics.
- Open the browser configuration editor.
- Verify all rooms and actions render.
- Test representative Denon and Roku commands.
- Save a harmless configuration change.
- Verify persistence after restart.
- Inspect backup generation.
- Test stale-tab revision rejection.
- Restore the intended configuration.
- Update current-state documentation.
- Record significant milestones in `DEVELOPMENT_HISTORY.md`.

Even apparently cosmetic startup changes deserve a smoke test.

---

## 23. Current Engineering Position

**As of October 27, 2026 — Chapter 4, Clonker Config v4 operational.**

Clonker Config v4 is the active versioned configuration schema. JSON remains its storage format, and the root `"version": 4` identifies the schema version.

**Implemented and tested:**

- Clonker Config v4, with fixed fundamental actions and executable user-defined custom actions.
- Up to three supported room IDs, with Den and Sunroom currently configured.
- Three generic built-in device slots per room.
- Fourteen fundamental actions per room.
- Custom actions with stable IDs, editable names, and ordered command steps.
- Browser creation, editing, deletion, validation, and persistence of custom actions.
- Room-specific custom-action selection and explicit Run execution in the browser Test Remote.
- Cooperative post-command waits using the shared Dumb Queue™.
- Strict configuration validation and size enforcement.
- Revision-protected browser saves.
- Verified temporary writes, backup rotation, and restart persistence.
- Stale-tab conflict rejection.
- Outbound HTTP GET/POST execution.
- Real Denon and Roku control.
- Successful live two-device compound-action execution.

The first verified live compound action used the Sunroom Roku Ultra and Denon AVR-X1800H:

1. Send Roku Home using HTTP POST.
2. Wait 3,000 milliseconds after the command completes.
3. Execute Denon Quick Select 1 using HTTP GET.

Both commands returned HTTP 200, and the connected equipment responded as expected.

The fully populated Roku/Denon configuration contains:

| Room | Fundamental actions | Custom actions | Command steps |
|---|---:|---:|---:|
| Den | 14 | 3 | 6 |
| Sunroom | 14 | 2 | 4 |
| **Total** | **28** | **5** | **10** |

A readable sample is maintained at:

`docs/samples/device_config_roku_denon_sample.json`

The operational configuration is stored as compact JSON and remains subject to the 8,192-byte size limit.

**Supported in configuration, but not yet operational at runtime:**

- Separate ON/OFF command paths for power and mute.
- Runtime selection of the appropriate toggle direction.

The configuration editor can store both paths, but the dispatcher currently defers power/mute toggle actions because runtime direction tracking has not been implemented.

**Remaining development:**

- Runtime power/mute direction history, without assuming knowledge of actual equipment state.
- Optional user-defined custom devices.
- Physical buttons, encoders, and room-selection controls.
- Apple TV protocol integration.
- Additional scheduler-interleaving and negative validation tests.
- Minor browser Test Remote refinements.

Custom actions currently target the three built-in device slots. Custom-device support remains intentionally deferred.

Clonker Config v4 extends the established configuration, queue, and HTTP transport architecture without introducing a separate macro execution subsystem.

> **The Clonker does not need to understand a device's personality. It needs a destination, a command, and the good sense to stay out of the way.**

**Less sleek. More CLONK.**
