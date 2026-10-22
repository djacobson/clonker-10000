# THE CLONKER 10000

### Less sleek. More CLONK. ⚡🔩

**Extreme beta — an enthusiast-built home theater remote with an unreasonable appreciation for substantial metallic controls.**

<p align="center">
  <img src="images/main_knobs.jpeg" width="350" alt="Clonker Main Knobs">
</p>

<p align="center">
  <img src="images/tmp_oled_screen.jpeg"
       height="150"
       alt="Clonker OLED Display Concept"
       style="vertical-align: top;">
  &nbsp;&nbsp;
  <img src="images/tmp_tri_selector.jpeg"
       height="150"
       alt="Clonker Room Selector Concept"
       style="vertical-align: top;">
</p>

**THE CLONKER 10000** is my DIY maker project to build the home theater and Hi-Fi remote control I've always wanted.

Fewer buttons. Bigger switches. Beautiful metallic knobs. Real tactile feedback. Modern Wi-Fi control.

And perhaps a case that opens with actual lunchbox latches.

*(For now, imagine those magnificent controls mounted on a big-ass, honkin' brick of an enclosure, weighing somewhere between 0.5 and 10 pounds. Possibly steampunk-ish. Definitely not something that disappears between sofa cushions.)*

---

## Why Does This Thing Exist?

I dislike modern remote controls.

Not because they're modern. I like modern technology.

I dislike the tiny, nearly indistinguishable rubber buttons, the obsession with sleekness, and the apparent assumption that everybody operates their television while staring directly at the remote.

Humans are tactile beasts.

I want to reach for my remote in pitch-black darkness, immediately recognize what I'm touching, and operate the important functions without looking.

I want my fingertips to encounter the kind of beautiful metallic knobs and substantial switches normally reserved for high-end Hi-Fi equipment, industrial control panels, and nuclear submarines.

Some vintage remotes came close.

<p align="center">
  <img src="images/nr1_nuclear_sub.jpeg"
       height="300"
       alt="NR-1 Nuclear Submarine"
       style="vertical-align: top;">
  &nbsp;&nbsp;
  <img src="images/vintage_zenith_remote.jpeg"
       height="300"
       alt="Vintage Zenith Remote"
       style="vertical-align: top;">
</p>

And when I press a button, I'd like my aging ears to hear a satisfying little **CLONK**.

Thus was born The Clonker 10000.

Because apparently the only way to get the remote I want is to build the damn thing myself.

---

## The Clonker Design Manifesto

**The Clonker 10000 is not a return to the past. It's a selective rescue operation.**

Once upon a time, remote controls had real buttons, satisfying mechanical feedback, and enough heft to remind you that you were holding an actual piece of equipment.

Unfortunately, they also had 117 buttons, six POWER switches, three mysterious INPUT selectors, and a row of controls nobody had touched since the Reagan administration.

Then came the modern remote: sleek, minimalist, and apparently designed for people with microscopic thumbs, perfect eyesight, and a deep emotional attachment to sponsored streaming services.

**The Clonker rejects the worst of both eras.**

We're keeping:

- Big, beautiful metallic switches and knobs.
- Fewer, thoughtfully chosen controls.
- Essential functions you can operate in complete darkness.
- Mechanical feedback that leaves no doubt something happened.
- Repairability and accessible internals.
- Modern Wi-Fi connectivity, configurable commands, and firmware updates.
- A healthy appreciation for vintage Hi-Fi equipment and nuclear submarines.

We're throwing overboard:

- The 117-button remote with six different POWER buttons.
- Microscopic rubber chiclets masquerading as controls.
- Sponsored streaming-service buttons.
- Sealed enclosures and microscopic proprietary screws.
- Complicated universal-remote programming rituals.
- Manufacturer IR code archaeology.
- Elaborate activity wizards that lose their minds when somebody manually changes an input.
- Anything designed primarily to look fabulous in a marketing photograph.

### The Harmony Memorial Department

I remember the Logitech Harmony era.

Those remotes were an ambitious attempt to bring order to the home theater industry's spectacular mess.

I respect the effort.

I also remember the configuration software.

The Clonker keeps the useful idea — one configurable controller for multiple devices — and leaves the infrared archaeology behind.

No hunting through 400 manufacturer codes. No teaching one remote to blink at another. No spending Saturday programming a *Watch TV* activity that gets confused when somebody turns the receiver on manually.

Our initial design uses network commands and readable configuration.

No IR is planned for the current version, although future optional support isn't ruled out.

**We want to watch the movie, not spend Saturday teaching the remote what a movie is.**

### Credit Where Credit Is Due

A respectful tip of the hat to companies making simplified, large-button remotes for seniors and people with accessibility needs.

They're addressing genuine problems, and I applaud them.

The Clonker isn't intended to replace or compete with those products.

I'm simply wondering why tactile, easy-to-find controls, sensible button counts, and straightforward operation shouldn't be desirable for *everybody*.

After all, you shouldn't have to qualify for a senior discount to get a volume button you can find in the dark.

**Accessibility isn't a niche feature. Sometimes it's just good engineering.**

### Serviceability Is a Feature

The enclosure should be something you can open, inspect, modify, and repair.

I'm seriously considering actual lunchbox-style latches.

And a real internal work light.

Because if servicing your remote requires three proprietary screwdrivers, reading glasses, tweezers, and holding a flashlight in your teeth, somebody has lost the plot.

These are design ideas, not completed hardware features.

**The Clonker isn't retro. It isn't minimalist. It's selectively maximalist.**

Maximum attention to the things that matter. Minimum tolerance for everything that doesn't.

---

## The Officially Unofficial Clonker Tagline Competition

The marketing department has been disbanded.

Unfortunately, nobody told them to stop submitting slogans.

The current finalists:

- **Less sleek. More CLONK.**
- **Six power buttons were five too many. Sponsored buttons are one too many.**
- **Our buttons are so big, the marketing department called them a safety hazard.**
- **No IR codes. No programming rituals. No HELP button to help the HELP button.**
- **[The Complete List](docs/TAGLINE_COMPETITION.md)** — Because apparently the disbanded marketing department didn't get the memo.

**Winner:** TBD. The selection committee is still arguing.

**Selection committee:** One engineer and an AI with questionable judgment.

**Marketing department:** Still disbanded.

---

## What Is the Clonker Actually Going to Do?

The Clonker is being developed as a configurable Wi-Fi remote for multiple home theater systems.

The goal is to control everyday functions through a small number of physical controls rather than a forest of device-specific buttons.

### Fundamental actions

Each configured room supports fourteen standard action IDs:

| Function | Actions |
|---|---|
| Volume | Up, Down, Mute Toggle |
| Navigation | Up, Down, Left, Right, Select |
| Navigation shortcuts | Back, Home |
| Playback | Play/Pause, Skip Back, Skip Forward |
| Power | Power Toggle |

Each action can be mapped to a configured TV, AV receiver, or streaming device.

The current configuration supports three rooms, each with its own devices and command mappings.

Custom actions are planned for additional functions such as listening modes and other equipment-specific operations.

### Device Compatibility Roadmap

Clonker's current, tested network-control targets are Denon AV receivers and Roku streaming devices.

**Apple TV support is an explicit future project objective.** The long-term goal is to support Apple TV alongside Roku through the same fundamental Clonker actions, without requiring different physical controls.

Other network-controllable TVs, receivers, and streaming devices may be considered as the project develops.

Apple TV support has not yet been implemented or tested. Its protocol, pairing, authentication, and integration requirements will be investigated when that development phase begins.

**The goal is simple: the physical controls shouldn't care whether they're talking to a Denon, Roku, or something we haven't added yet.**

---

## The Hardware

The current controller is a **Raspberry Pi Pico 2 W (RP2350)** running **CircuitPython 10.3.1**.

The planned physical design includes:

- **Grayhill optical rotary encoder** with a large Kilo metallic VOLUME knob.
- **Bourns rotary encoder** with a smaller Kilo SELECTOR knob.
- Substantial tactile navigation and playback buttons.
- A prominent system-power button, potentially protected by a flip-up guard.
- A physical room selector.
- A separate CONFIG/RUN control.
- A tiny OLED status display.
- Optional piezo or I2S-powered audible feedback.
- A serviceable enclosure with enough personality to frighten a product-design committee.

The Pico 2 W is the active development platform.

An earlier ESP32-S3 Feather board was part of the original hardware exploration, but is not the current firmware target.

**Hardware reality check:** Most of the physical controls are still being evaluated and have not yet been wired into the running firmware.

See [Hardware & Physical Controls](docs/HARDWARE_CONTROLS.md) for the detailed inventory, proposed layout, GPIO status, and ongoing design decisions.

---

## Software Architecture

The Clonker uses a small, intentionally straightforward software architecture.

```text
Physical controls (planned)       Browser Test Remote
             |                             |
             v                             v
        Input events                 HTTP action API
             |                             |
             +--------------+--------------+
                            |
                            v
                     Action dispatcher
                            |
                            v
                    THE DUMB QUEUE
                     (implemented)
                            |
                            v
                   JSON v2 resolution
                            |
                            v
                  Outbound HTTP transport
                     (implemented)
                            |
                            v
                  Home theater equipment
                    Denon AVR / Roku
```

The shared **Dumb Queue™** accepts generic actions and executes them sequentially through the outbound HTTP transport.

The queue absorbs commands arriving faster than the network can process them. It does not make network I/O nonblocking.

Real Denon and Roku commands were successfully executed from the Pico on October 21, 2026.

### Configuration

Configuration is stored in JSON and edited through the Clonker's browser interface.

The system supports:

- Three fixed rooms with editable names.
- TV, AVR, and streaming-device endpoints per room.
- IPv4 addresses with optional HTTP ports.
- Fourteen fundamental actions per room.
- GET and POST command definitions.
- Separate ON and OFF command paths for mute and power toggles.
- Blank commands as intentional no-ops.
- Configuration revision checking.
- Stale-edit conflict protection.
- No-change detection.
- Rotating backups.
- Validated startup recovery.
- Filesystem write protection during USB SERVICE mode.

The ON/OFF paths are supported by the configuration schema.

**The runtime toggle-state selection logic is not yet implemented.**

Custom actions are reserved for a future phase.

### Management Interface

The Pico hosts a browser-based configuration and testing interface on port `9090`.

The interface currently provides:

- JSON configuration editing.
- Device and room settings.
- Configuration save and validation.
- A Test Remote with all fourteen fundamental actions.
- A clock synchronization interface.
- SERVICE/DEVICE filesystem ownership protection.

The Test Remote uses the same shared action dispatcher and Dumb Queue™ intended for the future physical controls.

**Real outbound HTTP control is operational.** The Pico has successfully executed configured Denon AVR and Roku commands over Wi-Fi.

The browser receives an acknowledgment when an action is queued. Actual device execution occurs subsequently through the cooperative scheduler.

The next development phase will focus on completing runtime toggle behavior, improving failure testing, and integrating the physical controls.

---

## A Peek at the Software

The configuration interface already exists and runs on the Pico.

<p align="left">
  <img src="images/clonker_config_sample.png"
       height="300"
       alt="Clonker Configuration Interface"
       style="vertical-align: top;">
</p>

The project also includes a browser Test Remote for exercising the same fundamental action IDs that future physical controls will invoke.

This allows the software architecture to be tested before committing to a final enclosure and GPIO wiring arrangement.

---

## Project Status

**October 21, 2026 — Chapter 3 complete. Extreme beta, but the little monster can now control real equipment.**

### Working and tested

- Raspberry Pi Pico 2 W running CircuitPython 10.3.1.
- Wi-Fi connectivity and browser management interface.
- JSON v2 configuration loading, validation, and persistence.
- Browser configuration editing and saving.
- Revision checking and stale-edit rejection.
- No-change detection and backup rotation.
- SERVICE/DEVICE jumper controlling filesystem write ownership.
- Browser Test Remote with fourteen fundamental action controls.
- Shared Dumb Queue™ with bounded capacity and cooperative scheduling.
- Outbound HTTP GET/POST transport using bounded blocking socket operations.
- Real Denon AVR Volume Up and Volume Down commands.
- Real Roku Home and Back commands.
- Controlled five-command burst test, with all five commands completing successfully and returning HTTP 200.

The queue can accept multiple commands before executing them sequentially. Network operations temporarily block the cooperative loop, and physical encoder responsiveness has not yet been measured.

### Not yet implemented or fully tested

- Runtime ON/OFF toggle command history.
- Physical button and rotary encoder integration.
- Physical room selection and CONFIG/RUN switching.
- Custom-action execution.
- OLED display and audible feedback.
- Final enclosure and power architecture.
- Comprehensive network failure and timeout recovery tests.
- Sustained high-rate command workloads.
- Additional configuration failure-injection tests.

The earlier XML configuration implementation remains in the repository as historical and rollback reference.

**Next major phase: Give the working Clonker its physical controls.**

The software has learned to communicate.

Now the big metal switches get their turn.

---

## Documentation

The project is being documented as it develops, including decisions, testing, and implementation boundaries.

| Document | Purpose |
|---|---|
| [Architecture](docs/ARCHITECTURE.md) | Overall system design and implementation boundaries |
| [Hardware & Physical Controls](docs/HARDWARE_CONTROLS.md) | Physical controls, component inventory, and design manifesto |
| [Configuration](docs/CONFIGURATION.md) | JSON v2 schema, validation, and recovery |
| [Firmware & Network](docs/FIRMWARE_NETWORK.md) | HTTP API, networking, and clock behavior |
| [Operating Modes](docs/OPERATING_MODES.md) | SERVICE/DEVICE and CONFIG/RUN |
| [Development](docs/DEVELOPMENT.md) | Development and deployment workflow |
| [Development History](docs/DEVELOPMENT_HISTORY.md) | Major Milestones in Clonker development |
| [Chapter 2 Handoff](docs/CHAPTER_2_HANDOFF.md) | Historical Chapter 2 handoff and development baseline |

This is a personal, experimental maker project, not a finished commercial product.

The documentation is intended to distinguish implemented behavior from ideas, prototypes, and future plans.

---

## The Grand Objective

Build a remote that combines the best of the shamefully forgotten past with the carefully curated best of the present.

Keep the beautiful controls.

Keep the modern electronics.

Keep the software flexibility.

Throw away the button farms, the rubber chiclets, the programming rituals, the sealed plastic, and the sponsored nonsense.

And maybe install a couple of lunchbox latches.

**THE CLONKER 10000**

**Less sleek. More CLONK.**

**CLONK! ⚡🔩**

*Designed by David Jacobson. Marketing department not consulted.*
