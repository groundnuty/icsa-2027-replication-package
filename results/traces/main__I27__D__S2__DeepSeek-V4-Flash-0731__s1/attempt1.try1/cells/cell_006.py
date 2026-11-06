
import xarray as xr
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')

# Select region
sst_region = ds.analysed_sst.sel(latitude=slice(57.83, 59.03), longitude=slice(17.41, 18.61))

# Load data
baseline = sst_region.sel(time=slice('1991-12-27', '2003-01-05'))
target = sst_region.sel(time=slice('2008-06-01', '2008-08-31'))

baseline_arr = baseline.values.astype(np.float64)  # (nt, nlat, nlon)
target_arr = target.values.astype(np.float64)      # (92, nlat, nlon)
baseline_time = pd.to_datetime(baseline.time.values)
target_time = pd.to_datetime(target.time.values)

nlat, nlon = target_arr.shape[1], target_arr.shape[2]
print("shapes:", baseline_arr.shape, target_arr.shape, nlat, nlon)

# Save data for later use
np.save('/work/baseline_arr.npy', baseline_arr)
np.save('/work/target_arr.npy', target_arr)
np.save('/work/baseline_time.npy', baseline_time.values.astype('datetime64[D]'))
np.save('/work/target_time.npy', target_time.values.astype('datetime64[D]'))
np.save('/work/lat.npy', sst_region.latitude.values)
np.save('/work/lon.npy', sst_region.longitude.values)
print("saved")
