import numpy as np
import xarray as xr
import fsspec
from datetime import datetime, timedelta

def date_to_doy(date_str):
    """Convert YYYY-MM-DD string to day-of-year (1-366)"""
    dt = datetime.strptime(date_str, '%Y-%m-%d')
    doy = int(dt.strftime('%j'))
    # Special handling for Feb 29th (day 60)
    if dt.month == 2 and dt.day == 29:
        return 60
    return doy

def compute_pool_indices(doy, times, doys):
    """
    Compute indices of all dates in baseline period that are within ±5 days 
    of a date with the given day-of-year
    """
    # For each date in the baseline period, find if it falls within ±5 days of a date with this doy
    pool_indices = []
    
    for i, (t, t_doy) in enumerate(zip(times, doys)):
        # We want dates that fall within ±5 days of a date with the target doy
        # For this implementation, we'll collect all dates in the baseline period
        # and then filter based on the ±5 day window logic
        
        # This approach is more direct: for each day of year, find all dates in baseline
        # that match that day of year within ±5 days
        pass
    
    return []

def build_pools_for_doy(target_doy, times, doys, baseline_start, baseline_end):
    """
    Build pool of SST values for a specific day of year, considering ±5 day windows
    """
    # We need to identify all dates in the baseline period that would contribute to 
    # this day of year's pool (based on their calendar dates)
    
    # This is complex, let's take a simpler approach:
    # For each day of year, we'll find all baseline dates that have similar calendar dates
    # within a 5-day window
    
    # Create a mapping of day-of-year to actual dates (considering leap years)
    # For simplicity, we'll use a fixed approach that considers all baseline dates
    # and builds pools accordingly
    
    # This approach will be more direct - for each day of year d (1-366):
    # - Find all baseline dates whose calendar date is within ±5 days of a date with day d
    # - But since we're looking at day-of-year, we'll consider the calendar date
    
    # For each baseline date, determine what pool it belongs to
    # (i.e., what day-of-year it corresponds to, considering the ±5 day rule)
    
    # For now, let's just collect all baseline data for all days
    # This is inefficient but clearer for debugging
    
    pool_indices = []
    
    # For day 60 (Feb 29), we'll treat it separately as mentioned in the algorithm
    if target_doy == 60:
        # Feb 29 belongs to both Feb 28 and Mar 1 (days 59 and 61)
        # So we'll include all Feb 29 data in both pools
        for i, (t, doy) in enumerate(zip(times, doys)):
            if doy == 60:
                pool_indices.append(i)
    else:
        # For all other days, we include all baseline dates that have the same day-of-year
        # but also include those within ±5 days of that day
        for i, (t, doy) in enumerate(zip(times, doys)):
            # If it's the target day of year, include it
            if doy == target_doy:
                pool_indices.append(i)
            # Also include dates within ±5 days of the target day of year
            # This is tricky - let's calculate the date of the target day in a standard year
            # and then find matching dates in the baseline period
            elif target_doy != 60:  # Skip day 60 for this calculation
                # Create a reference date for this day of year
                ref_date = datetime(2001, 1, 1) + timedelta(days=target_doy-1)
                # Get the actual date for the baseline date
                actual_date = datetime.strptime(str(t)[:10], '%Y-%m-%d')
                # Calculate difference in days between reference dates
                diff = (actual_date - ref_date).days
                if abs(diff) <= 5:
                    pool_indices.append(i)
    
    return pool_indices

def compute_thresholds_and_climatology_simple(sst_data, times):
    """
    Simplified version of computing thresholds and climatology
    """
    # Convert times to day-of-year
    doys = [date_to_doy(str(t)[:10]) for t in times]
    
    # Initialize arrays for thresholds and climatology
    thresholds = np.full(366, np.nan, dtype=np.float64)
    climatology = np.full(366, np.nan, dtype=np.float64)
    
    print(f"Processing {len(times)} baseline days")
    print(f"Day-of-year range: {min(doys)} to {max(doys)}")
    
    # For each day of year (1-366, excluding 60 which is special)
    for doy in range(1, 367):
        if doy == 60:
            continue
            
        # Build pool for this day of year
        pool_indices = build_pools_for_doy(doy, times, doys, times[0], times[-1])
        
        if len(pool_indices) == 0:
            print(f"No data for day {doy}")
            continue
            
        # Collect all SST values from the pool
        pool_values = []
        for idx in pool_indices:
            # Extract 2D SST data and flatten, filtering out NaNs
            sst_slice = sst_data[idx]  # This is 2D (lat, lon)
            flat_vals = sst_slice.flatten()
            valid_vals = flat_vals[~np.isnan(flat_vals)]
            pool_values.extend(valid_vals)
        
        if len(pool_values) > 0:
            # Compute 90th percentile (threshold) and mean (climatology) 
            # Using method="hazen" equivalent
            thresholds[doy-1] = np.percentile(pool_values, 90, method='linear')
            climatology[doy-1] = np.mean(pool_values)
            print(f"Day {doy}: Pool size={len(pool_values)}, Threshold={thresholds[doy-1]:.2f}, Climatology={climatology[doy-1]:.2f}")
        else:
            print(f"Day {doy}: No valid data")
    
    # Handle day 60 specially - set to mean of days 59 and 61
    if not np.isnan(climatology[58]) and not np.isnan(climatology[60]):
        climatology[59] = (climatology[58] + climatology[60]) / 2
        thresholds[59] = (thresholds[58] + thresholds[60]) / 2
    
    # Apply smoothing with 31-day centered moving average that wraps around
    smoothed_thresholds = smooth_366_array(thresholds)
    smoothed_climatology = smooth_366_array(climatology)
    
    return smoothed_thresholds, smoothed_climatology

def smooth_366_array(arr):
    """Apply 31-day centered moving average that wraps around the year"""
    # Create a copy with padding to handle wrapping
    padded = np.concatenate([arr, arr, arr])  # Triple the array to handle wrapping
    smoothed = np.zeros_like(arr, dtype=np.float64)
    
    for i in range(len(arr)):
        # Take 15 days before and 15 days after (31 total)
        start_idx = i + len(arr) - 15
        end_idx = i + len(arr) + 16
        window = padded[start_idx:end_idx]
        smoothed[i] = np.mean(window)
    
    return smoothed

# Let's try a very simple test case first
def simple_test():
    # Create test data
    test_sst = np.random.rand(5, 3, 3) * 10 + 270  # 5 time steps, 3x3 grid
    test_times = np.array(['2000-01-01', '2000-01-02', '2000-01-03', '2000-01-04', '2000-01-05'],
                         dtype='datetime64[D]')
    
    print("Simple test with 5 time steps")
    try:
        thresholds, climatology = compute_thresholds_and_climatology_simple(test_sst, test_times)
        print("Success!")
        print("Thresholds length:", len(thresholds))
        print("Climatology length:", len(climatology))
    except Exception as e:
        print("Error in simple test:", str(e))
        import traceback
        traceback.print_exc()

simple_test()