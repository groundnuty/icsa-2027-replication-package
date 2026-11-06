
import fsspec
import xarray as xr
fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
f = fs.open(path, 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')

# Check the time range
print(ds.time.values[0], ds.time.values[-1])
print(ds.time.shape)

# Check latitude/longitude ranges
print("lat range:", ds.latitude.values[0], ds.latitude.values[-1])
print("lon range:", ds.longitude.values[0], ds.longitude.values[-1])
