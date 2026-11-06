
import numpy as np
import pandas as pd

# Load saved data
sst_baseline = np.load('/tmp/sst_baseline.npy')
sst_target = np.load('/tmp/sst_target.npy')
sea_cells = np.load('/tmp/sea_cells.npy')
baseline_dates = np.load('/tmp/baseline_dates.npy')
target_dates = np.load('/tmp/target_dates.npy')

print("baseline dates:", baseline_dates[0], baseline_dates[-1])
print("target dates:", target_dates[0], target_dates[-1])
print("dtypes:", baseline_dates.dtype)

# Convert to pandas for easier handling
baseline_dates_pd = pd.to_datetime(baseline_dates)

def doy_from_md(month, day):
    days_in_month = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return sum(days_in_month[:month-1]) + day

def doy_from_dt(dt):
    return doy_from_md(dt.month, dt.day)

# Baseline dates in 1992-2002 (the "baseline" years for pool construction)
baseline_year_dates = pd.date_range('1992-01-01', '2002-12-31', freq='D')
print("Baseline year dates count:", len(baseline_year_dates))

# For each doy (except 60), find which indices in baseline_dates_pd belong to its pool
pool_indices = {}  # doy -> list of indices into baseline_dates_pd
for d in range(1, 367):
    if d == 60:
        pool_indices[d] = np.array([], dtype=int)
        continue
    # Find baseline dates (1992-2002) with this doy
    b_dates = [dt for dt in baseline_year_dates if doy_from_dt(dt) == d]
    # For each such date, find indices in baseline_dates_pd within ±5 days
    idx_list = []
    for b in b_dates:
        b_ts = pd.Timestamp(b)
        # Find indices of dates within ±5 days of b
        diff = (baseline_dates_pd - b_ts).days
        mask = np.abs(diff) <= 5
        idx_list.extend(np.where(mask)[0])
    pool_indices[d] = np.array(sorted(set(idx_list)))

# Check
print("Pool sizes (number of baseline dates):")
for d in [1, 59, 61, 153, 244, 366]:
    print(f"  Day {d}: {len(pool_indices[d])}")

# Verify day 366 pool last date
last_pool_366 = baseline_dates_pd[pool_indices[366][-1]]
print(f"Day 366 last pool date: {last_pool_366}")

# Verify day 1 pool first date
first_pool_1 = baseline_dates_pd[pool_indices[1][0]]
print(f"Day 1 first pool date: {first_pool_1}")

# Save pool indices
import pickle
with open('/tmp/pool_indices.pkl', 'wb') as f:
    pickle.dump(pool_indices, f)
print("Saved pool indices")
