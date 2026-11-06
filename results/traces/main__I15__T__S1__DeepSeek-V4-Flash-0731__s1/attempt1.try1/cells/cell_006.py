import xarray as xr
import fsspec

fs = fsspec.filesystem('onedata')
# Open the s2 file
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')
print(ds)
print("\nVariables:")
for var in ds.variables:
    print(f"  {var}: {ds[var].dims}, dtype={ds[var].dtype}")
    if var == 'sst':
        print(f"    shape: {ds[var].shape}")
        print(f"    attrs: {dict(ds[var].attrs)}")
print("\nCoords:")
for c in ds.coords:
    print(f"  {c}: {ds[c].values}")
    if len(ds[c].values) > 10:
        print(f"    (first 10): {ds[c].values[:10]}")
        print(f"    (last 10): {ds[c].values[-10:]}")
