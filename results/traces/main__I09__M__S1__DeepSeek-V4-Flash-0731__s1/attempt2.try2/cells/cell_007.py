
import xarray as xr
import numpy as np
from datetime import date, timedelta
import os

# ====== CONFIG ======
data_dir = '/data/icsa2027_data_20261101T090944Z/s1z'
lat_min, lat_max = 54.81, 56.01
lon_min, lon_max = 19.61, 20.81
target_start = date(2022, 6, 1)
target_end = date(2022, 8, 31)
baseline_start = date(1992, 1, 1)
baseline_end = date(2002, 12, 31)

# ====== Helper: day-of-year mapping ======
# Jan=1..31, Feb=32..60 (Feb29=60), Mar=61...
# Months with days: Jan=31, Feb=29(always in this mapping), Mar=31, Apr=30, May=31, Jun=30,
# Jul=31, Aug=31, Sep=30, Oct=31, Nov=30, Dec=31
# Cumulative: Jan=0, Feb=31, Mar=60, Apr=91, May=121, Jun=152, Jul=182, Aug=213, Sep=244, Oct=274, Nov=305, Dec=335

month_days = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
cum_days = [0]
for md in month_days[:-1]:
    cum_days.append(cum_days[-1] + md)
# cum_days = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]

def date_to_doy(d):
    """Map a date to day of year 1-366 using the spec's mapping."""
    return cum_days[d.month - 1] + d.day

def doy_to_date_in_year(doy, year):
    """Convert day of year to a date in the given year. Returns None if impossible (e.g., doy=60 in non-leap year)."""
    for m in range(12):
        if doy <= cum_days[m] + month_days[m]:
            day = doy - cum_days[m]
            # Check if this is a valid date
            try:
                return date(year, m+1, day)
            except ValueError:
                return None
    return None

# Test
print(f"Jan 1 = {date_to_doy(date(2022,1,1))}")
print(f"Feb 28 = {date_to_doy(date(2022,2,28))}")
print(f"Mar 1 = {date_to_doy(date(2022,3,1))}")
print(f"Dec 31 = {date_to_doy(date(2022,12,31))}")
print(f"Feb 29 2024 = {date_to_doy(date(2024,2,29))}")
print(f"doy 60 in 2023: {doy_to_date_in_year(60, 2023)}")
print(f"doy 60 in 2024: {doy_to_date_in_year(60, 2024)}")
