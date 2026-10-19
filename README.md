# THE CLONKER 10000
(extreme beta version)

<p align="center">
  <img src="images/main_knobs.jpeg" width="350" alt="Clonker Main Knobs">
</p>
<p align="center">
  <img src="images/tmp_oled_screen.jpeg"
       height="150"
       alt="Clonker Stupid Screen"
       style="vertical-align: top;">
  &nbsp;&nbsp;
  <img src="images/tmp_tri_selector.jpeg"
       height="150"
       alt="Clonker Sample System Selector"
       style="vertical-align: top;">
</p>

**`THE CLONKER 10000`** is a DIY “maker” project to build a custom remote control for my home theater and HiFi stereo desires.

*(Note: For now, imagine the above awesome controls mounted on a big-ass, honkin’ brick of a case that will possibly weigh anywhere from 0.5 to 10 lbs. 😉 … maybe even steam-punk’ish)*

## Inspiration

I dislike modern remote controls. I think their designers have forgotten that humans are tactile beasts. I want a remote control that I can fumble around for in the dark, pick up, and use effortlessly. Yes, I am aware of “big button” products created for accessibility (very commendable) … BUT, I desire to handle REAL controls; I’d like my fingertips to caress beautiful metallic buttons and knobs I have only seen the likes of in other industries, i.e., HiFi stereo systems, nuclear submarines, etc. Some of the vintage TV remotes came close but, still, meh.

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

AND I want my tactile controls to please my aging ears with accompanying **audio** feedback like “**CLONK**”. Thus was born **The Clonker 10000** maker project … my realization that the only way I was going to get what I desire was to build it myself.

## Technical Details

This Beta version of The Clonker will be a Wi-Fi-only device, containing an easily programmable Raspberry Pi Pico 2 W (RP2350) controller running CircuitPython 10.3.1. It will first be tested against my own equipment: Roku Ultra streaming devices, Denon AV receivers, and possibly LG TVs. I definitely plan to test it against Apple TVs and Amazon Fire TV Sticks shortly after the initial birth. I have no plans on adding IR to it at this time.

## Current Hardware

Note: Just some high-lights for now…

Raspberry Pi Pico 2 W · Grayhill · Grayhill optical VOLUME encoder · Bourns SELECT encoder · Kilo metal knobs · metal navigation buttons · tiny OLED · I²S amp + speaker · illuminated SYSTEM MASTER

## Sample Software Functionality

Volume (ofc), Power ON / OFF, Navigation arrows and Select, and some audio / video selections like below… Also, see the [Architecture Document](docs/ARCHITECTURE.md) 

<p align="left">
  <img src="images/clonker_config_sample.png"
       height="300"
       alt="Sample Actions"
       style="vertical-align: top;">
</p>

## Project Status

### Configuration System — JSON v2 Operational ✅

The Clonker 10000 now runs its JSON v2 configuration system on the
Raspberry Pi Pico 2 W with CircuitPython 10.3.1.

The configuration system provides:

- Three fixed rooms, each with an editable name.
- TV, AVR, and streaming-device endpoints for each room,
  supporting IPv4 addresses with optional HTTP ports.
- Fourteen configurable fundamental actions per room.
- A planned V1 enhancement giving `power-toggle` and
  `mute-toggle` separate ON/OFF command paths.
- Simple per-room RAM command history for toggle actions,
  without requiring device-state queries.
- Fourteen configurable fundamental actions per room.
- Browser editing through the Clonker management interface on port 9090.
- Validated JSON configuration loading and saving.
- Revision checking and stale-edit protection.
- No-change detection to avoid unnecessary flash writes.
- Verified file writes and rotating configuration backups.
- Startup fallback to validated backups without silently repairing the primary file.
- Filesystem write protection in SERVICE (USB) mode.

The JSON v2 configuration engine and browser interface have passed
initial on-device tests, including successful saves, backup rotation,
no-change detection, and stale-revision conflict handling.

Additional failure-injection and persistence testing remains outstanding.
See the test record for the distinction between verified and pending behavior.

The previous XML v1 implementation remains in the repository as a
rollback reference; JSON v2 is the active configuration format.

**Next major milestone:** Connect the physical controls and action
dispatcher to actual home theater device commands.

📋 [Configuration Test Results](docs/configuration-testing.md)

📐 [Architecture](docs/ARCHITECTURE.md)

More awesome stuff to come…

**CLONK!** ⚡🔩
