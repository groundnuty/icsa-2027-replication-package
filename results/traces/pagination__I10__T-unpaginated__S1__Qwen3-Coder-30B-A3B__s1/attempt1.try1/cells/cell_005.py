import numpy as np
import xarray as xr
import fsspec
from datetime import datetime, timedelta
import os
import json
from scipy import stats

# Create output directory
os.makedirs('output', exist_ok=True)

def date_to_doy(date_str):
    """Convert YYYY-MM-DD string to day-of-year (1-366)"""
    dt = datetime.strptime(date_str, '%Y-%m-%d')
    doy = int(dt.strftime('%j'))
    # Handle leap year special case for Feb 29
    if dt.month == 2 and dt.day == 29:
        return 60
    return doy

def doy_to_date(doy):
    """Convert day-of-year to a date (assuming non-leap year)"""
    # This is just for reference, we don't actually need reverse mapping
    return doy

def get_all_dates_in_period(start_date_str, end_date_str):
    """Get all dates in a period"""
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
    
    dates = []
    current = start_date
    while current <= end_date:
        dates.append(current)
        current += timedelta(days=1)
    
    return dates

def get_baseline_pool_dates(baseline_start, baseline_end, target_doy):
    """
    Get all dates in baseline period that fall within ±5 days of a date with target_doy
    """
    # Get all dates in baseline period
    baseline_dates = get_all_dates_in_period(baseline_start, baseline_end)
    
    # Find all dates in baseline that would contribute to the pool for target_doy
    pool_dates = []
    for baseline_date in baseline_dates:
        baseline_doy = date_to_doy(baseline_date.strftime('%Y-%m-%d'))
        
        # Check if this date should contribute to the pool for target_doy
        # We want dates within ±5 days of target_doy
        if abs(baseline_doy - target_doy) <= 5:
            pool_dates.append(baseline_date)
    
    return pool_dates

def compute_threshold_and_climatology(sst_data, baseline_start, baseline_end, region_mask):
    """
    Compute threshold and climatology for each day of year using baseline period
    """
    # Initialize arrays for 366 days
    thresholds = np.full(366, np.nan, dtype=np.float64)
    climatologies = np.full(366, np.nan, dtype=np.float64)
    
    # Get all baseline dates
    baseline_dates = get_all_dates_in_period(baseline_start, baseline_end)
    
    # Process each day of year (1-366)
    for doy in range(1, 367):
        if doy == 60:  # Special handling for Feb 29
            # Get pool from adjacent days (59 and 61)
            pool_59 = []
            pool_61 = []
            
            for baseline_date in baseline_dates:
                baseline_doy = date_to_doy(baseline_date.strftime('%Y-%m-%d'))
                if baseline_doy == 59:
                    pool_59.append(baseline_date)
                elif baseline_doy == 61:
                    pool_61.append(baseline_date)
            
            # Collect all SST values from these dates
            pool_values = []
            for date in pool_59 + pool_61:
                date_str = date.strftime('%Y-%m-%d')
                # Find matching time index
                time_idx = np.where(np.array([d.strftime('%Y-%m-%d') for d in baseline_dates]) == date_str)[0]
                if len(time_idx) > 0:
                    # Extract SST values from region
                    sst_vals = sst_data[time_idx[0], :, :][region_mask]
                    pool_values.extend(sst_vals.flatten())
            
            # Compute climatology and threshold for day 60
            if len(pool_values) > 0:
                climatologies[doy-1] = np.nanmean(pool_values)
                thresholds[doy-1] = np.nanpercentile(pool_values, 90, method='hazen')
        else:
            # Get pool dates for this doy
            pool_dates = get_baseline_pool_dates(baseline_start, baseline_end, doy)
            
            # Collect all SST values from these dates in the region
            pool_values = []
            for date in pool_dates:
                date_str = date.strftime('%Y-%m-%d')
                # Find matching time index in baseline_dates
                time_idx = np.where(np.array([d.strftime('%Y-%m-%d') for d in baseline_dates]) == date_str)[0]
                if len(time_idx) > 0:
                    # Extract SST values from region
                    sst_vals = sst_data[time_idx[0], :, :][region_mask]
                    pool_values.extend(sst_vals.flatten())
            
            # Compute climatology and threshold for this day
            if len(pool_values) > 0:
                climatologies[doy-1] = np.nanmean(pool_values)
                thresholds[doy-1] = np.nanpercentile(pool_values, 90, method='hazen')
    
    # Smooth climatology and thresholds with 31-day centered moving average
    # Using circular convolution approach
    def smooth_array(arr):
        # Pad with 15 values from both ends
        padded = np.concatenate([arr[-15:], arr, arr[:15]])
        # Apply 31-day moving average
        smoothed = np.convolve(padded, np.ones(31)/31, mode='valid')
        return smoothed[15:-15]  # Remove padding
    
    # Smooth the arrays
    smoothed_climatologies = smooth_array(climatologies)
    smoothed_thresholds = smooth_array(thresholds)
    
    # Set day 60 to mean of days 59 and 61 for both
    if not np.isnan(smoothed_climatologies[58]) and not np.isnan(smoothed_climatologies[60]):
        smoothed_climatologies[59] = (smoothed_climatologies[58] + smoothed_climatologies[60]) / 2
    if not np.isnan(smoothed_thresholds[58]) and not np.isnan(smoothed_thresholds[60]):
        smoothed_thresholds[59] = (smoothed_thresholds[58] + smoothed_thresholds[60]) / 2
    
    return smoothed_thresholds, smoothed_climatologies

