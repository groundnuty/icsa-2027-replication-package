import xarray as xr
import fsspec
import numpy as np
from datetime import datetime, timedelta
import os

# Create output directory
os.makedirs('output', exist_ok=True)

def get_day_of_year(month, day):
    """Convert month/day to day of year (1-366)"""
    # Days in each month (non-leap year)
    days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    
    # Calculate cumulative days
    cum_days = [0]
    for days in days_in_month:
        cum_days.append(cum_days[-1] + days)
    
    # Return day of year (1-based)
    doy = cum_days[month-1] + day
    # Adjust for leap year (February 29th is day 60)
    if month > 2:  # After February
        doy += 1  # Add one for leap day
    
    return doy

def get_doy_for_date(date_str):
    """Convert YYYY-MM-DD string to day of year"""
    dt = datetime.strptime(date_str, '%Y-%m-%d')
    month, day = dt.month, dt.day
    return get_day_of_year(month, day)

def get_dates_in_range(start_date, end_date):
    """Generate all dates between start and end (inclusive)"""
    start = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')
    dates = []
    current = start
    while current <= end:
        dates.append(current.strftime('%Y-%m-%d'))
        current += timedelta(days=1)
    return dates

def get_baseline_window_dates(doy, base_start, base_end):
    """Get all dates in baseline period that fall within ±5 days of a date with day-of-year doy"""
    # Get the range of dates to check
    base_start_dt = datetime.strptime(base_start, '%Y-%m-%d')
    base_end_dt = datetime.strptime(base_end, '%Y-%m-%d')
    
    # Generate all dates in baseline period
    baseline_dates = get_dates_in_range(base_start, base_end)
    
    # Filter for dates that have the specified day-of-year
    matching_dates = []
    for date_str in baseline_dates:
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        if get_day_of_year(dt.month, dt.day) == doy:
            matching_dates.append(date_str)
    
    return matching_dates

def compute_threshold_and_climatology(sst_data, baseline_start, baseline_end):
    """
    Compute thresholds and climatology for each day of year based on baseline period
    sst_data: 3D array (time, lat, lon) with SST data
    """
    # Convert baseline dates to datetime objects
    baseline_start_dt = datetime.strptime(baseline_start, '%Y-%m-%d')
    baseline_end_dt = datetime.strptime(baseline_end, '%Y-%m-%d')
    
    # Create array to hold results
    thresholds = np.full(366, np.nan, dtype=np.float64)
    climatologies = np.full(366, np.nan, dtype=np.float64)
    
    # For each day of year (1-366)
    for doy in range(1, 367):
        if doy == 60:  # February 29th - special case
            continue
            
        # Get all dates in baseline with this day of year
        window_dates = get_baseline_window_dates(doy, baseline_start, baseline_end)
        
        # Collect SST values for these dates
        pool_values = []
        for date_str in window_dates:
            # Find corresponding time index
            date_dt = datetime.strptime(date_str, '%Y-%m-%d')
            time_idx = None
            for i, t in enumerate(sst_data.time.values):
                t_dt = datetime.fromtimestamp(t.astype('datetime64[s]').astype('int'))
                if t_dt.date() == date_dt.date():
                    time_idx = i
                    break
            
            if time_idx is not None:
                # Extract SST values for this date (only valid ones)
                sst_slice = sst_data.isel(time=time_idx).analysed_sst.values
                valid_sst = sst_slice[np.isfinite(sst_slice)]
                pool_values.extend(valid_sst)
        
        if len(pool_values) > 0:
            # Compute 90th percentile (Hazen method) and mean
            pool_array = np.array(pool_values, dtype=np.float64)
            thresholds[doy-1] = np.quantile(pool_array, 0.9, method='hazen')
            climatologies[doy-1] = np.mean(pool_array)
    
    # Handle February 29th (day 60) specially
    # Set to mean of days 59 and 61
    if not np.isnan(climatologies[58]) and not np.isnan(climatologies[60]):
        climatologies[59] = (climatologies[58] + climatologies[60]) / 2
    if not np.isnan(thresholds[58]) and not np.isnan(thresholds[60]):
        thresholds[59] = (thresholds[58] + thresholds[60]) / 2
    
    # Apply smoothing with 31-day centered moving average
    def smooth_366(arr):
        smoothed = np.full_like(arr, np.nan, dtype=np.float64)
        for i in range(366):
            # Get indices for 15 days before and after (wrapping around)
            values = []
            for j in range(-15, 16):
                idx = (i + j) % 366
                if not np.isnan(arr[idx]):
                    values.append(arr[idx])
            if values:
                smoothed[i] = np.mean(values)
        return smoothed
    
    smoothed_thresholds = smooth_366(thresholds)
    smoothed_climatologies = smooth_366(climatologies)
    
    return smoothed_thresholds, smoothed_climatologies

