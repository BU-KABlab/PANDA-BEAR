**Substrate fabrication**
Settings may vary based on your setup, we are targeting 300 nm ITO thickness deposited with an approximate wattage between 120 - 130 W using DC sputtering for 15 minutes.

Using an Electron Beam Evaporator (Angstrom Engineering EVOVAC), deposit ITO using Direct Current sputtering with the following profile:
  Ramp 1 power: 0%
  Ramp 1 time: 0 sec
  Soak 1 time: 0 sec
  Ramp 2 power: 27%
  Ramp 2 time: 500 sec
  Soak 2 time: 100 sec
  Shutter Acc. 20.0%
  Shutter Wait: 180 sec
  Shutter Hold: 3 sec
  *Final Thickness: 0.000 kA
  *Rate: 27.00 A/s
  *Thick End Pt: 0.000 kA
  Time End Pt: 900 sec
  *P Term: 75
  *I Term: 5.0
  *D Term: 0.00
  Ctrl Acc: 30%
  Max Power: 30.00%
  Slew Rate: 3%/sec
  Feed Power: 0.00
  Feed Ramp: 300 sec
  Feed Time: 0 sec
  Idle Power: 0.00%
  Idle Ramp: 0 sec

*Settings are related to electron beam evaporation and not relevant for DC sputtering. 
HOWEVER, **the rate must be set as the same value as your ramp power %** even though the units don't match or the main process will default to 0%, rapidly cool, and possibly crack your target.

_After deposition, heat the substrate on a hotplate at 400°F for 5-10 minutes. It should change color from pink to yellow. Verify this step worked by checking resistivity (it should be < 600 ohms)._


**Gasket fabrication**
Laser cut mylar with adhesive backing using this template: [documentation/3D-prints/PDMS adhesive lasercut - 40 Wells d10mm.dxf](https://github.com/BU-KABlab/PANDA-BEAR/blob/e12f17b71f0ca1619ce1f2e5ce441cd34fc1a6a5/documentation/3D-prints/PDMS%20adhesive%20lasercut%20-%2040%20Wells%20d10mm.dxf)

3D print this mold using 0.2 mm layer height: [documentation/3D-prints/PDMS Mold - 40 Wells d10mm.step](https://github.com/BU-KABlab/PANDA-BEAR/blob/e12f17b71f0ca1619ce1f2e5ce441cd34fc1a6a5/documentation/3D-prints/PDMS%20Mold%20-%2040%20Wells%20d10mm.step)

3D print these tools to help with gasket removal from the mold: [documentation/3D-prints/MoldTools](https://github.com/BU-KABlab/PANDA-BEAR/tree/d4180eaa3575ac604cb0f5268dbaa70384e03784/documentation/3D-prints/MoldTools)

Procedure steps:
1. Remove sheet to expose adhesive
2. Place in 3D printed mold
3. Ensure it fully adheres, press down around edges with a rigid tool to help
4. Prepare ~35 mL of PDMS in a 10:1 ratio (base:crosslinker)
5. Degass to remove bubbles
6. Slowly pour PDMS into mold, starting from one corner and moving across the rows and columns in a zigzag to ensure PDMS spreads evenly and doesn't overflow the mold
7. Place a cover over the mold to protect it from dust, but make sure it is still exposed to air
8. Allow to cure at room temperature for a minumum of 48 hours. If the PDMS is still tacky, it is not fully cured.

Removal from mold:
1. Remove from mold by cutting away the tabs around the outside of the gasket with a clean razor blade
2. Fill the reservoirs (where the tabs were) 50% full with IPA (this helps with gasket removal)
3. Use the 3D printed well release tool by pressing gently on the top of the mold around each of the "wells" (this helps unstick the well side walls from the mold)
4. Use the 3D printed pry tools to carefully pry the gasket up, starting from the outside and working your way in
    You can go back and forth with all the tools provided, print multiples of the tools and wedge the long pry tool under the mold in multiple locations, and find a strategy that works best for you
5. Once the gasket is removed, (if needed) clean up the edges with a razor blade using chopping motions (don't using sawing motions, this tears the PDMS)
6. Rinse the gasket with IPA and allow to dry


**Gasket mounting**
1. Prepare ~1-2 mL of PDMS in a 10:1 ratio (base:crosslinker) - this will be your "PDMS glue"
2. Using a small silicone spatula, q-tips, paint brush, your tool of choice carefully spread a thin layer of PDMS glue on the side of the gasket that touched the mylar sheet in the bottom of the mold
3. Place the gasket (uncured PDMS side down) on the substrate, using the alignment tool, by aligning two corners on one of the short sides and slowly lowering the PDMS gasket from one short side to the other
    DO NOT ADJUST THE GASKET or PDMS will "leak" into the wells.
    - If you notice any bubbles between the gasket and substrate, you need to apply more PDMS glue to the gasket (this can be done VERY CAREFULLY by removing the gasket and repeating the mounting steps)
    - If you notice PDMS in the well space, you applied too much PDMS glue to the gasket
4. Allow to cure for a minimum of 48 hours, 1 week is ideal to prevent leakage between wells.
5. Verify wells do not leak by using IPA, ethanol, or water do NOT use any other solvent for this (other solvents can hinder remounting the gasket if that's needed).
6. If wells leak, remove gasket and repeat mounting steps. Ensure gasket and substrate are completely dry before doing this.


_Use any prepared substrates with attached gaskets within 2 months. 
Delamination has been noted in gaskets older than this._



