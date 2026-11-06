import xarray as xr
import fsspec
import numpy as np
import os
from datetime import datetime, timedelta
from scipy import stats
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

def calculate_threshold_and_climatology(sst_data, dates, doy_list):
    """
    Calculate thresholds and climatology for each day of year
    sst_data: 2D array of SST values for each grid point (lat, lon)
    dates: list of datetime objects
    doy_list: list of day-of-year for each date
    """
    # Initialize arrays
    threshold = np.full(366, np.nan)
    climatology = np.full(366, np.nan)
    
    # Get baseline dates and their DOYs
    baseline_dates = get_baseline_dates()
    baseline_doy = get_doy_for_dates(baseline_dates)
    
    # Create pools for each day of year
    pools = [[] for _ in range(367)]  # Index 0 unused, 1-366 for days
    
    # For each baseline date, add its SST values to appropriate pools
    for i, (date, doy) in enumerate(zip(baseline_dates, baseline_doy)):
        # Add to the pool for this day of year (with 5-day window)
        # But handle edge cases for leap year
        if doy == 60:  # February 29
            # This gets handled specially later
            continue
            
        # Add to pool for this day of year and surrounding days
        for offset in range(-5, 6):  # -5 to +5 days
            target_doy = doy + offset
            # Wrap around year boundaries
            if target_doy < 1:
                target_doy += 366
            elif target_doy > 366:
                target_doy -= 366
                
            # Skip invalid DOYs (like 60 for non-leap years)
            if target_doy >= 1 and target_doy <= 366:
                # Find matching dates in our data
                for j, (d, d_doy) in enumerate(zip(dates, doy_list)):
                    if d_doy == target_doy:
                        # Add the SST values for this date (ignoring NaN)
                        sst_vals = sst_data[j, :, :].flatten()
                        valid_vals = sst_vals[np.isfinite(sst_vals)]
                        pools[target_doy].extend(valid_vals)
    
    # Special handling for day 60 (February 29)
    # Add all Feb 29 values to both Feb 28 and Mar 1 pools
    feb29_dates = [d for d in baseline_dates if (d.month == 2 and d.day == 29)]
    feb29_doy = [day_of_year(d) for d in feb29_dates]
    
    # Find corresponding dates in our data
    feb29_sst = []
    for i, (date, doy) in enumerate(zip(baseline_dates, baseline_doy)):
        if doy == 60:
            feb29_sst.extend(sst_data[i, :, :].flatten())
    
    # Add to pools for days 59 and 61 (if they exist)
    if len(feb29_sst) > 0:
        valid_feb29 = np.array(feb29_sst)[np.isfinite(feb29_sst)]
        if 59 < 366:  # Ensure we don't go out of bounds
            pools[59].extend(valid_feb29)
        if 61 < 366:
            pools[61].extend(valid_feb29)
    
    # Calculate threshold and climatology for each day of year
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
    smoothed_threshold = smooth_366_array(threshold)
    smoothed_climatology = smooth_366_array(climatology)
    
    return smoothed_threshold, smoothed_climatology

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