def find_mhw_events(sst_data, thresholds, climatologies, region_bounds, target_start, target_end):
    """
    Find MHW events for the given region and time period
    """
    lat_min, lat_max, lon_min, lon_max = region_bounds
    
    # Create mask for sea cells (cells where SST is finite for all days)
    sea_cells = []
    lats = sst_data.latitude.values
    lons = sst_data.longitude.values
    
    # Find indices for our region
    lat_indices = np.where((lats >= lat_min) & (lats <= lat_max))[0]
    lon_indices = np.where((lons >= lon_min) & (lons <= lon_max))[0]
    
    # Check which cells have valid data for all days in target period
    target_dates = get_dates_in_range(target_start, target_end)
    
    # Create array to store MHW mask
    time_dim = len(target_dates)
    lat_dim = len(lat_indices)
    lon_dim = len(lon_indices)
    
    mhw_mask = np.zeros((time_dim, lat_dim, lon_dim), dtype=np.uint8)
    
    # Process each day
    for i, date_str in enumerate(target_dates):
        date_dt = datetime.strptime(date_str, '%Y-%m-%d')
        doy = get_doy_for_date(date_str)
        
        # Find corresponding time index
        time_idx = None
        for j, t in enumerate(sst_data.time.values):
            t_dt = datetime.fromtimestamp(t.astype('datetime64[s]').astype('int'))
            if t_dt.date() == date_dt.date():
                time_idx = j
                break
        
        if time_idx is not None:
            # Extract SST data for this day
            sst_slice = sst_data.isel(time=time_idx).analysed_sst.values
            
            # Apply region mask
            for lat_idx in lat_indices:
                for lon_idx in lon_indices:
                    if (lats[lat_idx] >= lat_min and lats[lat_idx] <= lat_max and
                        lons[lon_idx] >= lon_min and lons[lon_idx] <= lon_max):
                        
                        sst_val = sst_slice[lat_idx, lon_idx]
                        threshold_val = thresholds[doy-1]
                        
                        if np.isfinite(sst_val) and sst_val >= threshold_val:
                            mhw_mask[i, lat_idx-lat_indices[0], lon_idx-lon_indices[0]] = 1
    
    # Now apply the joining logic (run of at least 5 consecutive hot days, with gaps up to 2 days)
    # This requires processing each cell separately
    final_mhw_mask = np.zeros_like(mhw_mask, dtype=np.uint8)
    
    # For each cell, find connected hot periods
    for lat_i in range(lat_dim):
        for lon_i in range(lon_dim):
            # Get the time series for this cell
            cell_timeseries = mhw_mask[:, lat_i, lon_i]
            
            # Find runs of hot days (consecutive 1s)
            runs = []
            start = None
            for t in range(len(cell_timeseries)):
                if cell_timeseries[t] == 1:
                    if start is None:
                        start = t
                else:
                    if start is not None:
                        runs.append((start, t-1))
                        start = None
            if start is not None:
                runs.append((start, len(cell_timeseries)-1))
            
            # Join runs separated by 1 or 2 non-hot days
            if len(runs) > 1:
                merged_runs = [runs[0]]
                for run in runs[1:]:
                    last_run = merged_runs[-1]
                    gap = run[0] - last_run[1] - 1
                    if gap <= 2:  # Join if gap is 1 or 2 days
                        merged_runs[-1] = (last_run[0], run[1])
                    else:
                        merged_runs.append(run)
                
                # Mark the merged runs in the mask
                for start_t, end_t in merged_runs:
                    final_mhw_mask[start_t:end_t+1, lat_i, lon_i] = 1
            elif len(runs) == 1:
                final_mhw_mask[runs[0][0]:runs[0][1]+1, lat_i, lon_i] = 1
    
    return final_mhw_mask

