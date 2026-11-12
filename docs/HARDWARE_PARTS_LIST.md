## Battery and Power Hardware

The Clonker's portable power system uses a DFRobot DFR0969 module with two rechargeable 18650 lithium-ion cells.

Battery-powered operation has been successfully demonstrated on the bench. Permanent enclosure integration and extended runtime validation remain in progress.

| Component | Manufacturer / Part # | Description |
|---|---|---|
| **Battery power module** | DFRobot DFR0969 | Two-cell 18650 battery holder with regulated USB output |
| **Rechargeable cells** | 18650 lithium-ion, exact model to confirm | Two cells installed for portable operation |
| **USB power tester** | Color TFT USB Tester, exact model to confirm | Inline voltage, current, and power monitoring |
| **Power cable** | USB-A to Micro-USB | Connects battery module output to the Pico 2 W |

### DFRobot 18650 Battery Module

- **Manufacturer:** DFRobot
- **Manufacturer part number:** DFR0969
- **DigiKey part number:** 1738-DFR0969-ND
- **Battery positions:** Two 18650 cells
- **USB connections:** USB-C and USB-A
- **Additional power connections:** Board-mounted connection pads
- **NORMAL / HOLD switch:** HOLD selected for battery-powered Clonker testing
- **Power output:** Approximately 5.12 V measured during operation
- **Clonker integration:** Bench-tested successfully; permanent mounting pending

The battery module powers the Pico through its USB-A output and the Pico's Micro-USB connector.

The inline USB tester measures electrical consumption without requiring changes to the Clonker firmware.

### Initial Battery-Powered Testing — November 12, 2026

The initial tests established that the Clonker can operate independently of a computer or external USB power supply.

**Observed measurements:**

- Individual 18650 cell voltage before testing: approximately 3.560 V each.
- Regulated USB output during operation: approximately 5.12 V.
- Typical observed idle current: approximately 33–37 mA.
- Approximate idle power consumption: 0.17–0.19 W.

**Functional observations:**

- CircuitPython and the Clonker application boot successfully from battery power.
- The OLED displays the startup READY message approximately 10–12 seconds after power-on.
- The startup message clears automatically.
- Physical rotary controls and OLED feedback operate normally.
- The Clonker remains responsive during initial battery-powered operation.
- The USB tester displays changes in current consumption associated with physical controls and browser activity.

The current measurements represent observed USB input consumption under the tested conditions. They are not yet a complete characterization of peak consumption, battery efficiency, or expected runtime.

Extended battery endurance testing is underway.

### Remaining Validation

- Complete extended battery runtime testing.
- Characterize battery discharge and low-voltage behavior.
- Verify charging and power-path behavior.
- Confirm the production cell model and specifications.
- Finalize battery module placement and internal cable routing.
- Evaluate future sleep and wake behavior.

**Battery safety:** Old, deeply discharged, or damaged lithium-ion cells must not be used. Confirm correct cell polarity, compatibility, charging requirements, and protection behavior before permanent installation.
