
import numpy as np

# hot: (92, n_sea) boolean array
# For each cell, find runs of hot days, join those separated by 1-2 non-hot days

n_days, n_sea = hot.shape

# Initialize per-cell MHW mask
cell_mhw = np.zeros_like(hot, dtype=bool)

for c in range(n_sea):
    h = hot[:, c]
    
    # Find runs of hot days
    # First, identify runs of consecutive hot days
    runs = []  # list of (start, end) where end is inclusive
    i = 0
    while i < n_days:
        if h[i]:
            start = i
            while i < n_days and h[i]:
                i += 1
            end = i - 1
            runs.append((start, end))
        else:
            i += 1
    
    if not runs:
        continue
    
    # Join runs separated by 1 or 2 non-hot days
    joined = [runs[0]]
    for r in runs[1:]:
        prev = joined[-1]
        gap = r[0] - prev[1] - 1  # number of non-hot days between
        if gap <= 2:
            # Join
            joined[-1] = (prev[0], r[1])
        else:
            joined.append(r)
    
    # Keep only runs of at least 5 days (after joining)
    for start, end in joined:
        if end - start + 1 >= 5:
            cell_mhw[start:end+1, c] = True

print("Per-cell MHW days:", cell_mhw.sum())
print("Per-cell MHW days per cell: min={}, max={}, mean={:.1f}".format(
    cell_mhw.sum(axis=0).min(), cell_mhw.sum(axis=0).max(), cell_mhw.sum(axis=0).mean()))
print("Cells with at least one MHW:", (cell_mhw.sum(axis=0) > 0).sum())

# Save per-cell MHW mask
np.save('/work/cell_mhw.npy', cell_mhw)
