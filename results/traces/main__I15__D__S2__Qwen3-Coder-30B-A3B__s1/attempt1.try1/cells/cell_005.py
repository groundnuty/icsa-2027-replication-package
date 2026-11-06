import xarray as xr
import numpy as np
from datetime import datetime, timedelta
import os
import json

def day_of_year(date):
    """Convert a date to day of year (1-366)"""
    # Handle leap year cases
    if date.month == 2 and date.day == 29:
        return 60
    # Create a date for Jan 1 of the same year
    jan1 = datetime(date.year, 1, 1)
    # Calculate the difference in days
    delta = date - jan1
    return delta.days + 1

def get_baseline_pools(sst_data, dates, day_of_year_func):
    """Create pools for each day of year based on baseline data"""
    # Initialize pools dictionary
    pools = {}
    
    # Create mapping from date to day of year
    date_to_doy = {}
    for i, date in enumerate(dates):
        doy = day_of_year_func(date)
        date_to_doy[date] = doy
    
    # Process each day of year
    for doy in range(1, 367):  # 1 to 366
        if doy == 60:  # Skip day 60 as special case
            continue
            
        # Collect all dates that match this day of year (within ±5 days)
        pool_dates = []
        
        # Find all dates in baseline period that have this day of year
        for date, date_doy in date_to_doy.items():
            if date_doy == doy:
                pool_dates.append(date)
        
        # Add dates within ±5 days around each matching date
        extended_pool_dates = set()
        for date in pool_dates:
            # Add dates within ±5 days
            for i in range(-5, 6):
                test_date = date + timedelta(days=i)
                # Make sure the date is within baseline period
                if baseline_start <= test_date <= baseline_end:
                    extended_pool_dates.add(test_date)
        
        # Convert back to sorted list
        extended_pool_dates = sorted(list(extended_pool_dates))
        
        # Store the pool dates for this day of year
        pools[doy] = extended_pool_dates
    
    return pools

def compute_threshold_and_climatology(sst_data, dates, baseline_start, baseline_end):
    """Compute threshold and climatology for each day of year"""
    
    # Get pools for each day of year
    pools = get_baseline_pools(sst_data, dates, day_of_year)
    
    # Initialize arrays for threshold and climatology
    threshold = np.full(366, np.nan, dtype=np.float64)
    climatology = np.full(366, np.nan, dtype=np.float64)
    
    # Compute for each day of year
    for doy in range(1, 367):
        if doy == 60:  # Special handling for day 60 (leap day)
            # Set to mean of days 59 and 61
            if not np.isnan(climatology[58]) and not np.isnan(climatology[60]):
                climatology[doy-1] = (climatology[58] + climatology[60]) / 2
                threshold[doy-1] = (threshold[58] + threshold[60]) / 2
            else:
                climatology[doy-1] = np.nan
                threshold[doy-1] = np.nan
        else:
            # Get the pool dates for this day of year
            pool_dates = pools[doy]
            
            # Extract SST values for these dates
            sst_values = []
            for date in pool_dates:
                # Find the corresponding index in our data
                date_idx = np.where(dates == date)[0]
                if len(date_idx) > 0:
                    sst_values.extend(sst_data[date_idx[0], :, :].flatten())
            
            # Remove NaN values
            sst_values = np.array(sst_values)
            sst_values = sst_values[~np.isnan(sst_values)]
            
            if len(sst_values) > 0:
                # Compute climatology (mean) and threshold (90th percentile)
                climatology[doy-1] = np.mean(sst_values)
                threshold[doy-1] = np.percentile(sst_values, 90, method='hazen')
            else:
                climatology[doy-1] = np.nan
                threshold[doy-1] = np.nan
    
    # Handle day 60 specially
    if not np.isnan(climatology[58]) and not np.isnan(climatology[60]):
        climatology[59] = (climatology[58] + climatology[60]) / 2
    else:
        climatology[59] = np.nan
        
    if not np.isnan(threshold[58]) and not np.isnan(threshold[60]):
        threshold[59] = (threshold[58] + threshold[60]) / 2
    else:
        threshold[59] = np.nan
    
    return threshold, climatology

def smooth_array(arr, window_size=31):
    """Apply a centered moving average with wraparound"""
    n = len(arr)
    smoothed = np.zeros_like(arr, dtype=np.float64)
    half_window = window_size // 2
    
    for i in range(n):
        # Get indices for the window, with wraparound
        window_indices = [(i + j - half_window) % n for j in range(window_size)]
        window_values = arr[window_indices]
        # Remove NaN values for the calculation
        valid_values = window_values[~np.isnan(window_values)]
        if len(valid_values) > 0:
            smoothed[i] = np.mean(valid_values)
        else:
            smoothed[i] = np.nan
    
    return smoothed

