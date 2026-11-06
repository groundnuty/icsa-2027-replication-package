
import fsspec
import xarray as xr

fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s1z/sst_19820101.nc'
f = fs.open(path, "rb")
ds = xr.open_dataset(f, engine="h5netcdf")
print(ds)
print("\nVariables:")
for var in ds.variables:
    print(f"  {var}: {ds[var].dims} {ds[var].dtype}")
print("\nCoordinates:")
for coord in ds.coords:
    print(f"  {coord}: {ds[coord].values}")
