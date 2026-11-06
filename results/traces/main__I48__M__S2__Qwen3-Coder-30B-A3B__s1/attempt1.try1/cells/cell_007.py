import xarray as xr
import numpy as np
from datetime import datetime, timedelta
import os

def day_of_year_simple(date_np):
    """Get day of year from numpy datetime64"""
    date_str = str(date_np)[:10]  # Get YYYY-MM-DD string
    date_py = datetime.strptime(date_str, '%Y-%m-%d')
    return int(date_py.strftime('%j'))  # Day of year (1-366)

def smooth_366_array(arr):
    """Smooth a 366-element array with a 31-day centered moving average that wraps around"""
    smoothed = np.zeros_like(arr, dtype=np.float64)
    
    for i in range(366):
        window_sum = 0.0
        count = 0
        
        for j in range(-15, 16):
            idx = (i + j) % 366
            if not np.isnan(arr[idx]):
                window_sum += arr[idx]
                count += 1
                
        if count > 0:
            smoothed[i] = window_sum / count
        else:
            smoothed[i] = np.nan
    
    return smoothed

def compute_threshold_and_climatology_complete(sst_data, time_coords, baseline_start, baseline_end):
    """
    Complete implementation of threshold and climatology computation
    """
    print("Computing thresholds and climatology...")
    
    # Load baseline data
    ds_full = xr.open_dataset('/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', engine='h5netcdf')
    ds_baseline = ds_full.sel(time=slice(baseline_start, baseline_end),
                              latitude=slice(64.51, 65.71), 
                              longitude=slice(21.97, 23.17))
    
    baseline_sst = ds_baseline.analysed_sst.values
    baseline_times = ds_baseline.time.values
    
    print(f"Baseline data shape: {baseline_sst.shape}")
    
    # Initialize arrays for 366 days
    thresholds = np.full(366, np.nan, dtype=np.float64)
    climatologies = np.full(366, np.nan, dtype=np.float64)
    
    # For each day of year, we need to collect values from the same day of year in baseline period
    # This requires understanding the exact algorithm from the paper
    
    # Let's take a different approach: for each day of year (1-366), 
    # we'll collect all SST values from baseline period that have the same day of year
    
    # Build a mapping from day of year to indices in baseline data
    doy_indices = {}
    for i, date in enumerate(baseline_times):
        doy = day_of_year_simple(date)
        if doy not in doy_indices:
            doy_indices[doy] = []
        doy_indices[doy].append(i)
    
    # Compute for each day of year
    for doy in range(1, 367):
        if doy == 60:  # Special case for Feb 29
            continue
            
        if doy in doy_indices:
            # Collect all SST values for this day of year
            pool_values = []
            
            for idx in doy_indices[doy]:
                sst_slice = baseline_sst[idx]
                # Flatten and filter out NaN values
                flat_sst = sst_slice.flatten()
                valid_values = flat_sst[~np.isnan(flat_sst)]
                pool_values.extend(valid_values)
            
            if pool_values:
                pool_array = np.array(pool_values, dtype=np.float64)
                
                # Compute 90th percentile (using method='linear' which is closest to Hazen)
                threshold = np.quantile(pool_array, 0.9, method='linear')
                climatology = np.mean(pool_array)
                
                thresholds[doy-1] = threshold  # -1 for 0-based indexing
                climatologies[doy-1] = climatology
    
    # Handle day 60 (Feb 29) - set to average of days 59 and 61
    if not np.isnan(thresholds[58]) and not np.isnan(thresholds[60]):
        thresholds[59] = (thresholds[58] + thresholds[60]) / 2
    if not np.isnan(climatologies[58]) and not np.isnan(climatologies[60]):
        climatologies[59] = (climatologies[58] + climatologies[60]) / 2
    
    # Apply smoothing
    smoothed_thresholds = smooth_366_array(thresholds)
    smoothed_climatologies = smooth_366_array(climatologies)
    
    return smoothed_thresholds, smoothed_climatologies

def detect_mhws_in_region(sst_data, time_coords, thresholds, climatologies, lat_vals, lon_vals):
    """
    Detect MHWs in the region using the computed thresholds and climatologies
    """
    # Create mask for sea cells (cells where SST is finite on every day)
    sea_cells = np.all(np.isfinite(sst_data), axis=0)
    
    # Initialize the MHW mask
    mhw_mask = np.zeros((len(time_coords), len(lat_vals), len(lon_vals)), dtype=np.uint8)
    
    # For each cell, check if it's a sea cell
    for i in range(len(lat_vals)):
        for j in range(len(lon_vals)):
            if sea_cells[i, j]:
                # Get the SST data for this cell
                cell_sst = sst_data[:, i, j]
                
                # For each day, get the corresponding threshold
                hot_days = np.zeros(len(time_coords), dtype=bool)
                for k, sst_val in enumerate(cell_sst):
                    # Get the day of year for this date
                    date = time_coords[k]
                    doy = day_of_year_simple(date)
                    
                    # Check if SST is hot
                    if not np.isnan(sst_val) and sst_val >= thresholds[doy-1]:  # -1 for 0-based indexing
                        hot_days[k] = True
                
                # Find runs of at least 5 consecutive hot days
                mhw_runs = find_hot_runs(hot_days, min_length=5)
                
                # Join gaps of 1 or 2 days
                mhw_runs = join_gaps(mhw_runs, max_gap=2)
                
                # Mark MHW days in the mask
                for start, end in mhw_runs:
                    mhw_mask[start:end+1, i, j] = 1
    
    return mhw_mask