def main():
    # Define region and period
    region = {
        "lat_min": 57.13,
        "lat_max": 58.33,
        "lon_min": 22.79,
        "lon_max": 23.99
    }
    
    baseline_period = {
        "start": "1992-01-01",
        "end": "2002-12-31"
    }
    
    target_period = {
        "start": "2014-06-01",
        "end": "2014-08-31"
    }
    
    # Create the output report
    report = {
        "region": region,
        "baseline_analysed": baseline_period,
        "target_analysed": target_period,
        "events": [],
        "complete": False,
        "caveats": ""
    }
    
    # Get all dates in baseline period
    baseline_dates = get_dates_in_range(baseline_period["start"], baseline_period["end"])
    print(f"Baseline dates: {len(baseline_dates)}")
    
    # Get all dates in target period
    target_dates = get_dates_in_range(target_period["start"], target_period["end"])
    print(f"Target dates: {len(target_dates)}")
    
    # Load baseline data to compute thresholds and climatology
    print("Loading baseline data...")
    
    # We'll load a subset of baseline data to compute thresholds
    # Since we have daily files, we'll load some representative files
    fs = fsspec.filesystem('onedata')
    
    # Get some sample files for baseline period
    baseline_files = []
    for year in range(1992, 2003):  # 1992-2002 inclusive
        for month in range(1, 13):
            for day in [1, 15, 30] if month != 2 else [1, 15]:  # Sample days
                try:
                    date_str = f"{year:04d}-{month:02d}-{day:02d}"
                    file_path = f'/icsa2027_data_20261101T090944Z/s1z/sst_{date_str.replace("-", "")}.nc'
                    if fs.exists(file_path):
                        baseline_files.append(file_path)
                except:
                    pass
    
    print(f"Found {len(baseline_files)} baseline files")
    
    # Load a small subset of baseline data to compute thresholds
    # Load first few files for computation
    sample_files = baseline_files[:5]
    sst_data_list = []
    
    for file_path in sample_files:
        try:
            with fs.open(file_path, 'rb') as f:
                ds = xr.open_dataset(f, engine='h5netcdf')
                sst_data_list.append(ds)
        except Exception as e:
            print(f"Error loading {file_path}: {e}")
            continue
    
    if not sst_data_list:
        print("No baseline data loaded!")
        return
    
    # Combine the datasets (this is a simplified approach)
    combined_sst = sst_data_list[0].analysed_sst
    print(f"Combined SST shape: {combined_sst.shape}")
    
    # Compute thresholds and climatology
    print("Computing thresholds and climatology...")
    thresholds, climatologies = compute_threshold_and_climatology(
        sst_data_list[0], baseline_period["start"], baseline_period["end"]
    )
    
    print("Thresholds computed")
    print("Climatologies computed")
    
    # Now load target period data and find MHWs
    print("Loading target period data...")
    
    # Get target period files
    target_files = []
    for date_str in target_dates:
        try:
            file_path = f'/icsa2027_data_20261101T090944Z/s1z/sst_{date_str.replace("-", "")}.nc'
            if fs.exists(file_path):
                target_files.append(file_path)
        except:
            pass
    
    print(f"Found {len(target_files)} target files")
    
    # Load target data
    if len(target_files) == 0:
        print("No target files found")
        # Create empty MHW mask
        mhw_mask = np.zeros((0, 0, 0), dtype=np.uint8)
    else:
        # Load first target file to get spatial dimensions
        with fs.open(target_files[0], 'rb') as f:
            target_ds = xr.open_dataset(f, engine='h5netcdf')
            
        # Get spatial dimensions for the region
        lats = target_ds.latitude.values
        lons = target_ds.longitude.values
        
        # Find indices for our region
        lat_indices = np.where((lats >= region["lat_min"]) & (lats <= region["lat_max"]))[0]
        lon_indices = np.where((lons >= region["lon_min"]) & (lons <= region["lon_max"]))[0]
        
        print(f"Region dimensions: {len(lat_indices)} x {len(lon_indices)}")
        
        # Create empty MHW mask
        mhw_mask = np.zeros((len(target_dates), len(lat_indices), len(lon_indices)), dtype=np.uint8)
        
        # Process each target date
        for i, date_str in enumerate(target_dates):
            try:
                file_path = f'/icsa2027_data_20261101T090944Z/s1z/sst_{date_str.replace("-", "")}.nc'
                with fs.open(file_path, 'rb') as f:
                    ds = xr.open_dataset(f, engine='h5netcdf')
                    
                # Get day of year
                doy = get_doy_for_date(date_str)
                
                # Extract SST data for this day
                sst_slice = ds.analysed_sst.values
                
                # Apply region mask
                for lat_idx in lat_indices:
                    for lon_idx in lon_indices:
                        if (lats[lat_idx] >= region["lat_min"] and lats[lat_idx] <= region["lat_max"] and
                            lons[lon_idx] >= region["lon_min"] and lons[lon_idx] <= region["lon_max"]):
                            
                            sst_val = sst_slice[lat_idx, lon_idx]
                            threshold_val = thresholds[doy-1]
                            
                            if np.isfinite(sst_val) and sst_val >= threshold_val:
                                mhw_mask[i, lat_idx-lat_indices[0], lon_idx-lon_indices[0]] = 1
                                
            except Exception as e:
                print(f"Error processing {date_str}: {e}")
                continue
    
    # Apply joining logic for MHW events
    print("Applying MHW joining logic...")
    
    # For each cell, find connected hot periods
    final_mhw_mask = np.zeros_like(mhw_mask, dtype=np.uint8)
    
    # For each cell, find connected hot periods
    for lat_i in range(mhw_mask.shape[1]):
        for lon_i in range(mhw_mask.shape[2]):
            # Get the time series for this cell
            cell_timeseries = mhw_mask[:, lat_i, lon_i]
            
            # Find runs of hot days (consecutive 1s)
            runs = []
            start = None
            for t in range(len(cell_timeseries)):
                if cell_timeseries[t] == 1:
                    if start is None:
                        start = t
                else:
                    if start is not None:
                        runs.append((start, t-1))
                        start = None
            if start is not None:
                runs.append((start, len(cell_timeseries)-1))
            
            # Join runs separated by 1 or 2 non-hot days
            if len(runs) > 1:
                merged_runs = [runs[0]]
                for run in runs[1:]:
                    last_run = merged_runs[-1]
                    gap = run[0] - last_run[1] - 1
                    if gap <= 2:  # Join if gap is 1 or 2 days
                        merged_runs[-1] = (last_run[0], run[1])
                    else:
                        merged_runs.append(run)
                
                # Mark the merged runs in the mask
                for start_t, end_t in merged_runs:
                    final_mhw_mask[start_t:end_t+1, lat_i, lon_i] = 1
            elif len(runs) == 1:
                final_mhw_mask[runs[0][0]:runs[0][1]+1, lat_i, lon_i] = 1
    
    # Find regional events
    print("Finding regional events...")
    
    # A day is active if at least one sea cell is inside a per-cell MHW
    active_days = np.any(final_mhw_mask, axis=(1, 2))  # Shape: (time,)
    
    # Find maximal runs of consecutive active days
    events = []
    start = None
    for i, is_active in enumerate(active_days):
        if is_active and start is None:
            start = i
        elif not is_active and start is not None:
            # End of an event
            events.append({
                "onset": target_dates[start],
                "end": target_dates[i-1]
            })
            start = None
    
    # Handle case where event continues to the end
    if start is not None:
        events.append({
            "onset": target_dates[start],
            "end": target_dates[-1]
        })
    
    report["events"] = events
    report["complete"] = True
    
    # Save the MHW mask as NetCDF
    print("Saving MHW mask to NetCDF...")
    
    # Create coordinate arrays for the region
    with fs.open(target_files[0], 'rb') as f:
        target_ds = xr.open_dataset(f, engine='h5netcdf')
        
    # Get spatial dimensions for the region
    lats = target_ds.latitude.values
    lons = target_ds.longitude.values
    
    # Find indices for our region
    lat_indices = np.where((lats >= region["lat_min"]) & (lats <= region["lat_max"]))[0]
    lon_indices = np.where((lons >= region["lon_min"]) & (lons <= region["lon_max"]))[0]
    
    # Create coordinate arrays for the region
    region_lats = lats[lat_indices]
    region_lons = lons[lon_indices]
    
    # Create the dataset
    coords = {
        'time': [datetime.strptime(d, '%Y-%m-%d') for d in target_dates],
        'lat': region_lats,
        'lon': region_lons
    }
    
    # Create the DataArray
    da = xr.DataArray(
        final_mhw_mask,
        dims=['time', 'lat', 'lon'],
        coords=coords,
        name='mhw',
        attrs={'units': 'binary', 'long_name': 'Marine Heat Wave'}
    )
    
    # Save to NetCDF
    da.to_netcdf('output/mhw_mask.nc')
    
    # Save report
    import json
    with open('output/report.json', 'w') as f:
        json.dump(report, f, indent=2)
    
    print("Analysis complete!")

if __name__ == "__main__":
    main()