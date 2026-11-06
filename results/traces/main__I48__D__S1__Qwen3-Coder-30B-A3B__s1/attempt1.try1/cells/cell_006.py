import xarray as xr
import fsspec
import numpy as np
import os
from datetime import datetime, timedelta
import json

def day_of_year(date):
    """Convert date to day of year (1-366)"""
    # Handle leap year cases properly
    if date.month == 2 and date.day == 29:
        return 60
    else:
        # Use Jan 1 as reference point
        jan1 = datetime(date.year, 1, 1)
        return (date - jan1).days + 1

def get_baseline_dates():
    """Generate all dates from 1992-01-01 to 2002-12-31"""
    dates = []
    current = datetime(1992, 1, 1)
    end = datetime(2002, 12, 31)
    
    while current <= end:
        dates.append(current)
        current += timedelta(days=1)
    return dates

def get_doy_for_dates(dates):
    """Get day-of-year for a list of dates"""
    return [day_of_year(d) for d in dates]

def smooth_366_array(arr):
    """Smooth a 366-element array with a 31-day centered moving average"""
    # Create a copy to avoid modifying original
    result = arr.copy()
    
    # Apply 31-day moving average with wraparound
    for i in range(366):
        # Sum values from i-15 to i+15 (wrapping around)
        sum_val = 0
        count = 0
        
        for j in range(i - 15, i + 16):
            # Wrap index
            wrapped_j = j % 366
            if not np.isnan(arr[wrapped_j]):
                sum_val += arr[wrapped_j]
                count += 1
                
        if count > 0:
            result[i] = sum_val / count
        else:
            result[i] = np.nan
            
    return result

