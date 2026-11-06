
import fsspec
fs = fsspec.filesystem('onedata')
# Get the s2z file
fs.get('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', '/work/sst_s2.nc')
import xarray as xr
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
print(ds)
print("\nTime range:")
if 'time' in ds.coords:
    print(ds.time.values[:5])
    print(ds.time.values[-5:])
    print(f"Size: {len(ds.time)}")
