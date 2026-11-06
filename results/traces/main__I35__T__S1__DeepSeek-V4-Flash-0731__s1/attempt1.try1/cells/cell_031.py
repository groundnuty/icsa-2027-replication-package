
import numpy as np

# Load data
hot_mask = np.load('/tmp/hot_mask.npy')  # (92, 60, 60)
target_sst = np.load('/tmp/target_sst.npy')
n_time, n_lat, n_lon = target_sst.shape

# Identify sea cells
sea_mask = np.zeros((n_lat, n_lon), dtype=bool)
for i in range(n_lat):
    for j in range(n_lon):
        sea_mask[i,j] = np.all(np.isfinite(target_sst[:, i, j]))

# Redo MHW detection: first find runs >= 5 hot days, then join MHWs separated by 1-2 non-hot days
mhw_mask = np.zeros((n_time, n_lat, n_lon), dtype=np.uint8)

for i in range(n_lat):
    for j in range(n_lon):
        if not sea_mask[i,j]:
            continue
        hot = hot_mask[:, i, j]
        
        # Find all runs of consecutive hot days
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
        
        # Keep only runs >= 5 days (these are the initial MHWs)
        mhws = [(s, e) for (s, e) in runs if e - s + 1 >= 5]
        
        if not mhws:
            continue
        
        # Join MHWs separated by 1-2 non-hot days
        joined = []
        current_start = mhws[0][0]
        current_end = mhws[0][1]
        
        for k in range(1, len(mhws)):
            gap = mhws[k][0] - current_end - 1
            if gap <= 2:  # gap is 1 or 2 non-hot days
                # Join
                current_end = mhws[k][1]
            else:
                joined.append((current_start, current_end))
                current_start = mhws[k][0]
                current_end = mhws[k][1]
        joined.append((current_start, current_end))
        
        # Mark MHW days
        for (s, e) in joined:
            mhw_mask[s:e+1, i, j] = 1

print(f"MHW mask sum (corrected): {mhw_mask.sum()}")
print(f"MHW mask sum (old): {np.load('/tmp/mhw_mask.npy').sum()}")

# Check differences
old_mask = np.load('/tmp/mhw_mask.npy')
diff = mhw_mask != old_mask
print(f"Cells with differences: {diff.any(axis=0).sum()}")
print(f"Days with differences: {diff.any(axis=(1,2)).sum()}")

# Find where the differences are
diff_indices = np.argwhere(diff.any(axis=(1,2)))
print(f"Time indices with differences: {diff_indices.flatten()}")

# Save corrected mask
np.save('/tmp/mhw_mask_corrected.npy', mhw_mask)
