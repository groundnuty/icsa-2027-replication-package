import xarray as xr
import fsspec
import numpy as np
from datetime import datetime, timedelta
import os
import gc
from scipy import stats

def day_of_year(date):
    """Convert date to day of year (1-366)"""
    # Handle leap year cases
    if date.month == 2 and date.day == 29:
        return 60
    # Convert to day of year
    doy = date.timetuple().tm_yday
    # Adjust for leap year cases (if not leap year, Feb 29 doesn't exist)
    if not is_leap_year(date.year) and date.month > 2:
        doy -= 1
    return doy

def is_leap_year(year):
    """Check if year is leap year"""
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)

def get_doy_from_date(date_str):
    """Get day of year from YYYY-MM-DD string"""
    date = datetime.strptime(date_str, "%Y-%m-%d")
    return day_of_year(date)

def get_date_from_doy(doy, year):
    """Get date from day of year and year"""
    # This is a bit tricky because we need to handle leap years correctly
    if doy == 60 and not is_leap_year(year):
        # Non-leap year, so day 60 doesn't exist
        return None
    
    # Create January 1st of that year
    jan1 = datetime(year, 1, 1)
    
    # Add the appropriate number of days
    target_date = jan1 + timedelta(days=doy-1)
    
    # Special handling for leap year day 60
    if doy == 60:
        return datetime(year, 2, 29)
    
    return target_date

def get_baseline_dates():
    """Get all dates in baseline period 1992-2002"""
    baseline_dates = []
    for year in range(1992, 2003):  # 1992 to 2002 inclusive
        # For each year, get all dates
        for month in range(1, 13):
            if month in [1, 3, 5, 7, 8, 10, 12]:
                days_in_month = 31
            elif month in [4, 6, 9, 11]:
                days_in_month = 30
            else:  # February
                days_in_month = 29 if is_leap_year(year) else 28
                
            for day in range(1, days_in_month + 1):
                date = datetime(year, month, day)
                baseline_dates.append(date)
    return baseline_dates

def get_all_dates(start_date_str, end_date_str):
    """Get all dates in a range"""
    start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
    end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
    
    dates = []
    current_date = start_date
    while current_date <= end_date:
        dates.append(current_date)
        current_date += timedelta(days=1)
        
    return dates

def get_window_dates(target_date, baseline_dates, window_size=5):
    """Get baseline dates within window around target_date"""
    # Find the corresponding day of year for the target date
    target_doy = day_of_year(target_date)
    
    # Get all baseline dates with matching day of year (±window_size days)
    window_dates = []
    
    # We want to find dates in baseline that are within ±window_size days of target_doy
    # But we also need to consider the actual calendar dates
    
    # For day 60 (Feb 29), we don't create a separate pool
    if target_doy == 60:
        return []
        
    # Find all dates in baseline that match the day of year
    matching_doy_dates = []
    for baseline_date in baseline_dates:
        if day_of_year(baseline_date) == target_doy:
            matching_doy_dates.append(baseline_date)
    
    # For each matching date, we look within ±window_size days
    for baseline_date in matching_doy_dates:
        # Calculate the date range for the window
        start_window = baseline_date - timedelta(days=window_size)
        end_window = baseline_date + timedelta(days=window_size)
        
        # Include all dates in the window
        current = start_window
        while current <= end_window:
            if current in baseline_dates:  # Make sure it exists in our baseline
                window_dates.append(current)
            current += timedelta(days=1)
    
    # Remove duplicates and sort
    window_dates = sorted(list(set(window_dates)))
    return window_dates

