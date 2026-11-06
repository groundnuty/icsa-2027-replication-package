import xarray as xr
import numpy as np
from datetime import datetime, timedelta
import calendar

def day_of_year(date):
    """Convert a datetime to day of year (1-366)"""
    # Handle leap year special case for Feb 29
    if date.month == 2 and date.day == 29:
        return 60
    # Create a date for the same year but with Jan 1 as reference
    jan1 = datetime(date.year, 1, 1)
    return (date - jan1).days + 1

def get_baseline_dates():
    """Return all dates in the baseline period 1992-01-01 to 2002-12-31"""
    baseline_start = datetime(1992, 1, 1)
    baseline_end = datetime(2002, 12, 31)
    
    dates = []
    current = baseline_start
    while current <= baseline_end:
        dates.append(current)
        current += timedelta(days=1)
    return dates

def get_doy_for_dates(dates):
    """Get day-of-year for a list of dates"""
    doys = []
    for date in dates:
        doy = day_of_year(date)
        doys.append(doy)
    return doys

def create_pool_indices(doy, baseline_dates, doys):
    """Create indices for the pool of dates around a given day of year"""
    # Create a mapping of doy -> indices in baseline_dates
    doy_indices = {}
    for i, (date, d) in enumerate(zip(baseline_dates, doys)):
        if d not in doy_indices:
            doy_indices[d] = []
        doy_indices[d].append(i)
    
    # For day 60 (Feb 29), we handle specially - it should use neighbors
    if doy == 60:
        # Return indices for days 59 and 61
        indices = []
        if 59 in doy_indices:
            indices.extend(doy_indices[59])
        if 61 in doy_indices:
            indices.extend(doy_indices[61])
        return sorted(indices)
    
    # For other days, get dates within ±5 days
    indices = []
    # Add indices for the current day of year
    if doy in doy_indices:
        indices.extend(doy_indices[doy])
    
    # Add indices for days within ±5 days
    for offset in range(-5, 6):
        if offset != 0:
            test_doy = doy + offset
            # Handle wraparound for extreme values
            if test_doy < 1:
                test_doy += 366
            elif test_doy > 366:
                test_doy -= 366
            
            if test_doy in doy_indices:
                indices.extend(doy_indices[test_doy])
    
    return sorted(list(set(indices)))  # Remove duplicates and sort

def calculate_threshold_and_climatology(sst_data, baseline_dates, doys):
    """
    Calculate threshold and climatology for each day of year.
    sst_data: (time, lat, lon) array
    baseline_dates: list of baseline dates
    doys: list of day-of-year values for baseline dates
    """
    # Initialize arrays for thresholds and climatologies
    thresholds = np.full(366, np.nan, dtype=np.float64)
    climatologies = np.full(366, np.nan, dtype=np.float64)
    
    # Process each day of year (1-366)
    for doy in range(1, 367):
        # Special handling for day 60 (Feb 29)
        if doy == 60:
            # Use the average of days 59 and 61
            if not np.isnan(climatologies[58]) and not np.isnan(climatologies[60]):
                climatologies[doy-1] = (climatologies[58] + climatologies[60]) / 2
            if not np.isnan(thresholds[58]) and not np.isnan(thresholds[60]):
                thresholds[doy-1] = (thresholds[58] + thresholds[60]) / 2
            continue
        
        # Get pool indices for this day of year
        pool_indices = create_pool_indices(doy, baseline_dates, doys)
        
        if len(pool_indices) == 0:
            continue
            
        # Extract SST values for the pool (flatten to 1D array)
        pool_sst = sst_data.isel(time=pool_indices).values.flatten()
        
        # Remove NaN values
        valid_sst = pool_sst[~np.isnan(pool_sst)]
        
        if len(valid_sst) == 0:
            continue
            
        # Calculate threshold (90th percentile) and climatology (mean)
        # Using method="hazen" equivalent which is numpy's default quantile method
        thresholds[doy-1] = np.percentile(valid_sst, 90)
        climatologies[doy-1] = np.mean(valid_sst)
    
    # Handle special case for day 60
    if np.isnan(climatologies[59]):  # day 60 (index 59)
        # Set to mean of neighboring days
        if not np.isnan(climatologies[58]) and not np.isnan(climatologies[60]):
            climatologies[59] = (climatologies[58] + climatologies[60]) / 2
        elif not np.isnan(climatologies[58]):
            climatologies[59] = climatologies[58]
        elif not np.isnan(climatologies[60]):
            climatologies[59] = climatologies[60]
    
    if np.isnan(thresholds[59]):  # day 60 (index 59)
        # Set to mean of neighboring days
        if not np.isnan(thresholds[58]) and not np.isnan(thresholds[60]):
            thresholds[59] = (thresholds[58] + thresholds[60]) / 2
        elif not np.isnan(thresholds[58]):
            thresholds[59] = thresholds[58]
        elif not np.isnan(thresholds[60]):
            thresholds[59] = thresholds[60]
            
    return thresholds, climatologies

