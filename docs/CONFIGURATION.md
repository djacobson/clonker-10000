# The Clonker 10000 — Configuration, Persistence & Recovery

**Design reference:** November 7, 2026  
**Platform:** Raspberry Pi Pico 2 W / CircuitPython 10.3.1  
**Active schema:** Clonker Config v4 (JSON)  
**Baseline:** Chapter 7 — three configured rooms, physical navigation/playback controls, Roku button holds, Dumb Queue™, and protocol adapters operational

> Clonker controls intent, not reality. A command can be accepted, transmitted, and acknowledged without proving what the television actually did.

---

## 1. Scope and sources of truth

This is the authoritative **configuration schema, validation, persistence, and recovery** reference. Its implementation is `firmware/clonker/device_config_v2.py`, whose historical filename does **not** indicate the active schema version. `CONFIG_VERSION = 4` is authoritative. The browser editor must agree.

The source repository holds maintained firmware and an example configuration; the running Pico's `/clonker/device_config.json` is the active, potentially newer, user-edited configuration. Never overwrite that file casually during firmware deployment.

Other responsibilities: [Architecture](ARCHITECTURE.md) covers boundaries; [Firmware, Network & Clock](FIRMWARE_NETWORK.md) covers execution, queue, adapters, and timing; [Operating Modes](OPERATING_MODES.md) covers filesystem ownership; [Hardware & Controls](HARDWARE_CONTROLS.md) covers wiring; [Development & Deployment](DEVELOPMENT.md) covers procedure; [Development History](DEVELOPMENT_HISTORY.md) preserves dated evidence.

### Design commitments

- A fixed, small vocabulary of fundamental actions; editable room-specific command mappings.
- Stable IDs for rooms, devices, and custom actions. Display names are not identifiers.
- Strict schema validation, bounded storage, and deterministic serialized output.
- Blank endpoints and ordinary fundamental command paths are valid intentional no-ops.
- No implicit repair, migration, retries, or equipment-state inference.
- All browser and physical actions share the same dispatcher and Dumb Queue™.

## 2. Files and ownership

| File | Role |
|---|---|
| `/clonker/device_config.json` | Primary active JSON on Pico |
| `/clonker/device_config.json.bak` | Previous valid primary after a changed save |
| `/clonker/device_config.json.bak.old` | Older rotated backup |
| `/clonker/device_config.json.tmp` | Verified temporary write before rotation |
| `firmware/clonker/device_config.json` | Repository copy; not automatically authoritative over Pico |
| `samples/device_config_roku_denon_sample.json` | Readable complete two-room example |
| `firmware/clonker/device_config_v2.py` | Current Config v4 engine despite legacy filename |

GP17 SERVICE (USB) makes the USB host the filesystem writer; GP17 DEVICE makes Pico firmware the writer. **Persistent browser saves require DEVICE + CONFIG** (GP17 grounded at cold boot; GP18 grounded at runtime). SERVICE + CONFIG permits inspection and action testing, but rejects saves. RUN disables the management HTTP listener; it does not disable the queue or physical controls.

## 3. Exact Config v4 shape

The root object has **exactly** `version` and `rooms`:

```json
{
  "version": 4,
  "rooms": {
    "room-1": { "name": "Den", "devices": {}, "actions": {}, "custom_actions": [] }
  }
}
```

**The fragment above illustrates keys only and is not deployable:** the `devices` and `actions` objects must contain all required entries.

The `rooms` object contains **one to three** of the stable IDs `room-1`, `room-2`, and `room-3`. They may be omitted individually, but at least one room must exist. The current development installation contains Den (`room-1`), Sunroom (`room-2`), and a configured Room 3 placeholder (`room-3`) with blank device addresses and command paths. The physical selector recognizes all three positions. An unconfigured room and a configured room containing blank commands are distinct conditions; neither should cause an action to fall back to another room.

Every configured room has **exactly** these four keys:

| Key | Value |
|---|---|
| `name` | Nonblank string, maximum 40 characters; trimmed on validation |
| `devices` | Exactly `device-1`, `device-2`, `device-3` |
| `actions` | Exactly the 14 fundamental action IDs |
| `custom_actions` | Ordered array of 0–16 custom action definitions |

### 3.1 Built-in device destinations

| Stable ID | UI identity | Typical equipment |
|---|---|---|
| `device-1` | TV | Currently blank endpoints |
| `device-2` | AVR | Denon AVR-X3700H / AVR-X1800H |
| `device-3` | Streaming | Roku Ultra |

