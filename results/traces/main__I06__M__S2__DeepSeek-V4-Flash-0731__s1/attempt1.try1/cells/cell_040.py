
import numpy as np
import pandas as pd

hot = np.load('/tmp/hot.npy')
sea_cells = np.load('/tmp/sea_cells.npy')
target_dates = np.load('/tmp/target_dates.npy')

n_days, n_lat, n_lon = hot.shape

# For each sea cell, find all runs of >= 5 hot days
n_mhw_cells = 0
all_mhw_runs = []
for i in range(n_lat):
    for j in range(n_lon):
        if not sea_cells[i, j]:
            continue
        h = hot[:, i, j]
        # Find runs
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
        
        # MHWs: runs >= 5
        mhw_runs = [(s, e) for s, e in runs if e - s + 1 >= 5]
        if mhw_runs:
            n_mhw_cells += 1
            for s, e in mhw_runs:
                onset = pd.Timestamp(target_dates[s]).strftime('%Y-%m-%d')
                end = pd.Timestamp(target_dates[e]).strftime('%Y-%m-%d')
                all_mhw_runs.append((i, j, s, e, onset, end))
                print(f"Cell ({i},{j}): MHW {onset} to {end}, len={e-s+1}")

print(f"\nTotal cells with MHWs: {n_mhw_cells}")
print(f"Total MHW runs: {len(all_mhw_runs)}")
