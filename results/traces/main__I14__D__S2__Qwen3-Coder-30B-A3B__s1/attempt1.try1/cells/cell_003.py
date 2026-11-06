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

# Check the analysed_sst variable
print("\nAnalysed SST data shape:", ds['analysed_sst'].shape)

# Check coordinate ranges
print("\nLatitude range:", ds['latitude'].min().values, "to", ds['latitude'].max().values)
print("Longitude range:", ds['longitude'].min().values, "to", ds['longitude'].max().values)
print("Time range:", ds['time'].min().values, "to", ds['time'].max().values)

# Check some sample data points
print("\nSample values (first few time steps at a specific location):")
sample_lat_idx = 100
sample_lon_idx = 200
print(ds['analysed_sst'].isel(time=slice(0, 5), latitude=sample_lat_idx, longitude=sample_lon_idx).values)