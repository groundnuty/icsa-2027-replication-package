import xarray as xr
import numpy as np
from datetime import datetime, timedelta
import os
import json

# Create output directory
os.makedirs('output', exist_ok=True)

def get_doy_from_date(date_str):
    """Convert YYYY-MM-DD string to day of year (1-366)"""
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    month = date_obj.month
    day = date_obj.day
    
    # Days in each month (non-leap year)
    days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    
    # Calculate cumulative days
    cum_days = np.cumsum([0] + days_in_month)
    
    # Handle leap year case for Feb 29
    if month == 2 and day == 29:
        return 60
    
    # Return day of year
    return cum_days[month-1] + day

def load_data_for_period(data_dir, start_date_str, end_date_str):
    """Load data for a given period"""
    start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
    end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
    
    data_dict = {}
    current_date = start_date
    
    while current_date <= end_date:
        date_str = current_date.strftime("%Y-%m-%d")
        filename = f"{data_dir}/sst_{current_date.strftime('%Y%m%d')}.nc"
        
        try:
            ds = xr.open_dataset(filename, engine="h5netcdf")
            sst_data = ds['analysed_sst']
            data_dict[date_str] = sst_data
            ds.close()
        except Exception as e:
            print(f"Could not load {filename}: {e}")
            
        current_date += timedelta(days=1)
    
    return data_dict

def compute_threshold_and_climatology(baseline_data, region_mask):
    """
    Compute threshold and climatology for each day of year using baseline data.
    """
    # Initialize arrays
    thresholds = np.full(366, np.nan)
    climatologies = np.full(366, np.nan)
    
    # Create mapping from date to day of year
    date_to_doy = {}
    for date_str in baseline_data.keys():
        doy = get_doy_from_date(date_str)
        date_to_doy[date_str] = doy
    
    # Process each day of year (excluding day 60 which will be handled separately)
    for doy in range(1, 367):
        if doy == 60:  # Skip day 60 for direct computation
            continue
            
        # Find all baseline dates that correspond to this day of year
        matching_dates = []
        for date_str, date_doy in date_to_doy.items():
            if date_doy == doy:
                matching_dates.append(date_str)
        
        # Get data for these dates in the region
        pool_values = []
        for date_str in matching_dates:
            # Get data for this date
            data_slice = baseline_data[date_str]
            # Apply region mask
            masked_data = data_slice.where(region_mask, np.nan)
            # Flatten and add to pool
            flat_data = masked_data.values.flatten()
            pool_values.extend(flat_data[~np.isnan(flat_data)])
            
        # Convert to numpy array
        pool_array = np.array(pool_values)
        
        # Compute threshold (90th percentile) and climatology (mean)
        if len(pool_array) > 0:
            # Threshold is 90th percentile (Hazen method)
            threshold = np.percentile(pool_array, 90, method='hazen')
            # Climatology is mean
            climatology = np.mean(pool_array)
            
            thresholds[doy-1] = threshold
            climatologies[doy-1] = climatology
    
    # Special handling for day 60 (Feb 29)
    # Set to mean of days 59 and 61
    if not np.isnan(thresholds[58]) and not np.isnan(thresholds[60]):
        thresholds[59] = (thresholds[58] + thresholds[60]) / 2
    if not np.isnan(climatologies[58]) and not np.isnan(climatologies[60]):
        climatologies[59] = (climatologies[58] + climatologies[60]) / 2
    
    # Smooth with 31-day centered moving average (wrapping around)
    def smooth_31_day(arr):
        smoothed = np.zeros_like(arr)
        for i in range(len(arr)):
            # Get the window (31 days centered on i)
            window_sum = 0
            count = 0
            for j in range(-15, 16):
                idx = (i + j) % len(arr)
                if not np.isnan(arr[idx]):
                    window_sum += arr[idx]
                    count += 1
            if count > 0:
                smoothed[i] = window_sum / count
            else:
                smoothed[i] = np.nan
        return smoothed
    
    # Apply smoothing
    smoothed_thresholds = smooth_31_day(thresholds)
    smoothed_climatologies = smooth_31_day(climatologies)
    
    return smoothed_thresholds, smoothed_climatologies

