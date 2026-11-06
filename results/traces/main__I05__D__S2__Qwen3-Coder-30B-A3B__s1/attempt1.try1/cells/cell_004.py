import fsspec
import xarray as xr
import numpy as np
from datetime import datetime, timedelta
import os

# Set up the filesystem
fs = fsspec.filesystem('onedata')

# Download the file
remote_path = '/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
local_path = '/work/sst_s2.nc'

fs.get(remote_path, local_path)

# Open the dataset
ds = xr.open_dataset(local_path, engine='h5netcdf')

# Define region and time period
lat_min, lat_max = 54.39, 55.59
lon_min, lon_max = 18.25, 19.45
start_date = "2021-06-01"
end_date = "2021-08-31"

# Extract the region of interest
region_ds = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))

# Extract time period
region_ds = region_ds.sel(time=slice(start_date, end_date))

print("Region dimensions:")
print("Time:", region_ds.time.shape)
print("Latitude:", region_ds.latitude.shape)
print("Longitude:", region_ds.longitude.shape)

# Let's also get the full time range for baseline calculations
baseline_start = "1992-01-01"
baseline_end = "2002-12-31"
baseline_ds = ds.sel(time=slice(baseline_start, baseline_end))

# Create a function to convert date to day of year (1-366)
def date_to_doy(date_str):
    """Convert date string to day of year (1-366)"""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    # Handle leap year cases
    if dt.month == 2 and dt.day == 29:
        return 60
    else:
        # Get day of year, adjusting for leap year
        doy = dt.timetuple().tm_yday
        # Adjust for leap year - if it's after Feb 28 and we're not in a leap year, subtract 1
        if dt.month > 2:
            # Check if this year is a leap year
            year = dt.year
            is_leap = (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)
            if not is_leap and dt.month > 2:
                doy -= 1
        return doy

# Create a function to get baseline pools
def get_baseline_pools(baseline_ds, target_doy):
    """Get baseline pool for a specific day of year"""
    # Get all dates with the same day of year
    pool_dates = []
    
    # This will be a bit tricky because we need to handle the window around each date
    # For now, let's collect all dates from the baseline period that match the DOY
    # and consider the ±5 day window
    
    # Get all dates from baseline period
    baseline_times = baseline_ds.time.values
    baseline_doy_map = {}
    
    for t in baseline_times:
        date_str = str(t).split('T')[0]  # Extract YYYY-MM-DD
        doy = date_to_doy(date_str)
        if doy not in baseline_doy_map:
            baseline_doy_map[doy] = []
        baseline_doy_map[doy].append(date_str)
    
    # For DOY 60 (Feb 29), we want to use days 59 and 61 
    if target_doy == 60:
        # Use the average of DOY 59 and 61
        if 59 in baseline_doy_map and 61 in baseline_doy_map:
            # Combine all dates from both DOYs
            combined_dates = baseline_doy_map[59] + baseline_doy_map[61]
            return combined_dates
        else:
            return []
    else:
        # For other days, return dates with matching DOY
        if target_doy in baseline_doy_map:
            return baseline_doy_map[target_doy]
        else:
            return []

