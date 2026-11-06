
import numpy as np
import datetime

# Load data
baseline_vals = np.load('baseline_vals.npy')  # (4028, 60, 60) float32
target_vals = np.load('target_vals.npy')  # (92, 60, 60)
baseline_dates_str = np.load('baseline_dates.npy', allow_pickle=True)
target_dates_str = np.load('target_dates.npy', allow_pickle=True)
lat_vals = np.load('lat_vals.npy')
lon_vals = np.load('lon_vals.npy')

# Convert to datetime
baseline_dt = [datetime.datetime.strptime(str(s), '%Y-%m-%d') for s in baseline_dates_str]
target_dt = [datetime.datetime.strptime(str(s), '%Y-%m-%d') for s in target_dates_str]

# Day of year mapping
def day_of_year(dt):
    month_offsets = [0, 0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return month_offsets[dt.month] + dt.day

# Month-day mapping
month_days = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

def doy_to_md(doy):
    cum = 0
    for m in range(12):
        if doy <= cum + month_days[m]:
            return m + 1, doy - cum
        cum += month_days[m]
    raise ValueError(f"Invalid doy: {doy}")

def is_valid_date(y, m, d):
    try:
        datetime.date(y, m, d)
        return True
    except ValueError:
        return False

# For each day of year d (except 60), find all dates in our data range belonging to pool d
all_dates = baseline_dt  # 1991-12-27 to 2003-01-05

pool_indices = {}
for d in range(1, 367):
    if d == 60:
        continue
    m, dd = doy_to_md(d)
    
    # Find baseline dates (1992-2002) with this month/day
    baseline_dates_for_d = []
    for y in range(1992, 2003):
        if is_valid_date(y, m, dd):
            baseline_dates_for_d.append(datetime.datetime(y, m, dd))
    
    # For each such baseline date, find all dates in our data within ±5 days
    idx_set = set()
    for D in baseline_dates_for_d:
        for delta in range(-5, 6):
            X = D + datetime.timedelta(days=delta)
            # Check if X is in our data range
            if X >= all_dates[0] and X <= all_dates[-1]:
                idx = (X - all_dates[0]).days
                idx_set.add(idx)
    
    pool_indices[d] = sorted(idx_set)

print(f"Number of pools: {len(pool_indices)}")
# Check pool sizes
for d in [1, 59, 61, 153, 244, 366]:
    print(f"Pool {d}: {len(pool_indices[d])} dates")

# Check: pool 59 (Feb 28) should include Feb 29 dates
print("\nPool 59 dates:")
for i in pool_indices[59]:
    print(f"  {all_dates[i]}")
print("\nPool 61 dates:")
for i in pool_indices[61]:
    print(f"  {all_dates[i]}")
