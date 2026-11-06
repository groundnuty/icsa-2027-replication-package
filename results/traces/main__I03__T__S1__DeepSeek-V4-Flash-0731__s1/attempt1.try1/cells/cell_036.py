
import fsspec
import xarray as xr
fs = fsspec.filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s1z/sst_19820101.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')
print(ds)
print("\nVariables:")
for var in ds.data_vars:
    print(f"  {var}: {ds[var].dims} {ds[var].dtype}")
print("\nCoords:")
for coord in ds.coords:
    print(f"  {coord}: {ds[coord].values[:3]}... {ds[coord].dtype}")
print("\nAttrs:")
print(ds.attrs)
