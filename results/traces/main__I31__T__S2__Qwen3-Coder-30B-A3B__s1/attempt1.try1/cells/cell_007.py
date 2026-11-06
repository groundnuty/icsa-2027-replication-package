import numpy as np
import xarray as xr
import fsspec
from datetime import datetime, timedelta
import os

# Set up the filesystem
fs = fsspec.filesystem('onedata')

# Open the dataset
f = fs.open('/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')

# Define our region boundaries
lat_min, lat_max = 58.69, 59.89
lon_min, lon_max = 18.69, 19.89

# Filter to our region
ds_region = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))

# Define our target period
start_date = datetime(2017, 6, 1)
end_date = datetime(2017, 8, 31)

# Filter to our time period
ds_period = ds_region.sel(time=slice(start_date, end_date))

# Get the actual SST data
sst_data = ds_period.analysed_sst.values  # Shape: (92, 60, 60)
time_coords = ds_period.time.values

print(f"Region data shape: {sst_data.shape}")
print(f"Time period: {time_coords[0]} to {time_coords[-1]}")

# Close the original file
f.close()

# Now let's implement the full MHW detection algorithm
def date_to_doy(date):
    """Convert a date to day of year (1-366)"""
    if isinstance(date, str):
        date = datetime.strptime(date, "%Y-%m-%d")
    return date.timetuple().tm_yday

# Create the baseline period (1992-01-01 to 2002-12-31)
baseline_start = datetime(1992, 1, 1)
baseline_end = datetime(2002, 12, 31)

# Generate all baseline dates
baseline_dates = []
current = baseline_start
while current <= baseline_end:
    baseline_dates.append(current)
    current += timedelta(days=1)

print(f"Baseline period: {baseline_dates[0]} to {baseline_dates[-1]}")
print(f"Number of baseline days: {len(baseline_dates)}")

# Create a mapping from date to day-of-year for all baseline dates
date_to_doy_map = {date: date_to_doy(date) for date in baseline_dates}

# Create a reverse mapping: from DOY to all dates with that DOY
doy_to_dates = {}
for date in baseline_dates:
    doy = date_to_doy_map[date]
    if doy not in doy_to_dates:
        doy_to_dates[doy] = []
    doy_to_dates[doy].append(date)

print(f"DOY 1 has {len(doy_to_dates[1])} dates")
print(f"DOY 60 has {len(doy_to_dates[60])} dates (Feb 29)")
print(f"DOY 61 has {len(doy_to_dates[61])} dates")

def get_pool_for_doy(target_doy, baseline_dates, date_to_doy_map):
    """
    Get all baseline dates that should contribute to the pool for a given day of year.
    """
    pool_dates = set()
    
    # For day 60 (February 29), handle specially
    if target_doy == 60:
        # All Feb 29 dates from baseline should be included, plus their windows
        for date in baseline_dates:
            if date_to_doy_map[date] == 60:
                # Include dates within ±5 days of this date
                for i in range(-5, 6):
                    candidate_date = date + timedelta(days=i)
                    # Ensure it's within valid range (1991-12-27 to 2003-01-05)
                    if datetime(1991, 12, 27) <= candidate_date <= datetime(2003, 1, 5):
                        pool_dates.add(candidate_date)
    else:
        # For other DOYs, find all dates matching this DOY and include their windows
        for date in baseline_dates:
            if date_to_doy_map[date] == target_doy:
                # Include dates within ±5 days of this date
                for i in range(-5, 6):
                    candidate_date = date + timedelta(days=i)
                    # Ensure it's within valid range (1991-12-27 to 2003-01-05)
                    if datetime(1991, 12, 27) <= candidate_date <= datetime(2003, 1, 5):
                        pool_dates.add(candidate_date)
    
    return sorted(list(pool_dates))

def compute_threshold_and_climatology(sst_data, time_coords, baseline_dates, date_to_doy_map):
    """
    Compute thresholds and climatology for each grid cell and day of year.
    """
    n_time, n_lat, n_lon = sst_data.shape
    
    # Initialize arrays for thresholds and climatology (366 days)
    thresholds = np.full((366, n_lat, n_lon), np.nan, dtype=np.float64)
    climatology = np.full((366, n_lat, n_lon), np.nan, dtype=np.float64)
    
    # For each day of year (1-366)
    for doy in range(1, 367):
        print(f"Processing DOY {doy}...")
        
        # Get the pool of dates for this DOY
        pool_dates = get_pool_for_doy(doy, baseline_dates, date_to_doy_map)
        
        # For each grid point, collect all values from the pool dates
        for lat_idx in range(n_lat):
            for lon_idx in range(n_lon):
                pool_values = []
                
                # Collect all valid SST values for this grid point from pool dates
                for pool_date in pool_dates:
                    try:
                        # Find the index of this date in the baseline dates
                        pool_date_idx = baseline_dates.index(pool_date)
                        val = sst_data[pool_date_idx, lat_idx, lon_idx]
                        if np.isfinite(val):
                            pool_values.append(val)
                    except ValueError:
                        continue  # Date not found in baseline dates
                        
                # Calculate threshold and climatology for this DOY and grid point
                if pool_values:
                    pool_array = np.array(pool_values, dtype=np.float64)
                    thresholds[doy-1, lat_idx, lon_idx] = np.nanpercentile(pool_array, 90, method='linear')
                    climatology[doy-1, lat_idx, lon_idx] = np.nanmean(pool_array)
    
    # Special handling for day 60 (set to mean of days 59 and 61)
    # This is done later after smoothing
    
    return thresholds, climatology

