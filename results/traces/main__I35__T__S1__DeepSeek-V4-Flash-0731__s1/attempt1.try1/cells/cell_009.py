
import fsspec
import xarray as xr
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'

# Open one file to understand its structure
f = fs.open(f'{base}/sst_20090601.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')
print(ds)
print("\nVariables:")
for var in ds.variables:
    print(f"  {var}: {ds[var].dtype}, shape={ds[var].shape}")
print("\nCoordinates:")
for coord in ds.coords:
    print(f"  {coord}: {ds[coord].values}")
