# THE CLONKER 10000 — Hardware Parts List

> Less sleek. More CLONK.

## Purpose

This document identifies the physical controls and mounting hardware used in THE CLONKER 10000.

It serves as a reference for component identification, replacement parts, and drilling the aluminum faceplate or enclosure.

For GPIO assignments, wiring, and control behavior, see [Hardware Controls](HARDWARE_CONTROLS.md).

## Controls Parts List

| Control | Manufacturer / Part # | Hole / Drill Size |
|---|---|---|
| **Volume / Mute** | Bourns PEC11R-4215F-S0024 rotary encoder | 7 mm (≈9/32") — step |
| ↳ Volume knob | Kilo OEJNI-90-3-5 | — |
| **Custom Actions / Run** | Bourns PEC11R-4215F-S0024 rotary encoder | 7 mm (≈9/32") — step |
| ↳ Action knob | Kilo OEJL-63-4-7 | — |
| **Home (red)** | E-Switch PS1023, red square pushbutton | Approx. 12 mm (≈15/32") — step |
| **Back (black)** | E-Switch PS1023ABLK, black square pushbutton | Approx. 12 mm (≈15/32") — step |
| **Nav Up** | Philmore 30-146 momentary pushbutton | 12.5 mm (≈1/2") — step |
| **Nav Down** | Philmore 30-146 momentary pushbutton | 12.5 mm (≈1/2") — step |
| **Nav Left** | Philmore 30-146 momentary pushbutton | 12.5 mm (≈1/2") — step |
| **Nav Right** | Philmore 30-146 momentary pushbutton | 12.5 mm (≈1/2") — step |
| **Nav Select / OK** | YMJSAN 19 mm metal momentary pushbutton, high head | 19 mm (≈3/4") — step |
| **Skip Back** | Philmore 30-2299 sub-mini momentary pushbutton | 6.35 mm (1/4") — twist |
| **Play / Pause** | Philmore 30-111 momentary pushbutton | 10.3 mm (13/32") — step |
| **Skip Forward** | Philmore 30-2299 sub-mini momentary pushbutton | 6.35 mm (1/4") — twist |
| **Room Selector** | uxcell 2P3T, 3-position rotary switch | 10 mm (≈3/8") — step |
| ↳ Selector knob | uxcell s18102300ux0967, 6 mm D-shaft | — |
| **Power Toggle** | YMJSAN 19 mm metal momentary pushbutton, high head | 19 mm (≈3/4") — step |
| **CONFIG / RUN (side)** | Dorman Conduct-Tite 84815 racing-style switch | 12.7 mm (1/2") — step |
| **SERVICE / DEVICE (internal)** | Philmore 30-10007 SPST toggle switch | 6.35 mm (1/4") — no hole planned |

## OLED Mounting Hardware

The OLED is mounted to the aluminum faceplate using four machine screws, matching nuts, and nylon spacers.

| Component | Manufacturer / Part # | Hole / Drill Size |
|---|---|---|
| **OLED mounting screws (×4)** | PLPCI M2.5 × 0.45 × 16 mm, model 9130870 | 2.7 mm (≈7/64") — twist |
| ↳ Matching nuts (×4) | PLPCI M2.5 × 0.45, model 9120267 | — |
| ↳ Nylon spacers (×4) | Bivar 907-3MM, 3 mm round nylon | — |

## Drilling Notes

- **Faceplate:** Aluminum.
- **Pilot holes:** 1.6 mm (1/16") initially drilled for the main controls.
- **Enlarged pilot holes:** 3.2 mm (1/8") where appropriate before final drilling.
- **Step:** Use a step drill bit, particularly for larger panel holes.
- **Twist:** Use a conventional twist drill bit.
- **OLED:** Drill the four small mounting holes separately, using careful alignment.
- **Test-fit:** Check each component before enlarging a hole further.
- **Deburring:** Remove sharp edges after drilling.

### Drill Size Conventions

Hole dimensions are listed in millimeters first, with approximate or exact imperial equivalents in parentheses.

The sizes in this document represent manufacturer recommendations or preliminary mounting estimates, **not necessarily the final drill sizes used**.

Actual drill sizes should be recorded after the components have been fitted successfully.

### Special Mounting Considerations

**Rotary encoders:** The panel hole must accommodate the threaded mounting bushing, not merely the smaller rotating shaft.

**Room selector:** The selector uses a 10 mm threaded mounting bushing and a 6 mm D-shaped shaft. The knob was reused from an earlier multi-position selector.

**CONFIG / RUN switch:** The Dorman racing-style switch mounts through a circular hole in the side of the enclosure, despite its square external housing.

**SERVICE / DEVICE switch:** Remains inside the enclosure. No dedicated exterior mounting hole is planned.

**Power Toggle:** Uses a guarded momentary pushbutton. The protective guard is a separate component.

## Maintenance

Update this document when:

- A physical control is replaced or changed.
- A manufacturer or part number is confirmed.
- An actual mounting-hole diameter is established.
- Additional mounting hardware is installed.
- The enclosure or faceplate design changes.

The goal is to preserve enough information to repair, reproduce, or rebuild the hardware without having to reverse-engineer the original build.

---

*One Monster. One Dumb Queue™.*
