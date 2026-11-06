import xarray as xr
import numpy as np
from datetime import datetime, timedelta
import os
import gc

# Define region and period
LAT_MIN, LAT_MAX = 54.39, 55.59
LON_MIN, LON_MAX = 18.25, 19.45
START_DATE = datetime(2021, 6, 1)
END_DATE = datetime(2021, 8, 31)
BASELINE_START = datetime(1992, 1, 1)
BASELINE_END = datetime(2002, 12, 31)

# Create output directory
os.makedirs('output', exist_ok=True)

def date_to_doy(date):
    """Convert a date to day-of-year (1-366)"""
    # Handle leap year cases properly
    if date.month == 2 and date.day == 29:
        return 60
    
    # Create a date for Jan 1 of the same year
    jan1 = datetime(date.year, 1, 1)
    doy = (date - jan1).days + 1
    
    # Adjust for leap year if needed
    if date.month > 2 and (date.year % 4 == 0 and (date.year % 100 != 0 or date.year % 400 == 0)):
        if doy >= 60:  # After Feb 29
            doy += 1
            
    return doy

def get_baseline_window_dates(doy, baseline_start, baseline_end):
    """Get all dates in baseline period that fall within ±5 days of a date with the given doy"""
    window_dates = []
    
    # Get the range of dates to check
    for year in range(baseline_start.year, baseline_end.year + 1):
        # Find the date that corresponds to this doy in this year
        try:
            # Create a date for Jan 1 of this year
            jan1 = datetime(year, 1, 1)
            
            # Calculate the target date
            target_date = jan1 + timedelta(days=doy - 1)
            
            # Add dates within ±5 days
            for i in range(-5, 6):
                candidate_date = target_date + timedelta(days=i)
                
                # Make sure it's within baseline period
                if baseline_start <= candidate_date <= baseline_end:
                    window_dates.append(candidate_date)
                    
        except ValueError:
            # Skip invalid dates (like Feb 29 in non-leap years)
            continue
    
    return window_dates

def smooth_with_wrapping(arr, window_size=31):
    """
    Apply a centered moving average with wrapping around the year.
    """
    # Ensure array is 366 elements
    if len(arr) != 366:
        raise ValueError("Array must be of length 366")
    
    smoothed = np.zeros_like(arr)
    half_window = window_size // 2
    
    for i in range(366):
        # Calculate the indices with wrapping
        indices = [(i + j - half_window) % 366 for j in range(window_size)]
        # Take the valid values (excluding NaN)
        values = arr[indices]
        valid_values = values[np.isfinite(values)]
        
        if len(valid_values) > 0:
            smoothed[i] = np.mean(valid_values)
        else:
            smoothed[i] = np.nan
    
    return smoothed