def detect_mhw_per_cell(sst_cell, threshold_cell, min_duration=5, max_gap=2):
    """Detect MHWs for a single cell"""
    # Convert to boolean array where True means hot day
    hot_days = sst_cell >= threshold_cell
    
    # Find runs of hot days
    mhw_mask = np.zeros_like(hot_days, dtype=bool)
    
    # Simple approach: find contiguous hot periods
    i = 0
    while i < len(hot_days):
        if hot_days[i]:
            # Start of a potential MHW
            start = i
            # Extend as long as days are hot
            while i < len(hot_days) and hot_days[i]:
                i += 1
            # Check if duration meets minimum requirement
            if i - start >= min_duration:
                # Mark this MHW
                mhw_mask[start:i] = True
            else:
                # Not a valid MHW, skip to next day
                i += 1
        else:
            i += 1
    
    # Join gaps of 1 or 2 days
    # This is a simplified approach - we'll just mark all hot days that are part of 
    # a run that would have been valid if we had filled the gaps
    mhw_mask_final = np.zeros_like(mhw_mask, dtype=bool)
    
    # First pass: identify all hot periods
    i = 0
    while i < len(hot_days):
        if hot_days[i]:
            # Start of a hot period
            start = i
            # Extend until no more hot days
            while i < len(hot_days) and hot_days[i]:
                i += 1
            # If the duration is at least 5 days, keep it
            if i - start >= min_duration:
                mhw_mask_final[start:i] = True
            else:
                # Check if we can join with adjacent periods
                # This is complex - for now, we'll just make a simpler implementation
                # that follows the spirit of the specification
                
                # Look ahead and behind for gaps of 1 or 2 days
                # But let's implement the proper joining logic
                pass
        else:
            i += 1
    
    # Simpler approach: just mark all hot days in runs of at least 5 consecutive hot days
    # and also mark days that bridge gaps of 1-2 days with valid runs
    mhw_mask_final = np.zeros_like(hot_days, dtype=bool)
    
    # Find all runs of hot days
    i = 0
    while i < len(hot_days):
        if hot_days[i]:
            # Start of a hot run
            start = i
            while i < len(hot_days) and hot_days[i]:
                i += 1
            end = i
            
            # If this run is long enough, mark it
            if end - start >= min_duration:
                mhw_mask_final[start:end] = True
            else:
                # Check if we can connect it with adjacent runs
                # Look for nearby valid MHWs
                pass
        else:
            i += 1
    
    # More careful implementation
    # Find all sequences of consecutive hot days
    hot_runs = []
    i = 0
    while i < len(hot_days):
        if hot_days[i]:
            start = i
            while i < len(hot_days) and hot_days[i]:
                i += 1
            end = i
            hot_runs.append((start, end))
        else:
            i += 1
    
    # Apply the joining rule: gaps of 1 or 2 days between MHWs can be joined
    # First determine which runs are valid (length >= 5)
    valid_runs = []
    for start, end in hot_runs:
        if end - start >= min_duration:
            valid_runs.append((start, end))
    
    # Now create final mask
    mhw_mask_final = np.zeros_like(hot_days, dtype=bool)
    
    # Mark all valid runs
    for start, end in valid_runs:
        mhw_mask_final[start:end] = True
    
    # For the joining logic, we'll mark any hot day that connects to a valid run
    # with a gap of 1-2 days
    if len(valid_runs) > 1:
        for i in range(len(valid_runs) - 1):
            current_end = valid_runs[i][1]
            next_start = valid_runs[i+1][0]
            gap = next_start - current_end
            
            # If gap is 1 or 2 days, extend the current run
            if 1 <= gap <= 2:
                # Extend current run to include the gap
                mhw_mask_final[current_end:next_start] = True
    
    return mhw_mask_final

