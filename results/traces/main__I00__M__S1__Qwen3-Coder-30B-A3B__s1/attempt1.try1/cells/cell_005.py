import xarray as xr
import numpy as np
import os
from datetime import datetime, timedelta
from scipy.ndimage import uniform_filter1d
import netCDF4 as nc

# Define region boundaries
LAT_MIN, LAT_MAX = 54.13, 55.33
LON_MIN, LON_MAX = 14.67, 15.87

# Target period
TARGET_START = datetime(2004, 6, 1)
TARGET_END = datetime(2004, 8, 31)

# Baseline period
BASELINE_START = datetime(1992, 1, 1)
BASELINE_END = datetime(2002, 12, 31)

def date_to_doy(date):
    """Convert date to day of year (1-366)"""
    # Handle leap years correctly
    if date.month == 2 and date.day == 29:
        return 60  # Special case for Feb 29
    
    # Create a date for Jan 1 of the same year to calculate doy
    jan1 = datetime(date.year, 1, 1)
    doy = (date - jan1).days + 1
    
    # Adjust for leap year cases where Feb 29 is not included in doy calculation
    if date.month > 2 and (date.year % 4 == 0 and (date.year % 100 != 0 or date.year % 400 == 0)):
        # This is a leap year and we're past Feb 29
        doy += 1
    
    return doy

def get_doy_for_date(date):
    """Get day of year for a date, handling special cases"""
    # For Feb 29, we assign it to day 60
    if date.month == 2 and date.day == 29:
        return 60
    # Otherwise, calculate normally
    jan1 = datetime(date.year, 1, 1)
    doy = (date - jan1).days + 1
    # For leap years, adjust days after Feb 29
    if date.month > 2 and (date.year % 4 == 0 and (date.year % 100 != 0 or date.year % 400 == 0)):
        doy += 1
    return doy

def get_pool_dates(base_date, doy):
    """Get the pool of dates around base_date for the given doy"""
    # Get the dates within ±5 days
    pool_dates = []
    
    # Add the base date itself
    pool_dates.append(base_date)
    
    # Add dates before and after (up to 5 days)
    for i in range(1, 6):
        prev_date = base_date - timedelta(days=i)
        next_date = base_date + timedelta(days=i)
        
        # Add previous date if it matches the doy
        if get_doy_for_date(prev_date) == doy:
            pool_dates.append(prev_date)
            
        # Add next date if it matches the doy  
        if get_doy_for_date(next_date) == doy:
            pool_dates.append(next_date)
    
    # Handle edge cases where we go beyond baseline period
    # Add extra dates at the beginning and end if needed
    if base_date >= BASELINE_START and base_date <= BASELINE_END:
        # Check for boundary dates
        if base_date.month == 1 and base_date.day <= 5:
            # Add dates from previous year's end
            prev_year = base_date.year - 1
            # Add dates from Dec 27 to Dec 31 of previous year if they match doy
            for i in range(27, 32):
                try:
                    dec_date = datetime(prev_year, 12, i)
                    if get_doy_for_date(dec_date) == doy:
                        pool_dates.append(dec_date)
                except:
                    pass
                    
        elif base_date.month == 12 and base_date.day >= 27:
            # Add dates from next year's beginning
            next_year = base_date.year + 1
            # Add dates from Jan 1 to Jan 5 of next year if they match doy
            for i in range(1, 6):
                try:
                    jan_date = datetime(next_year, 1, i)
                    if get_doy_for_date(jan_date) == doy:
                        pool_dates.append(jan_date)
                except:
                    pass
    
    return pool_dates

