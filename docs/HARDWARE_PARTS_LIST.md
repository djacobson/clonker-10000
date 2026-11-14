# Battery and Power Hardware

Clonker's portable power system uses a DFRobot DFR0969
module with two rechargeable 18650 lithium-ion cells.

Battery-powered operation, overnight software sleep, and
physical-button wake have been demonstrated successfully.

Permanent enclosure integration and full-discharge runtime
testing remain pending.

## Components

| Component | Manufacturer / Part # | Description |
|---|---|---|
| Battery power module | DFRobot DFR0969 | Dual-18650 charging and 5 V boost module |
| Rechargeable cells | 18650 lithium-ion, exact model to confirm | Two cells for portable operation |
| USB power tester | Color TFT USB Tester, exact model to confirm | Inline voltage and current measurements |
| Pico power cable | USB-A to Micro-USB | Connects DFRobot output to Pico 2 W |
| Charging connector | Panel-mounted USB-C extension | External charging access through enclosure |

## DFRobot 18650 Battery Module

- **Manufacturer:** DFRobot
- **Manufacturer part number:** DFR0969
- **DigiKey part number:** 1738-DFR0969-ND
- **Battery positions:** Two 18650 cells
- **Charging input:** USB-C
- **Regulated output:** USB-A, approximately 5 V
- **Additional connections:** Board-mounted power pads
- **Operating switch:** NORMAL / HOLD
- **Selected Clonker mode:** HOLD
- **Integration status:** Bench-tested; permanent mounting pending

The module powers the Pico through its USB-A output and
the Pico's Micro-USB connector.

A panel-mounted USB-C charging connector has been fitted
to Clonker's enclosure. Final internal connections and
strain relief remain to be verified.

## Initial Battery-Powered Testing — November 12, 2026

The initial tests established that Clonker can operate
independently of a computer or external USB supply.

Observed results included:

- Initial cell voltage of approximately 3.560 V per cell.
- Regulated USB output of approximately 5.12 V.
- Typical idle current around 33–37 mA at the Pico input.
- Successful CircuitPython and Clonker startup.
- Normal OLED and physical-control operation.
- Approximately 10–12 seconds to the READY display.

These were initial functional and electrical observations,
not complete battery-runtime measurements.

## Chapter 9 Software Sleep

Software-managed sleep is operational.

The current default inactivity timeout is 600 seconds
(10 minutes) in RUN mode.

Sleep disables the OLED and Wi-Fi while the CPU continues
polling physical wake controls.

Measured current at the Pico USB input:

| Condition | Approximate current |
|---|---:|
| Awake, idle RUN | 33–35 mA |
| Software sleep | 24 mA |

These values exclude the DFRobot module's conversion losses
and internal consumption. They are not battery-cell currents.

Wake by physical pushbutton triggers a microcontroller
reboot and normal application startup.

## Overnight Battery Endurance — November 13–14, 2026

Clonker completed an approximately 12-hour battery-powered
software-sleep test.

Test conditions:

- Two rechargeable 18650 cells.
- DFRobot in HOLD mode.
- No external charging power.
- No inline USB power meter.
- Development inactivity timeout of 60 seconds.
- OLED and Wi-Fi shutdown during software sleep.

After the overnight period:

- The DFRobot indicated three of four battery LEDs.
- A physical button successfully woke Clonker.
- The Pico rebooted and displayed `CLONKER READY!`.
- One cell measured approximately 3.814 V.

**Result: PASSED.**

This demonstrates overnight power availability and
wake responsiveness, not maximum battery endurance.

## Charging and Power Transitions

The DFRobot exhibited asymmetric power-path behavior.

| Transition | Observed behavior |
|---|---|
| Battery to charger connected | Seamless operation |
| Charger connected to battery | Brief interruption; Pico reboots |
| Charger removed in HOLD | USB tester reboots |
| Charger removed in NORMAL | USB tester reboots |

The charger-removal interruption was independently
reproduced with the Pico disconnected and the USB tester
connected directly to the DFRobot's USB-A output.

Representative no-load output measurements:

| Mode | Charger connected | Battery-only |
|---|---:|---:|
| HOLD | 5.040 V | 5.129 V |
| NORMAL | 4.999 V | 5.121 V |

The exact duration and shape of the interruption have
not been measured.

HOLD remains the intended operating mode.

Charging-input measurements have reached approximately
1.8 A from an external 5 V supply.

A reputable, suitably rated 5 V USB supply is recommended
for continued testing.

## Remaining Validation

- Confirm the final 18650 cell model and specifications.
- Complete permanent mounting and internal wiring.
- Verify the panel-mounted USB-C charging connection.
- Inspect insulation, cell retention, and strain relief.
- Check charging behavior and temperatures after assembly.
- Repeat power-transition tests in the completed enclosure.
- Establish longer-term battery runtime and discharge behavior.
- Investigate hardware sleep when supported by a suitable
  stable CircuitPython release.

**Battery safety:** Do not use old, deeply discharged,
damaged, or mismatched lithium-ion cells. Confirm correct
polarity, compatible cell specifications, appropriate
charging behavior, and protection before permanent
installation.

For detailed experiments, see
[Development History](DEVELOPMENT_HISTORY.md).

For enclosure integration, see
[Hardware Design](HARDWARE_DESIGN.md).
