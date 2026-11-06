
import numpy as np
from datetime import date
import xarray as xr
import pandas as pd

# Reload everything
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
region = ds.sel(latitude=slice(55.67, 56.87), longitude=slice(16.45, 17.65))

target = region.sel(time=slice('2021-06-01', '2021-08-31'))
target_sst = target.analysed_sst.values.astype(np.float64)
target_dates = pd.to_datetime(target.time.values).date

threshold_smooth = np.load('/work/threshold_smooth.npy')
sea_mask = np.load('/work/sea_mask.npy')

# Day of year mapping
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

print("Hot computed")

# Find per-cell MHWs
mhw_mask = np.zeros((60, 60, n_time), dtype=bool)

for i in range(60):
    for j in range(60):
        if not sea_mask[i, j]:
            continue
        cell_hot = hot[i, j, :]
        
        # Find initial hot runs
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
                if gap <= 2:
                    joined_runs[-1] = (joined_runs[-1][0], r[1])
                else:
                    joined_runs.append(r)
        
        # Keep runs of length >= 5
        for start, end in joined_runs:
            if end - start + 1 >= 5:
                mhw_mask[i, j, start:end+1] = True

print("MHW mask count:", mhw_mask.sum())
print("MHW per time step:", mhw_mask.sum(axis=(0,1)))

# Save
np.save('/work/mhw_mask.npy', mhw_mask)
np.save('/work/hot.npy', hot)
