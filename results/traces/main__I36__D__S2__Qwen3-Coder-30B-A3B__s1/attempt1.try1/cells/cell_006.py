import xarray as xr
import numpy as np
import os
from datetime import datetime, timedelta
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

# Convert times to datetime objects for easier handling
all_times = ds.time.values
target_time_values = all_times[target_times]
baseline_time_values = all_times[baseline_times]

# Function to convert date to day-of-year (1-366)
def date_to_doy(date):
    """Convert datetime64 to day-of-year (1-366)"""
    dt = pd.to_datetime(date)
    doy = dt.timetuple().tm_yday
    # Special case for Feb 29 (day 60)
    if dt.month == 2 and dt.day == 29:
        return 60
    # Adjust for leap years - in our calculation we'll handle it properly
    return doy

# We need to work with pandas for date operations
import pandas as pd

# Create mapping from dates to day-of-year
date_to_doy_map = {}
for date in baseline_time_values:
    dt = pd.to_datetime(date)
    doy = dt.timetuple().tm_yday
    # Handle leap year special case
    if dt.month == 2 and dt.day == 29:
        date_to_doy_map[date] = 60
    else:
        date_to_doy_map[date] = doy

# Create a comprehensive function to compute thresholds and climatology
def compute_thresholds_and_climatology(sst_data, baseline_times, target_times, region_lat, region_lon):
    """
    Compute thresholds and climatology for each grid cell and day of year
    """
    n_lat, n_lon = sst_data.shape[1], sst_data.shape[2]
    n_days = 366  # Days in a year (including leap year day)
    
    # Initialize arrays for thresholds and climatology
    thresholds = np.full((n_days, n_lat, n_lon), np.nan, dtype=np.float64)
    climatology = np.full((n_days, n_lat, n_lon), np.nan, dtype=np.float64)
    
    # Create date-to-doy mapping for all baseline dates
    baseline_dates = baseline_time_values
    date_to_doy = {}
    for date in baseline_dates:
        dt = pd.to_datetime(date)
        if dt.month == 2 and dt.day == 29:
            date_to_doy[date] = 60
        else:
            date_to_doy[date] = dt.timetuple().tm_yday
    
    # Create pools for each day of year
    pools = [[] for _ in range(367)]  # Index 0 unused, days 1-366
    
    # Fill pools for baseline period
    print("Building baseline pools...")
    for i, date in enumerate(baseline_dates):
        doy = date_to_doy[date]
        if doy == 60:  # Skip day 60 for building pools (it will be handled specially)
            continue
            
        # Get SST data for this date for all grid cells
        sst_vals = sst_data.isel(time=i).values  # Shape (n_lat, n_lon)
        
        # Add to the appropriate pool (we'll handle the windowing later)
        pools[doy].append(sst_vals)
    
    # Special handling for day 60 (Feb 29)
    # Collect data from Feb 28 and Mar 1 for day 60
    feb28_vals = []
    mar1_vals = []
    for i, date in enumerate(baseline_dates):
        dt = pd.to_datetime(date)
        if dt.month == 2 and dt.day == 28:
            sst_vals = sst_data.isel(time=i).values
            feb28_vals.append(sst_vals)
        elif dt.month == 3 and dt.day == 1:
            sst_vals = sst_data.isel(time=i).values
            mar1_vals.append(sst_vals)
    
    # For day 60, we'll average the Feb 28 and Mar 1 data
    if feb28_vals and mar1_vals:
        pools[60] = feb28_vals + mar1_vals
    
    # Calculate thresholds and climatologies
    print("Computing thresholds and climatologies...")
    for doy in range(1, 367):
        if doy == 60:
            # Special case for day 60
            # Use the mean of days 59 and 61
            if pools[59] and pools[61]:
                # Combine all data for both days
                combined_data = np.concatenate(pools[59] + pools[61])
                # Remove NaNs
                combined_data = combined_data[~np.isnan(combined_data)]
                if len(combined_data) > 0:
                    climatology[doy-1] = np.mean(combined_data)
                    # For threshold, use 90th percentile with hazen method
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
                    # For threshold, use 90th percentile with hazen method
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
            if np.isfinite(arr[idx]):
                sum_val += arr[idx]
                count += 1
                
        if count > 0:
            result[i] = sum_val / count
        else:
            result[i] = np.nan
            
    return result

# First, let's extract just the data we need for the baseline period
baseline_sst = sst_data.isel(time=baseline_times)

# But wait, I need to make sure I'm working with the right data structure. Let me reorganize.

# Let's simplify approach and build a more straightforward implementation
print("Starting MHW analysis...")

# First, let's get all data for the region in a more efficient way
region_sst_full = ds['analysed_sst'].isel(latitude=lat_indices, longitude=lon_indices)
print(f"Full region SST shape: {region_sst_full.shape}")

# Get the full time series for our region
region_times = ds.time.values
target_mask = (region_times >= target_start) & (region_times <= target_end)
baseline_mask = (region_times >= baseline_start) & (region_times <= baseline_end)

# Get target period data (what we'll analyze for MHWs)
target_sst = region_sst_full.where(target_mask, drop=True)
baseline_sst = region_sst_full.where(baseline_mask, drop=True)

print(f"Target SST shape: {target_sst.shape}")
print(f"Baseline SST shape: {baseline_sst.shape}")

