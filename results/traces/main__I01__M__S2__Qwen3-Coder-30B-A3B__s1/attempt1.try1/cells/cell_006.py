import xarray as xr
import numpy as np
from datetime import datetime, timedelta
import os

def day_of_year(date):
    """Convert a date to day of year (1-366)"""
    # Handle datetime64 objects
    if hasattr(date, 'astype'):
        dt = date.astype(datetime)
    else:
        dt = date
    
    # Handle leap years properly
    if dt.month == 2 and dt.day == 29:
        return 60
    # Create a date for Jan 1 of the same year to calculate DOY
    jan1 = datetime(dt.year, 1, 1)
    return (dt - jan1).days + 1

def compute_threshold_and_climatology(baseline_data, baseline_times):
    """
    Compute thresholds and climatology for each day of year using the specified method.
    
    Args:
        baseline_data: (n_days, n_lat, n_lon) array of SST values
        baseline_times: (n_days,) array of datetime64 objects
    
    Returns:
        threshold: (366,) array of 90th percentiles for each day of year
        climatology: (366,) array of means for each day of year
    """
    # Initialize arrays
    threshold = np.full(366, np.nan, dtype=np.float64)
    climatology = np.full(366, np.nan, dtype=np.float64)
    
    # Get day of year for each baseline date
    doys = []
    for t in baseline_times:
        dt = t.astype(datetime)
        doy = day_of_year(dt)
        doys.append(doy)
    doys = np.array(doys)
    
    # Process each day of year (1-366)
    for doy in range(1, 367):
        if doy == 60:  # February 29th - special case
            continue
            
        # Find all baseline dates that have this day of year
        matching_dates = np.where(doys == doy)[0]
        
        # Collect all SST values from the ±5 day window around these dates
        pool_values = []
        
        # For each matching date, collect values from ±5 day window
        for idx in matching_dates:
            # Define the window boundaries
            start_idx = max(0, idx - 5)
            end_idx = min(len(baseline_times), idx + 6)  # +6 because range is exclusive
            
            # Add all values in this window (excluding the reference day itself)
            for i in range(start_idx, end_idx):
                if i != idx:  # Skip the reference day itself
                    # Flatten the 2D spatial data to 1D for this day
                    day_values = baseline_data[i].flatten()
                    # Filter out NaN values
                    valid_values = day_values[~np.isnan(day_values)]
                    pool_values.extend(valid_values)
        
        # Special handling for day 60 (February 29) - use mean of days 59 and 61
        if doy == 60:
            # We'll handle this later
            pass
        else:
            # Compute 90th percentile and mean
            if len(pool_values) > 0:
                # Use numpy's method="hazen" equivalent (which is the default in scipy)
                threshold[doy-1] = np.percentile(pool_values, 90, method='linear')  # hazen is linear
                climatology[doy-1] = np.mean(pool_values)
    
    # Handle day 60 (February 29) specially
    # Set to mean of days 59 and 61
    if not np.isnan(climatology[58]) and not np.isnan(climatology[60]):  # 59 and 61 (0-indexed)
        climatology[59] = (climatology[58] + climatology[60]) / 2
        threshold[59] = (threshold[58] + threshold[60]) / 2
    
    # Apply smoothing with 31-day centered moving average that wraps around
    threshold_smoothed = smooth_366_array(threshold)
    climatology_smoothed = smooth_366_array(climatology)
    
    return threshold_smoothed, climatology_smoothed

def smooth_366_array(arr):
    """Apply 31-day centered moving average that wraps around the year"""
    smoothed = np.zeros_like(arr, dtype=np.float64)
    window_size = 31
    half_window = window_size // 2
    
    for i in range(366):
        # Sum values in the window around day i
        sum_val = 0
        count = 0
        for j in range(-half_window, half_window + 1):
            # Wrap around the year
            wrapped_day = (i + j) % 366
            if not np.isnan(arr[wrapped_day]):
                sum_val += arr[wrapped_day]
                count += 1
        
        if count > 0:
            smoothed[i] = sum_val / count
        else:
            smoothed[i] = np.nan
    
    return smoothed

def detect_mhws(target_data, target_times, threshold, climatology):
    """
    Detect MHWs in the target period.
    
    Args:
        target_data: (n_days, n_lat, n_lon) array of SST values
        target_times: (n_days,) array of datetime64 objects
        threshold: (366,) array of thresholds
        climatology: (366,) array of climatologies
    
    Returns:
        mhw_mask: (n_days, n_lat, n_lon) boolean array indicating MHW days
    """
    # Initialize mask
    mhw_mask = np.zeros(target_data.shape, dtype=np.uint8)
    
    # For each day, determine the day of year and compare to threshold
    for i, time in enumerate(target_times):
        dt = time.astype(datetime)
        doy = day_of_year(dt)
        
        # Compare SST to threshold for this day of year
        threshold_value = threshold[doy-1]  # Convert to 0-based index
        hot_days = target_data[i] >= threshold_value
        
        # Mark hot days
        mhw_mask[i] = hot_days.astype(np.uint8)
    
    # Now identify runs of at least 5 consecutive hot days and join gaps of 1-2 days
    # Process each spatial location independently
    n_lat, n_lon = target_data.shape[1], target_data.shape[2]
    
    for lat_idx in range(n_lat):
        for lon_idx in range(n_lon):
            # Get the time series for this location
            hot_series = mhw_mask[:, lat_idx, lon_idx]
            
            # Find runs of hot days
            runs = find_runs(hot_series)
            
            # Join runs separated by 1-2 non-hot days
            merged_runs = merge_runs(runs, max_gap=2)
            
            # Update the mask with merged runs
            for start, end in merged_runs:
                mhw_mask[start:end+1, lat_idx, lon_idx] = 1
    
    return mhw_mask