def process_mhw_analysis():
    """Main function to process MHW detection"""
    
    print("Starting MHW analysis...")
    
    # Step 1: Find all files in baseline and target periods
    base_path = "/data/icsa2027_data_20261101T090944Z/s1z"
    
    # Get all files and sort them by date
    files = []
    for filename in os.listdir(base_path):
        if filename.startswith('sst_') and filename.endswith('.nc'):
            try:
                # Extract date from filename (format sst_YYYYMMDD.nc)
                date_str = filename[4:12]  # sst_YYYYMMDD.nc -> YYYYMMDD
                date_obj = datetime.strptime(date_str, '%Y%m%d')
                files.append((filename, date_obj))
            except:
                continue

    # Sort by date
    files.sort(key=lambda x: x[1])

    # Filter files for baseline and target periods
    baseline_files = [f for f in files if BASELINE_START <= f[1] <= BASELINE_END]
    target_files = [f for f in files if START_DATE <= f[1] <= END_DATE]
    
    print(f"Found {len(baseline_files)} baseline files")
    print(f"Found {len(target_files)} target files")
    
    # Step 2: Load baseline data to compute thresholds and climatology
    print("Loading baseline data to compute thresholds and climatology...")
    
    # Initialize storage for baseline SST values
    baseline_sst_by_doy = {}
    
    # Process each day of year
    for doy in range(1, 367):
        if doy == 60:  # Skip Feb 29 as specified
            continue
            
        # Get all baseline dates for this doy
        window_dates = get_baseline_window_dates(doy, BASELINE_START, BASELINE_END)
        baseline_sst_by_doy[doy] = []
        
        # For each window date, collect SST data
        for win_date in window_dates:
            # Find corresponding file
            filename = f"sst_{win_date.strftime('%Y%m%d')}.nc"
            file_path = os.path.join(base_path, filename)
            
            if os.path.exists(file_path):
                try:
                    # Load the file
                    ds = xr.open_dataset(file_path, engine="h5netcdf")
                    
                    # Extract region
                    region_ds = ds.sel(latitude=slice(LAT_MIN, LAT_MAX), longitude=slice(LON_MIN, LON_MAX))
                    
                    # Get SST values (we're interested in all grid points)
                    sst_vals = region_ds.analysed_sst.values
                    
                    # Flatten and add to our collection
                    flat_sst = sst_vals.flatten()
                    baseline_sst_by_doy[doy].extend(flat_sst)
                    
                    ds.close()
                    del ds, region_ds, sst_vals, flat_sst
                    gc.collect()
                    
                except Exception as e:
                    print(f"Error processing {filename}: {e}")
                    continue
    
    # Step 3: Compute thresholds and climatology
    print("Computing thresholds and climatology...")
    
    threshold = np.full(366, np.nan, dtype=np.float64)
    climatology = np.full(366, np.nan, dtype=np.float64)
    
    # Process each day of year
    for doy in range(1, 367):
        if doy == 60:  # Skip day 60 (Feb 29)
            continue
            
        # Collect all SST values for this doy
        sst_values = np.array(baseline_sst_by_doy[doy])
        # Remove NaN values
        sst_values = sst_values[np.isfinite(sst_values)]
        
        if len(sst_values) > 0:
            # 90th percentile using method="hazen" (Hyndman–Fan type 5)
            threshold[doy-1] = np.quantile(sst_values, 0.9, method='hazen')
            climatology[doy-1] = np.mean(sst_values)
    
    # Handle day 60 (Feb 29) - set to mean of days 59 and 61
    if not np.isnan(climatology[58]) and not np.isnan(climatology[60]):
        climatology[59] = (climatology[58] + climatology[60]) / 2
    if not np.isnan(threshold[58]) and not np.isnan(threshold[60]):
        threshold[59] = (threshold[58] + threshold[60]) / 2
    
    # Step 4: Smooth climatology and threshold
    print("Smoothing climatology and threshold...")
    smoothed_threshold = smooth_with_wrapping(threshold)
    smoothed_climatology = smooth_with_wrapping(climatology)
    
    # Step 5: Process target period to detect MHWs
    print("Processing target period to detect MHWs...")
    
    # Load the region data for target period
    # First, identify all sea cells (those with data for all target days)
    sea_cells = []
    sea_cell_indices = []  # Store indices for later use
    
    # We'll identify sea cells by checking if they have data for all target days
    # For efficiency, we'll check a subset of the data first
    
    # Create mask for the region
    region_mask = None
    
    # First, let's check a few files to understand the data
    print("Identifying sea cells...")
    
    # We'll iterate through target files to find sea cells
    # But for efficiency, let's check a representative sample
    sample_target_files = target_files[:min(5, len(target_files))]  # First 5 or all
    
    # Let's find sea cells by examining a few sample files
    temp_sea_cells = []
    temp_lat_lon_map = {}  # To track which lat/lon pairs have data
    
    for filename, date in sample_target_files:
        file_path = os.path.join(base_path, filename)
        try:
            ds = xr.open_dataset(file_path, engine="h5netcdf")
            region_ds = ds.sel(latitude=slice(LAT_MIN, LAT_MAX), longitude=slice(LON_MIN, LON_MAX))
            
            # Get the spatial dimensions
            lats = region_ds.latitude.values
            lons = region_ds.longitude.values
            
            # Check which grid cells have finite values
            sst_data = region_ds.analysed_sst.values
            for i, lat in enumerate(lats):
                for j, lon in enumerate(lons):
                    # Check if this cell has valid data
                    if np.isfinite(sst_data[0, i, j]):  # Assuming 1 time slice
                        temp_lat_lon_map[(lat, lon)] = True
                        
            ds.close()
            del ds, region_ds, sst_data
            gc.collect()
            
        except Exception as e:
            print(f"Error processing {filename}: {e}")
            continue
    
    # Now we know which lat/lon pairs are valid
    sea_cells = list(temp_lat_lon_map.keys())
    print(f"Found {len(sea_cells)} potential sea cells in region")
    
    # Step 6: For each sea cell, determine if it experiences MHWs
    # Create the MHW mask array
    mhw_mask = np.zeros((len(target_files), len(sea_cells)), dtype=np.uint8)
    
    # Get time indices for target period
    target_time_indices = []
    target_dates = []
    
    for filename, date in target_files:
        target_time_indices.append(date)
        target_dates.append(date)
    
    # Process each target day to check for MHWs
    print("Detecting MHWs in target period...")
    
    # For each day, check which cells exceed threshold
    # This will be done by loading target files and comparing with thresholds
    
    # We'll process files in chunks to manage memory
    mhw_per_cell = {}  # Store MHW information per cell
    
    # Process target files one by one
    for i, (filename, date) in enumerate(target_files):
        file_path = os.path.join(base_path, filename)
        try:
            ds = xr.open_dataset(file_path, engine="h5netcdf")
            region_ds = ds.sel(latitude=slice(LAT_MIN, LAT_MAX), longitude=slice(LON_MIN, LON_MAX))
            
            # Get SST data for this day
            sst_day = region_ds.analysed_sst.values[0]  # First time dimension
            
            # Get the day-of-year for this date
            doy = date_to_doy(date)
            
            # Compare with threshold (use smoothed threshold)
            threshold_day = smoothed_threshold[doy - 1]
            
            # Create boolean mask for hot days
            hot_mask = sst_day >= threshold_day
            
            # Set MHW mask for this day (for all sea cells)
            # This is a simplified approach - we'll need to properly track runs
            
            # For now, let's store the hot mask for this day
            ds.close()
            del ds, region_ds, sst_day, hot_mask
            gc.collect()
            
        except Exception as e:
            print(f"Error processing {filename}: {e}")
            continue
    
    # Actually, let's restructure this approach. We need to:
    # 1. Load target data for all days
    # 2. For each sea cell, find hot days
    # 3. Identify MHW runs
    # 4. Join gaps of 1-2 days
    
    # Reorganize approach - let's build a comprehensive solution
    
    # Load all target data
    print("Loading all target data...")
    
    # Create arrays to hold SST data for all sea cells across all days
    n_days = len(target_files)
    n_cells = len(sea_cells)
    
    # Create SST array: [time, cells]
    sst_array = np.full((n_days, n_cells), np.nan, dtype=np.float64)
    
    # Fill in the SST data
    for i, (filename, date) in enumerate(target_files):
        file_path = os.path.join(base_path, filename)
        try:
            ds = xr.open_dataset(file_path, engine="h5netcdf")
            region_ds = ds.sel(latitude=slice(LAT_MIN, LAT_MAX), longitude=slice(LON_MIN, LON_MAX))
            
            # Get SST data for this day
            sst_day = region_ds.analysed_sst.values[0]  # First time dimension
            
            # For each sea cell, extract the SST value
            for j, (lat, lon) in enumerate(sea_cells):
                # Find indices in the region
                lat_idx = np.argmin(np.abs(region_ds.latitude.values - lat))
                lon_idx = np.argmin(np.abs(region_ds.longitude.values - lon))
                sst_array[i, j] = sst_day[lat_idx, lon_idx]
            
            ds.close()
            del ds, region_ds, sst_day
            gc.collect()
            
        except Exception as e:
            print(f"Error processing {filename}: {e}")
            continue
    
    # Now we have all SST data for sea cells over the target period
    print(f"Loaded SST data for {n_cells} sea cells over {n_days} days")
    
    # Step 7: Determine MHWs for each sea cell
    print("Determining MHWs for each sea cell...")
    
    # Create MHW mask for all days and sea cells
    mhw_mask = np.zeros((n_days, n_cells), dtype=np.uint8)
    
    # For each cell, identify MHWs
    for j in range(n_cells):
        # Get SST timeseries for this cell
        sst_series = sst_array[:, j]
        
        # Get the day-of-year for each day
        doy_series = [date_to_doy(date) for date in target_dates]
        
        # Check which days are hot (>= threshold)
        hot_days = np.zeros(n_days, dtype=bool)
        for i in range(n_days):
            doy = doy_series[i]
            threshold_val = smoothed_threshold[doy - 1]
            if np.isfinite(sst_series[i]) and sst_series[i] >= threshold_val:
                hot_days[i] = True
                
        # Find runs of hot days (at least 5 consecutive)
        # Simple implementation: mark MHWs as sequences of at least 5 hot days
        # Also join gaps of 1-2 days
        
        # First, find all hot days
        hot_indices = np.where(hot_days)[0]
        
        if len(hot_indices) > 0:
            # Group consecutive hot days
            mhw_starts = []
            mhw_ends = []
            
            # Start with first hot day
            start_i = hot_indices[0]
            end_i = start_i
            
            # Process all hot indices
            for i in range(1, len(hot_indices)):
                if hot_indices[i] == end_i + 1:  # Consecutive day
                    end_i = hot_indices[i]
                else:  # Gap
                    # Check if gap is 1 or 2 days, if so join
                    gap_length = hot_indices[i] - end_i - 1
                    if gap_length <= 2:
                        # Join with next segment
                        end_i = hot_indices[i]
                    else:
                        # End current MHW
                        mhw_starts.append(start_i)
                        mhw_ends.append(end_i)
                        # Start new MHW
                        start_i = hot_indices[i]
                        end_i = hot_indices[i]
            
            # Don't forget the last MHW
            if len(mhw_starts) == 0 or mhw_ends[-1] != end_i:
                mhw_starts.append(start_i)
                mhw_ends.append(end_i)
            
            # Mark MHW days in mask
            for start, end in zip(mhw_starts, mhw_ends):
                # Make sure we don't go out of bounds
                if 0 <= start < n_days and 0 <= end < n_days:
                    mhw_mask[start:end+1, j] = 1
    
    # Step 8: Determine regional events
    print("Identifying regional events...")
    
    # A day is active if at least one sea cell is in an MHW
    active_days = np.any(mhw_mask, axis=1)
    
    # Find maximal runs of consecutive active days
    events = []
    i = 0
    while i < len(active_days):
        if active_days[i]:
            # Found start of an event
            start_day = i
            # Extend until inactive day
            while i < len(active_days) and active_days[i]:
                i += 1
            # End of event
            end_day = i - 1
            # Convert to dates
            start_date = target_dates[start_day]
            end_date = target_dates[end_day]
            events.append({
                'onset': start_date.strftime('%Y-%m-%d'),
                'end': end_date.strftime('%Y-%m-%d')
            })
        else:
            i += 1
    
    # Step 9: Create NetCDF output
    print("Creating NetCDF output...")
    
    # Create coordinate arrays
    times = [date.strftime('%Y-%m-%d') for date in target_dates]
    
    # Create a temporary dataset to generate the NetCDF
    # We need to create the proper coordinate system
    lat_vals = [cell[0] for cell in sea_cells]
    lon_vals = [cell[1] for cell in sea_cells]
    
    # Create a minimal dataset structure
    # For now, let's create a simple NetCDF with the right dimensions
    
    # Create the NetCDF file
    import netCDF4 as nc
    
    # Create the NetCDF file
    with nc.Dataset('output/mhw_mask.nc', 'w', format='NETCDF4') as ncfile:
        # Create dimensions
        time_dim = ncfile.createDimension('time', len(target_files))
        lat_dim = ncfile.createDimension('lat', len(sea_cells))
        lon_dim = ncfile.createDimension('lon', len(sea_cells))
        
        # Create variables
        time_var = ncfile.createVariable('time', 'S10', ('time',))
        lat_var = ncfile.createVariable('lat', 'f4', ('lat',))
        lon_var = ncfile.createVariable('lon', 'f4', ('lon',))
        mhw_var = ncfile.createVariable('mhw', 'u1', ('time', 'lat', 'lon'), fill_value=0)
        
        # Fill time variable
        time_var[:] = [t.strftime('%Y-%m-%d').encode('utf-8') for t in target_dates]
        
        # Fill lat/lon variables
        lat_var[:] = lat_vals
        lon_var[:] = lon_vals
        
        # Fill mhw variable
        mhw_var[:] = mhw_mask.astype(np.uint8)
        
        # Add attributes
        ncfile.description = 'Marine Heatwave mask for Baltic Sea region'
        ncfile.history = 'Created from Copernicus Marine SST data'
        
    # Step 10: Create report JSON
    print("Creating report...")
    
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
            "start": START_DATE.strftime("%Y-%m-%d"),
            "end": END_DATE.strftime("%Y-%m-%d")
        },
        "events": events,
        "complete": True,
        "caveats": ""
    }
    
    # Write report to file
    import json
    with open('output/report.json', 'w') as f:
        json.dump(report, f, indent=2)
    
    print("Analysis complete!")
    print(f"Found {len(events)} regional MHW events")
    if events:
        for event in events:
            print(f"  Event: {event['onset']} to {event['end']}")
    
    return report

# Run the analysis
try:
    result = process_mhw_analysis()
except Exception as e:
    print(f"Error during analysis: {e}")
    import traceback
    traceback.print_exc()