Each `devices` value is a string containing either `""`, a dotted IPv4 address, or `IPv4:port` with a numeric port from 1 to 65535. Hostnames, IPv6 literals, and URL schemes are not supported. Validation checks syntax, **not** reachability. An empty endpoint is legal and yields a no-op for commands addressed to it.

Development LAN examples (not permanent defaults): Den AVR `192.168.50.44:8080`, Den Roku `192.168.50.43:8060`, Sunroom AVR `192.168.50.40:8080`, Sunroom Roku `192.168.50.28:8060`. Actual values come from the Pico's loaded configuration. TCP Denon volume uses port **23** based on the host extracted from the configured AVR endpoint; it does not change the stored endpoint format.

### 3.2 Fundamental action IDs

Each configured room must define **all fourteen** IDs, even when individual mappings are intentionally blank:

```text
volume-up     volume-down     mute-toggle
nav-up        nav-down        nav-left        nav-right
select        back            home            play-pause
skip-back     skip-forward    power-toggle
```

There are two shapes:

**Ordinary fundamental action** (12 IDs other than the two toggles):

```json
"volume-up": {
  "target": "device-2",
  "method": "GET",
  "path": "/goform/formiPhoneAppDirect.xml?MVUP"
}
```

**Toggle action** (`mute-toggle` and `power-toggle` only):

```json
"power-toggle": {
  "target": "device-3",
  "method": "POST",
  "on_path": "/keypress/PowerOn",
  "off_path": "/keypress/PowerOff"
}
```

The target must be one of the three built-in IDs. The method is exactly `GET` or `POST`. Ordinary `path`, toggle `on_path`, and toggle `off_path` are strings of at most **512 characters**. An empty path is valid for fundamental actions. Nonempty paths are sent as configured; the schema does not prove that a device supports them. A blank endpoint or selected blank path produces an intentional no-op, not an invented substitute command.

### 3.3 Power and mute direction history

Toggle commands are not physical state queries. The dispatcher keeps **volatile, independent next-direction histories** per room and toggle action, selecting configured ON/OFF paths. A successful execution advances the history; failed requests, blank selected paths, and missing endpoints do not. A changed configuration save clears all histories; an unchanged save preserves them. History is lost on reboot.

An external remote, HDMI-CEC, or manual equipment control can change actual state independently. Therefore `power-toggle` means **send the next remembered command**, not “discover and invert actual power state.” Browser Test Remote and physical GP2 Power Toggle use the same action semantics. GP2 controls configured room equipment; it does **not** turn the Pico itself on or off.

## 4. Custom actions (implemented)

Custom actions are room-specific, ordered, user-named sequences. They are **not** replacements for the fourteen fundamental actions. Each custom action has exactly `id`, `name`, and `steps`:

```json
{
  "id": "custom-action-1",
  "name": "Movie",
  "steps": [
    {
      "target": "device-3",
      "method": "POST",
      "path": "/keypress/Home",
      "wait_after_ms": 3000
    },
    {
      "target": "device-2",
      "method": "GET",
      "path": "/goform/formiPhoneAppDirect.xml?MSQUICK1",
      "wait_after_ms": 0
    }
  ]
}
```

| Constraint | Current rule |
|---|---|
| Custom actions | 0–16 per room |
| ID | 1–40 characters; lowercase `a-z`, digits, hyphen; cannot start/end with hyphen |
| ID uniqueness | Unique within each room |
| Name | Nonblank, maximum 60 characters; trimmed |
| Steps | 1–16 per action, in declared order |
| Target | Only `device-1`, `device-2`, `device-3` |
| Method | `GET` or `POST` |
| Path | Nonempty string beginning `/`, maximum 512 characters |
| `wait_after_ms` | Integer 0–60000, not a boolean |
| Final step | Must have `wait_after_ms: 0` |

A custom action is admitted as one queue task. Each successful step sends one command; when more steps remain, the task is rescheduled **after** the completed request using its `wait_after_ms`. Other eligible work can execute during the delay. A step failure clears pending queue work. No nested macros, loops, branches, automatic retries, rollback, or parallel executor exist.

The Sunroom “Movie” action was verified with Roku Home → cooperative 3000 ms wait → Denon Quick Select 1. The physical custom-action encoder and press-to-run remain pending; the browser editor and Test Remote custom actions work today.

