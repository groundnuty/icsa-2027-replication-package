import xarray as xr
import numpy as np
from datetime import datetime
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

# Close the original dataset
ds.close()

# Helper function to convert date to day of year
def date_to_doy(date_val):
    """Convert datetime64 to day of year"""
    # Convert to Python datetime
    if hasattr(date_val, 'astype'):
        # It's a numpy datetime64
        date_obj = datetime.utcfromtimestamp(date_val.astype('datetime64[s]').astype('int'))
    else:
        date_obj = date_val
    return date_obj.timetuple().tm_yday

# Process data in a memory-efficient manner
print("Starting MHW analysis...")

# Step 1: Identify sea cells (cells with finite SST on every day of target period)
print("Identifying sea cells...")
# Reopen dataset to process this step
ds = xr.open_dataset('/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', engine='h5netcdf')

# Get subset for target period
target_subset = ds.analysed_sst.sel(
    latitude=slice(lat_min, lat_max),
    longitude=slice(lon_min, lon_max),
    time=slice(target_start, target_end)
)

# Create a mask for sea cells
n_lat, n_lon = target_subset.latitude.size, target_subset.longitude.size
sea_cells = np.ones((n_lat, n_lon), dtype=bool)

# Check for each cell if it has finite SST on all days
for lat_idx in range(n_lat):
    for lon_idx in range(n_lon):
        # Extract all SST values for this cell
        sst_values = target_subset.isel(latitude=lat_idx, longitude=lon_idx).values
        # Check if all values are finite
        if np.all(np.isfinite(sst_values)):
            sea_cells[lat_idx, lon_idx] = True
        else:
            sea_cells[lat_idx, lon_idx] = False

print(f"Number of sea cells: {np.sum(sea_cells)}")

# Close dataset for now
ds.close()

# Step 2: Compute thresholds and climatology efficiently
print("Computing thresholds and climatology...")

# Reopen dataset for baseline processing
ds = xr.open_dataset('/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', engine='h5netcdf')

# Get baseline subset
baseline_subset = ds.analysed_sst.sel(
    latitude=slice(lat_min, lat_max),
    longitude=slice(lon_min, lon_max),
    time=slice(baseline_start, baseline_end)
)

# Process baseline data day by day to build pools
print("Building baseline pools...")

# Create mapping from date to day of year for baseline dates
doy_map = {}
for date in baseline_times.values:
    # Convert to datetime object for doy calculation
    if isinstance(date, np.datetime64):
        date_obj = datetime.utcfromtimestamp(date.astype('datetime64[s]').astype('int'))
    else:
        date_obj = date
    doy = date_obj.timetuple().tm_yday
    doy_map[str(date)] = doy

# Initialize arrays for thresholds and climatologies
n_lat, n_lon = baseline_subset.latitude.size, baseline_subset.longitude.size
thresholds = np.full((366, n_lat, n_lon), np.nan, dtype=np.float64)
climatologies = np.full((366, n_lat, n_lon), np.nan, dtype=np.float64)

# For each day of year, collect data and compute statistics
print("Processing day-of-year groups...")

# Process each day of year separately
for doy in range(1, 367):
    if doy == 60:  # Skip Feb 29th for now, will handle specially
        continue
    
    # Collect all dates that correspond to this doy
    matching_dates = []
    for date in baseline_times.values:
        if doy_map.get(str(date), 0) == doy:
            matching_dates.append(date)
    
    print(f"Day {doy}: Found {len(matching_dates)} matching dates")
    
    # For each location, collect all valid SST values for this doy
    for lat_idx in range(n_lat):
        for lon_idx in range(n_lon):
            pool_values = []
            for date in matching_dates:
                # Get the SST value for this date and location
                sst_val = baseline_subset.sel(time=date, latitude=baseline_subset.latitude[lat_idx], longitude=baseline_subset.longitude[lon_idx]).values
                if np.isfinite(sst_val):
                    pool_values.append(sst_val)
            
            # Compute statistics if we have values
            if len(pool_values) > 0:
                threshold = np.quantile(pool_values, 0.9, method='hazen')
                climatology = np.mean(pool_values)
                thresholds[doy-1, lat_idx, lon_idx] = threshold
                climatologies[doy-1, lat_idx, lon_idx] = climatology

# Handle Feb 29th (day 60) - set to mean of days 59 and 61
print("Handling Feb 29th...")
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
print("Smoothing arrays...")
def smooth_366_array(arr):
    """Smooth a 366-element array with 31-day moving average"""
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

smoothed_thresholds = smooth_366_array(thresholds)
smoothed_climatologies = smooth_366_array(climatologies)

# Close baseline dataset
ds.close()

# Step 3: Find hot days in target period
print("Finding hot days...")

# Reopen dataset for target period processing
ds = xr.open_dataset('/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', engine='h5netcdf')

# Get target subset
target_subset = ds.analysed_sst.sel(
    latitude=slice(lat_min, lat_max),
    longitude=slice(lon_min, lon_max),
    time=slice(target_start, target_end)
)

# Initialize hot days mask
hot_days = np.zeros((len(target_times), n_lat, n_lon), dtype=bool)

# Process each day in target period
for day_idx, date in enumerate(target_times.values):
    # Convert date to day of year
    if isinstance(date, np.datetime64):
        date_obj = datetime.utcfromtimestamp(date.astype('datetime64[s]').astype('int'))
    else:
        date_obj = date
    doy = date_obj.timetuple().tm_yday
    
    print(f"Processing day {day_idx+1}/{len(target_times)} (DOY {doy})")
    
    # For each cell
    for lat_idx in range(n_lat):
        for lon_idx in range(n_lon):
            # Get SST value
            sst_val = target_subset.isel(time=day_idx, latitude=lat_idx, longitude=lon_idx).values
            
            # Get threshold value
            threshold_val = smoothed_thresholds[doy-1, lat_idx, lon_idx]  # doy-1 because 0-indexed
            
            # Check if it's hot
            if np.isfinite(sst_val) and np.isfinite(threshold_val):
                if sst_val >= threshold_val:
                    hot_days[day_idx, lat_idx, lon_idx] = True

# Close dataset
ds.close()

# Step 4: Identify MHWs
print("Identifying MHWs...")

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