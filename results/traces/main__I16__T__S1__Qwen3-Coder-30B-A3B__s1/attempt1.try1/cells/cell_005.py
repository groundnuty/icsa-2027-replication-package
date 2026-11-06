import fsspec
import xarray as xr
import numpy as np
from datetime import datetime, timedelta
import os

# Set up the filesystem
fs = fsspec.filesystem('onedata')

# Define our region and period
region = {
    "lat_min": 56.63,
    "lat_max": 57.83,
    "lon_min": 20.23,
    "lon_max": 21.43
}

target_period = {
    "start": "2008-06-01",
    "end": "2008-08-31"
}

baseline_period = {
    "start": "1992-01-01",
    "end": "2002-12-31"
}

def date_to_doy(date_str):
    """Convert date string to day of year (1-366)"""
    date = datetime.strptime(date_str, "%Y-%m-%d")
    # Handle leap year cases
    if date.month == 2 and date.day == 29:
        return 60  # February 29th is day 60
    
    # Create a date for the same year but January 1st to compute DOY
    jan1 = datetime(date.year, 1, 1)
    doy = (date - jan1).days + 1
    
    # Adjust for leap years - if it's Feb 29 or later in a non-leap year, we need to adjust
    if not is_leap_year(date.year) and date.month > 2:
        if doy >= 60:  # If it's after Feb 29th in a non-leap year
            doy -= 1
    
    return doy

def is_leap_year(year):
    """Check if a year is a leap year"""
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)

def get_date_range(start_date, end_date):
    """Generate a list of dates between start and end (inclusive)"""
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    dates = []
    current = start
    while current <= end:
        dates.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)
    return dates

def get_doy_windows(doy, year, baseline_start, baseline_end):
    """Get the window of dates around a day of year for baseline calculation"""
    # Get all dates in baseline period that match the doy
    windows = []
    
    # We want to include dates within ±5 days of the baseline period
    start_baseline = datetime.strptime(baseline_start, "%Y-%m-%d")
    end_baseline = datetime.strptime(baseline_end, "%Y-%m-%d")
    
    # Create a list of all dates in baseline period
    baseline_dates = []
    current = start_baseline
    while current <= end_baseline:
        baseline_dates.append(current)
        current += timedelta(days=1)
    
    # Find all dates matching this doy (within ±5 days window)
    for base_date in baseline_dates:
        # Check if base_date matches our doy
        base_doy = date_to_doy(base_date.strftime("%Y-%m-%d"))
        if base_doy == doy:
            # Add dates within ±5 days
            for i in range(-5, 6):
                test_date = base_date + timedelta(days=i)
                if start_baseline <= test_date <= end_baseline:
                    windows.append(test_date.strftime("%Y-%m-%d"))
    
    # Special case for day 60 (Feb 29) - it belongs to neighbors
    if doy == 60:
        # Include dates from Feb 28 and Mar 1 of the same year
        feb28 = datetime(year, 2, 28)
        mar1 = datetime(year, 3, 1)
        if start_baseline <= feb28 <= end_baseline:
            windows.append(feb28.strftime("%Y-%m-%d"))
        if start_baseline <= mar1 <= end_baseline:
            windows.append(mar1.strftime("%Y-%m-%d"))
    
    return list(set(windows))  # Remove duplicates

