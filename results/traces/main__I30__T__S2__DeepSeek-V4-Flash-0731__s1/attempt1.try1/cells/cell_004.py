
import fsspec
import xarray as xr
fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'

with fs.open(path, 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    # Check lat/lon ranges
    print("Lat range:", ds.latitude.min().values, ds.latitude.max().values)
    print("Lon range:", ds.longitude.min().values, ds.longitude.max().values)
    print("Time range:", ds.time.min().values, ds.time.max().values)
    # Check time step
    print("Time first 5:", ds.time.values[:5])
    print("Time last 5:", ds.time.values[-5:])
