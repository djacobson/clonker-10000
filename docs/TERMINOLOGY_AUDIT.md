# SERVICE (USB) Terminology Audit

**Source inspected:** GitHub default branch, 15 October 2026. This is an audit of the **retrieved files**, not a guaranteed exhaustive scan of every repository file; GitHub code search returned no indexed matches for these terms.

## Confirmed code references

| Path | Current text / behavior | Suggested change |
|---|---|---|
| `firmware/boot.py` | `# Clonker USB / DEVICE jumper detection test` | `# Clonker SERVICE (USB) / DEVICE jumper selection` |
| `firmware/boot.py` | `# No filesystem ownership changes yet.` | **Remove** — stale; DEVICE branch calls `storage.remount` |
| `firmware/boot.py` | `CLONKER BOOT: USB mode (jumper OPEN)` | `CLONKER BOOT: SERVICE (USB) mode (jumper OPEN)` |
| `firmware/clonker/www/index.html` | `USB mode -- filesystem read-only. Configuration saving unavailable.` | `SERVICE (USB) mode -- filesystem read-only. Configuration saving unavailable.` |

## Other documentation references

| Path | Finding | Suggested change |
|---|---|---|
| `ARCHITECTURE.md` | Many `USB mode`, `USB / DEVICE`, port 8080, Web Workflow port 80 and future-config statements | Replace with the new architecture index and focused docs |
| `README.md` | Calls FeatherS3[D] the current controller | Update to Pico 2 W; link to docs |
| `firmware/settings.example.toml` | Web Workflow correctly disabled; no USB-mode wording | Keep; optionally fix typographic quote around example hostname |

## Not terminology errors

- `USB serial REPL`, `USB cable`, and `USB power` refer to the physical USB interface, **not** the filesystem mode. Keep these terms.
- `storage.getmount('/').readonly` and HTTP `filesystem_writable` are **correct capability checks**; do not rename them.
- `DEVICE mode` remains unchanged.

## Suggested safe code-edit order

1. Change **only the human-readable comment and boot print string** in `firmware/boot.py`.
2. Change **only the browser status message** in `firmware/clonker/www/index.html`.
3. Commit/push, deploy in SERVICE (USB) mode, and verify both jumper states at a full power cycle.
4. Keep actual GPIO polarity, `storage.remount`, and backend write checks **unchanged**.

## Additional code cleanup spotted

- `firmware/clonker/device_config.py`: `_load_existing()` docstring still says it is “recovering an interrupted save”; it now **only loads**. Change to `Load and validate configuration from the specified path` when convenient.
- `firmware/clonker/device_config.py`: `_backup_looks_valid()` docstring says “basic XML integrity” but it also validates rooms; update wording.
- `firmware/clonker/web.py`: POST `/api/config` currently returns **validated; not saved**. Do not change its message until persistence is implemented.
