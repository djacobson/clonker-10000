# THE CLONKER 10000

## Architecture & Pseudocode Notes

*Working design summary --- October 2026*

> **Design mantra:** Clonker controls actions, not brands --- and
> devices own their own state.

## Core Philosophy

**Clonker controls actions, not brands.**

The physical remote should behave primarily as an input device. It
reports what the human did; configuration determines what network
command that action means. Whenever practical, the controlled devices
remain the authoritative owners of their own state.

Avoid turning Clonker into an old-style universal-remote state machine
that tries to remember whether every TV, AVR, streamer, input, and power
state is on or off. Modern HDMI-CEC/ARC/eARC and network APIs allow much
of that coordination and state to live in the equipment itself.

## Four Kinds of State

  -----------------------------------------------------------------------
  State type              Examples                Where truth lives
  ----------------------- ----------------------- -----------------------
  **Physical state**      3-position room         Read the hardware/GPIO
                          selector, maintained    pins
                          switches                

  **Configuration state** Room names, endpoint    Persistent flash config
                          URLs, HTTP actions,     
                          preferences             

  **Device state**        AVR volume, TV          The actual device;
                          power/input, Roku app   query when needed

  **Ephemeral Clonker     Debounce, temporary     RAM only
  state**                 OLED message, menu      
                          position                
  -----------------------------------------------------------------------

## Three-Room Model

V1 deliberately supports up to **three rooms** because the physical
Clonker has a three-position selector. The firmware can use generic
`Room1`, `Room2`, and `Room3` identities while persistent configuration
supplies friendly names such as `DEN`, `SUN`, or `BED` for the OLED.

``` text
ROOM 1 -> configurable name -> Media endpoint + AVR endpoint
ROOM 2 -> configurable name -> Media endpoint + AVR endpoint
ROOM 3 -> configurable name -> Media endpoint + AVR endpoint
```

The maintained selector itself is persistent physical state. Clonker
does **not** need to save the current room to flash whenever the switch
moves. After power-up, it can simply read the GPIO pins and know where
the switch was left.

## Generic Physical Actions

Firmware should translate hardware activity into generic actions first.
Device-specific behavior is applied afterward.

``` text
NAV_UP
NAV_DOWN
NAV_LEFT
NAV_RIGHT
NAV_SELECT
BACK

REWIND
PLAYPAUSE
FFWD

VOLUME_UP
VOLUME_DOWN
MUTE

POWER
MODE_1
MODE_2
MODE_3
```

The hardware knows **what the human did**. Configuration determines
**what that action means on the network**.

## Configurable Network Commands

Each generic action can map to a configurable HTTP request. This allows
different rooms to contain different brands or device types without
changing the core firmware.

``` text
Room1.Media.Home:
    method: POST
    url: http://<media-device>/keypress/Home

Room1.Media.Up:
    method: POST
    url: http://<media-device>/keypress/Up

Room1.AVR.VolumeUp:
    method: GET
    url: http://<avr-device>/<configured-command>
```

Initial command configuration should stay intentionally small:

-   HTTP method
-   URL
-   Optional body

Add custom headers or more complicated request features only when a real
device requires them. We do not need to turn Clonker configuration into
Postman.

## Persistent Configuration

The FeatherS3\[D\] stores configuration in **nonvolatile flash**, not
persistent RAM. Configuration therefore survives complete power loss.
CircuitPython code loads it again at boot.

A possible organization:

``` text
CIRCUITPY/
    code.py
    settings.toml          # secrets / Wi-Fi bootstrap values
    clonker_config.json    # rooms, commands, preferences
    sounds/
        clonk.wav
        startup.wav
```

Do **not** commit the real `settings.toml`, Wi-Fi credentials,
passwords, tokens, or other secrets to the public GitHub repository. A
sanitized `settings.example.toml` can document the required fields.

## iOS Shortcut Configuration Interface

The initial configuration UI should stay deliberately simple: an
iPhone/iPad Shortcut sends HTTP requests to the Clonker ESP32 over the
local network.

``` text
iPhone / iPad Shortcut
        |
        | HTTP POST over home Wi-Fi
        v
http://clonker.local/api/config
        |
        +--> validate request
        +--> update running configuration
        +--> save configuration to flash
        +--> reply OK / error
```

The Shortcut can expose friendly configuration choices such as:

