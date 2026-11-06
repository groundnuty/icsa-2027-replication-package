
import numpy as np
import pandas as pd

# Load data
target_data = np.load('/tmp/target_data.npy').astype(np.float64)
target_times = np.load('/tmp/target_times.npy').astype('datetime64[D]')
threshold_smooth = np.load('/tmp/threshold_smooth.npy')
climatology_smooth = np.load('/tmp/climatology_smooth.npy')
sea_mask = np.load('/tmp/sea_mask.npy')

print("target shape:", target_data.shape)
print("target times:", target_times[0], "to", target_times[-1])
print("sea mask count:", sea_mask.sum())

# Day of year function
def day_of_year(month, day):
    month_days = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return sum(month_days[:month-1]) + day

# Get day of year for each target date
target_doy = np.array([day_of_year(pd.Timestamp(t).month, pd.Timestamp(t).day) for t in target_times])
print("target doy:", target_doy[:5], "...", target_doy[-5:])

# For each target day, find the threshold for each sea cell
# threshold_smooth[doy-1, lat, lon]

n_time, n_lat, n_lon = target_data.shape
n_doy = 366

# Determine hot days: SST >= threshold
# hot[time, lat, lon] = 1 if hot, 0 otherwise
hot = np.zeros((n_time, n_lat, n_lon), dtype=bool)

for t in range(n_time):
    doy = target_doy[t]
    thr = threshold_smooth[doy-1, :, :]  # threshold for this day of year
    sst = target_data[t, :, :]
    hot[t, :, :] = (sst >= thr) & sea_mask

print("Hot count:", hot.sum(), "of", hot.size)

# Find per-cell MHWs
# A per-cell MHW is a run of at least 5 consecutive hot days
# Per-cell MHWs separated by 1 or 2 non-hot days are joined, and gap days belong to the event

# We'll process each cell independently
n_lat, n_lon = sea_mask.shape
n_time = target_data.shape[0]

# For each cell, find MHW masks
# mhw_mask[time, lat, lon] = 1 if cell is in a per-cell MHW on that day
mhw_mask = np.zeros((n_time, n_lat, n_lon), dtype=np.uint8)

for i in range(n_lat):
    for j in range(n_lon):
        if not sea_mask[i, j]:
            continue
        
        hot_series = hot[:, i, j]
        
        # Find runs of consecutive hot days
        # First, find all hot runs (any length)
        runs = []
        in_run = False
        start = 0
        for t in range(n_time):
            if hot_series[t]:
                if not in_run:
                    in_run = True
                    start = t
            else:
                if in_run:
                    runs.append((start, t-1))
                    in_run = False
        if in_run:
            runs.append((start, n_time-1))
        
        if not runs:
            continue
        
        # Join runs separated by 1 or 2 non-hot days
        # First, mark runs of >= 5 hot days as MHW candidates
        # Then join MHW candidates separated by <= 2 non-hot days
        
        # Step 1: identify runs with length >= 5
        mhw_runs = []
        for (s, e) in runs:
            if e - s + 1 >= 5:
                mhw_runs.append([s, e])
        
        if not mhw_runs:
            continue
        
        # Step 2: join MHW runs separated by 1 or 2 non-hot days
        joined = [mhw_runs[0].copy()]
        for k in range(1, len(mhw_runs)):
            prev_end = joined[-1][1]
            curr_start = mhw_runs[k][0]
            gap = curr_start - prev_end - 1
            if gap <= 2:
                joined[-1][1] = mhw_runs[k][1]
            else:
                joined.append(mhw_runs[k].copy())
        
        # Mark the mask
        for (s, e) in joined:
            mhw_mask[s:e+1, i, j] = 1

print("MHW mask count:", mhw_mask.sum())

# Regional events
# A day is active if at least one sea cell is inside a per-cell MHW
active = np.any(mhw_mask > 0, axis=(1, 2))
print("Active days:", active.sum(), "of", n_time)

# Find maximal runs of consecutive active days
events = []
in_event = False
start = 0
for t in range(n_time):
    if active[t]:
        if not in_event:
            in_event = True
            start = t
    else:
        if in_event:
            events.append((start, t-1))
            in_event = False
if in_event:
    events.append((start, n_time-1))

print("Regional events:", len(events))
for (s, e) in events:
    print(f"  {target_times[s]} to {target_times[e]} ({e-s+1} days)")

# Save results
np.save('/tmp/mhw_mask.npy', mhw_mask)
print("Saved mhw_mask")
