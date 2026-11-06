import xarray as xr
import numpy as np
from datetime import datetime, timedelta

# Open the dataset
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')

# Define the region of interest
lat_min, lat_max = 54.13, 55.33
lon_min, lon_max = 14.67, 15.87

# Select the region
ds_region = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))

# Define baseline period
baseline_start = '1992-01-01'
baseline_end = '2002-12-31'

# Define target period  
target_start = '2008-06-01'
target_end = '2008-08-31'

# Get baseline data
ds_baseline = ds_region.sel(time=slice(baseline_start, baseline_end))

# Get target data
ds_target = ds_region.sel(time=slice(target_start, target_end))

print("Processing baseline data...")
print(f"Baseline period: {baseline_start} to {baseline_end}")
print(f"Target period: {target_start} to {target_end}")

# Convert dates to day-of-year numbers
def date_to_doy(date_str):
    """Convert YYYY-MM-DD to day-of-year (1-366)"""
    dt = datetime.strptime(date_str, '%Y-%m-%d')
    # Handle leap years properly
    if dt.month > 2 and (dt.year % 4 == 0 and (dt.year % 100 != 0 or dt.year % 400 == 0)):
        # This is a leap year
        if dt.month == 2 and dt.day == 29:
            return 60
        elif dt.month > 2:
            # Adjust for leap year
            return dt.timetuple().tm_yday
        else:
            return dt.timetuple().tm_yday
    else:
        # Non-leap year
        return dt.timetuple().tm_yday

# Create mapping from date to day-of-year for baseline period
baseline_dates = ds_baseline.time.values.astype('datetime64[D]').astype('datetime64[s]').astype(datetime)
baseline_doy = [date_to_doy(dt.strftime('%Y-%m-%d')) for dt in baseline_dates]

# Create a dictionary to store all SST values by day-of-year
doy_pools = {}

# Process each day in baseline period
for i, (date, doy) in enumerate(zip(baseline_dates, baseline_doy)):
    if doy is not None and doy != 60:  # Skip day 60 for now
        if doy not in doy_pools:
            doy_pools[doy] = []
        # Add all SST values from this day
        sst_values = ds_baseline.analysed_sst[i].values
        # Flatten and filter out NaN values
        flat_values = sst_values.flatten()
        valid_values = flat_values[np.isfinite(flat_values)]
        doy_pools[doy].extend(valid_values)

# Handle day 60 separately (it's February 29 in leap years)
# For day 60, we need to collect values from Feb 28 and Mar 1 in all years
feb28_pool = []
mar1_pool = []

for i, (date, doy) in enumerate(zip(baseline_dates, baseline_doy)):
    if doy == 59:  # Feb 28
        sst_values = ds_baseline.analysed_sst[i].values
        flat_values = sst_values.flatten()
        valid_values = flat_values[np.isfinite(flat_values)]
        feb28_pool.extend(valid_values)
    elif doy == 61:  # Mar 1
        sst_values = ds_baseline.analysed_sst[i].values
        flat_values = sst_values.flatten()
        valid_values = flat_values[np.isfinite(flat_values)]
        mar1_pool.extend(valid_values)

# For day 60, we'll use the average of day 59 and day 61
doy_pools[60] = (np.array(feb28_pool) + np.array(mar1_pool)) / 2

print(f"Processed {len(doy_pools)} day-of-year pools")

# Calculate thresholds and climatologies
thresholds = np.full((366, ds_region.latitude.size, ds_region.longitude.size), np.nan)
climatologies = np.full((366, ds_region.latitude.size, ds_region.longitude.size), np.nan)

# Function to compute quantile (Hazen method)
def hazen_quantile(arr, q):
    """Compute quantile using Hazen method (same as MATLAB's quantile default)"""
    if len(arr) == 0:
        return np.nan
    # Sort the array
    sorted_arr = np.sort(arr)
    n = len(sorted_arr)
    # Hazen method: (i - 0.5) / n where i is the rank
    # For 90th percentile: q = 0.9
    idx = (q * (n - 1)) + 0.5
    if idx <= 0:
        return sorted_arr[0]
    elif idx >= n:
        return sorted_arr[-1]
    else:
        lower_idx = int(np.floor(idx - 1))
        upper_idx = int(np.ceil(idx - 1))
        weight = idx - 1 - lower_idx
        return sorted_arr[lower_idx] * (1 - weight) + sorted_arr[upper_idx] * weight

