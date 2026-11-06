import xarray as xr
import numpy as np
import os
import pandas as pd
import json

# Set up paths
local_path = '/work/sst_s2.nc'
output_dir = '/work/output'
os.makedirs(output_dir, exist_ok=True)

# Load the dataset
ds = xr.open_dataset(local_path, engine="h5netcdf")

# Define our region boundaries
lat_min, lat_max = 60.09, 61.29
lon_min, lon_max = 20.01, 21.21

# Find indices for our region
lat_indices = np.where((ds.latitude >= lat_min) & (ds.latitude <= lat_max))[0]
lon_indices = np.where((ds.longitude >= lon_min) & (ds.longitude <= lon_max))[0]

# Extract the region data
region_sst = ds['analysed_sst'].isel(latitude=lat_indices, longitude=lon_indices)
region_lat = ds.latitude.isel(latitude=lat_indices)
region_lon = ds.longitude.isel(longitude=lon_indices)

print(f"Processing region: {len(lat_indices)} lat x {len(lon_indices)} lon = {len(lat_indices)*len(lon_indices)} grid cells")

# Target period: 2003-06-01 to 2003-08-31
target_start = np.datetime64('2003-06-01')
target_end = np.datetime64('2003-08-31')

# Baseline period: 1992-01-01 to 2002-12-31
baseline_start = np.datetime64('1992-01-01')
baseline_end = np.datetime64('2002-12-31')

# Get all time indices for the target period
target_times = np.where((ds.time >= target_start) & (ds.time <= target_end))[0]
baseline_times = np.where((ds.time >= baseline_start) & (ds.time <= baseline_end))[0]

print(f"Target period: {len(target_times)} days")
print(f"Baseline period: {len(baseline_times)} days")

# Get the actual time values
all_times = ds.time.values
target_time_values = all_times[target_times]
baseline_time_values = all_times[baseline_times]

# Function to compute day-of-year (1-366) from datetime
def date_to_doy(date):
    """Convert datetime64 to day-of-year (1-366)"""
    dt = pd.to_datetime(date)
    doy = dt.timetuple().tm_yday
    # Special handling for Feb 29 - it's day 60
    if dt.month == 2 and dt.day == 29:
        return 60
    return doy

# Step 1: Compute thresholds and climatology from baseline period
def compute_thresholds_and_climatology(baseline_sst, baseline_times):
    """
    Compute thresholds and climatology for each grid cell and day of year
    """
    n_lat, n_lon = baseline_sst.shape[1], baseline_sst.shape[2]
    n_days = 366  # Days in a year (including leap year day)
    
    # Initialize arrays for thresholds and climatology
    thresholds = np.full((n_days, n_lat, n_lon), np.nan, dtype=np.float64)
    climatology = np.full((n_days, n_lat, n_lon), np.nan, dtype=np.float64)
    
    # Create mapping from datetime to day of year
    date_to_doy_map = {}
    for date in baseline_times:
        doy = date_to_doy(date)
        date_to_doy_map[date] = doy
    
    # Build pools for each day of year (1-366)
    # Pool will store all SST values for that day of year
    pools = [[] for _ in range(367)]  # Index 0 unused, days 1-366
    
    # Populate pools with baseline data
    print("Populating baseline pools...")
    for i, date in enumerate(baseline_times):
        doy = date_to_doy_map[date]
        
        # For day 60 (Feb 29), we treat specially
        if doy == 60:
            continue  # Will handle separately
            
        # Get SST values for this date for all grid cells
        sst_vals = baseline_sst.isel(time=i).values  # Shape (n_lat, n_lon)
        
        # Store in appropriate pool
        pools[doy].append(sst_vals)
    
    # Handle day 60 (February 29) - combine data from Feb 28 and Mar 1
    feb28_data = []
    mar1_data = []
    
    for i, date in enumerate(baseline_times):
        dt = pd.to_datetime(date)
        if dt.month == 2 and dt.day == 28:
            sst_vals = baseline_sst.isel(time=i).values
            feb28_data.append(sst_vals)
        elif dt.month == 3 and dt.day == 1:
            sst_vals = baseline_sst.isel(time=i).values
            mar1_data.append(sst_vals)
    
    # Pool for day 60 is combination of Feb 28 and Mar 1 data
    if feb28_data or mar1_data:
        pools[60] = feb28_data + mar1_data
    
    # Compute thresholds and climatologies for each day of year
    print("Computing thresholds and climatologies...")
    for doy in range(1, 367):
        if doy == 60:
            # Special case: day 60 gets the mean of days 59 and 61
            if pools[59] and pools[61]:
                # Combine all data for days 59 and 61
                combined_data = np.concatenate(pools[59] + pools[61])
                # Remove NaNs
                combined_data = combined_data[~np.isnan(combined_data)]
                if len(combined_data) > 0:
                    climatology[doy-1] = np.mean(combined_data)
                    # 90th percentile with Hazen method (linear interpolation)
                    thresholds[doy-1] = np.percentile(combined_data, 90, method='linear')
        else:
            # Normal case
            if pools[doy]:
                # Flatten all data for this day of year
                flat_data = np.array(pools[doy])
                # Remove NaNs
                flat_data = flat_data[~np.isnan(flat_data)]
                
                if len(flat_data) > 0:
                    climatology[doy-1] = np.mean(flat_data)
                    # 90th percentile with Hazen method (linear interpolation)
                    thresholds[doy-1] = np.percentile(flat_data, 90, method='linear')
    
    # Smooth the climatology and thresholds using 31-day centered moving average
    print("Smoothing climatology and thresholds...")
    smoothed_climatology = smooth_366_array(climatology)
    smoothed_thresholds = smooth_366_array(thresholds)
    
    return smoothed_thresholds, smoothed_climatology

