# THE CLONKER 10000 — Hardware Parts List

> Less sleek. More CLONK.

## Purpose

This document identifies the physical components used in
THE CLONKER 10000, including manufacturer part numbers,
mechanical specifications, mounting hardware, and the
actual drill sizes used during construction.

It serves as a reference for maintenance, replacement,
modification, and reproduction of the hardware.

This document describes **what is installed and how it
fits**. Design decisions, wiring, experiments, and project
history are documented separately.

For GPIO assignments, wiring, and electrical design,
see [Hardware Design](HARDWARE_DESIGN.md).

---

## Physical Controls

All listed exterior control holes were drilled and
successfully test-fitted.

**✓ = Actual drilled and verified hole size.**

| Control | Manufacturer / Part # | Hole / Drill Size |
|---|---|---|
| **Volume / Mute** | Bourns PEC11R-4215F-S0024 rotary encoder | 7.14 mm (9/32") — twist ✓ |
| ↳ Volume knob | Kilo OEJNI-90-3-5 | — |
| **Custom Actions / Run** | Bourns PEC11R-4215F-S0024 rotary encoder | 7.14 mm (9/32") — twist ✓ |
| ↳ Action knob | Kilo OEJL-63-4-7 | — |
| **Home (red)** | E-Switch PS1023, red square pushbutton | 12.7 mm (1/2") — twist ✓ |
| **Back (black)** | E-Switch PS1023ABLK, black square pushbutton | 12.7 mm (1/2") — twist ✓ |
| **Nav Up** | Philmore 30-146 momentary pushbutton | 12.7 mm (1/2") — twist ✓ |
| **Nav Down** | Philmore 30-146 momentary pushbutton | 12.7 mm (1/2") — twist ✓ |
| **Nav Left** | Philmore 30-146 momentary pushbutton | 12.7 mm (1/2") — twist ✓ |
| **Nav Right** | Philmore 30-146 momentary pushbutton | 12.7 mm (1/2") — twist ✓ |
| **Nav Select / OK** | YMJSAN 19 mm metal momentary pushbutton, high head | 20 mm (≈25/32") — step ✓ |
| **Skip Back** | Philmore 30-2299 sub-mini momentary pushbutton | 7.14 mm (9/32") — twist ✓ |
| **Play / Pause** | Philmore 30-111 momentary pushbutton | 10 mm (≈25/64") — step ✓ |
| **Skip Forward** | Philmore 30-2299 sub-mini momentary pushbutton | 7.14 mm (9/32") — twist ✓ |
| **Room Selector** | uxcell 2P3T, 3-position rotary switch | 10 mm (≈25/64") — step ✓ |
| ↳ Selector knob | uxcell s18102300ux0967, 6 mm D-shaft | — |
| **Power Toggle** | YMJSAN 19 mm metal momentary pushbutton, high head (non-illuminated) | 20 mm (≈25/32") — step ✓ |
| **CONFIG / RUN (side)** | Dorman Conduct-Tite 84815 racing-style switch | 12.7 mm (1/2") ✓ |
| **SERVICE / DEVICE (internal)** | Philmore 30-10007 SPST toggle switch | No exterior hole required |

### Rotary Encoders

Both Volume/Mute and Custom Actions/Run use
Bourns PEC11R-4215F-S0024 rotary encoders.

- Incremental rotary operation with detents.
- Integrated momentary pushbutton.
- Threaded panel-mount bushing.
- Verified mounting opening: 9/32 inch.
- Separate Kilo knobs as listed above.

The mounting hole accommodates the threaded bushing,
not merely the smaller rotating shaft.

### Navigation and Playback Buttons

The four Philmore 30-146 navigation buttons fit
1/2-inch openings.

The Home and Back square pushbuttons also fit
1/2-inch openings.

The Philmore 30-111 Play/Pause button fits a
10 mm opening.

The Philmore 30-2299 Skip Back and Skip Forward
buttons require 9/32-inch openings.

### Metal Pushbuttons

Both Nav Select/OK and Power Toggle use the same
YMJSAN 19 mm high-head metal momentary pushbutton.

- **Manufacturer:** YMJSAN
- **Type:** Momentary, normally open
- **Nominal size:** 19 mm
- **Illumination:** None
- **Verified mounting hole:** 20 mm
- **Quantity:** 2

The Power Toggle also uses a separate red flip-up
protective guard.

### Room Selector

- **Manufacturer:** uxcell
- **Switch type:** 2P3T, three-position rotary
- **Mounting hole:** 10 mm
- **Shaft:** 6 mm D-shaped
- **Knob:** uxcell s18102300ux0967

The selector provides three mechanical positions
for room selection.

### Configuration and Service Switches

**CONFIG / RUN**

- Dorman Conduct-Tite 84815 racing-style switch.
- Mounted through a 1/2-inch opening in the enclosure side.
- Circular mounting hole despite its square external housing.

**SERVICE / DEVICE**

- Philmore 30-10007 SPST toggle switch.
- Internal mounting; no dedicated exterior opening.

---

## Display and Mounting Hardware

### OLED Display

- **Display:** SSD1306 monochrome OLED
- **Size:** 0.49 inch
- **Resolution:** 64 × 32 pixels
- **Interface:** I²C
- **Mounting:** Four machine screws with nuts and nylon spacers

### OLED Mounting Parts

| Component | Manufacturer / Part # | Hole / Drill Size |
|---|---|---|
| **OLED mounting screws (×4)** | PLPCI M2.5 × 0.45 × 16 mm, model 9130870 | 2.78 mm (7/64") — twist ✓ |
| ↳ Matching nuts (×4) | PLPCI M2.5 × 0.45, model 9120267 | — |
| ↳ Nylon spacers (×4) | Bivar 907-3MM, 3 mm round nylon | — |

The OLED connector cable passes through a separate
hand-cut slot near the upper edge of the display.

The four 7/64-inch mounting holes provide sufficient
clearance for minor rotational adjustment when the
screws are loosened.

---

## Controller and Supporting Electronics

| Component | Manufacturer / Part # | Purpose |
|---|---|---|
| **Microcontroller** | Raspberry Pi Pico 2 W | Main controller, Wi-Fi, and CircuitPython runtime |
| **Expansion board** | Adafruit Cowbell for Pico | Supporting electrical connections and distribution |
| **OLED display** | SSD1306 0.49-inch, 64 × 32 | Physical-control feedback |
| **Ground distribution** | WAGO 221-412 / 221-413 / 221-415 | Lever-nut wiring connections |

The Pico 2 W is the primary controller.

For GPIO assignments, wiring, and supporting electrical
design, see [Hardware Design](HARDWARE_DESIGN.md).

---

## Battery and Power Hardware

### Components

| Component | Manufacturer / Part # | Qty | Purpose |
|---|---|---:|---|
| **Battery power module** | DFRobot DFR0969 | 1 | Rechargeable battery management and regulated 5 V output |
| **Rechargeable cells** | 18650 lithium-ion; exact model not recorded | 2 | Portable power |
| **Pico power cable** | USB-A to Micro-USB | 1 | Connects DFRobot output to Pico 2 W |
| **Charging connector** | Panel-mounted USB-C extension | 1 | External charging access |

### DFRobot DFR0969

- **Manufacturer:** DFRobot
- **Manufacturer part number:** DFR0969
- **DigiKey part number:** 1738-DFR0969-ND
- **Battery positions:** Two 18650 cells
- **Charging input:** USB-C
- **Regulated output:** USB-A, nominal 5 V
- **Additional connections:** Board-mounted power pads
- **Operating switch:** NORMAL / HOLD
- **Clonker configuration:** HOLD

The module's USB-A output powers the Pico through its
Micro-USB connector.

The USB-C charging input is accessible through the
enclosure's panel-mounted extension.

The two rechargeable 18650 cells are installed in
the module's battery positions.

For charging behavior, power-path characteristics,
electrical measurements, and battery endurance, see
[Hardware Design](HARDWARE_DESIGN.md) and
[Development History](DEVELOPMENT_HISTORY.md).

---

## Faceplate and Enclosure

### Aluminum Faceplate

- **Manufacturer:** PATIKIL
- **Material:** 6061-T651 aluminum
- **Dimensions:** 152.4 × 203.2 mm (6 × 8 inches)
- **Thickness:** Approximately 1.5 mm (1/16 inch)
- **Finish:** Brushed aluminum
- **Manufacturer part:** pta240807tt001253
- **Amazon ASIN:** B0DHR7TLNX

### Mounting Arrangement

- Aluminum faceplate secured to the enclosure using ten perimeter mounting points.
- Fender washers used beneath the plate where clearance permits.
- Smaller washers used where internal component clearance is limited.
- Nuts secure the faceplate from inside the enclosure.
- Internal enclosure foam trimmed for controls and wiring clearance.

The original protective film was retained during
drilling and removed after completion.

---

## Drilling and Mechanical Reference

### Drill Size Conventions

All dimensions in the controls table represent
actual drilled and successfully test-fitted holes.

- **Step:** Final opening made using a step drill.
- **Twist:** Final opening made using a conventional twist drill.
- **✓:** Verified finished mounting hole.

Hole dimensions are given in millimeters, followed
by imperial equivalents.

### Drilling Details

- Initial pilot holes: 1.6 mm (1/16 inch).
- Enlarged pilot holes: 3.2 mm (1/8 inch), where appropriate.
- Step drills used for larger openings and metric sizes.
- Twist drills used for encoder holes, smaller controls, and OLED mounting.
- Controls test-fitted before accepting their final hole diameters.
- Sharp edges deburred, including the OLED connector opening.

### Component-Specific Mounting Notes

**Bourns encoders:** The threaded mounting bushing
requires a 9/32-inch opening.

**19 mm metal pushbuttons:** The verified 20 mm
mounting holes provide acceptable clearance.

**Play/Pause:** The 10 mm opening fits the Philmore
30-111 button without requiring the originally
estimated larger opening.

**Room selector:** The 10 mm opening fits the uxcell
selector's mounting bushing.

**Skip Back / Forward:** Both buttons require
9/32-inch openings.

**OLED:** Four 7/64-inch holes fit the M2.5
mounting hardware.

**CONFIG / RUN:** The side-mounted switch uses
a 1/2-inch circular opening.

**SERVICE / DEVICE:** No exterior hole required.

---

## Test Equipment

Equipment used during hardware development and
diagnostics, but not installed as part of the
Clonker's normal operating hardware.

| Equipment | Description |
|---|---|
| **USB power tester** | Color TFT inline USB voltage/current meter; exact model not recorded |

---

## Document Maintenance

Update this parts list when:

- A component is replaced or changed.
- A manufacturer or part number is confirmed.
- Mounting hardware or dimensions change.
- The enclosure or faceplate design changes.
- Additional permanent hardware is installed.

Keep experiments, test results, design decisions,
and project status in their respective documents.

The goal is to preserve enough physical information
to repair, reproduce, or rebuild THE CLONKER 10000
without reverse-engineering the original hardware.

---

*One Monster. One Dumb Queue™.*

**Less sleek. More CLONK.**