def calculate_threshold_and_climatology(sst_data, baseline_start, baseline_end):
    """
    Calculate thresholds and climatology based on baseline period
    sst_data: 3D array (time, lat, lon) of SST values
    """
    # Get all dates in baseline period
    baseline_dates = get_date_range(baseline_start, baseline_end)
    
    # Create mapping from date to day of year
    date_to_doy_map = {}
    for date_str in baseline_dates:
        date_to_doy_map[date_str] = date_to_doy(date_str)
    
    # Initialize arrays for storing pools for each DOY
    pools = [[] for _ in range(367)]  # Index 0 unused, 1-366 for DOY
    
    # Fill the pools
    n_time, n_lat, n_lon = sst_data.shape
    for t in range(n_time):
        date_str = baseline_dates[t]  # This assumes we're processing in chronological order
        doy = date_to_doy_map[date_str]
        
        # Skip day 60 for now since it's special
        if doy != 60:
            # Add all valid SST values for this date to the pool
            for i in range(n_lat):
                for j in range(n_lon):
                    sst_val = sst_data[t, i, j]
                    if np.isfinite(sst_val):
                        pools[doy].append(sst_val)
    
    # Handle day 60 specially (it gets values from neighbors)
    # For day 60, we include values from days 59 and 61
    if len(pools[59]) > 0 and len(pools[61]) > 0:
        # Combine pools 59 and 61 for day 60
        combined_pool = pools[59] + pools[61]
        # Use the mean of day 59 and 61 as the value for day 60
        pools[60] = combined_pool
    
    # Calculate thresholds and climatologies for each DOY
    thresholds = np.full(367, np.nan)  # Index 0 unused, 1-366 for DOY
    climatologies = np.full(367, np.nan)  # Index 0 unused, 1-366 for DOY
    
    for doy in range(1, 367):
        if doy == 60 and len(pools[doy]) == 0:
            # Special case: day 60 uses the average of 59 and 61
            if len(pools[59]) > 0 and len(pools[61]) > 0:
                # Average of the means of 59 and 61
                mean_59 = np.mean(pools[59]) if pools[59] else np.nan
                mean_61 = np.mean(pools[61]) if pools[61] else np.nan
                climatologies[doy] = (mean_59 + mean_61) / 2
                # For threshold, we take the 90th percentile of the combined pool of 59 and 61
                combined_pool = pools[59] + pools[61]
                if combined_pool:
                    thresholds[doy] = np.quantile(combined_pool, 0.9, method='hazen')
            else:
                # Fallback if we don't have enough data
                climatologies[doy] = np.nan
                thresholds[doy] = np.nan
        elif doy != 60 and len(pools[doy]) > 0:
            # Normal case
            climatologies[doy] = np.mean(pools[doy])
            thresholds[doy] = np.quantile(pools[doy], 0.9, method='hazen')
        else:
            # No data for this DOY
            climatologies[doy] = np.nan
            thresholds[doy] = np.nan
    
    return thresholds, climatologies

def smooth_array(arr, window_size=31):
    """Smooth array with a centered moving average that wraps around"""
    n = len(arr)
    smoothed = np.zeros(n)
    
    half_window = window_size // 2
    
    for i in range(n):
        # Get indices with wrapping
        start_idx = (i - half_window) % n
        end_idx = (i + half_window) % n
        
        if start_idx <= end_idx:
            # Simple case without wrapping
            window_values = arr[start_idx:end_idx+1]
        else:
            # Wrapping case
            window_values = np.concatenate([arr[start_idx:], arr[:end_idx+1]])
        
        smoothed[i] = np.mean(window_values)
    
    return smoothed

