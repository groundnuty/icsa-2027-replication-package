
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

print("baseline shape:", baseline_slice.analysed_sst.shape)
print("target shape:", target_slice.analysed_sst.shape)

baseline_data = baseline_slice.analysed_sst.values
target_data = target_slice.analysed_sst.values
print("baseline dtype:", baseline_data.dtype, "shape:", baseline_data.shape)
print("target dtype:", target_data.dtype, "shape:", target_data.shape)