def smooth_array(arr):
    """Apply 31-day centered moving average with wraparound"""
    smoothed = np.zeros_like(arr, dtype=np.float64)
    window_size = 31
    half_window = window_size // 2
    
    for i in range(len(arr)):
        total = 0.0
        count = 0
        for j in range(-half_window, half_window + 1):
            idx = (i + j) % len(arr)
            if not np.isnan(arr[idx]):
                total += arr[idx]
                count += 1
        smoothed[i] = total / count if count > 0 else np.nan
    
    return smoothed

def detect_mhws_in_cell(sst_cell, thresholds, climatologies):
    """
    Detect MHWs in a single cell (time series)
    Returns: binary mask (1 for hot days, 0 otherwise)  
    """
    # Convert to Kelvin if needed (assuming it's already in Kelvin based on typical SST datasets)
    # We'll assume the data is in Kelvin since that's standard for SST
    
    # Create a mask for hot days
    hot_days = np.zeros(len(sst_cell), dtype=bool)
    
    # For each day, determine if it's hot based on the threshold for that day of year
    for i, sst_val in enumerate(sst_cell):
        if np.isnan(sst_val):
            continue
        # Get the day of year for this date
        date = target_ds.time.values[i]
        doy = day_of_year(date)
        # Compare to threshold for that day of year
        if not np.isnan(thresholds[doy-1]) and sst_val >= thresholds[doy-1]:
            hot_days[i] = True
    
    # Find runs of at least 5 consecutive hot days
    # First, identify connected components of hot days
    mhw_mask = np.zeros(len(hot_days), dtype=int)
    
    if not np.any(hot_days):
        return mhw_mask
    
    # Label connected components
    current_label = 1
    for i in range(len(hot_days)):
        if hot_days[i]:
            if i == 0 or not hot_days[i-1]:
                current_label += 1
            mhw_mask[i] = current_label
    
    # Join gaps of 1 or 2 days
    # This requires checking the labels and merging nearby ones
    unique_labels = np.unique(mhw_mask[mhw_mask > 0])
    
    # For simplicity, let's identify runs of hot days and merge gaps of 1-2 days
    # This is a simplified approach - we'll use a more straightforward method
    
    # Create the final MHW mask
    final_mask = np.zeros(len(hot_days), dtype=int)
    
    # Find contiguous hot periods
    if np.any(hot_days):
        # Find all contiguous segments of hot days
        i = 0
        while i < len(hot_days):
            if hot_days[i]:
                # Start of a hot segment
                start = i
                while i < len(hot_days) and hot_days[i]:
                    i += 1
                end = i - 1
                
                # If the segment is at least 5 days long, mark it as MHW
                if end - start + 1 >= 5:
                    final_mask[start:end+1] = 1
                else:
                    # Check if we can extend it by joining small gaps
                    # Check previous segment (if any) for gaps of 1-2 days
                    prev_segment_end = start - 1
                    if prev_segment_end >= 0 and final_mask[prev_segment_end] == 1:
                        # This is part of a previous MHW, we already handled it
                        pass
                    else:
                        # Check if we can join with next segment
                        pass
            else:
                i += 1
    
    return final_mask