# Compute thresholds and climatologies for each day-of-year
for doy in range(1, 367):
    if doy in doy_pools:
        # Create arrays for this day-of-year
        pool = np.array(doy_pools[doy])
        if len(pool) > 0:
            # Calculate 90th percentile (threshold)
            threshold = hazen_quantile(pool, 0.9)
            
            # Calculate mean (climatology)
            climatology = np.mean(pool)
            
            # Store in arrays
            thresholds[doy-1] = threshold
            climatologies[doy-1] = climatology

# Special handling for day 60 (average of days 59 and 61)
if 59 in doy_pools and 61 in doy_pools:
    avg_threshold = (hazen_quantile(np.array(doy_pools[59]), 0.9) + hazen_quantile(np.array(doy_pools[61]), 0.9)) / 2
    avg_climatology = (np.mean(doy_pools[59]) + np.mean(doy_pools[61])) / 2
    thresholds[59] = avg_threshold  # day 60 is index 59 in 0-based indexing
    climatologies[59] = avg_climatology

print("Thresholds and climatologies calculated")

# Apply smoothing with 31-day centered moving average (wrapping around year)
def smooth_366_array(arr):
    """Apply 31-day centered moving average to 366-element array with wrapping"""
    smoothed = np.zeros_like(arr)
    window_size = 31
    half_window = window_size // 2
    
    for i in range(366):
        # Sum values in the window, wrapping around the year
        total = 0
        count = 0
        for j in range(-half_window, half_window + 1):
            wrapped_index = (i + j) % 366
            if not np.isnan(arr[wrapped_index]):
                total += arr[wrapped_index]
                count += 1
        
        if count > 0:
            smoothed[i] = total / count
        else:
            smoothed[i] = np.nan
            
    return smoothed

# Smooth thresholds and climatologies
smoothed_thresholds = np.full_like(thresholds, np.nan)
smoothed_climatologies = np.full_like(climatologies, np.nan)

print("Smoothing thresholds and climatologies...")
for lat_idx in range(ds_region.latitude.size):
    for lon_idx in range(ds_region.longitude.size):
        thresh = thresholds[:, lat_idx, lon_idx]
        clim = climatologies[:, lat_idx, lon_idx]
        
        if not np.all(np.isnan(thresh)):
            smoothed_thresh = smooth_366_array(thresh)
            smoothed_clim = smooth_366_array(clim)
            
            smoothed_thresholds[:, lat_idx, lon_idx] = smoothed_thresh
            smoothed_climatologies[:, lat_idx, lon_idx] = smoothed_clim

print("Smoothing completed")

# Now find sea cells (cells with finite SST on every day of target period)
print("Identifying sea cells...")
sea_cells = np.full((ds_region.latitude.size, ds_region.longitude.size), False)

# Check which cells have finite SST on all days of target period
target_sst = ds_target.analysed_sst.values  # Shape: (92, 60, 60)

for lat_idx in range(ds_region.latitude.size):
    for lon_idx in range(ds_region.longitude.size):
        # Check if all SST values are finite for this cell
        sst_values = target_sst[:, lat_idx, lon_idx]
        if np.all(np.isfinite(sst_values)):
            sea_cells[lat_idx, lon_idx] = True

print(f"Found {np.sum(sea_cells)} sea cells out of {ds_region.latitude.size * ds_region.longitude.size}")

# Find MHWs in each sea cell
print("Detecting MHWs...")
mhw_mask = np.zeros((ds_target.time.size, ds_region.latitude.size, ds_region.longitude.size), dtype=np.uint8)

# Create a mapping from dates to day-of-year for target period
target_dates = ds_target.time.values.astype('datetime64[D]').astype('datetime64[s]').astype(datetime)
target_doy = [date_to_doy(dt.strftime('%Y-%m-%d')) for dt in target_dates]