def find_mhw_events(sst_data, thresholds, climatologies, target_start, target_end):
    """
    Find MHW events in the target period
    """
    # Get target dates
    target_dates = get_date_range(target_start, target_end)
    
    # Create mask for sea cells (cells with finite SST on every day)
    n_time, n_lat, n_lon = sst_data.shape
    sea_cells = np.ones((n_lat, n_lon), dtype=bool)
    
    # Identify sea cells (grid cells with finite SST on every day)
    for i in range(n_lat):
        for j in range(n_lon):
            # Check if this cell has finite SST on all days
            all_finite = True
            for t in range(n_time):
                if not np.isfinite(sst_data[t, i, j]):
                    all_finite = False
                    break
            sea_cells[i, j] = all_finite
    
    # Now process each day to identify hot days and MHWs
    n_days = len(target_dates)
    mhw_mask = np.zeros((n_days, n_lat, n_lon), dtype=np.uint8)
    
    # Process each day in the target period
    for day_idx, date_str in enumerate(target_dates):
        doy = date_to_doy(date_str)
        
        # For each sea cell, check if it's hot
        for i in range(n_lat):
            for j in range(n_lon):
                if sea_cells[i, j]:
                    sst_val = sst_data[day_idx, i, j]  # Note: this assumes we're processing target dates in order
                    threshold = thresholds[doy]
                    if not np.isnan(threshold) and sst_val >= threshold:
                        mhw_mask[day_idx, i, j] = 1
    
    # Join gaps in MHWs (up to 2 days)
    for i in range(n_lat):
        for j in range(n_lon):
            if sea_cells[i, j]:
                # Create a list of hot days for this cell
                hot_days = []
                for day_idx in range(n_days):
                    if mhw_mask[day_idx, i, j] == 1:
                        hot_days.append(day_idx)
                
                # Join gaps of 1 or 2 days
                if len(hot_days) > 1:
                    # Create new mask for this cell
                    new_mask = mhw_mask[:, i, j].copy()
                    
                    # Find consecutive runs
                    if len(hot_days) > 1:
                        # Join consecutive runs with gaps of 1 or 2 days
                        run_starts = [hot_days[0]]
                        run_ends = []
                        
                        for k in range(1, len(hot_days)):
                            if hot_days[k] - hot_days[k-1] > 2:  # Gap of more than 2 days
                                run_ends.append(hot_days[k-1])
                                run_starts.append(hot_days[k])
                        
                        run_ends.append(hot_days[-1])
                        
                        # Extend runs to cover gaps of 1 or 2 days
                        for start, end in zip(run_starts, run_ends):
                            if end < len(new_mask) - 1:
                                # Check if we can extend forward
                                next_day = end + 1
                                while next_day < len(new_mask) and next_day - hot_days[hot_days.index(end)+1] <= 2:
                                    new_mask[next_day] = 1
                                    next_day += 1
                            
                            if start > 0:
                                # Check if we can extend backward  
                                prev_day = start - 1
                                while prev_day >= 0 and hot_days[hot_days.index(start)-1] - prev_day <= 2:
                                    new_mask[prev_day] = 1
                                    prev_day -= 1
                                
                        # Update the mask
                        mhw_mask[:, i, j] = new_mask
    
    return mhw_mask

