
import fsspec
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'

# Check the s2z file which seems to be a combined file
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
import xarray as xr
ds = xr.open_dataset(f, engine='h5netcdf')
print(ds)
print("\nTime range:")
if 'time' in ds.coords:
    t = ds.time.values
    print(f"  {t[0]} to {t[-1]}, {len(t)} times")
