
import fsspec
import xarray as xr
fs = fsspec.filesystem('onedata')
# Open one s1z file to understand its structure
f = fs.open('icsa2027_data_20261101T090944Z/s1z/sst_19820101.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')
print(ds)
print(ds.dims)
print(ds.coords)
print(ds.data_vars)
