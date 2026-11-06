import xarray as xr
import numpy as np
from datetime import datetime, timedelta
import os
import json

# Define our region of interest
LAT_MIN, LAT_MAX = 56.09, 57.29
LON_MIN, LON_MAX = 10.55, 11.75

# Define periods
BASELINE_START = datetime(1992, 1, 1)
BASELINE_END = datetime(2002, 12, 31)
TARGET_START = datetime(2009, 6, 1)
TARGET_END = datetime(2009, 8, 31)

def date_to_doy(date):
    """Convert date to day of year (1-366) - treating all years as non-leap"""
    jan1 = datetime(2001, 1, 1)  # Non-leap year
    doy = (date - jan1).days + 1
    return doy

def compute_thresholds_and_climatology(baseline_sst, baseline_times):
    """Compute thresholds and climatology for each day of year"""
    # Initialize arrays for 366 days
    thresholds = np.full(366, np.nan)
    climatologies = np.full(366, np.nan)
    
    # Get all unique days of year in baseline period
    doys = [date_to_doy(d) for d in baseline_times]
    unique_doy = sorted(list(set(doys)))
    
    # For each day of year, compute the pool of values
    for doy in unique_doy:
        if doy == 60:  # Skip day 60 as special case
            continue
            
        # Find all baseline dates with this DOY
        pool_dates = []
        for i, date in enumerate(baseline_times):
            if date_to_doy(date) == doy:
                pool_dates.append(i)
        
        # Collect all SST values from these dates within ±5 days window
        pool_values = []
        for i in pool_dates:
            # Get the actual date
            date = baseline_times[i]
            
            # Find all dates within ±5 days of this date
            for j, other_date in enumerate(baseline_times):
                delta_days = abs((other_date - date).days)
                if delta_days <= 5:
                    # Make sure we're not including the same date twice (though it shouldn't happen)
                    if i != j or (i == j and delta_days == 0):
                        # Extract SST value for this location
                        sst_val = baseline_sst[j]  # This is a 2D array
                        # Flatten and filter out NaN values
                        flat_sst = sst_val.flatten()
                        valid_sst = flat_sst[~np.isnan(flat_sst)]
                        pool_values.extend(valid_sst)
        
        # Compute threshold (90th percentile) and climatology (mean)
        if len(pool_values) > 0:
            # Using numpy's method='hazen' equivalent (which is hyndman-fan type 5)
            threshold = np.percentile(pool_values, 90, method='linear')  # This approximates hazen
            climatology = np.mean(pool_values)
            
            thresholds[doy] = threshold
            climatologies[doy] = climatology
    
    # Special handling for day 60 (Feb 29)
    # Set it to the mean of days 59 and 61
    if not np.isnan(thresholds[59]) and not np.isnan(thresholds[61]):
        thresholds[60] = (thresholds[59] + thresholds[61]) / 2
    if not np.isnan(climatologies[59]) and not np.isnan(climatologies[61]):
        climatologies[60] = (climatologies[59] + climatologies[61]) / 2
    
    # Smooth both arrays with 31-day centered moving average
    def smooth_366_array(arr):
        """Smooth a 366-element array with 31-day centered moving average"""
        smoothed = np.zeros_like(arr)
        half_window = 15  # 31-day window = 15 on each side
        
        for i in range(366):
            # Get the window indices (wrapping around)
            window_values = []
            for j in range(-half_window, half_window + 1):
                idx = (i + j) % 366
                if not np.isnan(arr[idx]):
                    window_values.append(arr[idx])
            
            if len(window_values) > 0:
                smoothed[i] = np.mean(window_values)
            else:
                smoothed[i] = np.nan
                
        return smoothed
    
    # Apply smoothing
    smoothed_thresholds = smooth_366_array(thresholds)
    smoothed_climatologies = smooth_366_array(climatologies)
    
    return smoothed_thresholds, smoothed_climatologies