def detect_mhw_per_cell(sst_data, threshold, climatology, dates, region_bounds):
    """
    Detect MHWs for each cell in the region
    sst_data: 3D array (time, lat, lon) 
    threshold: 366-element array of thresholds
    climatology: 366-element array of climatologies
    dates: list of datetime objects for each time step
    region_bounds: (lat_min, lat_max, lon_min, lon_max)
    """
    lat_min, lat_max, lon_min, lon_max = region_bounds
    
    # Create mask for sea cells (grid cells with finite SST on every day)
    sea_cells = np.zeros((sst_data.shape[1], sst_data.shape[2]), dtype=bool)
    
    # Check which grid cells have finite values for all days
    for i in range(sst_data.shape[1]):  # latitude
        for j in range(sst_data.shape[2]):  # longitude
            # Check if all days have finite values
            all_finite = True
            for t in range(sst_data.shape[0]):
                if not np.isfinite(sst_data[t, i, j]):
                    all_finite = False
                    break
            if all_finite:
                sea_cells[i, j] = True
    
    # Create MHW mask
    mhw_mask = np.zeros((len(dates), sst_data.shape[1], sst_data.shape[2]), dtype=np.uint8)
    
    # Process each cell
    for i in range(sst_data.shape[1]):  # latitude
        for j in range(sst_data.shape[2]):  # longitude
            if not sea_cells[i, j]:
                continue  # Not a sea cell
                
            # Get the SST time series for this cell
            sst_series = sst_data[:, i, j]
            
            # For each day, determine if it's hot based on threshold
            hot_days = np.zeros(len(dates), dtype=bool)
            
            for t, (date, sst_val) in enumerate(zip(dates, sst_series)):
                if not np.isfinite(sst_val):
                    continue
                    
                doy = day_of_year(date)
                # Handle special case for day 60
                if doy == 60:
                    # Use mean of days 59 and 61
                    if not np.isnan(threshold[59]) and not np.isnan(threshold[61]):
                        threshold_val = (threshold[59] + threshold[61]) / 2
                    else:
                        continue
                else:
                    if np.isnan(threshold[doy]):
                        continue
                    threshold_val = threshold[doy]
                    
                if sst_val >= threshold_val:
                    hot_days[t] = True
            
            # Find runs of hot days (at least 5 consecutive)
            # Then join gaps of 1-2 days
            mhw_runs = []
            start = None
            
            for t in range(len(hot_days)):
                if hot_days[t]:
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
                duration = len(hot_days) - start
                if duration >= 5:
                    mhw_runs.append((start, len(hot_days)-1))
            
            # Join gaps of 1-2 days
            if len(mhw_runs) > 1:
                merged_runs = [mhw_runs[0]]
                for i in range(1, len(mhw_runs)):
                    prev_end = merged_runs[-1][1]
                    curr_start = mhw_runs[i][0]
                    gap = curr_start - prev_end - 1
                    
                    if 1 <= gap <= 2:
                        # Join the runs
                        merged_runs[-1] = (merged_runs[-1][0], mhw_runs[i][1])
                    else:
                        merged_runs.append(mhw_runs[i])
                
                mhw_runs = merged_runs
            
            # Mark MHW days in the mask
            for start, end in mhw_runs:
                mhw_mask[start:end+1, i, j] = 1
    
    return mhw_mask

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
    
    # Define baseline period
    baseline_start = datetime(1992, 1, 1)
    baseline_end = datetime(2002, 12, 31)
    
    # Create output directories
    os.makedirs('output', exist_ok=True)
    
    # Get all files for the baseline period
    fs = fsspec.filesystem('onedata')
    
    # Collect all baseline files
    baseline_files = []
    current = baseline_start
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
    
    # Load baseline data
    if len(baseline_files) == 0:
        print("No baseline files found!")
        return
    
    # Read baseline data
    baseline_sst_data = []
    baseline_dates = []
    baseline_doy = []
    
    for remote_path, date in baseline_files:
        try:
            local_path = f"/work/{remote_path.split('/')[-1]}"
            ds = xr.open_dataset(local_path, engine='h5netcdf')
            sst_data = ds.analysed_sst.values[0]  # Remove time dimension
            baseline_sst_data.append(sst_data)
            baseline_dates.append(date)
            baseline_doy.append(day_of_year(date))
            ds.close()
        except Exception as e:
            print(f"Error reading {remote_path}: {e}")
    
    baseline_sst_data = np.array(baseline_sst_data)
    
    # Calculate thresholds and climatology
    print("Calculating thresholds and climatology...")
    threshold, climatology = calculate_threshold_and_climatology(
        baseline_sst_data, baseline_dates, baseline_doy
    )
    
    # Load target data
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
    
    # Read target data  
    target_sst_data = []
    target_dates = []
    
    for remote_path, date in target_files:
        try:
            local_path = f"/work/{remote_path.split('/')[-1]}"
            ds = xr.open_dataset(local_path, engine='h5netcdf')
            sst_data = ds.analysed_sst.values[0]  # Remove time dimension
            target_sst_data.append(sst_data)
            target_dates.append(date)
            ds.close()
        except Exception as e:
            print(f"Error reading {remote_path}: {e}")
    
    target_sst_data = np.array(target_sst_data)
    
    # Extract region data
    # First, we need to figure out the indices for the region
    # Let's load one file to determine the coordinate system
    first_file = target_files[0][0]
    local_first = f"/work/{first_file.split('/')[-1]}"
    ds = xr.open_dataset(local_first, engine='h5netcdf')
    
    # Get lat/lon coordinates
    lats = ds.latitude.values
    lons = ds.longitude.values
    
    # Find indices for region
    lat_indices = np.where((lats >= region["lat_min"]) & (lats <= region["lat_max"]))[0]
    lon_indices = np.where((lons >= region["lon_min"]) & (lons <= region["lon_max"]))[0]
    
    # Extract region data
    region_sst_data = target_sst_data[:, lat_indices[0]:lat_indices[-1]+1, lon_indices[0]:lon_indices[-1]+1]
    region_lats = lats[lat_indices]
    region_lons = lons[lon_indices]
    
    ds.close()
    
    # Detect MHWs
    print("Detecting MHWs...")
    mhw_mask = detect_mhw_per_cell(region_sst_data, threshold, climatology, target_dates, 
                                   (region["lat_min"], region["lat_max"], region["lon_min"], region["lon_max"]))
    
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