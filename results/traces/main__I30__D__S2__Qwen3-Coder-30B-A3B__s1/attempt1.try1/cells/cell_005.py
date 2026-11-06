import fsspec
import xarray as xr
import numpy as np
import os
from datetime import datetime
import json

# Create filesystem
fs = fsspec.filesystem('onedata')

# Download the file
remote_path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
local_path = '/work/sst_s2.nc'

print("Downloading file...")
fs.get(remote_path, local_path)
print("Download complete")

# Open with xarray
ds = xr.open_dataset(local_path, engine='h5netcdf')

# Define region boundaries
lat_min, lat_max = 58.69, 59.89
lon_min, lon_max = 18.69, 19.89

# Define target period
target_start = np.datetime64('2010-06-01')
target_end = np.datetime64('2010-08-31')
target_period = slice(target_start, target_end)

# Define baseline period
baseline_start = np.datetime64('1992-01-01')
baseline_end = np.datetime64('2002-12-31')

# Get the data for our region and target period
def get_region_data(ds, lat_min, lat_max, lon_min, lon_max, time_slice):
    """Extract data for the specified region and time period"""
    # Select region
    region_ds = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))
    
    # Select time period
    region_ds = region_ds.sel(time=time_slice)
    
    return region_ds

# Get the data
region_ds = get_region_data(ds, lat_min, lat_max, lon_min, lon_max, target_period)

# Extract SST data
sst_data = region_ds['analysed_sst'].values  # Shape: (days, lat, lon)
latitudes = region_ds.latitude.values
longitudes = region_ds.longitude.values
times = region_ds.time.values

print(f"Region data shape: {sst_data.shape}")
print(f"Latitudes: {latitudes.shape}, range: [{latitudes.min()}, {latitudes.max()}]")
print(f"Longitudes: {longitudes.shape}, range: [{longitudes.min()}, {longitudes.max()}]")
print(f"Times: {times.shape}")

# Helper function to convert datetime64 to day-of-year
def get_doy_for_datetime64(dt64):
    """Convert datetime64 to day-of-year (1-366)"""
    # Convert to datetime object
    dt = dt64.astype(datetime)
    # Get day of year (1-366)
    doy = dt.timetuple().tm_yday
    return doy

# Better approach: Let's implement the correct method for building pools
def build_pools_baseline(sst_data, times, baseline_start, baseline_end):
    """
    Build pools for baseline period correctly
    """
    # Get baseline data
    baseline_mask = (times >= baseline_start) & (times <= baseline_end)
    baseline_times = times[baseline_mask]
    baseline_sst = sst_data[baseline_mask]
    
    print(f"Baseline period: {baseline_times[0]} to {baseline_times[-1]}")
    print(f"Baseline data shape: {baseline_sst.shape}")
    
    # Create a mapping from day of year to indices in baseline
    doy_to_indices = {}
    for i, date in enumerate(baseline_times):
        doy = get_doy_for_datetime64(date)
        if doy not in doy_to_indices:
            doy_to_indices[doy] = []
        doy_to_indices[doy].append(i)
    
    # For each day of year, we want to collect all SST values from dates 
    # within ±5 days of any date with that DOY
    pools = {}
    
    # Process each DOY from 1 to 366
    for doy in range(1, 367):
        if doy == 60:  # Feb 29 - special handling
            pools[doy] = []
            # For Feb 29, we want all Feb 28 and Mar 1 values from leap years
            # But we'll handle this differently later
            continue
            
        pools[doy] = []
        
        # Collect all SST values from dates within ±5 days of dates with this DOY
        for i, date in enumerate(baseline_times):
            date_doy = get_doy_for_datetime64(date)
            if date_doy == doy:
                # Add this date's SST values
                pools[doy].extend(baseline_sst[i].flatten())
                
                # Add nearby dates' values (within ±5 days)
                for j in range(max(0, i-5), min(len(baseline_times), i+6)):
                    if j != i:
                        j_doy = get_doy_for_datetime64(baseline_times[j])
                        # Check if within 5 days window (but not necessarily same DOY)
                        # Actually, we want to add values from dates that are within 5 days of a date with DOY=doy
                        if abs(j_doy - doy) <= 5:
                            pools[doy].extend(baseline_sst[j].flatten())
    
    # Handle day 60 (Feb 29) separately
    # Pool for day 60 includes Feb 28 and Mar 1 values
    pools[60] = []
    for i, date in enumerate(baseline_times):
        dt = date.astype(datetime)
        if (dt.month == 2 and dt.day == 28) or (dt.month == 3 and dt.day == 1):
            pools[60].extend(baseline_sst[i].flatten())
    
    return pools, baseline_times

