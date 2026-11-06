
import numpy as np

# hot: (60, 60, n_time) boolean array
# Find per-cell MHWs
n_time = hot.shape[2]

# For each cell, find runs of hot days
# A per-cell MHW is a run of at least 5 consecutive hot days
# Runs separated by 1 or 2 non-hot days are joined

# mhw_mask[cell_i, cell_j, t] = True if cell is inside a per-cell MHW on day t
mhw_mask = np.zeros((60, 60, n_time), dtype=bool)

# Also track per-cell MHW intervals for regional event detection
# We need to know which cells are in an MHW on each day

for i in range(60):
    for j in range(60):
        if not sea_mask[i, j]:
            continue
        cell_hot = hot[i, j, :]
        
        # Find initial hot runs
        # runs: list of (start, end) for runs of consecutive hot days
        runs = []
        t = 0
        while t < n_time:
            if cell_hot[t]:
                start = t
                while t < n_time and cell_hot[t]:
                    t += 1
                end = t - 1
                runs.append((start, end))
            else:
                t += 1
        
        # Join runs separated by 1 or 2 non-hot days
        if len(runs) <= 1:
            joined_runs = runs
        else:
            joined_runs = [runs[0]]
            for r in runs[1:]:
                prev_end = joined_runs[-1][1]
                gap = r[0] - prev_end - 1
                if gap <= 2:  # separated by 1 or 2 non-hot days
                    # Join
                    joined_runs[-1] = (joined_runs[-1][0], r[1])
                else:
                    joined_runs.append(r)
        
        # Keep only runs of length >= 5
        for start, end in joined_runs:
            if end - start + 1 >= 5:
                mhw_mask[i, j, start:end+1] = True

print("MHW mask count:", mhw_mask.sum())
print("MHW per time step:", mhw_mask.sum(axis=(0,1)))
