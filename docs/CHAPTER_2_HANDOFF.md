# THE CLONKER 10000 — Chapter 2 Handoff

**As of:** 2026-10-19  
**Milestone:** Browser action dispatcher operational (logging-only)  
**Next chapter:** Real HTTP device actions

> CLONK! The monster has learned to recognize its buttons. Next, it learns to talk to the equipment.

## Source of truth and document precedence

Repository: `djacobson/clonker-10000`.

Read current repository files before proposing changes. For current behavior, **running firmware is authoritative**; dated documentation records design intent and test history. The earlier XML v1 implementation and `docs/OLD_ARCHITECTURE.md` are historical, not active architecture. This handoff describes the milestone reached on October 19, 2026, but should be checked against newer commits.

Useful documents:
- `docs/ARCHITECTURE.md` — architecture and toggle design; some status statements predate this milestone.
- `docs/CONFIGURATION.md` — JSON v2 schema, persistence, recovery and historical migration.
- `docs/FIRMWARE_NETWORK.md` — HTTP and cooperative scheduling.
- `docs/OPERATING_MODES.md` — SERVICE/DEVICE versus CONFIG/RUN.
- `docs/DEVELOPMENT.md` — deployment workflow.
- `docs/HARDWARE_CONTROLS.md` — eventual physical inputs.
- `docs/DEVELOPMENT_HISTORY.md` — development milestones and dated tests; do not mistake older pending lists for current status.

## Platform and workflow

- **Current controller:** Raspberry Pi Pico 2 W (RP2350), CircuitPython 10.3.1.
- **Firmware:** `firmware/code.py`, `firmware/boot.py`, and `firmware/clonker/`.
- **User workflow:** edit with Working Copy on iPad; commit and push to GitHub; deploy selected files to CIRCUITPY using Windows only as necessary; test on iPad in browser.
- **SERVICE (USB):** GP17 open at boot; host can write Pico filesystem, Pico cannot persist config.
- **DEVICE:** GP17 connected to GND at boot; Pico can persist config, USB host is read-only.
- **Switching SERVICE/DEVICE requires a full power cycle.**
- **CONFIG/RUN:** independent application mode; CONFIG currently simulated enabled; physical switch not yet wired. Web UI is available while CONFIG is enabled.
- **Management UI:** `http://192.168.50.12:9090/` on trusted LAN; remote page `/remote.html`.
- **Security:** no application authentication; do not expose port 9090 to the internet. CircuitPython Web Workflow is disabled in private settings.

## Active configuration

`/clonker/device_config.json` is JSON schema version 2, loaded through `firmware/clonker/device_config_v2.py` into a validated RAM snapshot. The browser editor and firmware share this schema.

- Three fixed rooms: `room-1` Den, `room-2` Sunroom, `room-3` placeholder; room display names editable.
- Three optional endpoints per room: `tv`, `avr`, `streaming`; IPv4 address with optional port.
- Fourteen fundamental action IDs per room:
  `volume-up`, `volume-down`, `mute-toggle`, `nav-up`, `nav-down`, `nav-left`, `nav-right`, `select`, `back`, `home`, `play-pause`, `skip-back`, `skip-forward`, `power-toggle`.
- Ordinary actions: `target`, `method`, `path`.
- Toggle actions: `target`, `method`, `on_path`, `off_path`. These fields are **implemented in configuration**; the ON/OFF alternation behavior is **not yet implemented in dispatcher**.
- Blank endpoint/path means no outbound action.
- Reserved `custom_actions` configuration exists; browser Test Remote's Movie Mode / Stereo Mode / Next Audio Mode selector is **illustrative only**, with no execution handler.

### Current tested devices

| Room | Device | Endpoint |
|---|---|---|
| Den | Denon AVR-X3700H | `192.168.50.44:8080` |
| Den | Roku Ultra | `192.168.50.43:8060` |
| Sunroom | Denon AVR-X1800H | `192.168.50.40:8080` |
| Sunroom | Roku Ultra | `192.168.50.28:8060` |

LG TV endpoints are blank; Room 3 is placeholder. Confirm these against the active config before sending real commands. No credentials are part of these endpoint definitions.

Known configured patterns:
- Denon HTTP GET `/goform/formiPhoneAppDirect.xml?MVUP`, `?MVDOWN`, `?MUON`, `?MUOFF`, and quick-select example `?MSQUICK2`.
- Roku HTTP POST `/keypress/Up`, `/Down`, `/Left`, `/Right`, `/Select`, `/Back`, `/Home`, `/Play`, `/Fwd`, `/InstantReplay`.
- Roku PowerOn/PowerOff behavior and HDMI-CEC side effects remain to be confirmed on actual hardware; never infer state from a successful HTTP response.

## Verified October 19 browser-remote milestone

**Files:**
- `firmware/clonker/actions.py`: shared `dispatch(room_id, action_id)` logging-only stub.
- `firmware/clonker/web.py`: GET `/remote.html`; POST `/api/action?room=room-1&action=volume-up`; CircuitPython-compatible query parser without `urllib.parse`.
- `firmware/clonker/www/remote.html`: room selector, 14 fundamental action buttons, response/status display, inactive custom-action dropdown.
- `firmware/clonker/www/index.html`: side-by-side System Clock and Test Remote panels, button-style remote link, responsive stacking, and configuration editor.

