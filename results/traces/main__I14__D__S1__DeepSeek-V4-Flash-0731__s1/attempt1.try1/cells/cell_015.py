
import numpy as np
import pandas as pd

# Load data
baseline_sst = np.load('/work/baseline_sst.npy')
baseline_times = np.load('/work/baseline_times.npy')
baseline_pd = pd.to_datetime(baseline_times)

def doy(date):
    dt = pd.Timestamp(date)
    month = dt.month
    day = dt.day
    month_lengths = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return sum(month_lengths[:month-1]) + day

# Compute DOY for each baseline date
baseline_doy = np.array([doy(d) for d in baseline_pd])

# For the pool construction:
# For each DOY d, the pool includes dates that are within ±5 calendar days of a baseline date (1992-01-01 to 2002-12-31) whose DOY is d.
# "Baseline date" = date in 1992-01-01 to 2002-12-31

# Let me first find the baseline dates (1992-01-01 to 2002-12-31) in our extracted data
baseline_core_start = pd.Timestamp('1992-01-01')
baseline_core_end = pd.Timestamp('2002-12-31')

# All dates in our baseline extraction (includes extension)
all_dates = baseline_pd
all_doy = baseline_doy

# Find which dates are "baseline dates" (in 1992-01-01 to 2002-12-31)
is_core = (all_dates >= baseline_core_start) & (all_dates <= baseline_core_end)
core_indices = np.where(is_core)[0]
print(f"Core baseline dates (1992-01-01 to 2002-12-31): {len(core_indices)}")

# For each DOY d, find all core baseline dates with that DOY
# Then expand ±5 calendar days
pools = {}  # DOY -> list of indices into baseline_sst

for d in range(1, 367):
    if d == 60:
        pools[d] = None  # No pool for day 60
        continue
    
    # Find core baseline dates with this DOY
    matching_core = core_indices[all_doy[core_indices] == d]
    
    if len(matching_core) == 0:
        pools[d] = []
        continue
    
    # For each such date, find all dates within ±5 calendar days
    pool_indices = set()
    for idx in matching_core:
        date = all_dates[idx]
        # Find dates from date-5 days to date+5 days
        start = date - pd.Timedelta(days=5)
        end = date + pd.Timedelta(days=5)
        
        # Find indices in all_dates within [start, end]
        mask = (all_dates >= start) & (all_dates <= end)
        idxs = np.where(mask)[0]
        pool_indices.update(idxs)
    
    pools[d] = sorted(pool_indices)

# Verify some pools
for d in [1, 59, 60, 61, 153, 244, 366]:
    if pools[d] is not None:
        print(f"DOY {d}: pool size = {len(pools[d])}")
        if len(pools[d]) > 0:
            print(f"  First few dates: {[str(all_dates[i].date()) for i in pools[d][:3]]}")
            print(f"  Last few dates: {[str(all_dates[i].date()) for i in pools[d][-3:]]}")
    else:
        print(f"DOY {d}: No pool")

# Check DOY 59 pool - should include Feb 29 values
print(f"\nDOY 59 pool dates (sample):")
idx59 = pools[59]
for i in idx59[:10]:
    print(f"  {all_dates[i].date()} DOY={all_doy[i]}")

# Check if any DOY 60 dates (Feb 29) are in pools of neighbors
doy60_dates = [all_dates[i] for i in range(len(all_dates)) if all_doy[i] == 60]
print(f"\nFeb 29 dates in baseline: {len(doy60_dates)}")
for d in [59, 61]:
    for dt in doy60_dates:
        # Is this Feb 29 date within ±5 of a DOY 59 or 61 date?
        # Feb 29 is between Feb 28 and Mar 1
        # Feb 28 (DOY 59) ± 5 includes Feb 29
        # Mar 1 (DOY 61) ± 5 includes Feb 29
        pass
    # Check if any pool includes Feb 29 dates
    if d in pools:
        doy60_in_pool = [all_dates[i] for i in pools[d] if all_doy[i] == 60]
        print(f"  DOY {d} pool includes {len(doy60_in_pool)} Feb 29 dates")
