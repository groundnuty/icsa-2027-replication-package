
import fsspec
import xarray as xr
import numpy as np

fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'

# Open a single file to understand structure
f = fs.open(f'{base}/sst_20120601.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')
print(ds)
print("\nCoordinates:", ds.coords)
print("\nData vars:", list(ds.data_vars.keys()))
print("\nDims:", dict(ds.sizes))
