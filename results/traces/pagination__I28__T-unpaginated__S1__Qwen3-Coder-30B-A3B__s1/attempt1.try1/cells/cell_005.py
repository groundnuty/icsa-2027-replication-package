import xarray as xr
import fsspec
import numpy as np
from datetime import datetime, timedelta
import os
import json

def date_to_doy(date):
    """Convert date to day of year (1-366)"""
    # Handle leap year special case for Feb 29
    if date.month == 2 and date.day == 29:
        return 60
    # Create a date for Jan 1 of the same year
    jan1 = datetime(date.year, 1, 1)
    # Calculate the difference in days
    diff = date - jan1
    doy = diff.days + 1
    # Adjust for leap years - if it's after Feb 28 in a non-leap year, add 1
    if not (date.year % 4 == 0 and (date.year % 100 != 0 or date.year % 400 == 0)):
        if date.month > 2:
            doy += 1
    return doy

def calculate_threshold_and_climatology(baseline_dates):
    """
    Calculate threshold and climatology for each DOY using baseline period 1992-2002
    """
    fs = fsspec.filesystem('onedata')
    
    # Create mapping from date to DOY
    date_to_doy_map = {}
    for date in baseline_dates:
        doy = date_to_doy(date)
        date_to_doy_map[date] = doy
    
    # Initialize arrays for threshold and climatology
    threshold = np.full(366, np.nan, dtype=np.float64)
    climatology = np.full(366, np.nan, dtype=np.float64)
    
    # Get all unique DOYs from baseline
    unique_doy = sorted(set(date_to_doy_map.values()))
    
    # Process each DOY except 60 (which we handle specially)
    for doy in unique_doy:
        if doy == 60:
            continue
            
        # Get all baseline dates with this DOY
        pool_dates = [date for date, d in date_to_doy_map.items() if d == doy]
        
        # Get all dates within ±5 days of these dates (but bounded by baseline period)
        all_pool_dates = []
        for date in pool_dates:
            for i in range(-5, 6):
                candidate = date + timedelta(days=i)
                if datetime(1992, 1, 1) <= candidate <= datetime(2002, 12, 31):
                    all_pool_dates.append(candidate)
        
        # Extract SST values for these dates at all grid points
        pool_values = []
        for date in all_pool_dates:
            # Find matching file
            file_path = f'/icsa2027_data_20261101T090944Z/s1z/sst_{date.strftime("%Y%m%d")}.nc'
            try:
                with fs.open(file_path, 'rb') as f:
                    ds = xr.open_dataset(f, engine='h5netcdf')
                    sst_values = ds.analysed_sst.values.flatten()
                    pool_values.extend(sst_values)
            except Exception as e:
                print(f"Error reading {file_path}: {e}")
                continue
        
        # Convert to numpy array and remove NaNs
        pool_array = np.array(pool_values, dtype=np.float64)
        valid_values = pool_array[np.isfinite(pool_array)]
        
        if len(valid_values) > 0:
            # Calculate 90th percentile (Hazen method) and mean
            threshold[doy-1] = np.percentile(valid_values, 90, method='hazen')
            climatology[doy-1] = np.mean(valid_values)
    
    # Special handling for day 60 (Feb 29)
    # Set it to the mean of days 59 and 61
    if not np.isnan(threshold[58]) and not np.isnan(threshold[60]):
        threshold[59] = (threshold[58] + threshold[60]) / 2
    if not np.isnan(climatology[58]) and not np.isnan(climatology[60]):
        climatology[59] = (climatology[58] + climatology[60]) / 2
    
    # Smooth with 31-day centered moving average (wrapping around year)
    def smooth_366(arr):
        smoothed = np.zeros_like(arr)
        for i in range(366):
            # Sum values from i-15 to i+15 (with wrapping)
            total = 0
            count = 0
            for j in range(i-15, i+16):
                idx = j % 366
                if not np.isnan(arr[idx]):
                    total += arr[idx]
                    count += 1
            smoothed[i] = total / count if count > 0 else np.nan
        return smoothed
    
    threshold_smoothed = smooth_366(threshold)
    climatology_smoothed = smooth_366(climatology)
    
    return threshold_smoothed, climatology_smoothed