### 4.1 Future custom destinations — design only

The agreed extension reserves `device-4` onward for user-defined destinations, with stable IDs, editable names, and endpoints in an optional per-room `custom_devices` collection. Fundamental actions would continue to target the three built-in slots; custom steps could reference additional destinations. Deleting one destination must never renumber or silently retarget another.

**Config v4 rejects `custom_devices` and `device-4` targets.** Their future shape, capacity, and validation are not implemented. Apple TV may require discovery, pairing, authentication, and a stateful protocol adapter; its planned support does not imply compatibility with today's stateless HTTP commands. No PS5 or other custom-device support should be claimed until implemented and tested.

## 5. Validation and storage limits

`validate_config()` returns a new normalized, ordered object. It requires exact fields at every defined level, rejects unknown keys, unsupported versions, wrong types, invalid targets, malformed endpoints, duplicate custom-action IDs, invalid steps, and out-of-range values. It preserves canonical room order `room-1` through `room-3`, fundamental action order, and declared custom-action order. Names are trimmed. The input object is not edited in place.

| Constant / constraint | Value |
|---|---:|
| `CONFIG_VERSION` | 4 |
| `MAX_CONFIG_BYTES` | 8192 UTF-8 bytes |
| `MAX_ROOM_NAME_LENGTH` | 40 characters |
| `MAX_PATH_LENGTH` | 512 characters |
| `MAX_CUSTOM_ACTION_ID_LENGTH` | 40 characters |
| `MAX_CUSTOM_ACTION_NAME_LENGTH` | 60 characters |
| `MAX_CUSTOM_ACTIONS_PER_ROOM` | 16 |
| `MAX_STEPS_PER_ACTION` | 16 |
| `MAX_WAIT_AFTER_MS` | 60000 |
| Supported rooms | 1–3 |
| Built-in devices per room | Exactly 3 |
| Fundamental actions per room | Exactly 14 |

`to_json()` serializes validated configuration compactly with deterministic field ordering and checks the UTF-8 byte limit. `from_json()` bounds the incoming byte count before parsing and validates the result. A pretty-printed sample can exceed the limit even if its compact canonical equivalent fits; use the provided sample as a reference rather than blindly copying it onto the Pico.

The standard CircuitPython JSON parser is used; there is **no special duplicate-key detector**. Validation does not verify command semantics, network reachability, endpoint safety, device capabilities, or actual equipment state.

## 6. Active RAM state and revisions

`load()` publishes a validated configuration to module-owned RAM, and rebuilds the adapter cache. `current()` returns a validated **copy**, protecting the active object from accidental external mutation. Internal `action_details()` and `custom_action_details()` return direct references for efficient execution; callers must treat them as read-only. A queued action uses the current validated configuration when it executes, subject to queue clearing on changed saves.

`revision()` computes a deterministic **32-bit FNV-1a** hash over canonical UTF-8 JSON and formats it as eight lowercase hexadecimal digits. It is a stale-editor concurrency token, **not** cryptographic authentication or a globally unique content identifier.

The browser obtains the current revision with `GET /api/config` and submits that expected revision with `POST /api/config`. A mismatch rejects the save and asks the editor to refresh. The engine also compares the current primary file to the RAM snapshot before writing, preventing silent overwrites of out-of-band disk changes.

If the submitted configuration serializes identically to the active configuration, `save()` returns `False`: **no unnecessary flash write, backup rotation, queue clear, or toggle reset**. A changed successful save returns `True`, publishes the new RAM configuration, rebuilds the adapter cache, clears pending action work, and resets toggle histories via the management save path.

## 7. Exact save and backup behavior

`save(config, expected_revision, path=None)` requires a previously successful load and permits saving **only to the primary path bound by that load**. It checks the expected RAM revision, validates and canonicalizes the new object, reads and validates the primary disk file, and rejects any mismatch with active RAM. If the primary is absent or damaged, normal save **does not repair it** merely because startup loaded a backup.

For a genuinely changed configuration, the engine:

1. Writes compact JSON to `device_config.json.tmp` and flushes it.
2. Reads the temporary file back, compares exact bytes, and validates it again.
3. Verifies the current primary is valid before rotating backups.
4. Renames existing `.bak` to `.bak.old` when present.
5. Renames the primary to `.bak`.
6. Renames verified `.tmp` to the primary filename.
7. Reads back and validates the installed primary.
8. Rebuilds the adapter cache and publishes the new validated RAM snapshot.

