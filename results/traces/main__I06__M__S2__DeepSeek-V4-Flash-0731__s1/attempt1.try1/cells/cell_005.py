
import xarray as xr
import numpy as np
import pandas as pd
path = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
ds = xr.open_dataset(path, engine="h5netcdf")

# Time indices for baseline + windows
start_baseline = np.datetime64('1991-12-27')
end_baseline = np.datetime64('2003-01-05')

# Target period
start_target = np.datetime64('2012-06-01')
end_target = np.datetime64('2012-08-31')

t = ds.time.values
mask_baseline = (t >= start_baseline) & (t <= end_baseline)
mask_target = (t >= start_target) & (t <= end_target)

print("Baseline days:", mask_baseline.sum())
print("Target days:", mask_target.sum())

# Get indices
baseline_idx = np.where(mask_baseline)[0]
target_idx = np.where(mask_target)[0]
print("Baseline index range:", baseline_idx[0], baseline_idx[-1])
print("Target index range:", target_idx[0], target_idx[-1])
print("Target dates:", np.datetime_as_string(t[target_idx], unit='D')[:5], "...", np.datetime_as_string(t[target_idx], unit='D')[-5:])
