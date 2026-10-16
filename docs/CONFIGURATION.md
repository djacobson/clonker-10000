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
