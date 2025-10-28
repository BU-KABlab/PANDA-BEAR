# Construction | [Installation](installation.md) | [End User Manual](end_user_manual.md) | [Dev User Manual](developer_manual.md) | [Contents](user_manual.md) <!-- omit from toc -->

## Table of Contents <!-- omit from toc -->
- [Parts](#parts)
- [Constructing the Process Automation Widget (PAW)](#constructing-the-process-automation-widget-paw)
  - [PAWduino (Arduino)](#pawduino-arduino)
- [Placing Objects on the Deck](#placing-objects-on-the-deck)
  - [Vials](#vials)
  - [Wellplates](#wellplates)
- [Mapping the Location of Objects and Calibrating Offsets](#mapping-the-location-of-objects-and-calibrating-offsets)



# Parts

For purchased parts please see [Bill of Materials (BOM)](documents/bom.md) for a parts list. It includes estimated prices and possible vendors to obtain the parts from (biased towards United States).

For 3D-Printed parts please see [3D files](3D-prints)

# Constructing the Process Automation Widget (PAW)

The PANDA's PAW is what physically performs all of the physical actions the SDL offers. It is also the location of most of the system's experiment-related instrumentation (i.e., supporting electrodes, camera, electromagnet, lighting for contact angle and in process images, pipette, etc.).

3D Printed Parts:

- [ ] Body
- [ ] Lightring
- [ ] Electrode mount
  - [ ] Base
  - [ ] Front
  - [ ] Clips
- [ ] Pipette mount
- [ ] Electromagnet mount

Purchased Parts:
- [ ] Arduino Uno R3
- [ ] Adafruit Dev Shield
- [ ] Adafruit Servo Shield
- [ ] Adafruit Neopixel Ring (24 lights)
- [ ] Adafruit Neopixel Dots x2 or Red LEDs x2
- [ ] Wires
- [ ] FLIR Grasshopper3
- [ ] Edmunds Optics Telcentric Lense
- [ ] 5V Electromagnet
- [ ] 5V DC Power Supply
- [ ] IRLZ44 MOSFET
- [ ] 1k Ohm Resistor
- [ ] 200 Ohm Resistor
- [ ] 3k Ohm Resistor 
- [ ] Flyback Diode

## PAWduino (Arduino)

The PAWduino is a microcontroller that allows us to simply our connection to the PAW to just two USB cables and the potentiostat leads. Refer to the diagram below while wiring the dev shield (Note: The motor is representing the electromagnet):

Using Red LEDS


Using Neopixel Dots




# Placing Objects on the Deck

## Vials

Use the vial holder found in 3d-prints. Vials should be positioned along the Y-axis with the first vial having the lowest y-value. 

## Wellplates

When using the main menu to change the wellplate, you will be asked for the wellplate's a1 (XYZ) location and the orientation of the wellplate. Refer to the following figure to determine your wellplate orientation:

![Wellplate Orientations](images/wellplate_orientations.png)

# Mapping the Location of Objects and Calibrating Offsets

From the main menu there is the option to run `mill_calibration_and_positioning.py`. If the system is in testing mode, the mill will not move, but the program will print the xyz movements that it would have sent so that you may manually move the mill yourself. However, any changes you make WILL be saved to the active database.
