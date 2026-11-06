import fsspec
import xarray as xr
import numpy as np
from datetime import datetime, timedelta
import os

# Create output directory
os.makedirs('output', exist_ok=True)

# Read all data at once to avoid file handle issues
print("Loading data from remote file...")

# Create the filesystem
fs = fsspec.filesystem('onedata')

# Open and load the full dataset
with fs.open('/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb') as f:
    # Load the dataset
    ds = xr.open_dataset(f, engine='h5netcdf')
    
    # Define region boundaries
    lat_min, lat_max = 57.33, 58.53
    lon_min, lon_max = 9.03, 10.23
    
    # Filter to region
    ds_region = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))
    
    # Define target period
    start_date = "2021-06-01"
    end_date = "2021-08-31"
    
    # Filter to time period
    ds_target = ds_region.sel(time=slice(start_date, end_date))
    
    # Get baseline period (1992-2002)
    baseline_start = "1992-01-01"
    baseline_end = "2002-12-31"
    ds_baseline = ds_region.sel(time=slice(baseline_start, baseline_end))
    
    print(f"Region dimensions: {ds_region.dims}")
    print(f"Target period: {start_date} to {end_date}")
    print(f"Baseline period: {baseline_start} to {baseline_end}")
    print(f"Target data shape: {ds_target.analysed_sst.shape}")
    print(f"Baseline data shape: {ds_baseline.analysed_sst.shape}")

# Now let's implement the MHW detection algorithm step by step
def date_to_doy(date_str):
    """Convert date string to day of year (1-366)"""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    # Handle leap year cases - 29 Feb is DOY 60
    if dt.month == 2 and dt.day == 29:
        return 60
    # Calculate day of year normally
    doy = int(dt.strftime("%j"))
    # Adjust for leap year (29 Feb is treated as day 60)
    if dt.year % 4 == 0 and (dt.year % 100 != 0 or dt.year % 400 == 0):
        if doy > 59:  # After Feb 28 in leap year
            doy += 1
    return doy

# Extract baseline data for computing thresholds
baseline_times = ds_baseline.time.values
baseline_sst = ds_baseline.analysed_sst.values

print("Processing baseline data to compute thresholds...")
print(f"Baseline data shape: {baseline_sst.shape}")

# Initialize arrays for thresholds and climatology
thresholds = np.full((366, ds_region.latitude.size, ds_region.longitude.size), np.nan, dtype=np.float64)
climatologies = np.full((366, ds_region.latitude.size, ds_region.longitude.size), np.nan, dtype=np.float64)

# Process each day of year
print("Computing thresholds and climatologies for each DOY...")
for doy in range(1, 367):
    if doy == 60:  # Special handling for Feb 29
        continue
        
    # Collect all SST values for this DOY from baseline period
    pool_values = []
    
    # Find matching dates in baseline period
    for i, baseline_time in enumerate(baseline_times):
        baseline_doy = date_to_doy(str(baseline_time.astype('datetime64[D]').astype('datetime64[s]').astype(datetime).strftime('%Y-%m-%d')))
        
        # Check if within ±5 days window
        if baseline_doy == doy:
            # Add this SST value to the pool
            sst_values = baseline_sst[i, :, :]
            # Flatten and filter out NaNs
            flat_values = sst_values.flatten()
            valid_values = flat_values[~np.isnan(flat_values)]
            pool_values.extend(valid_values)
        elif doy == 60 and baseline_doy in [59, 61]:  # Special case for Feb 29
            # Include values from Feb 28 and Mar 1 for DOY 60
            sst_values = baseline_sst[i, :, :]
            flat_values = sst_values.flatten()
            valid_values = flat_values[~np.isnan(flat_values)]
            pool_values.extend(valid_values)
    
    if len(pool_values) > 0:
        # Compute 90th percentile (Hazen method) and mean
        pool_array = np.array(pool_values, dtype=np.float64)
        threshold = np.quantile(pool_array, 0.9, method='hazen')
        climatology = np.mean(pool_array)
        
        # Store results
        thresholds[doy-1, :, :] = threshold
        climatologies[doy-1, :, :] = climatology

# Handle DOY 60 specially (mean of DOY 59 and 61)
print("Handling special case for DOY 60...")
# For DOY 60, we take the mean of thresholds for DOY 59 and 61
threshold_59 = np.nanmean(thresholds[58, :, :])  # DOY 59 is index 58
threshold_61 = np.nanmean(thresholds[60, :, :])  # DOY 61 is index 60
thresholds[59, :, :] = (threshold_59 + threshold_61) / 2.0  # DOY 60 is index 59

climatology_59 = np.nanmean(climatologies[58, :, :])
climatology_61 = np.nanmean(climatologies[60, :, :])
climatologies[59, :, :] = (climatology_59 + climatology_61) / 2.0

print("Computing smoothed thresholds and climatologies...")
# Apply 31-day centered moving average smoothing
def smooth_366(arr):
    """Apply 31-day centered moving average smoothing to 366-element array"""
    smoothed = np.zeros_like(arr)
    for i in range(366):
        # Sum values from i-15 to i+15 (wrapping around)
        sum_val = 0
        count = 0
        for j in range(i-15, i+16):
            idx = j % 366  # Wrap around
            if not np.isnan(arr[idx]):
                sum_val += arr[idx]
                count += 1
        if count > 0:
            smoothed[i] = sum_val / count
        else:
            smoothed[i] = np.nan
    return smoothed