The HTTP management save path then clears pending queue work and resets volatile toggle histories for a changed save. The individual renames are **not a single power-loss-atomic transaction**. Verified writes and two backup generations reduce risk but do not guarantee recovery from every sudden interruption. The full interrupted-write matrix remains untested.

**Important:** A save returning successfully is distinct from a physical equipment action succeeding. Saving configuration does not itself execute its actions.

## 8. Startup loading and deliberate recovery

Normal `load()` attempts candidates in this order:

```text
/clonker/device_config.json
/clonker/device_config.json.bak
/clonker/device_config.json.bak.old
```

Each candidate must parse and validate under the **current schema version**. Errors are logged, then the next candidate is tried. If all fail, startup raises an error rather than fabricating a default. Loading a valid backup provides a working RAM configuration but **does not overwrite, delete, or repair** a damaged primary. Subsequent ordinary saves refuse to overwrite that invalid primary.

The private `_recover_missing_file()` helper is an **explicit**, narrow operation for a **missing** primary; it may rename a valid backup into place. It will not replace an existing damaged primary. It is not part of normal automatic loading. Do not casually invoke private recovery helpers during routine deployment.

Recommended recovery sequence:

1. Capture the serial error and identify which generation failed and why.
2. Preserve the primary, `.bak`, and `.bak.old` externally before modifying anything.
3. Check `CONFIG_VERSION`, JSON structure, and deployed firmware compatibility.
4. Examine whether the primary is missing, truncated, malformed, or an older schema.
5. Validate a matching backup or known-good exported configuration.
6. Enter SERVICE (USB) through a **full power cycle** before host-side file restoration.
7. Restore a deliberate, compatible primary; return to DEVICE and cold boot.
8. Confirm loaded rooms and actions, browser display, and a harmless real action.

A Config v2/v3 JSON backup does not become valid Config v4 merely because it parses. Schema migrations are not automatic; preserve compatible firmware/configuration pairs when experimenting with version changes.

## 9. Browser editor and management API

The management service is available **only in CONFIG**, on port **9090**, and has no application-level authentication or HTTPS. Keep it on a trusted LAN; do not forward it to the public internet. The editor and Test Remote are operational, not mockups.

| Request | Purpose |
|---|---|
| `GET /` | Configuration editor |
| `GET /remote.html` | Test Remote |
| `GET /api/config` | Active config plus response-only revision and filesystem-writable metadata |
| `POST /api/config` | Validate and revision-check a save |
| `POST /api/action?room=...&action=...` | Enqueue fundamental or custom action |
| `GET /api/clock` | Clock status |
| `POST /api/clock?utc=...` | Browser-provided UTC sync |

`revision` and `filesystem_writable` are API metadata, **not stored JSON schema fields**. The POST handler removes the submitted revision before passing the configuration to the validator. A read-only filesystem rejects persistent saves (HTTP 403). Validation and revision errors produce error responses. Action acceptance reports admission to the queue, not completion.

Current inbound implementation limits (see `firmware/clonker/net/web.py` for changes): port `9090`; maximum request `10240` bytes; maximum headers `2048` bytes; I/O chunks `512` bytes; idle silent-client timeout **0.2 s**; active-client timeout **4.0 s**. The cooperative server handles one client at a time. Browser responsiveness can still be affected by synchronous outbound execution.

The editor exposes room names, built-in device endpoints, fourteen fundamental mappings, toggle ON/OFF paths, ordered custom actions and steps, revision-aware saves, and clock tools. It does not provide arbitrary new room IDs, additional built-in action IDs, nested macros, or custom-device destinations. Browser action tests use the same dispatcher as physical controls.

## 10. Action execution and transport boundary

Configuration describes **what** command is associated with an action. The shared dispatcher and Dumb Queue™ decide **when** to execute; adapters and transports decide **how** to deliver. Keep these concerns separate.

- Queue capacity is **128**. Each poll executes at most one eligible outbound command.
- Future-dated custom steps do not block unrelated immediately eligible work.
- A failed execution clears remaining queued work; there are no automatic retries.
- Generic configured commands use bounded, synchronous HTTP GET/POST.
- The Denon adapter recognizes the configured **fundamental** `volume-up`/`volume-down` GET paths exactly matching `/goform/formiPhoneAppDirect.xml?MVUP` and `?MVDOWN`; those use a persistent TCP connection on port **23**, sending `MVUP` or `MVDOWN` with carriage return.
- Denon TCP volume commands have a **50 ms minimum spacing**. A command waiting for pacing stays queued and preserves ordering. Other configured commands, including custom-action steps, remain on generic HTTP unless separately supported.
- Adapter mappings are rebuilt when configuration changes. No new configuration schema fields are required for the Denon TCP optimization.
- A network success or HTTP 2xx is not proof that the receiver or television changed state. The TCP adapter likewise does not parse equipment responses into authoritative state.

