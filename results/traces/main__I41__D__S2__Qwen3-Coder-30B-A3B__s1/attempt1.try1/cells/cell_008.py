import fsspec
import xarray as xr
import numpy as np
import os
from datetime import datetime, timedelta
import calendar
from scipy import stats

# Set up the filesystem
fs = fsspec.filesystem('onedata')

# Correct path based on what we saw
remote_path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
local_path = '/work/sst_s2.nc'

# Download the file
fs.get(remote_path, local_path)

# Open the dataset
ds = xr.open_dataset(local_path, engine='h5netcdf')

# Define our region and time period
lat_min, lat_max = 61.57, 62.77
lon_min, lon_max = 20.17, 21.37
start_date = datetime(2021, 6, 1)
end_date = datetime(2021, 8, 31)

# Select the region for all time
ds_region = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))

# Get all times
all_times = ds_region.time.values

# Define baseline period
baseline_start = np.datetime64('1992-01-01')
baseline_end = np.datetime64('2002-12-31')

# Filter baseline data
baseline_mask = (all_times >= baseline_start) & (all_times <= baseline_end)
baseline_times = all_times[baseline_mask]
baseline_data = ds_region.analysed_sst.isel(time=baseline_mask)

print("Processing baseline data for climatology...")

# Create mapping from date to day-of-year (1-366)
def date_to_doy(date):
    """Convert datetime to day-of-year (1-366)"""
    if isinstance(date, np.datetime64):
        # Convert numpy datetime64 to Python datetime
        date = date.astype(datetime)
    doy = date.timetuple().tm_yday
    
    # Adjust for leap years - this handles the special case for Feb 29
    # For non-leap years, Feb 29 doesn't exist, so we don't include Feb 29 data
    # For leap years, Feb 29 is day 60
    return doy

# Create arrays for storing data by day-of-year
# We'll process all baseline data to build pools
baseline_dates = [datetime.strptime(str(d), '%Y-%m-%dT%H:%M:%S.%f') for d in baseline_times]
doy_list = [date_to_doy(d) for d in baseline_dates]

# Create mapping of day-of-year to indices in baseline data
doy_indices = {}
for i, doy in enumerate(doy_list):
    if doy not in doy_indices:
        doy_indices[doy] = []
    doy_indices[doy].append(i)

print(f"Created DOY mappings for {len(doy_indices)} unique days")

# Create pools for each day of year
# We'll use the same approach as described in the problem:
# For each day of year d (other than 60), pool includes SST values from ±5 days around that DOY
# Day 60 gets no pool of its own, but will use the average of days 59 and 61
# Windows near year ends include days beyond the year boundary

# First, let's identify which baseline dates fall in our region and are valid
print("Building climatology pools...")

# Create empty arrays for thresholds and climatologies
thresholds = np.full((366, 60, 60), np.nan, dtype=np.float64)
climatologies = np.full((366, 60, 60), np.nan, dtype=np.float64)

# Process each day of year (1-366)
for doy in range(1, 367):
    # Special handling for day 60 (Feb 29) - it gets no pool of its own
    if doy == 60:
        # For day 60, use the average of days 59 and 61
        if 59 in doy_indices and 61 in doy_indices:
            # Combine the data from days 59 and 61
            pool_data = []
            for idx in doy_indices[59]:
                pool_data.append(baseline_data.values[idx])
            for idx in doy_indices[61]:
                pool_data.append(baseline_data.values[idx])
            
            # Stack and compute statistics
            pool_data = np.array(pool_data)
            # Compute climatology (mean) and threshold (90th percentile) for each cell
            climatologies[doy-1] = np.nanmean(pool_data, axis=0)
            thresholds[doy-1] = np.nanpercentile(pool_data, 90, method='hazen', axis=0)
        else:
            # If we don't have both days, we can't compute it properly
            # Leave as NaN for now
            pass
    else:
        # For other days, gather data from ±5 days around this DOY
        # This requires careful handling of year boundaries
        pool_data = []
        
        # Get the window of dates around this DOY
        # We'll look at the 11-day window (±5 days) around this DOY
        # But we also need to handle year boundaries
        
        # For each date in baseline data, check if it falls within the window
        for i, baseline_date in enumerate(baseline_dates):
            baseline_doy = date_to_doy(baseline_date)
            
            # Calculate distance considering year wraparound
            if baseline_doy <= doy:
                dist = doy - baseline_doy
            else:
                # This means we're wrapping around the year
                dist = 366 - baseline_doy + doy
            
            # If within 5 days (including the day itself)
            if dist <= 5:
                pool_data.append(baseline_data.values[i])
        
        if len(pool_data) > 0:
            pool_data = np.array(pool_data)
            # Compute climatology (mean) and threshold (90th percentile) for each cell
            climatologies[doy-1] = np.nanmean(pool_data, axis=0)
            thresholds[doy-1] = np.nanpercentile(pool_data, 90, method='hazen', axis=0)