def smooth_366_array(arr):
    """
    Apply 31-day centered moving average to a 366-element array, wrapping around
    """
    result = np.zeros_like(arr, dtype=np.float64)
    window_size = 31
    half_window = window_size // 2
    
    for i in range(366):
        # Sum values in the window
        sum_val = 0
        count = 0
        
        for j in range(-half_window, half_window + 1):
            idx = (i + j) % 366
            # Only add finite values
            if np.isfinite(arr[idx]).any():
                # Handle the fact that arr[idx] might be 2D (lat, lon)
                if arr[idx].ndim > 0:
                    # For multi-dimensional arrays, we want to check if any element is finite
                    finite_elements = arr[idx][np.isfinite(arr[idx])]
                    if len(finite_elements) > 0:
                        sum_val += np.sum(finite_elements)
                        count += len(finite_elements)
                else:
                    if np.isfinite(arr[idx]):
                        sum_val += arr[idx]
                        count += 1
                        
        if count > 0:
            result[i] = sum_val / count
        else:
            result[i] = np.nan
            
    return result

# Now extract the baseline data properly
baseline_sst_subset = ds['analysed_sst'].isel(time=baseline_times, latitude=lat_indices, longitude=lon_indices)
print(f"Baseline SST subset shape: {baseline_sst_subset.shape}")

# Compute thresholds and climatology
print("Computing thresholds and climatology...")
thresholds, climatology = compute_thresholds_and_climatology(baseline_sst_subset, baseline_time_values)
print("Thresholds shape:", thresholds.shape)
print("Climatology shape:", climatology.shape)

# Let's test with a small sample
print("Sample thresholds (first few grid cells):", thresholds[:, 0, 0][:5])
print("Sample climatology (first few grid cells):", climatology[:, 0, 0][:5])

# Now let's detect MHWs in the target period
def detect_mhw_events(target_sst, thresholds, climatology):
    """
    Detect MHW events in target period
    """
    n_time, n_lat, n_lon = target_sst.shape
    
    # Initialize MHW mask
    mhw_mask = np.zeros((n_time, n_lat, n_lon), dtype=np.uint8)
    
    # Get target times
    target_times = target_sst.time.values
    
    # Convert times to day-of-year
    date_to_doy = {}
    for date in target_times:
        doy = date_to_doy(date)
        date_to_doy[date] = doy
    
    # Process each day
    print("Detecting MHW events...")
    for t in range(n_time):
        date = target_times[t]
        doy = date_to_doy[date]
        
        # Get SST data for this day
        sst_day = target_sst.isel(time=t).values  # Shape (n_lat, n_lon)
        
        # Get threshold and climatology for this day of year
        threshold_day = thresholds[doy-1]  # Convert to 0-based index
        climatology_day = climatology[doy-1]
        
        # Mark hot days (where SST >= threshold)
        hot_mask = (sst_day >= threshold_day) & np.isfinite(sst_day)
        mhw_mask[t] = hot_mask.astype(np.uint8)
    
    return mhw_mask

# Extract target data
target_sst_subset = ds['analysed_sst'].isel(time=target_times, latitude=lat_indices, longitude=lon_indices)
print(f"Target SST subset shape: {target_sst_subset.shape}")

# Detect MHW events
print("Detecting MHW events...")
mhw_mask = detect_mhw_events(target_sst_subset, thresholds, climatology)
print("MHW mask shape:", mhw_mask.shape)
print("MHW mask sample (first day):", mhw_mask[0, :, :5])

