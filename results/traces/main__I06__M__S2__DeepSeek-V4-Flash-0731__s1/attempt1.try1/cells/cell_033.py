
import numpy as np
import pandas as pd

# Load data
hot = np.load('/tmp/hot.npy')  # (92, 60, 60)
sea_cells = np.load('/tmp/sea_cells.npy')

n_days, n_lat, n_lon = hot.shape

# For each cell, identify per-cell MHWs with corrected gap handling
mhw_cell = np.zeros_like(hot, dtype=bool)

for i in range(n_lat):
    for j in range(n_lon):
        if not sea_cells[i, j]:
            continue
        
        h = hot[:, i, j]  # (92,)
        
        # Find all runs of hot days
        runs = []
        in_run = False
        start = 0
        for d in range(n_days):
            if h[d] and not in_run:
                in_run = True
                start = d
            elif not h[d] and in_run:
                in_run = False
                runs.append((start, d - 1))
        if in_run:
            runs.append((start, n_days - 1))
        
        # Filter runs of length >= 5
        mhw_runs = [(s, e) for s, e in runs if e - s + 1 >= 5]
        
        if len(mhw_runs) == 0:
            continue
        
        # Join MHWs separated by 1 or 2 non-hot days (all gap days must be non-hot)
        joined_runs = []
        current = list(mhw_runs[0])
        for r in mhw_runs[1:]:
            gap_start = current[1] + 1
            gap_end = r[0] - 1
            gap_days = gap_end - gap_start + 1
            if 1 <= gap_days <= 2 and not h[gap_start:gap_end+1].any():
                current[1] = r[1]
            else:
                joined_runs.append(tuple(current))
                current = list(r)
        joined_runs.append(tuple(current))
        
        # Mark the cells in MHWs (including gap days)
        for s, e in joined_runs:
            mhw_cell[s:e+1, i, j] = True

print("Per-cell MHW mask computed (corrected)")

# Check
cells_with_mhw = np.where(mhw_cell.any(axis=0))
print(f"Cells with MHW: {len(cells_with_mhw[0])}")

# Find active days and regional events
target_dates = np.load('/tmp/target_dates.npy')
active = mhw_cell.any(axis=(1, 2))
print("Active days:", np.where(active)[0])

runs = []
in_run = False
start = 0
for d in range(len(active)):
    if active[d] and not in_run:
        in_run = True
        start = d
    elif not active[d] and in_run:
        in_run = False
        runs.append((start, d - 1))
if in_run:
    runs.append((start, len(active) - 1))

print("Regional events:")
for s, e in runs:
    onset = pd.Timestamp(target_dates[s]).strftime('%Y-%m-%d')
    end = pd.Timestamp(target_dates[e]).strftime('%Y-%m-%d')
    print(f"  Onset: {onset}, End: {end}, Duration: {e - s + 1} days")

np.save('/tmp/mhw_cell_corrected.npy', mhw_cell)
