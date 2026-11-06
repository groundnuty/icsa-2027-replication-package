import xarray as xr
import numpy as np
import fsspec
import os
from datetime import datetime, timedelta
import calendar

# Create output directory
os.makedirs('output', exist_ok=True)

def day_of_year_from_date(date_str):
    """Convert YYYY-MM-DD to day of year (1-366)"""
    date = datetime.strptime(date_str, '%Y-%m-%d')
    return date.timetuple().tm_yday

def get_baseline_dates():
    """Generate all dates from 1992-01-01 to 2002-12-31"""
    start = datetime(1992, 1, 1)
    end = datetime(2002, 12, 31)
    dates = []
    current = start
    while current <= end:
        dates.append(current.strftime('%Y-%m-%d'))
        current += timedelta(days=1)
    return dates

def get_target_dates():
    """Generate all dates from 2013-06-01 to 2013-08-31"""
    start = datetime(2013, 6, 1)
    end = datetime(2013, 8, 31)
    dates = []
    current = start
    while current <= end:
        dates.append(current.strftime('%Y-%m-%d'))
        current += timedelta(days=1)
    return dates

def get_doy_for_dates(dates):
    """Get day-of-year for a list of dates"""
    doys = []
    for date_str in dates:
        doy = day_of_year_from_date(date_str)
        # Handle leap year special case for Feb 29
        if datetime.strptime(date_str, '%Y-%m-%d').month == 2 and datetime.strptime(date_str, '%Y-%m-%d').day == 29:
            doys.append(60)  # Feb 29 maps to day 60
        else:
            doys.append(doy)
    return doys

def smooth_with_wrapping(data):
    """Apply 31-day centered moving average with wrapping"""
    result = np.zeros_like(data)
    window_size = 31
    half_window = window_size // 2
    
    for i in range(len(data)):
        # Calculate the indices with wrapping
        indices = [(i + j - half_window) % len(data) for j in range(window_size)]
        # Take mean of valid values (ignoring NaN)
        values = [data[idx] for idx in indices if not np.isnan(data[idx])]
        if len(values) > 0:
            result[i] = np.mean(values)
        else:
            result[i] = np.nan
            
    return result

def find_sea_cells(sst_data, dates):
    """Find sea cells that have finite SST on every day of the period"""
    n_days, n_lat, n_lon = sst_data.shape
    sea_cells = np.zeros((n_lat, n_lon), dtype=bool)
    
    # For each grid cell, check if it has finite values for all days
    for i in range(n_lat):
        for j in range(n_lon):
            # Check if all days have finite SST for this cell
            cell_has_all_finite = True
            for k in range(n_days):
                if not np.isfinite(sst_data[k, i, j]):
                    cell_has_all_finite = False
                    break
            if cell_has_all_finite:
                sea_cells[i, j] = True
                
    return sea_cells

def find_hot_runs(hot_days, min_length=5):
    """Find runs of consecutive hot days with minimum length"""
    runs = []
    in_run = False
    start_idx = 0
    
    for i, is_hot in enumerate(hot_days):
        if is_hot and not in_run:
            # Start of a new run
            start_idx = i
            in_run = True
        elif not is_hot and in_run:
            # End of a run
            if i - start_idx >= min_length:
                runs.append((start_idx, i-1))
            in_run = False
            
    # Handle case where the last day is hot
    if in_run and len(hot_days) - start_idx >= min_length:
        runs.append((start_idx, len(hot_days)-1))
        
    return runs

def join_gaps(runs, max_gap=2):
    """Join consecutive runs separated by up to max_gap non-hot days"""
    if not runs:
        return runs
        
    joined = [runs[0]]
    
    for i in range(1, len(runs)):
        prev_start, prev_end = joined[-1]
        curr_start, curr_end = runs[i]
        
        # Check if gap is acceptable
        gap = curr_start - prev_end - 1
        if gap <= max_gap:
            # Join the runs
            joined[-1] = (prev_start, curr_end)
        else:
            joined.append((curr_start, curr_end))
            
    return joined

def detect_mhw_per_cell(sst_data, thresholds, climatologies, dates, sea_cells):
    """Detect MHWs for each sea cell"""
    n_days, n_lat, n_lon = sst_data.shape
    mhw_mask = np.zeros((n_days, n_lat, n_lon), dtype=np.uint8)
    
    # For each sea cell, detect MHWs
    for i in range(n_lat):
        for j in range(n_lon):
            if not sea_cells[i, j]:
                continue
                
            # Get SST time series for this cell
            cell_sst = sst_data[:, i, j]
            # Get corresponding day-of-year for each date
            cell_doys = [day_of_year_from_date(date) for date in dates]
            
            # Create hot days mask (SST >= threshold)
            hot_days = np.zeros(n_days, dtype=bool)
            for k in range(n_days):
                doy = cell_doys[k]
                if not np.isnan(thresholds[doy-1]):  # Indexing is 0-based
                    hot_days[k] = cell_sst[k] >= thresholds[doy-1]
            
            # Find runs of at least 5 consecutive hot days
            mhw_runs = find_hot_runs(hot_days, min_length=5)
            
            # Join gaps of 1-2 days
            joined_runs = join_gaps(mhw_runs, max_gap=2)
            
            # Mark MHW days in mask
            for start_day, end_day in joined_runs:
                mhw_mask[start_day:end_day+1, i, j] = 1
                
    return mhw_mask