**User-tested on physical Pico:** all browser action tests worked and logged as expected; Den and Sunroom actions, unconfigured Room 3, and placeholder dropdown were exercised. Browser-to-Pico request/response and action validation work. **No outbound HTTP AV control is implemented or tested yet.**

The UI includes compact right-aligned volume/mute group, Back/Home group, directional navigation, playback controls, oversized centered POWER button, custom-action dropdown underneath, and matching centered designer/GitHub attribution on both pages. `Device Configuration` is the user-facing heading; JSON version remains an internal technical detail.

## Architecture and responsibilities

1. Physical inputs (future) or browser remote (current) produce **generic action IDs** and a room ID.
2. `actions.py` resolves action ID, room, target endpoint, and command definition from the **current validated configuration**.
3. A small outbound HTTP transport (next chapter) sends one command to the configured device.
4. Browser receives a bounded JSON result and presents success/failure; serial logger records diagnostics.
5. CONFIG server `web.poll()` remains cooperative and bounded. Future physical inputs take scheduling priority.

Do not duplicate the entire config in a second cache unless measurement justifies a targeted optimization. Keep transport independent of room/toggle policy.

## Agreed V1 toggle semantics — DESIGN, NOT YET CODE

- Maintain RAM **last-successful-command** direction separately for each `(room_id, action_id)` pair for `mute-toggle` and `power-toggle`.
- Unknown at boot -> attempt ON first.
- After a successful request, remember ON or OFF; next press attempts the opposite.
- Missing endpoint, blank selected path, or failed request -> **do not advance** the remembered direction.
- Identical `on_path` and `off_path` are allowed for native device toggles.
- Never persist toggle memory to flash. It is command history, **not actual device state**. Other remotes/CEC may cause divergence.
- Decide what counts as HTTP success during transport implementation and test against real responses; network success does not guarantee the device changed state.

## Recommended next chapter — staged, measurable steps

1. Re-read GitHub `actions.py`, `web.py`, `device_config_v2.py`, `main.py`, sample config and relevant docs; inspect available CircuitPython networking libraries/dependencies before coding.
2. Agree on a **minimal outbound HTTP transport** with bounded connect/read timeouts, URL/path validation, GET and POST, response-status handling, logging, and no credentials or internet exposure.
3. Start with a **single low-risk Denon or Roku action** from the browser; verify response and physical effect. Avoid POWER initially.
4. Implement ordinary action dispatch using the active room config; test Den and Sunroom separately; verify missing endpoint/path is a safe no-op.
5. Implement RAM toggle direction after ordinary commands are reliable. Test MUON/MUOFF and failure/no-op behavior before considering Roku power/CEC.
6. Assess responsiveness, socket cleanup, sequential button presses, and interaction with cooperative `web.poll()`; optimize only if observed need.
7. Document tests and limitations, then plan physical GPIO control integration and eventual custom actions.

**Out of scope for this first step:** general macro engine, state polling, retries/queues, connection pooling, OLED, sounds, enclosure and battery work.

## Testing / safety reminders

- Current stub logs are a useful regression baseline; do not silently switch to live control without clearly marking the milestone.
- Real commands can change AVR volume or power equipment. Start at a safe listening level and test one action at a time.
- Use source-controlled sample data for documentation, but do not assume production Pico configuration exactly matches a GitHub fixture without checking.
- Preserve tested configuration persistence, revision protection, backup rotation and read-only SERVICE behavior.
- Historical `DEVELOPMENT_HISTORY.md` entries include old statuses; append dated test results rather than rewriting history.
 
## Collaboration preferences

- User works **iPad-first**, uses Working Copy, and prefers minimal Windows work.
- Provide **raw, complete, pasteable Markdown/HTML/Python** when requested; preserve comments and readable indentation.
- Review live GitHub source before proposing code changes. Make incremental, testable changes, with exact paths and deployment instructions.
- Distinguish observed behavior, source-code implementation, and future design. Never claim a file is pushed/deployed/tested unless verified.
- User appreciates Clonker's goofy mechanical/nuclear-submarine humor, but wants engineering discipline and straightforward troubleshooting.
- Project sign-off: **CLONK! ⚡🔩**

## Documentation reconciliation checklist

- `README.md`: remove duplicate 'fourteen fundamental actions' bullet; update toggle wording to distinguish configured ON/OFF fields from future execution; add October 19 stub dispatcher milestone and current next milestone.
- `docs/ARCHITECTURE.md`: mark dispatcher **stub implemented and on-device browser tested**; mark real HTTP transport and physical event capture as planned; add `actions.py` and `www/remote.html` to firmware map; update stale `firmware/clonker/device_config.py` path to `firmware/clonker/legacy/device_config.py`.
- `docs/FIRMWARE_NETWORK.md`: add GET `/remote.html` and POST `/api/action?...` with stub response semantics and request parser compatibility note.
- `docs/DEVELOPMENT_HISTORY.md`: chronological engineering history through October 19, including the browser-remote milestone; append future milestones without rewriting earlier evidence.
- `docs/DEVELOPMENT.md`: note deployment of `actions.py`, `web.py`, `index.html`, `remote.html` and SERVICE/DEVICE power-cycle requirement.
- Do not erase older test results or call incomplete failure-injection tests passed.
