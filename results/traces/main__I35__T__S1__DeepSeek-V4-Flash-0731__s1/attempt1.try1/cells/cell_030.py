
import numpy as np

# Load data
hot_mask = np.load('/tmp/hot_mask.npy')  # (92, 60, 60)
mhw_mask_old = np.load('/tmp/mhw_mask.npy')

# Let me check: for each sea cell, find the hot runs and see if my approach differs
# from the "runs >= 5 first, then join" approach

# Identify sea cells
target_sst = np.load('/tmp/target_sst.npy')
n_time, n_lat, n_lon = target_sst.shape
sea_mask = np.zeros((n_lat, n_lon), dtype=bool)
for i in range(n_lat):
    for j in range(n_lon):
        sea_mask[i,j] = np.all(np.isfinite(target_sst[:, i, j]))

# For a sample cell, show the hot pattern
for i in range(n_lat):
    for j in range(n_lon):
        if sea_mask[i,j]:
            hot = hot_mask[:, i, j]
            if hot.sum() > 0:
                # Find runs
                runs = []
                start = None
                for t in range(n_time):
                    if hot[t]:
                        if start is None:
                            start = t
                    else:
                        if start is not None:
                            runs.append((start, t-1))
                            start = None
                if start is not None:
                    runs.append((start, n_time-1))
                
                # Show runs >= 3 days
                long_runs = [r for r in runs if r[1]-r[0]+1 >= 3]
                if long_runs:
                    print(f"Cell ({i},{j}): hot runs = {runs}")
                    print(f"  MHW mask: {mhw_mask_old[:, i, j]}")
                    break