def detect_regional_events(mhw_mask, dates):
    """Detect regional MHW events"""
    n_days, n_lat, n_lon = mhw_mask.shape
    active_days = np.any(mhw_mask, axis=(1, 2))  # Days when any sea cell is in MHW
    
    # Find runs of active days
    events = []
    in_event = False
    start_day = 0
    
    for i, is_active in enumerate(active_days):
        if is_active and not in_event:
            # Start of a new event
            start_day = i
            in_event = True
        elif not is_active and in_event:
            # End of an event
            events.append((start_day, i-1))
            in_event = False
            
    # Handle case where the last day is active
    if in_event:
        events.append((start_day, len(active_days)-1))
    
    # Convert to date strings
    formatted_events = []
    for start_idx, end_idx in events:
        onset = datetime.strptime(dates[start_idx], '%Y-%m-%d').strftime('%Y-%m-%d')
        end = datetime.strptime(dates[end_idx], '%Y-%m-%d').strftime('%Y-%m-%d')
        formatted_events.append({'onset': onset, 'end': end})
        
    return formatted_events

def load_and_process_baseline_data():
    """Load baseline data (1992-2002) and compute thresholds/climatologies"""
    # Get baseline dates
    baseline_dates = get_baseline_dates()
    baseline_doys = get_doy_for_dates(baseline_dates)
    
    print(f"Processing baseline period: {baseline_dates[0]} to {baseline_dates[-1]}")
    
    # Initialize lists to store data
    baseline_data_list = []
    processed_files = 0
    
    # Use fsspec to access the data
    fs = fsspec.filesystem('onedata')
    
    # Load baseline data
    for date_str in baseline_dates:
        filename = f'/icsa2027_data_20261101T090944Z/s1z/sst_{date_str.replace("-", "")}.nc'
        try:
            # Download file to local storage
            local_filename = f'sst_{date_str.replace("-", "")}.nc'
            fs.get(filename, local_filename)
            
            # Load data
            ds = xr.open_dataset(local_filename, engine='h5netcdf')
            baseline_data_list.append(ds['analysed_sst'].squeeze().values.astype(np.float64))
            ds.close()
            
            processed_files += 1
            if processed_files % 50 == 0:
                print(f"Processed {processed_files} baseline files...")
                
        except Exception as e:
            print(f"Error processing {filename}: {e}")
            continue
    
    if not baseline_data_list:
        raise ValueError("No baseline data could be loaded!")
    
    print(f"Successfully loaded {len(baseline_data_list)} baseline files")
    
    # Stack data
    baseline_sst = np.stack(baseline_data_list, axis=0)
    print(f"Baseline SST shape: {baseline_sst.shape}")
    
    # Compute thresholds and climatology
    print("Computing thresholds and climatology...")
    
    # Initialize arrays for thresholds and climatologies
    thresholds = np.full(366, np.nan)
    climatologies = np.full(366, np.nan)
    
    # For each day of year, collect data from baseline period
    for doy in range(1, 367):  # Days 1-366
        if doy == 60:  # Special case for Feb 29
            continue
            
        # Collect pool values for this day of year
        pool_values = []
        
        # Go through all baseline dates
        for i, (date_str, date_doy) in enumerate(zip(baseline_dates, baseline_doys)):
            if date_doy == doy:
                # Add all valid SST values for this day
                day_sst = baseline_sst[i, :, :]
                valid_sst = day_sst[np.isfinite(day_sst)]
                pool_values.extend(valid_sst)
        
        if len(pool_values) > 0:
            pool_array = np.array(pool_values, dtype=np.float64)
            thresholds[doy-1] = np.percentile(pool_array, 90, method='hazen')
            climatologies[doy-1] = np.mean(pool_array)
    
    # Handle day 60 (Feb 29) specially - average of days 59 and 61
    if not np.isnan(climatologies[58]) and not np.isnan(climatologies[60]):
        climatologies[59] = (climatologies[58] + climatologies[60]) / 2
        thresholds[59] = (thresholds[58] + thresholds[60]) / 2
    
    # Smooth with 31-day centered moving average (wrapping around year)
    smoothed_thresholds = smooth_with_wrapping(thresholds)
    smoothed_climatologies = smooth_with_wrapping(climatologies)
    
    return smoothed_thresholds, smoothed_climatologies, baseline_dates

