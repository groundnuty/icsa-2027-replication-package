
import xarray as xr
import fsspec

fs = fsspec.filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s1z/sst_19820101.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')
print(ds)
print("\n--- Variables ---")
for var in ds.variables:
    print(f"{var}: {ds[var].dims} {ds[var].dtype} shape={ds[var].shape}")
print("\n--- Coordinates ---")
print("time:", ds.time.values)
print("latitude:", ds.latitude.values[:10])
print("longitude:", ds.longitude.values[:10])
