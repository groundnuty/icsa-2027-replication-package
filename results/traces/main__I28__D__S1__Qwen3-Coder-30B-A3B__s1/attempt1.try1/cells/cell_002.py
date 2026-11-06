import xarray as xr
import numpy as np
import os

# Create output directory
os.makedirs('output', exist_ok=True)

# Download and examine a sample file
fs = fsspec.filesystem('onedata')
sample_file = '/icsa2027_data_20261101T090944Z/s1z/sst_19820101.nc'
local_sample = '/work/sample.nc'
fs.get(sample_file, local_sample)

# Open with xarray
ds = xr.open_dataset(local_sample, engine='h5netcdf')
print("Sample dataset structure:")
print(ds)
print("\nVariables:", list(ds.data_vars.keys()))
print("\nCoordinates:")
for coord in ds.coords:
    print(f"  {coord}: {ds[coord].shape}")
    
# Check the SST data
print(f"\nSST data shape: {ds['analysed_sst'].shape}")
print(f"SST data type: {ds['analysed_sst'].dtype}")
print(f"SST data range: {ds['analysed_sst'].min().values} to {ds['analysed_sst'].max().values}")

# Close the dataset
ds.close()