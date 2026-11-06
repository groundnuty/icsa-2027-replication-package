
import numpy as np
import pandas as pd
from datetime import date, timedelta

# Load saved data
baseline_sst = np.load('/work/baseline_sst.npy')  # (4028, 60, 60)
target_sst = np.load('/work/target_sst.npy')  # (92, 60, 60)
lat_vals = np.load('/work/lat_vals.npy')
lon_vals = np.load('/work/lon_vals.npy')

# Reload time data
import xarray as xr
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
time_vals = ds.time.values
baseline_idx = np.where((time_vals >= np.datetime64('1991-12-27')) & (time_vals <= np.datetime64('2003-01-05')))[0]
target_idx = np.where((time_vals >= np.datetime64('2021-06-01')) & (time_vals <= np.datetime64('2021-08-31')))[0]
baseline_time = time_vals[baseline_idx]
target_time = time_vals[target_idx]
baseline_dates = [pd.Timestamp(t).date() for t in baseline_time]
target_dates = [pd.Timestamp(t).date() for t in target_time]

# Day of year mapping (always Feb=29)
def day_of_year_366(d):
    m, day = d.month, d.day
    days_in_month = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return sum(days_in_month[:m-1]) + day

# Build mapping from date to index in baseline_sst
baseline_date_to_idx = {d: i for i, d in enumerate(baseline_dates)}

# Identify sea cells
sea_mask = np.all(~np.isnan(target_sst), axis=0)  # (60, 60)
print(f"Sea cells: {np.sum(sea_mask)}")

# Get month/day for each day-of-year
days_in_month = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
month_day_for_doy = {}
for m in range(12):
    for day in range(1, days_in_month[m] + 1):
        doy = sum(days_in_month[:m]) + day
        if doy not in month_day_for_doy:
            month_day_for_doy[doy] = (m + 1, day)

# Full baseline date range including windows
full_start = date(1991, 12, 27)
full_end = date(2003, 1, 5)

# For each day-of-year, build the list of dates that contribute to its pool
# First, let's pre-compute which dates are in the baseline data
# We need to map each date D to its SST data (for the sea cells only, we'll filter later)

# For each day-of-year d (1-366, d≠60):
# 1. Find (month, day) for d
# 2. For each year Y in 1992-2002:
#    a. E = (Y, month, day) - if valid
#    b. For offset in [-5, 5]: D = E + offset, if D in [1991-12-27, 2003-01-05], add to pool

# Let me first build the complete list of (doy, date_index) pairs for pooling
# Then we can extract the SST values

# Actually, let me think about a more efficient approach.
# For each date D in the baseline data, find which days-of-year it contributes to.
# A date D contributes to day-of-year d if D is within ±5 days of some date E with doy(E)=d, where E is in [1992-01-01, 2002-12-31].

# Given D's date, we can compute all E dates (from 1992-2002) that are within ±5 days of D.
# Then we compute doy(E) for each such E.
# D contributes to each of those doy values.

# This is O(n_dates * 11 years * 11 offsets) = O(4028 * 11 * 11) = ~487k operations, which is fine.

# Actually, let me be smarter. For each date D, the E dates within ±5 days are at most 11 dates per year * 11 years = up to 121 dates (some might not be valid, e.g., Feb 29 in non-leap years).

# But actually, for each date D, I can directly compute the doy values it contributes to.
# D is a date. The E dates within ±5 calendar days are D-5, D-4, ..., D+5.
# For each such E, if E is in [1992-01-01, 2002-12-31], compute doy(E).
# D contributes to the pool for each such doy(E).

# Let me implement this.

# For each date D in the baseline data, find which doy pools it contributes to
doy_to_date_indices = {}  # doy -> list of baseline indices

for i, D in enumerate(baseline_dates):
    doy_D = day_of_year_366(D)
    # For each offset in [-5, 5], compute E = D + offset
    for offset in range(-5, 6):
        E = D + timedelta(days=offset)
        # Check if E is in [1992-01-01, 2002-12-31]
        if date(1992, 1, 1) <= E <= date(2002, 12, 31):
            doy_E = day_of_year_366(E)
            if doy_E != 60:  # Skip day 60
                if doy_E not in doy_to_date_indices:
                    doy_to_date_indices[doy_E] = []
                doy_to_date_indices[doy_E].append(i)

# Verify
print(f"Number of days-of-year with pools: {len(doy_to_date_indices)}")
# Check some specific days
for d in [1, 59, 61, 153, 244, 366]:
    if d in doy_to_date_indices:
        print(f"DOY {d}: {len(doy_to_date_indices[d])} dates in pool")
    else:
        print(f"DOY {d}: no pool")

# Check day 153 (June 1): should have ~11 years * 11 days = 121 dates (some may overlap)
# Actually, let me check: for doy=153 (June 1), the baseline dates are June 1 of 1992-2002 (11 dates).
# Each has ±5 days, so 11 days each. But adjacent years' windows may overlap at the boundary.
# E.g., May 27 1992 is within ±5 of June 1 1992, but also within ±5 of June 1 1993 (June 1 1993 - 5 = May 27 1993, which is different from May 27 1992).
# So no overlap between different years. The total should be ~121 dates.
print(f"Expected ~121 dates for DOY 153: {len(doy_to_date_indices.get(153, []))}")
