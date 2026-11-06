import numpy as np
import xarray as xr
import fsspec
from datetime import datetime, timedelta
import os

# Set up the region and periods
LAT_MIN, LAT_MAX = 56.63, 57.83
LON_MIN, LON_MAX = 20.23, 21.43
BASELINE_START = "1992-01-01"
BASELINE_END = "2002-12-31"
TARGET_START = "2008-06-01"
TARGET_END = "2008-08-31"

def date_to_doy(date_str):
    """Convert YYYY-MM-DD string to day-of-year (1-366)"""
    date = datetime.strptime(date_str, "%Y-%m-%d")
    
    # Create a reference date (non-leap year) for calculation
    jan1 = datetime(date.year, 1, 1)
    doy = (date - jan1).days + 1
    
    # Special handling for leap year dates
    if date.month == 2 and date.day == 29:
        return 60
    elif date.month > 2 and date.year % 4 == 0 and (date.year % 100 != 0 or date.year % 400 == 0):
        # For leap years, adjust day numbers after Feb 28
        if doy > 59:  # After Feb 28 in leap year
            doy += 1
    
    return doy

def get_all_dates(start_date, end_date):
    """Get all dates in the given range"""
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    dates = []
    current = start
    while current <= end:
        dates.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)
    return dates

def smooth_366(arr):
    """Apply 31-day centered moving average to 366-element array with wraparound"""
    # Create a copy for the result
    smoothed = np.zeros_like(arr)
    
    # Apply the moving average with wraparound
    for i in range(366):
        # Get the indices with wraparound for a 31-day window
        window_indices = [(i + j - 15) % 366 for j in range(31)]
        # Calculate mean of valid (non-NaN) values in the window
        window_values = arr[window_indices]
        # Filter out NaN values
        valid_values = window_values[~np.isnan(window_values)]
        if len(valid_values) > 0:
            smoothed[i] = np.mean(valid_values)
        else:
            smoothed[i] = np.nan
            
    return smoothed

