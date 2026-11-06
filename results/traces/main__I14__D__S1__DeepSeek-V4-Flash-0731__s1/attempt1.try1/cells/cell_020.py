
import numpy as np
import pandas as pd

# Load data
target_sst = np.load('/work/target_sst.npy')
target_times = np.load('/work/target_times.npy')
target_pd = pd.to_datetime(target_times)
thresholds_smooth = np.load('/work/thresholds_smooth.npy')
climatology_smooth = np.load('/work/climatology_smooth.npy')

def doy(date):
    dt = pd.Timestamp(date)
    month = dt.month
    day = dt.day
    month_lengths = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return sum(month_lengths[:month-1]) + day

target_doy = np.array([doy(d) for d in target_pd])
print(f"Target DOYs: {target_doy}")
print(f"Target dates: {[str(d.date()) for d in target_pd]}")

# Identify sea cells
sea_cells = np.all(np.isfinite(target_sst), axis=0)
n_time, n_lat, n_lon = target_sst.shape

# For each sea cell, determine which days are hot
# A day is hot if SST >= threshold for that day of year
hot = np.zeros((n_time, n_lat, n_lon), dtype=bool)

for t in range(n_time):
    d = target_doy[t]
    # Get threshold for this DOY
    thresh = thresholds_smooth[d]  # shape (n_lat, n_lon)
    hot[t] = target_sst[t] >= thresh

# For non-sea cells, set hot = False
hot[:, ~sea_cells] = False

print(f"Hot days per cell: {hot.sum(axis=0).sum()} out of {n_time * n_lat * n_lon}")

# Find per-cell MHWs
# A run of at least 5 consecutive hot days
# MHWs separated by 1-2 non-hot days are joined
# Gap days belong to the event

per_cell_mhw = np.zeros((n_time, n_lat, n_lon), dtype=bool)

for lat_i in range(n_lat):
    for lon_i in range(n_lon):
        if not sea_cells[lat_i, lon_i]:
            continue
        
        # Get hot sequence for this cell
        hot_seq = hot[:, lat_i, lon_i]
        
        # Find runs of consecutive hot days
        # First find all hot runs, then join those separated by 1-2 non-hot days
        
        # Strategy: mark each day as "in an MHW" if:
        # - It's part of a run of >=5 hot days, OR
        # - It's within a gap of 1-2 non-hot days between two such runs
        
        # Find runs of hot days
        hot_runs = []  # list of (start, end) inclusive
        
        i = 0
        while i < n_time:
            if hot_seq[i]:
                # Find end of this hot run
                j = i
                while j < n_time and hot_seq[j]:
                    j += 1
                hot_runs.append((i, j - 1))
                i = j
            else:
                i += 1
        
        # Filter runs of length >= 5
        long_runs = [(s, e) for s, e in hot_runs if e - s + 1 >= 5]
        
        if len(long_runs) == 0:
            continue
        
        # Join runs separated by 1-2 non-hot days
        joined_runs = []
        current = long_runs[0]
        
        for next_run in long_runs[1:]:
            gap = next_run[0] - current[1] - 1
            if 1 <= gap <= 2:
                # Join
                current = (current[0], next_run[1])
            else:
                joined_runs.append(current)
                current = next_run
        
        joined_runs.append(current)
        
        # Mark all days in joined runs as part of MHW
        for s, e in joined_runs:
            per_cell_mhw[s:e+1, lat_i, lon_i] = True

print(f"Per-cell MHW days: {per_cell_mhw.sum()}")

# Regional events
# A day is active if at least one sea cell is in a per-cell MHW
active = np.any(per_cell_mhw, axis=(1, 2))
print(f"Active days: {active.sum()} out of {n_time}")

# Find maximal runs of consecutive active days
events = []
i = 0
while i < n_time:
    if active[i]:
        j = i
        while j < n_time and active[j]:
            j += 1
        events.append((i, j - 1))
        i = j
    else:
        i += 1

print(f"Regional events: {len(events)}")
for s, e in events:
    print(f"  {target_pd[s].date()} to {target_pd[e].date()} ({e - s + 1} days)")

np.save('/work/per_cell_mhw.npy', per_cell_mhw)