def load_and_process_data():
    """Load and process the data for our analysis"""
    fs = fsspec.filesystem('onedata')
    
    # Define our region
    lat_min, lat_max = 56.13, 57.33
    lon_min, lon_max = 17.71, 18.91
    
    # Define periods
    baseline_start = "1992-01-01"
    baseline_end = "2002-12-31"
    target_start = "2015-06-01"
    target_end = "2015-08-31"
    
    # Get all baseline dates
    baseline_dates = get_baseline_dates()
    baseline_dates = [d for d in baseline_dates if baseline_start <= d.strftime("%Y-%m-%d") <= baseline_end]
    
    print(f"Baseline period: {baseline_start} to {baseline_end}")
    print(f"Total baseline dates: {len(baseline_dates)}")
    
    # Get all target dates
    target_dates = get_all_dates(target_start, target_end)
    print(f"Target period: {target_start} to {target_end}")
    print(f"Total target dates: {len(target_dates)}")
    
    # First, we need to identify the sea cells that have finite SST on every day of target period
    # For this, we'll need to load some data to determine which grid points are valid
    
    # Load a sample of target period data to determine sea cells
    print("Loading sample target period data to identify sea cells...")
    
    # Load data for a few days to identify valid cells
    sea_cells = set()  # Will store (lat_idx, lon_idx) pairs
    valid_target_dates = []
    
    # Try loading some target dates to identify sea cells
    test_days = min(10, len(target_dates))  # Just a few days to start
    for i, target_date in enumerate(target_dates[:test_days]):
        date_str = target_date.strftime("%Y-%m-%d")
        filename = f"/icsa2027_data_20261101T090944Z/s1z/sst_{date_str.replace('-', '')}.nc"
        
        try:
            # Download and load the file
            local_path = f"/work/sst_{date_str.replace('-', '')}.nc"
            fs.get(filename, local_path)
            
            ds = xr.open_dataset(local_path, engine='h5netcdf')
            sst = ds['analysed_sst'].squeeze()  # Remove time dimension
            
            # Find valid (finite) SST values in our region
            lat_indices = np.where((ds.latitude >= lat_min) & (ds.latitude <= lat_max))[0]
            lon_indices = np.where((ds.longitude >= lon_min) & (ds.longitude <= lon_max))[0]
            
            if len(lat_indices) > 0 and len(lon_indices) > 0:
                # Extract the subset for our region
                sst_subset = sst.isel(latitude=lat_indices, longitude=lon_indices)
                
                # Check which grid cells have finite values
                valid_cells = np.where(np.isfinite(sst_subset.values))
                
                for j, k in zip(valid_cells[0], valid_cells[1]):
                    # Store the original indices
                    orig_lat_idx = lat_indices[j]
                    orig_lon_idx = lon_indices[k]
                    sea_cells.add((orig_lat_idx, orig_lon_idx))
                    
                valid_target_dates.append(target_date)
                ds.close()
                os.remove(local_path)
                
        except Exception as e:
            print(f"Error processing {date_str}: {e}")
            continue
    
    print(f"Identified {len(sea_cells)} sea cells")
    
    # Now we'll build the climatology and thresholds
    # We need to compute pools for each day of year
    print("Computing climatology and thresholds...")
    
    # Initialize arrays for climatology and thresholds
    climatology = np.full(366, np.nan, dtype=np.float64)
    threshold = np.full(366, np.nan, dtype=np.float64)
    
    # Process each day of year (1-366)
    for doy in range(1, 367):
        # Skip day 60 for individual computation (it will be handled specially)
        if doy == 60:
            continue
            
        # Collect all baseline dates that correspond to this day of year
        pool_dates = []
        for baseline_date in baseline_dates:
            if day_of_year(baseline_date) == doy:
                # Add dates within ±5 days of this baseline date
                start_window = baseline_date - timedelta(days=5)
                end_window = baseline_date + timedelta(days=5)
                
                # Check all dates in window
                current = start_window
                while current <= end_window:
                    if current in baseline_dates:
                        pool_dates.append(current)
                    current += timedelta(days=1)
        
        # Get unique pool dates and remove duplicates
        pool_dates = list(set(pool_dates))
        
        # Now collect SST values for these dates
        pool_values = []
        
        for pool_date in pool_dates:
            date_str = pool_date.strftime("%Y-%m-%d")
            filename = f"/icsa2027_data_20261101T090944Z/s1z/sst_{date_str.replace('-', '')}.nc"
            
            try:
                local_path = f"/work/sst_{date_str.replace('-', '')}.nc"
                fs.get(filename, local_path)
                
                ds = xr.open_dataset(local_path, engine='h5netcdf')
                sst = ds['analysed_sst'].squeeze()
                
                # Extract values for our sea cells
                for lat_idx, lon_idx in sea_cells:
                    val = sst.values[lat_idx, lon_idx]
                    if np.isfinite(val):
                        pool_values.append(val)
                
                ds.close()
                os.remove(local_path)
            except Exception as e:
                # print(f"Error reading {date_str}: {e}")
                continue
        
        # Compute threshold and climatology for this day of year
        if len(pool_values) > 0:
            # Use numpy's method="hazen" equivalent (which is the 5th quantile type)
            # np.quantile with method='linear' is close to MATLAB's default
            threshold[doy-1] = np.quantile(pool_values, 0.9, method='linear')
            climatology[doy-1] = np.mean(pool_values)
        else:
            # If no data, set to NaN
            threshold[doy-1] = np.nan
            climatology[doy-1] = np.nan
    
    # Handle day 60 (February 29) specially
    # Set to mean of days 59 and 61
    if not np.isnan(climatology[58]) and not np.isnan(climatology[60]):  # Days 59 and 61 (0-indexed)
        climatology[59] = (climatology[58] + climatology[60]) / 2  # Day 60 (0-indexed as 59)
    else:
        climatology[59] = np.nan
        
    if not np.isnan(threshold[58]) and not np.isnan(threshold[60]):
        threshold[59] = (threshold[58] + threshold[60]) / 2  # Day 60 (0-indexed as 59)
    else:
        threshold[59] = np.nan
    
    # Apply smoothing with 31-day moving average that wraps around
    print("Applying smoothing...")
    smoothed_climatology = smooth_366_array(climatology)
    smoothed_threshold = smooth_366_array(threshold)
    
    # Now detect MHWs in the target period
    print("Detecting MHWs...")
    
    # Prepare result arrays
    mhw_mask = np.zeros((len(target_dates), len(sea_cells)), dtype=np.uint8)
    
    # Reorder sea cells for consistent indexing
    sea_cells_list = sorted(list(sea_cells))
    
    # Create coordinate arrays for the final NetCDF
    lat_coords = []
    lon_coords = []
    
    # Load the reference file to get coordinates
    ref_file = "/icsa2027_data_20261101T090944Z/s1z/sst_19820101.nc"
    fs.get(ref_file, "/work/ref.nc")
    ref_ds = xr.open_dataset("/work/ref.nc", engine='h5netcdf')
    
    # Get the full coordinate arrays
    full_lats = ref_ds.latitude.values
    full_lons = ref_ds.longitude.values
    
    # Get coordinates for our sea cells
    sea_cell_lats = []
    sea_cell_lons = []
    for lat_idx, lon_idx in sea_cells_list:
        sea_cell_lats.append(full_lats[lat_idx])
        sea_cell_lons.append(full_lons[lon_idx])
        
    ref_ds.close()
    os.remove("/work/ref.nc")
    
    # Process target period
    target_day_indices = []  # To keep track of which days we actually processed
    
    for i, target_date in enumerate(target_dates):
        date_str = target_date.strftime("%Y-%m-%d")
        filename = f"/icsa2027_data_20261101T090944Z/s1z/sst_{date_str.replace('-', '')}.nc"
        
        try:
            local_path = f"/work/sst_{date_str.replace('-', '')}.nc"
            fs.get(filename, local_path)
            
            ds = xr.open_dataset(local_path, engine='h5netcdf')
            sst = ds['analysed_sst'].squeeze()
            
            # Get day of year for this date
            doy = day_of_year(target_date)
            
            # Get threshold for this day of year
            threshold_val = smoothed_threshold[doy-1]  # Convert to 0-based indexing
            
            # For each sea cell, check if SST exceeds threshold
            for j, (lat_idx, lon_idx) in enumerate(sea_cells_list):
                val = sst.values[lat_idx, lon_idx]
                if np.isfinite(val) and val >= threshold_val:
                    mhw_mask[i, j] = 1
                    
            target_day_indices.append(i)
            ds.close()
            os.remove(local_path)
            
        except Exception as e:
            print(f"Error processing {date_str}: {e}")
            continue
    
    # Now perform the MHW merging and detection
    print("Performing MHW detection and merging...")
    
    # For each sea cell, identify runs of at least 5 consecutive hot days
    # and join gaps of 1-2 days
    merged_mhw = np.zeros_like(mhw_mask, dtype=np.uint8)
    
    for j in range(len(sea_cells_list)):
        # Extract the time series for this cell
        cell_series = mhw_mask[:, j]
        
        # Find runs of consecutive hot days (at least 5)
        runs = find_hot_runs(cell_series, min_run_length=5)
        
        # Join gaps of 1-2 days
        merged_runs = join_gaps(runs, max_gap=2)
        
        # Mark the merged MHWs in the mask
        for start, end in merged_runs:
            merged_mhw[start:end+1, j] = 1
    
    # Create final report
    events = detect_regional_events(merged_mhw)
    
    # Write results to files
    save_results(merged_mhw, target_dates, sea_cells_list, sea_cell_lats, sea_cell_lons, events)
    
    # Create report
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
    with open('/work/report.json', 'w') as f:
        json.dump(report, f, indent=2)
        
    print("Analysis complete!")
    print(f"Found {len(events)} regional MHW events")
    return report