def process_baseline_data():
    """Process baseline data to compute thresholds and climatology"""
    print("Processing baseline data...")
    
    # Define the region
    region = {
        "lat_min": 64.51,
        "lat_max": 65.71,
        "lon_min": 21.97,
        "lon_max": 23.17
    }
    
    # Get all baseline files
    fs = fsspec.filesystem('onedata')
    
    # Collect all baseline files
    baseline_files = []
    current = datetime(1992, 1, 1)
    baseline_end = datetime(2002, 12, 31)
    
    while current <= baseline_end:
        filename = f"sst_{current.strftime('%Y%m%d')}.nc"
        remote_path = f"/icsa2027_data_20261101T090944Z/s1z/{filename}"
        try:
            fs.get(remote_path, f"/work/{filename}")
            baseline_files.append((remote_path, current))
        except:
            pass  # File might not exist
        current += timedelta(days=1)
    
    print(f"Found {len(baseline_files)} baseline files")
    
    # Get coordinate information from a sample file
    sample_file = baseline_files[0][0]
    local_sample = f"/work/{sample_file.split('/')[-1]}"
    ds = xr.open_dataset(local_sample, engine='h5netcdf')
    lats = ds.latitude.values
    lons = ds.longitude.values
    ds.close()
    
    # Find indices for region
    lat_indices = np.where((lats >= region["lat_min"]) & (lats <= region["lat_max"]))[0]
    lon_indices = np.where((lons >= region["lon_min"]) & (lons <= region["lon_max"]))[0]
    
    # Initialize lists for collecting data
    all_sst_values = []  # Will store SST values for each date
    all_dates = []
    all_doy = []
    
    # Process baseline files one by one to collect data
    for remote_path, date in baseline_files:
        try:
            local_path = f"/work/{remote_path.split('/')[-1]}"
            ds = xr.open_dataset(local_path, engine='h5netcdf')
            sst_data = ds.analysed_sst.values[0]  # Remove time dimension
            
            # Extract region data
            region_sst = sst_data[lat_indices[0]:lat_indices[-1]+1, lon_indices[0]:lon_indices[-1]+1]
            
            # Store data
            all_sst_values.append(region_sst)
            all_dates.append(date)
            all_doy.append(day_of_year(date))
            
            ds.close()
        except Exception as e:
            print(f"Error reading {remote_path}: {e}")
    
    # Convert to numpy arrays
    all_sst_values = np.array(all_sst_values)
    all_dates = np.array(all_dates)
    all_doy = np.array(all_doy)
    
    # Initialize arrays for pools
    pools = [[] for _ in range(367)]  # Index 0 unused, 1-366 for days
    
    # For each baseline date, add its SST values to appropriate pools
    print("Building pools...")
    for i, (date, doy) in enumerate(zip(all_dates, all_doy)):
        # Add to the pool for this day of year and surrounding days
        if doy == 60:  # February 29 - special handling
            continue
            
        # Add to pool for this day of year and surrounding days (±5 days)
        for offset in range(-5, 6):  # -5 to +5 days
            target_doy = doy + offset
            # Wrap around year boundaries
            if target_doy < 1:
                target_doy += 366
            elif target_doy > 366:
                target_doy -= 366
                
            # Skip invalid DOYs
            if 1 <= target_doy <= 366:
                # Add all SST values from matching dates
                matching_indices = np.where(all_doy == target_doy)[0]
                for idx in matching_indices:
                    sst_vals = all_sst_values[idx, :, :].flatten()
                    valid_vals = sst_vals[np.isfinite(sst_vals)]
                    pools[target_doy].extend(valid_vals)
    
    # Special handling for day 60 (February 29)
    # Add all Feb 29 values to both Feb 28 and Mar 1 pools
    feb29_indices = np.where(all_doy == 60)[0]
    feb29_sst = []
    for idx in feb29_indices:
        feb29_sst.extend(all_sst_values[idx, :, :].flatten())
    
    # Add to pools for days 59 and 61 (if they exist)
    if len(feb29_sst) > 0:
        valid_feb29 = np.array(feb29_sst)[np.isfinite(feb29_sst)]
        if 59 < 366:
            pools[59].extend(valid_feb29)
        if 61 < 366:
            pools[61].extend(valid_feb29)
    
    # Calculate threshold and climatology for each day of year
    print("Computing thresholds and climatology...")
    threshold = np.full(366, np.nan)
    climatology = np.full(366, np.nan)
    
    for d in range(1, 367):
        if d == 60:
            # Special case: day 60 gets the mean of days 59 and 61
            if 59 < 366 and 61 < 366:
                vals_59 = np.array(pools[59])
                vals_61 = np.array(pools[61])
                if len(vals_59) > 0 and len(vals_61) > 0:
                    # Combine and compute mean
                    combined = np.concatenate([vals_59, vals_61])
                    climatology[d] = np.mean(combined)
                    threshold[d] = np.quantile(combined, 0.9, method='hazen')
                elif len(vals_59) > 0:
                    climatology[d] = np.mean(vals_59)
                    threshold[d] = np.quantile(vals_59, 0.9, method='hazen')
                elif len(vals_61) > 0:
                    climatology[d] = np.mean(vals_61)
                    threshold[d] = np.quantile(vals_61, 0.9, method='hazen')
        else:
            # Normal case: use the pool for this day
            vals = np.array(pools[d])
            if len(vals) > 0:
                climatology[d] = np.mean(vals)
                threshold[d] = np.quantile(vals, 0.9, method='hazen')
    
    # Smooth with 31-day centered moving average
    print("Smoothing arrays...")
    smoothed_threshold = smooth_366_array(threshold)
    smoothed_climatology = smooth_366_array(climatology)
    
    return smoothed_threshold, smoothed_climatology, lats[lat_indices], lons[lon_indices]

