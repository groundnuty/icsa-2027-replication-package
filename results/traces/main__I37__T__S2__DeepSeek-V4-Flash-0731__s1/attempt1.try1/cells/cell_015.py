
import pandas as pd
import numpy as np

# We have the extended baseline dates
ext_dates = pd.date_range('1991-12-27', '2003-01-05', freq='D')

# Baseline dates (1992-01-01 to 2002-12-31)
base_dates = pd.date_range('1992-01-01', '2002-12-31', freq='D')

# Fixed day-of-year function
def fixed_doy(ts):
    cum = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum[ts.month - 1] + ts.day

# For each day-of-year d (1-366, d≠60), find which extended baseline dates belong to pool d
# A date t in ext_dates belongs to pool d if ∃ B in base_dates with doy(B)=d and |t-B| ≤ 5

# Build mapping from each extended baseline date to the pools it belongs to
# Actually, let me build the inverse: for each pool d, the set of extended baseline dates

# First, for each doy d, find all baseline dates B with doy(B)=d
base_doy = np.array([fixed_doy(d) for d in base_dates])

# Build pool date indices for each d
pool_time_indices = {}  # d -> list of indices in ext_dates

for d in range(1, 367):
    if d == 60:
        continue
    # Find baseline dates with this doy
    b_mask = (base_doy == d)
    b_dates_for_d = base_dates[b_mask]
    
    # For each such date, find extended baseline dates within ±5 days
    pool_dates = set()
    for b in b_dates_for_d:
        for t in ext_dates:
            if abs((t - b).days) <= 5:
                pool_dates.add(t)
    
    # Convert to indices in ext_dates
    indices = [np.where(ext_dates == t)[0][0] for t in sorted(pool_dates)]
    pool_time_indices[d] = indices

# Check sizes
for d in [1, 59, 61, 365, 366]:
    print(f"Day {d}: pool has {len(pool_time_indices[d])} dates")

# Check total
total = sum(len(v) for v in pool_time_indices.values())
print(f"Total pool date entries: {total}")