# More careful approach to calculate thresholds
def calculate_thresholds_and_climatology_v2(sst_data, times, baseline_start, baseline_end):
    """
    Calculate thresholds and climatology correctly
    """
    # Get baseline data
    baseline_mask = (times >= baseline_start) & (times <= baseline_end)
    baseline_times = times[baseline_mask]
    baseline_sst = sst_data[baseline_mask]
    
    print(f"Baseline period: {baseline_times[0]} to {baseline_times[-1]}")
    print(f"Baseline data shape: {baseline_sst.shape}")
    
    # Build pools for each day of year
    pools = {}
    
    # For each day of year 1-366, collect all SST values from dates within ±5 days 
    # of any date with that day of year
    for doy in range(1, 367):
        pools[doy] = []
        
        # Find all dates that fall within 5 days of having this DOY
        for i, date in enumerate(baseline_times):
            date_doy = get_doy_for_datetime64(date)
            
            # We want to include values from dates that are within 5 days of a date with DOY=doy
            # This means we include dates where |date_doy - doy| <= 5
            if abs(date_doy - doy) <= 5:
                pools[doy].extend(baseline_sst[i].flatten())
    
    # Special handling for day 60 (Feb 29)
    # Since Feb 29 doesn't exist in all years, we'll handle it by taking values from 
    # Feb 28 and Mar 1 in leap years
    feb28_mar1_values = []
    for i, date in enumerate(baseline_times):
        dt = date.astype(datetime)
        if (dt.month == 2 and dt.day == 28) or (dt.month == 3 and dt.day == 1):
            feb28_mar1_values.extend(baseline_sst[i].flatten())
    pools[60] = feb28_mar1_values
    
    # Calculate thresholds and climatologies for each day of year
    thresholds = np.full(366, np.nan, dtype=np.float64)
    climatologies = np.full(366, np.nan, dtype=np.float64)
    
    # For each day of year, compute 90th percentile and mean
    for doy in range(1, 367):
        if len(pools[doy]) == 0:
            continue
            
        # Convert to numpy array and remove NaNs
        pool_array = np.array(pools[doy], dtype=np.float64)
        valid_pool = pool_array[~np.isnan(pool_array)]
        
        if len(valid_pool) > 0:
            # Threshold is 90th percentile (Hazen method)
            thresholds[doy-1] = np.percentile(valid_pool, 90, method='hazen')
            
            # Climatology is mean
            climatologies[doy-1] = np.mean(valid_pool)
    
    # Special handling for day 60: set to mean of days 59 and 61
    if not np.isnan(thresholds[58]) and not np.isnan(thresholds[60]):
        thresholds[59] = (thresholds[58] + thresholds[60]) / 2  # Days 59 and 61 average
    if not np.isnan(climatologies[58]) and not np.isnan(climatologies[60]):
        climatologies[59] = (climatologies[58] + climatologies[60]) / 2
    
    # Apply smoothing (31-day centered moving average with wraparound)
    def smooth_366(arr):
        """Smooth a 366-element array with 31-day centered moving average"""
        smoothed = np.zeros_like(arr)
        window_size = 31
        half_window = window_size // 2
        
        for i in range(366):
            # Sum values in window with wraparound
            sum_val = 0
            count = 0
            for j in range(-half_window, half_window + 1):
                idx = (i + j) % 366
                if not np.isnan(arr[idx]):
                    sum_val += arr[idx]
                    count += 1
            if count > 0:
                smoothed[i] = sum_val / count
            else:
                smoothed[i] = np.nan
        return smoothed
    
    # Smooth thresholds and climatologies
    smoothed_thresholds = smooth_366(thresholds)
    smoothed_climatologies = smooth_366(climatologies)
    
    return smoothed_thresholds, smoothed_climatologies, baseline_times[0], baseline_times[-1]

# Calculate thresholds and climatology
print("Calculating thresholds and climatology...")
thresholds, climatologies, baseline_start_used, baseline_end_used = calculate_thresholds_and_climatology_v2(
    sst_data, times, baseline_start, baseline_end)

print(f"Thresholds shape: {thresholds.shape}")
print(f"Climatologies shape: {climatologies.shape}")

# Check some sample values
print("Sample thresholds:", thresholds[:10])
print("Sample climatologies:", climatologies[:10])

# Find sea cells (grid cells with finite SST on every day)
def find_sea_cells(sst_data, latitudes, longitudes):
    """
    Find sea cells (grid cells with finite SST on every day of target period)
    """
    # sst_data shape: (days, lat, lon)
    sea_cells = np.ones((latitudes.shape[0], longitudes.shape[0]), dtype=bool)
    
    # For each grid cell, check if it has finite values on all days
    for i in range(latitudes.shape[0]):
        for j in range(longitudes.shape[0]):
            # Check if all values for this cell are finite
            cell_values = sst_data[:, i, j]
            if np.any(~np.isfinite(cell_values)):
                sea_cells[i, j] = False
                
    return sea_cells

sea_cells = find_sea_cells(sst_data, latitudes, longitudes)
print(f"Number of sea cells: {np.sum(sea_cells)} out of {latitudes.shape[0] * longitudes.shape[0]}")

