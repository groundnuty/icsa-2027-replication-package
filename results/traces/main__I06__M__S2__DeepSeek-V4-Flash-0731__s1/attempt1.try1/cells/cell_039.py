
import numpy as np
import pandas as pd

hot = np.load('/tmp/hot.npy')
sea_cells = np.load('/tmp/sea_cells.npy')
target_dates = np.load('/tmp/target_dates.npy')

n_days, n_lat, n_lon = hot.shape

# Find all sea cells and check their hot patterns
print("Hot patterns for all sea cells:")
for i in range(n_lat):
    for j in range(n_lon):
        if not sea_cells[i, j]:
            continue
        h = hot[:, i, j]
        if h.any():
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
            
            # Print runs of length >= 1
            for s, e in runs:
                length = e - s + 1
                onset = pd.Timestamp(target_dates[s]).strftime('%m-%d')
                end = pd.Timestamp(target_dates[e]).strftime('%m-%d')
                marker = "MHW" if length >= 5 else ""
                if length >= 3 or (s in range(8, 25)):  # show June-related runs
                    print(f"  Cell ({i},{j}): {onset} to {end}, len={length} {marker}")
