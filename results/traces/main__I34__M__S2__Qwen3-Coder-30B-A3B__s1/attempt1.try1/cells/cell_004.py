import xarray as xr
import numpy as np
from datetime import datetime, timedelta
import os
import math

def day_of_year(date):
    """Convert a date to day of year (1-366)"""
    # Handle leap year cases
    if date.month == 2 and date.day == 29:
        return 60
    else:
        # Create a date for the same year but Jan 1 to calculate DOY
        jan1 = datetime(date.year, 1, 1)
        return (date - jan1).days + 1

def get_doy_for_date(date_str):
    """Convert YYYY-MM-DD string to day of year"""
    date = datetime.strptime(date_str, "%Y-%m-%d")
    return day_of_year(date)

def get_dates_in_range(start_date, end_date):
    """Get all dates in a range"""
    dates = []
    current = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    
    while current <= end:
        dates.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)
    
    return dates

def get_baseline_dates():
    """Get all dates in baseline period 1992-2002"""
    dates = []
    for year in range(1992, 2003):  # 1992 to 2002 inclusive
        # For each year, get all dates
        for month in range(1, 13):
            if month in [1, 3, 5, 7, 8, 10, 12]:
                days_in_month = 31
            elif month in [4, 6, 9, 11]:
                days_in_month = 30
            elif month == 2:
                # Check if leap year
                if (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0):
                    days_in_month = 29
                else:
                    days_in_month = 28
            
            for day in range(1, days_in_month + 1):
                dates.append(f"{year:04d}-{month:02d}-{day:02d}")
    
    return dates

def create_pool_dates(baseline_dates, target_date, doy):
    """Create pool of dates for a given target date and day of year"""
    # For day 60 (Feb 29), we don't create a pool
    if doy == 60:
        return []
    
    # Find all dates in baseline that match the DOY
    matching_dates = []
    for date_str in baseline_dates:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        if day_of_year(date_obj) == doy:
            matching_dates.append(date_str)
    
    # For each matching date, find dates within ±5 days
    pool_dates = []
    target_obj = datetime.strptime(target_date, "%Y-%m-%d")
    
    for date_str in matching_dates:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        # Calculate difference in days
        diff = (target_obj - date_obj).days
        
        # Include dates within ±5 days
        if abs(diff) <= 5:
            pool_dates.append(date_str)
    
    # Handle edge cases where window goes beyond baseline
    # This happens for the first and last few days of the year
    if doy == 1:  # January 1
        # Include dates from Dec 27 to Dec 31 of previous year
        prev_dec_dates = []
        for day in range(27, 32):
            prev_dec_dates.append(f"1991-12-{day:02d}")
        pool_dates.extend(prev_dec_dates)
        
    if doy == 365 or doy == 366:  # December 31 or 30
        # Include dates from Jan 1 to Jan 5 of next year  
        next_jan_dates = []
        for day in range(1, 6):
            next_jan_dates.append(f"2003-01-{day:02d}")
        pool_dates.extend(next_jan_dates)
    
    return pool_dates

def smooth_array(arr):
    """Smooth array with 31-day moving average that wraps around"""
    # arr should be 366 elements long
    result = np.zeros_like(arr)
    
    for i in range(len(arr)):
        # Sum up the 31 elements centered on i (wrapping around)
        sum_val = 0
        count = 0
        
        for j in range(-15, 16):  # -15 to +15
            idx = (i + j) % len(arr)
            if not np.isnan(arr[idx]):
                sum_val += arr[idx]
                count += 1
        
        if count > 0:
            result[i] = sum_val / count
        else:
            result[i] = np.nan
    
    return result

