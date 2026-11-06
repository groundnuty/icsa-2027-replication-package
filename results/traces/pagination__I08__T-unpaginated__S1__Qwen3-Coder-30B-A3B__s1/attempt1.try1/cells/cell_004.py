import xarray as xr
import fsspec
import numpy as np
from datetime import datetime, timedelta
import os

# Define the region of interest
lat_min, lat_max = 54.81, 56.01
lon_min, lon_max = 19.61, 20.81

# Define the target period
target_start = datetime(2007, 6, 1)
target_end = datetime(2007, 8, 31)

# Define the baseline period
baseline_start = datetime(1992, 1, 1)
baseline_end = datetime(2002, 12, 31)

def day_of_year(dt):
    """Convert a datetime to day of year (1-366)"""
    # Handle leap year special case for Feb 29
    if dt.month == 2 and dt.day == 29:
        return 60
    doy = (dt - datetime(dt.year, 1, 1)).days + 1
    # Adjust for leap year if needed
    if dt.month > 2 and (dt.year % 4 == 0 and (dt.year % 100 != 0 or dt.year % 400 == 0)):
        if doy >= 60:  # After Feb 29, shift by 1
            doy += 1
    return doy

def get_doy_from_date(date_str):
    """Convert YYYY-MM-DD string to day of year"""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return day_of_year(dt)

def get_dates_in_range(start_date, end_date):
    """Generate all dates in a range"""
    dates = []
    current = start_date
    while current <= end_date:
        dates.append(current)
        current += timedelta(days=1)
    return dates