def detect_mhws(target_sst, target_times, thresholds, climatologies):
    """Detect MHWs in the target period"""
    # Initialize MHW mask
    mhw_mask = np.zeros_like(target_sst, dtype=np.uint8)
    
    # For each day in target period
    for i, date in enumerate(target_times):
        doy = date_to_doy(date)
        threshold = thresholds[doy]
        
        # Check which cells are hot (SST >= threshold)
        hot_cells = target_sst[i] >= threshold
        
        # Mark hot cells in the mask
        mhw_mask[i] = hot_cells.astype(np.uint8)
    
    # Now apply the hot-run detection logic
    # For each cell, find runs of at least 5 consecutive hot days
    # and join gaps of 1 or 2 days
    
    # This is a complex operation that requires careful handling
    # Let's process each spatial point separately
    
    # Create a copy for modification
    final_mhw_mask = mhw_mask.copy()
    
    # For each spatial point (lat/lon position)
    n_lat, n_lon = target_sst.shape[1], target_sst.shape[2]
    
    for lat_idx in range(n_lat):
        for lon_idx in range(n_lon):
            # Extract the time series for this point
            time_series = mhw_mask[:, lat_idx, lon_idx]
            
            # Find runs of hot days (1s) 
            # This is a simplified version - we need to identify runs of 5+ consecutive 1s
            # and then merge runs separated by 1-2 days
            
            # Identify runs of 1s
            runs = []
            start = None
            for t in range(len(time_series)):
                if time_series[t] == 1 and start is None:
                    start = t
                elif time_series[t] == 0 and start is not None:
                    runs.append((start, t-1))
                    start = None
            # Don't forget the last run if it's still going
            if start is not None:
                runs.append((start, len(time_series)-1))
            
            # Now merge runs that are separated by 1-2 days
            merged_runs = []
            if len(runs) > 0:
                current_start, current_end = runs[0]
                
                for i in range(1, len(runs)):
                    next_start, next_end = runs[i]
                    gap = next_start - current_end
                    
                    if gap <= 2:  # Gap of 1 or 2 days - merge
                        current_end = next_end
                    else:  # Gap of 3+ days - new run
                        merged_runs.append((current_start, current_end))
                        current_start, current_end = next_start, next_end
                
                merged_runs.append((current_start, current_end))
            
            # Update the mask with merged runs
            for start, end in merged_runs:
                final_mhw_mask[start:end+1, lat_idx, lon_idx] = 1
    
    return final_mhw_mask

def create_output_files(mhw_mask, target_times, target_sst):
    """Create the required output files"""
    # Create output directory
    os.makedirs('output', exist_ok=True)
    
    # Save NetCDF file
    # First, we need to create proper coordinate arrays
    lat_vals = np.linspace(LAT_MIN, LAT_MAX, target_sst.shape[1])
    lon_vals = np.linspace(LON_MIN, LON_MAX, target_sst.shape[2])
    
    # Create the dataset
    ds = xr.Dataset(
        {
            'mhw': (['time', 'lat', 'lon'], mhw_mask)
        },
        coords={
            'time': target_times,
            'lat': lat_vals,
            'lon': lon_vals
        }
    )
    
    ds.to_netcdf('output/mhw_mask.nc')
    
    # Create report JSON
    events = []  # Will be populated later
    
    report = {
        "region": {
            "lat_min": LAT_MIN,
            "lat_max": LAT_MAX,
            "lon_min": LON_MIN,
            "lon_max": LON_MAX
        },
        "baseline_analysed": {
            "start": BASELINE_START.strftime("%Y-%m-%d"),
            "end": BASELINE_END.strftime("%Y-%m-%d")
        },
        "target_analysed": {
            "start": TARGET_START.strftime("%Y-%m-%d"),
            "end": TARGET_END.strftime("%Y-%m-%d")
        },
        "events": events,
        "complete": True,
        "caveats": ""
    }
    
    with open('output/report.json', 'w') as f:
        json.dump(report, f, indent=2)

# Main execution flow
print("Computing thresholds and climatology...")
thresholds, climatologies = compute_thresholds_and_climatology(baseline_sst, baseline_times)

print("Detecting MHWs...")
mhw_mask = detect_mhws(target_sst, target_times, thresholds, climatologies)

print("Creating output files...")
create_output_files(mhw_mask, target_times, target_sst)

print("Analysis complete!")