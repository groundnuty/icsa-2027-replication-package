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

def identify_sea_cells(ds):
    """Identify sea cells that have finite SST on every day of the target period"""
    # Extract the region of interest
    region_ds = ds.sel(latitude=slice(57.33, 58.53), longitude=slice(9.03, 10.23))
    
    # Extract the target period (2012-06-01 to 2012-08-31)
    target_ds = region_ds.sel(time=slice('2012-06-01', '2012-08-31'))
    
    # Check which cells have finite values for all days
    sst_data = target_ds.analysed_sst.values
    valid_days_per_cell = np.sum(np.isfinite(sst_data), axis=0)
    sea_cells = valid_days_per_cell == sst_data.shape[0]  # All days should be finite
    
    return target_ds, sea_cells

def find_mhws_in_region(target_ds, climatology, threshold, sea_cells):
    """Find MHWs in the region"""
    # Get the SST data for the target period
    sst_data = target_ds.analysed_sst.values  # Shape: (days, lat, lon)
    
    # Initialize MHW mask
    mhw_mask = np.zeros(sst_data.shape, dtype=np.uint8)
    
    # Get coordinates
    latitudes = target_ds.latitude.values
    longitudes = target_ds.longitude.values
    times = target_ds.time.values
    
    # For each cell, determine if it's part of an MHW
    for i_lat in range(sst_data.shape[1]):
        for i_lon in range(sst_data.shape[2]):
            # Skip land cells
            if not sea_cells[i_lat, i_lon]:
                continue
                
            # Get the SST time series for this cell
            sst_series = sst_data[:, i_lat, i_lon]
            
            # Get the corresponding day-of-year indices for each day
            doy_indices = []
            for time_val in times:
                date_str = str(time_val)[:10]  # Extract YYYY-MM-DD
                doy = date_to_doy(date_str)
                doy_indices.append(doy - 1)  # Convert to 0-based index
            
            doy_indices = np.array(doy_indices)
            
            # Determine which days are hot (SST >= threshold for that day of year)
            hot_days = np.zeros(len(sst_series), dtype=bool)
            for i_day, (sst_val, doy_idx) in enumerate(zip(sst_series, doy_indices)):
                if np.isfinite(sst_val) and np.isfinite(threshold[doy_idx]):
                    hot_days[i_day] = sst_val >= threshold[doy_idx]
            
            # Find runs of hot days (at least 5 consecutive)
            # First, identify connected components of hot days
            mhw_runs = []
            i = 0
            while i < len(hot_days):
                if hot_days[i]:
                    # Start of a potential MHW
                    start = i
                    while i < len(hot_days) and hot_days[i]:
                        i += 1
                    end = i - 1
                    
                    # Check if it's at least 5 days long
                    if end - start + 1 >= 5:
                        mhw_runs.append((start, end))
                else:
                    i += 1
            
            # Join gaps of 1 or 2 days
            if len(mhw_runs) > 1:
                merged_runs = [mhw_runs[0]]
                for i in range(1, len(mhw_runs)):
                    prev_start, prev_end = merged_runs[-1]
                    curr_start, curr_end = mhw_runs[i]
                    
                    # If gap is 1 or 2 days, merge
                    if curr_start - prev_end <= 2:
                        merged_runs[-1] = (prev_start, curr_end)
                    else:
                        merged_runs.append((curr_start, curr_end))
                
                mhw_runs = merged_runs
            
            # Mark MHW days in the mask
            for start, end in mhw_runs:
                mhw_mask[start:end+1, i_lat, i_lon] = 1
    
    return mhw_mask

# Load the data
ds = xr.open_dataset('/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', engine='h5netcdf')

# Step 1: Identify sea cells
target_ds, sea_cells = identify_sea_cells(ds)

print(f"Found {np.sum(sea_cells)} sea cells")

# Step 2: Compute climatology and thresholds (already done)
climatology = np.load('/tmp/climatology.npy') if np.load('/tmp/climatology.npy', allow_pickle=True) is not None else None
threshold = np.load('/tmp/threshold.npy') if np.load('/tmp/threshold.npy', allow_pickle=True) is not None else None

# Since we already computed them above, let's just make sure they exist
# For now, let's recompute them properly
def compute_climatology_and_thresholds_optimized(ds, baseline_start='1992-01-01', baseline_end='2002-12-31'):
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

# Recompute climatology and threshold
climatology, threshold = compute_climatology_and_thresholds_optimized(ds)

print("Computing MHWs...")

# Step 3: Find MHWs in the region
mhw_mask = find_mhws_in_region(target_ds, climatology, threshold, sea_cells)

print("MHW computation complete")
print("MHW mask shape:", mhw_mask.shape)

# Save climatology and threshold for reuse
np.save('/tmp/climatology.npy', climatology)
np.save('/tmp/threshold.npy', threshold)

ds.close()