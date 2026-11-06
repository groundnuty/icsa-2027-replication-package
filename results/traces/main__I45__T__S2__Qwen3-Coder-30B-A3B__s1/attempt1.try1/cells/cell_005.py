import fsspec
import xarray as xr
import numpy as np

# Set up the filesystem
fs = fsspec.filesystem('onedata')

# Open the dataset
ds = xr.open_dataset(fs.open('/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb'), engine='h5netcdf')

# Define the region of interest
lat_min, lat_max = 63.31, 64.51
lon_min, lon_max = 21.31, 22.51

# Select the region
ds_region = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))

# Define baseline period
baseline_start = '1992-01-01'
baseline_end = '2002-12-31'

# Select the baseline period
ds_baseline = ds_region.sel(time=slice(baseline_start, baseline_end))

print(f"Baseline period shape: {ds_baseline.analysed_sst.shape}")
print(f"Baseline time range: {ds_baseline.time.values[0]} to {ds_baseline.time.values[-1]}")

# Now let's examine the data without forcing conversion to numpy immediately
print(f"Sample SST data shape: {ds_baseline.analysed_sst.isel(time=0).shape}")
print("First few values from first time step:")
sample_data = ds_baseline.analysed_sst.isel(time=0)
print(sample_data.values.flat[:10])

# Close the dataset properly
ds.close()