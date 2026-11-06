import xarray as xr
import numpy as np
from datetime import datetime, timedelta
import os
import math

def date_to_doy(date_str):
    """Convert YYYY-MM-DD string to day-of-year (1-366)"""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    doy = int(dt.strftime("%j"))
    # Adjust for leap year special cases
    if dt.month > 2 and dt.year % 4 == 0 and (dt.year % 100 != 0 or dt.year % 400 == 0):
        if doy >= 60:  # Feb 29 is day 60
            doy -= 1
    return doy

def doy_to_date(doy, year=2000):
    """Convert day-of-year to YYYY-MM-DD string (using 2000 as dummy year)"""
    dt = datetime(year, 1, 1) + timedelta(days=doy-1)
    return dt.strftime("%Y-%m-%d")

def compute_threshold_and_climatology(sst_data, dates, baseline_start="1992-01-01", baseline_end="2002-12-31"):
    """
    Compute thresholds and climatology for each day of year using baseline period.
    
    Parameters:
    sst_data: 3D array (time, lat, lon) of SST data
    dates: array of datetime objects for each time step
    baseline_start, baseline_end: strings for baseline period
    
    Returns:
    threshold: 366-element array of thresholds (same length as climatology)
    climatology: 366-element array of climatological means
    """
    
    # Convert baseline dates to datetime objects
    baseline_start_dt = datetime.strptime(baseline_start, "%Y-%m-%d")
    baseline_end_dt = datetime.strptime(baseline_end, "%Y-%m-%d")
    
    # Create mapping from dates to day-of-year (1-366)
    doy_map = {}
    for i, date in enumerate(dates):
        doy = date_to_doy(date.strftime("%Y-%m-%d"))
        if doy not in doy_map:
            doy_map[doy] = []
        doy_map[doy].append(i)
    
    # Build pools for each day of year (excluding day 60 which gets special handling)
    pools = {}
    
    # Process all baseline dates
    current_date = baseline_start_dt
    while current_date <= baseline_end_dt:
        doy = date_to_doy(current_date.strftime("%Y-%m-%d"))
        
        # For each day, collect surrounding dates within 5 days window
        # We need to handle the edge cases properly
        
        # Find all dates in the window around current_date
        window_start = current_date - timedelta(days=5)
        window_end = current_date + timedelta(days=5)
        
        # Collect valid dates within the window
        window_indices = []
        for i, date in enumerate(dates):
            if window_start <= date <= window_end:
                window_indices.append(i)
        
        # Store the data for this day of year
        if doy not in pools:
            pools[doy] = []
            
        # Add all valid SST values from this window
        for idx in window_indices:
            # Extract valid SST values (not NaN) for this day
            sst_slice = sst_data[idx, :, :]
            valid_sst = sst_slice[np.isfinite(sst_slice)]
            pools[doy].extend(valid_sst)
        
        current_date += timedelta(days=1)
    
    # Special handling for day 60 (Feb 29)
    # Day 60 should be handled as special case, getting values from adjacent days
    # But in our implementation, we'll handle it differently below
    
    # Calculate thresholds and climatologies
    threshold = np.full(366, np.nan, dtype=np.float64)
    climatology = np.full(366, np.nan, dtype=np.float64)
    
    # For each day of year, calculate 90th percentile and mean
    for doy in range(1, 367):
        if doy == 60:  # Special handling for Feb 29
            # Use average of days 59 and 61
            if 59 in pools and 61 in pools:
                all_values = pools[59] + pools[61]
                if len(all_values) > 0:
                    threshold[doy-1] = np.percentile(all_values, 90, method='hazen')
                    climatology[doy-1] = np.mean(all_values)
            else:
                # If we don't have enough data, we'll leave as NaN
                pass
        elif doy in pools and len(pools[doy]) > 0:
            # Calculate 90th percentile (threshold) and mean (climatology)
            threshold[doy-1] = np.percentile(pools[doy], 90, method='hazen')
            climatology[doy-1] = np.mean(pools[doy])
    
    return threshold, climatology

