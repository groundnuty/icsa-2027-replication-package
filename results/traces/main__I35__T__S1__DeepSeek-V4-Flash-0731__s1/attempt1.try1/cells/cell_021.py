
import numpy as np

baseline_sst = np.load('/tmp/baseline_sst.npy')
target_sst = np.load('/tmp/target_sst.npy')

# Check if some cells have all-NaN in baseline
n_time, n_lat, n_lon = target_sst.shape
sea_mask = np.zeros((n_lat, n_lon), dtype=bool)
for i in range(n_lat):
    for j in range(n_lon):
        sea_mask[i,j] = np.all(np.isfinite(target_sst[:, i, j]))

# Check how many cells have any finite values in baseline
for i in range(n_lat):
    for j in range(n_lon):
        if sea_mask[i,j]:
            n_finite = np.sum(np.isfinite(baseline_sst[:, i, j]))
            if n_finite < 100:
                print(f"Cell ({i},{j}) is sea but has only {n_finite} finite baseline values")
