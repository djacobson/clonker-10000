# THE CLONKER 10000 — Hardware Parts List

> Less sleek. More CLONK.

## Purpose

This document identifies the physical components used in THE CLONKER 10000, including the electronics, controls, enclosure, mounting hardware, and power system.

It serves as a permanent reference for:

- Component identification and replacement parts.
- Manufacturer names and model numbers.
- Important hardware specifications.
- Actual faceplate and enclosure drilling measurements.
- Mechanical details useful when repairing or reproducing the hardware.

This is a hardware inventory and specifications reference, not a construction guide or development-status report.

For GPIO assignments, wiring, and control behavior, see [Hardware Design](HARDWARE_DESIGN.md).

For the system design, see [Architecture](ARCHITECTURE.md).

---

## Main Electronics

| Component | Manufacturer / Part # | Description |
|---|---|---|
| **Microcontroller** | Raspberry Pi Pico 2 W, UeeKKoo pre-soldered header version | RP2350-based microcontroller with onboard Wi-Fi; the Clonker's main processor |
| **GPIO expansion** | Adafruit Pico Cowbell — exact model to confirm | GPIO breakout and connection platform for the Pico |
| **OLED display** | Hosyond B077, 1.3-inch SH1106 | 128 × 64 monochrome I2C OLED display; purchased as a five-pack |
| **Wire connectors** | WAGO 221-415 | Compact five-conductor lever connectors used for internal wiring distribution |

### Raspberry Pi Pico 2 W

The Raspberry Pi Pico 2 W is the Clonker's main processor, running the firmware, managing physical controls, and communicating with network devices.

**Hardware specifications:**

- **Board:** Raspberry Pi Pico 2 W
- **Purchased version:** UeeKKoo, with pre-soldered color-coded headers
- **Microcontroller:** Raspberry Pi RP2350
- **Processor architecture:** Dual-core Arm Cortex-M33 or dual-core Hazard3 RISC-V
- **Maximum processor clock:** 150 MHz
- **SRAM:** 520 KB
- **Onboard flash:** 4 MB
- **Wireless controller:** Infineon CYW43439
- **Wi-Fi:** 2.4 GHz IEEE 802.11n (Wi-Fi 4)
- **Bluetooth hardware:** Bluetooth 5.2
- **GPIO:** 26 multifunction user GPIO pins
- **Interfaces:** 2 SPI, 2 I2C, 2 UART
- **ADC:** 3 externally available 12-bit ADC inputs
- **PWM:** 16 controllable PWM channels
- **Programmable I/O:** 12 PIO state machines
- **USB:** USB 1.1 controller with device and host support
- **Amazon ASIN:** B0DP54FWX1

**Clonker software:**

- CircuitPython 10.3.1
- Custom network-based remote-control firmware
- Physical input handling, configuration management, and HTTP communication

The Pico's limited RAM makes memory management and long-running reliability particularly important to the project.

### GPIO Expansion — Pico Cowbell

The Cowbell provides convenient access to the Pico's GPIO and power connections.

- **Manufacturer:** Adafruit
- **Model:** To be confirmed
- **Application:** Internal Pico connection and GPIO breakout platform

Exact product specifications will be added when confirmed.

### OLED Display — Hosyond SH1106

The OLED provides local visual feedback for the Clonker's physical controls and operating state.

**Hardware specifications:**

- **Manufacturer:** Hosyond
- **Model:** B077
- **Display size:** 1.3 inches
- **Resolution:** 128 × 64 pixels
- **Display controller:** SH1106
- **Interface:** I2C
- **Supply voltage:** Advertised 3–5 V
- **Display type:** Monochrome OLED
- **Viewing angle:** Advertised greater than 160 degrees
- **Original package:** Five modules
- **Amazon ASIN:** B0C3L7N917

The display uses a four-wire connection: GND, VCC, SCL, and SDA.

### Internal Wiring Connectors — WAGO

**Hardware specifications:**

- **Manufacturer:** WAGO
- **Series:** 221
- **Model:** 221-415
- **Connection positions:** Five
- **Connection method:** Lever-operated spring clamps
- **Housing:** Transparent
- **Supported conductors:** Solid, stranded, and fine-stranded copper conductors, within the manufacturer's specified ranges
- **Amazon ASIN:** B01M6Y2UEK