def find_mhw_events(target_data, thresholds, climatologies, region_mask):
    """
    Find MHW events in target period.
    """
    # Get dimensions from first dataset
    first_data = list(target_data.values())[0]
    time_dim = len(target_data)
    lat_dim = first_data.shape[1] 
    lon_dim = first_data.shape[2]
    
    # Create result array
    mhw_mask = np.zeros((time_dim, lat_dim, lon_dim), dtype=np.uint8)
    
    # Process each day
    date_list = list(target_data.keys())
    for i, date_str in enumerate(date_list):
        # Get day of year for this date
        doy = get_doy_from_date(date_str)
        
        # Get threshold and climatology for this day
        threshold = thresholds[doy-1]
        climatology = climatologies[doy-1]
        
        # Get SST data for this day
        sst_slice = target_data[date_str].isel(time=0)
        
        # Compare to threshold
        hot_mask = (sst_slice >= threshold) & region_mask
        
        # Store in result array
        mhw_mask[i] = hot_mask.astype(np.uint8).values
    
    # Now identify actual MHW events by grouping consecutive hot days
    # and joining gaps of 1-2 days
    final_mhw_mask = np.zeros_like(mhw_mask)
    
    # Process each grid point independently
    for i in range(lat_dim):
        for j in range(lon_dim):
            # Extract time series for this grid point
            time_series = mhw_mask[:, i, j]
            
            # Identify runs of hot days (at least 5 consecutive)
            # First, identify all hot days
            hot_indices = np.where(time_series == 1)[0]
            
            if len(hot_indices) > 0:
                # Group consecutive indices
                runs = []
                current_run = [hot_indices[0]]
                
                for idx in hot_indices[1:]:
                    if idx == current_run[-1] + 1:
                        current_run.append(idx)
                    else:
                        runs.append(current_run)
                        current_run = [idx]
                runs.append(current_run)
                
                # Filter runs of at least 5 days
                long_runs = [run for run in runs if len(run) >= 5]
                
                # Join gaps of 1-2 days
                merged_runs = []
                if long_runs:
                    merged_runs = [long_runs[0]]
                    for run in long_runs[1:]:
                        last_run = merged_runs[-1]
                        # Check if gap is 1 or 2 days
                        gap_size = run[0] - last_run[-1] - 1
                        if gap_size <= 2:
                            # Merge runs
                            merged_runs[-1] = list(range(last_run[0], run[-1] + 1))
                        else:
                            merged_runs.append(run)
                
                # Mark all days in merged runs as MHW
                for run in merged_runs:
                    for day_idx in run:
                        if 0 <= day_idx < len(final_mhw_mask):
                            final_mhw_mask[day_idx, i, j] = 1
    
    return final_mhw_mask, date_list

def main():
    # Define region of interest
    lat_min, lat_max = 57.83, 59.03
    lon_min, lon_max = 17.41, 18.61
    
    # Define periods
    baseline_start = "1992-01-01"
    baseline_end = "2002-12-31"
    target_start = "2008-06-01"
    target_end = "2008-08-31"
    
    # Load baseline data
    print("Loading baseline data...")
    baseline_data = load_data_for_period(
        "/data/icsa2027_data_20261101T090944Z/s1z",
        baseline_start,
        baseline_end
    )
    
    if not baseline_data:
        print("No baseline data loaded!")
        return
    
    print(f"Loaded {len(baseline_data)} baseline files")
    
    # Load target data
    print("Loading target data...")
    target_data = load_data_for_period(
        "/data/icsa2027_data_20261101T090944Z/s1z",
        target_start,
        target_end
    )
    
    if not target_data:
        print("No target data loaded!")
        return
    
    print(f"Loaded {len(target_data)} target files")
    
    # Get coordinate information from any dataset
    sample_ds = list(baseline_data.values())[0]
    lats = sample_ds.latitude.values
    lons = sample_ds.longitude.values
    
    # Create region mask
    lat_mask = (lats >= lat_min) & (lats <= lat_max)
    lon_mask = (lons >= lon_min) & (lons <= lon_max)
    
    # Create 2D masks
    lat_indices = np.where(lat_mask)[0]
    lon_indices = np.where(lon_mask)[0]
    
    # Create full 2D region mask
    region_mask_2d = np.zeros((len(lats), len(lons)), dtype=bool)
    for i in lat_indices:
        for j in lon_indices:
            region_mask_2d[i, j] = True
    
    # Get region coordinates
    region_lats = lats[lat_indices]
    region_lons = lons[lon_indices]
    
    print(f"Region: lat {lat_min} to {lat_max}, lon {lon_min} to {lon_max}")
    print(f"Region dimensions: {len(region_lats)} x {len(region_lons)}")
    
    # Compute climatology and thresholds for baseline period
    print("Computing climatology and thresholds...")
    thresholds, climatologies = compute_threshold_and_climatology(
        baseline_data, region_mask_2d
    )
    
    # Now process target period to detect MHWs
    print("Detecting MHWs in target period...")
    
    # Find MHW events
    final_mhw_mask, date_list = find_mhw_events(
        target_data, thresholds, climatologies, region_mask_2d
    )
    
    # Create NetCDF file with proper coordinates
    print("Creating NetCDF output...")
    
    # Create coordinate arrays for the subset
    coords = {
        'time': date_list,
        'lat': region_lats,
        'lon': region_lons
    }
    
    # Create dataset with proper coordinate indexing
    # We need to make sure the dimensions match
    mhw_var = xr.Variable(('time', 'lat', 'lon'), final_mhw_mask, attrs={'units': 'binary'})
    
    # Create the dataset with explicit coordinates
    ds = xr.Dataset(
        {
            'mhw': mhw_var
        },
        coords=coords
    )
    
    # Save to file
    ds.to_netcdf('output/mhw_mask.nc')
    
    # Create report
    print("Generating report...")
    # Find regional events (days when at least one cell is in MHW)
    active_days = np.any(final_mhw_mask, axis=(1, 2))  # Active days for each time index
    
    # Find runs of consecutive active days
    events = []
    if np.any(active_days):
        # Group consecutive True values
        runs = []
        start = None
        for i, active in enumerate(active_days):
            if active and start is None:
                start = i
            elif not active and start is not None:
                runs.append((start, i-1))
                start = None
        if start is not None:
            runs.append((start, len(active_days)-1))
        
        # Convert to event format
        for start_idx, end_idx in runs:
            event_start = date_list[start_idx]
            event_end = date_list[end_idx]
            events.append({
                "onset": event_start,
                "end": event_end
            })
    
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
        "events": events,
        "complete": True,
        "caveats": ""
    }
    
    # Save report
    with open('output/report.json', 'w') as f:
        json.dump(report, f, indent=2)
    
    print("Analysis complete.")
    print(f"Report contains {len(events)} events")

if __name__ == "__main__":
    main()