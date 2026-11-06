
import numpy as np
from datetime import datetime, timedelta
import pandas as pd
from collections import defaultdict

def day_of_year(dt):
    cum_days_leap = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum_days_leap[dt.month - 1] + dt.day

# All loaded dates (baseline)
start = datetime(1991, 12, 27)
end = datetime(2003, 1, 5)
all_loaded_dates = []
d = start
while d <= end:
    all_loaded_dates.append(d)
    d += timedelta(days=1)

date_to_idx = {dt: i for i, dt in enumerate(all_loaded_dates)}

# Build pool_indices for each day of year
pool_indices = defaultdict(set)
baseline_start = datetime(1992, 1, 1)
baseline_end = datetime(2002, 12, 31)

d = baseline_start
while d <= baseline_end:
    doy = day_of_year(d)
    if doy != 60:
        for offset in range(-5, 6):
            x = d + timedelta(days=offset)
            if x in date_to_idx:
                pool_indices[doy].add(date_to_idx[x])
    d += timedelta(days=1)

# Convert sets to sorted lists for reproducibility
pool_indices = {doy: sorted(list(indices)) for doy, indices in pool_indices.items()}
print(f"Number of pools: {len(pool_indices)}")

# Check all days 1-366 except 60 have pools
missing = [d for d in range(1, 367) if d != 60 and d not in pool_indices]
print(f"Missing pools: {missing}")
