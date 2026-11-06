# THE CLONKER 10000 — Hardware Parts List

> Less sleek. More CLONK.

## Purpose

This document identifies the physical controls and mounting hardware used in THE CLONKER 10000.

It serves as a reference for component identification, replacement parts, and the actual drill sizes used during construction of the aluminum faceplate and enclosure.

For GPIO assignments, wiring, and control behavior, see [Hardware Controls](HARDWARE_CONTROLS.md).

## Controls Parts List

All listed exterior mounting holes have been drilled and successfully test-fitted.

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
| **Power Toggle** | YMJSAN 19 mm metal momentary pushbutton, high head | 20 mm (≈25/32") — step ✓ |
| **CONFIG / RUN (side)** | Dorman Conduct-Tite 84815 racing-style switch | 12.7 mm (1/2") ✓ |
| **SERVICE / DEVICE (internal)** | Philmore 30-10007 SPST toggle switch | No exterior hole required |

## OLED Mounting Hardware

The OLED is mounted to the aluminum faceplate using four machine screws, matching nuts, and nylon spacers.

| Component | Manufacturer / Part # | Hole / Drill Size |
|---|---|---|
| **OLED mounting screws (×4)** | PLPCI M2.5 × 0.45 × 16 mm, model 9130870 | 2.78 mm (7/64") — twist ✓ |
| ↳ Matching nuts (×4) | PLPCI M2.5 × 0.45, model 9120267 | — |
| ↳ Nylon spacers (×4) | Bivar 907-3MM, 3 mm round nylon | — |

The OLED connector cable passes through a separate hand-cut slot near the upper edge of the display.

## Faceplate and Enclosure

**Faceplate material:**

- Manufacturer: PATIKIL
- Material: 6061-T651 aluminum
- Dimensions: 152.4 × 203.2 mm (6 × 8 inches)
- Thickness: Approximately 1.5 mm (1/16 inch)
- Finish: Brushed aluminum
- Manufacturer part: pta240807tt001253
- Amazon ASIN: B0DHR7TLNX

**Mounting arrangement:**

- Aluminum faceplate secured to the enclosure using ten perimeter mounting points.
- Fender washers used beneath the plate where clearance permits.
- Smaller washers retained where internal component clearance is limited.
- Nuts secure the plate from inside the enclosure.
- The enclosure's internal foam was trimmed to provide clearance for the controls and wiring.

The original protective film was retained during drilling and removed after completion.

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

These measurements document the actual construction results rather than relying solely on manufacturer mounting recommendations.

### Important Findings

**Bourns rotary encoders:** Both encoders fit perfectly through 9/32-inch openings. The threaded mounting bushing determines the required hole size, not the smaller rotating shaft.

**YMJSAN metal pushbuttons:** Although advertised as 19 mm pushbuttons, both the Nav Select / OK and Power Toggle required 20 mm mounting holes. The resulting small amount of clearance was acceptable.

**Philmore navigation buttons:** All four navigation buttons fit perfectly in 1/2-inch openings.

**Home and Back buttons:** Both square pushbuttons also fit perfectly in 1/2-inch openings.

**Philmore Play / Pause:** A 10 mm hole provided a perfect fit, eliminating the need for the previously estimated 13/32-inch opening.

**Room selector:** The uxcell 2P3T selector fit perfectly in a 10 mm opening. It uses a 6 mm D-shaped shaft. The knob was reused from an earlier multi-position selector.

**Skip Back / Forward:** Both smaller pushbuttons required 9/32-inch openings rather than the initially attempted 1/4-inch holes.

**OLED mounting:** Four 7/64-inch holes provided a good fit for the M2.5 mounting screws. Minor rotational adjustment was possible by loosening the screws.

**CONFIG / RUN switch:** The Dorman racing-style switch fits through a 1/2-inch hole in the side of the enclosure, despite its square external housing.

**SERVICE / DEVICE switch:** Remains inside the enclosure. No dedicated exterior mounting hole is required.

**Power Toggle:** Uses a guarded momentary pushbutton with a red flip-up protective guard. The guard is a separate component.

## Construction Status

As of November 5, 2026:

- All 14 faceplate control holes completed and verified.
- All four OLED mounting holes completed and verified.
- Side-mounted CONFIG / RUN switch hole completed and verified.
- Aluminum faceplate installed on the enclosure.
- All front-panel controls mechanically mounted.
- OLED mechanically mounted.
- Raspberry Pi Pico 2 W and associated electronics moved inside the enclosure.
- Internal wiring, soldering, strain relief, and final electrical integration remain in progress.

**Total: 19 completed and verified control/display mounting holes.**

The faceplate drilling phase is complete.

## Maintenance

Update this document when:

- A physical control is replaced or changed.
- A manufacturer or part number is confirmed.
- Additional mounting hardware is installed.
- The enclosure or faceplate design changes.
- New electronics or internal mounting arrangements are finalized.

The goal is to preserve enough information to repair, reproduce, or rebuild the hardware without having to reverse-engineer the original build.

---

*One Monster. One Dumb Queue™.*
