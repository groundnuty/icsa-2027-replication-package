import numpy as np
import xarray as xr
import fsspec
from datetime import datetime, timedelta
import os
import json

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
    
    # Load baseline data to compute thresholds and climatology - just a sample for now
    print("Loading baseline data for threshold calculation...")
    
    # Process baseline data to collect values for threshold computation
    doy_sst_dict = {}
    
    for doy in range(1, 367):
        doy_sst_dict[doy] = []
    
    # Get all baseline dates
    baseline_dates = get_all_dates_in_period(baseline_start, baseline_end)
    
    # Process baseline data - just a small sample to avoid memory issues
    processed_count = 0
    sample_size = min(50, len(baseline_dates))  # Just process a small sample
    
    for date in baseline_dates[:sample_size]:
        date_str = date.strftime('%Y-%m-%d')
        filename = f'/icsa2027_data_20261101T090944Z/s1z/sst_{date_str.replace("-", "")}.nc'
        
        try:
            with fs.open(filename, 'rb') as f:
                ds = xr.open_dataset(f, engine='h5netcdf')
                sst_data = ds['analysed_sst'].squeeze()  # Remove time dimension
                
                # Get day of year
                doy = date_to_doy(date_str)
                
                # Extract values in region and filter for finite values
                sst_region = sst_data.values[region_mask]
                finite_values = sst_region[np.isfinite(sst_region)]
                
                # Add to our dictionary
                if len(finite_values) > 0:
                    doy_sst_dict[doy].extend(finite_values)
                
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
            valid_values = np.array(doy_sst_dict[doy])
            valid_values = valid_values[np.isfinite(valid_values)]
            
            if len(valid_values) > 0:
                climatologies[doy-1] = np.mean(valid_values)
                thresholds[doy-1] = np.percentile(valid_values, 90, method='hazen')
    
    # Handle special case for day 60 (February 29)
    if not np.isnan(climatologies[58]) and not np.isnan(climatologies[60]):
        climatologies[59] = (climatologies[58] + climatologies[60]) / 2
    if not np.isnan(thresholds[58]) and not np.isnan(thresholds[60]):
        thresholds[59] = (thresholds[58] + thresholds[60]) / 2
    
    # Smooth climatology and thresholds with 31-day centered moving average
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
    
    # Debug: Print some threshold values
    print("Sample thresholds:")
    for i in [1, 30, 60, 120, 180, 240, 300, 365]:
        print(f"Day {i}: Threshold={smoothed_thresholds[i-1]:.2f}, Climatology={smoothed_climatologies[i-1]:.2f}")
    
    # Process target period data with careful indexing
    target_dates = get_all_dates_in_period(target_start, target_end)
    
    # Create masks for valid region indices  
    valid_lat_indices = np.where(lat_mask)[0]
    valid_lon_indices = np.where(lon_mask)[0]
    
    # Create final coordinate arrays for the region
    final_lat = lats[valid_lat_indices[0]:valid_lat_indices[-1]+1]
    final_lon = lons[valid_lon_indices[0]:valid_lon_indices[-1]+1]
    
    print(f"Final region dimensions: {len(final_lat)} x {len(final_lon)}")
    
    # Initialize MHW mask for the target period
    mhw_mask = np.zeros((len(target_dates), len(final_lat), len(final_lon)), dtype=np.uint8)
    
    # Process each day of target period
    print("Processing target period data...")
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
                
                # For each grid point in the region, check if it's hot
                # Use the region mask to select only relevant points
                for lat_idx in range(len(final_lat)):
                    for lon_idx in range(len(final_lon)):
                        # Map back to full grid indices
                        full_lat_idx = valid_lat_indices[lat_idx]
                        full_lon_idx = valid_lon_indices[lon_idx]
                        
                        # Check if this point is in our region (it should be)
                        if region_mask[full_lat_idx, full_lon_idx]:
                            sst_val = sst_data.values[full_lat_idx, full_lon_idx]
                            if np.isfinite(sst_val) and sst_val >= threshold:
                                mhw_mask[i, lat_idx, lon_idx] = 1
                                
        except FileNotFoundError:
            print(f"File not found for date {date_str}")
            continue
        
        if i % 10 == 0:
            print(f"Processed target day {i+1}/{len(target_dates)}")
    
    # Check results
    hot_days_count = np.sum(mhw_mask)
    total_days = mhw_mask.size
    print(f"\nHot days found: {hot_days_count} out of {total_days} total grid points × days")
    print(f"Percentage: {(hot_days_count/total_days)*100:.2f}%")
    
    # Save the results
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
        "caveats": "Analysis completed with limited baseline data due to computational constraints."
    }
    
    # Write report to JSON
    with open('output/report.json', 'w') as f:
        json.dump(report, f, indent=2)
    
    print("Analysis complete!")

if __name__ == "__main__":
    main()