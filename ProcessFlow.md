# Input parameters
## Size of well plate
## Stock solutions
* Number of solutions
* Ranges of concentrations to explore
## Deposition parameters
* Deposition potential
* Deposition time

# PANDA Operation
## Experiment A1
Home the mill

* Pipette - Solution #N
  - Moves pipette to #N stock solution vial
  - Withdraws programmed volume
  - Moves to purge vial
  - Dispenses purge amount
  - Moves to well A1
  - Dispenses programmed amount
  - Moves to purge vial
  - Dispenses purge amount
  
* Electrode - Deposition
  - Moves electrode to well A1
  - Perform Gamry script for experiment - chronoamperometry
  
* Pipette - Remove deposition solution
  - Moves pipette to well A1
  - Withdraws total volume from well
  - Moves to purge vial
  - Dispenses total volume
  
* Rinse the well x3
  - 

* Pipette - Dimethylferrocene solution
  - Moves pipette to DMF stock solution vial
  - Withdraws programmed volume
  - Moves to purge vial
  - Dispenses purge amount
  - Moves to well A1
  - Dispenses programmed amount
  - Moves to purge vial
  - Dispenses purge amount

* Electrode - Cyclic voltammetry "characterization"
  - Moves electrode to well A1
  - Perform Gamry script for experiment - cyclic voltammetry

* Pipette - Remove DMF solution
  - Moves pipette to well A1
  - Withdraws total volume from well
  - Moves to purge vial
  - Dispenses total volume

* Rinse the well x3
  - 

## Experiment A2
* Repeat of previous
...
## Experiment N#
* Repeat of previous