def main():
    # Open the dataset
    local_path = '/work/sst_s2.nc'
    ds = xr.open_dataset(local_path, engine='h5netcdf')

    # Define regions and periods
    lat_min, lat_max = 56.13, 57.33
    lon_min, lon_max = 17.71, 18.91
    baseline_start = datetime(1992, 1, 1)
    baseline_end = datetime(2002, 12, 31)
    target_start = datetime(2019, 6, 1)
    target_end = datetime(2019, 8, 31)

    # Extract baseline data for the region
    baseline_ds = ds.sel(time=slice(baseline_start, baseline_end))
    baseline_region_ds = baseline_ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))
    baseline_sst = baseline_region_ds['analysed_sst'].values
    baseline_times = baseline_region_ds['time'].values
    print(f"Baseline data shape: {baseline_sst.shape}")
    
    # Extract target data for the region  
    target_ds = ds.sel(time=slice(target_start, target_end))
    target_region_ds = target_ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))
    target_sst = target_region_ds['analysed_sst'].values
    target_times = target_region_ds['time'].values
    print(f"Target data shape: {target_sst.shape}")

    # Compute thresholds and climatology from baseline data
    print("Computing climatology and thresholds...")
    
    # Create arrays to store threshold and climatology for each day of year
    threshold = np.full(366, np.nan, dtype=np.float64)
    climatology = np.full(366, np.nan, dtype=np.float64)
    
    # Get all dates in baseline period
    dates = baseline_times.astype('datetime64[D]').astype(datetime)
    
    # Compute for each day of year
    for doy in range(1, 367):
        if doy == 60:  # Leap day case
            continue
            
        # Find all dates in baseline that have this day of year
        matching_dates = []
        for date in dates:
            if day_of_year(date) == doy:
                matching_dates.append(date)
        
        # Get all dates within ±5 days of these matching dates
        extended_dates = set()
        for date in matching_dates:
            for i in range(-5, 6):
                test_date = date + timedelta(days=i)
                if baseline_start <= test_date <= baseline_end:
                    extended_dates.add(test_date)
        
        # Convert to sorted list
        extended_dates = sorted(list(extended_dates))
        
        # Extract SST values for these dates
        sst_values = []
        for date in extended_dates:
            # Find index in original dates array
            idx = np.where(dates == date)[0]
            if len(idx) > 0:
                sst_values.extend(baseline_sst[idx[0], :, :].flatten())
        
        # Remove NaN values
        sst_values = np.array(sst_values)
        sst_values = sst_values[~np.isnan(sst_values)]
        
        if len(sst_values) > 0:
            # Compute climatology (mean) and threshold (90th percentile)
            climatology[doy-1] = np.mean(sst_values)
            threshold[doy-1] = np.percentile(sst_values, 90, method='hazen')
    
    # Handle day 60 specially
    if not np.isnan(climatology[58]) and not np.isnan(climatology[60]):
        climatology[59] = (climatology[58] + climatology[60]) / 2
    else:
        climatology[59] = np.nan
        
    if not np.isnan(threshold[58]) and not np.isnan(threshold[60]):
        threshold[59] = (threshold[58] + threshold[60]) / 2
    else:
        threshold[59] = np.nan
    
    # Smooth the threshold and climatology
    print("Smoothing climatology and threshold...")
    climatology_smoothed = smooth_array(climatology, 31)
    threshold_smoothed = smooth_array(threshold, 31)
    
    # Create MHW mask for target period
    print("Detecting MHWs...")
    mhw_mask = np.zeros((len(target_times), len(target_region_ds.latitude), len(target_region_ds.longitude)), dtype=np.uint8)
    
    # For each cell, detect MHWs
    for i_lat in range(len(target_region_ds.latitude)):
        for i_lon in range(len(target_region_ds.longitude)):
            # Extract SST time series for this cell
            sst_series = target_sst[:, i_lat, i_lon]
            
            # Get threshold for each day of year
            thresholds_for_cell = np.full(len(target_times), np.nan, dtype=np.float64)
            for i_time, date in enumerate(target_times):
                doy = day_of_year(date.astype(datetime))
                thresholds_for_cell[i_time] = threshold_smoothed[doy-1]
            
            # Detect MHWs for this cell
            mhw_for_cell = detect_mhw_per_cell(sst_series, thresholds_for_cell)
            
            # Fill the mask
            mhw_mask[:, i_lat, i_lon] = mhw_for_cell.astype(np.uint8)
    
    # Create the regional events
    print("Creating regional events...")
    # A day is active if at least one sea cell is inside an MHW
    active_days = np.any(mhw_mask, axis=(1, 2))  # Shape: (number_of_days,)
    
    # Find runs of active days
    events = []
    i = 0
    while i < len(active_days):
        if active_days[i]:
            # Found start of an event
            start = i
            while i < len(active_days) and active_days[i]:
                i += 1
            end = i - 1
            # Convert indices back to dates
            onset_date = target_times[start].astype(datetime)
            end_date = target_times[end].astype(datetime)
            events.append({
                "onset": onset_date.strftime("%Y-%m-%d"),
                "end": end_date.strftime("%Y-%m-%d")
            })
        else:
            i += 1
    
    # Prepare output report
    report = {
        "region": {
            "lat_min": lat_min,
            "lat_max": lat_max,
            "lon_min": lon_min,
            "lon_max": lon_max
        },
        "baseline_analysed": {
            "start": baseline_start.strftime("%Y-%m-%d"),
            "end": baseline_end.strftime("%Y-%m-%d")
        },
        "target_analysed": {
            "start": target_start.strftime("%Y-%m-%d"),
            "end": target_end.strftime("%Y-%m-%d")
        },
        "events": events,
        "complete": True,
        "caveats": ""
    }
    
    # Save report
    with open('/work/output/report.json', 'w') as f:
        json.dump(report, f, indent=2)
    
    # Save NetCDF file
    # Create new dataset with the MHW mask
    mhw_da = xr.DataArray(
        mhw_mask,
        dims=['time', 'latitude', 'longitude'],
        coords={
            'time': target_times,
            'latitude': target_region_ds.latitude,
            'longitude': target_region_ds.longitude
        },
        name='mhw',
        attrs={'units': 'binary', 'long_name': 'Marine Heat Wave'}
    )
    
    # Create dataset
    mhw_ds = xr.Dataset({'mhw': mhw_da})
    
    # Save to file
    mhw_ds.to_netcdf('/work/output/mhw_mask.nc')
    
    print("Analysis complete.")
    
    # Close datasets
    ds.close()
    baseline_region_ds.close()
    target_region_ds.close()

# Run the main function
main()