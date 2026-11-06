import xarray as xr
import numpy as np
from datetime import datetime, timedelta
import os
import json

def day_of_year(date_obj):
    """Convert a date to day of year (1-366)"""
    # Convert numpy datetime64 to Python datetime if needed
    if isinstance(date_obj, np.datetime64):
        # Convert numpy datetime64 to datetime
        date_obj = date_obj.astype(datetime)
    
    # Handle case where it might be a date object (not datetime)
    if isinstance(date_obj, date) and not isinstance(date_obj, datetime):
        # Convert date to datetime
        date_obj = datetime.combine(date_obj, datetime.min.time())
    
    # Handle leap year cases - Feb 29 is day 60
    if date_obj.month == 2 and date_obj.day == 29:
        return 60
    
    # Create a date for Jan 1 of the same year
    jan1 = datetime(date_obj.year, 1, 1)
    # Calculate the difference in days
    delta = date_obj - jan1
    return delta.days + 1

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

def detect_mhw_per_cell(sst_cell, threshold_cell, min_duration=5):
    """Detect MHWs for a single cell - simplified version"""
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
    
    return mhw_mask

def main():
    # Create output directory
    os.makedirs('/work/output', exist_ok=True)
    
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
        if doy == 60:  # Leap day case - special handling
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
        print(f"Processing latitude {i_lat}/{len(target_region_ds.latitude)}")
        for i_lon in range(len(target_region_ds.longitude)):
            # Extract SST time series for this cell
            sst_series = target_sst[:, i_lat, i_lon]
            
            # Get threshold for each day of year
            thresholds_for_cell = np.full(len(target_times), np.nan, dtype=np.float64)
            for i_time, date in enumerate(target_times):
                # Convert numpy datetime64 to Python datetime for day_of_year function
                if isinstance(date, np.datetime64):
                    dt = date.astype(datetime)
                else:
                    dt = date
                doy = day_of_year(dt)
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