def load_target_data():
    """Load target data (2013-06-01 to 2013-08-31)"""
    target_dates = get_target_dates()
    
    print(f"Processing target period: {target_dates[0]} to {target_dates[-1]}")
    
    # Initialize lists to store data
    target_data_list = []
    processed_files = 0
    
    # Use fsspec to access the data
    fs = fsspec.filesystem('onedata')
    
    # Load target data
    for date_str in target_dates:
        filename = f'/icsa2027_data_20261101T090944Z/s1z/sst_{date_str.replace("-", "")}.nc'
        try:
            # Download file to local storage
            local_filename = f'sst_{date_str.replace("-", "")}.nc'
            fs.get(filename, local_filename)
            
            # Load data
            ds = xr.open_dataset(local_filename, engine='h5netcdf')
            target_data_list.append(ds['analysed_sst'].squeeze().values.astype(np.float64))
            ds.close()
            
            processed_files += 1
            if processed_files % 50 == 0:
                print(f"Processed {processed_files} target files...")
                
        except Exception as e:
            print(f"Error processing {filename}: {e}")
            continue
    
    if not target_data_list:
        raise ValueError("No target data could be loaded!")
    
    print(f"Successfully loaded {len(target_data_list)} target files")
    
    # Stack data
    target_sst = np.stack(target_data_list, axis=0)
    print(f"Target SST shape: {target_sst.shape}")
    
    return target_sst, target_dates

def main():
    # Define region bounds
    lat_min, lat_max = 64.39, 65.59
    lon_min, lon_max = 23.41, 24.61
    
    print("Starting MHW analysis...")
    
    try:
        # Step 1: Load and process baseline data
        thresholds, climatologies, baseline_dates = load_and_process_baseline_data()
        
        # Step 2: Load target data
        target_sst, target_dates = load_target_data()
        
        # Step 3: Get coordinate info from first file
        fs = fsspec.filesystem('onedata')
        first_filename = f'/icsa2027_data_20261101T090944Z/s1z/sst_{target_dates[0].replace("-", "")}.nc'
        fs.get(first_filename, f'sst_{target_dates[0].replace("-", "")}.nc')
        first_ds = xr.open_dataset(f'sst_{target_dates[0].replace("-", "")}.nc', engine='h5netcdf')
        lats = first_ds['latitude'].values
        lons = first_ds['longitude'].values
        first_ds.close()
        
        # Step 4: Filter coordinates to our region
        lat_mask = (lats >= lat_min) & (lats <= lat_max)
        lon_mask = (lons >= lon_min) & (lons <= lon_max)
        
        lat_indices = np.where(lat_mask)[0]
        lon_indices = np.where(lon_mask)[0]
        
        if len(lat_indices) == 0 or len(lon_indices) == 0:
            raise ValueError("No grid cells found in the specified region!")
        
        # Extract region data
        region_lats = lats[lat_indices]
        region_lons = lons[lon_indices]
        
        # Adjust SST data to region
        region_sst = target_sst[:, lat_indices, :][:, :, lon_indices]
        print(f"Region dimensions: {region_lats.shape} x {region_lons.shape}")
        
        # Step 5: Find sea cells (cells with finite SST on every day)
        print("Finding sea cells...")
        sea_cells = find_sea_cells(region_sst, target_dates)
        print(f"Number of sea cells: {np.sum(sea_cells)}")
        
        # Step 6: Detect MHWs per cell
        print("Detecting MHWs per cell...")
        mhw_mask = detect_mhw_per_cell(region_sst, thresholds, climatologies, target_dates, sea_cells)
        
        # Step 7: Detect regional events
        print("Detecting regional events...")
        events = detect_regional_events(mhw_mask, target_dates)
        
        # Step 8: Write NetCDF output
        print("Writing NetCDF output...")
        # Create a new dataset with the mhw mask
        ds_output = xr.Dataset(
            {
                'mhw': (['time', 'lat', 'lon'], mhw_mask)
            },
            coords={
                'time': target_dates,
                'lat': region_lats,
                'lon': region_lons
            }
        )
        
        # Set proper attributes
        ds_output['mhw'].attrs = {'units': 'binary', 'long_name': 'Marine Heat Wave indicator'}
        
        # Save to file
        ds_output.to_netcdf('output/mhw_mask.nc')
        print("NetCDF file saved.")
        
        # Step 9: Write report
        print("Writing report...")
        report = {
            "region": {
                "lat_min": float(lat_min),
                "lat_max": float(lat_max),
                "lon_min": float(lon_min),
                "lon_max": float(lon_max)
            },
            "baseline_analysed": {
                "start": "1992-01-01",
                "end": "2002-12-31"
            },
            "target_analysed": {
                "start": "2013-06-01",
                "end": "2013-08-31"
            },
            "events": events,
            "complete": True,
            "caveats": ""
        }
        
        import json
        with open('output/report.json', 'w') as f:
            json.dump(report, f, indent=2)
        
        print("Analysis complete.")
        print(f"Found {len(events)} regional MHW events.")
        
    except Exception as e:
        print(f"Error in main execution: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()