
import numpy as np
import pickle
import datetime
import json

# Load data
target_sst = np.load('/tmp/target_sst.npy').astype(np.float64)
sea_cells = np.load('/tmp/sea_cells.npy')
threshold_smooth = np.load('/tmp/threshold_smooth.npy')
climatology_smooth = np.load('/tmp/climatology_smooth.npy')

print(f"Target SST shape: {target_sst.shape}")
print(f"Sea cells shape: {sea_cells.shape}")
print(f"Threshold shape: {threshold_smooth.shape}")

# Reconstruct target dates
target_dates = []
d = datetime.date(2021, 6, 1)
while d <= datetime.date(2021, 8, 31):
    target_dates.append(d)
    d += datetime.timedelta(days=1)
n_days = len(target_dates)
print(f"Target days: {n_days}")

# Compute doy for each target day
def doy_from_date(date):
    month_starts = [1, 32, 61, 92, 122, 153, 183, 214, 245, 275, 306, 336]
    return month_starts[date.month - 1] + date.day - 1

target_doys = [doy_from_date(d) for d in target_dates]
print(f"Target doys: {target_doys[:5]} ... {target_doys[-5:]}")

# Get sea cell indices
sea_idx = np.where(sea_cells)
n_sea = len(sea_idx[0])
print(f"Sea cells: {n_sea}")

# For each sea cell, compute hot days
# hot[i, li, loi] = target_sst[i, li, loi] >= threshold_smooth[doy-1, li, loi]
hot = np.zeros((n_days, 60, 60), dtype=bool)

for si in range(n_sea):
    li, loi = sea_idx[0][si], sea_idx[1][si]
    for i in range(n_days):
        d = target_doys[i] - 1  # 0-based index into threshold array
        sst_val = target_sst[i, li, loi]
        thr_val = threshold_smooth[d, li, loi]
        if not np.isnan(sst_val) and not np.isnan(thr_val):
            hot[i, li, loi] = sst_val >= thr_val

print(f"Hot day count: {hot.sum()}")

# Find per-cell MHWs
# For each sea cell, find runs of >= 5 consecutive hot days
# Then join MHWs separated by 1-2 non-hot days

def find_per_cell_mhws(hot_array):
    """Find per-cell MHWs from a boolean array of hot days."""
    n = len(hot_array)
    # Find all maximal runs of hot days
    runs = []
    i = 0
    while i < n:
        if hot_array[i]:
            j = i
            while j < n and hot_array[j]:
                j += 1
            runs.append((i, j-1))
            i = j
        else:
            i += 1
    
    # Keep runs with length >= 5
    mhws = [(s, e) for s, e in runs if e - s + 1 >= 5]
    
    # Merge MHWs separated by 1-2 non-hot days
    merged = []
    for mhw in mhws:
        if not merged:
            merged.append(mhw)
        else:
            prev_end = merged[-1][1]
            gap = mhw[0] - prev_end - 1
            if 1 <= gap <= 2:
                merged[-1] = (merged[-1][0], mhw[1])
            else:
                merged.append(mhw)
    
    return merged

# Compute per-cell MHWs for all sea cells
# mhw_mask: (n_days, 60, 60) uint8 - 1 if cell is in an MHW on that day
mhw_mask = np.zeros((n_days, 60, 60), dtype=np.uint8)

# For each sea cell
for si in range(n_sea):
    li, loi = sea_idx[0][si], sea_idx[1][si]
    cell_hot = hot[:, li, loi]
    mhws = find_per_cell_mhws(cell_hot)
    for (s, e) in mhws:
        mhw_mask[s:e+1, li, loi] = 1

print(f"MHW mask sum: {mhw_mask.sum()}")
print(f"Cells with MHWs: {(mhw_mask.max(axis=0) > 0).sum()}")

# Compute regional events
# A day is active if at least one sea cell is in an MHW on that day
active = mhw_mask.max(axis=(1, 2)) > 0
print(f"Active days: {active.sum()}")

# Find maximal runs of consecutive active days
regional_events = []
i = 0
while i < n_days:
    if active[i]:
        j = i
        while j < n_days and active[j]:
            j += 1
        regional_events.append((i, j-1))
        i = j
    else:
        i += 1

print(f"Regional events: {len(regional_events)}")
for s, e in regional_events:
    print(f"  Event: {target_dates[s]} to {target_dates[e]} ({e-s+1} days)")

# Save intermediate results
np.save('/tmp/mhw_mask.npy', mhw_mask)
np.save('/tmp/hot.npy', hot)
with open('/tmp/regional_events.pkl', 'wb') as f:
    pickle.dump([(s, e) for s, e in regional_events], f)
print("Saved intermediate results")
