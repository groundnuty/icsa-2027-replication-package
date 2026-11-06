
import numpy as np
from datetime import date, timedelta

def doy_from_date(d):
    """Map a date to day of year 1-366."""
    cum = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum[d.month - 1] + d.day

# Verify
print(f"Jan 1: {doy_from_date(date(1992,1,1))}")
print(f"Feb 28: {doy_from_date(date(1992,2,28))}")
print(f"Feb 29: {doy_from_date(date(1992,2,29))}")
print(f"Mar 1: {doy_from_date(date(1992,3,1))}")
print(f"Dec 31: {doy_from_date(date(1992,12,31))}")
print(f"Feb 28 (non-leap): {doy_from_date(date(1993,2,28))}")
print(f"Mar 1 (non-leap): {doy_from_date(date(1993,3,1))}")