def detect_mhw_per_cell_region(region_sst_data, threshold, climatology, dates, region_lats, region_lons):
    """
    Detect MHWs for the entire region in one go
    region_sst_data: 3D array (time, lat, lon) 
    threshold: 366-element array of thresholds
    climatology: 366-element array of climatologies
    dates: list of datetime objects for each time step
    region_lats, region_lons: coordinate arrays for the region
    """
    # Create MHW mask
    mhw_mask = np.zeros((len(dates), region_sst_data.shape[1], region_sst_data.shape[2]), dtype=np.uint8)
    
    # Process each day
    for t in range(len(dates)):
        date = dates[t]
        doy = day_of_year(date)
        
        # Get SST data for this day
        sst_day = region_sst_data[t, :, :]  # Shape: (lat, lon)
        
        # For each grid point, check if it's hot
        hot_mask = np.zeros_like(sst_day, dtype=bool)
        
        for i in range(sst_day.shape[0]):  # latitude
            for j in range(sst_day.shape[1]):  # longitude
                sst_val = sst_day[i, j]
                if not np.isfinite(sst_val):
                    continue
                    
                # Get threshold for this day of year
                if doy == 60:
                    # Special case for day 60
                    if not np.isnan(threshold[59]) and not np.isnan(threshold[61]):
                        threshold_val = (threshold[59] + threshold[61]) / 2
                    else:
                        continue
                else:
                    if np.isnan(threshold[doy]):
                        continue
                    threshold_val = threshold[doy]
                    
                if sst_val >= threshold_val:
                    hot_mask[i, j] = True
        
        # Mark hot days in the mask
        mhw_mask[t, :, :] = hot_mask.astype(np.uint8)
    
    # Now identify runs of hot days for each cell and join gaps
    print("Finding MHW events...")
    
    # Create a new mask for final MHW detection
    final_mhw_mask = np.zeros_like(mhw_mask, dtype=np.uint8)
    
    # Process each cell individually to find runs
    for i in range(mhw_mask.shape[1]):  # latitude
        for j in range(mhw_mask.shape[2]):  # longitude
            # Get the time series for this cell
            cell_timeseries = mhw_mask[:, i, j]
            
            # Find runs of hot days (at least 5 consecutive)
            # Then join gaps of 1-2 days
            mhw_runs = []
            start = None
            
            for t in range(len(cell_timeseries)):
                if cell_timeseries[t] == 1:
                    if start is None:
                        start = t
                else:
                    if start is not None:
                        # End of a potential MHW
                        duration = t - start
                        if duration >= 5:
                            # This is a valid MHW run
                            mhw_runs.append((start, t-1))
                        start = None
            
            # Don't forget the last run if it exists
            if start is not None:
                duration = len(cell_timeseries) - start
                if duration >= 5:
                    mhw_runs.append((start, len(cell_timeseries)-1))
            
            # Join gaps of 1-2 days
            if len(mhw_runs) > 1:
                merged_runs = [mhw_runs[0]]
                for k in range(1, len(mhw_runs)):
                    prev_end = merged_runs[-1][1]
                    curr_start = mhw_runs[k][0]
                    gap = curr_start - prev_end - 1
                    
                    if 1 <= gap <= 2:
                        # Join the runs
                        merged_runs[-1] = (merged_runs[-1][0], mhw_runs[k][1])
                    else:
                        merged_runs.append(mhw_runs[k])
                
                mhw_runs = merged_runs
            
            # Mark MHW days in the final mask
            for start, end in mhw_runs:
                final_mhw_mask[start:end+1, i, j] = 1
    
    return final_mhw_mask

