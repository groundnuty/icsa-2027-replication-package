
import fsspec
import xarray as xr
fs = fsspec.filesystem('onedata')

# Let's look at the s2z file
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')
print(ds)
print("\n--- Variables ---")
for var in ds.data_vars:
    print(f"{var}: {ds[var].dims} {ds[var].dtype}")
print("\n--- Coords ---")
for coord in ds.coords:
    print(f"{coord}: {ds[coord].values[:5]}... {ds[coord].dtype} {len(ds[coord])}")