``` text
Configure Clonker

Room 1
    Name
    Media
    AVR

Room 2
    Name
    Media
    AVR

Room 3
    Name
    Media
    AVR

Actions
    Home
    Up
    Down
    Left
    Right
    Select
    Back
    Rewind
    Play/Pause
    Fast Forward
    Volume Up
    Volume Down
    Mute
    ...
```

Use HTTP `POST` bodies (for example JSON) rather than putting passwords
or sensitive values into query-string URLs.

Ordinary configuration changes and firmware/code updates should remain
**separate workflows**.

## Configuration Transport: HTTP

Clonker's persistent configuration should be editable over the local
network without requiring a firmware update or USB connection.

The simplest model is a tiny HTTP server running on the ESP32 while
Clonker is awake. An iOS Shortcut, browser, or other LAN client can send
configuration changes to it.

``` text
iPhone / iPad / Browser
        |
        | HTTP over local Wi-Fi
        v
Clonker ESP32 HTTP server
        |
        +--> GET current configuration
        +--> validate requested changes
        +--> update configuration in RAM
        +--> write configuration to flash
        +--> reply success / error
```

This does **not** require Linux or a separate operating-system "server
process." It is simply part of the CircuitPython program: while Clonker
is awake, the main event loop services incoming HTTP requests along with
buttons, encoders, the OLED, audio, and device commands.

### Possible Clonker-hosted configuration page

A later version could serve a very small web page directly from Clonker:

``` text
http://clonker.local/
```

The page might expose:

``` text
CLONKER CONFIGURATION

Room 1: DEN
  Media endpoint: [...]
  AVR endpoint:   [...]

Room 2: SUN
  Media endpoint: [...]
  AVR endpoint:   [...]

Room 3: AUX
  Media endpoint: [...]
  AVR endpoint:   [...]

Actions:
  HOME       [...]
  BACK       [...]
  UP         [...]
  DOWN       [...]
  LEFT       [...]
  RIGHT      [...]
  SELECT     [...]
  REWIND     [...]
  PLAYPAUSE  [...]
  FFWD       [...]
  VOLUME_UP  [...]
  VOLUME_DOWN [...]
  MUTE       [...]
  POWER      [...]
```

This could eventually replace or complement the iOS Shortcut
configuration interface. It is not required for the first bench version.

## Power, Wake, and System Control

Clonker's **own power state** and the selected room's **POWER action**
are two different things.

A modern remote generally does not require the user to turn the remote
itself on before using it. The remote spends most of its time in a
low-power state, wakes when a control is used, sends the requested
command, and eventually returns to sleep.

Clonker should aim for the same behavior.

### Proposed SYSTEM/POWER behavior

The guarded SYSTEM/POWER button can have a useful dual role:

``` text
Clonker sleeping
      |
      | SYSTEM/POWER pressed
      v
Wake ESP32
      |
      +--> connect/reconnect Wi-Fi as needed
      +--> load persistent configuration
      +--> read physical room selector
      |
      v
Execute selected room's configured POWER action
      |
      v
Remain awake for normal operation
      |
      | inactivity timeout
      v
Return to low-power sleep automatically
```

This means the user should not normally need to press SYSTEM/POWER a
second time merely to "turn off the remote." Clonker can manage its own
sleep state automatically.

The exact wake behavior, Wi-Fi reconnection time, inactivity timeout,
and sleep mode should be determined experimentally on the real
FeatherS3\[D\]. Battery-life assumptions should be based on measurements
rather than guesses.

### HTTP availability follows Clonker's wake state

While Clonker is awake, its CircuitPython program can service the local
HTTP configuration API and optional configuration web page.

In a sufficiently deep sleep state, Wi-Fi will not be available and
Clonker will not answer HTTP requests. That is acceptable: wake Clonker
before configuring it.

``` text
CLONKER ASLEEP
    -> very low consumption
    -> HTTP unavailable

CLONKER AWAKE
    -> controls active
    -> Wi-Fi available
    -> HTTP API/configuration page available
```

### POWER is still just a configurable action

Waking Clonker does not dictate how the entertainment system itself is
powered. After waking, Clonker executes the `POWER` action configured
for the currently selected room.

For example:

``` text
SYSTEM/POWER press
    -> wake Clonker
    -> selector says ROOM1
    -> look up ROOM1 / POWER
    -> execute configured network command
```

That command might target a TV, AVR, media device, or some future
system-level sequence. The core firmware should not assume that `POWER`
means "LG TV power" or any other particular brand/device.

## Command Routing, CEC, ARC/eARC, and Volume

