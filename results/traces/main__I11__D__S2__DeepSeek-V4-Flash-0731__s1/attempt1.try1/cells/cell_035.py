
import numpy as np
import xarray as xr
import pandas as pd

# Check cell (0,0) hot pattern
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

# Compute hot for cell (0,0)
hot_cell = np.zeros(n_time, dtype=bool)
for t in range(n_time):
    doy = target_doy[t]
    hot_cell[t] = (target_sst[t, 0, 0] >= threshold_smooth[doy-1, 0, 0]) & sea_mask[0, 0]

print("Hot pattern for cell (0,0):", hot_cell.astype(int))
print("Target dates:", [str(d) for d in target_dates])

# Find runs
runs = []
t = 0
while t < n_time:
    if hot_cell[t]:
        start = t
        while t < n_time and hot_cell[t]:
            t += 1
        runs.append((start, t-1))
    else:
        t += 1
print("Runs:", runs)
for s, e in runs:
    print(f"  Run {s}-{e}: length={e-s+1}, dates={target_dates[s]} to {target_dates[e]}")