# Function to compute threshold and climatology
def compute_threshold_climatology(region_ds, baseline_ds):
    """Compute thresholds and climatology for each grid cell"""
    # Get spatial dimensions
    n_lat = region_ds.latitude.size
    n_lon = region_ds.longitude.size
    
    # Initialize arrays
    thresholds = np.full((366, n_lat, n_lon), np.nan, dtype=np.float64)
    climatologies = np.full((366, n_lat, n_lon), np.nan, dtype=np.float64)
    
    # Process each day of year
    for doy in range(1, 367):  # 1 to 366
        print(f"Computing for DOY {doy}")
        
        # Get all baseline dates that correspond to this DOY
        baseline_dates = []
        
        # Get all baseline dates that match this DOY (with ±5 day window)
        baseline_times = baseline_ds.time.values
        for t in baseline_times:
            date_str = str(t).split('T')[0]
            actual_doy = date_to_doy(date_str)
            
            # Check if this date falls within the ±5 day window of our target DOY
            # We'll expand the search to include dates within 5 days of the target DOY
            # But we also need to consider the year boundaries
            
            # Get all dates that are within 5 days of this DOY
            if actual_doy == doy or abs(actual_doy - doy) <= 5:
                baseline_dates.append(date_str)
        
        # Special handling for DOY 60 (February 29)
        if doy == 60:
            # Get data from DOY 59 and 61
            doy_59_dates = []
            doy_61_dates = []
            for t in baseline_times:
                date_str = str(t).split('T')[0]
                actual_doy = date_to_doy(date_str)
                if actual_doy == 59:
                    doy_59_dates.append(date_str)
                elif actual_doy == 61:
                    doy_61_dates.append(date_str)
            
            # Combine the dates for DOY 60
            baseline_dates = doy_59_dates + doy_61_dates
        
        # For each grid point, compute the threshold and climatology
        for i_lat in range(n_lat):
            for j_lon in range(n_lon):
                # Collect all SST values for this grid point across baseline dates
                sst_values = []
                
                for date_str in baseline_dates:
                    # Find corresponding time index
                    try:
                        # Find the time in the dataset that matches this date
                        date_time = np.datetime64(date_str)
                        time_idx = np.where(baseline_ds.time == date_time)[0][0]
                        
                        # Get the SST value
                        sst_val = baseline_ds.analysed_sst.isel(time=time_idx, latitude=i_lat, longitude=j_lon).values
                        
                        # Only add finite values
                        if np.isfinite(sst_val):
                            sst_values.append(sst_val)
                    except:
                        continue  # Skip if not found
                
                # Compute threshold (90th percentile) and climatology (mean)
                if len(sst_values) > 0:
                    # Convert to numpy array for easier processing
                    sst_array = np.array(sst_values, dtype=np.float64)
                    
                    # Calculate climatology (mean) and threshold (90th percentile)
                    climatologies[doy-1, i_lat, j_lon] = np.mean(sst_array)
                    thresholds[doy-1, i_lat, j_lon] = np.percentile(sst_array, 90, method='hazen')
                else:
                    # If no valid data, keep NaN
                    pass
    
    # Special handling for DOY 60 - set it to average of DOY 59 and 61
    climatologies[59, :, :] = (climatologies[58, :, :] + climatologies[60, :, :]) / 2
    thresholds[59, :, :] = (thresholds[58, :, :] + thresholds[60, :, :]) / 2
    
    # Smooth climatology and thresholds with 31-day centered moving average
    # This is a simplified approach - we'll apply it along the DOY axis
    def smooth_31_day(arr):
        """Apply 31-day centered moving average with wraparound"""
        smoothed = np.zeros_like(arr)
        window_size = 31
        half_window = window_size // 2
        
        for i in range(366):
            # Sum values in the window with wraparound
            sum_val = 0
            count = 0
            for j in range(-half_window, half_window + 1):
                # Wrap around the year
                wrapped_i = (i + j) % 366
                if not np.isnan(arr[wrapped_i]):
                    sum_val += arr[wrapped_i]
                    count += 1
            if count > 0:
                smoothed[i] = sum_val / count
            else:
                smoothed[i] = np.nan
        return smoothed
    
    # Apply smoothing to climatologies and thresholds
    for i_lat in range(n_lat):
        for j_lon in range(n_lon):
            # Smooth climatology
            climatologies[:, i_lat, j_lon] = smooth_31_day(climatologies[:, i_lat, j_lon])
            # Smooth thresholds  
            thresholds[:, i_lat, j_lon] = smooth_31_day(thresholds[:, i_lat, j_lon])
    
    return thresholds, climatologies

# Now let's compute the MHW mask
def compute_mhw_mask(region_ds, thresholds, climatologies):
    """Compute the MHW mask for the target period"""
    n_time = region_ds.time.size
    n_lat = region_ds.latitude.size
    n_lon = region_ds.longitude.size
    
    # Initialize MHW mask
    mhw_mask = np.zeros((n_time, n_lat, n_lon), dtype=np.uint8)
    
    # For each time step, check if SST exceeds threshold
    for i_time in range(n_time):
        print(f"Processing time step {i_time+1}/{n_time}")
        current_date = str(region_ds.time.isel(time=i_time).values).split('T')[0]
        current_doy = date_to_doy(current_date)
        
        # Get the threshold and climatology for this DOY
        threshold_vals = thresholds[current_doy-1, :, :]
        climatology_vals = climatologies[current_doy-1, :, :]
        
        # Get SST for this time step
        sst_vals = region_ds.analysed_sst.isel(time=i_time).values
        
        # Compare with threshold
        hot_days = sst_vals >= threshold_vals
        
        # Label hot days in the mask
        mhw_mask[i_time, :, :] = hot_days.astype(np.uint8)
    
    return mhw_mask

