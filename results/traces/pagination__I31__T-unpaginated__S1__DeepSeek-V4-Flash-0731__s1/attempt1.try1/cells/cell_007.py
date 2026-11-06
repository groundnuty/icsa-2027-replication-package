
import fsspec
import xarray as xr
import numpy as np
import datetime as dt
import os

fs = fsspec.filesystem('onedata')
base_path = 'icsa2027_data_20261101T090944Z/s1z'

# Region indices (computed earlier)
lat_start, lat_end = 260, 319
lon_start, lon_end = 485, 544
n_lat = 60
n_lon = 60

# Day of year mapping (month, day) -> doy (1-366)
month_offsets = {1: 0, 2: 31, 3: 60, 4: 91, 5: 121, 6: 152, 7: 182, 8: 213, 9: 244, 10: 274, 11: 305, 12: 335}

def date_to_doy(y, m, d):
    return month_offsets[m] + d

# Test some values
assert date_to_doy(1992, 1, 1) == 1
assert date_to_doy(1992, 2, 28) == 59
assert date_to_doy(1992, 2, 29) == 60
assert date_to_doy(1992, 3, 1) == 61
assert date_to_doy(1992, 12, 31) == 366
print("doy mapping OK")

# Generate all dates in the baseline + windows range
baseline_start = dt.date(1991, 12, 27)
baseline_end = dt.date(2003, 1, 5)

dates_baseline = []
d = baseline_start
while d <= baseline_end:
    dates_baseline.append(d)
    d += dt.timedelta(days=1)
print(f"Baseline dates: {len(dates_baseline)}, {dates_baseline[0]} to {dates_baseline[-1]}")

# Generate all target dates
target_start = dt.date(2017, 6, 1)
target_end = dt.date(2017, 8, 31)
dates_target = []
d = target_start
while d <= target_end:
    dates_target.append(d)
    d += dt.timedelta(days=1)
print(f"Target dates: {len(dates_target)}, {dates_target[0]} to {dates_target[-1]}")