The Bourns physical volume encoder on GP8/GP9 generates generic volume actions, not Denon-specific commands. Physical room selection (GP3/GP6/GP7) determines which configured room receives them. GP2 Power Toggle and the browser Test Remote share the same action path. The volume encoder push-to-mute, custom-action encoder, navigation buttons, OLED, audio feedback, and future sleep/ignition system remain pending.

For transport details, exact scheduler intervals, and test evidence, use [Firmware, Network & Clock](FIRMWARE_NETWORK.md), not duplicated configuration rules here.

## 11. Regression checklist

The Bourns physical volume encoder on GP8/GP9 generates generic volume actions, not Denon-specific commands. Physical room selection (GP3/GP6/GP7) determines which configured room receives them. GP2 Power Toggle, volume push-to-mute, navigation, playback buttons, and the browser Test Remote share the same action system.

Chapter 7 added six explicit Roku physical-button holds (navigation Up/Down/Left/Right and Skip Back/Forward). These use queued press/release events and require a valid Roku endpoint, POST method, and recognized ECP command path. Unlike ordinary fundamental actions, the current hold execution path does not yet treat blank commands as no-ops. See [Firmware, Network & Clock](FIRMWARE_NETWORK.md) for implementation details.

- **Schema:** Reject unknown/missing keys, unsupported versions, invalid room IDs, invalid endpoints, missing fundamental actions, invalid toggle fields, and custom-action rule violations.
- **Size:** Test the 8192-byte serialized limit, including multibyte UTF-8 cases where relevant.
- **Stale editor:** Save from Tab A; verify stale Tab B is rejected until refreshed.
- **Unchanged save:** Confirm no flash rewrite or queue/toggle reset.
- **Changed save:** Confirm persistence after cold boot, backup rotation, adapter rebuild, and queue/toggle reset.
- **Filesystem:** Confirm SERVICE + CONFIG rejects saves and DEVICE + CONFIG permits valid saves.
- **Out-of-band change:** Confirm disk/RAM mismatch rejects a save rather than overwriting an unexpected primary.
- **Recovery:** Test primary, `.bak`, `.bak.old` fallback separately; verify fallback does not silently repair primary.
- **Execution:** Test both rooms, configured no-ops, power/mute histories, custom step waits, mixed HTTP/TCP ordering, and failures clearing the queue.
- **Physical:** Verify all three room-selector positions, Power Toggle, volume/mute, navigation and playback buttons, and Roku press/release behavior. For configured Room 3, verify ordinary blank-command no-ops separately from physical hold behavior; blank-command protection for holds remains pending.

Record what was actually exercised rather than labeling the entire checklist “passed.” The documented Denon volume bench tests included five slow and ten moderate clicks in each direction and aggressive turning, with volume returning to its starting level. A separate TCP pacing test sent ten commands in approximately 606 ms; mixed-transport queue regression tests covered ordering, waits, and failure clearing. Those are useful evidence, not exhaustive long-duration guarantees.

## 12. History and future compatibility

- **XML v1:** Historical engine and migration context; not the active format.
- **Config v2:** JSON foundation with fixed mappings; historical.
- **Config v3:** Generic `device-1`/`device-2`/`device-3` slots; historical.
- **Config v4:** Optional configured rooms, fourteen fundamental actions, ordered custom actions, revision-protected persistence; **active**.
- **Chapter 6 transport:** Denon TCP volume adapter and physical encoder use the existing Config v4 mappings; **no schema bump**.
- **Deferred:** `custom_devices`/`device-4` onward, Apple TV protocol integration, and any new schema required by those capabilities.

Dated migrations, bench experiments, and prior implementation snapshots belong in [Development History](DEVELOPMENT_HISTORY.md). Do not preserve obsolete behavior as if it were current, and do not silently delete historically meaningful decisions.

---

**THE CLONKER 10000**  
*Less sleek. More CLONK.*  
**CLONK! ⚡🔩**
