
import numpy as np
from datetime import date, timedelta
import pandas as pd

# Day of year mapping by month/day
def doy_from_md(month, day):
    # 1 Jan = 1, 28 Feb = 59, 29 Feb = 60, 1 Mar = 61, ..., 31 Dec = 366
    cum = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    return cum[month-1] + day

def md_from_doy(doy):
    # Inverse mapping
    cum = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    for m in range(12):
        if doy <= cum[m+1]:
            return m+1, doy - cum[m]
    return 12, 31

def get_doy(d):
    return doy_from_md(d.month, d.day)

# Build day-of-year for all baseline ext dates
baseline_doy = np.array([get_doy(d) for d in baseline_dates])

# Baseline dates only (1992-01-01 to 2002-12-31)
baseline_mask = np.array([(date(1992,1,1) <= d <= date(2002,12,31)) for d in baseline_dates])
baseline_idx = np.where(baseline_mask)[0]
print("Number of baseline dates:", len(baseline_idx))

# For each day-of-year d (1-366, d!=60), find which dates in the window belong to pool d
# A date t belongs to pool d if there is a baseline date b with doy(b)=d and |t-b|<=5 days

# For efficiency, for each date t in the window, find which day-of-year pools it belongs to
# by checking baseline dates within ±5 days
from collections import defaultdict

# Precompute pools: pool_doy[d] = list of indices into baseline_sst for pool d
pool_indices = defaultdict(list)

# For each baseline date b (day-of-year d), find dates t in window with |t-b| <= 5
for bi in baseline_idx:
    b = baseline_dates[bi]
    b_doy = baseline_doy[bi]
    if b_doy == 60:
        continue  # day 60 gets no pool of its own
    # Find dates t in window within ±5 days of b
    t_start = b - timedelta(days=5)
    t_end = b + timedelta(days=5)
    # Binary search or linear scan for t indices
    # Since dates are sorted, use searchsorted
    # Convert to datetime64 for comparison
    ts = np.array([(d - date(1991,12,27)).days for d in baseline_dates])
    b_daynum = (b - date(1991,12,27)).days
    lo = b_daynum - 5
    hi = b_daynum + 5
    # Find indices in [lo, hi]
    indices = np.where((ts >= lo) & (ts <= hi))[0]
    pool_indices[b_doy].extend(indices)

print("Number of day-of-year pools:", len(pool_indices))
# Check a few pools
for d in [1, 59, 61, 90, 365, 366]:
    if d in pool_indices:
        print(f"Pool {d}: {len(pool_indices[d])} dates")
    else:
        print(f"Pool {d}: empty")
