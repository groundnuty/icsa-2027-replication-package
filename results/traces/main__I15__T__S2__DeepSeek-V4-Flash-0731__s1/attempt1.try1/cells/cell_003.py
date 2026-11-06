
import fsspec
fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
# Open with xarray
import xarray as xr
f = fs.open(path, 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')
print(ds)
