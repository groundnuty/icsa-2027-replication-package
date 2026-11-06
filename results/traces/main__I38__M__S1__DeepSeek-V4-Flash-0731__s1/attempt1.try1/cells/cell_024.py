
import numpy as np
from datetime import date, timedelta
import json, time

intermediate_dir = 'intermediate'

# Load metadata
with open(f'{intermediate_dir}/metadata.json') as f:
    meta = json.load(f)

target_dates = [date.fromisoformat(d) for d in meta['target_dates']]

# Load data
threshold_smooth = np.load(f'{intermediate_dir}/threshold_smooth.npy')
sea_cells = np.load(f'{intermediate_dir}/sea_cells.npy')
target_sst = np.load(f'{intermediate_dir}/target_sst.npy')

# Day of year mapping
def day_of_year(d):
    month_days = [0, 31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return sum(month_days[:d.month]) + d.day

# Compute doy for each target date
target_doy = [day_of_year(d) for d in target_dates]
n_days = len(target_dates)

# Get thresholds with correct indexing
target_threshold = np.zeros((n_days, 60, 60))
for i, doy in enumerate(target_doy):
    target_threshold[i] = threshold_smooth[doy - 1]

# Compute hot/cold
hot = np.zeros((n_days, 60, 60), dtype=bool)
for i in range(n_days):
    sst = target_sst[i].astype(np.float64)
    th = target_threshold[i]
    hot[i] = (sst >= th) & ~np.isnan(sst)

# Per-cell MHWs - Interpretation B
# 1. Find runs of >= 5 consecutive hot days as MHWs
# 2. Join MHWs separated by 1-2 cold days
mhw_mask = np.zeros((n_days, 60, 60), dtype=bool)

t0 = time.time()
for la in range(60):
    for lo in range(60):
        if not sea_cells[la, lo]:
            continue
        
        cell_hot = hot[:, la, lo]
        
        # Find runs of hot days
        runs = []
        i = 0
        while i < n_days:
            if cell_hot[i]:
                start = i
                while i < n_days and cell_hot[i]:
                    i += 1
                end = i - 1
                runs.append((start, end))
            else:
                i += 1
        
        # Identify MHWs as runs of >= 5 hot days
        mhws = [(s, e) for s, e in runs if e - s + 1 >= 5]
        
        # Join MHWs separated by 1-2 cold days
        if mhws:
            merged = [mhws[0]]
            for m in mhws[1:]:
                gap = m[0] - merged[-1][1] - 1
                if gap <= 2:
                    merged[-1] = (merged[-1][0], m[1])
                else:
                    merged.append(m)
            
            # Mark merged MHWs
            for start, end in merged:
                mhw_mask[start:end+1, la, lo] = True

print(f"MHW computation took {time.time()-t0:.1f}s")
print(f"MHW mask sum: {mhw_mask.sum()}")

# Regional events
active = mhw_mask.any(axis=(1, 2))
print(f"Active days: {active.sum()}")
print(f"Active days pattern: {active}")

events = []
i = 0
while i < n_days:
    if active[i]:
        start = i
        while i < n_days and active[i]:
            i += 1
        end = i - 1
        events.append((start, end))
    else:
        i += 1

print(f"Regional events: {len(events)}")
for s, e in events:
    print(f"  Event: {target_dates[s]} to {target_dates[e]}")