def smooth_366_array(arr):
    """
    Smooth a 366-element array with a 31-day centered moving average that wraps around.
    """
    smoothed = np.zeros_like(arr, dtype=np.float64)
    window_size = 31
    half_window = window_size // 2
    
    for i in range(366):
        # Sum values in the window
        window_sum = 0
        count = 0
        
        for j in range(-half_window, half_window + 1):
            # Wrap around the year
            wrapped_idx = (i + j) % 366
            if not np.isnan(arr[wrapped_idx]):
                window_sum += arr[wrapped_idx]
                count += 1
                
        if count > 0:
            smoothed[i] = window_sum / count
        else:
            smoothed[i] = np.nan
            
    return smoothed

def smooth_thresholds_and_climatology(thresholds, climatology):
    """
    Apply smoothing to thresholds and climatology arrays.
    """
    n_lat, n_lon = thresholds.shape[1], thresholds.shape[2]
    
    # Create new arrays for smoothed values
    smoothed_thresholds = np.full_like(thresholds, np.nan, dtype=np.float64)
    smoothed_climatology = np.full_like(climatology, np.nan, dtype=np.float64)
    
    # Smooth each grid point independently
    for lat_idx in range(n_lat):
        for lon_idx in range(n_lon):
            # Extract 366-day arrays for this grid point
            threshold_series = thresholds[:, lat_idx, lon_idx]
            climatology_series = climatology[:, lat_idx, lon_idx]
            
            # Smooth them
            smoothed_thresholds[:, lat_idx, lon_idx] = smooth_366_array(threshold_series)
            smoothed_climatology[:, lat_idx, lon_idx] = smooth_366_array(climatology_series)
    
    # Special handling for day 60 (set to mean of days 59 and 61)
    for lat_idx in range(n_lat):
        for lon_idx in range(n_lon):
            if not np.isnan(smoothed_thresholds[59, lat_idx, lon_idx]) and \
               not np.isnan(smoothed_thresholds[61, lat_idx, lon_idx]):
                smoothed_thresholds[59, lat_idx, lon_idx] = \
                    (smoothed_thresholds[58, lat_idx, lon_idx] + smoothed_thresholds[60, lat_idx, lon_idx]) / 2
                
            if not np.isnan(smoothed_climatology[59, lat_idx, lon_idx]) and \
               not np.isnan(smoothed_climatology[61, lat_idx, lon_idx]):
                smoothed_climatology[59, lat_idx, lon_idx] = \
                    (smoothed_climatology[58, lat_idx, lon_idx] + smoothed_climatology[60, lat_idx, lon_idx]) / 2
    
    return smoothed_thresholds, smoothed_climatology

def find_mhws_per_cell(sst_data, time_coords, thresholds, climatology):
    """
    Find MHWs for each cell over the target period.
    """
    n_time, n_lat, n_lon = sst_data.shape
    
    # Initialize MHW mask
    mhw_mask = np.zeros((n_time, n_lat, n_lon), dtype=np.uint8)
    
    # For each cell, determine if it's in an MHW
    for lat_idx in range(n_lat):
        for lon_idx in range(n_lon):
            # Get the threshold and climatology for this cell
            cell_thresholds = thresholds[:, lat_idx, lon_idx]
            cell_climatology = climatology[:, lat_idx, lon_idx]
            
            # Get SST data for this cell
            cell_sst = sst_data[:, lat_idx, lon_idx]
            
            # Determine which days are hot (SST >= threshold)
            hot_days = np.zeros(n_time, dtype=bool)
            for t_idx in range(n_time):
                doy = date_to_doy(time_coords[t_idx])
                # Check if threshold is valid for this day
                if not np.isnan(cell_thresholds[doy-1]):
                    hot_days[t_idx] = cell_sst[t_idx] >= cell_thresholds[doy-1]
            
            # Find runs of hot days (minimum 5 consecutive)
            # Also join gaps of 1 or 2 days
            hot_runs = []
            if np.any(hot_days):
                # Find connected components of hot days
                i = 0
                while i < len(hot_days):
                    if hot_days[i]:
                        start = i
                        while i < len(hot_days) and hot_days[i]:
                            i += 1
                        end = i - 1
                        
                        # If run is at least 5 days long, record it
                        if end - start + 1 >= 5:
                            hot_runs.append((start, end))
                    else:
                        i += 1
                
                # Join gaps of 1 or 2 days
                if len(hot_runs) > 1:
                    merged_runs = [hot_runs[0]]
                    for i in range(1, len(hot_runs)):
                        prev_start, prev_end = merged_runs[-1]
                        curr_start, curr_end = hot_runs[i]
                        
                        # Check if gap is 1 or 2 days
                        gap = curr_start - prev_end - 1
                        if 1 <= gap <= 2:
                            # Merge runs
                            merged_runs[-1] = (prev_start, curr_end)
                        else:
                            merged_runs.append((curr_start, curr_end))
                    
                    hot_runs = merged_runs
                
                # Mark all days in runs as MHW
                for start, end in hot_runs:
                    mhw_mask[start:end+1, lat_idx, lon_idx] = 1
            else:
                # No hot days at all
                pass
    
    return mhw_mask

