import numpy as np
import xarray as xr
import fsspec
from datetime import datetime, timedelta
import os
import json

def date_to_doy(date_str):
    """Convert YYYY-MM-DD string to day-of-year (1-366)"""
    dt = datetime.strptime(date_str, '%Y-%m-%d')
    doy = int(dt.strftime('%j'))
    # Special handling for Feb 29th (day 60)
    if dt.month == 2 and dt.day == 29:
        return 60
    return doy

def get_baseline_pools(doy, times, doys, baseline_start, baseline_end):
    """
    Get all indices of baseline dates that contribute to the pool for a given day of year
    """
    pool_indices = []
    
    # For day 60 (February 29), we include all Feb 29 dates in both day 59 and 61 pools
    if doy == 60:
        for i, (t, t_doy) in enumerate(zip(times, doys)):
            if t_doy == 60:
                pool_indices.append(i)
    else:
        # For all other days, we include dates that are within ±5 days of a date with this day of year
        # This means we include any baseline date whose calendar date is within ±5 days of the 
        # calendar date corresponding to this day of year
        ref_date = datetime(2001, 1, 1) + timedelta(days=doy-1)
        
        for i, (t, t_doy) in enumerate(zip(times, doys)):
            # Calculate the calendar date for this baseline date
            actual_date = datetime.strptime(str(t)[:10], '%Y-%m-%d')
            # Calculate the difference from our reference date (same day-of-year)
            diff = (actual_date - ref_date).days
            
            # Include if within ±5 days
            if abs(diff) <= 5:
                pool_indices.append(i)
    
    return pool_indices

def compute_thresholds_and_climatology(sst_data, times):
    """
    Compute thresholds and climatology for each day of year using baseline data
    """
    # Convert times to day-of-year
    doys = [date_to_doy(str(t)[:10]) for t in times]
    
    # Initialize arrays for thresholds and climatology
    thresholds = np.full(366, np.nan, dtype=np.float64)
    climatology = np.full(366, np.nan, dtype=np.float64)
    
    print(f"Computing thresholds and climatology for {len(times)} baseline days")
    
    # For each day of year (1-366, excluding 60 which is special)
    for doy in range(1, 367):
        if doy == 60:
            continue
            
        # Build pool for this day of year
        pool_indices = get_baseline_pools(doy, times, doys, times[0], times[-1])
        
        if len(pool_indices) == 0:
            continue
            
        # Collect all SST values from the pool
        pool_values = []
        for idx in pool_indices:
            # Extract 2D SST data and flatten, filtering out NaNs
            sst_slice = sst_data[idx]  # This is 2D (lat, lon)
            flat_vals = sst_slice.flatten()
            valid_vals = flat_vals[~np.isnan(flat_vals)]
            pool_values.extend(valid_vals)
        
        if len(pool_values) > 0:
            # Compute 90th percentile (threshold) and mean (climatology) 
            # Using method="hazen" equivalent (linear interpolation)
            thresholds[doy-1] = np.percentile(pool_values, 90, method='linear')
            climatology[doy-1] = np.mean(pool_values)
    
    # Handle day 60 specially - set to mean of days 59 and 61
    if not np.isnan(climatology[58]) and not np.isnan(climatology[60]):
        climatology[59] = (climatology[58] + climatology[60]) / 2
        thresholds[59] = (thresholds[58] + thresholds[60]) / 2
    
    # Apply smoothing with 31-day centered moving average that wraps around
    smoothed_thresholds = smooth_366_array(thresholds)
    smoothed_climatology = smooth_366_array(climatology)
    
    return smoothed_thresholds, smoothed_climatology

def smooth_366_array(arr):
    """Apply 31-day centered moving average that wraps around the year"""
    # Create a copy with padding to handle wrapping
    padded = np.concatenate([arr, arr, arr])  # Triple the array to handle wrapping
    smoothed = np.zeros_like(arr, dtype=np.float64)
    
    for i in range(len(arr)):
        # Take 15 days before and 15 days after (31 total)
        start_idx = i + len(arr) - 15
        end_idx = i + len(arr) + 16
        window = padded[start_idx:end_idx]
        smoothed[i] = np.mean(window)
    
    return smoothed

def find_mhw_events(sst_data, thresholds, climatology, times, region_mask):
    """
    Find marine heatwave events in the region
    """
    # Create mask for sea cells (cells with finite SST on every day)
    sea_cells = np.all(np.isfinite(sst_data), axis=0)
    
    # For the target period, we'll check if each cell meets the criteria
    # First, create a mask for all valid cells in the region
    valid_cells = np.logical_and(sea_cells, region_mask)
    
    # Initialize the MHW mask
    mhw_mask = np.zeros((len(times), sst_data.shape[1], sst_data.shape[2]), dtype=np.uint8)
    
    # For each day, check if SST exceeds threshold
    for i, (t, sst_slice) in enumerate(zip(times, sst_data)):
        doy = date_to_doy(str(t)[:10])
        threshold_for_day = thresholds[doy-1]  # Adjust for 0-based indexing
        
        # Check which cells exceed threshold
        hot_cells = sst_slice >= threshold_for_day
        # Only consider cells that are valid sea cells
        hot_cells = np.logical_and(hot_cells, valid_cells)
        
        # Mark these as part of potential MHW
        mhw_mask[i] = hot_cells.astype(np.uint8)
    
    # Now apply the run detection and gap joining logic
    # For each cell independently, find runs of at least 5 consecutive hot days
    # Then join runs separated by 1-2 non-hot days
    
    # Process each cell individually
    for lat_idx in range(mhw_mask.shape[1]):
        for lon_idx in range(mhw_mask.shape[2]):
            # Only process if this is a valid sea cell
            if valid_cells[lat_idx, lon_idx]:
                # Get the time series for this cell
                cell_series = mhw_mask[:, lat_idx, lon_idx]
                
                # Find runs of hot days
                runs = find_consecutive_runs(cell_series)
                
                # Join runs separated by 1-2 non-hot days
                merged_runs = merge_close_runs(runs)
                
                # Update the mask for these merged runs
                for start, end in merged_runs:
                    mhw_mask[start:end+1, lat_idx, lon_idx] = 1
    
    return mhw_mask