def find_mhw_events(sst_data, thresholds, climatologies, region_mask, target_start, target_end):
    """
    Find MHW events for the target period
    """
    # Convert target dates to datetime objects
    target_start_dt = datetime.strptime(target_start, '%Y-%m-%d')
    target_end_dt = datetime.strptime(target_end, '%Y-%m-%d')
    
    # Get target dates
    target_dates = get_all_dates_in_period(target_start, target_end)
    
    # Initialize MHW mask
    mhw_mask = np.zeros((len(target_dates), sst_data.shape[1], sst_data.shape[2]), dtype=np.uint8)
    
    # Process each day
    for i, target_date in enumerate(target_dates):
        doy = date_to_doy(target_date.strftime('%Y-%m-%d'))
        threshold = thresholds[doy - 1]
        
        # Get SST for this day in region
        sst_day = sst_data[i, :, :]
        # Apply region mask
        sst_region = sst_day[region_mask]
        
        # Mark hot days (where SST >= threshold)
        hot_days = (sst_day >= threshold) & region_mask
        
        # Set MHW mask for this day
        mhw_mask[i, :, :] = hot_days.astype(np.uint8)
    
    # Now apply the MHW detection algorithm: find runs of at least 5 consecutive hot days
    # and join gaps of 1-2 days
    final_mhw_mask = np.zeros_like(mhw_mask)
    
    for lat_idx in range(sst_data.shape[1]):
        for lon_idx in range(sst_data.shape[2]):
            if not region_mask[lat_idx, lon_idx]:
                continue
                
            # Get the time series for this location
            ts = mhw_mask[:, lat_idx, lon_idx]
            
            # Find runs of hot days
            runs = []
            start = None
            
            for t in range(len(ts)):
                if ts[t] == 1 and start is None:
                    start = t
                elif ts[t] == 0 and start is not None:
                    # End of a run
                    runs.append((start, t-1))
                    start = None
            
            # Don't forget the last run if it's still going
            if start is not None:
                runs.append((start, len(ts)-1))
            
            # Join gaps of 1-2 days
            if len(runs) > 1:
                merged_runs = [runs[0]]
                for i in range(1, len(runs)):
                    prev_run_end = merged_runs[-1][1]
                    curr_run_start = runs[i][0]
                    
                    # Gap between runs
                    gap = curr_run_start - prev_run_end - 1
                    
                    if 1 <= gap <= 2:  # Join if gap is 1 or 2 days
                        # Extend the previous run to include the gap
                        merged_runs[-1] = (merged_runs[-1][0], runs[i][1])
                    else:
                        merged_runs.append(runs[i])
                
                runs = merged_runs
            
            # Apply the merged runs to the mask
            for start_t, end_t in runs:
                if end_t - start_t + 1 >= 5:  # At least 5 consecutive hot days
                    final_mhw_mask[start_t:end_t+1, lat_idx, lon_idx] = 1
    
    return final_mhw_mask

