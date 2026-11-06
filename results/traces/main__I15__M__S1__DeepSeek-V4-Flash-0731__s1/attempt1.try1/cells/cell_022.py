import numpy as np

# Load hot days: (n_sea, n_target)
hot = np.load('/tmp/hot.npy')
n_sea, n_target = hot.shape

# Find per-cell MHWs
# For each cell, find runs of hot days
# Then join runs separated by 1-2 non-hot days

# For each cell, create a boolean array indicating if the cell is in a per-cell MHW on each day
# Step 1: Find runs of at least 5 consecutive hot days
# Step 2: Join runs separated by 1 or 2 non-hot days

# For each cell:
# - Identify hot runs (consecutive hot days)
# - Keep runs with length >= 5
# - Join runs separated by <= 2 non-hot days

in_mhw = np.zeros((n_sea, n_target), dtype=bool)

for c in range(n_sea):
    h = hot[c]  # (n_target,)
    
    # Find consecutive runs of hot days
    runs = []
    i = 0
    while i < n_target:
        if h[i]:
            start = i
            while i < n_target and h[i]:
                i += 1
            end = i - 1
            runs.append((start, end))
        else:
            i += 1
    
    # Keep runs with length >= 5
    long_runs = [(s, e) for (s, e) in runs if (e - s + 1) >= 5]
    
    if not long_runs:
        continue
    
    # Join runs separated by 1 or 2 non-hot days
    joined_runs = []
    current = long_runs[0]
    for next_run in long_runs[1:]:
        gap = next_run[0] - current[1] - 1
        if gap <= 2:
            # Join
            current = (current[0], next_run[1])
        else:
            joined_runs.append(current)
            current = next_run
    joined_runs.append(current)
    
    # Mark days in MHWs
    for (s, e) in joined_runs:
        in_mhw[c, s:e+1] = True

print(f"Cells with MHWs: {(in_mhw.any(axis=1)).sum()}")
print(f"Days in MHWs: {in_mhw.sum()}")
np.save('/tmp/in_mhw.npy', in_mhw)
