
import numpy as np
import pandas as pd

hot = np.load('/tmp/hot.npy')  # (92, 60, 60)
sea_cells = np.load('/tmp/sea_cells.npy')

n_days, n_lat, n_lon = hot.shape

# For each cell, identify per-cell MHWs
# Store as a boolean array: mhw_cell[day, lat, lon] = True if cell is in a per-cell MHW on that day
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
        
        # Join MHWs separated by 1 or 2 non-hot days
        joined_runs = []
        current = list(mhw_runs[0])
        for r in mhw_runs[1:]:
            gap = r[0] - current[1] - 1
            if gap <= 2:  # 1 or 2 non-hot days between them
                current[1] = r[1]
            else:
                joined_runs.append(tuple(current))
                current = list(r)
        joined_runs.append(tuple(current))
        
        # Mark the cells in MHWs (including gap days)
        for s, e in joined_runs:
            mhw_cell[s:e+1, i, j] = True

print("Per-cell MHW mask computed")
print("Cells with at least one MHW:", mhw_cell.any(axis=0).sum())

# Check some stats
print("Days with MHW activity:")
for d in range(n_days):
    n_mhw = mhw_cell[d].sum()
    if n_mhw > 0:
        date = pd.Timestamp(np.load('/tmp/target_dates.npy')[d])
        print(f"  {date}: {n_mhw} cells in MHW")

np.save('/tmp/mhw_cell.npy', mhw_cell)
print("Saved per-cell MHW mask")