# Now let's implement the complete algorithm step by step
# Step 1: Compute thresholds and climatology from baseline period
def compute_mhw_thresholds_climatology(baseline_sst_data, region_lat, region_lon):
    """
    Compute thresholds and climatology for each grid cell and day of year
    """
    n_lat, n_lon = baseline_sst_data.shape[1], baseline_sst_data.shape[2]
    n_days = 366  # Days in a year (including leap year day)
    
    # Initialize arrays for thresholds and climatology
    thresholds = np.full((n_days, n_lat, n_lon), np.nan, dtype=np.float64)
    climatology = np.full((n_days, n_lat, n_lon), np.nan, dtype=np.float64)
    
    # Create mapping from datetime to day of year
    baseline_times = baseline_sst_data.time.values
    date_to_doy = {}
    
    for i, date in enumerate(baseline_times):
        dt = pd.to_datetime(date)
        # Handle leap year cases correctly
        if dt.month == 2 and dt.day == 29:
            date_to_doy[date] = 60
        else:
            date_to_doy[date] = dt.timetuple().tm_yday
    
    # Build pools for each day of year (1-366)
    # Pool will store all SST values for that day of year
    pools = [[] for _ in range(367)]  # Index 0 unused, days 1-366
    
    # Populate pools with baseline data
    print("Populating baseline pools...")
    for i, date in enumerate(baseline_times):
        doy = date_to_doy[date]
        
        # For day 60, we treat specially - it belongs to Feb 29 but we collect from neighbors
        if doy == 60:
            continue  # Will handle separately
            
        # Get SST values for this date for all grid cells
        sst_vals = baseline_sst_data.isel(time=i).values  # Shape (n_lat, n_lon)
        
        # Store in appropriate pool
        pools[doy].append(sst_vals)
    
    # Handle day 60 (February 29) - combine data from Feb 28 and Mar 1
    feb28_data = []
    mar1_data = []
    
    for i, date in enumerate(baseline_times):
        dt = pd.to_datetime(date)
        if dt.month == 2 and dt.day == 28:
            sst_vals = baseline_sst_data.isel(time=i).values
            feb28_data.append(sst_vals)
        elif dt.month == 3 and dt.day == 1:
            sst_vals = baseline_sst_data.isel(time=i).values
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

# Now let's actually implement this step by step
print("Computing thresholds and climatology...")

# First, let's get our baseline data in a more usable form
baseline_sst_subset = baseline_sst
print(f"Baseline SST subset shape: {baseline_sst_subset.shape}")

# Compute thresholds and climatology
thresholds, climatology = compute_mhw_thresholds_climatology(baseline_sst_subset, region_lat, region_lon)
print("Thresholds shape:", thresholds.shape)
print("Climatology shape:", climatology.shape)

# Let's test with a small sample
print("Sample thresholds (first few grid cells):", thresholds[:, 0, 0][:5])
print("Sample climatology (first few grid cells):", climatology[:, 0, 0][:5])

# Now let's detect MHWs in the target period
def detect_mhw_events(target_sst_data, thresholds, climatology):
    """
    Detect MHW events in target period
    """
    n_time, n_lat, n_lon = target_sst_data.shape
    
    # Initialize MHW mask
    mhw_mask = np.zeros((n_time, n_lat, n_lon), dtype=np.uint8)
    
    # Get target times
    target_times = target_sst_data.time.values
    
    # Convert times to day-of-year
    date_to_doy = {}
    for i, date in enumerate(target_times):
        dt = pd.to_datetime(date)
        if dt.month == 2 and dt.day == 29:
            date_to_doy[date] = 60
        else:
            date_to_doy[date] = dt.timetuple().tm_yday
    
    # Process each day
    print("Detecting MHW events...")
    for t in range(n_time):
        date = target_times[t]
        doy = date_to_doy[date]
        
        # Get SST data for this day
        sst_day = target_sst_data.isel(time=t).values  # Shape (n_lat, n_lon)
        
        # Get threshold and climatology for this day of year
        threshold_day = thresholds[doy-1]  # Convert to 0-based index
        climatology_day = climatology[doy-1]
        
        # Mark hot days (where SST >= threshold)
        hot_mask = (sst_day >= threshold_day) & np.isfinite(sst_day)
        mhw_mask[t] = hot_mask.astype(np.uint8)
    
    return mhw_mask

# Detect MHW events
print("Detecting MHW events...")
mhw_mask = detect_mhw_events(target_sst, thresholds, climatology)
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
    target_times = target_sst.time.values
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

# Create the NetCDF file
import netCDF4 as nc
from netCDF4 import Dataset

# Prepare coordinate arrays
time_coords = target_sst.time.values
lat_coords = region_lat.values
lon_coords = region_lon.values

# Create NetCDF file
nc_file_path = os.path.join(output_dir, 'mhw_mask.nc')
with Dataset(nc_file_path, 'w', format='NETCDF4') as ncfile:
    # Create dimensions
    ncfile.createDimension('time', len(time_coords))
    ncfile.createDimension('lat', len(lat_coords))
    ncfile.createDimension('lon', len(lon_coords))
    
    # Create variables
    time_var = ncfile.createVariable('time', 'i8', ('time',))
    lat_var = ncfile.createVariable('lat', 'f4', ('lat',))
    lon_var = ncfile.createVariable('lon', 'f4', ('lon',))
    mhw_var = ncfile.createVariable('mhw', 'u1', ('time', 'lat', 'lon'), zlib=True)
    
    # Assign data
    time_var[:] = nc.date2num(time_coords, units=time_var.units, calendar=time_var.calendar)
    lat_var[:] = lat_coords
    lon_var[:] = lon_coords
    mhw_var[:] = joined_mhw_mask
    
    # Add attributes
    time_var.units = 'days since 1970-01-01 00:00:00'
    time_var.calendar = 'standard'
    mhw_var.units = '1 if inside MHW, 0 otherwise'
    
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