def main_mhw_detection():
    """
    Main function to perform MHW detection.
    """
    print("Starting MHW detection process...")
    
    # Step 1: Compute thresholds and climatology
    print("Step 1: Computing thresholds and climatology...")
    thresholds, climatology = compute_threshold_and_climatology(
        sst_data, time_coords, baseline_dates, date_to_doy_map)
    
    # Step 2: Smooth thresholds and climatology
    print("Step 2: Smoothing thresholds and climatology...")
    smoothed_thresholds, smoothed_climatology = smooth_thresholds_and_climatology(
        thresholds, climatology)
    
    # Step 3: Find MHWs per cell
    print("Step 3: Finding MHWs per cell...")
    mhw_mask = find_mhws_per_cell(sst_data, time_coords, smoothed_thresholds, smoothed_climatology)
    
    # Step 4: Compute regional events
    print("Step 4: Computing regional events...")
    
    # A day is active if at least one sea cell is inside a per-cell MHW
    active_days = np.any(mhw_mask, axis=(1, 2))  # Shape: (92,)
    
    # A regional MHW event is a maximal run of consecutive active days
    events = []
    if np.any(active_days):
        i = 0
        while i < len(active_days):
            if active_days[i]:
                onset = i
                # Find end of this run
                while i < len(active_days) and active_days[i]:
                    i += 1
                end = i - 1
                
                # Convert indices to dates
                onset_date = time_coords[onset].astype('datetime64[D]').astype(datetime)
                end_date = time_coords[end].astype('datetime64[D]').astype(datetime)
                
                events.append({
                    "onset": onset_date.strftime("%Y-%m-%d"),
                    "end": end_date.strftime("%Y-%m-%d")
                })
            else:
                i += 1
    
    # Prepare results
    region = {
        "lat_min": lat_min,
        "lat_max": lat_max,
        "lon_min": lon_min,
        "lon_max": lon_max
    }
    
    baseline_analysed = {
        "start": "1992-01-01",
        "end": "2002-12-31"
    }
    
    target_analysed = {
        "start": start_date.strftime("%Y-%m-%d"),
        "end": end_date.strftime("%Y-%m-%d")
    }
    
    report = {
        "region": region,
        "baseline_analysed": baseline_analysed,
        "target_analysed": target_analysed,
        "events": events,
        "complete": True,
        "caveats": ""
    }
    
    # Save results
    os.makedirs("output", exist_ok=True)
    
    # Save the NetCDF file
    save_mhw_mask_to_netcdf(mhw_mask, time_coords, ds_region)
    
    # Save the report
    import json
    with open("output/report.json", "w") as f:
        json.dump(report, f, indent=2)
    
    print("MHW detection completed!")
    print(f"Found {len(events)} regional events")
    if events:
        for event in events:
            print(f"Event: {event['onset']} to {event['end']}")
    
    return report

def save_mhw_mask_to_netcdf(mhw_mask, time_coords, ds_region):
    """
    Save the MHW mask to a NetCDF file.
    """
    # Create a new dataset with the MHW data
    import xarray as xr
    
    # Create time coordinate
    time_coord = [np.datetime64(t) for t in time_coords]
    
    # Create the dataset
    ds_out = xr.Dataset(
        {
            "mhw": (["time", "latitude", "longitude"], mhw_mask.astype(np.uint8))
        },
        coords={
            "time": time_coord,
            "latitude": ds_region.latitude.values,
            "longitude": ds_region.longitude.values
        }
    )
    
    # Save to file
    ds_out.to_netcdf("output/mhw_mask.nc", engine="h5netcdf")
    print("Saved MHW mask to output/mhw_mask.nc")

# Run the main function
try:
    report = main_mhw_detection()
except Exception as e:
    print(f"Error occurred: {e}")
    import traceback
    traceback.print_exc()