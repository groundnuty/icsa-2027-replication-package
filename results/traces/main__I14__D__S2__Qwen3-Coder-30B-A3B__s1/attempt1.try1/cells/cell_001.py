import fsspec
import xarray as xr
import numpy as np

# Create filesystem
fs = fsspec.filesystem('onedata')

# Download the file
remote_path = '/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
local_path = '/work/sst_s2.nc'
fs.get(remote_path, local_path)

# Open with xarray
ds = xr.open_dataset(local_path, engine='h5netcdf')
print("Dataset dimensions:", ds.dims)
print("Dataset variables:", list(ds.data_vars.keys()))
print("Coordinates:")
for coord in ds.coords:
    print(f"  {coord}: {ds[coord].shape}")
    
# Check some sample data
print("\nSample SST data:")
print(ds['sst'].isel(time=0, lat=0, lon=0))