import os
import xarray as xr
import numpy as np

os.makedirs('output', exist_ok=True)

# Examine the dataset structure more closely
ds = xr.open_dataset('/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', engine='h5netcdf')

print("Dataset coordinates:")
print(f"time: {ds.time.min().values} to {ds.time.max().values}")
print(f"latitude range: {ds.latitude.min().values} to {ds.latitude.max().values}")
print(f"longitude range: {ds.longitude.min().values} to {ds.longitude.max().values}")

print("\nData variables:")
print(ds.data_vars)

# Check the actual data shape
print(f"\nAnalysed SST shape: {ds.analysed_sst.shape}")

# Let's look at a small sample of the data to understand the format
print(f"\nSample SST data (first few values):")
print(ds.analysed_sst.isel(time=0, latitude=0, longitude=0).values)