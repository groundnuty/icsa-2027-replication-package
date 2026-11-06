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

def compute_climatology_and_thresholds_optimized(ds, baseline_start='1992-01-01', baseline_end='2002-12-31'):
    """
    Compute climatology and thresholds for each sea cell and day of year
    using the baseline period, optimized for memory usage.
    """
    # Get the baseline period data
    baseline_ds = ds.sel(time=slice(baseline_start, baseline_end))
    
    # Get all unique dates in baseline period
    baseline_dates = baseline_ds.time.values
    
    # Convert all baseline dates to day-of-year
    baseline_doy = [date_to_doy(str(date)[:10]) for date in baseline_dates]
    baseline_doy = np.array(baseline_doy)
    
    # Process each day of year separately to avoid memory issues
    climatology = np.full(366, np.nan)
    threshold = np.full(366, np.nan)
    
    # Process each day of year
    for doy in range(1, 367):
        if doy == 60:
            # Special case for Feb 29
            # We'll handle this by computing the average of days 59 and 61
            continue
            
        # Collect all SST values for this day of year (±5 days window)
        pool_values = []
        
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
                # Extract the SST values for this time step
                sst_values = baseline_ds.analysed_sst.isel(time=i).values
                # Flatten and filter out NaN values
                flat_values = sst_values.flatten()
                clean_values = flat_values[np.isfinite(flat_values)]
                pool_values.extend(clean_values)
        
        if len(pool_values) > 0:
            pool_array = np.array(pool_values)
            climatology[doy-1] = np.nanmean(pool_array)
            threshold[doy-1] = np.nanquantile(pool_array, 0.9, method='linear')
    
    # Handle day 60 (February 29) specially
    # Use the average of days 59 and 61
    if not np.isnan(climatology[58]) and not np.isnan(climatology[60]):
        climatology[59] = (climatology[58] + climatology[60]) / 2
        # For threshold, combine pools of 59 and 61
        pool_59 = []
        pool_61 = []
        
        for i, date in enumerate(baseline_dates):
            date_doy = baseline_doy[i]
            if abs(date_doy - 59) <= 5:
                sst_values = baseline_ds.analysed_sst.isel(time=i).values
                flat_values = sst_values.flatten()
                clean_values = flat_values[np.isfinite(flat_values)]
                pool_59.extend(clean_values)
            elif abs(date_doy - 61) <= 5:
                sst_values = baseline_ds.analysed_sst.isel(time=i).values
                flat_values = sst_values.flatten()
                clean_values = flat_values[np.isfinite(flat_values)]
                pool_61.extend(clean_values)
        
        if len(pool_59) > 0 and len(pool_61) > 0:
            combined_pool = np.array(pool_59 + pool_61)
            threshold[59] = np.nanquantile(combined_pool, 0.9, method='linear')
    
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
climatology, threshold = compute_climatology_and_thresholds_optimized(region_ds)

print("Climatology and Threshold computed")
print("Climatology shape:", climatology.shape)
print("Threshold shape:", threshold.shape)
print("Sample climatology values:", climatology[:10])
print("Sample threshold values:", threshold[:10])

ds.close()