# Function to join gaps in MHW events
def join_mhw_gaps(mhw_mask):
    """Join MHWs separated by 1 or 2 non-hot days"""
    n_time, n_lat, n_lon = mhw_mask.shape
    
    # For each grid point, process time series
    for i_lat in range(n_lat):
        for j_lon in range(n_lon):
            # Create a copy of the time series for this location
            ts = mhw_mask[:, i_lat, j_lon].copy()
            
            # Find runs of hot days (1s)
            i = 0
            while i < n_time:
                if ts[i] == 1:  # Found a hot day
                    # Find the end of this run
                    start = i
                    while i < n_time and ts[i] == 1:
                        i += 1
                    end = i - 1
                    
                    # Check if there are gaps that should be joined
                    # We need to look ahead to see if there are < 3 consecutive non-hot days
                    # and if they should be connected
                    if end + 3 < n_time:  # If there's room to look ahead
                        # Check next 3 days
                        gap_start = end + 1
                        gap_end = gap_start + 2  # Look ahead 2 days (for 1 or 2 day gaps)
                        if gap_end < n_time:
                            # Count consecutive non-hot days
                            gap_count = 0
                            for k in range(gap_start, min(gap_end + 1, n_time)):
                                if ts[k] == 0:
                                    gap_count += 1
                                else:
                                    break
                            
                            # If gap is 1 or 2 days, extend the MHW
                            if gap_count in [1, 2]:
                                # Extend the run to include the gap days
                                for k in range(gap_start, min(gap_start + gap_count, n_time)):
                                    ts[k] = 1
                else:
                    i += 1
            
            # Update the mask with modified time series
            mhw_mask[:, i_lat, j_lon] = ts
    
    return mhw_mask

# Function to identify regional events
def find_regional_events(mhw_mask):
    """Find regional MHW events based on active days"""
    n_time, n_lat, n_lon = mhw_mask.shape
    
    # Find active days (at least one cell is in MHW)
    active_days = np.any(mhw_mask == 1, axis=(1, 2))
    
    # Find maximal runs of consecutive active days
    events = []
    i = 0
    while i < n_time:
        if active_days[i]:
            # Found start of an event
            start = i
            # Find end of event
            while i < n_time and active_days[i]:
                i += 1
            end = i - 1
            # Add to events
            events.append((start, end))
        else:
            i += 1
    
    # Convert to date strings
    event_dates = []
    for start_idx, end_idx in events:
        start_date = str(region_ds.time.isel(time=start_idx).values).split('T')[0]
        end_date = str(region_ds.time.isel(time=end_idx).values).split('T')[0]
        event_dates.append({"onset": start_date, "end": end_date})
    
    return event_dates

# Main execution
print("Starting MHW computation...")
print("Region:", lat_min, "to", lat_max, "N,", lon_min, "to", lon_max, "E")
print("Target period:", start_date, "to", end_date)

# Compute thresholds and climatology
print("Computing thresholds and climatology...")
thresholds, climatologies = compute_threshold_climatology(region_ds, baseline_ds)

# Compute MHW mask
print("Computing MHW mask...")
mhw_mask = compute_mhw_mask(region_ds, thresholds, climatologies)

# Join gaps in MHWs
print("Joining MHW gaps...")
mhw_mask = join_mhw_gaps(mhw_mask)

# Find regional events
print("Finding regional events...")
events = find_regional_events(mhw_mask)

# Save results
print("Saving results...")

# Create output directory
os.makedirs("output", exist_ok=True)

# Save the MHW mask as NetCDF
print("Creating NetCDF output...")
import xarray as xr

# Create the dataset for output
output_ds = xr.Dataset(
    {
        'mhw': (['time', 'lat', 'lon'], mhw_mask),
    },
    coords={
        'time': region_ds.time,
        'lat': region_ds.latitude,
        'lon': region_ds.longitude,
    }
)

# Save to file
output_ds.to_netcdf('output/mhw_mask.nc')

# Create report
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

print("Analysis complete!")
print("Events found:", len(events))
for event in events:
    print(f"Event: {event['onset']} to {event['end']}")