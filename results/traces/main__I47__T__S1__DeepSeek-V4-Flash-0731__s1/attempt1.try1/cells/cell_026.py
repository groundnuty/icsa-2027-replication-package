
import numpy as np
import pandas as pd
import json
import os

# Load saved data
tgt_data = np.load('/tmp/tgt_data.npy')
tgt_times = np.load('/tmp/tgt_times.npy')
threshold_smooth = np.load('/tmp/threshold_smooth.npy')
lats = np.load('/tmp/lats.npy')
lons = np.load('/tmp/lons.npy')

# Define day-of-year function
def day_of_year(month, day):
    days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    if month == 2 and day == 29:
        return 60
    doy = sum(days_in_month[:month-1]) + day
    if month > 2:
        doy += 1
    return doy

# Compute day-of-year for each target date
tgt_doy = np.array([day_of_year(pd.Timestamp(t).to_pydatetime().month, 
                                pd.Timestamp(t).to_pydatetime().day) for t in tgt_times])

N_t = len(tgt_times)
N_lat = len(lats)
N_lon = len(lons)
print(f"Target period: {N_t} days, {N_lat} lats, {N_lon} lons")

# Step 1: Identify sea cells (finite SST on every target day)
sea_mask = np.all(np.isfinite(tgt_data), axis=0)
print(f"Sea cells: {sea_mask.sum()}")

# Step 2: Compute hot days
hot = np.zeros((N_t, N_lat, N_lon), dtype=bool)
for t in range(N_t):
    doy = tgt_doy[t]
    hot[t] = tgt_data[t] >= threshold_smooth[doy-1]
hot = hot & sea_mask

# Step 3: Find per-cell MHWs
mhw_mask = np.zeros((N_t, N_lat, N_lon), dtype=bool)

sea_idx = np.where(sea_mask)
for k in range(len(sea_idx[0])):
    i, j = sea_idx[0][k], sea_idx[1][k]
    cell_hot = hot[:, i, j]
    
    # Find runs of hot days
    runs = []
    t = 0
    while t < N_t:
        if cell_hot[t]:
            start = t
            while t < N_t and cell_hot[t]:
                t += 1
            end = t - 1
            runs.append((start, end))
        else:
            t += 1
    
    if not runs:
        continue
    
    # Join runs separated by 1-2 non-hot days
    joined = [runs[0]]
    for r in runs[1:]:
        prev_end = joined[-1][1]
        gap = r[0] - prev_end - 1
        if gap >= 1 and gap <= 2:
            joined[-1] = (joined[-1][0], r[1])
        else:
            joined.append(r)
    
    # Keep runs of length >= 5
    for start, end in joined:
        if end - start + 1 >= 5:
            mhw_mask[start:end+1, i, j] = True

print(f"MHW day-cell counts: {mhw_mask.sum()}")

# Step 4: Regional events
daily_mhw = mhw_mask.sum(axis=(1, 2))
active = daily_mhw > 0

# Find maximal runs of consecutive active days
events = []
t = 0
while t < N_t:
    if active[t]:
        start = t
        while t < N_t and active[t]:
            t += 1
        end = t - 1
        events.append((start, end))
    else:
        t += 1

print(f"Regional events: {len(events)}")
for start, end in events:
    onset = pd.Timestamp(tgt_times[start]).date().isoformat()
    end_date = pd.Timestamp(tgt_times[end]).date().isoformat()
    print(f"  Event: {onset} to {end_date} (days {start}-{end})")

# Build events list for report
events_list = []
for start, end in events:
    onset = pd.Timestamp(tgt_times[start]).date().isoformat()
    end_date = pd.Timestamp(tgt_times[end]).date().isoformat()
    events_list.append({"onset": onset, "end": end_date})

print("\nEvents list:", json.dumps(events_list, indent=2))

# Save mhw_mask for output
np.save('/tmp/mhw_mask.npy', mhw_mask)
np.save('/tmp/sea_mask.npy', sea_mask)
print("Saved mhw_mask and sea_mask")
