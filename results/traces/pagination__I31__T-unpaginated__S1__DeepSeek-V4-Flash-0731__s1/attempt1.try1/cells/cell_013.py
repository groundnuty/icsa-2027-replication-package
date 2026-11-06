
import numpy as np
import datetime as dt

# Day of year mapping
month_offsets = {1: 0, 2: 31, 3: 60, 4: 91, 5: 121, 6: 152, 7: 182, 8: 213, 9: 244, 10: 274, 11: 305, 12: 335}

def date_to_doy(y, m, d):
    return month_offsets[m] + d

# Build doy -> pool dates (as before)
baseline_start = dt.date(1992, 1, 1)
baseline_end = dt.date(2002, 12, 31)

doy_to_baseline_dates = {d: [] for d in range(1, 367)}
d = baseline_start
while d <= baseline_end:
    doy = date_to_doy(d.year, d.month, d.day)
    doy_to_baseline_dates[doy].append(d)
    d += dt.timedelta(days=1)

doy_to_pool_dates = {}
for doy in range(1, 367):
    if doy == 60:
        continue
    pool_dates = set()
    for B in doy_to_baseline_dates[doy]:
        for offset in range(-5, 6):
            pool_dates.add(B + dt.timedelta(days=offset))
    doy_to_pool_dates[doy] = sorted(pool_dates)

# Map each date to its index in the baseline array
# dates_baseline was defined as all dates from 1991-12-27 to 2003-01-05
# Let me reconstruct the dates list
dates_baseline = []
d = dt.date(1991, 12, 27)
while d <= dt.date(2003, 1, 5):
    dates_baseline.append(d)
    d += dt.timedelta(days=1)

date_to_index = {date: i for i, date in enumerate(dates_baseline)}

# For each doy, get the indices into baseline_sst
doy_to_pool_indices = {}
for doy in range(1, 367):
    if doy == 60:
        continue
    indices = [date_to_index[d] for d in doy_to_pool_dates[doy]]
    doy_to_pool_indices[doy] = np.array(indices)

# Verify: doy 1 should have 121 indices (11 years * 11 days)
print(f"doy 1 pool indices: {len(doy_to_pool_indices[1])}")
print(f"doy 59 pool indices: {len(doy_to_pool_indices[59])}")
print(f"doy 61 pool indices: {len(doy_to_pool_indices[61])}")
print(f"doy 366 pool indices: {len(doy_to_pool_indices[366])}")
