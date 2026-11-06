
import xarray as xr
import numpy as np
import pandas as pd

path = '/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
ds = xr.open_dataset(path, engine='h5netcdf')

time = ds.time.values
# Find indices
time_dt = pd.DatetimeIndex(time)

# Baseline window: 1991-12-27 to 2003-01-05
base_start = pd.Timestamp('1991-12-27')
base_end = pd.Timestamp('2003-01-05')
tgt_start = pd.Timestamp('2007-06-01')
tgt_end = pd.Timestamp('2007-08-31')

base_mask = (time_dt >= base_start) & (time_dt <= base_end)
tgt_mask = (time_dt >= tgt_start) & (time_dt <= tgt_end)

base_idx = np.where(base_mask)[0]
tgt_idx = np.where(tgt_mask)[0]

print(f"Baseline time indices: {base_idx[0]} to {base_idx[-1]}, count={len(base_idx)}")
print(f"Baseline time range: {time[base_idx[0]]} to {time[base_idx[-1]]}")
print(f"Target time indices: {tgt_idx[0]} to {tgt_idx[-1]}, count={len(tgt_idx)}")
print(f"Target time range: {time[tgt_idx[0]]} to {time[tgt_idx[-1]]}")

# Check daily spacing
diffs = np.diff(pd.DatetimeIndex(time[base_idx[0]:base_idx[-1]+1]))
print(f"\nMin diff: {diffs.min()}, max diff: {diffs.max()}")
