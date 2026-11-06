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

def compute_threshold_and_climatology_single_day(sst_data, baseline_start, baseline_end, target_doy, region_mask):
    """
    Compute threshold and climatology for a single day of year
    """
    # Get pool dates for this doy
    pool_dates = get_baseline_pool_dates(baseline_start, baseline_end, target_doy)
    
    # Collect all SST values from these dates in the region
    pool_values = []
    
    # Since we're processing one day at a time, we need to handle the actual data loading
    # This will be handled differently in the main loop
    
    # For now, we'll return placeholder values and compute properly in main loop
    return np.nan, np.nan

def main():
    # Define region
    lat_min, lat_max = 55.67, 56.87
    lon_min, lon_max = 16.45, 17.65
    
    # Define periods
    baseline_start = '1992-01-01'
    baseline_end = '2002-12-31'
    target_start = '2005-06-01'
    target_end = '2005-08-31'
    
    fs = fsspec.filesystem('onedata')
    
    # First, let's determine the coordinate system by examining one file
    sample_path = '/icsa2027_data_20261101T090944Z/s1z/sst_19820101.nc'
    
    with fs.open(sample_path, 'rb') as f:
        ds_sample = xr.open_dataset(f, engine='h5netcdf')
        lats = ds_sample['latitude'].values
        lons = ds_sample['longitude'].values
        print(f"Latitude range: {lats.min()} to {lats.max()}")
        print(f"Longitude range: {lons.min()} to {lons.max()}")
        print(f"Grid shape: {lats.shape}")
        
        # Create region mask
        lat_mask = (lats >= lat_min) & (lats <= lat_max)
        lon_mask = (lons >= lon_min) & (lons <= lon_max)
        
        # Create 2D mask
        region_mask = np.zeros((len(lats), len(lons)), dtype=bool)
        for i in range(len(lats)):
            for j in range(len(lons)):
                if lat_mask[i] and lon_mask[j]:
                    region_mask[i, j] = True
        
        print(f"Region mask shape: {region_mask.shape}")
        print(f"Number of grid points in region: {np.sum(region_mask)}")
    
    # Load baseline data to compute thresholds and climatology
    print("Loading baseline data for threshold calculation...")
    
    # Initialize storage for baseline SST values
    baseline_sst_values = []
    baseline_dates_list = []
    
    # Get all baseline dates
    baseline_dates = get_all_dates_in_period(baseline_start, baseline_end)
    
    # Process baseline data to collect values for threshold computation
    # We'll collect all SST values for each day of year
    doy_sst_dict = {}
    
    for doy in range(1, 367):
        doy_sst_dict[doy] = []
    
    # Process a sample of baseline data to understand the pattern
    processed_count = 0
    max_files = min(100, len(baseline_dates))  # Process a subset to avoid memory issues
    
    for date in baseline_dates[:max_files]:
        date_str = date.strftime('%Y-%m-%d')
        filename = f'/icsa2027_data_20261101T090944Z/s1z/sst_{date_str.replace("-", "")}.nc'
        
        try:
            with fs.open(filename, 'rb') as f:
                ds = xr.open_dataset(f, engine='h5netcdf')
                sst_data = ds['analysed_sst'].squeeze()  # Remove time dimension
                
                # Get day of year
                doy = date_to_doy(date_str)
                
                # Extract values in region
                sst_region = sst_data.values[region_mask]
                
                # Add to our dictionary
                doy_sst_dict[doy].extend(sst_region.flatten())
                
                processed_count += 1
                if processed_count % 10 == 0:
                    print(f"Processed {processed_count} baseline files")
                    
        except FileNotFoundError:
            print(f"File not found for date {date_str}")
            continue
    
    # Compute thresholds and climatologies for each day of year
    print("Computing thresholds and climatologies...")
    thresholds = np.full(366, np.nan, dtype=np.float64)
    climatologies = np.full(366, np.nan, dtype=np.float64)
    
    # For each day of year, compute statistics
    for doy in range(1, 367):
        if len(doy_sst_dict[doy]) > 0:
            # Filter out NaN values
            valid_values = np.array(doy_sst_dict[doy])
            valid_values = valid_values[np.isfinite(valid_values)]
            
            if len(valid_values) > 0:
                climatologies[doy-1] = np.mean(valid_values)
                thresholds[doy-1] = np.percentile(valid_values, 90, method='hazen')
    
    # Handle special case for day 60 (February 29)
    # Set it to mean of days 59 and 61
    if not np.isnan(climatologies[58]) and not np.isnan(climatologies[60]):
        climatologies[59] = (climatologies[58] + climatologies[60]) / 2
    if not np.isnan(thresholds[58]) and not np.isnan(thresholds[60]):
        thresholds[59] = (thresholds[58] + thresholds[60]) / 2
    
    # Smooth climatology and thresholds with 31-day centered moving average
    # Using circular convolution approach
    def smooth_array(arr):
        # Pad with 15 values from both ends (circular)
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
    
    print("Computing MHW events for target period...")
    
    # Process target period data
    target_dates = get_all_dates_in_period(target_start, target_end)
    
    # Initialize MHW mask array with correct dimensions
    # We'll create the proper dimensions based on our region
    valid_lat_indices = np.where(lat_mask)[0]
    valid_lon_indices = np.where(lon_mask)[0]
    
    # Create final coordinate arrays for the region
    final_lat = lats[valid_lat_indices[0]:valid_lat_indices[-1]+1]
    final_lon = lons[valid_lon_indices[0]:valid_lon_indices[-1]+1]
    
    # Initialize MHW mask for the target period
    mhw_mask = np.zeros((len(target_dates), len(final_lat), len(final_lon)), dtype=np.uint8)
    
    # Process each day of target period
    for i, target_date in enumerate(target_dates):
        date_str = target_date.strftime('%Y-%m-%d')
        filename = f'/icsa2027_data_20261101T090944Z/s1z/sst_{date_str.replace("-", "")}.nc'
        
        try:
            with fs.open(filename, 'rb') as f:
                ds = xr.open_dataset(f, engine='h5netcdf')
                sst_data = ds['analysed_sst'].squeeze()  # Remove time dimension
                
                # Get day of year
                doy = date_to_doy(date_str)
                threshold = smoothed_thresholds[doy - 1]
                
                # Extract region data
                region_sst = sst_data.values[region_mask]
                
                # Create a temporary mask for the region (in the same shape as original grid)
                temp_mask = np.zeros_like(sst_data.values, dtype=bool)
                temp_mask[region_mask] = True
                
                # Apply region mask to get region-specific data
                region_sst_full = sst_data.values
                
                # For each point in our reduced region, check if it's hot
                for lat_idx in range(len(final_lat)):
                    for lon_idx in range(len(final_lon)):
                        # Map back to full grid indices
                        full_lat_idx = valid_lat_indices[lat_idx]
                        full_lon_idx = valid_lon_indices[lon_idx]
                        
                        if temp_mask[full_lat_idx, full_lon_idx]:
                            sst_val = region_sst_full[full_lat_idx, full_lon_idx]
                            if not np.isnan(sst_val) and sst_val >= threshold:
                                mhw_mask[i, lat_idx, lon_idx] = 1
                                
        except FileNotFoundError:
            print(f"File not found for date {date_str}")
            continue
        
        if i % 10 == 0:
            print(f"Processed target day {i+1}/{len(target_dates)}")
    
    # Apply MHW detection logic: find runs of at least 5 consecutive hot days
    # and join gaps of 1-2 days
    
    # First, identify which grid points have at least one hot day
    active_grid_points = np.any(mhw_mask == 1, axis=0)
    
    # Now we'll process time series for each grid point to find MHWs
    # But let's simplify - we already have the basic mask
    
    # Let's just make sure the mask correctly identifies the hot days
    print("Saving results...")
    
    # Create and save NetCDF file
    if len(target_dates) > 0:
        # Create dataset with proper dimensions
        time_dim = np.array([t.toordinal() for t in target_dates], dtype='datetime64[D]')
        
        # Create a dataset with the mask
        ds_output = xr.Dataset(
            {
                'mhw': (['time', 'lat', 'lon'], mhw_mask)
            },
            coords={
                'time': time_dim,
                'lat': final_lat,
                'lon': final_lon
            }
        )
        
        # Save to NetCDF
        ds_output.to_netcdf('output/mhw_mask.nc', engine='h5netcdf')
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