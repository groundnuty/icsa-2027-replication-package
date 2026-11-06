
import xarray as xr
import numpy as np
from datetime import date, timedelta
import pandas as pd

ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
region = ds.sel(latitude=slice(55.67, 56.87), longitude=slice(16.45, 17.65))

target = region.sel(time=slice('2021-06-01', '2021-08-31'))
target_sst = target.analysed_sst.values.astype(np.float64)
target_dates = pd.to_datetime(target.time.values).date

baseline_ext = region.sel(time=slice('1991-12-27', '2003-01-05'))
baseline_sst = baseline_ext.analysed_sst.values.astype(np.float64)
baseline_dates = pd.to_datetime(baseline_ext.time.values).date

print("Target dates:", target_dates[0], "to", target_dates[-1], "count:", len(target_dates))
print("Baseline ext dates:", baseline_dates[0], "to", baseline_dates[-1], "count:", len(baseline_dates))

# Sea cells
sea_mask = np.all(np.isfinite(target_sst), axis=0)
print("Sea cells:", sea_mask.sum())
