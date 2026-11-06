import xarray as xr
import fsspec
import os

# Create a local directory for our work
os.makedirs('output', exist_ok=True)

# Download and examine one file to understand the structure
fs = fsspec.filesystem('onedata')
remote_path = '/icsa2027_data_20261101T090944Z/s1z/sst_19820101.nc'
local_path = 'sst_19820101.nc'
fs.get(remote_path, local_path)

# Open with xarray
ds = xr.open_dataset(local_path, engine='h5netcdf')
print("Dataset structure:")
print(ds)
print("\nVariables:")
for var in ds.data_vars:
    print(f"  {var}: {ds[var].dims}")
    
print("\nCoordinates:")
for coord in ds.coords:
    print(f"  {coord}: {ds[coord].values[:5] if len(ds[coord]) > 5 else ds[coord].values}")