
import fsspec
fs = fsspec.filesystem('onedata')

# Download the s2z file
fs.get('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', '/work/sst_s2.nc')
print("Downloaded s2 file")

import xarray as xr
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
print(ds)
print("\nVariables:", list(ds.data_vars))
print("\nDims:", dict(ds.dims))
print("\nTime range:", ds.time.values[0], "to", ds.time.values[-1])
print("\nTime size:", len(ds.time))
