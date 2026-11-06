
import xarray as xr
import fsspec
import numpy as np

fs = fsspec.filesystem('onedata')

# Try opening the s2z file with region selection
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')

# Select region
lat_min, lat_max = 57.83, 59.03
lon_min, lon_max = 17.41, 18.61

region = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))
print("Region dataset:", region.analysed_sst.shape)
print("Time:", region.time.values[:3], "...", region.time.values[-3:])