Different physical controls may naturally target different devices in
the same room.

For example, a room using a Roku, Denon AVR, and LG TV might be
configured conceptually as:

``` text
ROOM1

NAV_UP        -> Roku/media device
NAV_DOWN      -> Roku/media device
NAV_LEFT      -> Roku/media device
NAV_RIGHT     -> Roku/media device
NAV_SELECT    -> Roku/media device
BACK          -> Roku/media device

REWIND        -> Roku/media device
PLAYPAUSE     -> Roku/media device
FFWD          -> Roku/media device

VOLUME_UP     -> Denon AVR
VOLUME_DOWN   -> Denon AVR
MUTE          -> Denon AVR

POWER         -> configured system/TV action
```

This routing is configuration, not firmware architecture.

### Prefer the authoritative device when practical

If the Denon AVR is the component actually controlling speaker volume,
Clonker should generally send volume commands directly to the Denon
rather than deliberately routing them through another component.

Conceptually:

``` text
Preferred when practical:

Clonker
    -> network command
    -> Denon AVR
    -> volume changes
```

A television may also be able to accept a volume request and use
HDMI-CEC System Audio Control to coordinate the change with an AVR or
soundbar:

``` text
Clonker
    -> TV command
    -> TV
    -> HDMI-CEC
    -> AVR / soundbar
```

That may be useful in some installations, but it introduces an
intermediary when Clonker can already address the authoritative audio
device directly.

**ARC/eARC and CEC should not be treated as the same thing.** ARC/eARC
primarily provides the HDMI audio-return path. HDMI-CEC provides
device-control coordination, including behaviors such as system audio
and volume control.

### Configuration wins

None of these routing choices should be hard-coded.

Another room might intentionally use:

``` text
VOLUME_UP    -> LG TV
VOLUME_DOWN  -> LG TV
MUTE         -> LG TV
```

and rely on the television and HDMI-CEC to coordinate a soundbar.

The physical control still means only `VOLUME_UP`. The room
configuration determines where that action goes.

This reinforces the central rule:

> **Clonker controls actions, not brands --- and devices own their own
> state.**

## Draft Persistent Configuration

The exact format is not locked yet. XML is human-readable and makes the
configurable structure obvious, so the following is a useful design
draft. JSON may ultimately be more convenient in CircuitPython; the
important part is the data model rather than the syntax.

``` xml
<?xml version="1.0" encoding="UTF-8"?>
<clonker version="1">

  <device>
    <name>THE CLONKER 10000</name>
    <hostname>clonker</hostname>
  </device>

  <rooms>
    <room id="1" name="DEN">
      <endpoints>
        <media baseUrl="http://192.168.1.100"/>
        <avr baseUrl="http://192.168.1.101"/>
      </endpoints>

      <actions>
        <action name="HOME"       method="POST" target="media" path="/keypress/Home"/>
        <action name="BACK"       method="POST" target="media" path="/keypress/Back"/>
        <action name="NAV_UP"     method="POST" target="media" path="/keypress/Up"/>
        <action name="NAV_DOWN"   method="POST" target="media" path="/keypress/Down"/>
        <action name="NAV_LEFT"   method="POST" target="media" path="/keypress/Left"/>
        <action name="NAV_RIGHT"  method="POST" target="media" path="/keypress/Right"/>
        <action name="NAV_SELECT" method="POST" target="media" path="/keypress/Select"/>

        <action name="REWIND"     method="POST" target="media" path="/keypress/Rev"/>
        <action name="PLAYPAUSE"  method="POST" target="media" path="/keypress/Play"/>
        <action name="FFWD"       method="POST" target="media" path="/keypress/Fwd"/>

        <action name="VOLUME_UP"   method="GET" target="avr" path="/CONFIGURE_ME"/>
        <action name="VOLUME_DOWN" method="GET" target="avr" path="/CONFIGURE_ME"/>
        <action name="MUTE"        method="GET" target="avr" path="/CONFIGURE_ME"/>

        <action name="POWER"       method="POST" target="CONFIGURE_ME" path="/CONFIGURE_ME"/>
      </actions>
    </room>

    <room id="2" name="SUN">
      <endpoints>
        <media baseUrl="http://CONFIGURE_ME"/>
        <avr baseUrl="http://CONFIGURE_ME"/>
      </endpoints>
      <actions>
        <!-- Same generic Clonker actions; commands may be completely different. -->
      </actions>
    </room>

    <room id="3" name="AUX">
      <endpoints>
        <media baseUrl="http://CONFIGURE_ME"/>
        <avr baseUrl="http://CONFIGURE_ME"/>
      </endpoints>
      <actions>
        <!-- Same generic Clonker actions; commands may be completely different. -->
      </actions>
    </room>
  </rooms>

  <preferences>
    <clonkVolume>70</clonkVolume>
    <oledBrightness>100</oledBrightness>
  </preferences>

</clonker>
```

