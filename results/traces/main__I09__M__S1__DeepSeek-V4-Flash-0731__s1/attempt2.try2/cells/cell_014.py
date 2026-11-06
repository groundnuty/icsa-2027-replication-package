
import numpy as np
from datetime import date, timedelta

# Load baseline data
baseline_sst = np.load('/tmp/baseline_sst.npy')
baseline_dates_ord = np.load('/tmp/baseline_dates.npy')
baseline_dates = [date.fromordinal(int(o)) for o in baseline_dates_ord]

# Day-of-year mapping
month_days = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
cum_days = [0]
for md in month_days[:-1]:
    cum_days.append(cum_days[-1] + md)

def date_to_doy(d):
    return cum_days[d.month - 1] + d.day

def doy_to_date_in_year(doy, year):
    for m in range(12):
        if doy <= cum_days[m] + month_days[m]:
            day = doy - cum_days[m]
            try:
                return date(year, m+1, day)
            except ValueError:
                return None
    return None

# Build date->index mapping
date_to_idx = {}
for i, d in enumerate(baseline_dates):
    date_to_idx[d] = i

baseline_years = list(range(1992, 2003))

doy_pool_indices = {}
for d in range(1, 367):
    if d == 60:
        continue
    pool_idx = set()
    for y in baseline_years:
        d_base = doy_to_date_in_year(d, y)
        if d_base is None:
            continue
        for offset in range(-5, 6):
            dd = d_base + timedelta(days=offset)
            if dd in date_to_idx:
                pool_idx.add(date_to_idx[dd])
    doy_pool_indices[d] = sorted(pool_idx)

# Verify some pools
for test_d in [1, 59, 61, 200, 366]:
    dates_in_pool = [baseline_dates[i] for i in doy_pool_indices[test_d]]
    print(f"doy {test_d}: {len(doy_pool_indices[test_d])} pool entries")
    print(f"  First: {dates_in_pool[0]}, Last: {dates_in_pool[-1]}")

# Save pool indices (skip 60)
np.save('/tmp/doy_pool_indices.npy', 
        np.array([doy_pool_indices.get(d, []) for d in range(1, 367)], dtype=object), 
        allow_pickle=True)
print("Pool indices saved")
