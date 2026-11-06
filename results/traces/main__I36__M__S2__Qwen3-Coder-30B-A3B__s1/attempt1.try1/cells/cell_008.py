import xarray as xr
import numpy as np
from datetime import datetime, timedelta
import os

# Create output directory
os.makedirs('output', exist_ok=True)

# Open the dataset
ds = xr.open_dataset('/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', engine='h5netcdf')

# Define region of interest
lat_min, lat_max = 60.09, 61.29
lon_min, lon_max = 20.01, 21.21

# Find indices for the region
lat_indices = np.where((ds.latitude >= lat_min) & (ds.latitude <= lat_max))[0]
lon_indices = np.where((ds.longitude >= lon_min) & (ds.longitude <= lon_max))[0]

print(f"Region indices - Latitude: {lat_indices[0]} to {lat_indices[-1]}, Longitude: {lon_indices[0]} to {lon_indices[-1]}")

# Get the subset of data for our region
subset = ds.analysed_sst.isel(latitude=lat_indices, longitude=lon_indices)
print(f"Subset shape: {subset.shape}")

# Define periods
target_start = np.datetime64('2003-06-01')
target_end = np.datetime64('2003-08-31')
baseline_start = np.datetime64('1992-01-01')
baseline_end = np.datetime64('2002-12-31')

# Filter for baseline period
baseline_mask = (ds.time >= baseline_start) & (ds.time <= baseline_end)
baseline_times = ds.time[baseline_mask]
print(f"Baseline period: {baseline_times[0].values} to {baseline_times[-1].values}")
print(f"Number of baseline days: {len(baseline_times)}")

# Filter for target period  
target_mask = (ds.time >= target_start) & (ds.time <= target_end)
target_times = ds.time[target_mask]
print(f"Target period: {target_times[0].values} to {target_times[-1].values}")
print(f"Number of target days: {len(target_times)}")

# Extract SST data for baseline and target periods
baseline_sst = ds.analysed_sst.sel(time=baseline_times).values
target_sst = ds.analysed_sst.sel(time=target_times).values

print(f"Baseline SST shape: {baseline_sst.shape}")
print(f"Target SST shape: {target_sst.shape}")

# Close the original dataset
ds.close()

# Now let's implement the core algorithm step by step
print("Starting MHW analysis...")

# Helper function to convert date to day of year
def date_to_doy(date_val):
    """Convert datetime64 to day of year"""
    date_obj = datetime.utcfromtimestamp(date_val.astype('datetime64[s]').astype('int'))
    return date_obj.timetuple().tm_yday

# Create mapping from date to day of year for baseline dates
doy_map = {}
for date in baseline_times.values:
    doy = date_to_doy(date)
    doy_map[str(date)] = doy

# Step 1: Identify sea cells (cells with finite SST on every day of target period)
def detect_sea_cells(sst_data, target_dates):
    """Identify sea cells (cells with finite SST on every day of target period)"""
    n_days, n_lat, n_lon = sst_data.shape
    sea_cells = np.ones((n_lat, n_lon), dtype=bool)
    
    for lat_idx in range(n_lat):
        for lon_idx in range(n_lon):
            # Check if all days have finite SST
            for day_idx in range(n_days):
                if not np.isfinite(sst_data[day_idx, lat_idx, lon_idx]):
                    sea_cells[lat_idx, lon_idx] = False
                    break
                    
    return sea_cells

sea_cells = detect_sea_cells(target_sst, target_times.values)
print(f"Number of sea cells: {np.sum(sea_cells)}")