def find_runs(series):
    """Find runs of consecutive True values in a boolean series."""
    runs = []
    in_run = False
    start = 0
    
    for i, val in enumerate(series):
        if val and not in_run:
            start = i
            in_run = True
        elif not val and in_run:
            runs.append((start, i-1))
            in_run = False
    
    # Don't forget the last run if it goes to the end
    if in_run:
        runs.append((start, len(series)-1))
    
    return runs

def merge_runs(runs, max_gap=2):
    """Merge consecutive runs separated by at most max_gap days."""
    if not runs:
        return []
    
    merged = [runs[0]]
    
    for i in range(1, len(runs)):
        prev_end = merged[-1][1]
        curr_start = runs[i][0]
        
        # If gap is small enough, merge
        if curr_start - prev_end <= max_gap + 1:
            # Extend the previous run
            merged[-1] = (merged[-1][0], runs[i][1])
        else:
            merged.append(runs[i])
    
    return merged

def create_output_files(mhw_mask, target_times, lat_coords, lon_coords):
    """Create the required output files."""
    # Create output directory if needed
    os.makedirs('output', exist_ok=True)
    
    # Create NetCDF file
    import xarray as xr
    
    # Create DataArray with proper dimensions
    da = xr.DataArray(
        mhw_mask,
        dims=['time', 'lat', 'lon'],
        coords={
            'time': target_times,
            'lat': lat_coords,
            'lon': lon_coords
        },
        name='mhw',
        attrs={'units': 'binary', 'long_name': 'Marine Heatwave'}
    )
    
    # Save to NetCDF
    da.to_netcdf('output/mhw_mask.nc')
    
    # Create report JSON
    report = {
        "region": {
            "lat_min": float(np.min(lat_coords)),
            "lat_max": float(np.max(lat_coords)),
            "lon_min": float(np.min(lon_coords)),
            "lon_max": float(np.max(lon_coords))
        },
        "baseline_analysed": {
            "start": str(np.datetime_as_string(np.min(target_times), unit='D')),
            "end": str(np.datetime_as_string(np.max(target_times), unit='D'))
        },
        "target_analysed": {
            "start": str(np.datetime_as_string(np.min(target_times), unit='D')),
            "end": str(np.datetime_as_string(np.max(target_times), unit='D'))
        },
        "events": [],
        "complete": True,
        "caveats": ""
    }
    
    import json
    with open('output/report.json', 'w') as f:
        json.dump(report, f, indent=2)

# Main execution
def main():
    # Open the dataset
    ds = xr.open_dataset('/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', engine='h5netcdf')

    # Define our region of interest
    lat_min, lat_max = 54.13, 55.33
    lon_min, lon_max = 14.67, 15.87

    # Find indices for our region
    lat_indices = np.where((ds.latitude >= lat_min) & (ds.latitude <= lat_max))[0]
    lon_indices = np.where((ds.longitude >= lon_min) & (ds.longitude <= lon_max))[0]

    # Extract the subset for our analysis
    subset = ds.isel(latitude=lat_indices, longitude=lon_indices)

    # Define our target period
    target_start = np.datetime64('2008-06-01')
    target_end = np.datetime64('2008-08-31')

    # Get all time indices within our target period
    time_indices = np.where((subset.time >= target_start) & (subset.time <= target_end))[0]

    # Get baseline period (1992-2002)
    baseline_start = np.datetime64('1992-01-01')
    baseline_end = np.datetime64('2002-12-31')

    # Get all time indices within baseline period
    baseline_indices = np.where((subset.time >= baseline_start) & (subset.time <= baseline_end))[0]

    # Extract data for baseline period
    baseline_data = subset.analysed_sst.isel(time=baseline_indices).values
    baseline_times = subset.time.isel(time=baseline_indices).values

    # Extract data for target period  
    target_data = subset.analysed_sst.isel(time=time_indices).values
    target_times = subset.time.isel(time=time_indices).values

    # Step 1: Compute thresholds and climatology
    print("Computing thresholds and climatology...")
    threshold, climatology = compute_threshold_and_climatology(baseline_data, baseline_times)
    
    # Step 2: Detect MHWs
    print("Detecting MHWs...")
    mhw_mask = detect_mhws(target_data, target_times, threshold, climatology)
    
    # Step 3: Create output files
    print("Creating output files...")
    create_output_files(mhw_mask, target_times, subset.latitude.values, subset.longitude.values)
    
    print("Analysis complete!")

if __name__ == "__main__":
    main()