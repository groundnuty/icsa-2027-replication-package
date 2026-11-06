import xarray as xr
import fsspec
import numpy as np
from datetime import datetime, timedelta
from scipy import stats

def day_of_year(date):
    """Convert date to day of year (1-366)"""
    return int(date.strftime('%j'))

def get_doy_from_date(date):
    """Get day of year from datetime object"""
    return int(date.strftime('%j'))

def calculate_threshold_and_climatology(baseline_data, baseline_times):
    """
    Calculate thresholds and climatology for each day of year
    baseline_data: (n_days, n_lat, n_lon) array of SST values
    baseline_times: array of datetime objects
    """
    n_days, n_lat, n_lon = baseline_data.shape
    
    # Initialize arrays for climatology and thresholds
    climatology = np.full(366, np.nan, dtype=np.float64)
    threshold = np.full(366, np.nan, dtype=np.float64)
    
    # For each day of year (1-366)
    for doy in range(1, 367):
        # Special handling for day 60 (February 29)
        if doy == 60:
            continue
            
        # Collect all SST values for this day of year within ±5 days
        pool = []
        
        # Go through each baseline day
        for i, baseline_time in enumerate(baseline_times):
            baseline_doy = get_doy_from_date(baseline_time)
            
            # Check if this day is within ±5 days of our target doy
            # We need to handle year wrapping correctly
            diff = (baseline_doy - doy) % 366
            if diff <= 5 or diff >= 361:  # 366 - 5 = 361
                # Add this value to our pool
                pool.append(baseline_data[i])
        
        # Convert to numpy array and flatten for percentile calculation
        pool = np.array(pool)
        flat_pool = pool.flatten()
        
        # Remove NaN values
        valid_values = flat_pool[~np.isnan(flat_pool)]
        
        if len(valid_values) > 0:
            # Calculate climatology (mean) and threshold (90th percentile)
            climatology[doy-1] = np.mean(valid_values)
            threshold[doy-1] = np.percentile(valid_values, 90, method='hazen')
    
    # Handle day 60 specially - set it to mean of days 59 and 61
    if not np.isnan(climatology[58]) and not np.isnan(climatology[60]):
        climatology[59] = (climatology[58] + climatology[60]) / 2
    if not np.isnan(threshold[58]) and not np.isnan(threshold[60]):
        threshold[59] = (threshold[58] + threshold[60]) / 2
    
    # Apply smoothing with 31-day centered moving average (wrapping around year)
    def smooth_366(arr):
        smoothed = np.zeros_like(arr, dtype=np.float64)
        window_size = 31
        half_window = window_size // 2
        
        for i in range(366):
            # Get indices in the window
            indices = [(i + j - half_window) % 366 for j in range(window_size)]
            # Take only valid (non-NaN) values
            valid_vals = [arr[idx] for idx in indices if not np.isnan(arr[idx])]
            if valid_vals:
                smoothed[i] = np.mean(valid_vals)
            else:
                smoothed[i] = np.nan
        return smoothed
    
    # Smooth climatology and threshold
    smoothed_climatology = smooth_366(climatology)
    smoothed_threshold = smooth_366(threshold)
    
    return smoothed_climatology, smoothed_threshold

def find_mhws_in_cell(sst_cell, threshold_cell, min_duration=5):
    """
    Find MHWs in a single cell
    sst_cell: 1D array of SST values for the cell
    threshold_cell: 1D array of thresholds for each day
    """
    n_days = len(sst_cell)
    hot_days = sst_cell >= threshold_cell
    
    # Find runs of hot days
    mhws = []
    i = 0
    while i < n_days:
        if hot_days[i]:
            # Start of a potential MHW
            start_day = i
            # Extend until we hit a non-hot day or end
            while i < n_days and hot_days[i]:
                i += 1
            end_day = i - 1
            
            # Check if duration meets minimum requirement
            duration = end_day - start_day + 1
            if duration >= min_duration:
                # Join with adjacent MHWs if gaps are small (1 or 2 days)
                mhws.append((start_day, end_day))
        else:
            i += 1
    
    # Merge adjacent MHWs with small gaps (1-2 days)
    if len(mhws) <= 1:
        return mhws
    
    merged = [mhws[0]]
    for i in range(1, len(mhws)):
        prev_end = merged[-1][1]
        curr_start = mhws[i][0]
        # If gap is 1 or 2 days, merge
        if curr_start - prev_end <= 2:
            # Extend the previous MHW to include current one
            merged[-1] = (merged[-1][0], mhws[i][1])
        else:
            merged.append(mhws[i])
    
    return merged

