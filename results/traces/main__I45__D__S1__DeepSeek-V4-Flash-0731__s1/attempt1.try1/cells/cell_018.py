
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
print(f"Baseline dates (1992-2002): {len(baseline_indices)}")

# For each day of year d (1-366, d≠60), find all dates within ±5 days of a baseline date with doy=d
# This means: for each baseline date with doy=d, add all dates in [date-5, date+5] to the pool for day d

# First, let's map each baseline date to its day of year
base_doy = np.array([doy_fixed(d) for d in base_dates[baseline_indices]])

# Now, for each day d, find the set of dates (indices into base_dates) that are in the pool
# A date at index i in base_dates is in the pool for day d if:
#   there exists a baseline date j with doy=d such that |base_dates[i] - base_dates[j]| <= 5 days

# Strategy: for each day d, find all baseline dates with doy=d, then expand each by ±5 days
# Collect the union of these date indices

# This could be expensive if done naively. Let's be smart about it.

# For each day d, find baseline indices with doy=d
from collections import defaultdict
doy_to_baseline_idx = defaultdict(list)
for idx, d in zip(baseline_indices, base_doy):
    doy_to_baseline_idx[d].append(idx)

# For each day d (1-366, d≠60), compute pool indices
# Pool for day d = union over baseline dates j with doy(j)=d of [j-5, j+5] in base_dates indices
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

# Print some stats
for d in [1, 59, 61, 153, 244, 366]:
    print(f"Day {d}: {len(pool_indices[d])} dates in pool, first={base_dates[pool_indices[d][0]]}, last={base_dates[pool_indices[d][-1]]}")

# Check day 60: should have no pool of its own
print(f"Day 60 has pool: {60 in pool_indices}")
