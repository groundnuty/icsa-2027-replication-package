
import xarray as xr
import fsspec
import numpy as np
import pandas as pd

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

print("baseline time:", baseline_slice.time.values[0], baseline_slice.time.values[-1], len(baseline_slice.time))
print("target time:", target_slice.time.values[0], target_slice.time.values[-1], len(target_slice.time))
print("lat:", baseline_slice.latitude.values[:3], baseline_slice.latitude.values[-3:])
print("lon:", baseline_slice.longitude.values[:3], baseline_slice.longitude.values[-3:])

# Check for NaN / land cells in target
target_nan = np.isnan(target_data)
# Sea cells: finite on every target day
sea_mask = ~np.any(target_nan, axis=0)
print("Sea cells count:", sea_mask.sum(), "of", sea_mask.size)

# Check baseline data
baseline_nan = np.isnan(baseline_data)
print("Baseline NaN fraction:", baseline_nan.mean())

# Check target data range
print("Target data min/max:", np.nanmin(target_data), np.nanmax(target_data))
print("Baseline data min/max:", np.nanmin(baseline_data), np.nanmax(baseline_data))