# For each day in target period, check if it's a hot day
for day_idx, (date, doy) in enumerate(zip(target_dates, target_doy)):
    if doy is not None:
        # Get the corresponding smoothed threshold for this day-of-year
        threshold_map = smoothed_thresholds[doy-1]  # doy is 1-indexed, so subtract 1
        sst_map = target_sst[day_idx]  # Current day's SST
        
        # Compare SST with threshold to identify hot days
        hot_days = sst_map >= threshold_map
        mhw_mask[day_idx] = hot_days.astype(np.uint8)

# Now join gaps of 1-2 days to form continuous MHWs
print("Joining MHW gaps...")
# We'll process each cell individually
for lat_idx in range(ds_region.latitude.size):
    for lon_idx in range(ds_region.longitude.size):
        if sea_cells[lat_idx, lon_idx]:  # Only process sea cells
            # Get the binary mask for this cell
            cell_mask = mhw_mask[:, lat_idx, lon_idx]
            
            # Find runs of consecutive hot days
            # We'll use a simple approach: extend runs by 1-2 days if they are adjacent
            # First, create a copy to avoid modifying during iteration
            new_mask = cell_mask.copy()
            
            # Look for sequences of 0s (non-hot days) that are 1 or 2 days long
            # and extend the previous hot run to include them
            i = 0
            while i < len(cell_mask):
                if cell_mask[i] == 0:  # Found a non-hot day
                    # Check if it's part of a small gap (1 or 2 days)
                    gap_length = 0
                    j = i
                    while j < len(cell_mask) and cell_mask[j] == 0:
                        gap_length += 1
                        j += 1
                    
                    # If gap is 1 or 2 days, extend the previous hot run
                    if gap_length <= 2 and i > 0:
                        # Extend previous hot run to include this gap
                        # Find the start of the previous hot run
                        k = i - 1
                        while k >= 0 and cell_mask[k] == 0:
                            k -= 1
                        if k >= 0:  # There was a previous hot run
                            # Mark the gap days as hot too
                            for g in range(i, min(i + gap_length, len(cell_mask))):
                                new_mask[g] = 1
                        
                    i = j  # Skip past the gap
                else:
                    i += 1
            
            # Update the mask for this cell
            mhw_mask[:, lat_idx, lon_idx] = new_mask

# Now identify regional events
print("Identifying regional events...")
# A day is active if at least one sea cell is in an MHW
active_days = np.any(mhw_mask, axis=(1, 2))  # Shape: (92,)

# Find maximal runs of consecutive active days
events = []
start_idx = None

for i, is_active in enumerate(active_days):
    if is_active and start_idx is None:
        # Start of a new event
        start_idx = i
    elif not is_active and start_idx is not None:
        # End of an event
        events.append({
            'onset': target_dates[start_idx].strftime('%Y-%m-%d'),
            'end': target_dates[i-1].strftime('%Y-%m-%d')
        })
        start_idx = None

# Handle case where the last day is active
if start_idx is not None:
    events.append({
        'onset': target_dates[start_idx].strftime('%Y-%m-%d'),
        'end': target_dates[-1].strftime('%Y-%m-%d')
    })

print(f"Found {len(events)} regional MHW events")

# Prepare output
print("Preparing output files...")

# Create output directory if it doesn't exist
import os
os.makedirs('output', exist_ok=True)

# Save mhw_mask to NetCDF
import xarray as xr

# Create the dataset with proper coordinates
time_coords = ds_target.time.values
lat_coords = ds_region.latitude.values
lon_coords = ds_region.longitude.values

# Create the dataset
ds_output = xr.Dataset(
    {
        'mhw': (['time', 'latitude', 'longitude'], mhw_mask)
    },
    coords={
        'time': time_coords,
        'latitude': lat_coords,
        'longitude': lon_coords
    }
)

# Save to file
ds_output.to_netcdf('output/mhw_mask.nc')

# Create report JSON
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
        "start": target_start,
        "end": target_end
    },
    "events": events,
    "complete": True,
    "caveats": ""
}

import json
with open('output/report.json', 'w') as f:
    json.dump(report, f, indent=2)

print("Output files created successfully!")
print(f"Region: {lat_min}°N to {lat_max}°N, {lon_min}°E to {lon_max}°E")
print(f"Baseline period: {baseline_start} to {baseline_end}")
print(f"Target period: {target_start} to {target_end}")
print(f"Number of events detected: {len(events)}")
for event in events:
    print(f"Event: {event['onset']} to {event['end']}")