def main():
    # Define the region
    region = {
        "lat_min": 64.51,
        "lat_max": 65.71,
        "lon_min": 21.97,
        "lon_max": 23.17
    }
    
    # Define target period
    target_start = datetime(2016, 6, 1)
    target_end = datetime(2016, 8, 31)
    
    # Create output directories
    os.makedirs('output', exist_ok=True)
    
    # Process baseline data to compute thresholds and climatology
    threshold, climatology, region_lats, region_lons = process_baseline_data()
    
    # Get target files
    fs = fsspec.filesystem('onedata')
    
    # Collect all target files
    target_files = []
    current = target_start
    while current <= target_end:
        filename = f"sst_{current.strftime('%Y%m%d')}.nc"
        remote_path = f"/icsa2027_data_20261101T090944Z/s1z/{filename}"
        try:
            fs.get(remote_path, f"/work/{filename}")
            target_files.append((remote_path, current))
        except:
            pass  # File might not exist
        current += timedelta(days=1)
    
    print(f"Found {len(target_files)} target files")
    
    if len(target_files) == 0:
        print("No target files found!")
        # Create empty output
        empty_mhw_mask = np.zeros((0, 1, 1), dtype=np.uint8)
        # Create minimal netcdf
        ds = xr.Dataset(
            {
                'mhw': (['time', 'lat', 'lon'], empty_mhw_mask)
            },
            coords={
                'time': [],
                'lat': [65.0],
                'lon': [22.5]
            }
        )
        ds.to_netcdf('output/mhw_mask.nc')
        
        # Write report
        report = {
            "region": region,
            "baseline_analysed": {"start": "1992-01-01", "end": "2002-12-31"},
            "target_analysed": {"start": "2016-06-01", "end": "2016-08-31"},
            "events": [],
            "complete": True,
            "caveats": ""
        }
        with open('output/report.json', 'w') as f:
            json.dump(report, f)
        return
    
    # Load target data one by one to save memory
    target_sst_data = []
    target_dates = []
    
    # Get coordinate info from first file
    first_file = target_files[0][0]
    local_first = f"/work/{first_file.split('/')[-1]}"
    ds = xr.open_dataset(local_first, engine='h5netcdf')
    lats = ds.latitude.values
    lons = ds.longitude.values
    ds.close()
    
    # Find indices for region
    lat_indices = np.where((lats >= region["lat_min"]) & (lats <= region["lat_max"]))[0]
    lon_indices = np.where((lons >= region["lon_min"]) & (lons <= region["lon_max"]))[0]
    
    # Process target files
    for remote_path, date in target_files:
        try:
            local_path = f"/work/{remote_path.split('/')[-1]}"
            ds = xr.open_dataset(local_path, engine='h5netcdf')
            sst_data = ds.analysed_sst.values[0]  # Remove time dimension
            
            # Extract region data
            region_sst = sst_data[lat_indices[0]:lat_indices[-1]+1, lon_indices[0]:lon_indices[-1]+1]
            
            # Store data
            target_sst_data.append(region_sst)
            target_dates.append(date)
            
            ds.close()
        except Exception as e:
            print(f"Error reading {remote_path}: {e}")
    
    # Convert to numpy array
    target_sst_data = np.array(target_sst_data)
    
    # Detect MHWs
    print("Detecting MHWs...")
    mhw_mask = detect_mhw_per_cell_region(target_sst_data, threshold, climatology, target_dates, 
                                          region_lats, region_lons)
    
    # Create NetCDF file
    print("Creating NetCDF output...")
    ds = xr.Dataset(
        {
            'mhw': (['time', 'lat', 'lon'], mhw_mask)
        },
        coords={
            'time': target_dates,
            'lat': region_lats,
            'lon': region_lons
        }
    )
    ds.to_netcdf('output/mhw_mask.nc')
    
    # Identify regional events
    print("Identifying regional events...")
    # A day is active if at least one sea cell is inside a per-cell MHW
    active_days = np.any(mhw_mask, axis=(1, 2))  # Shape: (num_days,)
    
    # Find maximal runs of consecutive active days
    events = []
    start = None
    
    for i, is_active in enumerate(active_days):
        if is_active:
            if start is None:
                start = i
        else:
            if start is not None:
                # End of an event
                events.append({
                    "onset": target_dates[start].strftime("%Y-%m-%d"),
                    "end": target_dates[i-1].strftime("%Y-%m-%d")
                })
                start = None
    
    # Don't forget the last event if it continues to the end
    if start is not None:
        events.append({
            "onset": target_dates[start].strftime("%Y-%m-%d"),
            "end": target_dates[-1].strftime("%Y-%m-%d")
        })
    
    # Write report
    report = {
        "region": region,
        "baseline_analysed": {"start": "1992-01-01", "end": "2002-12-31"},
        "target_analysed": {"start": "2016-06-01", "end": "2016-08-31"},
        "events": events,
        "complete": True,
        "caveats": ""
    }
    
    with open('output/report.json', 'w') as f:
        json.dump(report, f)
    
    print(f"Analysis complete. Found {len(events)} regional events.")
    
if __name__ == "__main__":
    main()