# Detect MHWs for each sea cell
def detect_mhws_per_cell(sst_data, thresholds, times, sea_cells):
    """
    Detect MHWs for each sea cell
    """
    # sst_data shape: (days, lat, lon)
    # thresholds shape: (366,)
    
    # Initialize MHW mask
    mhw_mask = np.zeros((sst_data.shape[0], sst_data.shape[1], sst_data.shape[2]), dtype=np.uint8)
    
    # For each sea cell, detect MHWs
    for i in range(sst_data.shape[1]):  # lat
        for j in range(sst_data.shape[2]):  # lon
            if not sea_cells[i, j]:  # Skip land cells
                continue
                
            # Get SST for this cell
            cell_sst = sst_data[:, i, j]
            
            # For each day, check if it's hot (>= threshold for that DOY)
            hot_days = np.zeros(len(times), dtype=bool)
            
            for k, (sst_val, time_val) in enumerate(zip(cell_sst, times)):
                if np.isnan(sst_val):
                    continue
                    
                doy = get_doy_for_datetime64(time_val)
                if doy >= 1 and doy <= 366:
                    # Compare with threshold for this day of year
                    if sst_val >= thresholds[doy - 1]:
                        hot_days[k] = True
            
            # Find runs of at least 5 consecutive hot days
            # Use a simple approach to find runs
            mhw_runs = []
            start_idx = None
            
            for k in range(len(hot_days)):
                if hot_days[k] and start_idx is None:
                    start_idx = k
                elif not hot_days[k] and start_idx is not None:
                    # End of a potential MHW
                    if k - start_idx >= 5:
                        mhw_runs.append((start_idx, k - 1))
                    start_idx = None
            
            # Handle case where run continues to end
            if start_idx is not None and len(hot_days) - start_idx >= 5:
                mhw_runs.append((start_idx, len(hot_days) - 1))
            
            # Join gaps of 1 or 2 days
            if len(mhw_runs) > 1:
                merged_runs = [mhw_runs[0]]
                for run in mhw_runs[1:]:
                    last_run = merged_runs[-1]
                    # If gap is 1 or 2 days, merge
                    if run[0] - last_run[1] <= 2:
                        merged_runs[-1] = (last_run[0], run[1])
                    else:
                        merged_runs.append(run)
                mhw_runs = merged_runs
            
            # Mark MHW days in mask
            for start, end in mhw_runs:
                mhw_mask[start:end+1, i, j] = 1
    
    return mhw_mask

print("Detecting MHWs per cell...")
mhw_mask = detect_mhws_per_cell(sst_data, thresholds, times, sea_cells)
print(f"MHW mask shape: {mhw_mask.shape}")

# Create regional events
def create_regional_events(mhw_mask, times):
    """
    Create regional MHW events based on active days
    """
    # mhw_mask shape: (days, lat, lon)
    
    # A day is active if at least one sea cell is inside an MHW
    active_days = np.any(mhw_mask, axis=(1, 2))  # Shape: (days,)
    
    # Find runs of consecutive active days
    events = []
    start_idx = None
    
    for i in range(len(active_days)):
        if active_days[i] and start_idx is None:
            start_idx = i
        elif not active_days[i] and start_idx is not None:
            # End of an event
            events.append((start_idx, i - 1))
            start_idx = None
    
    # Handle case where event continues to end
    if start_idx is not None and len(active_days) - start_idx >= 1:
        events.append((start_idx, len(active_days) - 1))
    
    # Convert indices to dates
    event_list = []
    for start_idx, end_idx in events:
        onset_date = str(times[start_idx]).split('T')[0]
        end_date = str(times[end_idx]).split('T')[0]
        event_list.append({"onset": onset_date, "end": end_date})
    
    return event_list

print("Creating regional events...")
regional_events = create_regional_events(mhw_mask, times)
print(f"Found {len(regional_events)} regional events")

# Prepare output files
print("Preparing output files...")

# Create output directory
os.makedirs('output', exist_ok=True)

# Write mhw_mask.nc
# First, we need to create a proper Dataset with coordinates
output_ds = xr.Dataset(
    {
        'mhw': (['time', 'lat', 'lon'], mhw_mask.astype(np.uint8))
    },
    coords={
        'time': times,
        'lat': latitudes,
        'lon': longitudes
    }
)

# Save to netcdf
output_ds.to_netcdf('output/mhw_mask.nc')
print("Saved mhw_mask.nc")

# Write report.json
report = {
    "region": {
        "lat_min": lat_min,
        "lat_max": lat_max,
        "lon_min": lon_min,
        "lon_max": lon_max
    },
    "baseline_analysed": {
        "start": str(baseline_start_used).split('T')[0],
        "end": str(baseline_end_used).split('T')[0]
    },
    "target_analysed": {
        "start": str(target_start).split('T')[0],
        "end": str(target_end).split('T')[0]
    },
    "events": regional_events,
    "complete": True,
    "caveats": ""
}

with open('output/report.json', 'w') as f:
    json.dump(report, f, indent=2)

print("Saved report.json")

print("Analysis complete!")