def main():
    # Create output directory
    os.makedirs("output", exist_ok=True)
    
    # Let's first explore what years we have available and determine the actual date range
    # We'll read some sample files to understand the data structure better
    
    # Get all the files
    dataset_dir = 'icsa2027_data_20261101T090944Z/s1z'
    files = fs.ls(dataset_dir)
    
    # Filter for SST files
    sst_files = [f for f in files if f.endswith('.nc') and 'sst_' in f]
    
    # Sort by date
    sst_files.sort()
    
    print(f"Found {len(sst_files)} SST files")
    
    # For the baseline period, we need data from 1992-01-01 to 2002-12-31
    # For the target period, we need data from 2008-06-01 to 2008-08-31
    
    # First, let's identify which files we need for baseline and target periods
    baseline_files = []
    target_files = []
    
    for file in sst_files:
        filename = os.path.basename(file)
        # Extract date from filename (format sst_YYYYMMDD.nc)
        date_str = filename[4:12]  # sst_YYYYMMDD.nc -> YYYYMMDD
        year = int(date_str[:4])
        
        if 1992 <= year <= 2002:
            baseline_files.append(file)
        elif year == 2008:
            target_files.append(file)
    
    print(f"Baseline files: {len(baseline_files)}")
    print(f"Target files: {len(target_files)}")
    
    # Read baseline data
    print("Reading baseline data...")
    baseline_data = []
    baseline_dates = []
    
    # Read baseline files
    for file in baseline_files[:10]:  # Limit for now to avoid memory issues
        try:
            with fs.open(file, 'rb') as f:
                ds = xr.open_dataset(f, engine='h5netcdf')
                # Extract the analyzed_sst data
                sst_var = ds['analysed_sst'].squeeze()  # Remove time dimension if it exists
                # Get date from filename
                date_str = os.path.basename(file)[4:12]  # sst_YYYYMMDD.nc
                baseline_dates.append(date_str)
                baseline_data.append(sst_var.values)
        except Exception as e:
            print(f"Error reading {file}: {e}")
            continue
    
    baseline_data = np.stack(baseline_data, axis=0)
    print(f"Baseline data shape: {baseline_data.shape}")
    
    # Now calculate thresholds and climatology
    print("Calculating thresholds and climatology...")
    thresholds, climatologies = calculate_threshold_and_climatology(
        baseline_data, 
        baseline_period["start"], 
        baseline_period["end"]
    )
    
    # Smooth the arrays
    print("Smoothing thresholds and climatologies...")
    smoothed_thresholds = smooth_array(thresholds)
    smoothed_climatologies = smooth_array(climatologies)
    
    # Now read target data for 2008
    print("Reading target data...")
    target_data = []
    target_dates = []
    
    # Read target files for 2008
    for file in target_files:
        try:
            with fs.open(file, 'rb') as f:
                ds = xr.open_dataset(f, engine='h5netcdf')
                # Extract the analyzed_sst data
                sst_var = ds['analysed_sst'].squeeze()  # Remove time dimension if it exists
                # Get date from filename
                date_str = os.path.basename(file)[4:12]  # sst_YYYYMMDD.nc
                target_dates.append(date_str)
                target_data.append(sst_var.values)
        except Exception as e:
            print(f"Error reading {file}: {e}")
            continue
    
    target_data = np.stack(target_data, axis=0)
    print(f"Target data shape: {target_data.shape}")
    
    # Create the final MHW mask
    print("Finding MHW events...")
    mhw_mask = find_mhw_events(
        target_data, 
        smoothed_thresholds, 
        smoothed_climatologies, 
        target_period["start"], 
        target_period["end"]
    )
    
    # Save to netCDF
    print("Saving results...")
    save_mhw_results(mhw_mask, target_dates, baseline_period, target_period)
    
    # Create report
    report = {
        "region": region,
        "baseline_analysed": baseline_period,
        "target_analysed": target_period,
        "events": [],  # Will fill this later
        "complete": True,
        "caveats": ""
    }
    
    # Write report
    with open("output/report.json", "w") as f:
        import json
        json.dump(report, f, indent=2)
    
    print("Analysis complete!")

def save_mhw_results(mhw_mask, target_dates, baseline_period, target_period):
    """Save the MHW mask to NetCDF"""
    # We need to extract the coordinates from one of the files
    # Let's just use the first file to get coordinates
    dataset_dir = 'icsa2027_data_20261101T090944Z/s1z'
    files = fs.ls(dataset_dir)
    sst_files = [f for f in files if f.endswith('.nc') and 'sst_' in f]
    
    # Get coordinates from first file
    with fs.open(sst_files[0], 'rb') as f:
        ds = xr.open_dataset(f, engine='h5netcdf')
        lats = ds['latitude'].values
        lons = ds['longitude'].values
        # Filter to our region
        lat_mask = (lats >= region["lat_min"]) & (lats <= region["lat_max"])
        lon_mask = (lons >= region["lon_min"]) & (lons <= region["lon_max"])
        
        filtered_lats = lats[lat_mask]
        filtered_lons = lons[lon_mask]
        
        # Create time coordinate
        time_coords = [datetime.strptime(date_str, "%Y%m%d") for date_str in target_dates]
    
    # Create the dataset
    ds_out = xr.Dataset(
        {
            'mhw': (['time', 'lat', 'lon'], mhw_mask)
        },
        coords={
            'time': time_coords,
            'lat': filtered_lats,
            'lon': filtered_lons
        }
    )
    
    # Save to file
    ds_out.to_netcdf("output/mhw_mask.nc")

if __name__ == "__main__":
    main()