
import numpy as np

hot_mask = np.load('/tmp/hot_mask.npy')
old_mask = np.load('/tmp/mhw_mask.npy')
new_mask = np.load('/tmp/mhw_mask_corrected.npy')

target_sst = np.load('/tmp/target_sst.npy')
n_time, n_lat, n_lon = target_sst.shape
sea_mask = np.zeros((n_lat, n_lon), dtype=bool)
for i in range(n_lat):
    for j in range(n_lon):
        sea_mask[i,j] = np.all(np.isfinite(target_sst[:, i, j]))

# Find cells where old != new
diff_cells = np.argwhere((old_mask != new_mask).any(axis=0))
print(f"Cells with differences: {len(diff_cells)}")

# Show a few examples
for idx in diff_cells[:5]:
    i, j = idx
    hot = hot_mask[:, i, j]
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
    
    print(f"\nCell ({i},{j}):")
    print(f"  Hot runs: {runs}")
    print(f"  Hot days: {np.where(hot)[0]}")
    print(f"  Old MHW days: {np.where(old_mask[:, i, j] > 0)[0]}")
    print(f"  New MHW days: {np.where(new_mask[:, i, j] > 0)[0]}")