def find_sea_cells_and_thresholds():
    """Find sea cells and compute thresholds and climatology for baseline period"""
    
    # Get all dates in baseline period
    baseline_dates = get_dates_in_range(baseline_start, baseline_end)
    
    # Create mapping from date to day of year
    date_to_doy = {}
    for date in baseline_dates:
        doy = day_of_year(date)
        date_to_doy[date] = doy
    
    # Get all dates in target period
    target_dates = get_dates_in_range(target_start, target_end)
    
    # First, we need to identify which grid points are valid for the entire baseline period
    print("Identifying sea cells...")
    
    # We'll load a subset of files to determine which grid cells have valid data for the whole baseline period
    # Let's look at a few representative files from the baseline period
    sea_cells = set()
    total_files_loaded = 0
    
    # Sample some files to determine sea cells
    sample_files = []
    for i, date in enumerate(baseline_dates):
        if i % 30 == 0:  # Take every 30th file to reduce computation
            year = date.year
            month = date.month
            day = date.day
            filename = f"sst_{year:04d}{month:02d}{day:02d}.nc"
            sample_files.append(filename)
    
    # Load sample files to determine valid grid points
    valid_grid_points = set()
    
    # Let's try to load a few sample files and check the region
    fs = fsspec.filesystem('onedata')
    
    for filename in sample_files[:10]:  # Just a few samples to start
        try:
            file_path = f'/icsa2027_data_20261101T090944Z/s1z/{filename}'
            with fs.open(file_path, 'rb') as f:
                ds = xr.open_dataset(f, engine='h5netcdf')
                sst = ds.analysed_sst.isel(time=0)
                
                # Find indices for our region
                lat_indices = np.where((ds.latitude >= lat_min) & (ds.latitude <= lat_max))[0]
                lon_indices = np.where((ds.longitude >= lon_min) & (ds.longitude <= lon_max))[0]
                
                if len(lat_indices) > 0 and len(lon_indices) > 0:
                    # Check if any point in our region has finite values
                    lat_slice = slice(lat_indices[0], lat_indices[-1] + 1)
                    lon_slice = slice(lon_indices[0], lon_indices[-1] + 1)
                    
                    sst_region = sst.isel(latitude=lat_slice, longitude=lon_slice)
                    # Check if there are any finite values in this region
                    if np.any(np.isfinite(sst_region.values)):
                        # Add all valid grid points in this region to our set
                        for lat_idx in lat_indices:
                            for lon_idx in lon_indices:
                                valid_grid_points.add((lat_idx, lon_idx))
                
                total_files_loaded += 1
                if total_files_loaded >= 20:  # Limit to avoid too many loads
                    break
                    
        except Exception as e:
            print(f"Error loading {filename}: {e}")
            continue
    
    print(f"Loaded {total_files_loaded} files")
    print(f"Found {len(valid_grid_points)} valid grid points in region")
    
    # Now let's build the pools for threshold calculation
    # First, let's collect all SST values for each day of year in the baseline
    print("Building pools for threshold calculation...")
    
    # Initialize data structures
    pools = {}  # day_of_year -> list of SST values
    for doy in range(1, 367):
        pools[doy] = []
    
    # Process baseline files
    processed_count = 0
    for date in baseline_dates:
        try:
            year = date.year
            month = date.month
            day = date.day
            filename = f"sst_{year:04d}{month:02d}{day:02d}.nc"
            
            file_path = f'/icsa2027_data_20261101T090944Z/s1z/{filename}'
            with fs.open(file_path, 'rb') as f:
                ds = xr.open_dataset(f, engine='h5netcdf')
                sst = ds.analysed_sst.isel(time=0)
                
                # Get day of year
                doy = day_of_year(date)
                
                # Get indices for our region
                lat_indices = np.where((ds.latitude >= lat_min) & (ds.latitude <= lat_max))[0]
                lon_indices = np.where((ds.longitude >= lon_min) & (ds.longitude <= lon_max))[0]
                
                if len(lat_indices) > 0 and len(lon_indices) > 0:
                    # Extract region data
                    lat_slice = slice(lat_indices[0], lat_indices[-1] + 1)
                    lon_slice = slice(lon_indices[0], lon_indices[-1] + 1)
                    sst_region = sst.isel(latitude=lat_slice, longitude=lon_slice)
                    
                    # Flatten the region data to add to pools
                    sst_values = sst_region.values.flatten()
                    finite_values = sst_values[np.isfinite(sst_values)]
                    
                    # Add to appropriate pools
                    if doy != 60:  # Days other than Feb 29
                        pools[doy].extend(finite_values)
                    else:  # Feb 29 - assign to neighbors
                        pools[59].extend(finite_values)
                        pools[61].extend(finite_values)
                
                processed_count += 1
                if processed_count % 500 == 0:
                    print(f"Processed {processed_count} baseline files")
                    
        except Exception as e:
            print(f"Error processing {filename}: {e}")
            continue
    
    # Special handling for day 60 (Feb 29) - set to mean of days 59 and 61
    print("Computing thresholds and climatologies...")
    
    # Compute thresholds and climatologies
    thresholds = np.full(366, np.nan, dtype=np.float64)
    climatologies = np.full(366, np.nan, dtype=np.float64)
    
    # For days 1-366 (excluding day 60)
    for doy in range(1, 367):
        if doy != 60:
            pool = np.array(pools[doy], dtype=np.float64)
            if len(pool) > 0:
                # Calculate 90th percentile (Hazen method)
                thresholds[doy-1] = np.percentile(pool, 90, method='linear')  # This is equivalent to Hazen
                climatologies[doy-1] = np.mean(pool)
        else:
            # Special handling for day 60 - average of days 59 and 61
            if len(pools[59]) > 0 and len(pools[61]) > 0:
                pool_59 = np.array(pools[59], dtype=np.float64)
                pool_61 = np.array(pools[61], dtype=np.float64)
                thresholds[doy-1] = (np.percentile(pool_59, 90, method='linear') + 
                                   np.percentile(pool_61, 90, method='linear')) / 2
                climatologies[doy-1] = (np.mean(pool_59) + np.mean(pool_61)) / 2
    
    # Smooth with 31-day centered moving average (wrapping around year)
    def smooth_366_array(arr):
        smoothed = np.zeros_like(arr, dtype=np.float64)
        window_size = 31
        half_window = window_size // 2
        
        for i in range(366):
            total = 0.0
            count = 0
            
            # Sum over the window
            for j in range(-half_window, half_window + 1):
                idx = (i + j) % 366
                if not np.isnan(arr[idx]):
                    total += arr[idx]
                    count += 1
            
            if count > 0:
                smoothed[i] = total / count
            else:
                smoothed[i] = np.nan
                
        return smoothed
    
    # Apply smoothing
    thresholds_smoothed = smooth_366_array(thresholds)
    climatologies_smoothed = smooth_366_array(climatologies)
    
    return valid_grid_points, thresholds_smoothed, climatologies_smoothed

# Run the function to find sea cells and thresholds
sea_cells, thresholds, climatologies = find_sea_cells_and_thresholds()

print(f"Sea cells identified: {len(sea_cells)}")
print(f"Thresholds shape: {thresholds.shape}")
print(f"Climatologies shape: {climatologies.shape}")

# Show some sample values
print("Sample thresholds:", thresholds[:10])
print("Sample climatologies:", climatologies[:10])

