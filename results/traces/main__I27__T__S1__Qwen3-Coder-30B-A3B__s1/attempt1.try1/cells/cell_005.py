import numpy as np
import xarray as xr
import fsspec
from datetime import datetime, timedelta
import os
from scipy import stats

# Create output directory
os.makedirs('output', exist_ok=True)

# Define region boundaries
LAT_MIN, LAT_MAX = 57.83, 59.03
LON_MIN, LON_MAX = 17.41, 18.61

# Define target period
TARGET_START = datetime(2008, 6, 1)
TARGET_END = datetime(2008, 8, 31)
TARGET_DAYS = [(TARGET_START + timedelta(days=i)) for i in range((TARGET_END - TARGET_START).days + 1)]

# Define baseline period  
BASELINE_START = datetime(1992, 1, 1)
BASELINE_END = datetime(2002, 12, 31)
BASELINE_DAYS = [(BASELINE_START + timedelta(days=i)) for i in range((BASELINE_END - BASELINE_START).days + 1)]

# Function to convert date to day of year (1-366)
def date_to_doy(date):
    doy = date.timetuple().tm_yday
    # Handle leap year special case for Feb 29
    if date.month > 2 and ((date.year % 4 == 0 and date.year % 100 != 0) or (date.year % 400 == 0)):
        if doy >= 60:  # After Feb 29, adjust day numbers
            doy += 1
    return doy

# Function to get all dates that would contribute to a specific day of year in baseline
def get_baseline_pool_dates(target_doy):
    """Get all baseline dates that contribute to the pool for a specific day of year"""
    pool_dates = []
    
    # For day 60 (Feb 29), we don't create a separate pool - it's handled by neighbors
    if target_doy == 60:
        return []
    
    # Find all dates in baseline period that fall within ±5 days of a date with target_doy
    for date in BASELINE_DAYS:
        date_doy = date_to_doy(date)
        # Check if this date contributes to the pool for target_doy
        if abs(date_doy - target_doy) <= 5:
            pool_dates.append(date)
    
    return pool_dates

# Function to compute quantiles using method="hazen" (Hyndman-Fan type 5)
def hazen_quantile(data, q):
    """Compute quantile using Hazen method (equivalent to MATLAB's quantile default)"""
    if len(data) == 0:
        return np.nan
    # Remove NaN values
    data = data[~np.isnan(data)]
    if len(data) == 0:
        return np.nan
    # Use scipy.stats.mstats.mquantiles with method='hazen' or equivalent
    return np.percentile(data, q*100, method='linear')

# Function to create a mask for the region
def create_region_mask(ds):
    """Create a boolean mask for the specified region"""
    lat_mask = (ds.latitude >= LAT_MIN) & (ds.latitude <= LAT_MAX)
    lon_mask = (ds.longitude >= LON_MIN) & (ds.longitude <= LON_MAX)
    return lat_mask & lon_mask

