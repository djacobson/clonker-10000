# THE CLONKER 10000

## Architecture and Design Reference

**Updated:** October 12, 2026  
**Active platform:** Raspberry Pi Pico 2 W / CircuitPython 10.3.1  
**Repository:** [djacobson/clonker-10000](https://github.com/djacobson/clonker-10000)

> **Clonker controls actions, not brands. Controlled devices own their own state.**

This is the consolidated current design, not a running change log. **Verified** means demonstrated on the active Pico; **planned** means not yet integrated or tested.

## 1. Mission and Priorities

Clonker is a tactile home-theater remote. Buttons, encoders, and switches produce generic actions, which configuration maps to network commands for a selected room. It does not guess the power, volume, or input state of other devices.

Priority order: responsive physical controls; reliable device commands; three-position room selection; simple local configuration; diagnostics and time; OLED/audio personality; eventual battery optimization. Never let optional services make volume or navigation feel sluggish.

## 2. Current Hardware and Workflow

**Verified:** Raspberry Pi Pico 2 W (RP2350), CircuitPython 10.3.1, on dedicated 2.4 GHz `jrtr` Wi-Fi via TP-Link Deco. Reserved IP **`192.168.50.12`**, hostname `clonker-pico`. The Pico remained reachable during an overnight standalone 5 V USB-power test. This is promising, not proof of permanent reliability.

CircuitPython Web Workflow is at **`http://192.168.50.12/`** (port 80). `.local` resolution is intermittent in iPad Safari; prefer the IP. Deco client-list visibility does not establish actual network reachability.

The earlier FeatherS3[D] and Feather ESP32 V2 boards are historical experiments, **not the active controller**. Do not carry ESP32-specific sleep assumptions into Pico implementation.

**Source-control/deployment workflow:** edit and commit on iPad with Working Copy → push to GitHub `djacobson/clonker-10000` → GitHub Desktop on Lenovo (`Fetch origin`, `Pull origin`) → copy files from `firmware/` to `CIRCUITPY` using File Explorer → test USB serial REPL at `https://code.circuitpython.org/`. GitHub is the source of truth; Pico flash is the deployed runtime. Lenovo is usable on wall power despite its battery problem.

Windows USB ownership can make CircuitPython Wi-Fi Web Workflow read-only; ejecting the Windows drive did not reliably release write access. USB serial and File Explorer remain workable. Do not casually modify `boot.py`, USB settings, or the private `settings.toml`. Never commit credentials or secrets; keep only `settings.example.toml` in GitHub.

## 3. Design Principles and State Ownership

Clonker is not an old-fashioned universal remote with a shadow copy of every device's state. A user action becomes a **generic event**, the current room selection and configuration resolve the target, and the device receives an appropriate command. The device itself remains authoritative about whether it is powered on, what input is active, and its current volume. Avoid speculative toggling and cached state unless a device protocol actually requires it.

### Four distinct kinds of state

| Kind | Examples | Source of truth | Persistence |
|---|---|---|---|
| Physical | Room selector, RUN/CONFIG switch, maintained controls | Actual GPIO position | None; reread after wake |
| Configuration | Room names, endpoint URLs, action maps, preferences | Versioned flash configuration | Persist only intentional edits |
| Device | AVR volume, TV power/input, streamer state | Controlled device, queried when needed | Not duplicated by Clonker |
| Ephemeral | Debounce, queue, idle state, clock reference, OLED messages | RAM | Rebuilt at boot |

The physical selector *is its own memory*: never write its position to flash every time it moves. A successfully transmitted HTTP request does not prove the controlled device accepted or executed it. The action layer should be able to report errors without making physical controls unresponsive.

### Network-control philosophy

Prefer direct control of the authoritative device: Denon for speaker volume when it owns speaker volume; Roku for Roku navigation; LG for TV-specific operations. Another installation can remap actions to different endpoints without changing input-handling code. HDMI-CEC is the control protocol; ARC/eARC is primarily the audio-return path. Device-specific quirks belong in mappings/adapters, not the GPIO driver.

## 4. Physical Inputs and Logical Rooms

**Three-position maintained room selector (planned):** `Room1`, `Room2`, `Room3`, with configurable labels such as `DEN`, `SUN`, `AUX` or `BOTH`. Read the actual GPIO position on startup and wake; it is the authoritative room selection, not a value repeatedly stored in flash.

**Separate maintained CONFIG switch (approved design, not wired):** selects RUN versus CONFIG mode. It is distinct from the room selector and from the guarded SYSTEM/POWER button. GPIO, polarity, debounce, and final hardware remain TBD.

Candidate controls: Grayhill optical VOLUME encoder with large silver knob; Bourns SELECT encoder with smaller black knob; navigation and metal momentary buttons; guarded momentary SYSTEM/POWER; room selector. The ring illumination on a 12/24 V-rated button must not be powered directly from 3.3 V GPIO.

Generic action vocabulary:

```text
NAV_UP       NAV_DOWN      NAV_LEFT      NAV_RIGHT
NAV_SELECT   BACK          HOME
REWIND       PLAYPAUSE     FFWD
VOLUME_UP    VOLUME_DOWN   MUTE
POWER        MODE_1        MODE_2        MODE_3
STATUS       INFO
```

Physical input becomes an action before mapping to a device. Actions may be unmapped for a given room. The guarded POWER control is a logical action, not a physical battery disconnect.

## 5. Device Commands and Routing

A room/action mapping may specify HTTP method, endpoint, path, and optional body. Examples below are **illustrative**, not confirmed equipment URLs:

```text
Room1.Media.Home: POST http://<media-device>/keypress/Home
Room1.AVR.VolumeUp: GET http://<avr-device>/<configured-command>
```

Prefer commanding the device that owns the function (e.g. Denon AVR for speaker volume) instead of relying unnecessarily on TV/HDMI-CEC intermediaries. ARC/eARC is audio return; HDMI-CEC is control. Verify Roku, Denon, LG, and other protocols on actual devices. Network requests must be bounded so slow endpoints cannot stall input capture.

### Configurable action map

Each room has logical media and AVR endpoints (and may later define TV, lighting, or other endpoints). The action map should be inspectable, editable, and independent of the hardware wiring. Support HTTP method, target endpoint, path, and optional body; add headers or authentication only where real device protocols require them. Do not turn the remote into a general-purpose HTTP testing application.

The three logical identities `Room1`, `Room2`, and `Room3` map to display names and endpoints. Example:

```text
Room1 (DEN) -> media: living-room Roku -> AVR: living-room Denon
Room2 (SUN) -> media: sunroom Roku -> AVR: sunroom Denon
Room3 (AUX/BOTH) -> future configurable target or group behavior
```

`BOTH` or group-control semantics are not yet fixed. A three-position switch does not necessarily imply three independent physical rooms; keep this configurable and test fan-out behavior before promising simultaneous control.

### Generic action vocabulary and event semantics

```text
NAV_UP NAV_DOWN NAV_LEFT NAV_RIGHT NAV_SELECT
BACK HOME REWIND PLAYPAUSE FFWD
VOLUME_UP VOLUME_DOWN MUTE POWER
MODE_1 MODE_2 MODE_3 STATUS INFO
```

Encoder rotation should become a direction/step event; avoid one blocking network transaction for every raw electrical transition. Apply debounce to mechanical buttons and switches, and consider repeat/coalescing rules for volume. An action may intentionally be unmapped in a room.

## 6. Software Organization

| Path under `firmware/` | Purpose | Status |
|---|---|---|
| `code.py` | CircuitPython startup | Safe stub; full app auto-start not verified |
| `clonker/main.py` | App initialization and cooperative loop | Stub; integration next |
| `clonker/clock.py` | Monotonic uptime and UTC reference | **Verified** |
| `clonker/logger.py` | Serial severity logging | Bench implemented |
| `clonker/web.py` | Port-8080 HTTP management and clock API | **Verified manually** |
| `clonker/www/index.html` | External HTML/CSS/JS clock page | **Verified in Safari** |
| `clonker/events.py` | Event definitions | Planned |
| `clonker/dispatcher.py` | Event queue and handlers | Planned |
| `clonker/actions.py` | Generic-action execution | Planned |
| `clonker/config.py` | Persistent config loading/saving | Planned |

Deployment mirrors `firmware/` at the Pico filesystem root. `settings.toml` remains private. Future `/clonker_config.xml` and `/lib/` are not yet production dependencies.

## 7. Cooperative Loop and Polling Priority

**Planned architecture, not yet integrated into automatic startup.** Priority:

1. Capture GPIO and encoder changes.
2. Dispatch input actions and initiate bounded device commands.
3. Process timers, idle logic, and background work.
4. Poll the management HTTP interface **only in CONFIG mode**.

Conceptual pseudocode, not executable current firmware:

```python
web_running = False
while True:
    inputs.poll()
    dispatcher.poll()
    timers.poll()

    config_enabled = config_switch.read()  # simulated initially
    if config_enabled != web_running:
        if config_enabled:
            web.start()
        else:
            web.stop()
        web_running = config_enabled

    if web_running and web_poll_due():
        web.poll()
```

A tentative 50 ms management polling interval is a scheduling experiment, **not** a guaranteed response-time bound. The current `web.poll()` handles at most one request per call, but a client receive timeout of up to **one second** and socket sends can block. Improve this before relying on fast encoders. Consider hardware quadrature capture or interrupts where necessary. Do not put blocking sleeps, NTP lookups, or long network requests in the critical input path.

Planned event names: `CONFIG_CHANGED`, `BUTTON_PRESSED`, `ENCODER_TURNED`, `IDLE_TIMEOUT`, `ACTIVITY_DETECTED`. Bound queue growth and avoid repetitive idle logging.

### Dispatcher contract and isolation

The event producer should not know whether `VOLUME_UP` maps to Denon, LG, or another target. The dispatcher resolves room context and configured action, then schedules execution. Queue entries should include event kind, source, value/steps, and a monotonic timestamp. Preserve ordering where it matters (navigation and power), while allowing safe coalescing of high-frequency encoder steps. An unresponsive receiver must not prevent the next GPIO sample.

Keep initialization and cleanup explicit. On startup read the maintained switches, load configuration, initialize input capture, then start only the services allowed by the selected mode. When the CONFIG switch changes, start/stop the management listener exactly once. Catch recoverable network errors at the service boundary; unexpected failures should remain visible in the serial log. No tight loop should repeatedly print or write flash.

### Web server caveat

The current socket accept is nonblocking *when idle*, but `recv_into()` and `sendall()` are not guaranteed nonblocking. The current 1-second client timeout could make a physical control miss a responsiveness target. A future implementation should use a small per-poll work budget, bounded request size, connection state, explicit timeouts, and cooperative response sending. The browser may tolerate a slower refresh; a volume encoder cannot.


## 8. RUN and CONFIG Switch Behavior

**RUN (eventual hardware default):** no application management listener on port 8080; Wi-Fi remains usable for theater commands. Input capture and control dispatch remain primary. No routine config flash writes.

**CONFIG:** start the port-8080 listener once when entering mode; serve the management page and API; keep physical controls functional and higher priority. On returning to RUN, **close** the listener--merely skipping `web.poll()` leaves a listening socket open.

**Development simulation:** begin with `CONFIG_MODE_ENABLED = True` so the page remains reachable before wiring the switch. Verify enabled/disabled states and transitions before adopting GPIO. A physical mode switch should not require a reboot to take effect.

**Security:** no login/authentication required for the trusted-LAN prototype. Do not forward port 8080 to the internet. Validate incoming data and request sizes. The physical switch is a convenience gate, not strong security. CircuitPython's separate **port-80 Web Workflow is not gated** by this application switch.

## 9. Current HTTP Configuration Interface

**Verified on Pico with manual REPL startup:** application HTTP listener on port **8080**, separate from CircuitPython port 80.

| Request | Behavior |
|---|---|
| `GET /` | Serve `/clonker/www/index.html` |
| `GET /api/clock` | JSON `source` and `timestamp` |
| `POST /api/clock?utc=<unix_seconds>` | Validate UTC Unix seconds; set source to BROWSER; return JSON |

Open **`http://192.168.50.12:8080/`** only while Clonker's listener is running. The external HTML/CSS/JS page refreshes clock status on load and approximately every five seconds. The yellow **Synchronize with Browser** button has worked end-to-end in iPad Safari and displayed real UTC with source `BROWSER`.

Current server uses CircuitPython built-ins `wifi`, `socketpool`, and `json`, with minimal request parsing. Strengthen bounded/nonblocking I/O, request limits, and validation before adding configuration writes. Automatic `code.py`/`main.py` integration remains unverified.

## 10. Clock Service and Time Sources

`clonker/clock.py` is independent of the web server, dispatcher, and logger.

**DEFAULTTIME -- verified, always available:** `time.monotonic()` uptime formatted like `[DEFAULTTIME +09172.6s]`; no network, RTC, or flash dependency.

**BROWSER -- verified, permanent manual fallback:** independent button on the CONFIG page sends `Math.floor(Date.now()/1000)` as UTC Unix seconds. `clock.set_utc(seconds, "BROWSER")` validates range and stores an in-RAM UTC and monotonic reference; timestamps advance without further requests. CircuitPython on this board uses `time.localtime()` for conversion; `time.gmtime()` was unavailable. Browser sync does **not** write flash, alter configuration, or require the future Save button.

**NTP -- preferred future automatic source, not implemented:** investigate CircuitPython library behavior, DNS, socket timeouts, and failure cases. Do not assume an NTP call is nonblocking. Use bounded attempts, sensible retry intervals, and no boot or GPIO delay. If needed, schedule attempts during safe idle opportunities or implement a cooperative state machine. NTP failures must not prevent remote operation.

After reboot the clock starts at DEFAULTTIME until NTP or the browser establishes a reference. Exact source precedence and resync policy remain TBD. No clock reference is persisted to flash.

## 11. Logging

`clonker/logger.py` provides serial-only **DEBUG**, **INFO** (default), **WARNING**, and **ERROR**, timestamped through `clock.timestamp()`.

```text
[DEFAULTTIME +09172.6s] INFO    Clonker HTTP listening on port 8080
2026-10-12T18:10:08Z INFO    Clock synchronized from browser
```

No persistent log, RAM history, external logging library, or flash writes. Avoid high-volume idle logs; logging failures must not prevent control actions.

## 12. Persistent Configuration and Editor

**Planned; no persistent editor/save implemented yet.** Experiment with an inspectable `/clonker_config.xml`; JSON is an acceptable alternative if XML parsing or memory cost is troublesome.

The eventual page must **load existing saved values and prepopulate fields**, permit editing, then expose a distinct **Save Configuration** button. Saving validates inputs, writes only meaningful changes, and updates live configuration (`CONFIG_CHANGED` event or equivalent). Preserve export/backup/recovery. Test filesystem write permissions, USB ownership, and power-loss-safe replacement before enabling writes.

**Synchronize with Browser** remains a **separate button** from **Save Configuration**. Time sync updates only RAM; saving configuration must not silently change the clock.

### Proposed file organization and flash safety

```text
CIRCUITPY/
  code.py                       # app entry point; currently safe stub
  settings.toml                 # PRIVATE: Wi-Fi / Web Workflow bootstrap
  clonker_config.xml            # FUTURE: persistent action mappings
  clonker/
    __init__.py
    main.py
    clock.py
    logger.py
    web.py
    www/index.html
    events.py                    # future
    dispatcher.py                # future
    actions.py                   # future
    config.py                    # future
  lib/                           # future third-party .mpy modules
  sounds/                        # future audio assets
```

Only save after validation and only if data changed. Consider temporary-file plus backup/rename strategies *after* checking CircuitPython filesystem behavior and power-loss failure modes. The Pico's filesystem can be USB-owned by Windows; never assume Python-side flash writes are permitted while mounted. Configuration backup/export should be available before introducing editing. Keep bootstrap Wi-Fi credentials separate from the user-editable action configuration.

### Illustrative full XML action map (not deployed)

All `CONFIGURE_ME` values are placeholders, not real equipment URLs. The XML structure is a design example, not a fixed parser contract.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<clonker version="1">
  <device>
    <name>THE CLONKER 10000</name>
  </device>
  <rooms>
    <room id="1" name="DEN">
      <endpoints>
        <media baseUrl="http://CONFIGURE_ME" />
        <avr baseUrl="http://CONFIGURE_ME" />
      </endpoints>
      <actions>
        <action name="HOME" method="POST" target="media" path="/keypress/Home" />
        <action name="BACK" method="POST" target="media" path="/keypress/Back" />
        <action name="NAV_UP" method="POST" target="media" path="/keypress/Up" />
        <action name="NAV_DOWN" method="POST" target="media" path="/keypress/Down" />
        <action name="NAV_LEFT" method="POST" target="media" path="/keypress/Left" />
        <action name="NAV_RIGHT" method="POST" target="media" path="/keypress/Right" />
        <action name="NAV_SELECT" method="POST" target="media" path="/keypress/Select" />
        <action name="REWIND" method="POST" target="media" path="/keypress/Rev" />
        <action name="PLAYPAUSE" method="POST" target="media" path="/keypress/Play" />
        <action name="FFWD" method="POST" target="media" path="/keypress/Fwd" />
        <action name="VOLUME_UP" method="GET" target="avr" path="/CONFIGURE_ME" />
        <action name="VOLUME_DOWN" method="GET" target="avr" path="/CONFIGURE_ME" />
        <action name="MUTE" method="GET" target="avr" path="/CONFIGURE_ME" />
        <action name="POWER" method="POST" target="CONFIGURE_ME" path="/CONFIGURE_ME" />
      </actions>
    </room>
    <room id="2" name="SUN">
      <endpoints>
        <media baseUrl="http://CONFIGURE_ME" />
        <avr baseUrl="http://CONFIGURE_ME" />
      </endpoints>
      <actions><!-- Configure room-specific mappings --></actions>
    </room>
    <room id="3" name="AUX">
      <endpoints>
        <media baseUrl="http://CONFIGURE_ME" />
        <avr baseUrl="http://CONFIGURE_ME" />
      </endpoints>
      <actions><!-- Configure room-specific mappings --></actions>
    </room>
  </rooms>
  <preferences>
    <clonkVolume>70</clonkVolume>
    <oledBrightness>100</oledBrightness>
  </preferences>
</clonker>
```

### Proposed local management API

| Method/path | Purpose | Status |
|---|---|---|
| `GET /` | Serve configuration page | Verified clock-only page |
| `GET /api/clock` | Read source and time | Verified |
| `POST /api/clock?utc=...` | Set clock from browser | Verified |
| `GET /api/config` | Read current persistent configuration | Proposed |
| `POST /api/config` | Validate and save changed configuration | Proposed |
| `GET /api/status` | Future system/room/Wi-Fi status | Proposed |

The final API may use JSON for browser transport even if persistent configuration is XML. The page should be generated or prepopulated from the **actual current configuration**, not static hardcoded defaults. Validate XML/HTML escaping and bound input lengths. A browser clock sync is never an implicit configuration save.

## 13. Power, Wake, and System Control

**Planned and hardware-dependent.** The guarded SYSTEM/POWER control dispatches a theater action. It is not a physical battery disconnect and must not be confused with Clonker's own sleep state. A wake-only press must never accidentally toggle theater power.

### Proposed V1 state machine

```text
                 physical activity
                        |
                        v
                     ACTIVE
         inputs / network / OLED / sound
                        |
                 short idle timer
                        v
                   LIGHT SLEEP
             supported input wakes
             and ideally also acts
                        |
                longer idle timer
                        v
                    DEEP SLEEP
                display and Wi-Fi off
                        |
               first eligible press
                        v
                 WAKE-ONLY BOOT
         reload config, read switches,
             reconnect, show ready
                        |
                 next button press
                        v
                    ACTIVE
                dispatch command
```

**ACTIVE:** Handle inputs and device commands. CONFIG-mode HTTP is available only while CONFIG is selected; RUN has no management listener. User activity resets the inactivity timer. Display and sound should be brief and nonblocking.

**LIGHT SLEEP:** Goal is *one press, one action* where RP2350 GPIO alarm capabilities permit it. Wake source, input electrical behavior, and Wi-Fi reconnect cost must be verified. Short quadrature encoder pulses may not be recoverable after sleep; do not promise an encoder wake/step direction until measured.

**DEEP SLEEP:** Earlier candidate was approximately ten minutes of inactivity; this is **not a committed timeout**. The first eligible button press is wake-only, causing fresh initialization; a subsequent press sends the mapped command. Read both maintained room and CONFIG switches on restart. A wake-only guarded SYSTEM press must not issue `POWER`. Not every pin necessarily supports every wake mechanism; confirm RP2350/CircuitPython capabilities before pin assignment.

**Simulated first:** Until real sleep tests, transition to a simulated idle state and log `Would light sleep` or `Would deep sleep` only once per transition. Do not disable Wi-Fi or alter hardware sleep modes while building the dispatcher.

### Power and network consequences

Wi-Fi and the management server are not expected to be reachable in deep sleep. After wake, reconnect before sending commands. OLED display-off may leave electronics powered; measure total board current rather than assuming zero. Whole-system consumption includes regulator, indicators, amplifier, and peripherals. A motion-sensor wake interrupt is a possible future refinement, not a V1 requirement. A true physical off state needs separate power circuitry.

## 14. OLED and Sound

Begin with the available **0.49-inch 64×32 SSD1306 I²C OLED**, checking pin labels, soldering, and 3.3 V compatibility. Display startup, Wi-Fi, IP, and later status/brightness. A **1.3-inch 128×64 SH1106** remains a possible final display, requiring its own driver.

An Adafruit piezo can beep; MAX98357A I²S amplifier and small speaker can provide short startup/CLONK effects. No sound or animation should delay user commands. Mechanical enclosure and final pin map are not locked.

### Display integration order

1. Inspect the 0.49-inch SSD1306 module pin labels, soldering, I²C address, and 3.3 V compatibility before applying power.
2. Show startup banner, Wi-Fi state/IP, selected room, and later clock/config status.
3. Test contrast changes, dimming, and display-off; measure real power effects.
4. Evaluate the larger 1.3-inch 128×64 SH1106 candidate with its correct driver if more readable status is needed.
5. Ensure screen updates do not delay encoder and button sampling.

### Audio and physical personality

The Adafruit piezo can generate simple feedback. The MAX98357A I²S amplifier and small 8 Ω speaker are candidates for startup/grumble/CLONK sounds; confirm RP2350 CircuitPython audio support and GPIO pin allocation. Avoid long synchronous sound playback. Candidate metal ball tactile buttons, guarded momentary SYSTEM control, illuminated FILN button, and room-selector slide switch require physical fit and electrical verification. The FILN illumination is rated for 12/24 V; do not connect that illumination directly to a Pico GPIO or assume it will illuminate at 3.3 V. Momentary contact circuits can typically use internal pull-ups and a ground closure, subject to testing.

### Hardware integration order

OLED bench test → one simple button and debounce → room and CONFIG maintained switches → encoders (especially Grayhill optical capture) → command routing → sound and guarded POWER → sleep/power measurement → enclosure layout. This is a preferred sequence, not a rigid requirement.


## 16. Dependencies and Compatibility

Current clock, logger, and web experiments use CircuitPython built-ins (`time`, `json`, `wifi`, `socketpool`) without third-party `.mpy` dependencies. As hardware is integrated, document exact board, CircuitPython version, `/lib` bundles, GPIO pin map, voltage rails, and hardware constraints. A CPython `requirements.txt` alone is not a sufficient CircuitPython compatibility manifest.

## 17. Verified Milestones and Known Gaps

| Capability | Status |
|---|---|
| Pico Wi-Fi, reserved IP, Web Workflow | **Verified** |
| Standalone USB power overnight | **Verified for one night** |
| USB serial REPL and File Explorer deployment | **Verified** |
| DEFAULTTIME and browser UTC | **Verified** |
| Logger and port-8080 HTTP | **Bench verified** |
| `GET /api/clock` and browser sync button | **Verified in Safari** |
| Automatic full application startup | **Not verified** |
| Simulated/physical CONFIG gating | **Not yet integrated** |
| Fully bounded HTTP request processing | **Not yet implemented** |
| Event dispatcher and physical GPIO inputs | **Planned** |
| XML save/reload and config prepopulation | **Planned** |
| NTP | **Planned; blocking behavior untested** |
| Pico sleep/wake and battery measurements | **Deferred** |

### Historical prototype tests (not proof on Pico 2 W)

Earlier Feather experiments demonstrated iPad Web Workflow, serial REPL, keyboard-simulated button events (`u`, `d`, `s`, `q`), repeated idle cycles, and short timed light-sleep experiments. These were performed on a different microcontroller and do **not** establish Pico 2 W sleep/wake behavior. Earlier Feather ESP32 V2 lacked a USB mass-storage drive, unlike the current Pico. Do not carry those hardware-specific constraints forward.

### Acceptance tests for upcoming milestones

- RUN mode: no port-8080 listener; physical input capture and normal Wi-Fi device commands remain available.
- CONFIG mode: page and clock API reachable; moving switch back to RUN closes the listener; switching again reopens it.
- HTTP: idle polls return promptly; slow or malformed clients cannot stall GPIO sampling; malformed timestamps receive an error without changing clock.
- Clock: DEFAULTTIME after restart; browser button sets BROWSER; future NTP failure leaves remote functional.
- Config: page loads existing values; Save is separate from browser time sync; reboot restores committed config; failed save does not destroy last good config.
- Wake: first deep-sleep wake press never triggers theater POWER; real RP2350 wake source and timing are measured.

## 18. Next Development Sequence

1. Integrate `main.py` and a **simulated CONFIG switch** (`True` initially), with transition-based `web.start()`/`web.stop()` and gated `web.poll()`; retain USB REPL recovery.
2. Verify `code.py` automatic startup, both simulated switch positions, and port-8080 listener closure in RUN.
3. Make HTTP request handling bounded before connecting time-sensitive encoders.
4. Implement dispatcher, simulated events, then GPIO and encoder capture.
5. Implement config load/prepopulation and controlled flash save with an independent **Save Configuration** button.
6. Evaluate optional bounded NTP, retaining the browser fallback.
7. Integrate OLED/audio and final hardware switches; test sleep only after core controls are dependable.

---

**Non-negotiable rule:** Clonker must remain a responsive remote even when configuration, logging, browser management, NTP, or sound effects are unavailable.