# Step 2: Compute thresholds and climatology using baseline period
def compute_threshold_and_climatology(sst_data, baseline_dates, doy_map):
    """
    Compute thresholds and climatology for each day of year
    """
    n_lat, n_lon = sst_data.shape[1], sst_data.shape[2]
    n_doy = 366
    
    # Initialize arrays
    thresholds = np.full((n_doy, n_lat, n_lon), np.nan, dtype=np.float64)
    climatologies = np.full((n_doy, n_lat, n_lon), np.nan, dtype=np.float64)
    
    # Create a mapping from date to index in baseline_dates
    date_to_index = {str(date): i for i, date in enumerate(baseline_dates)}
    
    # Process each day of year
    for doy in range(1, 367):  # Days 1-366
        if doy == 60:  # February 29th - special handling
            continue
            
        # Collect all data points for this day of year
        pool_values = []
        
        # Go through all baseline dates and collect those matching this doy
        for date in baseline_dates:
            date_str = str(date)
            if date_str in doy_map and doy_map[date_str] == doy:
                # Collect SST values for this date at all locations
                for lat_idx in range(n_lat):
                    for lon_idx in range(n_lon):
                        val = sst_data[date_to_index[date_str], lat_idx, lon_idx]
                        if np.isfinite(val):
                            pool_values.append(val)
        
        if len(pool_values) > 0:
            # Compute 90th percentile (Hazen method) 
            threshold = np.quantile(pool_values, 0.9, method='hazen')
            # Compute mean
            climatology = np.mean(pool_values)
            
            # This is a simplified approach - in practice we'd assign to each position
            # But since we're computing for each day of year, we'll just store one value
            # We'll handle individual positions later in a more detailed way
            
    # For now, let's implement a more practical version that works with actual arrays
    # Create a proper implementation that assigns values to specific positions
    thresholds = np.full((n_doy, n_lat, n_lon), np.nan, dtype=np.float64)
    climatologies = np.full((n_doy, n_lat, n_lon), np.nan, dtype=np.float64)
    
    # Create mapping of doy -> list of dates for that doy
    doy_to_dates = {}
    for date in baseline_dates:
        date_str = str(date)
        doy = doy_map[date_str]
        if doy not in doy_to_dates:
            doy_to_dates[doy] = []
        doy_to_dates[doy].append(date)
    
    # For each day of year, compute thresholds and climatologies for each location
    for doy in range(1, 367):
        if doy == 60:  # Special case for Feb 29
            continue
            
        # Collect all valid SST values for this doy across all locations
        pool_by_location = {}  # { (lat, lon): [values] }
        
        for date in doy_to_dates.get(doy, []):
            date_idx = date_to_index[str(date)]
            for lat_idx in range(n_lat):
                for lon_idx in range(n_lon):
                    val = sst_data[date_idx, lat_idx, lon_idx]
                    if np.isfinite(val):
                        if (lat_idx, lon_idx) not in pool_by_location:
                            pool_by_location[(lat_idx, lon_idx)] = []
                        pool_by_location[(lat_idx, lon_idx)].append(val)
        
        # Assign thresholds and climatologies for each location
        for (lat_idx, lon_idx), values in pool_by_location.items():
            if len(values) > 0:
                threshold = np.quantile(values, 0.9, method='hazen')
                climatology = np.mean(values)
                thresholds[doy-1, lat_idx, lon_idx] = threshold
                climatologies[doy-1, lat_idx, lon_idx] = climatology
    
    # Handle February 29th (day 60) - set to mean of days 59 and 61
    for lat_idx in range(n_lat):
        for lon_idx in range(n_lon):
            if (np.isfinite(thresholds[58, lat_idx, lon_idx]) and 
                np.isfinite(thresholds[60, lat_idx, lon_idx])):
                thresholds[59, lat_idx, lon_idx] = (thresholds[58, lat_idx, lon_idx] + 
                                                   thresholds[60, lat_idx, lon_idx]) / 2
            elif np.isfinite(thresholds[58, lat_idx, lon_idx]):
                thresholds[59, lat_idx, lon_idx] = thresholds[58, lat_idx, lon_idx]
            elif np.isfinite(thresholds[60, lat_idx, lon_idx]):
                thresholds[59, lat_idx, lon_idx] = thresholds[60, lat_idx, lon_idx]
                
            if (np.isfinite(climatologies[58, lat_idx, lon_idx]) and 
                np.isfinite(climatologies[60, lat_idx, lon_idx])):
                climatologies[59, lat_idx, lon_idx] = (climatologies[58, lat_idx, lon_idx] + 
                                                      climatologies[60, lat_idx, lon_idx]) / 2
            elif np.isfinite(climatologies[58, lat_idx, lon_idx]):
                climatologies[59, lat_idx, lon_idx] = climatologies[58, lat_idx, lon_idx]
            elif np.isfinite(climatologies[60, lat_idx, lon_idx]):
                climatologies[59, lat_idx, lon_idx] = climatologies[60, lat_idx, lon_idx]
    
    # Smooth with 31-day moving average (wrapping around)
    smoothed_thresholds = smooth_366_array(thresholds)
    smoothed_climatologies = smooth_366_array(climatologies)
    
    return smoothed_thresholds, smoothed_climatologies

def smooth_366_array(arr):
    """Smooth a 366-element array with 31-day moving average"""
    n_lat, n_lon = arr.shape[1], arr.shape[2]
    result = np.full_like(arr, np.nan, dtype=np.float64)
    
    # For each location
    for lat_idx in range(n_lat):
        for lon_idx in range(n_lon):
            # For each day of year
            for doy in range(366):
                # Compute the sum for the 31-day window (15 before, 15 after)
                window_sum = 0.0
                count = 0
                
                for i in range(-15, 16):  # -15 to +15 inclusive
                    adj_doy = (doy + i) % 366  # Wrap around
                    if np.isfinite(arr[adj_doy, lat_idx, lon_idx]):
                        window_sum += arr[adj_doy, lat_idx, lon_idx]
                        count += 1
                        
                if count > 0:
                    result[doy, lat_idx, lon_idx] = window_sum / count
                    
    return result

# Step 2: Compute thresholds and climatology
print("Computing thresholds and climatology...")
thresholds, climatologies = compute_threshold_and_climatology(
    baseline_sst, baseline_times.values, doy_map
)