def smooth_366_array(arr):
    """Apply 31-day centered moving average that wraps around"""
    # Create a copy for the result
    smoothed = np.empty_like(arr, dtype=np.float64)
    
    # For each element, compute the average of 31 elements (15 before, 15 after, plus itself)
    for i in range(366):
        # Get the indices for the window (wrapping around)
        window_sum = 0.0
        count = 0
        
        for j in range(-15, 16):  # -15 to 15 inclusive (15 before, 15 after, 1 itself)
            idx = (i + j) % 366  # Wrap around using modulo
            if not np.isnan(arr[idx]):
                window_sum += arr[idx]
                count += 1
                
        # If we found any valid values, assign the mean
        if count > 0:
            smoothed[i] = window_sum / count
        else:
            smoothed[i] = np.nan
    
    return smoothed

def find_hot_runs(series, min_run_length=5):
    """Find runs of consecutive hot days (1s) of at least min_run_length"""
    runs = []
    i = 0
    while i < len(series):
        if series[i] == 1:
            start = i
            # Extend the run
            while i < len(series) and series[i] == 1:
                i += 1
            end = i - 1
            # Only include runs of sufficient length
            if end - start + 1 >= min_run_length:
                runs.append((start, end))
        else:
            i += 1
    return runs

def join_gaps(runs, max_gap=2):
    """Join consecutive runs that are separated by max_gap or fewer days"""
    if not runs:
        return runs
    
    merged = [runs[0]]
    
    for i in range(1, len(runs)):
        prev_start, prev_end = merged[-1]
        curr_start, curr_end = runs[i]
        
        # Check if gap is acceptable
        gap = curr_start - prev_end - 1
        if gap <= max_gap:
            # Merge the runs
            merged[-1] = (prev_start, curr_end)
        else:
            merged.append((curr_start, curr_end))
            
    return merged