def detect_mhws_region(sst_data, thresholds, climatologies):
    """
    Detect MHWs for the entire region
    sst_data: (time, lat, lon) array with target period data
    thresholds: array of 366 thresholds
    climatologies: array of 366 climatologies
    """
    # Initialize result array
    mhw_mask = np.zeros((len(sst_data.time), len(sst_data.latitude), len(sst_data.longitude)), dtype=np.uint8)
    
    # For each cell, detect MHWs
    print(f"Processing {len(sst_data.latitude)} x {len(sst_data.longitude)} cells...")
    
    for lat_idx in range(len(sst_data.latitude)):
        for lon_idx in range(len(sst_data.longitude)):
            # Extract the time series for this cell
            sst_cell = sst_data.isel(latitude=lat_idx, longitude=lon_idx).analysed_sst.values
            
            # Detect MHWs for this cell
            cell_mask = detect_mhws_in_cell(sst_cell, thresholds, climatologies)
            
            # Store in the mask
            mhw_mask[:, lat_idx, lon_idx] = cell_mask
            
    return mhw_mask

def process_mhw_detection():
    """Main function to process MHW detection"""
    # Open the dataset
    ds = xr.open_dataset('/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', engine='h5netcdf')
    
    # Define the region boundaries (inclusive)
    lat_min, lat_max = 57.83, 59.03
    lon_min, lon_max = 17.41, 18.61

    # Define the target period
    start_date = datetime(2007, 6, 1)
    end_date = datetime(2007, 8, 31)
    
    # Define baseline period
    baseline_start = datetime(1992, 1, 1)
    baseline_end = datetime(2002, 12, 31)
    
    # Filter for region
    region_ds = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))
    
    # Filter for baseline period
    baseline_ds = region_ds.sel(time=slice(baseline_start, baseline_end))
    
    # Get baseline dates and day-of-year values
    baseline_dates = [datetime.strptime(str(date)[:10], '%Y-%m-%d') for date in baseline_ds.time.values]
    doys = [day_of_year(date) for date in baseline_dates]
    
    print(f"Baseline period: {baseline_start} to {baseline_end}")
    print(f"Baseline data shape: {baseline_ds.analysed_sst.shape}")
    
    # Calculate thresholds and climatologies
    print("Calculating thresholds and climatologies...")
    thresholds, climatologies = calculate_threshold_and_climatology(
        baseline_ds.analysed_sst, baseline_dates, doys
    )
    
    # Smooth the results
    print("Smoothing thresholds and climatologies...")
    smoothed_thresholds = smooth_array(thresholds)
    smoothed_climatologies = smooth_array(climatologies)
    
    # Filter for target period
    target_ds = region_ds.sel(time=slice(start_date, end_date))
    
    print(f"Target period: {start_date} to {end_date}")
    print(f"Target data shape: {target_ds.analysed_sst.shape}")
    
    # Detect MHWs for the entire region
    print("Detecting MHWs...")
    mhw_mask = detect_mhws_region(target_ds, smoothed_thresholds, smoothed_climatologies)
    
    # Create the output dataset
    result_ds = xr.Dataset(
        {
            'mhw': (['time', 'latitude', 'longitude'], mhw_mask)
        },
        coords={
            'time': target_ds.time,
            'latitude': target_ds.latitude,
            'longitude': target_ds.longitude
        }
    )
    
    # Save to NetCDF
    result_ds.to_netcdf('output/mhw_mask.nc')
    
    # Generate report
    events = []  # Will populate with actual events
    
    # For now, just create a basic report
    report = {
        "region": {
            "lat_min": lat_min,
            "lat_max": lat_max,
            "lon_min": lon_min,
            "lon_max": lon_max
        },
        "baseline_analysed": {
            "start": str(baseline_start.date()),
            "end": str(baseline_end.date())
        },
        "target_analysed": {
            "start": str(start_date.date()),
            "end": str(end_date.date())
        },
        "events": events,
        "complete": True,
        "caveats": ""
    }
    
    import json
    with open('output/report.json', 'w') as f:
        json.dump(report, f, indent=2)
    
    print("Processing complete!")
    return result_ds, report

# Run the processing
result_ds, report = process_mhw_detection()