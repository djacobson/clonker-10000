# Configuration, Persistence & Recovery

**Design reference · 15 October 2026**

## Current format

Active XML path: **`/clonker/device_config.xml`**. Schema version `1`, three fixed IDs `room-1`, `room-2`, `room-3`. Each room has a name (1–40 characters), optional IPv4 TV and AVR addresses, and `volume_device` (`tv` or `avr`). The room names are editable; the count and IDs are developer-defined.

`device_config.py` supplies `validate_config`, `to_xml`, `_load_existing`, `load`, `current`, `revision`, `_write_verified_temp`, `_replace_with_backup`, `_backup_looks_valid`, and `_recover_missing_file`.

**Important:** Current `load()` tries primary, `.bak`, then `.bak.old` and publishes the first successfully parsed configuration to RAM. It does **not** automatically rename a backup into place. `_recover_missing_file()` is a separate explicit repair operation.

## Browser and HTTP status

| Request | Current behavior |
|---|---|
| `GET /api/config` | Returns current rooms, revision, and `filesystem_writable` |
| `POST /api/config` in SERVICE (USB) | HTTP 403: filesystem read-only |
| `POST /api/config` in DEVICE | Validates submitted room data; responds `Configuration validated; not saved` |
| `GET /` | Configuration and clock UI |

The Save Configuration control and API are **not yet wired to persistence**. Do not describe an HTTP 200 validation response as a successful save. Browser UI may indicate filesystem writable even though saving is not yet implemented.

## Proposed save transaction (implemented as helper; not yet integrated)

1. Serialize validated configuration in RAM (`to_xml`).
2. Write `device_config.xml.tmp`, flush, reopen, compare contents.
3. Check primary exists with `os.stat(path)`.
4. Rename previous `.bak` to `.bak.old` (overwriting older `.bak.old` on tested filesystem).
5. Rename primary to `.bak`.
6. Rename verified `.tmp` to primary.
7. Read back primary and compare.

**Known limits:** multi-step rename is not atomic as a transaction; unexpected reset can leave primary missing. `.bak.old` is a rolling third generation, **not** a permanent archival backup. The latest backup might be invalid, so recovery must validate candidates. No power-cut endurance test or filesystem durability guarantee has been established.

## Recovery behavior

- On boot, `load()` reads first valid primary / `.bak` / `.bak.old` without changing files.
- Explicit `_recover_missing_file(path)` acts only if primary is missing; checks `.bak`, then `.bak.old`, validates full expected room structure, and renames the first valid candidate to primary.
- Never call the recovery helper on arbitrary non-XML test strings: it validates Clonker XML.
- In SERVICE (USB) mode, reading a backup is possible; renaming it is not.

## Remaining safety work

- Test updated helper functions with **disposable, valid XML files** in DEVICE mode; earlier text-file rename tests do not validate the XML-specific recovery helper.
- Test missing primary, corrupt `.bak`, valid `.bak.old`, read-only fallback, and interruption states.
- Verify that startup behavior, UI messaging, and save permissions agree.
- Validate revision/concurrency behavior and reject stale submissions at the actual POST endpoint before persistence.
- Decide whether successful saves update in-memory configuration immediately or reload and publish only after verified installation.
- Keep external exports of important configuration before enabling real saves.

## XML and parser constraints

The current parser is deliberately lightweight rather than a general XML library. It validates expected wrappers and room fields and escapes/unescapes names. Do not assume arbitrary XML documents or action maps are supported. Device command/action mappings are **future schema work**.

---

## Configuration v2 — Approved Design (Not Yet Implemented)

**Decision date:** October 16, 2026

Configuration v2 will replace the v1 XML schema while retaining the
proven configuration validation, persistence, revision checking,
backup rotation, and browser editing mechanisms.

### Scope

- Exactly three rooms with fixed room IDs.
- Exactly three device endpoints per room: `tv`, `avr`, `streaming`.
- All device IPv4 addresses are optional; empty addresses are valid.
- Exactly five fundamental actions per room:
  - `volume-up`
  - `volume-down`
  - `mute-toggle`
  - `home`
  - `back`
- Every fundamental action has an editable `target`, `method`, and `path`.
- Valid targets: `tv`, `avr`, `streaming`.
- Valid HTTP methods: `GET`, `POST`.
- Empty command paths are valid and disable the corresponding action.
- Action IDs are fixed and cannot be renamed or deleted.
- Unknown or duplicate fundamental action IDs are rejected.
- Action targets are independent of action IDs.
- A missing target IP address prevents command execution.
- No HTTP command execution is included in the initial v2 milestone.

### Reserved Custom Actions

Each room will contain an empty `<custom-actions />` element.

User-defined names, command sequences, waits, token substitution,
and macro parsing are deferred to a later milestone.

The v2 parser will recognize the empty placeholder but will not
accept arbitrary custom-action contents.

### Removed v1 Preference

The `volume_device` preference will be removed.

Volume Up, Volume Down, and Mute Toggle will each have their own
configurable destination. This avoids conflicting configuration rules.

### Validation and Limits

- Fundamental action structure is strict.
- Command paths may be empty.
- Command path maximum length will be controlled by a single constant
  near the top of `device_config.py`.
- XML size limits will be centralized in `device_config.py`.
- HTTP request size limits will remain separately configurable
  in `web.py`.
- Request limits will be measured and adjusted for the expanded
  three-room configuration.

### Schema Versioning

- New XML schema version: `2`.
- No automatic v1-to-v2 migration framework at this stage.
- Firmware, browser editor, and XML will be upgraded together.
- Existing v1 backups will be handled during the controlled upgrade.
- Backward compatibility can be introduced later if needed.

### Planned Implementation Sequence

1. Finalize and review complete v2 XML.
2. Update Python parsing, validation, and serialization.
3. Update browser configuration fields and save payload.
4. Adjust HTTP request size limits.
5. Deploy matching firmware, HTML, and XML together.
6. Verify loading, browser saves, backup rotation, and persistence.
7. Implement HTTP action execution in a subsequent milestone.

### Design Principle

Fundamental action IDs describe what the user wants to accomplish.
Configurable destinations, HTTP methods, and paths describe how
Clonker accomplishes it.

No fixed assumption that volume requires an AVR or navigation
requires a separate streaming device.

**Status: Design approved; implementation pending.**