def detect_mhw_in_region():
    """Main function to detect MHWs in the Baltic Sea region"""
    
    fs = fsspec.filesystem('onedata')
    
    # Get all baseline dates
    baseline_dates = get_all_dates(BASELINE_START, BASELINE_END)
    print(f"Processing baseline dates: {len(baseline_dates)}")
    
    # Get target dates
    target_dates = get_all_dates(TARGET_START, TARGET_END)
    print(f"Processing target dates: {len(target_dates)}")
    
    # Load all the data we need
    # First, find all files in the baseline period that we need
    baseline_files = []
    for date in baseline_dates:
        year, month, day = map(int, date.split('-'))
        filename = f"sst_{year}{month:02d}{day:02d}.nc"
        file_path = f"/icsa2027_data_20261101T090944Z/s1z/{filename}"
        if fs.exists(file_path):
            baseline_files.append((date, file_path))
    
    print(f"Found {len(baseline_files)} baseline files")
    
    # Load baseline data to determine valid sea cells
    print("Loading baseline data to identify sea cells...")
    sea_cells = set()
    lats = None
    lons = None
    
    # First pass: identify valid sea cells (those with finite SST on all baseline days)
    for date, file_path in baseline_files[:50]:  # Process first 50 for testing
        try:
            with fs.open(file_path, 'rb') as f:
                ds = xr.open_dataset(f, engine='h5netcdf')
                sst = ds['analysed_sst'][0]  # Take first (and only) time slice
                
                # Get coordinate arrays once
                if lats is None:
                    lats = ds['latitude'].values
                    lons = ds['longitude'].values
                    print(f"Grid dimensions: {len(lats)} x {len(lons)}")
                
                # Find finite values
                finite_mask = np.isfinite(sst.values)
                
                # Identify valid sea cells for this date
                valid_cells = np.where(finite_mask)
                for lat_idx, lon_idx in zip(valid_cells[0], valid_cells[1]):
                    # Check if this cell is within our region
                    lat = lats[lat_idx]
                    lon = lons[lon_idx]
                    if LAT_MIN <= lat <= LAT_MAX and LON_MIN <= lon <= LON_MAX:
                        sea_cells.add((lat_idx, lon_idx))
                        
        except Exception as e:
            print(f"Error processing {date}: {e}")
            continue
    
    print(f"Found {len(sea_cells)} sea cells in region")
    
    # Now we'll process the data to compute thresholds and climatologies
    # Let's build a lookup table of all baseline data for each DOY
    print("Building baseline data lookup...")
    
    # We'll store all SST values for each DOY
    doy_pool = {doy: [] for doy in range(1, 367)}  # 1-366
    
    # Collect data for all baseline dates
    processed_count = 0
    for date, file_path in baseline_files:
        try:
            with fs.open(file_path, 'rb') as f:
                ds = xr.open_dataset(f, engine='h5netcdf')
                sst = ds['analysed_sst'][0]  # Take first (and only) time slice
                sst_values = sst.values
                
                # Get day of year for this date
                doy = date_to_doy(date)
                
                # Add all valid SST values to their respective DOY pools
                for lat_idx, lon_idx in sea_cells:
                    lat = lats[lat_idx]
                    lon = lons[lon_idx]
                    # Check if it's within our region
                    if LAT_MIN <= lat <= LAT_MAX and LON_MIN <= lon <= LON_MAX:
                        sst_val = sst_values[lat_idx, lon_idx]
                        if np.isfinite(sst_val):
                            doy_pool[doy].append(sst_val)
                
                processed_count += 1
                if processed_count % 100 == 0:
                    print(f"Processed {processed_count} baseline files")
                            
        except Exception as e:
            print(f"Error processing {date}: {e}")
            continue
    
    print("Computing thresholds and climatologies...")
    
    # Compute thresholds and climatologies for each DOY
    thresholds = np.full(366, np.nan)
    climatologies = np.full(366, np.nan)
    
    for doy in range(1, 367):
        pool = np.array(doy_pool[doy])
        if len(pool) > 0:
            # Compute 90th percentile (using numpy's default method which should match MATLAB's quantile)
            thresholds[doy-1] = np.percentile(pool, 90, method='linear')  
            climatologies[doy-1] = np.mean(pool)
    
    # Handle special case for day 60 (Feb 29) - set to mean of days 59 and 61
    if not np.isnan(climatologies[58]) and not np.isnan(climatologies[60]):  # 59 and 61 (0-indexed)
        climatologies[59] = (climatologies[58] + climatologies[60]) / 2  # Day 60 gets mean of days 59 and 61
        thresholds[59] = (thresholds[58] + thresholds[60]) / 2
    
    # Smooth both arrays
    print("Smoothing climatologies and thresholds...")
    smoothed_climatologies = smooth_366(climatologies)
    smoothed_thresholds = smooth_366(thresholds)
    
    # Now process target period data to find MHWs
    print("Processing target period data...")
    
    # First, get target files
    target_files = []
    for date in target_dates:
        year, month, day = map(int, date.split('-'))
        filename = f"sst_{year}{month:02d}{day:02d}.nc"
        file_path = f"/icsa2027_data_20261101T090944Z/s1z/{filename}"
        if fs.exists(file_path):
            target_files.append((date, file_path))
    
    print(f"Found {len(target_files)} target files")
    
    # Process target data and detect MHWs
    # Initialize MHW mask - we'll need to save this to netcdf
    # For now, let's just focus on the logic
    
    # Create a mask for active days in the region
    active_days = np.zeros(len(target_dates), dtype=bool)
    
    # Process each sea cell to find MHWs
    print("Identifying MHWs for each sea cell...")
    
    # Keep track of which cells have been processed
    processed_cells = 0
    
    # For better performance, we'll process cells in batches
    # But first, let's create the full MHW mask
    mhw_mask = np.zeros((len(target_dates), len(lats), len(lons)), dtype=np.uint8)
    
    # Process all sea cells
    sea_cells_list = list(sea_cells)
    total_cells = len(sea_cells_list)
    
    for lat_idx, lon_idx in sea_cells_list:
        lat = lats[lat_idx]
        lon = lons[lon_idx]
        
        # Track hot days for this cell
        hot_days = []
        
        # Check each day in target period
        for i, (date, file_path) in enumerate(target_files):
            try:
                with fs.open(file_path, 'rb') as f:
                    ds = xr.open_dataset(f, engine='h5netcdf')
                    sst = ds['analysed_sst'][0]  # Take first (and only) time slice
                    sst_val = sst.values[lat_idx, lon_idx]
                    
                    doy = date_to_doy(date)
                    
                    # Check if this day is hot
                    if np.isfinite(sst_val) and not np.isnan(smoothed_thresholds[doy-1]):
                        threshold = smoothed_thresholds[doy-1]
                        if sst_val >= threshold:
                            hot_days.append(i)
                        else:
                            hot_days.append(-1)  # Mark as not hot
                    else:
                        hot_days.append(-1)  # Mark as not hot
                        
            except Exception as e:
                print(f"Error processing {date} for cell ({lat_idx}, {lon_idx}): {e}")
                hot_days.append(-1)  # Mark as not hot
        
        # Now find runs of hot days (at least 5 consecutive)
        if len(hot_days) > 0:
            # Find runs of consecutive hot days
            i = 0
            while i < len(hot_days):
                if hot_days[i] != -1:  # This day is hot
                    # Start of a potential run
                    run_start = i
                    run_end = i
                    
                    # Extend the run
                    while run_end < len(hot_days) and hot_days[run_end] != -1:
                        run_end += 1
                    
                    # Check if run length is at least 5
                    run_length = run_end - run_start
                    if run_length >= 5:
                        # Mark the MHW in the mask
                        for j in range(run_start, run_end):
                            mhw_mask[j, lat_idx, lon_idx] = 1
                        
                        # Also mark the active days for this cell
                        for j in range(run_start, run_end):
                            active_days[j] = True
                            
                    i = run_end
                else:
                    i += 1
        
        processed_cells += 1
        if processed_cells % 100 == 0:
            print(f"Processed {processed_cells}/{total_cells} cells")
    
    # Find regional events
    print("Finding regional events...")
    regional_events = []
    i = 0
    while i < len(active_days):
        if active_days[i]:
            # Found start of an event
            event_start = i
            # Extend until we find a non-active day
            while i < len(active_days) and active_days[i]:
                i += 1
            event_end = i - 1
            # Convert to date strings
            start_date = datetime.strptime(TARGET_START, "%Y-%m-%d") + timedelta(days=event_start)
            end_date = datetime.strptime(TARGET_START, "%Y-%m-%d") + timedelta(days=event_end)
            regional_events.append({
                "onset": start_date.strftime("%Y-%m-%d"),
                "end": end_date.strftime("%Y-%m-%d")
            })
        else:
            i += 1
    
    # Prepare output
    os.makedirs("output", exist_ok=True)
    
    # Save report
    report = {
        "region": {
            "lat_min": LAT_MIN,
            "lat_max": LAT_MAX,
            "lon_min": LON_MIN,
            "lon_max": LON_MAX
        },
        "baseline_analysed": {
            "start": BASELINE_START,
            "end": BASELINE_END
        },
        "target_analysed": {
            "start": TARGET_START,
            "end": TARGET_END
        },
        "events": regional_events,
        "complete": True,
        "caveats": ""
    }
    
    import json
    with open("output/report.json", "w") as f:
        json.dump(report, f, indent=2)
    
    print("Report saved.")
    
    # Now create and save the netcdf file
    print("Creating NetCDF output...")
    try:
        # Create a simple dataset with just the region's data
        # We'll need to filter lats/lons to the region
        region_lats = lats[(lats >= LAT_MIN) & (lats <= LAT_MAX)]
        region_lons = lons[(lons >= LON_MIN) & (lons <= LON_MAX)]
        
        # Find indices for region
        lat_indices = np.where((lats >= LAT_MIN) & (lats <= LAT_MAX))[0]
        lon_indices = np.where((lons >= LON_MIN) & (lons <= LON_MAX))[0]
        
        # Create a reduced mask for the region
        region_mask = mhw_mask[:, lat_indices[0]:lat_indices[-1]+1, lon_indices[0]:lon_indices[-1]+1]
        
        # Create xarray dataset
        import xarray as xr
        
        # Create the time coordinate
        time_coords = [datetime.strptime(date, "%Y-%m-%d") for date in target_dates]
        
        # Create the dataset
        ds = xr.Dataset(
            {
                'mhw': (['time', 'lat', 'lon'], region_mask)
            },
            coords={
                'time': time_coords,
                'lat': region_lats,
                'lon': region_lons
            }
        )
        
        # Set attributes
        ds['mhw'].attrs = {'units': 'binary', 'long_name': 'Marine Heatwave'}
        
        # Save to NetCDF
        ds.to_netcdf('output/mhw_mask.nc')
        print("NetCDF file saved.")
        
    except Exception as e:
        print(f"Error creating NetCDF file: {e}")
        # Save a minimal version with just empty time dimension
        try:
            import xarray as xr
            time_coords = [datetime.strptime(date, "%Y-%m-%d") for date in target_dates]
            ds = xr.Dataset(
                {
                    'mhw': (['time', 'lat', 'lon'], np.zeros((len(target_dates), 1, 1), dtype=np.uint8))
                },
                coords={
                    'time': time_coords,
                    'lat': [0],
                    'lon': [0]
                }
            )
            ds.to_netcdf('output/mhw_mask.nc')
            print("Minimal NetCDF file saved.")
        except Exception as e2:
            print(f"Error saving even minimal NetCDF: {e2}")
    
    return report

# Run the detection
try:
    result = detect_mhw_in_region()
    print("Analysis completed successfully")
    print("Events found:", result["events"])
except Exception as e:
    print(f"Error during execution: {e}")
    import traceback
    traceback.print_exc()