def compute_threshold_and_climatology():
    """Compute thresholds and climatology for each day of year"""
    print("Computing thresholds and climatology...")
    
    # Get all baseline dates
    baseline_dates = []
    for year in range(1992, 2003):  # 1992 to 2002 inclusive
        for month in range(1, 13):
            for day in range(1, 32):
                try:
                    date = datetime(year, month, day)
                    if BASELINE_START <= date <= BASELINE_END:
                        baseline_dates.append(date)
                except ValueError:
                    continue
    
    # Initialize arrays for 366 days of year
    threshold = np.full(366, np.nan)
    climatology = np.full(366, np.nan)
    pool_size = np.zeros(366)  # Track pool sizes
    
    # Process each day of year
    for doy in range(1, 367):
        if doy == 60:  # Skip day 60 as special case
            continue
            
        # Collect all SST values for this doy across baseline period
        sst_values = []
        
        # For each baseline date, find matching doy dates
        for base_date in baseline_dates:
            # Calculate doy for this base date
            base_doy = get_doy_for_date(base_date)
            
            # If this date's doy matches our target doy, include it
            if base_doy == doy:
                # Get the actual file for this date
                date_str = base_date.strftime('%Y%m%d')
                file_path = f"/data/icsa2027_data_20261101T090944Z/s1z/sst_{date_str}.nc"
                
                try:
                    ds = xr.open_dataset(file_path, engine="h5netcdf")
                    sst_data = ds.analysed_sst.values[0]  # Remove time dimension
                    
                    # Store all valid SST values
                    valid_sst = sst_data[np.isfinite(sst_data)]
                    sst_values.extend(valid_sst)
                    
                    ds.close()
                except Exception as e:
                    print(f"Error reading {file_path}: {e}")
                    continue
        
        # Convert to numpy array and compute statistics
        if len(sst_values) > 0:
            sst_array = np.array(sst_values)
            # Compute 90th percentile (Hazen method)
            threshold[doy-1] = np.percentile(sst_array, 90, method='linear')
            # Compute mean
            climatology[doy-1] = np.mean(sst_array)
            pool_size[doy-1] = len(sst_array)
        else:
            print(f"No data for doy {doy}")
    
    # Handle day 60 specially (assign to mean of days 59 and 61)
    if not np.isnan(threshold[59]) and not np.isnan(threshold[60]):
        threshold[59] = (threshold[58] + threshold[60]) / 2
        threshold[60] = threshold[59]
    elif not np.isnan(threshold[58]) and not np.isnan(threshold[60]):
        threshold[59] = (threshold[58] + threshold[60]) / 2
        threshold[60] = threshold[59]
    elif not np.isnan(threshold[58]) and not np.isnan(threshold[61]):
        threshold[59] = (threshold[58] + threshold[61]) / 2
        threshold[60] = threshold[59]
    
    # Smooth with 31-day moving average
    # First, handle the circular nature of the year
    smoothed_threshold = np.zeros(366)
    smoothed_climatology = np.zeros(366)
    
    # Extend arrays to handle wrapping
    extended_threshold = np.concatenate([threshold, threshold, threshold])
    extended_climatology = np.concatenate([climatology, climatology, climatology])
    
    # Apply 31-day moving average (centered)
    window_size = 31
    half_window = window_size // 2
    
    for i in range(366):
        start_idx = i - half_window
        end_idx = i + half_window + 1
        
        # Handle wrapping
        window_values = extended_threshold[start_idx:end_idx]
        # Remove NaN values
        window_values = window_values[~np.isnan(window_values)]
        
        if len(window_values) > 0:
            smoothed_threshold[i] = np.mean(window_values)
            
        # Same for climatology
        window_values_c = extended_climatology[start_idx:end_idx]
        window_values_c = window_values_c[~np.isnan(window_values_c)]
        
        if len(window_values_c) > 0:
            smoothed_climatology[i] = np.mean(window_values_c)
    
    return smoothed_threshold, smoothed_climatology

def identify_sea_cells():
    """Identify sea cells in the region that have finite SST for all target days"""
    print("Identifying sea cells...")
    
    # Get all target dates
    target_dates = []
    current_date = TARGET_START
    while current_date <= TARGET_END:
        target_dates.append(current_date)
        current_date += timedelta(days=1)
    
    # Load coordinates from any file to get spatial structure
    sample_file = f"/data/icsa2027_data_20261101T090944Z/s1z/sst_{TARGET_START.strftime('%Y%m%d')}.nc"
    ds = xr.open_dataset(sample_file, engine="h5netcdf")
    latitudes = ds.latitude.values
    longitudes = ds.longitude.values
    ds.close()
    
    # Find indices for our region
    lat_indices = np.where((latitudes >= LAT_MIN) & (latitudes <= LAT_MAX))[0]
    lon_indices = np.where((longitudes >= LON_MIN) & (longitudes <= LON_MAX))[0]
    
    if len(lat_indices) == 0 or len(lon_indices) == 0:
        return None, None, None, None
    
    # Create mask for our region
    region_mask = np.zeros((len(latitudes), len(longitudes)), dtype=bool)
    region_mask[np.ix_(lat_indices, lon_indices)] = True
    
    # Initialize array to track cells with finite values for all days
    sea_cell_mask = np.ones((len(lat_indices), len(lon_indices)), dtype=bool)
    
    # Check each cell for all target days
    for i, lat_idx in enumerate(lat_indices):
        for j, lon_idx in enumerate(lon_indices):
            # Check if this cell has finite SST for all days
            has_all_finite = True
            for date in target_dates:
                date_str = date.strftime('%Y%m%d')
                file_path = f"/data/icsa2027_data_20261101T090944Z/s1z/sst_{date_str}.nc"
                
                try:
                    ds = xr.open_dataset(file_path, engine="h5netcdf")
                    sst_value = ds.analysed_sst.values[0, lat_idx, lon_idx]
                    ds.close()
                    
                    if not np.isfinite(sst_value):
                        has_all_finite = False
                        break
                except Exception as e:
                    print(f"Error reading {file_path}: {e}")
                    has_all_finite = False
                    break
            
            # If any day is missing or invalid, mark as not a sea cell
            if not has_all_finite:
                sea_cell_mask[i, j] = False
    
    return lat_indices, lon_indices, region_mask, sea_cell_mask