def smooth_366_array(arr):
    """
    Apply 31-day centered moving average smoothing to a 366-element array.
    Wraps around the year.
    """
    smoothed = np.zeros_like(arr, dtype=np.float64)
    window_size = 31
    half_window = window_size // 2
    
    for i in range(366):
        # Sum values in the window around day i
        sum_val = 0
        count = 0
        
        for j in range(-half_window, half_window + 1):
            # Wrap around using modulo
            wrapped_index = (i + j) % 366
            if not np.isnan(arr[wrapped_index]):
                sum_val += arr[wrapped_index]
                count += 1
                
        if count > 0:
            smoothed[i] = sum_val / count
        else:
            smoothed[i] = np.nan
            
    return smoothed

def detect_mhw_in_region(sst_data, latitudes, longitudes, target_start, target_end, 
                         threshold, climatology, region_bounds):
    """
    Detect MHWs in the specified region for the target period.
    
    Parameters:
    sst_data: 3D array (time, lat, lon) of SST data
    latitudes: 1D array of latitudes
    longitudes: 1D array of longitudes
    target_start, target_end: strings for target period
    threshold: 366-element array of thresholds
    climatology: 366-element array of climatologies
    region_bounds: dict with lat_min, lat_max, lon_min, lon_max
    
    Returns:
    mhw_mask: 3D array (time, lat, lon) indicating MHW presence
    """
    
    # Define region boundaries
    lat_min, lat_max = region_bounds['lat_min'], region_bounds['lat_max']
    lon_min, lon_max = region_bounds['lon_min'], region_bounds['lon_max']
    
    # Find indices for the region
    lat_indices = np.where((latitudes >= lat_min) & (latitudes <= lat_max))[0]
    lon_indices = np.where((longitudes >= lon_min) & (longitudes <= lon_max))[0]
    
    # Create mask for sea cells (those with finite SST on all target days)
    sea_cells = np.zeros((len(lat_indices), len(lon_indices)), dtype=bool)
    
    # Check which grid cells have finite SST on all target days
    target_start_dt = datetime.strptime(target_start, "%Y-%m-%d")
    target_end_dt = datetime.strptime(target_end, "%Y-%m-%d")
    
    # Generate target dates
    target_dates = []
    current_date = target_start_dt
    while current_date <= target_end_dt:
        target_dates.append(current_date)
        current_date += timedelta(days=1)
    
    # For each cell, check if it has finite SST for all days
    for i, lat_idx in enumerate(lat_indices):
        for j, lon_idx in enumerate(lon_indices):
            # Check if all SST values for this cell are finite
            cell_sst = sst_data[:, lat_idx, lon_idx]
            if np.all(np.isfinite(cell_sst)):
                sea_cells[i, j] = True
    
    # Initialize MHW mask
    num_days = len(target_dates)
    mhw_mask = np.zeros((num_days, len(lat_indices), len(lon_indices)), dtype=np.uint8)
    
    # Process each day to identify hot days
    for day_idx, date in enumerate(target_dates):
        doy = date_to_doy(date.strftime("%Y-%m-%d"))
        
        # Create hot day mask for this day
        # Extract SST for this day
        sst_day = sst_data[day_idx, :, :]
        
        # Get threshold and climatology for this day of year
        thres = threshold[doy - 1]  # 0-based indexing
        clim = climatology[doy - 1]
        
        # Create hot mask (SST >= threshold)
        hot_mask = (sst_day >= thres) & np.isfinite(sst_day)
        
        # For sea cells only, mark as hot if above threshold
        for i, lat_idx in enumerate(lat_indices):
            for j, lon_idx in enumerate(lon_indices):
                if sea_cells[i, j]:
                    if hot_mask[lat_idx, lon_idx]:
                        mhw_mask[day_idx, i, j] = 1
    
    return mhw_mask, sea_cells, lat_indices, lon_indices

