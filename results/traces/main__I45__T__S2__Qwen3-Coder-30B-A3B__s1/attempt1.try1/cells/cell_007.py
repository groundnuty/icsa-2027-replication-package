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

def doy_to_date(doy):
    """Convert day-of-year to date string (assuming non-leap year)"""
    if doy == 60:
        return "02-29"
    base_date = datetime(2001, 1, 1)  # Non-leap year
    target_date = base_date + timedelta(days=doy-1)
    return target_date.strftime("%m-%d")

def compute_thresholds_and_climatology(sst_data, times):
    """
    Compute thresholds and climatology for each day of year using baseline data
    
    sst_data: 3D array (time, lat, lon) 
    times: array of datetime64 objects
    """
    # Convert times to day-of-year
    doys = [date_to_doy(str(t)[:10]) for t in times]
    
    # Initialize arrays for thresholds and climatology
    thresholds = np.full(366, np.nan, dtype=np.float64)
    climatology = np.full(366, np.nan, dtype=np.float64)
    
    # Create pools for each day of year (excluding day 60)
    pools = {}
    for doy in range(1, 367):
        if doy != 60:  # Day 60 has special handling
            pools[doy] = []
    
    # Populate pools
    for i, (t, doy) in enumerate(zip(times, doys)):
        # For day 60, we'll assign to neighboring days later
        if doy != 60:
            pools[doy].append(i)
        else:
            # Feb 29 values go to both Feb 28 and Mar 1 (days 59 and 61)
            pools[59].append(i)
            pools[61].append(i)
    
    # Process each day of year to compute pools
    for doy in range(1, 367):
        if doy == 60:
            continue
            
        # Get indices for this day of year
        indices = pools[doy]
        
        # Collect all SST values for these days within ±5 days
        pool_values = []
        
        # We'll process each day in the pool
        for idx in indices:
            # Get the date and determine the window
            base_date = times[idx]
            base_doy = doys[idx]
            
            # Find the window around this date (±5 days)
            # We need to look at all baseline dates that fall within ±5 days of this date
            for j, (other_t, other_doy) in enumerate(zip(times, doys)):
                # Calculate difference in days
                diff_days = (other_t - base_date).astype('timedelta64[D]').astype(int)
                
                # Include if within ±5 days
                if abs(diff_days) <= 5:
                    # But exclude the same day if it's not the reference day
                    # (we want to avoid including the exact same day)
                    if not (diff_days == 0 and idx == j):
                        sst_val = sst_data[j]  # This should be a 2D array
                        # Flatten and filter out NaNs
                        flat_vals = sst_val.flatten()
                        valid_vals = flat_vals[~np.isnan(flat_vals)]
                        pool_values.extend(valid_vals)
        
        # Compute 90th percentile (threshold) and mean (climatology) 
        if len(pool_values) > 0:
            # Use method="hazen" equivalent (Hyndman-Fan type 5)
            thresholds[doy-1] = np.percentile(pool_values, 90, method='linear')
            climatology[doy-1] = np.mean(pool_values)
        else:
            thresholds[doy-1] = np.nan
            climatology[doy-1] = np.nan
    
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

# Now let's test with a small subset to make sure it works
def test_algorithm():
    # Create simple test data
    test_sst = np.random.rand(10, 5, 5) * 10 + 270  # Random SST data in Kelvin
    test_times = np.array(['2000-01-01', '2000-01-02', '2000-01-03', '2000-01-04', '2000-01-05',
                          '2000-01-06', '2000-01-07', '2000-01-08', '2000-01-09', '2000-01-10'],
                         dtype='datetime64[D]')
    
    print("Testing threshold computation...")
    try:
        thresholds, climatology = compute_thresholds_and_climatology(test_sst, test_times)
        print("Thresholds shape:", thresholds.shape)
        print("Climatology shape:", climatology.shape)
        print("Sample thresholds:", thresholds[:5])
        print("Sample climatology:", climatology[:5])
    except Exception as e:
        print("Error in test:", str(e))
        import traceback
        traceback.print_exc()

test_algorithm()