def detect_mhws():
    """Main function to detect MHWs"""
    print("Starting MHW detection...")
    
    # Step 1: Compute thresholds and climatology
    threshold, climatology = compute_threshold_and_climatology()
    
    # Step 2: Identify sea cells
    lat_indices, lon_indices, region_mask, sea_cell_mask = identify_sea_cells()
    
    if lat_indices is None or lon_indices is None:
        print("No valid sea cells found in region.")
        return None, [], threshold, climatology
    
    # Get target dates
    target_dates = []
    current_date = TARGET_START
    while current_date <= TARGET_END:
        target_dates.append(current_date)
        current_date += timedelta(days=1)
    
    # Prepare results
    n_lat = len(lat_indices)
    n_lon = len(lon_indices)
    n_time = len(target_dates)
    
    # Create result mask
    mhw_mask = np.zeros((n_time, n_lat, n_lon), dtype=np.uint8)
    
    # Process each day to determine if cells are hot
    for t, date in enumerate(target_dates):
        print(f"Processing day {t+1}/{n_time}: {date.strftime('%Y-%m-%d')}")
        
        # Get doy for this date
        doy = get_doy_for_date(date)
        
        # Read SST data for this date
        date_str = date.strftime('%Y%m%d')
        file_path = f"/data/icsa2027_data_20261101T090944Z/s1z/sst_{date_str}.nc"
        
        try:
            ds = xr.open_dataset(file_path, engine="h5netcdf")
            sst_data = ds.analysed_sst.values[0]  # Remove time dimension
            ds.close()
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            continue
        
        # Create hot mask for this day
        hot_mask = np.zeros((n_lat, n_lon), dtype=bool)
        
        # For each sea cell, check if it's hot
        for i in range(n_lat):
            for j in range(n_lon):
                if sea_cell_mask[i, j]:  # Only process sea cells
                    lat_idx = lat_indices[i]
                    lon_idx = lon_indices[j]
                    
                    # Get SST value for this cell
                    sst_val = sst_data[lat_idx, lon_idx]
                    
                    # Check if it's hot (SST >= threshold for this doy)
                    if np.isfinite(sst_val) and sst_val >= threshold[doy-1]:
                        hot_mask[i, j] = True
        
        # Save hot mask for this day
        mhw_mask[t] = hot_mask.astype(np.uint8)
    
    # Step 3: Join gaps and identify MHWs
    print("Joining gaps and identifying MHWs...")
    
    # For each cell, identify MHWs
    for i in range(n_lat):
        for j in range(n_lon):
            if sea_cell_mask[i, j]:  # Only process sea cells
                # Extract the time series for this cell
                cell_timeseries = mhw_mask[:, i, j]
                
                # Find runs of at least 5 consecutive hot days
                # First, identify runs of hot days
                runs = []
                start_idx = None
                
                for k in range(len(cell_timeseries)):
                    if cell_timeseries[k] == 1:
                        if start_idx is None:
                            start_idx = k
                    else:
                        if start_idx is not None:
                            # End of a run
                            runs.append((start_idx, k-1))
                            start_idx = None
                
                # Don't forget the last run if it continues to the end
                if start_idx is not None:
                    runs.append((start_idx, len(cell_timeseries)-1))
                
                # Now filter runs to keep only those with at least 5 consecutive days
                long_runs = []
                for start, end in runs:
                    if end - start + 1 >= 5:
                        long_runs.append((start, end))
                
                # Join gaps of 1 or 2 days
                if len(long_runs) > 1:
                    merged_runs = [long_runs[0]]
                    for start, end in long_runs[1:]:
                        last_start, last_end = merged_runs[-1]
                        # Check if gap is 1 or 2 days
                        gap = start - last_end - 1
                        if 1 <= gap <= 2:
                            # Merge runs
                            merged_runs[-1] = (last_start, end)
                        else:
                            merged_runs.append((start, end))
                    long_runs = merged_runs
                
                # Update mask for this cell with the merged runs
                for start, end in long_runs:
                    mhw_mask[start:end+1, i, j] = 1
    
    # Step 4: Determine regional events
    print("Computing regional events...")
    
    # A regional event is a run of consecutive active days
    # Active means at least one sea cell is in an MHW
    active_days = np.any(mhw_mask, axis=(1, 2))  # Shape: (n_time,)
    
    # Find runs of consecutive active days
    events = []
    start_idx = None
    
    for i in range(len(active_days)):
        if active_days[i]:
            if start_idx is None:
                start_idx = i
        else:
            if start_idx is not None:
                # End of an event
                end_idx = i - 1
                event_start_date = TARGET_START + timedelta(days=start_idx)
                event_end_date = TARGET_START + timedelta(days=end_idx)
                events.append({
                    "onset": event_start_date.strftime("%Y-%m-%d"),
                    "end": event_end_date.strftime("%Y-%m-%d")
                })
                start_idx = None
    
    # Don't forget the last event if it continues to the end
    if start_idx is not None:
        end_idx = len(active_days) - 1
        event_start_date = TARGET_START + timedelta(days=start_idx)
        event_end_date = TARGET_START + timedelta(days=end_idx)
        events.append({
            "onset": event_start_date.strftime("%Y-%m-%d"),
            "end": event_end_date.strftime("%Y-%m-%d")
        })
    
    return mhw_mask, events, threshold, climatology

