
import numpy as np
import pandas as pd

# Define doy mapping function
cum = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]

def doy_from_md(m, d):
    """Compute day of year (1-366) from month and day.
    Jan=1..31, Feb=32..59(28)/60(29), Mar=61..91, ..., Dec=336..366"""
    return cum[m-1] + d

# Test the mapping
tests = [
    (1, 1, 1),    # Jan 1
    (1, 31, 31),  # Jan 31
    (2, 1, 32),   # Feb 1
    (2, 28, 59),  # Feb 28
    (2, 29, 60),  # Feb 29
    (3, 1, 61),   # Mar 1
    (3, 31, 91),  # Mar 31
    (4, 1, 92),   # Apr 1
    (4, 30, 121), # Apr 30
    (5, 1, 122),  # May 1
    (5, 31, 152), # May 31
    (6, 1, 153),  # Jun 1
    (6, 30, 182), # Jun 30
    (7, 1, 183),  # Jul 1
    (7, 31, 213), # Jul 31
    (8, 1, 214),  # Aug 1
    (8, 31, 244), # Aug 31
    (9, 1, 245),  # Sep 1
    (9, 30, 274), # Sep 30
    (10, 1, 275), # Oct 1
    (10, 31, 305),# Oct 31
    (11, 1, 306), # Nov 1
    (11, 30, 335),# Nov 30
    (12, 1, 336), # Dec 1
    (12, 31, 366),# Dec 31
]

for m, d, expected in tests:
    got = doy_from_md(m, d)
    assert got == expected, f"({m},{d}) expected {expected}, got {got}"
print("doy mapping verified!")

# Test inverse
def md_from_doy(doy):
    month_bounds = [(1,1,31),(2,32,60),(3,61,91),(4,92,121),(5,122,152),
                    (6,153,182),(7,183,213),(8,214,244),(9,245,274),
                    (10,275,305),(11,306,335),(12,336,366)]
    for m, lo, hi in month_bounds:
        if lo <= doy <= hi:
            return m, doy - lo + 1
    raise ValueError(f"Invalid doy: {doy}")

for doy in range(1, 367):
    m, d = md_from_doy(doy)
    assert doy_from_md(m, d) == doy
print("inverse mapping verified!")

# Test specific values
print("md_from_doy(59):", md_from_doy(59))
print("md_from_doy(60):", md_from_doy(60))
print("md_from_doy(61):", md_from_doy(61))