print("Climatology computation complete.")

# Now apply smoothing to climatology and thresholds (31-day centered moving average)
def smooth_366(arr):
    """Apply 31-day centered moving average with wraparound"""
    smoothed = np.zeros_like(arr)
    window_size = 31
    half_window = window_size // 2
    
    for i in range(366):
        # Sum values in the window with wraparound
        sum_val = 0
        count = 0
        for j in range(-half_window, half_window + 1):
            wrapped_idx = (i + j) % 366
            if not np.isnan(arr[wrapped_idx]):
                sum_val += arr[wrapped_idx]
                count += 1
        if count > 0:
            smoothed[i] = sum_val / count
        else:
            smoothed[i] = np.nan
    return smoothed

# Smooth climatologies and thresholds
print("Smoothing climatology and thresholds...")
smoothed_climatologies = np.zeros_like(climatologies)
smoothed_thresholds = np.zeros_like(thresholds)

for i in range(60):  # latitude
    for j in range(60):  # longitude
        # Smooth climatology
        clim_vals = climatologies[:, i, j]
        smoothed_climatologies[:, i, j] = smooth_366(clim_vals)
        
        # Smooth thresholds
        thresh_vals = thresholds[:, i, j]
        smoothed_thresholds[:, i, j] = smooth_366(thresh_vals)

print("Smoothing complete.")

# Now process the target period (2021-06-01 to 2021-08-31)
print("Processing target period for MHW detection...")

# Select the target period data
target_mask = (all_times >= np.datetime64('2021-06-01')) & (all_times <= np.datetime64('2021-08-31'))
target_times = all_times[target_mask]
target_data = ds_region.analysed_sst.isel(time=target_mask)

print(f"Target period data shape: {target_data.shape}")

# Create mask for MHWs
mhw_mask = np.zeros((len(target_times), 60, 60), dtype=np.uint8)

# Process each day in the target period
for t, time_idx in enumerate(range(len(target_times))):
    current_date = target_times[time_idx]
    current_doy = date_to_doy(current_date)
    
    # Get threshold and climatology for this DOY
    threshold = smoothed_thresholds[current_doy-1]  # DOY is 1-based
    climatology = smoothed_climatologies[current_doy-1]
    
    # Compare SST with threshold (SST >= threshold)
    hot_days = target_data.values[t] >= threshold
    
    # Apply the hot days mask to the MHW mask
    mhw_mask[t] = hot_days.astype(np.uint8)

print("MHW detection complete.")

# Now identify actual MHW events by grouping consecutive hot days
print("Identifying MHW events...")

