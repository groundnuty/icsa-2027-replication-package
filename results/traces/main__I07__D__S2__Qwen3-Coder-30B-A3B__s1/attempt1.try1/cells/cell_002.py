import fsspec
import xarray as xr
import numpy as np

# Setup filesystem
fs = fsspec.filesystem('onedata')

# Download the file
remote_path = '/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
local_path = '/work/sst_s2.nc'
fs.get(remote_path, local_path)

# Open with xarray
ds = xr.open_dataset(local_path, engine='h5netcdf')
print("Dataset coordinates:")
print(ds.coords)
print("\nDataset variables:")
print(ds.data_vars)
print("\nAnalysed SST variable details:")
print(ds['analysed_sst'])

# Check the range of data
print(f"\nTime range: {ds.time.min().values} to {ds.time.max().values}")
print(f"Latitude range: {ds.latitude.min().values} to {ds.latitude.max().values}")
print(f"Longitude range: {ds.longitude.min().values} to {ds.longitude.max().values}")

# Let's look at some sample data
print("\nSample data shape:", ds['analysed_sst'].shape)
print("Sample data (first few values):")
print(ds['analysed_sst'][:3, :3, :3].values)