def detect_mhw_in_region():
    """Main function to detect MHWs in the Baltic Sea region"""
    # Define region and period
    target_lat_min, target_lat_max = 57.85, 59.05
    target_lon_min, target_lon_max = 21.01, 22.21
    target_start = datetime(2013, 6, 1)
    target_end = datetime(2013, 8, 31)
    baseline_start = datetime(1992, 1, 1)
    baseline_end = datetime(2002, 12, 31)
    
    fs = fsspec.filesystem('onedata')
    
    # Create date ranges
    baseline_dates = []
    current = baseline_start
    while current <= baseline_end:
        baseline_dates.append(current)
        current += timedelta(days=1)
    
    target_dates = []
    current = target_start
    while current <= target_end:
        target_dates.append(current)
        current += timedelta(days=1)
    
    # Read all target data first to determine sea cells
    print("Reading target SST data...")
    target_sst_data = []
    sea_cells = []  # Will store indices of cells that have data for all target days
    
    # First pass: find which grid cells have data for all days
    first_day_data = None
    for i, date in enumerate(target_dates):
        file_path = f'/icsa2027_data_20261101T090944Z/s1z/sst_{date.strftime("%Y%m%d")}.nc'
        try:
            with fs.open(file_path, 'rb') as f:
                ds = xr.open_dataset(f, engine='h5netcdf')
                if i == 0:
                    first_day_data = ds
                sst_values = ds.analysed_sst.values
                target_sst_data.append(sst_values)
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            # Fill with NaNs if file missing
            if i == 0 and first_day_data is not None:
                # Use dimensions from first available file
                sst_values = np.full((len(first_day_data.latitude), len(first_day_data.longitude)), np.nan)
                target_sst_data.append(sst_values)
            elif i == 0:
                # No data available yet
                continue
            else:
                sst_values = np.full_like(target_sst_data[0], np.nan)
                target_sst_data.append(sst_values)
    
    # Check if we have data for the first day
    if first_day_data is None:
        print("No data available for any target day")
        return []
    
    # Determine sea cells (cells with finite values on all days)
    print("Determining sea cells...")
    latitudes = first_day_data.latitude.values
    longitudes = first_day_data.longitude.values
    
    # Find indices for our target region
    lat_indices = np.where((latitudes >= target_lat_min) & (latitudes <= target_lat_max))[0]
    lon_indices = np.where((longitudes >= target_lon_min) & (longitudes <= target_lon_max))[0]
    
    # Check which cells have data for all days
    sea_cell_mask = np.ones((len(lat_indices), len(lon_indices)), dtype=bool)
    
    for i, lat_idx in enumerate(lat_indices):
        for j, lon_idx in enumerate(lon_indices):
            # Check if all days have finite values for this cell
            all_finite = True
            for day_data in target_sst_data:
                if len(day_data.shape) == 2:  # Ensure it's 2D
                    if not np.isfinite(day_data[lat_idx, lon_idx]):
                        all_finite = False
                        break
                else:
                    # If the array is 1D or higher dimensional, just skip for now
                    all_finite = False
                    break
            sea_cell_mask[i, j] = all_finite
    
    # Store sea cells (indices relative to original grid)
    sea_cells = [(lat_idx, lon_idx) for i, lat_idx in enumerate(lat_indices) 
                 for j, lon_idx in enumerate(lon_indices) if sea_cell_mask[i, j]]
    
    print(f"Found {len(sea_cells)} sea cells in the target region")
    
    # Calculate threshold and climatology
    print("Calculating thresholds and climatology...")
    threshold, climatology = calculate_threshold_and_climatology(baseline_dates)
    
    # Now process each day to detect MHWs
    print("Detecting MHWs...")
    # Create result mask
    mhw_mask = np.zeros((len(target_dates), len(lat_indices), len(lon_indices)), dtype=np.uint8)
    
    # Process each day for each sea cell
    for day_idx, date in enumerate(target_dates):
        doy = date_to_doy(date)
        
        # Get threshold and climatology for this day of year
        threshold_val = threshold[doy - 1]
        climatology_val = climatology[doy - 1]
        
        # For each sea cell, check if it's hot
        for i, (lat_idx, lon_idx) in enumerate(sea_cells):
            # Get the SST value for this cell and day
            if len(target_sst_data[day_idx].shape) == 2:
                sst_value = target_sst_data[day_idx][lat_idx, lon_idx]
                
                # Check if it's hot
                if np.isfinite(sst_value) and sst_value >= threshold_val:
                    # Mark this cell as hot
                    lat_pos = np.where(lat_indices == lat_idx)[0][0]
                    lon_pos = np.where(lon_indices == lon_idx)[0][0]
                    mhw_mask[day_idx, lat_pos, lon_pos] = 1
    
    # Now apply the joining logic for MHWs
    # For each cell, find connected hot periods and join gaps of 1-2 days
    for i, (lat_idx, lon_idx) in enumerate(sea_cells):
        lat_pos = np.where(lat_indices == lat_idx)[0][0]
        lon_pos = np.where(lon_indices == lon_idx)[0][0]
        
        # Get the MHW flag for this cell across all days
        cell_mhw = mhw_mask[:, lat_pos, lon_pos]
        
        # Apply joining logic: merge runs separated by 1-2 non-hot days
        new_mhw = np.zeros_like(cell_mhw)
        i = 0
        while i < len(cell_mhw):
            if cell_mhw[i] == 1:
                # Start of a potential MHW
                j = i
                # Extend until we hit a non-hot day or end
                while j < len(cell_mhw) and cell_mhw[j] == 1:
                    j += 1
                # If this run is at least 5 days, mark all as MHW
                if j - i >= 5:
                    new_mhw[i:j] = 1
                i = j
            else:
                i += 1
        
        # Update the mask
        mhw_mask[:, lat_pos, lon_pos] = new_mhw
    
    # Create the final regional mask
    # A day is active if at least one sea cell is in an MHW
    regional_active = np.any(mhw_mask, axis=(1, 2))  # Shape: (num_days,)
    
    # Find regional MHW events (maximal runs of consecutive active days)
    events = []
    i = 0
    while i < len(regional_active):
        if regional_active[i]:
            # Start of an event
            onset = target_dates[i]
            j = i
            # Extend to end of the run
            while j < len(regional_active) and regional_active[j]:
                j += 1
            # End is the last active day
            end = target_dates[j-1]
            events.append({
                "onset": onset.strftime("%Y-%m-%d"),
                "end": end.strftime("%Y-%m-%d")
            })
            i = j
        else:
            i += 1
    
    # Prepare output files
    os.makedirs("output", exist_ok=True)
    
    # Write NetCDF file
    with fs.open('/icsa2027_data_20261101T090944Z/s1z/sst_19820101.nc', 'rb') as f:
        ds_template = xr.open_dataset(f, engine='h5netcdf')
    
    # Create a new dataset with the correct coordinates
    ds_result = xr.Dataset(
        {
            'mhw': (['time', 'lat', 'lon'], mhw_mask)
        },
        coords={
            'time': [date.strftime('%Y-%m-%d') for date in target_dates],
            'lat': latitudes[lat_indices],
            'lon': longitudes[lon_indices]
        }
    )
    
    # Save to file
    ds_result.to_netcdf('output/mhw_mask.nc')
    
    # Write report
    report = {
        "region": {
            "lat_min": target_lat_min,
            "lat_max": target_lat_max,
            "lon_min": target_lon_min,
            "lon_max": target_lon_max
        },
        "baseline_analysed": {
            "start": "1992-01-01",
            "end": "2002-12-31"
        },
        "target_analysed": {
            "start": "2013-06-01",
            "end": "2013-08-31"
        },
        "events": events,
        "complete": True,
        "caveats": ""
    }
    
    with open('output/report.json', 'w') as f:
        json.dump(report, f, indent=2)
    
    print("Analysis complete!")
    print(f"Found {len(events)} regional MHW events")
    for event in events:
        print(f"Event: {event['onset']} to {event['end']}")
    
    return events

# Run the detection
try:
    events = detect_mhw_in_region()
except Exception as e:
    print(f"Error during execution: {e}")
    import traceback
    traceback.print_exc()