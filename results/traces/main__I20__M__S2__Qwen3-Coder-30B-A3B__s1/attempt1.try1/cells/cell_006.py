import xarray as xr
import numpy as np
from datetime import datetime, timedelta

def date_to_doy(date_str):
    """Convert date string to day of year (1-366)"""
    dt = datetime.strptime(date_str, '%Y-%m-%d')
    # Handle leap year cases
    if dt.month == 2 and dt.day == 29:
        return 60
    else:
        # Get day of year (1-366)
        return int(dt.strftime('%j'))

def compute_climatology_and_thresholds(ds, baseline_start='1992-01-01', baseline_end='2002-12-31'):
    """
    Compute climatology and thresholds for each sea cell and day of year
    using the baseline period.
    """
    # Get the baseline period data
    baseline_ds = ds.sel(time=slice(baseline_start, baseline_end))
    
    # Get all unique dates in baseline period
    baseline_dates = baseline_ds.time.values
    
    # Convert all baseline dates to day-of-year
    baseline_doy = [date_to_doy(str(date)[:10]) for date in baseline_dates]
    baseline_doy = np.array(baseline_doy)
    
    # Create pool for each day of year
    pools = {}
    for doy in range(1, 367):  # 1 to 366
        if doy != 60:  # Day 60 gets special handling
            # Find all dates in baseline that fall within ±5 days of this doy
            # We need to account for the window around the year end
            pool_values = []
            
            # For each date in baseline, check if it's within ±5 days of a date with this doy
            for i, date in enumerate(baseline_dates):
                date_doy = baseline_doy[i]
                
                # Calculate distance between doy and date_doy
                # Handle year wrapping
                if date_doy <= 30 and doy >= 337:  # Near year end
                    dist = doy + 366 - date_doy
                elif date_doy >= 337 and doy <= 30:  # Near year start  
                    dist = date_doy + 366 - doy
                else:
                    dist = abs(doy - date_doy)
                    
                if dist <= 5:
                    pool_values.append(baseline_ds.analysed_sst.isel(time=i).values)
            
            if len(pool_values) > 0:
                # Stack all values and flatten
                pool_array = np.stack(pool_values)
                # Flatten to 1D, removing NaN values
                flat_pool = pool_array.flatten()
                clean_pool = flat_pool[np.isfinite(flat_pool)]
                pools[doy] = clean_pool
            else:
                pools[doy] = np.array([])
        else:
            # Day 60 (Feb 29) gets special treatment - it uses values from Feb 28 and Mar 1
            # But we'll handle this later when computing thresholds/climatology
            pools[doy] = np.array([])
    
    # Now compute climatology and thresholds for each day of year
    climatology = np.full(366, np.nan)
    threshold = np.full(366, np.nan)
    
    # Handle days 1-366
    for doy in range(1, 367):
        if doy == 60:
            # Special case: Day 60 gets the mean of days 59 and 61
            if len(pools[59]) > 0 and len(pools[61]) > 0:
                climatology[doy-1] = (np.nanmean(pools[59]) + np.nanmean(pools[61])) / 2
                # For threshold, we use the 90th percentile of the combined pool
                combined_pool = np.concatenate([pools[59], pools[61]])
                if len(combined_pool) > 0:
                    threshold[doy-1] = np.nanquantile(combined_pool, 0.9, method='linear')
            continue
            
        if len(pools[doy]) > 0:
            climatology[doy-1] = np.nanmean(pools[doy])
            threshold[doy-1] = np.nanquantile(pools[doy], 0.9, method='linear')
    
    # Smooth climatology and threshold with 31-day centered moving average
    def smooth_with_wrapping(data):
        """Apply 31-day centered moving average with year wrapping"""
        smoothed = np.zeros_like(data)
        half_window = 15
        
        for i in range(len(data)):
            # Sum values in the window
            window_sum = 0
            count = 0
            
            for j in range(-half_window, half_window + 1):
                idx = (i + j) % len(data)
                if not np.isnan(data[idx]):
                    window_sum += data[idx]
                    count += 1
                    
            if count > 0:
                smoothed[i] = window_sum / count
            else:
                smoothed[i] = np.nan
                
        return smoothed
    
    # Apply smoothing
    smoothed_climatology = smooth_with_wrapping(climatology)
    smoothed_threshold = smooth_with_wrapping(threshold)
    
    return smoothed_climatology, smoothed_threshold

# Load the data and compute climatology/thresholds
ds = xr.open_dataset('/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', engine='h5netcdf')

# Extract the region of interest
region_ds = ds.sel(latitude=slice(57.33, 58.53), longitude=slice(9.03, 10.23))

# Compute climatology and thresholds using baseline period
climatology, threshold = compute_climatology_and_thresholds(region_ds)

print("Climatology and Threshold computed")
print("Climatology shape:", climatology.shape)
print("Threshold shape:", threshold.shape)
print("Sample climatology values:", climatology[:10])
print("Sample threshold values:", threshold[:10])

ds.close()