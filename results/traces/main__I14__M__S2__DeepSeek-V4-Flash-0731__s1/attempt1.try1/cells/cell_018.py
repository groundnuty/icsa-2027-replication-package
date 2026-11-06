
import numpy as np
import pandas as pd

sst_data = np.load('/tmp/sst_data.npy')
times_int = np.load('/tmp/times.npy')
times = pd.to_datetime(times_int, unit='D')

thresholds = np.load('/tmp/thresholds.npy')
climatology = np.load('/tmp/climatology.npy')

# Sea cells
times_np = times.values
target_mask = (times_np >= np.datetime64('2015-06-01')) & (times_np <= np.datetime64('2015-08-31'))
target_indices = np.where(target_mask)[0]
target_sst = sst_data[target_indices, :, :]
finite_all = np.all(np.isfinite(target_sst), axis=0)
sea_cells = np.argwhere(finite_all)

# Check NaN in raw thresholds for sea cells
nan_thresh = np.isnan(thresholds[:, sea_cells[:, 0], sea_cells[:, 1]]).sum()
nan_clim = np.isnan(climatology[:, sea_cells[:, 0], sea_cells[:, 1]]).sum()
print("NaN in raw thresholds for sea cells:", nan_thresh)
print("NaN in raw climatology for sea cells:", nan_clim)

# Check which days have NaN
for d in range(1, 367):
    nan_cells = 0
    for lat, lon in sea_cells:
        if np.isnan(thresholds[d-1, lat, lon]):
            nan_cells += 1
    if nan_cells > 0:
        print(f"  Day {d}: {nan_cells} sea cells with NaN threshold")
