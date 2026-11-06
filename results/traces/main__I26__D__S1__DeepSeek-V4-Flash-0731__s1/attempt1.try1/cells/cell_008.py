import fsspec
fs = fsspec.filesystem('onedata')
# Download a sample file
fs.get('icsa2027_data_20261101T090944Z/s1z/sst_19820601.nc', '/work/sst_19820601.nc')
print("Downloaded")

import xarray as xr
ds = xr.open_dataset('/work/sst_19820601.nc', engine='h5netcdf')
print(ds)
print("\nData vars:", list(ds.data_vars))
print("\nCoords:", list(ds.coords))
