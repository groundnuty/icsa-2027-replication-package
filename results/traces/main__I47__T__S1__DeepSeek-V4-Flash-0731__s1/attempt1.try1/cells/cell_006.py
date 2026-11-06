
import fsspec
fs = fsspec.filesystem('onedata')
# Let's look at s2 file
import xarray as xr
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')
print(ds)
