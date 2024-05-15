'''
0.91 cP // y = 0.99x - 6.23
3.06 cP // y = 0.97x - 4.91
9.96 cP // y = 0.97x - 2.78
31.88 cP // y = 0.98x + 3.68
'''

from math import isclose
from decimal import Decimal

def correction_factor(x,viscosity=0.91) -> Decimal:
    '''
    Calculate the correction factor to applied to the programmed volume
    for the viscosity of the sample.
    
    0.91 cP // y = 1.01x + 6.23
    3.06 cP // y = 1.03x + 4.91
    9.96 cP // y = 1.03x + 2.78
    31.88 cP // y = 1.02x -3.68
    
    with x = programmed volume
    '''
    # Start with all floats and then return a Decimal
    x = float(x)
    viscosity = float(viscosity)

    if viscosity is None or x == 0:
        corrected_volume = x
    elif isclose(viscosity,0.91, abs_tol=0.05):
        corrected_volume = 1.01*x + 6.23
    elif isclose(viscosity,3.06):
        corrected_volume = 1.03*x + 4.91
    elif isclose(viscosity,9.96):
        corrected_volume = 1.03*x + 2.78
    elif isclose(viscosity,31.88):
        corrected_volume = 1.02*x - 3.68
    else:
        corrected_volume = x

    return Decimal(round(corrected_volume,3))

def reverse_correction_factor(x, viscosity) -> Decimal:
    """Calculate the original volume based on the given volume x and viscosity."""
    x = float(x)
    viscosity = float(viscosity)
    if viscosity is None or x == 0:
        original_volume = x
    elif isclose(viscosity,0.91):
        original_volume = (x - 6.23)/1.01
    elif isclose(viscosity,3.06):
        original_volume = (x - 4.91)/1.03
    elif isclose(viscosity,9.96):
        original_volume = (x - 2.78)/1.03
    elif isclose(viscosity,31.88):
        original_volume = (x + 3.68)/1.02
    else:
        original_volume = x

    return Decimal(round(original_volume,3))
