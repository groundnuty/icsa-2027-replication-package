
import fsspec
fs = fsspec.filesystem('onedata')
# Download one s1z file to check
fs.get('icsa2027_data_20261101T090944Z/s1z/sst_19820101.nc', '/work/sst_test.nc')
import xarray as xr
ds = xr.open_dataset('/work/sst_test.nc', engine='h5netcdf')
print(ds)
print("\nCoordinates:")
print(ds.coords)
print("\nVariables:")
for var in ds.data_vars:
    print(f"  {var}: {ds[var].dims}, {ds[var].dtype}")
    print(f"    attrs: {dict(ds[var].attrs)}")
