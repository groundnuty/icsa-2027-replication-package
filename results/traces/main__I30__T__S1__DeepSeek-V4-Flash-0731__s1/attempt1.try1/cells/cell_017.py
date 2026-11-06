
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import xarray as xr
import fsspec

# Load the data
fs = fsspec.filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')

lat_min, lat_max = 58.69, 59.89
lon_min, lon_max = 18.69, 19.89

baseline_slice = ds.sel(time=slice('1991-12-27', '2003-01-05'), 
                         latitude=slice(lat_min, lat_max), 
                         longitude=slice(lon_min, lon_max))
target_slice = ds.sel(time=slice('2010-06-01', '2010-08-31'),
                      latitude=slice(lat_min, lat_max),
                      longitude=slice(lon_min, lon_max))

baseline_data = baseline_slice.analysed_sst.values
target_data = target_slice.analysed_sst.values

baseline_times = pd.to_datetime(baseline_slice.time.values)
target_times = pd.to_datetime(target_slice.time.values)
lat_vals = baseline_slice.latitude.values
lon_vals = baseline_slice.longitude.values

print("Data loaded.")
print("baseline shape:", baseline_data.shape)
print("target shape:", target_data.shape)
print("baseline times:", baseline_times[0], "to", baseline_times[-1], "n=", len(baseline_times))
print("target times:", target_times[0], "to", target_times[-1], "n=", len(target_times))

# Save key data to disk for later use
np.save('/tmp/baseline_data.npy', baseline_data)
np.save('/tmp/target_data.npy', target_data)
np.save('/tmp/baseline_times.npy', baseline_times.values.astype('datetime64[s]'))
np.save('/tmp/target_times.npy', target_times.values.astype('datetime64[s]'))
np.save('/tmp/lat_vals.npy', lat_vals)
np.save('/tmp/lon_vals.npy', lon_vals)

print("Saved.")
