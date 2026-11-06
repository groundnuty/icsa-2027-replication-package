
import numpy as np
import pandas as pd

# Load saved data
sst_data = np.load('/tmp/sst_data.npy')
time_int = np.load('/tmp/time_sub.npy')
time_sub = time_int.astype('datetime64[s]')
lat_vals = np.load('/tmp/lat_vals.npy')
lon_vals = np.load('/tmp/lon_vals.npy')

def date_to_doy(date):
    ts = pd.Timestamp(date)
    month, day = ts.month, ts.day
    cum_days = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum_days[month-1] + day

# Compute all dates in full range
dates = pd.to_datetime(time_sub)
n_time = len(dates)

# Baseline period: 1992-01-01 to 2002-12-31
baseline_start = pd.Timestamp('1992-01-01')
baseline_end = pd.Timestamp('2002-12-31')

# For each DOY d (1-366, except 60), find all baseline dates with DOY d
# and then find all time steps within ±5 days of any such baseline date

# Create all dates in baseline range
baseline_dates = pd.date_range(baseline_start, baseline_end, freq='D')
baseline_doy = np.array([date_to_doy(d) for d in baseline_dates])

# For each DOY d, find the baseline dates with that DOY
# Then for each, find time steps within ±5 days

# Let me precompute this more efficiently
# For each time step D, check if there exists a baseline date B with DOY(B)=d and |D-B|<=5

# Actually, let me precompute for each time step which DOY pools it belongs to
# A time step D belongs to pool d if there exists a baseline date B with DOY d and |D-B|<=5

# Strategy: for each baseline date B, it contributes to pool date_to_doy(B).
# The time steps in [B-5, B+5] are all in pool date_to_doy(B).

# So: for each baseline date B in 1992-2002:
#   d = date_to_doy(B)
#   For all time steps D in [B-5, B+5], D belongs to pool d

# Let me build the pool masks for each DOY
# pool_masks[d] = boolean array of length n_time

# Initialize
pool_masks = {}
for d in range(1, 367):
    if d == 60:
        continue
    pool_masks[d] = np.zeros(n_time, dtype=bool)

# For each baseline date B, mark time steps in [B-5, B+5] as belonging to pool DOY(B)
for B in baseline_dates:
    d = date_to_doy(B)
    if d == 60:
        continue
    B_start = B - pd.Timedelta(days=5)
    B_end = B + pd.Timedelta(days=5)
    # Find time steps in [B_start, B_end]
    mask = (dates >= B_start) & (dates <= B_end)
    pool_masks[d] |= mask

# Verify: check counts for some DOYs
for d in [1, 60, 61, 153, 244, 366]:
    if d == 60:
        print(f"DOY {d}: skipped (no pool)")
    else:
        print(f"DOY {d}: {pool_masks[d].sum()} time steps in pool")

# Check: how many time steps are in multiple pools?
total_pool_steps = sum(pool_masks[d].sum() for d in pool_masks)
print(f"Total pool steps across all DOYs: {total_pool_steps}")
print(f"n_time: {n_time}")
