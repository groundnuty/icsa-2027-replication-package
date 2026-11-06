
import fsspec
import xarray as xr
fs = fsspec.filesystem('onedata')
# Open the s2 file to see its structure
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')
print(ds)
print(ds.dims)
print(ds.coords)
