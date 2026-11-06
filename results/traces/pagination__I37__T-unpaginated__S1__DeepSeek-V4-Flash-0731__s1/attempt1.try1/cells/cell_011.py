
import fsspec
import xarray as xr
import numpy as np
import datetime
import time

fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'

# Day of year mapping
def doy_from_date(date):
    month_days = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return month_days[date.month-1] + date.day

# Build the list of baseline dates
baseline_start = datetime.date(1991, 12, 27)
baseline_end = datetime.date(2003, 1, 5)

baseline_dates = []
d = baseline_start
while d <= baseline_end:
    baseline_dates.append(d)
    d += datetime.timedelta(days=1)

print(f"Number of baseline dates: {len(baseline_dates)}")

# For each day of year d (1-366, excluding 60), determine pool dates
# Pool for doy d = dates within ±5 calendar days of any baseline date (1992-2002) with doy d

# First, find dates in 1992-2002 with each doy
doy_to_center_dates = {i: [] for i in range(1, 367)}
for date in baseline_dates:
    if 1992 <= date.year <= 2002:
        d = doy_from_date(date)
        doy_to_center_dates[d].append(date)

# For each doy, expand to ±5 days
doy_to_pool_dates = {i: set() for i in range(1, 367)}
for d in range(1, 367):
    if d == 60:
        continue
    for center_date in doy_to_center_dates[d]:
        for offset in range(-5, 6):
            doy_to_pool_dates[d].add(center_date + datetime.timedelta(days=offset))

# Check: all pool dates should be within our extended baseline
all_pool_dates = set()
for d in range(1, 367):
    if d != 60:
        all_pool_dates |= doy_to_pool_dates[d]
        
baseline_date_set = set(baseline_dates)
missing = all_pool_dates - baseline_date_set
print(f"Pool dates not in baseline range: {len(missing)}")
if missing:
    print("Missing:", sorted(missing)[:10])

# Also check if there are baseline dates not used in any pool
unused = baseline_date_set - all_pool_dates
print(f"Baseline dates not used in any pool: {len(unused)}")
if unused:
    print("Unused:", sorted(unused)[:10])