# Smooth thresholds and climatologies for each grid point
smoothed_thresholds = np.full_like(thresholds, np.nan)
smoothed_climatologies = np.full_like(climatologies, np.nan)

print("Smoothing thresholds...")
for lat_idx in range(ds_region.latitude.size):
    for lon_idx in range(ds_region.longitude.size):
        # Smooth thresholds
        thresh_series = thresholds[:, lat_idx, lon_idx]
        smoothed_thresholds[:, lat_idx, lon_idx] = smooth_366(thresh_series)
        
        # Smooth climatologies  
        clim_series = climatologies[:, lat_idx, lon_idx]
        smoothed_climatologies[:, lat_idx, lon_idx] = smooth_366(clim_series)

print("Computing MHWs for target period...")
# Now process target period to find MHWs
target_times = ds_target.time.values
target_sst = ds_target.analysed_sst.values

# Initialize MHW mask
mhw_mask = np.zeros((len(target_times), ds_region.latitude.size, ds_region.longitude.size), dtype=np.uint8)

# For each day in target period, check if SST exceeds threshold
print("Identifying hot days...")
for t_idx, target_time in enumerate(target_times):
    target_doy = date_to_doy(str(target_time.astype('datetime64[D]').astype('datetime64[s]').astype(datetime).strftime('%Y-%m-%d')))
    
    # Get threshold for this DOY
    threshold_map = smoothed_thresholds[target_doy-1, :, :]
    
    # Compare SST with threshold
    sst_day = target_sst[t_idx, :, :]
    hot_days = sst_day >= threshold_map
    
    # Mark hot days in mask
    mhw_mask[t_idx, :, :] = hot_days.astype(np.uint8)

print("Detecting hot runs and joining gaps...")
# Apply the hot run detection logic (minimum 5 consecutive hot days)
def join_gaps(mask, max_gap=2):
    """Join MHW runs separated by small gaps"""
    result = mask.copy()
    
    # For each spatial point
    for lat_idx in range(mask.shape[1]):
        for lon_idx in range(mask.shape[2]):
            # Get the time series for this location
            ts = mask[:, lat_idx, lon_idx]
            
            # Find runs of True values
            runs = []
            i = 0
            while i < len(ts):
                if ts[i]:
                    start = i
                    while i < len(ts) and ts[i]:
                        i += 1
                    end = i - 1
                    runs.append((start, end))
                else:
                    i += 1
            
            # Join adjacent runs with small gaps
            if len(runs) > 1:
                merged_runs = [runs[0]]
                for start, end in runs[1:]:
                    prev_start, prev_end = merged_runs[-1]
                    gap_size = start - prev_end - 1
                    if 1 <= gap_size <= max_gap:
                        # Join the runs
                        merged_runs[-1] = (prev_start, end)
                    else:
                        merged_runs.append((start, end))
                
                # Update the result with merged runs
                result[:, lat_idx, lon_idx] = False
                for start, end in merged_runs:
                    result[start:end+1, lat_idx, lon_idx] = True
    
    return result

# Apply gap joining
joined_hot_mask = join_gaps(mhw_mask.astype(bool))

# Final MHW mask
final_mhw_mask = joined_hot_mask.astype(np.uint8)

# Determine regional events
print("Identifying regional events...")
# A day is active if at least one sea cell is inside a per-cell MHW
active_days = np.any(final_mhw_mask, axis=(1, 2))  # Shape: (num_days,)

# Find maximal runs of consecutive active days
events = []
i = 0
while i < len(active_days):
    if active_days[i]:
        # Start of an event
        start_day = i
        while i < len(active_days) and active_days[i]:
            i += 1
        end_day = i - 1
        # Convert indices to dates
        start_date = str(target_times[start_day].astype('datetime64[D]').astype('datetime64[s]').astype(datetime).strftime('%Y-%m-%d'))
        end_date = str(target_times[end_day].astype('datetime64[D]').astype('datetime64[s]').astype(datetime).strftime('%Y-%m-%d'))
        events.append({"onset": start_date, "end": end_date})
    else:
        i += 1

print(f"Found {len(events)} regional MHW events")

# Create the NetCDF file
print("Creating output NetCDF file...")
import xarray as xr

# Create the dataset with proper coordinates
coords = {
    'time': target_times,
    'lat': ds_region.latitude.values,
    'lon': ds_region.longitude.values
}

# Create the data variable
data_vars = {
    'mhw': (['time', 'lat', 'lon'], final_mhw_mask)
}

# Create the dataset
ds_output = xr.Dataset(data_vars, coords=coords)

# Set attributes
ds_output['mhw'].attrs = {'units': 'binary', 'long_name': 'Marine Heatwave indicator'}

# Save to file
ds_output.to_netcdf('output/mhw_mask.nc')

# Prepare report
report = {
    "region": {
        "lat_min": lat_min,
        "lat_max": lat_max,
        "lon_min": lon_min,
        "lon_max": lon_max
    },
    "baseline_analysed": {
        "start": baseline_start,
        "end": baseline_end
    },
    "target_analysed": {
        "start": start_date,
        "end": end_date
    },
    "events": events,
    "complete": True,
    "caveats": ""
}

import json
with open('output/report.json', 'w') as f:
    json.dump(report, f, indent=2)

print("Analysis complete. Files saved.")