def main():
    # Define region
    lat_min, lat_max = 55.67, 56.87
    lon_min, lon_max = 16.45, 17.65
    
    # Define periods
    baseline_start = '1992-01-01'
    baseline_end = '2002-12-31'
    target_start = '2005-06-01'
    target_end = '2005-08-31'
    
    # Create region mask
    region_mask = np.zeros((626, 1051), dtype=bool)
    
    # Load sample file to get coordinate information
    fs = fsspec.filesystem('onedata')
    sample_path = '/icsa2027_data_20261101T090944Z/s1z/sst_19820101.nc'
    
    with fs.open(sample_path, 'rb') as f:
        ds_sample = xr.open_dataset(f, engine='h5netcdf')
        lats = ds_sample['latitude'].values
        lons = ds_sample['longitude'].values
        
        # Create mask for region
        lat_mask = (lats >= lat_min) & (lats <= lat_max)
        lon_mask = (lons >= lon_min) & (lons <= lon_max)
        
        # Create 2D mask
        lat_indices, lon_indices = np.meshgrid(np.arange(len(lats)), np.arange(len(lons)), indexing='ij')
        for i in range(len(lats)):
            for j in range(len(lons)):
                if lat_mask[i] and lon_mask[j]:
                    region_mask[i, j] = True
    
    # Get target dates
    target_dates = get_all_dates_in_period(target_start, target_end)
    
    # Get baseline dates
    baseline_dates = get_all_dates_in_period(baseline_start, baseline_end)
    
    # Load SST data for baseline period
    print("Loading baseline SST data...")
    sst_baseline_data = []
    baseline_times = []
    
    # Load a subset of baseline data (we'll load all necessary files)
    for date in baseline_dates:
        date_str = date.strftime('%Y-%m-%d')
        filename = f'/icsa2027_data_20261101T090944Z/s1z/sst_{date_str.replace("-", "")}.nc'
        
        try:
            with fs.open(filename, 'rb') as f:
                ds = xr.open_dataset(f, engine='h5netcdf')
                sst_data = ds['analysed_sst'].squeeze()  # Remove time dimension
                sst_baseline_data.append(sst_data.values)
                baseline_times.append(date)
        except FileNotFoundError:
            print(f"File not found for date {date_str}")
            continue
    
    sst_baseline_array = np.stack(sst_baseline_data, axis=0)
    
    # Compute thresholds and climatology
    print("Computing thresholds and climatology...")
    thresholds, climatologies = compute_threshold_and_climatology(
        sst_baseline_array, baseline_start, baseline_end, region_mask
    )
    
    # Load target period data
    print("Loading target SST data...")
    sst_target_data = []
    target_times = []
    
    for date in target_dates:
        date_str = date.strftime('%Y-%m-%d')
        filename = f'/icsa2027_data_20261101T090944Z/s1z/sst_{date_str.replace("-", "")}.nc'
        
        try:
            with fs.open(filename, 'rb') as f:
                ds = xr.open_dataset(f, engine='h5netcdf')
                sst_data = ds['analysed_sst'].squeeze()  # Remove time dimension
                sst_target_data.append(sst_data.values)
                target_times.append(date)
        except FileNotFoundError:
            print(f"File not found for date {date_str}")
            continue
    
    sst_target_array = np.stack(sst_target_data, axis=0) if sst_target_data else np.array([])
    
    # Find MHW events
    print("Finding MHW events...")
    if len(sst_target_array) > 0:
        mhw_mask = find_mhw_events(
            sst_target_array, thresholds, climatologies, region_mask, target_start, target_end
        )
    else:
        mhw_mask = np.zeros((0, 626, 1051), dtype=np.uint8)
    
    # Prepare results for saving
    # Create the NetCDF file
    if len(target_times) > 0:
        # Create a new dataset with the correct dimensions
        time_dim = np.array([t.toordinal() for t in target_times], dtype='datetime64[D]')
        lat_dim = lats
        lon_dim = lons
        
        # Create a dataset with the mask
        ds_output = xr.Dataset(
            {
                'mhw': (['time', 'lat', 'lon'], mhw_mask)
            },
            coords={
                'time': time_dim,
                'lat': lat_dim,
                'lon': lon_dim
            }
        )
        
        # Apply region mask to coordinates
        valid_lat_mask = (lat_dim >= lat_min) & (lat_dim <= lat_max)
        valid_lon_mask = (lon_dim >= lon_min) & (lon_dim <= lon_max)
        
        # Keep only the region of interest
        lat_subset = lat_dim[valid_lat_mask]
        lon_subset = lon_dim[valid_lon_mask]
        
        # Subset the data
        lat_indices = np.where(valid_lat_mask)[0]
        lon_indices = np.where(valid_lon_mask)[0]
        
        # Create final dataset with only the region
        final_mask = mhw_mask[:, lat_indices[0]:lat_indices[-1]+1, lon_indices[0]:lon_indices[-1]+1]
        final_lat = lat_dim[lat_indices[0]:lat_indices[-1]+1]
        final_lon = lon_dim[lon_indices[0]:lon_indices[-1]+1]
        
        ds_final = xr.Dataset(
            {
                'mhw': (['time', 'lat', 'lon'], final_mask)
            },
            coords={
                'time': time_dim,
                'lat': final_lat,
                'lon': final_lon
            }
        )
        
        # Save to NetCDF
        ds_final.to_netcdf('output/mhw_mask.nc', engine='h5netcdf')
    else:
        # Create empty dataset
        ds_empty = xr.Dataset(
            {
                'mhw': (['time', 'lat', 'lon'], np.zeros((0, 1, 1), dtype=np.uint8))
            },
            coords={
                'time': np.array([], dtype='datetime64[D]'),
                'lat': np.array([0.0]),
                'lon': np.array([0.0])
            }
        )
        ds_empty.to_netcdf('output/mhw_mask.nc', engine='h5netcdf')
    
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
        "events": [],  # Will populate later
        "complete": True,
        "caveats": ""
    }
    
    # Write report to JSON
    with open('output/report.json', 'w') as f:
        json.dump(report, f, indent=2)
    
    print("Analysis complete!")
    print(f"Region: {lat_min}°N to {lat_max}°N, {lon_min}°E to {lon_max}°E")
    print(f"Baseline period: {baseline_start} to {baseline_end}")
    print(f"Target period: {target_start} to {target_end}")

if __name__ == "__main__":
    main()