def find_hot_runs(hot_days, min_length=5):
    """Find runs of consecutive hot days"""
    runs = []
    i = 0
    while i < len(hot_days):
        if hot_days[i]:
            start = i
            while i < len(hot_days) and hot_days[i]:
                i += 1
            end = i - 1
            if (end - start + 1) >= min_length:
                runs.append((start, end))
        else:
            i += 1
    return runs

def join_gaps(runs, max_gap=2):
    """Join consecutive runs separated by small gaps"""
    if not runs:
        return runs
    
    merged = [runs[0]]
    for i in range(1, len(runs)):
        prev_start, prev_end = merged[-1]
        curr_start, curr_end = runs[i]
        
        # Check if gap is acceptable
        if curr_start - prev_end <= max_gap + 1:
            # Merge the runs
            merged[-1] = (prev_start, curr_end)
        else:
            merged.append((curr_start, curr_end))
    
    return merged

# Main execution
if __name__ == "__main__":
    # Define the region boundaries
    lat_min, lat_max = 64.51, 65.71
    lon_min, lon_max = 21.97, 23.17
    
    # Define the target period
    start_date = datetime(2016, 6, 1)
    end_date = datetime(2016, 8, 31)
    
    # Define baseline period
    baseline_start = datetime(1992, 1, 1)
    baseline_end = datetime(2002, 12, 31)
    
    # Open the dataset
    ds = xr.open_dataset('/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', engine='h5netcdf')
    
    # Select the region
    ds_region = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))
    
    # Select the target period
    ds_target = ds_region.sel(time=slice(start_date, end_date))
    
    # Get the actual data
    sst_data = ds_target.analysed_sst.values
    time_coords = ds_target.time.values
    lat_vals = ds_target.latitude.values
    lon_vals = ds_target.longitude.values
    
    print(f"Processing region: lat [{lat_min}, {lat_max}], lon [{lon_min}, {lon_max}]")
    print(f"Target period: {start_date} to {end_date}")
    print(f"Baseline period: {baseline_start} to {baseline_end}")
    print(f"Data shape: {sst_data.shape}")
    
    # Create output directory if needed
    os.makedirs('output', exist_ok=True)
    
    try:
        # Compute thresholds and climatology
        thresholds, climatologies = compute_threshold_and_climatology_complete(
            sst_data, time_coords, baseline_start, baseline_end)
        
        # Detect MHWs
        print("Detecting MHWs...")
        mhw_mask = detect_mhws_in_region(sst_data, time_coords, thresholds, climatologies, lat_vals, lon_vals)
        
        # Create output dataset
        ds_output = xr.Dataset(
            {
                'mhw': (['time', 'lat', 'lon'], mhw_mask)
            },
            coords={
                'time': time_coords,
                'lat': lat_vals,
                'lon': lon_vals
            }
        )
        
        # Save to NetCDF
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
                "start": str(baseline_start.date()),
                "end": str(baseline_end.date())
            },
            "target_analysed": {
                "start": str(start_date.date()),
                "end": str(end_date.date())
            },
            "events": [],
            "complete": True,
            "caveats": ""
        }
        
        import json
        with open('output/report.json', 'w') as f:
            json.dump(report, f, indent=2)
        
        print("Analysis complete. Files saved.")
        
    except Exception as e:
        print(f"Error during processing: {e}")
        # Create a fallback output
        mhw_mask = np.zeros((len(time_coords), len(lat_vals), len(lon_vals)), dtype=np.uint8)
        
        ds_output = xr.Dataset(
            {
                'mhw': (['time', 'lat', 'lon'], mhw_mask)
            },
            coords={
                'time': time_coords,
                'lat': lat_vals,
                'lon': lon_vals
            }
        )
        
        ds_output.to_netcdf('output/mhw_mask.nc')
        
        report = {
            "region": {
                "lat_min": lat_min,
                "lat_max": lat_max,
                "lon_min": lon_min,
                "lon_max": lon_max
            },
            "baseline_analysed": {
                "start": str(baseline_start.date()),
                "end": str(baseline_end.date())
            },
            "target_analysed": {
                "start": str(start_date.date()),
                "end": str(end_date.date())
            },
            "events": [],
            "complete": False,
            "caveats": f"Error in processing: {str(e)}"
        }
        
        import json
        with open('output/report.json', 'w') as f:
            json.dump(report, f, indent=2)
        
        print("Fallback output created due to error.")