# Function to identify MHWs (runs of at least 5 consecutive hot days)
def find_mhws(mhw_daily_mask):
    """Find MHW events in daily MHW mask"""
    # mhw_daily_mask: (days, lat, lon) with 1 for hot, 0 for not hot
    events = []
    
    # For each spatial point, find MHW events
    for i in range(mhw_daily_mask.shape[1]):  # latitude
        for j in range(mhw_daily_mask.shape[2]):  # longitude
            # Get time series for this location
            ts = mhw_daily_mask[:, i, j]
            
            # Find runs of consecutive hot days
            start = None
            for day in range(len(ts)):
                if ts[day] == 1:
                    if start is None:
                        start = day
                else:
                    if start is not None:
                        # End of a potential MHW
                        if day - start >= 5:  # At least 5 consecutive hot days
                            events.append((start, day - 1, i, j))
                        start = None
            
            # Handle case where the series ends with a hot day
            if start is not None and len(ts) - start >= 5:
                events.append((start, len(ts) - 1, i, j))
    
    return events

# Find MHW events
mhw_events = find_mhws(mhw_mask)

print(f"Found {len(mhw_events)} MHW events")

# Now let's join gaps of 1 or 2 days
def merge_mhw_events(events, max_gap=2):
    """Merge MHW events separated by small gaps"""
    if not events:
        return []
    
    # Sort by start time
    sorted_events = sorted(events, key=lambda x: x[0])
    
    merged = [sorted_events[0]]
    
    for i in range(1, len(sorted_events)):
        prev_start, prev_end, prev_lat, prev_lon = merged[-1]
        curr_start, curr_end, curr_lat, curr_lon = sorted_events[i]
        
        # If they're at the same location and gap is acceptable
        if prev_lat == curr_lat and prev_lon == curr_lon:
            gap = curr_start - prev_end - 1
            if 0 <= gap <= max_gap:
                # Merge them
                merged[-1] = (prev_start, curr_end, prev_lat, prev_lon)
            else:
                merged.append(sorted_events[i])
        else:
            merged.append(sorted_events[i])
    
    return merged

# Merge events
merged_events = merge_mhw_events(mhw_events)
print(f"After merging gaps: {len(merged_events)} events")

# Now determine regional events (when at least one cell is in MHW)
print("Determining regional MHW events...")

# Create regional activity mask (1 if any cell is in MHW on that day)
regional_activity = np.any(mhw_mask, axis=(1, 2))  # Shape: (days,)

# Find maximal runs of consecutive active days
def find_regional_events(activity_mask):
    """Find regional MHW events from daily activity mask"""
    events = []
    start = None
    
    for day in range(len(activity_mask)):
        if activity_mask[day]:
            if start is None:
                start = day
        else:
            if start is not None:
                events.append((start, day - 1))
                start = None
    
    # Handle case where the series ends with active days
    if start is not None:
        events.append((start, len(activity_mask) - 1))
    
    return events

regional_events = find_regional_events(regional_activity)
print(f"Regional MHW events: {len(regional_events)}")

# Format output
report = {
    "region": {
        "lat_min": lat_min,
        "lat_max": lat_max,
        "lon_min": lon_min,
        "lon_max": lon_max
    },
    "baseline_analysed": {
        "start": str(baseline_start),
        "end": str(baseline_end)
    },
    "target_analysed": {
        "start": "2021-06-01",
        "end": "2021-08-31"
    },
    "events": [],
    "complete": True,
    "caveats": ""
}

# Add event information to report
for start_day, end_day in regional_events:
    start_date = target_times[start_day].astype(datetime).date()
    end_date = target_times[end_day].astype(datetime).date()
    report["events"].append({
        "onset": str(start_date),
        "end": str(end_date)
    })

# Save report
import json
os.makedirs('output', exist_ok=True)
with open('output/report.json', 'w') as f:
    json.dump(report, f, indent=2)

# Create netcdf file with mhw_mask
import xarray as xr

# Create a new dataset with the mhw mask
time_coords = target_times
lat_coords = ds_region.latitude.values
lon_coords = ds_region.longitude.values

# Create dataset
mhw_ds = xr.Dataset(
    {
        'mhw': (['time', 'lat', 'lon'], mhw_mask)
    },
    coords={
        'time': time_coords,
        'lat': lat_coords,
        'lon': lon_coords
    }
)

# Save to file
mhw_ds.to_netcdf('output/mhw_mask.nc')

print("Analysis complete. Files saved.")