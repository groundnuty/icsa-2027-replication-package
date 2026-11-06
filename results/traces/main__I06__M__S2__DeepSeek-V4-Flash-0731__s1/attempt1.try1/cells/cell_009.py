
import numpy as np
import pandas as pd

def doy_from_md(month, day):
    """Map month/day to day of year 1-366."""
    days_in_month = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    doy = sum(days_in_month[:month-1]) + day
    return doy

# Verify
print("Jan 1:", doy_from_md(1,1))
print("Feb 28:", doy_from_md(2,28))
print("Feb 29:", doy_from_md(2,29))
print("Mar 1:", doy_from_md(3,1))
print("Mar 31:", doy_from_md(3,31))
print("Dec 31:", doy_from_md(12,31))
