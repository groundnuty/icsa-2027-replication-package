
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

# Find cells where MHWs are joined (two runs >= 5 separated by 1-2 non-hot days)
joined_examples = []
for i in range(60):
    for j in range(60):
        if not sea_mask[i, j]:
            continue
        cell_hot = hot[i, j, :]
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
        
        mhw_indices = [k for k, (s, e) in enumerate(runs) if e - s + 1 >= 5]
        if len(mhw_indices) >= 2:
            for idx in range(len(mhw_indices)-1):
                ri1 = mhw_indices[idx]
                ri2 = mhw_indices[idx+1]
                gap = runs[ri2][0] - runs[ri1][1] - 1
                if 1 <= gap <= 2:
                    joined_examples.append((i, j, runs[ri1], runs[ri2], gap))
                    break

print(f"Cells with joined MHWs: {len(joined_examples)}")
for ex in joined_examples[:5]:
    i, j, r1, r2, gap = ex
    print(f"  Cell ({i},{j}): MHW {r1} and MHW {r2}, gap={gap} days")
    print(f"    Dates: {target_dates[r1[0]]} to {target_dates[r1[1]]} and {target_dates[r2[0]]} to {target_dates[r2[1]]}")