The connectors provide convenient, serviceable junctions for internal wiring without requiring permanent soldered splices.

---

## Controls Parts List

The following table preserves the actual drilling measurements used for the Clonker's physical controls.

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
| **Skip Back (red)** | Philmore 30-2289 sub-mini SPST NO momentary pushbutton | 7.14 mm (9/32") — twist ✓ |
| **Play / Pause** | Philmore 30-111 momentary pushbutton | 10 mm (≈25/64") — step ✓ |
| **Skip Forward (red)** | Philmore 30-2289 sub-mini SPST NO momentary pushbutton | 7.14 mm (9/32") — twist ✓ |
| **Room Selector** | uxcell 2P3T, 3-position rotary switch | 10 mm (≈25/64") — step ✓ |
| ↳ Selector knob | uxcell s18102300ux0967, 6 mm D-shaft | — |
| **Power Toggle** | YMJSAN 19 mm metal momentary pushbutton, high head | 20 mm (≈25/32") — step ✓ |
| **CONFIG / RUN (side)** | Dorman Conduct-Tite 84815 racing-style switch | 12.7 mm (1/2") ✓ |
| **SERVICE / DEVICE (internal)** | Philmore 30-10007 SPST toggle switch | No exterior hole required |

The Power Toggle uses a separate red flip-up protective guard.

---

## OLED Mounting Hardware

The OLED is mounted to the aluminum faceplate using four machine screws, matching nuts, and nylon spacers.

| Component | Manufacturer / Part # | Hole / Drill Size |
|---|---|---|
| **OLED mounting screws (×4)** | PLPCI M2.5 × 0.45 × 16 mm, model 9130870 | 2.78 mm (7/64") — twist ✓ |
| ↳ Matching nuts (×4) | PLPCI M2.5 × 0.45, model 9120267 | — |
| ↳ Nylon spacers (×4) | Bivar 907-3MM, 3 mm round nylon | — |

The OLED connector cable passes through a separate hand-cut slot near the upper edge of the display.

---

## Faceplate and Enclosure

### Aluminum Faceplate

The Clonker's control panel is fabricated from 6061-T651 aluminum sheet.

**Material specifications:**

- **Supplier:** PATIKIL
- **Material:** 6061-T651 aluminum alloy
- **Original sheet dimensions:** 152.4 × 203.2 mm (6 × 8 inches)
- **Thickness:** 1/16 inch (0.0625 inch, approximately 1.59 mm)
- **Finish:** Brushed aluminum
- **Original packaging:** Three sheets with protective film
- **Manufacturer part number:** pta240807tt001253
- **Amazon ASIN:** B0DHR7TLNX

The original sheet dimensions should not be confused with the finished faceplate dimensions.

The faceplate serves as the rigid mounting surface for the rotary encoders, navigation buttons, playback controls, room selector, power button, and OLED display.

### Enclosure — Lebakort B115

The Clonker uses a repurposed protective carrying case originally designed for 3D printing pens.

**Manufacturer specifications:**

- **Manufacturer:** Lebakort
- **Model:** B115
- **Original application:** Protective case for 3D printing pens
- **Color:** Black
- **Shell material:** Hard EVA (ethylene-vinyl acetate)
- **Closure:** Zipper
- **Interior:** Soft protective lining and mesh storage pockets
- **Compartments:** Two
- **Listed weight:** 7.4 oz (approximately 210 g)
- **Amazon ASIN:** B0D6K9NT32

The case provides a lightweight protective enclosure for the Pico, internal electronics, wiring, and power system.

Its internal foam has been trimmed to provide clearance for the controls and wiring.

### Faceplate Mounting

- Aluminum faceplate secured to the enclosure using ten perimeter mounting points.
- Fender washers used beneath the plate where clearance permits.
- Smaller washers retained where internal component clearance is limited.
- Nuts secure the plate from inside the enclosure.
- The original protective film was retained during drilling and removed after completion.

---

## Battery and Power Hardware

The Clonker's battery system uses a separate rechargeable power module.

| Component | Manufacturer / Part # | Description |
|---|---|---|
| **Battery power module** | DFRobot 18650 lithium battery shield — exact model to confirm | Two-cell battery holder with USB power connections and regulated outputs |
| **Rechargeable cells** | Exact production battery model to confirm | 18650 lithium-ion cells for portable operation |

The DFRobot module includes USB-C connectivity, a USB-A connection, additional power connections, and a NORMAL / HOLD switch.

Exact electrical ratings, charging behavior, and Pico power connections should be documented only after confirming the specific DFRobot board revision and completing electrical verification.

**Battery safety:** Old, deeply discharged, or damaged lithium-ion cells must not be used as the Clonker's production power source. Battery polarity, cell compatibility, output voltage, and power-path behavior must be verified before connecting the module to the Pico.

---

## Drilling Notes

### Completed Construction

- **Initial pilot holes:** 1.6 mm (1/16") for the main controls.
- **Enlarged pilot holes:** 3.2 mm (1/8") where appropriate.
- **Step drills:** Used for the larger panel openings and metric sizes.
- **Twist drills:** Used for the encoder holes, smaller controls, and OLED mounting holes.
- **Test-fitting:** Each control was checked before accepting its final hole diameter.
- **Deburring:** Sharp edges should be removed, particularly around the OLED connector opening.

### Drill Size Conventions

Hole dimensions are listed in millimeters first, followed by imperial equivalents.

- **Step:** Final opening made using a step drill bit.
- **Twist:** Final opening made using a conventional twist drill bit.
- **✓:** Actual finished hole size, successfully test-fitted.

Where the final hole was enlarged using a twist drill after an initial step-drilled opening, the table identifies the finishing drill.

These measurements document actual construction results rather than relying solely on manufacturer mounting recommendations.

### Important Findings

**Bourns rotary encoders:** Both encoders fit perfectly through 9/32-inch openings. The threaded mounting bushing determines the required hole size, not the smaller rotating shaft.

**YMJSAN metal pushbuttons:** Although advertised as 19 mm pushbuttons, both the Nav Select / OK and Power Toggle required 20 mm mounting holes. The resulting small amount of clearance was acceptable.

**Philmore navigation buttons:** All four navigation buttons fit perfectly in 1/2-inch openings.

**Home and Back buttons:** Both square pushbuttons also fit perfectly in 1/2-inch openings.

**Philmore Play / Pause:** A 10 mm hole provided a perfect fit, eliminating the need for the previously estimated 13/32-inch opening.

**Room selector:** The uxcell 2P3T selector fit perfectly in a 10 mm opening. It uses a 6 mm D-shaped shaft. The knob was reused from an earlier multi-position selector.

**Skip Back / Forward:** Both controls use Philmore 30-2289 red nylon, normally-open momentary pushbuttons. They fit the existing verified 7.14 mm (9/32") openings. The original black Philmore 30-2299 normally-closed switches were replaced after failing during soldering. Both models share the same published 0.265-inch mounting-hole specification.

**OLED mounting:** Four 7/64-inch holes provided a good fit for the M2.5 mounting screws. Minor rotational adjustment was possible by loosening the screws.

**CONFIG / RUN switch:** The Dorman racing-style switch fits through a 1/2-inch hole in the side of the enclosure, despite its square external housing.

**SERVICE / DEVICE switch:** Remains inside the enclosure. No dedicated exterior mounting hole is required.

**Power Toggle:** Uses a guarded momentary pushbutton with a red flip-up protective guard. The guard is a separate component.

---

## Maintenance

Update this document when:

- A physical component is replaced or changed.
- A manufacturer or part number is confirmed.
- Additional mounting hardware is installed.
- The enclosure or faceplate design changes.
- New electronics or internal mounting arrangements are finalized.
- Previously provisional specifications are verified.

Development milestones, implementation status, and test history belong in the project's development documentation rather than this inventory.

The goal is to preserve enough information to identify, repair, reproduce, or rebuild the hardware without reverse-engineering the original machine.

---

*One Monster. One Dumb Queue™.*