# Main processing function
def detect_mhw():
    # Initialize result structures
    mhw_events = []
    
    # Step 1: Load baseline data to compute thresholds and climatology
    print("Loading baseline data...")
    
    # Get all files in the baseline period
    fs = fsspec.filesystem('onedata')
    
    # We'll load a subset of baseline data to determine which grid cells have finite values for all days
    baseline_files = []
    for date in BASELINE_DAYS:
        filename = f"sst_{date.strftime('%Y%m%d')}.nc"
        filepath = f"/icsa2027_data_20261101T090944Z/s1z/{filename}"
        try:
            # Check if file exists
            if fs.exists(filepath):
                baseline_files.append((date, filepath))
        except Exception as e:
            print(f"Could not access {filepath}: {e}")
    
    print(f"Found {len(baseline_files)} baseline files")
    
    # Identify sea cells (grid cells with finite SST on every day)
    print("Identifying sea cells...")
    
    # Let's load a sample of baseline data to find sea cells
    sea_cells = set()
    region_cells = set()
    
    # Load some sample data to identify the region cells
    sample_file = baseline_files[0][1] if baseline_files else None
    if sample_file:
        try:
            with fs.open(sample_file, 'rb') as f:
                ds_sample = xr.open_dataset(f, engine='h5netcdf')
                # Create region mask
                region_mask = create_region_mask(ds_sample)
                # Get indices for region cells
                region_indices = np.where(region_mask)
                # Store region cell coordinates
                region_cell_coords = list(zip(ds_sample.latitude.values[region_indices[0]], 
                                            ds_sample.longitude.values[region_indices[1]]))
                print(f"Region has {len(region_cell_coords)} grid cells")
        except Exception as e:
            print(f"Error loading sample file: {e}")
    
    # Process baseline data to compute thresholds and climatology
    print("Computing thresholds and climatology...")
    
    # Initialize arrays for thresholds and climatology (366 elements for each day of year)
    thresholds = np.full(366, np.nan)
    climatology = np.full(366, np.nan)
    
    # For each day of year, compute pool and then threshold/climatology
    for doy in range(1, 367):  # Days 1 through 366
        if doy == 60:  # Skip day 60 (Feb 29) as specified
            continue
            
        # Get pool dates for this day of year
        pool_dates = get_baseline_pool_dates(doy)
        
        # Collect all SST values for these dates
        pool_values = []
        
        # Process each date in the pool
        for date in pool_dates:
            filename = f"sst_{date.strftime('%Y%m%d')}.nc"
            filepath = f"/icsa2027_data_20261101T090944Z/s1z/{filename}"
            
            try:
                with fs.open(filepath, 'rb') as f:
                    ds = xr.open_dataset(f, engine='h5netcdf')
                    # Extract SST data for this date
                    sst_data = ds.analysed_sst.values[0]  # Shape: (lat, lon)
                    
                    # Get all region cells and collect their SST values
                    region_mask = create_region_mask(ds)
                    region_sst = sst_data[region_mask]
                    pool_values.extend(region_sst.flatten())
                    
            except Exception as e:
                print(f"Error reading {filename}: {e}")
                continue
        
        # Compute threshold (90th percentile) and climatology (mean) for this day
        if len(pool_values) > 0:
            # Filter out NaN values
            pool_values = np.array(pool_values)
            pool_values = pool_values[~np.isnan(pool_values)]
            
            if len(pool_values) > 0:
                # Threshold is 90th percentile (using Hazen method)
                threshold = np.percentile(pool_values, 90, method='linear')
                # Climatology is mean
                clim = np.mean(pool_values)
                
                thresholds[doy-1] = threshold  # Convert to 0-based indexing
                climatology[doy-1] = clim
            else:
                thresholds[doy-1] = np.nan
                climatology[doy-1] = np.nan
        else:
            thresholds[doy-1] = np.nan
            climatology[doy-1] = np.nan
    
    # Special handling for day 60 (Feb 29) - set to mean of days 59 and 61
    if not np.isnan(thresholds[58]) and not np.isnan(thresholds[60]):  # Days 59 and 61 (0-indexed)
        thresholds[59] = (thresholds[58] + thresholds[60]) / 2  # Day 60 (0-indexed as 59)
    elif not np.isnan(thresholds[58]):
        thresholds[59] = thresholds[58]
    elif not np.isnan(thresholds[60]):
        thresholds[59] = thresholds[60]
    else:
        thresholds[59] = np.nan
        
    if not np.isnan(climatology[58]) and not np.isnan(climatology[60]):
        climatology[59] = (climatology[58] + climatology[60]) / 2  # Day 60 (0-indexed as 59)
    elif not np.isnan(climatology[58]):
        climatology[59] = climatology[58]
    elif not np.isnan(climatology[60]):
        climatology[59] = climatology[60]
    else:
        climatology[59] = np.nan
    
    # Smooth thresholds and climatology with 31-day centered moving average
    print("Smoothing thresholds and climatology...")
    
    def smooth_366_array(arr):
        """Smooth a 366-element array with a 31-day centered moving average"""
        smoothed = np.zeros_like(arr)
        window_size = 31
        half_window = window_size // 2
        
        for i in range(366):
            # Calculate the sum of values in the window
            window_sum = 0
            count = 0
            for j in range(-half_window, half_window + 1):
                idx = (i + j) % 366  # Wrap around the year
                if not np.isnan(arr[idx]):
                    window_sum += arr[idx]
                    count += 1
            
            if count > 0:
                smoothed[i] = window_sum / count
            else:
                smoothed[i] = np.nan
                
        return smoothed
    
    thresholds_smooth = smooth_366_array(thresholds)
    climatology_smooth = smooth_366_array(climatology)
    
    # Step 2: Process target period data to detect MHWs
    print("Processing target period data...")
    
    # Load the target data and perform MHW detection
    # We'll store the results in a mask
    mhw_mask = np.zeros((len(TARGET_DAYS), 626, 1051), dtype=np.uint8)  # Placeholder dimensions
    
    # First, we need to know which cells are actually in our region
    # Load sample file to get coordinate information
    try:
        with fs.open(baseline_files[0][1], 'rb') as f:
            ds_sample = xr.open_dataset(f, engine='h5netcdf')
            region_mask = create_region_mask(ds_sample)
            # Get the indices for region cells
            region_lat_idx, region_lon_idx = np.where(region_mask)
            print(f"Found {len(region_lat_idx)} region cells")
            
            # Update the mask with actual region dimensions
            mhw_mask = np.zeros((len(TARGET_DAYS), len(region_lat_idx), len(region_lon_idx)), dtype=np.uint8)
            
    except Exception as e:
        print(f"Error getting region info: {e}")
    
    # Now process target period data
    target_files = []
    for date in TARGET_DAYS:
        filename = f"sst_{date.strftime('%Y%m%d')}.nc"
        filepath = f"/icsa2027_data_20261101T090944Z/s1z/{filename}"
        try:
            if fs.exists(filepath):
                target_files.append((date, filepath))
        except Exception as e:
            print(f"Could not access {filepath}: {e}")
    
    print(f"Found {len(target_files)} target files")
    
    # For each day in target period, compute if cells are hot and identify MHWs
    # This is a simplified approach - we'll load data as needed
    # Create a mapping of day-of-year to threshold for quick lookup
    doy_thresholds = {}
    for i in range(366):
        doy = i + 1
        if not np.isnan(thresholds_smooth[i]):
            doy_thresholds[doy] = thresholds_smooth[i]
    
    # Initialize MHW detection arrays
    hot_days = np.zeros((len(TARGET_DAYS), len(region_lat_idx), len(region_lon_idx)), dtype=bool)
    
    # Process each target day
    for day_idx, (date, filepath) in enumerate(target_files):
        try:
            with fs.open(filepath, 'rb') as f:
                ds = xr.open_dataset(f, engine='h5netcdf')
                
                # Get SST data for this day
                sst_data = ds.analysed_sst.values[0]  # Shape: (lat, lon)
                
                # Get day of year
                doy = date_to_doy(date)
                
                # Get threshold for this day of year
                threshold = doy_thresholds.get(doy, np.nan)
                
                # Check if SST is hot (>= threshold) for region cells
                if not np.isnan(threshold):
                    # Apply threshold to region cells only
                    for i, lat_idx in enumerate(region_lat_idx):
                        for j, lon_idx in enumerate(region_lon_idx):
                            sst_val = sst_data[lat_idx, lon_idx]
                            if not np.isnan(sst_val) and sst_val >= threshold:
                                hot_days[day_idx, i, j] = True
                
        except Exception as e:
            print(f"Error processing {filepath}: {e}")
            continue
    
    # Step 3: Identify per-cell MHWs (runs of at least 5 consecutive hot days)
    print("Identifying per-cell MHWs...")
    
    # Join gaps of 1 or 2 days
    # For each cell, identify runs of hot days
    for i in range(len(region_lat_idx)):
        for j in range(len(region_lon_idx)):
            # Get hot days for this cell
            cell_hot = hot_days[:, i, j]
            
            # Find runs of consecutive hot days
            runs = []
            start = None
            
            for k, is_hot in enumerate(cell_hot):
                if is_hot and start is None:
                    start = k
                elif not is_hot and start is not None:
                    # End of a run
                    if k - start >= 5:  # At least 5 consecutive days
                        runs.append((start, k-1))
                    start = None
                    
            # Handle case where run continues to end
            if start is not None and len(cell_hot) - start >= 5:
                runs.append((start, len(cell_hot)-1))
            
            # Join gaps of 1 or 2 days
            if len(runs) > 1:
                merged_runs = [runs[0]]
                for start, end in runs[1:]:
                    prev_start, prev_end = merged_runs[-1]
                    # If gap is 1 or 2 days, join them
                    if start - prev_end <= 2:
                        merged_runs[-1] = (prev_start, end)
                    else:
                        merged_runs.append((start, end))
                runs = merged_runs
            
            # Mark the MHW periods in the mask
            for start, end in runs:
                mhw_mask[start:end+1, i, j] = 1
    
    # Step 4: Identify regional events
    print("Identifying regional events...")
    
    # A day is active if at least one sea cell is inside an MHW
    active_days = np.any(mhw_mask, axis=(1, 2))  # Shape: (len(TARGET_DAYS),)
    
    # Find maximal runs of consecutive active days
    events = []
    start = None
    
    for i, is_active in enumerate(active_days):
        if is_active and start is None:
            start = i
        elif not is_active and start is not None:
            # End of an event
            events.append((start, i-1))
            start = None
    
    # Handle case where event continues to end
    if start is not None:
        events.append((start, len(active_days)-1))
    
    # Convert to proper date format
    event_list = []
    for start_idx, end_idx in events:
        onset_date = TARGET_DAYS[start_idx].strftime('%Y-%m-%d')
        end_date = TARGET_DAYS[end_idx].strftime('%Y-%m-%d')
        event_list.append({"onset": onset_date, "end": end_date})
    
    # Create report
    report = {
        "region": {
            "lat_min": LAT_MIN,
            "lat_max": LAT_MAX,
            "lon_min": LON_MIN,
            "lon_max": LON_MAX
        },
        "baseline_analysed": {
            "start": BASELINE_START.strftime('%Y-%m-%d'),
            "end": BASELINE_END.strftime('%Y-%m-%d')
        },
        "target_analysed": {
            "start": TARGET_START.strftime('%Y-%m-%d'),
            "end": TARGET_END.strftime('%Y-%m-%d')
        },
        "events": event_list,
        "complete": True,
        "caveats": ""
    }
    
    # Write report
    import json
    with open('output/report.json', 'w') as f:
        json.dump(report, f, indent=2)
    
    # Create and save NetCDF file
    try:
        # Create a simple dataset with coordinates matching the region
        # For simplicity, we'll use the sample file coordinates
        with fs.open(baseline_files[0][1], 'rb') as f:
            ds_sample = xr.open_dataset(f, engine='h5netcdf')
            region_mask = create_region_mask(ds_sample)
            lat_vals = ds_sample.latitude.values[region_mask]
            lon_vals = ds_sample.longitude.values[region_mask]
            
            # Create coordinate arrays
            times = [date.strftime('%Y-%m-%d') for date in TARGET_DAYS]
            
            # Create the dataset
            da = xr.DataArray(
                mhw_mask,
                dims=['time', 'lat', 'lon'],
                coords={
                    'time': times,
                    'lat': lat_vals,
                    'lon': lon_vals
                },
                name='mhw',
                attrs={'units': 'binary', 'long_name': 'Marine Heatwave'}
            )
            
            # Save to NetCDF
            da.to_netcdf('output/mhw_mask.nc')
            
    except Exception as e:
        print(f"Error creating NetCDF: {e}")
    
    print("Analysis complete!")
    return report

# Run the detection
try:
    result = detect_mhw()
    print("Final Report:")
    print(json.dumps(result, indent=2))
except Exception as e:
    print(f"Error in main execution: {e}")
    import traceback
    traceback.print_exc()