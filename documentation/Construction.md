# Construction Guide

Detailed instructions for constructing the physical PANDA system components.

**Navigation**: [Home](00-Home.md) | [Build Guide](Build-Guide.md) | Construction Guide | [Arduino Wiring](Arduino-Wiring.md)

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
- [ ] Light ring mount
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

The PAWduino is a microcontroller that allows us to simply our connection to the PAW. Refer to the diagrams below while wiring the dev shield:

![PipetteControl.png](https://github.com/BU-KABlab/PANDA-BEAR/blob/b35834325b4b87da402321c42396ac70db04feb7/documentation/images/PipetteControl.png)
Circuit diagram showing the OT2 Pipette control with the Arduino.

![ArduinoCircuitDiagram.png](https://github.com/BU-KABlab/PANDA-BEAR/blob/4b215939d686a022e53818ca3fa3d375d60cca25/documentation/images/ArduinoCircuitDiagram.png)
Circuit diagram showing Arduino control of the other modules.



# Placing Objects on the Deck

## Vials

Use the [vial holder](https://github.com/BU-KABlab/PANDA-BEAR/blob/e2dda7a1acba4eb3918cbcc31763bea3238d3619/documentation/3D-prints/DeckAccessories/9VialHolder20mL_TightFit.step) found in 3D-prints. You will also need two of the ["pill" models](https://github.com/BU-KABlab/PANDA-BEAR/blob/e2dda7a1acba4eb3918cbcc31763bea3238d3619/documentation/3D-prints/DeckAccessories/9VialHolder20mL_TightFit%20-%20Pill.step) to place it on the deck. Vials should be positioned along the Y-axis with the first vial having the lowest y-value. 

## Wellplates

When using the main menu to change the wellplate, you will be asked for the wellplate's a1 (XYZ) location and the orientation of the wellplate. Refer to the following figure to determine your wellplate orientation:

![Wellplate Orientations](images/wellplate_orientations.png)


For fabrication of the wellplates, please see the [relevant SOP](https://github.com/BU-KABlab/PANDA-BEAR/blob/e2dda7a1acba4eb3918cbcc31763bea3238d3619/documentation/sops/wellplate_and_gasket_SOP_v1.md).


For the wellplate holder on the deck, use the following models found in 3D-prints.
- [Top](https://github.com/BU-KABlab/PANDA-BEAR/blob/e2dda7a1acba4eb3918cbcc31763bea3238d3619/documentation/3D-prints/DeckAccessories/SlideHolder_Top%20-%20holder%20top.step)
- [Top insert](https://github.com/BU-KABlab/PANDA-BEAR/blob/e2dda7a1acba4eb3918cbcc31763bea3238d3619/documentation/3D-prints/DeckAccessories/SlideHolder_Top%20-%20holder%20top%20insert.step)
- [Base](https://github.com/BU-KABlab/PANDA-BEAR/blob/e2dda7a1acba4eb3918cbcc31763bea3238d3619/documentation/3D-prints/DeckAccessories/SlideHolder_Bottom%20-%20holder%20base.step)
- [Base insert](https://github.com/BU-KABlab/PANDA-BEAR/blob/e2dda7a1acba4eb3918cbcc31763bea3238d3619/documentation/3D-prints/DeckAccessories/SlideHolder_Bottom%20-%20holder%20base%20insert.step)
- [Cover](https://github.com/BU-KABlab/PANDA-BEAR/blob/77a0dd6fa034267e48bfd818bc86c0d0ee037f51/documentation/3D-prints/DeckAccessories/SlideHolder%20-%20Cover.step)
- [Pill Slider x 2](https://github.com/BU-KABlab/PANDA-BEAR/blob/77a0dd6fa034267e48bfd818bc86c0d0ee037f51/documentation/3D-prints/DeckAccessories/HoldDownAttachmentPin%20-%20Pill_Slider.step)
- [Reverse Pill Slider x 2](https://github.com/BU-KABlab/PANDA-BEAR/blob/77a0dd6fa034267e48bfd818bc86c0d0ee037f51/documentation/3D-prints/DeckAccessories/Reverse_HoldDownAttachmentPin%20-%20ReversePill_Slider.step)
- [Retaining pin x 2](https://github.com/BU-KABlab/PANDA-BEAR/blob/77a0dd6fa034267e48bfd818bc86c0d0ee037f51/documentation/3D-prints/DeckAccessories/HoldDownAttachmentPin%20-%20PillRetainingPin.step)

_**You will need to orient the prints a specific way and include programmed pauses to use the magnetic securing mechanisms in the holder.**_


## Wellplate Holder Assembly

For assembly of the wellplate holder, you will need the following:

### 🔩 Magnets
 *You can stack magnets to get the right dimensions. Ensure they are **strong magnets** that work through 3D prints.*

#### Base Insert
- (2×) Round — **3 mm diameter × 3 mm height**

#### Base
- (2×) **2 mm × 10 mm × 5 mm**  
- (4×) Round — **5 mm diameter × 3 mm height**

#### Top
- (4×) **4 mm × 10 mm × 5 mm**  
- (2×) Round — **6 mm diameter × 2 mm height**

#### Top Insert
- (2×) Round — **6 mm diameter × 2 mm height**

#### Cover
- (4×) **2 mm × 10 mm × 5 mm**



### Pogo Pins
- (4×) **4.5 mm total height**  
- **2 mm diameter**  
- **1.5 mm barrel diameter**



### 🧲 Magnet Connectors
- [Adafruit Magnet Connectors – Product #5358](https://www.adafruit.com/product/5358)


---

# Mapping the Location of Objects and Calibrating Offsets

From the main menu there is the option to run `mill_calibration_and_positioning.py`. If the system is in testing mode, the mill will not move, but the program will print the xyz movements that it would have sent so that you may manually move the mill yourself. However, any changes you make WILL be saved to the active database.