def detect_regional_events(mhw_mask):
    """Detect regional MHW events based on active days"""
    # A day is active if at least one sea cell is inside an MHW
    active_days = np.any(mhw_mask, axis=1)
    
    # Find runs of consecutive active days
    events = []
    i = 0
    while i < len(active_days):
        if active_days[i]:
            start = i
            # Extend the run
            while i < len(active_days) and active_days[i]:
                i += 1
            end = i - 1
            # Convert indices to dates
            events.append({
                "onset": f"{start:04d}-{start:02d}-{start:02d}",
                "end": f"{end:04d}-{end:02d}-{end:02d}"
            })
        else:
            i += 1
    
    return events

def save_results(mhw_mask, target_dates, sea_cells_list, sea_cell_lats, sea_cell_lons, events):
    """Save results to NetCDF and JSON files"""
    # Create the directory if it doesn't exist
    os.makedirs('/work/output', exist_ok=True)
    
    # Save MHW mask to NetCDF
    import xarray as xr
    
    # Create coordinate arrays
    times = [date.strftime("%Y-%m-%d") for date in target_dates]
    
    # Create DataArray
    da = xr.DataArray(
        mhw_mask,
        dims=['time', 'location'],
        coords={
            'time': times,
            'lat': ('location', sea_cell_lats),
            'lon': ('location', sea_cell_lons)
        },
        name='mhw',
        attrs={'units': 'binary', 'long_name': 'Marine Heatwave indicator'}
    )
    
    # Create Dataset
    ds = xr.Dataset({'mhw': da})
    
    # Save to NetCDF
    ds.to_netcdf('/work/output/mhw_mask.nc')
    
    print(f"Saved MHW mask with shape {mhw_mask.shape}")
    print(f"Saved to /work/output/mhw_mask.nc")

# Run the analysis
try:
    report = load_and_process_data()
except Exception as e:
    print(f"Error in main analysis: {e}")
    import traceback
    traceback.print_exc()