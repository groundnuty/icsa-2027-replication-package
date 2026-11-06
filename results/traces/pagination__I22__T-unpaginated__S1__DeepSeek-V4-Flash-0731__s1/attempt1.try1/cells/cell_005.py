
import fsspec
import xarray as xr
import numpy as np

fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'

# Check a few different dates for consistency of the grid
for f in ['sst_19920101.nc', 'sst_19950715.nc', 'sst_20021231.nc', 'sst_20040601.nc', 'sst_20040831.nc']:
    with fs.open(f'{base}/{f}', 'rb') as fh:
        ds = xr.open_dataset(fh, engine='h5netcdf')
        lat = ds['latitude'].values
        lon = ds['longitude'].values
        print(f, 'lat', lat[0], lat[-1], 'lon', lon[0], lon[-1], 'lat len', len(lat), 'lon len', len(lon))
