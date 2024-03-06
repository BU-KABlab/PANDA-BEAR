# PANDA-BEAR Identifiction NUMBER (PIN)

Modeled on Vehicle Identification Number (VIN) the PIN identifies the hardware version of the PANDA-BEAR system
This is critical for experiment repeatability as an experiment run on different hardware may yield different results

Example PIN:
2 001 001 004 001 001 014 000 000

## Considerations

- The first category will not have leading 0s
- If any category grows beyond the initial 3-digits, all previous entries must be expanded with a leading 0.
- When adding a new category all previous entries must be backfilled with 0s
- All codes are numberic inorder to result in an integer value

## Categories

Mill | Pump | Potentiostat | Reference Electrode | Working Electrode | Wells | Pipette Adapter | Optics | Scale

mill 1 = Prover 3018 \
mill 2 = Prover 4030 Pro

pump 001 = New Era A-1000 syringe pump with 1ml, 4.699 diameter syringe

potentiostat 001 = Gamry

reference electrode 001 = silver chloride solution inside of glass tube\
reference electrode 002 = glass tube with reference elctrode fixed with PDMS\
reference electrode 003 = glass tube with reference elctrode fixed with epoxy\
reference electrode 004 = carbon-glass and silver

working electrode 001 = gold\
working electrode 002 = ITO

wells 001 = 96 silicon 9mm x 9mm square wells
wells 002 = 96 pdms circular wells

pipette adapter 001 = barbed fitting\
pipette adapter 002 = male leur-lock part of adapter\
pipette adapter 003 = female leur-lock part of adapter\
pipette adapter 004 = cut off end\
pipette adapter 005 = remodeled short adapter with female leur-lock

optics 000 = no optics

scale 000 = no scale
scale 001 = wellplate ontop of scale
scale 002 = scale below decking with access port
