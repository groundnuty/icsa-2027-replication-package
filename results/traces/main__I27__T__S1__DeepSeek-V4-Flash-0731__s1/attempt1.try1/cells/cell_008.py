
import xarray as xr
import fsspec

fs = fsspec.filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')
print(ds)
print("\n--- Variables ---")
for var in ds.variables:
    print(f"{var}: {ds[var].dims} {ds[var].dtype}")
print("\n--- Time range ---")
print(ds.time.values[:5])
print(ds.time.values[-5:])
print("Number of time steps:", len(ds.time))