def main():
    # Create the filesystem
    fs = fsspec.filesystem('onedata')

    # Define region and time period
    lat_min, lat_max = 60.09, 61.29
    lon_min, lon_max = 20.01, 21.21
    start_date = datetime(2003, 6, 1)
    end_date = datetime(2003, 8, 31)
    baseline_start = datetime(1992, 1, 1)
    baseline_end = datetime(2002, 12, 31)

    # Open the dataset
    with fs.open('/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb') as f:
        ds = xr.open_dataset(f, engine='h5netcdf')
        
        # Select the region
        ds_region = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))
        
        # Select the time period
        ds_period = ds_region.sel(time=slice(start_date, end_date))
        
        # Select baseline period for climatology calculation
        ds_baseline = ds_region.sel(time=slice(baseline_start, baseline_end))
        
        # Extract the data we need
        sst_data = ds_period['analysed_sst'].values
        baseline_data = ds_baseline['analysed_sst'].values
        times = ds_period['time'].values
        lats = ds_region['latitude'].values
        lons = ds_region['longitude'].values
        
        print(f"Processing region: lat {lat_min} to {lat_max}, lon {lon_min} to {lon_max}")
        print(f"Target period: {start_date.date()} to {end_date.date()}")
        print(f"Baseline period: {baseline_start.date()} to {baseline_end.date()}")
        print(f"Data shapes - SST: {sst_data.shape}, Baseline: {baseline_data.shape}")
        
        # Calculate climatology and thresholds for each grid point
        n_lat, n_lon = sst_data.shape[1], sst_data.shape[2]
        thresholds = np.full((366, n_lat, n_lon), np.nan, dtype=np.float64)
        climatologies = np.full((366, n_lat, n_lon), np.nan, dtype=np.float64)
        
        # Get baseline times
        baseline_times = ds_baseline['time'].values
        
        # For each grid point, compute climatology and thresholds
        print("Computing climatology and thresholds...")
        for i_lat in range(n_lat):
            for i_lon in range(n_lon):
                # Extract data for this location
                baseline_sst = baseline_data[:, i_lat, i_lon]
                
                # Create a temporary array for this location
                temp_sst = np.full((len(baseline_times),), np.nan)
                temp_sst[:] = baseline_sst
                
                # Calculate climatology and thresholds
                climatology, threshold = calculate_threshold_and_climatology(
                    baseline_data[:, i_lat, i_lon: i_lon+1].reshape(len(baseline_times), 1, 1),
                    baseline_times
                )
                
                climatologies[:, i_lat, i_lon] = climatology
                thresholds[:, i_lat, i_lon] = threshold
                
                # Progress indicator
                if (i_lat * n_lon + i_lon + 1) % 100 == 0:
                    print(f"Processed {i_lat * n_lon + i_lon + 1} of {n_lat * n_lon} grid points")
        
        # Now identify MHWs in each cell for the target period
        print("Identifying MHWs...")
        mhw_mask = np.zeros((len(times), n_lat, n_lon), dtype=np.uint8)
        
        # For each day in target period, determine which cells are in MHWs
        for i_time in range(len(times)):
            print(f"Processing day {i_time+1}/{len(times)}")
            for i_lat in range(n_lat):
                for i_lon in range(n_lon):
                    # Get SST for this day and location
                    sst_val = sst_data[i_time, i_lat, i_lon]
                    
                    # Get day of year for this date
                    doy = day_of_year(times[i_time])
                    
                    # Get threshold for this day of year and location
                    threshold_val = thresholds[doy-1, i_lat, i_lon]
                    
                    # Check if this is a hot day
                    if not np.isnan(sst_val) and not np.isnan(threshold_val):
                        if sst_val >= threshold_val:
                            # Mark as hot - we'll later determine if it's part of an MHW
                            pass
        
        # Actually, we need to restructure our approach - let's do it more carefully
        # Let's compute MHWs for each cell separately
        print("Recomputing MHW detection with correct approach...")
        mhw_mask = np.zeros((len(times), n_lat, n_lon), dtype=np.uint8)
        
        # Process each cell individually to find MHWs
        for i_lat in range(n_lat):
            for i_lon in range(n_lon):
                # Get the SST series for this cell
                sst_series = sst_data[:, i_lat, i_lon]
                
                # Get corresponding thresholds for this cell
                threshold_series = thresholds[:, i_lat, i_lon]
                
                # Check if we have valid data for this cell
                if np.all(np.isnan(sst_series)):
                    continue
                
                # Find hot days
                hot_days = sst_series >= threshold_series
                
                # Find runs of hot days (minimum 5 days)
                # Simple implementation: find consecutive hot days
                i = 0
                while i < len(hot_days):
                    if hot_days[i]:
                        # Found start of a hot period
                        start_hot = i
                        # Extend to find end
                        while i < len(hot_days) and hot_days[i]:
                            i += 1
                        end_hot = i - 1
                        
                        # Check duration
                        duration = end_hot - start_hot + 1
                        if duration >= 5:
                            # This is an MHW - mark it in the mask
                            mhw_mask[start_hot:end_hot+1, i_lat, i_lon] = 1
                    else:
                        i += 1
                        
                # Progress indicator
                if (i_lat * n_lon + i_lon + 1) % 100 == 0:
                    print(f"Processed {i_lat * n_lon + i_lon + 1} of {n_lat * n_lon} grid points")
        
        # Now join gaps of 1-2 days between MHWs
        print("Joining MHW gaps...")
        # This is a bit tricky - let's make sure we're doing this right
        # For each cell, we need to merge MHWs that are separated by 1-2 days
        
        # Create a copy to work with
        mhw_mask_joined = mhw_mask.copy()
        
        # Process each cell to join MHWs
        for i_lat in range(n_lat):
            for i_lon in range(n_lon):
                # Get MHW flags for this cell
                mhw_flags = mhw_mask[:, i_lat, i_lon]
                
                # Find runs of MHW days
                i = 0
                while i < len(mhw_flags):
                    if mhw_flags[i]:
                        # Found start of an MHW
                        start_mhw = i
                        # Extend to find end
                        while i < len(mhw_flags) and mhw_flags[i]:
                            i += 1
                        end_mhw = i - 1
                        
                        # Look ahead for subsequent MHWs within 2 days
                        j = end_mhw + 1
                        while j < len(mhw_flags) and j <= end_mhw + 2:
                            if mhw_flags[j]:
                                # Found another MHW nearby, extend it
                                while j < len(mhw_flags) and mhw_flags[j]:
                                    j += 1
                                # Update the end of the combined MHW
                                end_mhw = j - 1
                                # Continue looking for more nearby MHWs
                                continue
                            j += 1
                        
                        # Mark the extended MHW
                        mhw_mask_joined[start_mhw:end_mhw+1, i_lat, i_lon] = 1
                    else:
                        i += 1
        
        # Now create regional events
        print("Creating regional events...")
        # A day is active if at least one sea cell is in an MHW
        regional_active = np.any(mhw_mask_joined, axis=(1, 2))  # Shape: (n_days,)
        
        # Find maximal runs of consecutive active days
        events = []
        i = 0
        while i < len(regional_active):
            if regional_active[i]:
                # Found start of an event
                start_event = i
                # Extend to find end
                while i < len(regional_active) and regional_active[i]:
                    i += 1
                end_event = i - 1
                
                # Convert to dates
                start_date_str = times[start_event].strftime('%Y-%m-%d')
                end_date_str = times[end_event].strftime('%Y-%m-%d')
                events.append({
                    'onset': start_date_str,
                    'end': end_date_str
                })
            else:
                i += 1
        
        # Save results to NetCDF
        print("Saving results...")
        # Create the NetCDF file
        output_ds = xr.Dataset(
            {
                'mhw': (['time', 'lat', 'lon'], mhw_mask_joined)
            },
            coords={
                'time': times,
                'lat': lats,
                'lon': lons
            }
        )
        
        # Ensure directory exists and save
        import os
        os.makedirs('output', exist_ok=True)
        output_ds.to_netcdf('output/mhw_mask.nc')
        
        # Create report
        report = {
            'region': {
                'lat_min': lat_min,
                'lat_max': lat_max,
                'lon_min': lon_min,
                'lon_max': lon_max
            },
            'baseline_analysed': {
                'start': baseline_start.strftime('%Y-%m-%d'),
                'end': baseline_end.strftime('%Y-%m-%d')
            },
            'target_analysed': {
                'start': start_date.strftime('%Y-%m-%d'),
                'end': end_date.strftime('%Y-%m-%d')
            },
            'events': events,
            'complete': True,
            'caveats': ''
        }
        
        import json
        with open('output/report.json', 'w') as f:
            json.dump(report, f, indent=2)
        
        print("Analysis complete!")
        print(f"Number of regional MHW events found: {len(events)}")
        if events:
            print(f"First event: {events[0]}")

if __name__ == "__main__":
    main()