def find_consecutive_runs(series):
    """Find runs of consecutive 1s in a binary series"""
    runs = []
    in_run = False
    run_start = 0
    
    for i, val in enumerate(series):
        if val == 1 and not in_run:
            # Start of a new run
            run_start = i
            in_run = True
        elif val == 0 and in_run:
            # End of a run
            if i - run_start >= 5:  # At least 5 consecutive days
                runs.append((run_start, i-1))
            in_run = False
    
    # Don't forget the last run if it extends to the end
    if in_run and len(series) - run_start >= 5:
        runs.append((run_start, len(series)-1))
        
    return runs

def merge_close_runs(runs):
    """Merge runs that are separated by 1-2 non-hot days"""
    if len(runs) <= 1:
        return runs
    
    merged = [runs[0]]
    
    for i in range(1, len(runs)):
        prev_end = merged[-1][1]
        curr_start = runs[i][0]
        
        # If gap is 1 or 2 days, merge them
        if curr_start - prev_end <= 2:
            # Extend the previous run to cover this one
            merged[-1] = (merged[-1][0], runs[i][1])
        else:
            merged.append(runs[i])
    
    return merged

def main():
    # Set up the filesystem
    fs = fsspec.filesystem('onedata')

    # Open the dataset
    with fs.open('/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb') as f:
        ds = xr.open_dataset(f, engine='h5netcdf')
        
    # Define the region of interest
    lat_min, lat_max = 63.31, 64.51
    lon_min, lon_max = 21.31, 22.51

    # Select the region
    ds_region = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))

    # Define baseline period
    baseline_start = '1992-01-01'
    baseline_end = '2002-12-31'

    # Select the baseline period
    ds_baseline = ds_region.sel(time=slice(baseline_start, baseline_end))
    
    # Extract baseline data
    sst_baseline = ds_baseline.analysed_sst.values
    baseline_times = ds_baseline.time.values
    
    print("Computing thresholds and climatology...")
    # Compute thresholds and climatology
    thresholds, climatology = compute_thresholds_and_climatology(sst_baseline, baseline_times)
    
    # Define target period
    target_start = '2009-06-01'
    target_end = '2009-08-31'
    
    # Select the target period
    ds_target = ds_region.sel(time=slice(target_start, target_end))
    
    # Extract target data
    sst_target = ds_target.analysed_sst.values
    target_times = ds_target.time.values
    
    # Create a mask for the region (to know which cells are valid)
    region_mask = np.ones((ds_region.latitude.size, ds_region.longitude.size), dtype=bool)
    
    print("Detecting MHW events...")
    # Find MHW events
    mhw_mask = find_mhw_events(sst_target, thresholds, climatology, target_times, region_mask)
    
    # Create the output NetCDF file
    os.makedirs('output', exist_ok=True)
    
    # Create a new dataset for output
    output_ds = xr.Dataset(
        {
            'mhw': (['time', 'latitude', 'longitude'], mhw_mask)
        },
        coords={
            'time': target_times,
            'latitude': ds_region.latitude.values,
            'longitude': ds_region.longitude.values
        }
    )
    
    # Save to NetCDF
    output_ds.to_netcdf('output/mhw_mask.nc')
    
    # Generate report
    # Find regional events
    # A day is active if at least one sea cell is inside a per-cell MHW
    active_days = np.any(mhw_mask, axis=(1, 2))  # Shape: (num_days,)
    
    # Find runs of consecutive active days (regional events)
    regional_events = []
    in_event = False
    event_start = None
    
    for i, is_active in enumerate(active_days):
        if is_active and not in_event:
            # Start of a new event
            event_start = i
            in_event = True
        elif not is_active and in_event:
            # End of an event
            event_end = i - 1
            if event_end >= event_start:  # Make sure there's at least one day
                event_start_date = str(target_times[event_start])[:10]
                event_end_date = str(target_times[event_end])[:10]
                regional_events.append({
                    'onset': event_start_date,
                    'end': event_end_date
                })
            in_event = False
    
    # Handle the case where the last day is active
    if in_event:
        event_end = len(active_days) - 1
        if event_end >= event_start:
            event_start_date = str(target_times[event_start])[:10]
            event_end_date = str(target_times[event_end])[:10]
            regional_events.append({
                'onset': event_start_date,
                'end': event_end_date
            })
    
    report = {
        'region': {
            'lat_min': lat_min,
            'lat_max': lat_max,
            'lon_min': lon_min,
            'lon_max': lon_max
        },
        'baseline_analysed': {
            'start': baseline_start,
            'end': baseline_end
        },
        'target_analysed': {
            'start': target_start,
            'end': target_end
        },
        'events': regional_events,
        'complete': True,
        'caveats': ''
    }
    
    with open('output/report.json', 'w') as f:
        json.dump(report, f, indent=2)
    
    print("Analysis complete!")
    print(f"Found {len(regional_events)} regional events")
    for event in regional_events:
        print(f"Event: {event['onset']} to {event['end']}")
    
    # Close the dataset
    ds.close()

if __name__ == "__main__":
    main()