
import numpy as np
import xarray as xr
import pandas as pd

# Reload
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
region = ds.sel(latitude=slice(55.67, 56.87), longitude=slice(16.45, 17.65))
target = region.sel(time=slice('2021-06-01', '2021-08-31'))
target_sst = target.analysed_sst.values.astype(np.float64)
target_dates = pd.to_datetime(target.time.values).date

threshold_smooth = np.load('/work/threshold_smooth.npy')
sea_mask = np.load('/work/sea_mask.npy')

CUM = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
def doy_from_md(month, day):
    return CUM[month-1] + day

def get_doy(d):
    return doy_from_md(d.month, d.day)

target_doy = np.array([get_doy(d) for d in target_dates])
n_time = len(target_dates)

# Compute hot
hot = np.zeros((60, 60, n_time), dtype=bool)
for t in range(n_time):
    doy = target_doy[t]
    hot[:, :, t] = (target_sst[t] >= threshold_smooth[doy-1]) & sea_mask

# Check for pattern: short run (< 5 hot days) between two longer runs (>= 5)
count_pattern = 0
examples = []
for i in range(60):
    for j in range(60):
        if not sea_mask[i, j]:
            continue
        cell_hot = hot[i, j, :]
        
        # Find all maximal runs
        runs = []
        t = 0
        while t < n_time:
            if cell_hot[t]:
                start = t
                while t < n_time and cell_hot[t]:
                    t += 1
                runs.append((start, t-1))
            else:
                t += 1
        
        # Check for short runs between long runs
        for k in range(1, len(runs)-1):
            prev_len = runs[k-1][1] - runs[k-1][0] + 1
            curr_len = runs[k][1] - runs[k][0] + 1
            next_len = runs[k+1][1] - runs[k+1][0] + 1
            if prev_len >= 5 and curr_len < 5 and next_len >= 5:
                count_pattern += 1
                if len(examples) < 3:
                    examples.append((i, j, runs[k-1], runs[k], runs[k+1]))

print(f"Cells with short run between two long runs: {count_pattern}")
for ex in examples:
    print(f"  Cell ({ex[0]},{ex[1]}): runs {ex[2]}, {ex[3]}, {ex[4]}")