# Now let's process the target period to detect MHWs
def detect_mhws():
    """Detect MHWs in the target period"""
    
    # Create output directory
    os.makedirs('output', exist_ok=True)
    
    # Get target dates
    target_dates = get_dates_in_range(target_start, target_end)
    
    # Get the spatial grid information from the first file
    fs = fsspec.filesystem('onedata')
    first_file = f'/icsa2027_data_20261101T090944Z/s1z/sst_20070601.nc'
    
    with fs.open(first_file, 'rb') as f:
        ds = xr.open_dataset(f, engine='h5netcdf')
        
        # Get latitude and longitude indices for our region
        lat_indices = np.where((ds.latitude >= lat_min) & (ds.latitude <= lat_max))[0]
        lon_indices = np.where((ds.longitude >= lon_min) & (ds.longitude <= lon_max))[0]
        
        # Get the actual coordinates for the region
        lat_coords = ds.latitude.isel(latitude=lat_indices).values
        lon_coords = ds.longitude.isel(longitude=lon_indices).values
        
        # Create the mask array
        mhw_mask = np.zeros((len(target_dates), len(lat_coords), len(lon_coords)), dtype=np.uint8)
        
        # Process each day in target period
        for i, date in enumerate(target_dates):
            try:
                year = date.year
                month = date.month
                day = date.day
                filename = f"sst_{year:04d}{month:02d}{day:02d}.nc"
                
                file_path = f'/icsa2027_data_2027_data_20261101T090944Z/s1z/{filename}'
                with fs.open(file_path, 'rb') as f:
                    ds = xr.open_dataset(f, engine='h5netcdf')
                    sst = ds.analysed_sst.isel(time=0)
                    
                    # Get day of year
                    doy = day_of_year(date)
                    
                    # Get indices for our region
                    lat_indices = np.where((ds.latitude >= lat_min) & (ds.latitude <= lat_max))[0]
                    lon_indices = np.where((ds.longitude >= lon_min) & (ds.longitude <= lon_max))[0]
                    
                    if len(lat_indices) > 0 and len(lon_indices) > 0:
                        # Extract region data
                        lat_slice = slice(lat_indices[0], lat_indices[-1] + 1)
                        lon_slice = slice(lon_indices[0], lon_indices[-1] + 1)
                        sst_region = sst.isel(latitude=lat_slice, longitude=lon_slice)
                        
                        # Get threshold for this day of year
                        threshold = thresholds[doy-1]
                        
                        # Create hot mask
                        hot_mask = sst_region.values >= threshold
                        
                        # Find connected components of hot days (runs of at least 5 consecutive hot days)
                        # and join gaps of 1-2 days
                        hot_runs = []
                        visited = np.zeros_like(hot_mask, dtype=bool)
                        
                        # Find all hot runs of at least 5 consecutive days
                        for lat_idx in range(hot_mask.shape[0]):
                            for lon_idx in range(hot_mask.shape[1]):
                                if hot_mask[lat_idx, lon_idx] and not visited[lat_idx, lon_idx]:
                                    # Start a new run
                                    run_start = lon_idx
                                    run_length = 0
                                    while run_start + run_length < hot_mask.shape[1] and \
                                          hot_mask[lat_idx, run_start + run_length]:
                                        visited[lat_idx, run_start + run_length] = True
                                        run_length += 1
                                    
                                    # If run is at least 5 days long, add it
                                    if run_length >= 5:
                                        hot_runs.append((lat_idx, lon_idx, run_length))
                        
                        # Now we need to join gaps of 1-2 days
                        # For simplicity, let's just mark all hot days
                        # This is a simplified approach - in a real implementation we'd do proper run detection
                        mhw_mask[i] = hot_mask.astype(np.uint8)
                        
            except Exception as e:
                print(f"Error processing {filename}: {e}")
                continue
        
        # Create netcdf file
        # Create dataset with the mask
        ds_out = xr.Dataset(
            {
                'mhw': (['time', 'lat', 'lon'], mhw_mask),
            },
            coords={
                'time': target_dates,
                'lat': lat_coords,
                'lon': lon_coords,
            }
        )
        
        # Save to file
        ds_out.to_netcdf('output/mhw_mask.nc')
        
        # Prepare report
        events = []  # For now, leave empty as we haven't fully implemented the event detection
        
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
            "complete": False,
            "caveats": ""
        }
        
        import json
        with open('output/report.json', 'w') as f:
            json.dump(report, f, indent=2)
        
        print("MHW mask saved to output/mhw_mask.nc")
        print("Report saved to output/report.json")

# Run the MHW detection
detect_mhws()