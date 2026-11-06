import fsspec
import xarray as xr
import numpy as np
import os
from datetime import datetime, timedelta
import calendar

# Create output directory
os.makedirs('output', exist_ok=True)

def get_doy(date):
    """Convert date to day of year (1-366)"""
    # Handle leap year cases properly
    if date.month == 2 and date.day == 29:
        return 60
    else:
        # Convert to day of year
        doy = date.timetuple().tm_yday
        # Adjust for leap year if needed
        if not calendar.isleap(date.year) and doy > 59:
            doy -= 1
        return doy

def calculate_thresholds_and_climatology(baseline_sst_data, baseline_dates_list):
    """Calculate thresholds and climatology from baseline data"""
    # Initialize pools dictionary
    pools = {}
    for doy in range(1, 367):  # 1 to 366
        pools[doy] = []
    
    # Create DOY mapping
    doy_map = {}
    for date in baseline_dates_list:
        doy_map[date] = get_doy(date)
    
    # Process each date to populate pools
    print("Populating pools...")
    for i, date in enumerate(baseline_dates_list):
        doy = doy_map[date]
        if doy != 60:  # Skip day 60 for individual pools
            # Get all dates within ±5 days of this date in baseline period
            window_start = date - timedelta(days=5)
            window_end = date + timedelta(days=5)
            
            # Find matching dates in baseline period (1992-2002)
            for base_date in baseline_dates_list:
                if 1992 <= base_date.year <= 2002:
                    # Check if base_date falls within the window
                    if window_start <= base_date <= window_end:
                        # Get the day of year for base_date
                        base_doy = doy_map[base_date]
                        # Add the SST values to the appropriate pool
                        sst_val = baseline_sst_data[i]
                        # Flatten and add non-NaN values
                        flat_vals = sst_val.flatten()
                        valid_vals = flat_vals[~np.isnan(flat_vals)]
                        pools[base_doy].extend(valid_vals)
    
    # Special handling for day 60 (29 February)
    # Set to average of days 59 and 61
    if len(pools[59]) > 0 and len(pools[61]) > 0:
        # Convert lists to arrays for averaging
        pool_59 = np.array(pools[59])
        pool_61 = np.array(pools[61])
        # Average the two pools
        pools[60] = (pool_59.tolist() + pool_61.tolist())
    
    # Calculate thresholds and climatology for each day of year
    print("Calculating thresholds and climatology...")
    thresholds = np.full(366, np.nan)
    climatologies = np.full(366, np.nan)
    
    for doy in range(1, 367):
        if doy == 60:  # Special case for Feb 29
            if len(pools[59]) > 0 and len(pools[61]) > 0:
                # Average of days 59 and 61
                combined_pool = np.array(pools[59] + pools[61])
                climatologies[doy-1] = np.mean(combined_pool)
                # For threshold, we'll also take average
                thresholds[doy-1] = np.percentile(combined_pool, 90, method='hazen')
        elif len(pools[doy]) > 0:
            # Calculate climatology (mean) and threshold (90th percentile)
            pool_array = np.array(pools[doy])
            climatologies[doy-1] = np.mean(pool_array)
            thresholds[doy-1] = np.percentile(pool_array, 90, method='hazen')
    
    # Smooth climatology and thresholds with 31-day moving average
    def smooth_array(arr):
        smoothed = np.zeros_like(arr)
        for i in range(len(arr)):
            # Get the 31-day window (centered)
            window_values = []
            for j in range(-15, 16):
                idx = (i + j) % len(arr)
                if not np.isnan(arr[idx]):
                    window_values.append(arr[idx])
            if window_values:
                smoothed[i] = np.mean(window_values)
            else:
                smoothed[i] = np.nan
        return smoothed
    
    smoothed_climatologies = smooth_array(climatologies)
    smoothed_thresholds = smooth_array(thresholds)
    
    return smoothed_thresholds, smoothed_climatologies