The example Roku paths are illustrative of the configuration model;
actual device commands should be verified during implementation.
`CONFIGURE_ME` deliberately marks values that are expected to be
supplied for a particular installation.

The configuration format should remain easy to inspect, export, back up,
and restore. Secrets such as Wi-Fi passwords should remain separate from
this ordinary application configuration.

## Possible Local API

A simple first API might look something like:

``` text
POST /api/config        persistent configuration update
GET  /api/status        current Clonker status
POST /api/test/clonk    play test sound
POST /api/test/display  test OLED
POST /api/reboot        reboot controller
```

A browser-based configuration page served directly by Clonker is a
possible future enhancement, but it should **not complicate V1**.

## Runtime Flow

``` text
Human action
    |
    v
Physical control
    |
    v
Read GPIO / encoder
    |
    v
Generate generic action
    |
    +--> read physical room selector
    |
    v
Look up configured command for that room/action
    |
    v
Send network request
    |
    v
Controlled device owns resulting device state
```

## Example: Maintained Room Selector

Conceptually:

``` python
def selected_room():
    if selector_is_position_1():
        return "Room1"

    if selector_is_position_2():
        return "Room2"

    return "Room3"


def handle_action(action):
    room = selected_room()
    command = config[room]["actions"][action]
    send_http(command)
```

There is no need to persist `current_room` every time the selector
moves. **The switch itself is the memory.**

## State Query Rule

**Do not maintain duplicate truth unless there is a compelling reason.**

If Clonker eventually wants to display AVR volume, ask the AVR. If it
wants to know the active Roku application, query the Roku when its API
supports it.

Avoid maintaining a second internal copy of device state that can become
stale.

In other words:

``` text
Physical state       -> ask the physical control
Configuration state  -> ask Clonker's persistent config
Device state         -> ask the device
Temporary state      -> keep it in RAM
```

## Why Not an Old-Style Universal Remote?

Older universal remotes often had to control largely independent
devices:

``` text
TV POWER
AVR POWER
DVD POWER
CABLE POWER

TV INPUT
AVR INPUT

TV VOLUME
AVR VOLUME
```

That encouraged device modes, macros, multiple power buttons, and
remote-side assumptions about system state.

Modern HDMI-CEC, ARC/eARC, and network-controlled equipment can
coordinate much more of this themselves. Clonker should take advantage
of that rather than recreate the complexity of older "smart" remotes.

**Clonker should not try to become the brains of the home theater.**

It should be an unusually satisfying physical control surface that sends
the right actions to equipment that already knows its own state.

## V1 Design Guardrails

-   Three rooms maximum, matching the physical selector.
-   Generic actions first; brand/device mappings live in configuration
    whenever practical.
-   Keep persistent configuration human-readable and easy to back up.
-   Keep Wi-Fi credentials and secrets separate from public project
    configuration.
-   Use iOS Shortcuts as the initial configuration front end.
-   Keep ordinary configuration separate from firmware updates.
-   Do not build a giant device-state machine.
-   Let CEC/ARC/eARC and the controlled devices do work they already
    know how to do.
-   Add complexity only when an actual device or use case requires it.

## Enclosure Path --- Later

Once the breadboard and real controls are working:

``` text
Working breadboard
    ->
Arrange real controls physically
    ->
Full-size cardboard / foam-board mockup
    ->
Couch usability testing
    ->
Measure final hardware
    ->
Parametric CAD
    ->
Prototype fabrication / 3D print
    ->
Final enclosure
```

A promising final construction is a **hybrid enclosure**: a rigid metal,
acrylic, or wood control face with 3D-printed internal chassis,
brackets, mounts, and other custom pieces rather than automatically
printing the entire case.

Friends' 3D printers can provide the fabrication hardware. The Clonker
project can create portable design files such as STEP, STL/3MF, and DXF
without requiring ownership of a printer.

------------------------------------------------------------------------

**Clonker controls actions, not brands --- and devices own their own
state.**

*More awesome stuff to come...*