# Now join gaps of 1 or 2 days
def join_mhw_gaps(mhw_mask):
    """
    Join MHWs separated by 1 or 2 non-hot days
    """
    n_time, n_lat, n_lon = mhw_mask.shape
    joined_mask = mhw_mask.copy()
    
    # For each grid cell, process time series
    for i in range(n_lat):
        for j in range(n_lon):
            # Get time series for this grid cell
            ts = mhw_mask[:, i, j]
            
            # Find runs of consecutive 1s (hot days)
            if np.sum(ts) == 0:
                continue  # No hot days in this cell
                
            # Identify runs of consecutive MHW days
            runs = []
            start = None
            
            for t in range(len(ts)):
                if ts[t] == 1:
                    if start is None:
                        start = t
                else:
                    if start is not None:
                        runs.append((start, t-1))
                        start = None
            
            # Don't forget the last run if it extends to the end
            if start is not None:
                runs.append((start, len(ts)-1))
            
            # Join gaps of 1 or 2 days
            if len(runs) > 1:
                new_runs = [runs[0]]
                for i in range(1, len(runs)):
                    prev_run_end = new_runs[-1][1]
                    curr_run_start = runs[i][0]
                    
                    # Gap between runs
                    gap = curr_run_start - prev_run_end - 1
                    
                    # If gap is 1 or 2 days, join them
                    if 1 <= gap <= 2:
                        # Extend previous run to cover the gap
                        new_runs[-1] = (new_runs[-1][0], runs[i][1])
                    else:
                        new_runs.append(runs[i])
                
                # Update the mask with joined runs
                joined_mask[:, i, j] = 0  # Reset
                for start, end in new_runs:
                    joined_mask[start:end+1, i, j] = 1
    
    return joined_mask

# Join MHW gaps
print("Joining MHW gaps...")
joined_mhw_mask = join_mhw_gaps(mhw_mask)
print("Joined MHW mask sample (first day):", joined_mhw_mask[0, :, :5])

# Now identify regional events
def find_regional_events(joined_mhw_mask):
    """
    Find regional MHW events - runs of active days across the entire region
    """
    n_time, n_lat, n_lon = joined_mhw_mask.shape
    
    # Determine active days (at least one cell is in MHW)
    active_days = np.any(joined_mhw_mask, axis=(1, 2))  # Shape: (n_time,)
    
    # Find runs of consecutive active days
    events = []
    start = None
    
    for t in range(len(active_days)):
        if active_days[t]:
            if start is None:
                start = t
        else:
            if start is not None:
                events.append((start, t-1))
                start = None
    
    # Don't forget the last run if it extends to the end
    if start is not None:
        events.append((start, len(active_days)-1))
    
    # Convert back to date strings
    target_times = target_sst_subset.time.values
    formatted_events = []
    for start_t, end_t in events:
        onset_date = pd.to_datetime(target_times[start_t]).strftime('%Y-%m-%d')
        end_date = pd.to_datetime(target_times[end_t]).strftime('%Y-%m-%d')
        formatted_events.append({
            "onset": onset_date,
            "end": end_date
        })
    
    return formatted_events

# Find regional events
print("Finding regional events...")
regional_events = find_regional_events(joined_mhw_mask)
print("Regional events found:", len(regional_events))

# Create output files
print("Creating output files...")

# Create the NetCDF file using xarray directly
# Create a dataset with the required structure
result_ds = xr.Dataset(
    {
        'mhw': (['time', 'lat', 'lon'], joined_mhw_mask)
    },
    coords={
        'time': target_sst_subset.time,
        'lat': region_lat,
        'lon': region_lon
    }
)

# Save to NetCDF
nc_file_path = os.path.join(output_dir, 'mhw_mask.nc')
result_ds.to_netcdf(nc_file_path)

# Create report JSON
report = {
    "region": {
        "lat_min": float(lat_min),
        "lat_max": float(lat_max),
        "lon_min": float(lon_min),
        "lon_max": float(lon_max)
    },
    "baseline_analysed": {
        "start": str(baseline_start),
        "end": str(baseline_end)
    },
    "target_analysed": {
        "start": str(target_start),
        "end": str(target_end)
    },
    "events": regional_events,
    "complete": True,
    "caveats": ""
}

report_path = os.path.join(output_dir, 'report.json')
with open(report_path, 'w') as f:
    json.dump(report, f, indent=2)

print("Analysis complete!")
print(f"Regional events: {len(regional_events)}")
print(f"Report saved to: {report_path}")
print(f"NetCDF file saved to: {nc_file_path}")