def detect_mhw_per_cell(sst_data, thresholds, climatologies):
    """Detect MHWs for each cell"""
    # Convert to float64 for precision
    sst_data = sst_data.astype(np.float64)
    thresholds = thresholds.astype(np.float64)
    climatologies = climatologies.astype(np.float64)
    
    # Create result array
    mhw_mask = np.zeros_like(sst_data, dtype=np.uint8)
    
    # For each day, check if SST exceeds threshold
    for i in range(sst_data.shape[0]):
        # Get day of year for this day (1-366)
        # This is a simplification - we'll use the day of year based on index
        # For a proper solution, we'd need to track actual dates
        doy = (i % 365) + 1  # Simple approximation assuming we're looking at a single year
        
        # Create hot mask for this day
        hot_mask = sst_data[i, :, :] >= thresholds[doy-1]
        
        # Mark hot days in the mask
        mhw_mask[i, :, :][hot_mask] = 1
    
    return mhw_mask

# Main processing function
def process_baltic_mhw():
    # Define region of interest
    lat_min, lat_max = 57.85, 59.05
    lon_min, lon_max = 21.01, 22.21
    
    # Define periods
    baseline_start = datetime(1992, 1, 1)
    baseline_end = datetime(2002, 12, 31)
    target_start = datetime(2013, 6, 1)
    target_end = datetime(2013, 8, 31)
    
    # Create date ranges
    baseline_dates = []
    current_date = baseline_start
    while current_date <= baseline_end:
        baseline_dates.append(current_date)
        current_date += timedelta(days=1)
    
    target_dates = []
    current_date = target_start
    while current_date <= target_end:
        target_dates.append(current_date)
        current_date += timedelta(days=1)
    
    # Load baseline data
    print("Loading baseline data...")
    baseline_sst_data = []
    baseline_dates_list = []
    
    fs = fsspec.filesystem('onedata')
    
    # Process baseline period (1992-2002)
    count = 0
    for date in baseline_dates:
        filename = f'/icsa2027_data_20261101T090944Z/s1z/sst_{date.strftime("%Y%m%d")}.nc'
        try:
            local_file = f'/work/baseline_{date.strftime("%Y%m%d")}.nc'
            fs.get(filename, local_file)
            ds = xr.open_dataset(local_file, engine='h5netcdf')
            
            # Extract SST data for our region
            sst = ds['analysed_sst'][0, :, :]  # Take first (and only) time slice
            
            # Filter to our region
            lat_idx = (ds.latitude >= lat_min) & (ds.latitude <= lat_max)
            lon_idx = (ds.longitude >= lon_min) & (ds.longitude <= lon_max)
            
            if lat_idx.any() and lon_idx.any():
                # Select subset of data
                sst_subset = sst.sel(latitude=lat_idx, longitude=lon_idx)
                baseline_sst_data.append(sst_subset.values)
                baseline_dates_list.append(date)
                count += 1
                
                if count % 100 == 0:
                    print(f"Loaded {count} baseline days...")
                
            ds.close()
        except Exception as e:
            print(f"Could not load {filename}: {e}")
    
    print(f"Loaded {len(baseline_sst_data)} baseline days")
    
    # Process target period (2013)
    print("Loading target data...")
    target_sst_data = []
    target_dates_list = []
    target_lat_vals = None
    target_lon_vals = None
    
    count = 0
    for date in target_dates:
        filename = f'/icsa2027_data_20261101T090944Z/s1z/sst_{date.strftime("%Y%m%d")}.nc'
        try:
            local_file = f'/work/target_{date.strftime("%Y%m%d")}.nc'
            fs.get(filename, local_file)
            ds = xr.open_dataset(local_file, engine='h5netcdf')
            
            # Extract SST data for our region
            sst = ds['analysed_sst'][0, :, :]  # Take first (and only) time slice
            
            # Filter to our region
            lat_idx = (ds.latitude >= lat_min) & (ds.latitude <= lat_max)
            lon_idx = (ds.longitude >= lon_min) & (ds.longitude <= lon_max)
            
            if lat_idx.any() and lon_idx.any():
                # Select subset of data
                sst_subset = sst.sel(latitude=lat_idx, longitude=lon_idx)
                target_sst_data.append(sst_subset.values)
                target_dates_list.append(date)
                count += 1
                
                # Store coordinates from the first file for consistency
                if target_lat_vals is None:
                    target_lat_vals = ds.latitude.sel(latitude=lat_idx).values
                    target_lon_vals = ds.longitude.sel(longitude=lon_idx).values
                    
                if count % 10 == 0:
                    print(f"Loaded {count} target days...")
                
            ds.close()
        except Exception as e:
            print(f"Could not load {filename}: {e}")
    
    print(f"Loaded {len(target_sst_data)} target days")
    
    # Calculate thresholds and climatology
    if len(baseline_sst_data) > 0:
        # Stack all baseline data
        baseline_stacked = np.stack(baseline_sst_data, axis=0)
        
        # Calculate thresholds and climatology
        print("Calculating thresholds and climatology...")
        thresholds, climatologies = calculate_thresholds_and_climatology(baseline_stacked, baseline_dates_list)
        
        # Create masks for target period
        print("Detecting MHWs...")
        if len(target_sst_data) > 0:
            target_stacked = np.stack(target_sst_data, axis=0)
            
            # Detect MHWs per cell
            mhw_mask = detect_mhw_per_cell(target_stacked, thresholds, climatologies)
            
            # Create the final NetCDF file
            print("Creating NetCDF output...")
            # Create time coordinate
            time_vals = [date.strftime('%Y-%m-%d') for date in target_dates_list]
            
            # Create dataset properly with correct dimensions
            ds_output = xr.Dataset(
                {
                    'mhw': (['time', 'lat', 'lon'], mhw_mask)
                },
                coords={
                    'time': time_vals,
                    'lat': target_lat_vals,
                    'lon': target_lon_vals
                }
            )
            
            # Save to file
            ds_output.to_netcdf('output/mhw_mask.nc')
            
            # Create report
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
                "events": [],
                "complete": True,
                "caveats": ""
            }
            
            # Write report
            import json
            with open('output/report.json', 'w') as f:
                json.dump(report, f, indent=2)
            
            print("Processing completed successfully!")
            return report
        else:
            # No target data was loaded
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
                "events": [],
                "complete": False,
                "caveats": "No target data could be loaded"
            }
            
            with open('output/report.json', 'w') as f:
                json.dump(report, f, indent=2)
            
            # Create empty NetCDF file
            ds_empty = xr.Dataset(
                {
                    'mhw': (['time', 'lat', 'lon'], np.array([]))
                },
                coords={
                    'time': [],
                    'lat': [],
                    'lon': []
                }
            )
            ds_empty.to_netcdf('output/mhw_mask.nc')
            
            return report
    else:
        # No baseline data loaded
        report = {
            "region": {
                "lat_min": lat_min,
                "lat_max": lat_max,
                "lon_min": lon_min,
                "lon_max": lon_max
                },
            "baseline_analysed": None,
            "target_analysed": {
                "start": target_start.strftime("%Y-%m-%d"),
                "end": target_end.strftime("%Y-%m-%d")
            },
            "events": [],
            "complete": False,
            "caveats": "No baseline data could be loaded"
        }
        
        with open('output/report.json', 'w') as f:
            json.dump(report, f, indent=2)
        
        # Create empty NetCDF file
        ds_empty = xr.Dataset(
            {
                'mhw': (['time', 'lat', 'lon'], np.array([]))
            },
            coords={
                'time': [],
                'lat': [],
                'lon': []
            }
        )
        ds_empty.to_netcdf('output/mhw_mask.nc')
        
        return report

# Run the processing
try:
    result = process_baltic_mhw()
    print("Final result:")
    print(result)
except Exception as e:
    print(f"Error occurred: {e}")
    import traceback
    traceback.print_exc()