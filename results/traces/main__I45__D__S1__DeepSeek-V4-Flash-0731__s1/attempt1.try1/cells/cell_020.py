
import numpy as np
from datetime import datetime, timedelta

def doy_fixed(dt):
    month_offsets = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return month_offsets[dt.month - 1] + dt.day

# Load
base_sst = np.load('/work/base_sst.npy')
base_times = np.load('/work/base_times.npy')
base_dates = []
for t in base_times:
    dt = datetime.utcfromtimestamp(t.astype('datetime64[s]').astype(np.int64))
    base_dates.append(dt)
base_dates = np.array(base_dates)

# Identify baseline dates (1992-01-01 to 2002-12-31)
baseline_start = datetime(1992, 1, 1)
baseline_end = datetime(2002, 12, 31)
is_baseline = np.array([(d >= baseline_start) and (d <= baseline_end) for d in base_dates])
baseline_indices = np.where(is_baseline)[0]

base_doy = np.array([doy_fixed(d) for d in base_dates[baseline_indices]])

from collections import defaultdict
doy_to_baseline_idx = defaultdict(list)
for idx, d in zip(baseline_indices, base_doy):
    doy_to_baseline_idx[d].append(idx)

# Compute pool indices for each day
pool_indices = {}
for d in range(1, 367):
    if d == 60:
        continue
    pool_dates = set()
    for j in doy_to_baseline_idx[d]:
        for delta in range(-5, 6):
            idx = j + delta
            if 0 <= idx < len(base_dates):
                pool_dates.add(idx)
    pool_indices[d] = sorted(pool_dates)

# Check Feb 29
feb29_dates = []
for i, d in enumerate(base_dates):
    if d.month == 2 and d.day == 29:
        feb29_dates.append((i, d))
print("Feb 29 in data:", [(i, str(d)) for i, d in feb29_dates])

for i, d in feb29_dates:
    in_59 = i in pool_indices[59]
    in_61 = i in pool_indices[61]
    print(f"  Index {i} ({d}): in pool 59: {in_59}, in pool 61: {in_61}")