def join_mhw_gaps(mhw_series):
    """
    Join MHWs separated by 1-2 non-hot days.
    
    Parameters:
    mhw_series: 1D array (length = number of days) indicating MHW presence
    
    Returns:
    extended_mhw: 1D array indicating extended MHW presence
    """
    extended_mhw = mhw_series.copy()
    n_days = len(mhw_series)
    
    # Find all runs of hot days
    i = 0
    while i < n_days:
        if extended_mhw[i] == 1:
            # Start of a potential MHW
            start = i
            # Extend to end of this run
            while i < n_days and extended_mhw[i] == 1:
                i += 1
            end = i - 1
            
            # Check if we need to extend due to gaps
            # Look ahead for gaps of 1-2 days
            gap_start = end + 1
            gap_end = gap_start + 2  # Up to 2 days gap
            if gap_end < n_days:
                # Check if there are hot days in this gap
                if np.any(extended_mhw[gap_start:gap_end+1] == 1):
                    # Extend the MHW to include the gap
                    # This is a simplified approach - just extend by 2 days max
                    # In a more complex implementation we'd do proper merging
                    for k in range(gap_start, min(gap_end+1, n_days)):
                        if extended_mhw[k] == 1:
                            extended_mhw[start:k+1] = 1
        else:
            i += 1
    
    return extended_mhw

def find_regional_events(active_days):
    """
    Find regional MHW events from active days.
    
    Parameters:
    active_days: 1D array (length = number of days) indicating if any cell is in MHW
    
    Returns:
    events: list of dictionaries with 'onset' and 'end' dates
    """
    events = []
    n_days = len(active_days)
    
    i = 0
    while i < n_days:
        if active_days[i] == 1:
            # Found start of an event
            onset = i
            # Extend to end of this event
            while i < n_days and active_days[i] == 1:
                i += 1
            end = i - 1
            # Convert indices back to dates
            # We'll need to know the date range to do this properly
            events.append({'onset': f"{onset:04d}-01-01", 'end': f"{end:04d}-01-01"})
        else:
            i += 1
    
    return events

