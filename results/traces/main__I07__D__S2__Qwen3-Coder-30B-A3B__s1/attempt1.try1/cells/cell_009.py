import fsspec
import xarray as xr
import numpy as np
from datetime import datetime, timedelta

# Setup filesystem
fs = fsspec.filesystem('onedata')

# Download the file
remote_path = '/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
local_path = '/work/sst_s2.nc'
fs.get(remote_path, local_path)

# Open with xarray
ds = xr.open_dataset(local_path, engine='h5netcdf')

# Define our region and time period
lat_min, lat_max = 54.45, 55.65
lon_min, lon_max = 16.05, 17.25
start_date = datetime(2021, 6, 1)
end_date = datetime(2021, 8, 31)
baseline_start = datetime(1992, 1, 1)
baseline_end = datetime(2002, 12, 31)

# First let's get the full baseline dataset to ensure we have enough data
baseline_ds = ds.sel(time=slice(baseline_start, baseline_end))

# Now filter to our specific region
baseline_ds = baseline_ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))

# Filter target period
region_ds = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))
region_ds = region_ds.sel(time=slice(start_date, end_date))

print("Debugging threshold computation...")

# Let's look at a sample of baseline data
sample_baseline = baseline_ds['analysed_sst'].isel(time=0)  # First day
print("Sample baseline SST values (first few):")
print(sample_baseline.values.flat[:10])

# Let's also check what the actual temperatures look like
print("Baseline SST statistics:")
baseline_sst_values = baseline_ds['analysed_sst'].values.flatten()
baseline_sst_values = baseline_sst_values[np.isfinite(baseline_sst_values)]
print(f"Min: {np.min(baseline_sst_values):.2f} K")
print(f"Max: {np.max(baseline_sst_values):.2f} K")
print(f"Mean: {np.mean(baseline_sst_values):.2f} K")
print(f"Std: {np.std(baseline_sst_values):.2f} K")

# Let's look at the actual time series for one cell to see if it makes sense
test_lat_idx = 0
test_lon_idx = 0
cell_sst = region_ds['analysed_sst'].isel(latitude=test_lat_idx, longitude=test_lon_idx)
print(f"\nTest cell SST values (first 10 days):")
print(cell_sst.values[:10])

# Check what day of year the first few dates correspond to
print("\nFirst few dates and their DOY:")
for i in range(5):
    date = region_ds.time.values[i]
    doy = date.astype('datetime64[s]').astype('datetime64[ms]').astype(datetime).timetuple().tm_yday
    # Adjust for leap year if needed
    if date.astype('datetime64[s]').astype('datetime64[ms]').astype(datetime).month > 2:
        year = date.astype('datetime64[s]').astype('datetime64[ms]').astype(datetime).year
        if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0):
            if doy >= 60:
                doy += 1
    print(f"Date {date}: DOY {doy}")

# Check the climatology and threshold values for a few days
print("\nFirst 10 climatology and thresholds:")
for i in range(10):
    print(f"DOY {i+1}: Climatology={climatology[i]:.2f} K, Threshold={thresholds[i]:.2f} K")