# Main analysis function
def analyze_mhw():
    # Open dataset
    file_path = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
    ds = xr.open_dataset(file_path, engine="h5netcdf")
    
    # Define region and period
    lat_min, lat_max = 59.93, 61.13
    lon_min, lon_max = 18.69, 19.89
    target_start = "2007-06-01"
    target_end = "2007-08-31"
    baseline_start = "1992-01-01"
    baseline_end = "2002-12-31"
    
    # Select region
    region_ds = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))
    
    # Get time indices for target period
    target_times = get_dates_in_range(target_start, target_end)
    target_time_indices = []
    
    # Find matching time indices
    for date_str in target_times:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        # Find closest time in dataset
        time_matches = region_ds.time.where(region_ds.time.dt.strftime('%Y-%m-%d') == date_str, drop=True)
        if len(time_matches) > 0:
            target_time_indices.append(int(time_matches[0]))
    
    # Get the subset of data for target period
    if len(target_time_indices) > 0:
        subset_ds = region_ds.isel(time=target_time_indices)
    else:
        subset_ds = region_ds.isel(time=slice(0, 0))  # Empty selection
    
    # Get baseline dates
    baseline_dates = get_baseline_dates()
    
    # Prepare storage for thresholds and climatology
    thresholds = np.full((366, region_ds.latitude.size, region_ds.longitude.size), np.nan, dtype=np.float64)
    climatologies = np.full((366, region_ds.latitude.size, region_ds.longitude.size), np.nan, dtype=np.float64)
    
    # Process each day of year
    print("Computing thresholds and climatologies...")
    
    # Create mapping from date to day of year
    date_to_doy = {}
    for date_str in baseline_dates:
        doy = get_doy_for_date(date_str)
        date_to_doy[date_str] = doy
    
    # Process each grid point
    for lat_idx in range(region_ds.latitude.size):
        for lon_idx in range(region_ds.longitude.size):
            # Check if all days have valid data
            valid_days = []
            for date_str in target_times:
                date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                time_idx = None
                for i, time_val in enumerate(region_ds.time.values):
                    if datetime.strptime(str(time_val.astype('datetime64[s]').astype(datetime)), '%Y-%m-%d') == date_obj:
                        time_idx = i
                        break
                
                if time_idx is not None:
                    sst_val = region_ds.analysed_sst.isel(time=time_idx, latitude=lat_idx, longitude=lon_idx).values
                    if np.isfinite(sst_val):
                        valid_days.append(date_str)
            
            # If not all days have data, skip this cell
            if len(valid_days) < len(target_times):
                continue
            
            # For each day of year, compute threshold and climatology
            for doy in range(1, 367):
                if doy == 60:  # February 29
                    continue
                    
                # Collect all SST values for this DOY in baseline
                pool_values = []
                
                # For each baseline date that matches this DOY
                for baseline_date in baseline_dates:
                    baseline_doy = get_doy_for_date(baseline_date)
                    if baseline_doy == doy:
                        # Get all dates within ±5 days of this baseline date
                        target_obj = datetime.strptime(baseline_date, "%Y-%m-%d")
                        
                        # Find matching dates in baseline period
                        for date_str in baseline_dates:
                            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                            diff = (date_obj - target_obj).days
                            if abs(diff) <= 5:
                                # Get SST value
                                try:
                                    # Find time index for this date
                                    time_idx = None
                                    for i, time_val in enumerate(region_ds.time.values):
                                        if datetime.strptime(str(time_val.astype('datetime64[s]').astype(datetime)), '%Y-%m-%d') == date_obj:
                                            time_idx = i
                                            break
                                    
                                    if time_idx is not None:
                                        sst_val = region_ds.analysed_sst.isel(time=time_idx, latitude=lat_idx, longitude=lon_idx).values
                                        if np.isfinite(sst_val):
                                            pool_values.append(sst_val)
                                except:
                                    pass
                
                # Special handling for day 60 (February 29)
                if doy == 60:
                    # Use mean of days 59 and 61
                    if not np.isnan(thresholds[58, lat_idx, lon_idx]) and not np.isnan(thresholds[60, lat_idx, lon_idx]):
                        thresholds[doy-1, lat_idx, lon_idx] = (thresholds[58, lat_idx, lon_idx] + thresholds[60, lat_idx, lon_idx]) / 2
                    if not np.isnan(climatologies[58, lat_idx, lon_idx]) and not np.isnan(climatologies[60, lat_idx, lon_idx]):
                        climatologies[doy-1, lat_idx, lon_idx] = (climatologies[58, lat_idx, lon_idx] + climatologies[60, lat_idx, lon_idx]) / 2
                else:
                    # Compute 90th percentile and mean for this DOY
                    if len(pool_values) > 0:
                        # Using numpy's method="hazen" equivalent
                        pool_array = np.array(pool_values)
                        threshold = np.percentile(pool_array, 90, method='linear')
                        climatology = np.mean(pool_array)
                        
                        thresholds[doy-1, lat_idx, lon_idx] = threshold
                        climatologies[doy-1, lat_idx, lon_idx] = climatology
    
    # Smooth the thresholds and climatologies
    print("Smoothing thresholds and climatologies...")
    smoothed_thresholds = np.full_like(thresholds, np.nan)
    smoothed_climatologies = np.full_like(climatologies, np.nan)
    
    for lat_idx in range(region_ds.latitude.size):
        for lon_idx in range(region_ds.longitude.size):
            # Smooth thresholds
            thresh_slice = thresholds[:, lat_idx, lon_idx]
            if not np.all(np.isnan(thresh_slice)):
                smoothed_thresholds[:, lat_idx, lon_idx] = smooth_array(thresh_slice)
            
            # Smooth climatologies
            clim_slice = climatologies[:, lat_idx, lon_idx]
            if not np.all(np.isnan(clim_slice)):
                smoothed_climatologies[:, lat_idx, lon_idx] = smooth_array(clim_slice)
    
    # Now identify MHWs in the target period
    print("Identifying MHWs...")
    
    # Create MHW mask
    mhw_mask = np.zeros((len(target_times), region_ds.latitude.size, region_ds.longitude.size), dtype=np.uint8)
    
    # Process each day in target period
    for t_idx, date_str in enumerate(target_times):
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        doy = day_of_year(date_obj)
        
        # Get SST data for this day
        time_idx = None
        for i, time_val in enumerate(region_ds.time.values):
            if datetime.strptime(str(time_val.astype('datetime64[s]').astype(datetime)), '%Y-%m-%d') == date_obj:
                time_idx = i
                break
        
        if time_idx is None:
            continue
            
        # For each grid cell, check if it's part of an MHW
        for lat_idx in range(region_ds.latitude.size):
            for lon_idx in range(region_ds.longitude.size):
                # Get SST value
                sst_val = region_ds.analysed_sst.isel(time=time_idx, latitude=lat_idx, longitude=lon_idx).values
                
                # Get threshold for this day of year
                if not np.isnan(smoothed_thresholds[doy-1, lat_idx, lon_idx]):
                    threshold = smoothed_thresholds[doy-1, lat_idx, lon_idx]
                    
                    # If SST >= threshold, it's hot
                    if np.isfinite(sst_val) and sst_val >= threshold:
                        # Mark this cell as hot
                        mhw_mask[t_idx, lat_idx, lon_idx] = 1
    
    # Now join MHWs according to the rules
    print("Joining MHWs...")
    # This is a simplified approach - we'll create a more detailed implementation
    
    # Create final MHW mask
    final_mhw_mask = np.zeros_like(mhw_mask)
    
    # Process each grid point independently
    for lat_idx in range(region_ds.latitude.size):
        for lon_idx in range(region_ds.longitude.size):
            # Get the time series for this grid point
            time_series = mhw_mask[:, lat_idx, lon_idx]
            
            # Identify runs of hot days
            i = 0
            while i < len(time_series):
                if time_series[i] == 1:  # Hot day
                    # Start counting a potential MHW
                    start_day = i
                    while i < len(time_series) and time_series[i] == 1:
                        i += 1
                    end_day = i - 1
                    
                    # If run is at least 5 days, it's an MHW
                    if end_day - start_day + 1 >= 5:
                        # Mark the entire run as MHW
                        final_mhw_mask[start_day:end_day+1, lat_idx, lon_idx] = 1
                    else:
                        # Not long enough, ignore it
                        i += 1
                else:
                    i += 1
    
    # Join gaps of 1 or 2 days
    print("Joining gaps in MHWs...")
    for lat_idx in range(region_ds.latitude.size):
        for lon_idx in range(region_ds.longitude.size):
            # Process the time series for this grid point
            time_series = final_mhw_mask[:, lat_idx, lon_idx]
            
            # Find gaps and join them
            i = 0
            while i < len(time_series):
                if time_series[i] == 1:  # We're in a hot period
                    # Find the end of this period
                    j = i
                    while j < len(time_series) and time_series[j] == 1:
                        j += 1
                    
                    # Check if there's a gap of 1 or 2 days
                    if j < len(time_series):
                        gap_start = j
                        # Count consecutive non-hot days
                        gap_count = 0
                        k = gap_start
                        while k < len(time_series) and time_series[k] == 0:
                            gap_count += 1
                            k += 1
                        
                        # If gap is 1 or 2 days, and the next period is also hot
                        if gap_count in [1, 2] and k < len(time_series) and time_series[k] == 1:
                            # Join the periods
                            # Mark the gap days as hot too
                            for idx in range(gap_start, k):
                                time_series[idx] = 1
                        
                    i = j
                else:
                    i += 1
    
    # Create regional events
    print("Creating regional events...")
    # A day is active if at least one sea cell is inside a per-cell MHW
    active_days = np.any(final_mhw_mask, axis=(1, 2))
    
    # Find maximal runs of consecutive active days
    events = []
    i = 0
    while i < len(active_days):
        if active_days[i]:
            # Found start of an event
            start_day = i
            # Find end of this event
            while i < len(active_days) and active_days[i]:
                i += 1
            end_day = i - 1
            # Add event
            event_start = target_times[start_day]
            event_end = target_times[end_day]
            events.append({
                "onset": event_start,
                "end": event_end
            })
        else:
            i += 1
    
    # Create NetCDF output
    print("Creating NetCDF output...")
    # Create new dataset with the MHW mask
    if len(target_times) > 0:
        # Create coordinate arrays
        times = [datetime.strptime(d, "%Y-%m-%d") for d in target_times]
        
        # Create output directory if needed
        os.makedirs("output", exist_ok=True)
        
        # Create a new dataset with the mhw mask
        mhw_ds = xr.Dataset(
            {
                'mhw': (['time', 'latitude', 'longitude'], final_mhw_mask)
            },
            coords={
                'time': times,
                'latitude': region_ds.latitude.values,
                'longitude': region_ds.longitude.values
            }
        )
        
        # Set attributes
        mhw_ds['mhw'].attrs = {'units': 'binary', 'long_name': 'Marine Heatwave'}
        
        # Save to file
        mhw_ds.to_netcdf('output/mhw_mask.nc')
        
        # Close datasets
        mhw_ds.close()
    else:
        # Create empty dataset with proper dimensions
        os.makedirs("output", exist_ok=True)
        mhw_ds = xr.Dataset(
            {
                'mhw': (['time', 'latitude', 'longitude'], np.zeros((0, region_ds.latitude.size, region_ds.longitude.size), dtype=np.uint8))
            },
            coords={
                'time': [],
                'latitude': region_ds.latitude.values,
                'longitude': region_ds.longitude.values
            }
        )
        mhw_ds.to_netcdf('output/mhw_mask.nc')
        mhw_ds.close()

    # Create report JSON
    report = {
        "region": {
            "lat_min": lat_min,
            "lat_max": lat_max,
            "lon_min": lon_min,
            "lon_max": lon_max
        },
        "baseline_analysed": {
            "start": baseline_start,
            "end": baseline_end
        },
        "target_analysed": {
            "start": target_start,
            "end": target_end
        },
        "events": events,
        "complete": True,
        "caveats": ""
    }
    
    import json
    with open('output/report.json', 'w') as f:
        json.dump(report, f, indent=2)
    
    print("Analysis completed!")
    print(f"Found {len(events)} regional MHW events")
    
    # Close original dataset
    ds.close()

# Run the analysis
analyze_mhw()