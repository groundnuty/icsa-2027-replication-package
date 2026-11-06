import xarray as xr
import numpy as np
from datetime import datetime, timedelta
from scipy import stats

def date_to_doy(date):
    """Convert a date to day of year (1-366)"""
    if isinstance(date, np.datetime64):
        date = datetime.strptime(str(date), '%Y-%m-%dT%H:%M:%S.%f')
    # Handle leap year cases
    if date.month == 2 and date.day == 29:
        return 60
    # Convert to doy
    doy = date.timetuple().tm_yday
    # Adjust for leap year if needed (but we're using the actual calendar)
    return doy

def get_doy_from_date(date):
    """Convert a date to day of year (1-366)"""
    if isinstance(date, str):
        date = datetime.strptime(date, '%Y-%m-%d')
    elif isinstance(date, np.datetime64):
        date = datetime.strptime(str(date), '%Y-%m-%dT%H:%M:%S.%f')
    return date.timetuple().tm_yday

def get_date_range_with_leap_years(start_date, end_date):
    """Generate dates between start and end, including leap year dates"""
    dates = []
    current = start_date
    while current <= end_date:
        dates.append(current)
        current += timedelta(days=1)
    return dates

def get_baseline_windows(dates, doy_map):
    """Create windows for baseline period"""
    windows = {}
    for i, date in enumerate(dates):
        doy = doy_map[date]
        if doy == 60:  # Special case for Feb 29
            continue
            
        if doy not in windows:
            windows[doy] = []
            
        # Add this date to its window (±5 days)
        start_window = max(0, i - 5)
        end_window = min(len(dates), i + 6)  # +6 because range is exclusive
        
        for j in range(start_window, end_window):
            if j != i:  # Skip the current date itself
                windows[doy].append(j)
                
    return windows

def compute_threshold_and_climatology(sst_data, baseline_dates, doy_map):
    """
    Compute thresholds and climatology for each day of year
    
    sst_data: array of shape (n_days, n_lat, n_lon) 
    baseline_dates: array of baseline dates
    doy_map: mapping from date to day of year
    """
    n_lat, n_lon = sst_data.shape[1], sst_data.shape[2]
    n_doy = 366
    
    # Initialize arrays
    thresholds = np.full((n_doy, n_lat, n_lon), np.nan, dtype=np.float64)
    climatologies = np.full((n_doy, n_lat, n_lon), np.nan, dtype=np.float64)
    
    # Create a mapping from date to index in baseline_dates
    date_to_index = {date: i for i, date in enumerate(baseline_dates)}
    
    # Process each day of year
    for doy in range(1, 367):  # Days 1-366
        if doy == 60:  # February 29th - special handling
            continue
            
        # Collect all data points for this day of year
        pool_indices = []
        for date in baseline_dates:
            if doy_map[date] == doy:
                pool_indices.append(date_to_index[date])
                
        # For each location (lat, lon), collect data for this doy
        for lat_idx in range(n_lat):
            for lon_idx in range(n_lon):
                # Get all valid SST values for this day of year
                pool_values = []
                for idx in pool_indices:
                    val = sst_data[idx, lat_idx, lon_idx]
                    if np.isfinite(val):
                        pool_values.append(val)
                
                if len(pool_values) > 0:
                    # Compute 90th percentile (Hazen method)
                    threshold = np.quantile(pool_values, 0.9, method='hazen')
                    # Compute mean
                    climatology = np.mean(pool_values)
                    
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

def find_hot_days(sst_data, thresholds, climatologies, target_dates, doy_map):
    """Find hot days for each cell and day"""
    n_days, n_lat, n_lon = sst_data.shape
    hot_days = np.zeros((n_days, n_lat, n_lon), dtype=bool)
    
    for day_idx in range(n_days):
        date = target_dates[day_idx]
        doy = doy_map[date]
        
        # For each cell
        for lat_idx in range(n_lat):
            for lon_idx in range(n_lon):
                sst_val = sst_data[day_idx, lat_idx, lon_idx]
                threshold_val = thresholds[doy-1, lat_idx, lon_idx]  # doy-1 because 0-indexed
                
                if np.isfinite(sst_val) and np.isfinite(threshold_val):
                    if sst_val >= threshold_val:
                        hot_days[day_idx, lat_idx, lon_idx] = True
                        
    return hot_days

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

# Test our functions with a small subset
print("Functions defined successfully")