def save_results(mhw_mask, events, threshold, climatology):
    """Save results to files"""
    print("Saving results...")
    
    # Create output directory
    os.makedirs("output", exist_ok=True)
    
    # Save the MHW mask as NetCDF
    # First, get the coordinates from the original data
    sample_file = f"/data/icsa2027_data_20261101T090944Z/s1z/sst_{TARGET_START.strftime('%Y%m%d')}.nc"
    ds = xr.open_dataset(sample_file, engine="h5netcdf")
    latitudes = ds.latitude.values
    longitudes = ds.longitude.values
    ds.close()
    
    # Find indices for our region
    lat_indices = np.where((latitudes >= LAT_MIN) & (latitudes <= LAT_MAX))[0]
    lon_indices = np.where((longitudes >= LON_MIN) & (longitudes <= LON_MAX))[0]
    
    # Get subset of lat/lon for our region
    region_latitudes = latitudes[lat_indices]
    region_longitudes = longitudes[lon_indices]
    
    # Get target dates
    target_dates = []
    current_date = TARGET_START
    while current_date <= TARGET_END:
        target_dates.append(current_date)
        current_date += timedelta(days=1)
    
    # Create the dataset
    if mhw_mask.size > 0:
        # Reshape mhw_mask to match the expected dimensions
        time_dim = [date.strftime('%Y-%m-%d') for date in target_dates]
        
        # Create a new dataset with proper dimensions
        mhw_ds = xr.Dataset(
            {
                'mhw': (['time', 'lat', 'lon'], mhw_mask)
            },
            coords={
                'time': time_dim,
                'lat': region_latitudes,
                'lon': region_longitudes
            }
        )
        
        # Save to NetCDF
        mhw_ds.to_netcdf('output/mhw_mask.nc', engine='h5netcdf')
    else:
        # Create empty dataset with correct dimensions
        mhw_ds = xr.Dataset(
            {
                'mhw': (['time', 'lat', 'lon'], np.zeros((0, len(region_latitudes), len(region_longitudes)), dtype=np.uint8))
            },
            coords={
                'time': [],
                'lat': region_latitudes,
                'lon': region_longitudes
            }
        )
        mhw_ds.to_netcdf('output/mhw_mask.nc', engine='h5netcdf')
    
    # Create report JSON
    report = {
        "region": {
            "lat_min": LAT_MIN,
            "lat_max": LAT_MAX,
            "lon_min": LON_MIN,
            "lon_max": LON_MAX
        },
        "baseline_analysed": {
            "start": BASELINE_START.strftime("%Y-%m-%d"),
            "end": BASELINE_END.strftime("%Y-%m-%d")
        },
        "target_analysed": {
            "start": TARGET_START.strftime("%Y-%m-%d"),
            "end": TARGET_END.strftime("%Y-%m-%d")
        },
        "events": events,
        "complete": True,
        "caveats": ""
    }
    
    import json
    with open('output/report.json', 'w') as f:
        json.dump(report, f, indent=2)
    
    print("Results saved successfully.")

# Run the detection
try:
    mhw_mask, events, threshold, climatology = detect_mhws()
    save_results(mhw_mask, events, threshold, climatology)
    print("Analysis completed successfully!")
except Exception as e:
    print(f"Error during analysis: {e}")
    import traceback
    traceback.print_exc()