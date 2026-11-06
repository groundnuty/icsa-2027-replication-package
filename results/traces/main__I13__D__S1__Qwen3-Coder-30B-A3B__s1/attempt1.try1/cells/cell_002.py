import xarray as xr
import fsspec
import os

# Create work directory if it doesn't exist
os.makedirs('/work', exist_ok=True)

# Download and examine a sample file
fs = fsspec.filesystem('onedata')
remote_path = '/icsa2027_data_20261101T090944Z/s1z/sst_19820101.nc'
local_path = '/work/sst_19820101.nc'

fs.get(remote_path, local_path)
ds = xr.open_dataset(local_path, engine='h5netcdf')
print("Dataset structure:")
print(ds)
print("\nVariables:")
for var in ds.data_vars:
    print(f"  {var}: {ds[var].dims}")
    
print("\nCoordinates:")
for coord in ds.coords:
    print(f"  {coord}: {ds[coord].shape}")

# Close the dataset
ds.close()