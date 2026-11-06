import xarray as xr
import fsspec
import os

# First, download and examine one file to understand the structure
fs = fsspec.filesystem('onedata')
remote_path = '/icsa2027_data_20261101T090944Z/s1z/sst_19820101.nc'
local_path = '/work/sst_19820101.nc'

# Download a sample file
fs.get(remote_path, local_path)

# Open with xarray
ds = xr.open_dataset(local_path, engine='h5netcdf')
print("Dataset dimensions:", dict(ds.dims))
print("Dataset variables:", list(ds.data_vars.keys()))
print("Coordinates:")
for coord in ds.coords:
    print(f"  {coord}: {ds.coords[coord].shape}")
    
# Print some coordinate values
print("\nLatitude range:", ds.latitude.min().values, "to", ds.latitude.max().values)
print("Longitude range:", ds.longitude.min().values, "to", ds.longitude.max().values)
print("Time:", ds.time.values[:5])  # Show first 5 time points

# Check the SST data shape
print("SST data shape:", ds.analysed_sst.shape)
print("Sample SST values:", ds.analysed_sst.values.flatten()[:10])

# Close the dataset
ds.close()