# Step 3: Find hot days in target period
def find_hot_days(sst_data, thresholds, climatologies, target_dates, doy_map):
    """Find hot days for each cell and day"""
    n_days, n_lat, n_lon = sst_data.shape
    hot_days = np.zeros((n_days, n_lat, n_lon), dtype=bool)
    
    for day_idx in range(n_days):
        date = target_dates[day_idx]
        doy = doy_map[str(date)]
        
        # For each cell
        for lat_idx in range(n_lat):
            for lon_idx in range(n_lon):
                sst_val = sst_data[day_idx, lat_idx, lon_idx]
                threshold_val = thresholds[doy-1, lat_idx, lon_idx]  # doy-1 because 0-indexed
                
                if np.isfinite(sst_val) and np.isfinite(threshold_val):
                    if sst_val >= threshold_val:
                        hot_days[day_idx, lat_idx, lon_idx] = True
                        
    return hot_days

print("Finding hot days...")
hot_days = find_hot_days(target_sst, thresholds, climatologies, target_times.values, doy_map)

# Step 4: Identify MHWs
def identify_mhws(hot_days, min_duration=5):
    """Identify MHWs from hot days"""
    n_days, n_lat, n_lon = hot_days.shape
    mhw_mask = np.zeros((n_days, n_lat, n_lon), dtype=np.uint8)
    
    # For each cell
    for lat_idx in range(n_lat):
        for lon_idx in range(n_lon):
            # Find runs of hot days
            hot_runs = []
            current_run_start = None
            
            for day_idx in range(n_days):
                if hot_days[day_idx, lat_idx, lon_idx]:
                    if current_run_start is None:
                        current_run_start = day_idx
                else:
                    if current_run_start is not None:
                        # End of a run
                        if day_idx - current_run_start >= min_duration:
                            hot_runs.append((current_run_start, day_idx - 1))
                        current_run_start = None
            
            # Don't forget the last run if it continues to the end
            if current_run_start is not None:
                if n_days - current_run_start >= min_duration:
                    hot_runs.append((current_run_start, n_days - 1))
            
            # Join gaps of 1 or 2 days
            if len(hot_runs) > 1:
                merged_runs = [hot_runs[0]]
                for i in range(1, len(hot_runs)):
                    prev_end = merged_runs[-1][1]
                    curr_start = hot_runs[i][0]
                    
                    # If gap is 1 or 2 days, join them
                    if curr_start - prev_end <= 2:
                        merged_runs[-1] = (merged_runs[-1][0], hot_runs[i][1])
                    else:
                        merged_runs.append(hot_runs[i])
                
                hot_runs = merged_runs
            
            # Mark the MHW days in the mask
            for start_day, end_day in hot_runs:
                for day_idx in range(start_day, end_day + 1):
                    mhw_mask[day_idx, lat_idx, lon_idx] = 1
                    
    return mhw_mask

print("Identifying MHWs...")
mhw_mask = identify_mhws(hot_days)

# Step 5: Create regional events
print("Creating regional events...")
# A day is active if at least one sea cell is inside an MHW
active_days = np.any(mhw_mask, axis=(1,2))  # Shape: (n_target_days,)

# Find regional MHW events (maximal runs of consecutive active days)
events = []
start_event = None
for i, is_active in enumerate(active_days):
    if is_active and start_event is None:
        start_event = i
    elif not is_active and start_event is not None:
        # End of an event
        events.append((start_event, i-1))
        start_event = None

# Don't forget a possible ongoing event at the end
if start_event is not None:
    events.append((start_event, len(active_days)-1))

# Convert to proper date format for reporting
event_list = []
for start_idx, end_idx in events:
    start_date = str(target_times[start_idx].values)[:10]
    end_date = str(target_times[end_idx].values)[:10]
    event_list.append({"onset": start_date, "end": end_date})

# Prepare report
report = {
    "region": {
        "lat_min": lat_min,
        "lat_max": lat_max,
        "lon_min": lon_min,
        "lon_max": lon_max
    },
    "baseline_analysed": {
        "start": str(baseline_start)[:10],
        "end": str(baseline_end)[:10]
    },
    "target_analysed": {
        "start": str(target_start)[:10],
        "end": str(target_end)[:10]
    },
    "events": event_list,
    "complete": True,
    "caveats": ""
}

# Save the report
import json
with open('output/report.json', 'w') as f:
    json.dump(report, f, indent=2)

# Save the NetCDF file
# Reopen dataset to get the proper coordinates
ds_full = xr.open_dataset('/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', engine='h5netcdf')

# Get coordinates for our subset
lat_vals = ds_full.latitude.isel(latitude=lat_indices).values
lon_vals = ds_full.longitude.isel(longitude=lon_indices).values
time_vals = target_times.values

# Create the dataset
mhw_ds = xr.Dataset(
    {
        'mhw': (['time', 'lat', 'lon'], mhw_mask)
    },
    coords={
        'time': time_vals,
        'lat': lat_vals,
        'lon': lon_vals
    }
)

# Set attributes
mhw_ds['mhw'].attrs['units'] = 'binary'
mhw_ds['mhw'].attrs['long_name'] = 'Marine Heatwave indicator'

# Save to NetCDF
mhw_ds.to_netcdf('output/mhw_mask.nc')

print("Analysis complete!")
print(f"Events detected: {len(event_list)}")
print(f"Report saved to output/report.json")
print(f"MHW mask saved to output/mhw_mask.nc")

# Close datasets
ds_full.close()