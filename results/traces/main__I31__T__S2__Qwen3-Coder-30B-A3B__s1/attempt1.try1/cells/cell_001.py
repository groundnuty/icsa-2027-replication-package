import fsspec
import xarray as xr
import numpy as np

# Set up the filesystem
fs = fsspec.filesystem('onedata')

# Open the dataset
with fs.open('/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    
print("Dataset dimensions:", ds.dims)
print("\nDataset coordinates:")
for coord in ds.coords:
    print(f"  {coord}: {ds[coord].values[:5] if len(ds[coord]) > 5 else ds[coord].values}")

print("\nDataset variables:")
for var in ds.data_vars:
    print(f"  {var}: {ds[var].dims} - {ds[var].shape}")
    
# Check the time range
print(f"\nTime range: {ds.time.min().values} to {ds.time.max().values}")