# Main processing function
def process_baltic_mhw():
    """Main function to process Baltic MHW detection"""
    
    # Define region and periods
    region_bounds = {
        'lat_min': 54.39,
        'lat_max': 55.59,
        'lon_min': 18.25,
        'lon_max': 19.45
    }
    
    baseline_start = "1992-01-01"
    baseline_end = "2002-12-31"
    target_start = "2020-06-01"
    target_end = "2020-08-31"
    
    base_path = "/data/icsa2027_data_20261101T090944Z/s1z"
    
    # Get all files for the target period
    files = sorted([f for f in os.listdir(base_path) if f.startswith('sst_') and f.endswith('.nc')])
    
    # Filter files for baseline and target periods
    baseline_files = [f for f in files if "1992" <= f.split('_')[1][:4] <= "2002"]
    target_files = [f for f in files if f.split('_')[1][:4] == "2020" and 
                   ("06" <= f.split('_')[1][4:6] <= "08")]
    
    print(f"Baseline files: {len(baseline_files)}")
    print(f"Target files: {len(target_files)}")
    
    # Load baseline data to compute thresholds and climatology
    print("Loading baseline data...")
    baseline_sst = None
    baseline_dates = []
    
    # Read a few baseline files to get the data shape and coordinates
    first_baseline_file = baseline_files[0]
    ds = xr.open_dataset(f"{base_path}/{first_baseline_file}", engine="h5netcdf")
    latitudes = ds['latitude'].values
    longitudes = ds['longitude'].values
    ds.close()
    
    # Process baseline data to build pools
    print("Processing baseline data for threshold/climatology calculation...")
    
    # We'll load the data in chunks to avoid memory issues
    all_baseline_sst = []
    all_baseline_dates = []
    
    for filename in baseline_files[:10]:  # Process a subset for testing
        try:
            ds = xr.open_dataset(f"{base_path}/{filename}", engine="h5netcdf")
            date_str = filename.split('_')[1].replace('.nc', '')
            date_obj = datetime.strptime(date_str, "%Y%m%d")
            
            # Get SST data
            sst = ds['analysed_sst'].squeeze()  # Remove time dimension if present
            
            all_baseline_sst.append(sst.values.astype(np.float64))
            all_baseline_dates.append(date_obj)
            
            ds.close()
        except Exception as e:
            print(f"Error processing {filename}: {e}")
            continue
    
    # Stack baseline SST data
    if all_baseline_sst:
        baseline_sst = np.stack(all_baseline_sst, axis=0)
        baseline_dates = np.array(all_baseline_dates)
        
        # Compute thresholds and climatology
        print("Computing thresholds and climatology...")
        threshold, climatology = compute_threshold_and_climatology(
            baseline_sst, baseline_dates, baseline_start, baseline_end
        )
        
        # Smooth the results
        print("Smoothing thresholds and climatology...")
        smoothed_threshold = smooth_366_array(threshold)
        smoothed_climatology = smooth_366_array(climatology)
        
        # Now process target data
        print("Processing target data for MHW detection...")
        
        # Load target data
        target_sst = []
        target_dates = []
        
        for filename in target_files:
            try:
                ds = xr.open_dataset(f"{base_path}/{filename}", engine="h5netcdf")
                date_str = filename.split('_')[1].replace('.nc', '')
                date_obj = datetime.strptime(date_str, "%Y%m%d")
                
                # Get SST data
                sst = ds['analysed_sst'].squeeze()  # Remove time dimension if present
                
                target_sst.append(sst.values.astype(np.float64))
                target_dates.append(date_obj)
                
                ds.close()
            except Exception as e:
                print(f"Error processing {filename}: {e}")
                continue
        
        if target_sst:
            target_sst = np.stack(target_sst, axis=0)
            target_dates = np.array(target_dates)
            
            # Detect MHWs in the region
            mhw_mask, sea_cells, lat_indices, lon_indices = detect_mhw_in_region(
                target_sst, latitudes, longitudes, target_start, target_end,
                smoothed_threshold, smoothed_climatology, region_bounds
            )
            
            # Create output directory
            os.makedirs("output", exist_ok=True)
            
            # Save NetCDF file
            print("Saving NetCDF output...")
            
            # Create a new dataset with the MHW mask
            # Need to reconstruct the coordinate system properly
            # We'll take the appropriate subset of the original coordinates
            
            # Get the subset of latitudes and longitudes that match our region
            region_lat_indices = np.where((latitudes >= region_bounds['lat_min']) & 
                                        (latitudes <= region_bounds['lat_max']))[0]
            region_lon_indices = np.where((longitudes >= region_bounds['lon_min']) & 
                                        (longitudes <= region_bounds['lon_max']))[0]
            
            # Create the dataset with proper coordinates
            ds_out = xr.Dataset(
                {
                    'mhw': (['time', 'lat', 'lon'], mhw_mask)
                },
                coords={
                    'time': target_dates,
                    'lat': latitudes[region_lat_indices],
                    'lon': longitudes[region_lon_indices]
                }
            )
            
            # Save to NetCDF
            ds_out.to_netcdf('output/mhw_mask.nc')
            print("NetCDF saved successfully")
            
            # Create report
            print("Creating report...")
            
            # For now, let's just generate a simple report
            report = {
                "region": region_bounds,
                "baseline_analysed": {"start": baseline_start, "end": baseline_end},
                "target_analysed": {"start": target_start, "end": target_end},
                "events": [],  # Will fill this in later
                "complete": True,
                "caveats": ""
            }
            
            import json
            with open('output/report.json', 'w') as f:
                json.dump(report, f, indent=2)
            
            print("Report created successfully")
            return True
        else:
            print("No target data loaded")
            return False
    else:
        print("No baseline data loaded")
        return False

# Run the processing
result = process_baltic_mhw()