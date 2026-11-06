import xarray as xr
import numpy as np
from datetime import datetime, timedelta
import os
import json

def date_to_doy(date):
    """Convert date to day of year (1-366)"""
    # Handle leap year cases
    if date.month == 2 and date.day == 29:
        return 60  # 29 February is treated as day 60
    
    # Create a date for the same year but with Jan 1 to get the day of year
    jan1 = datetime(date.year, 1, 1)
    doy = (date - jan1).days + 1
    
    # Adjust for leap year if needed
    if date.month > 2 and (date.year % 4 == 0 and (date.year % 100 != 0 or date.year % 400 == 0)):
        # This is a leap year and we're past Feb 28
        if doy >= 60:  # If we're past Feb 28, adjust for leap day
            doy += 1
            
    return doy

def smooth_with_wrapping(arr, window_size=31):
    """Smooth array with wrapping around year boundaries"""
    n = len(arr)
    smoothed = np.zeros(n, dtype=np.float64)
    half_window = window_size // 2
    
    for i in range(n):
        # Calculate the indices for the window
        indices = [(i + j - half_window) % n for j in range(window_size)]
        # Take the mean of the values at these indices
        values = [arr[idx] for idx in indices]
        # Filter out NaN values
        valid_values = [v for v in values if not np.isnan(v)]
        if len(valid_values) > 0:
            smoothed[i] = np.mean(valid_values)
        else:
            smoothed[i] = np.nan
    
    return smoothed

def find_hot_days(sst, thresholds, doys):
    """Find hot days for each cell"""
    hot_days = np.zeros_like(sst, dtype=bool)
    
    # For each time step
    for t in range(sst.shape[0]):
        doy = doys[t]
        # Compare SST to threshold for that day of year
        hot_days[t] = sst[t] >= thresholds[doy]
    
    return hot_days

def find_mhw_runs(hot_days):
    """Find MHW runs of at least 5 consecutive hot days"""
    mhw = np.zeros_like(hot_days, dtype=np.uint8)
    
    for i in range(hot_days.shape[1]):  # Loop through latitude
        for j in range(hot_days.shape[2]):  # Loop through longitude
            # Find hot runs for this cell
            hot_series = hot_days[:, i, j]
            
            # Find runs of consecutive True values (hot days)
            if np.any(hot_series):
                # Create a boolean array for runs
                run_lengths = []
                run_starts = []
                run_ends = []
                
                in_run = False
                run_start_idx = 0
                
                for k, is_hot in enumerate(hot_series):
                    if is_hot and not in_run:
                        # Start of a new run
                        in_run = True
                        run_start_idx = k
                    elif not is_hot and in_run:
                        # End of a run
                        in_run = False
                        run_length = k - run_start_idx
                        if run_length >= 5:  # At least 5 consecutive hot days
                            run_lengths.append(run_length)
                            run_starts.append(run_start_idx)
                            run_ends.append(k - 1)
                
                # Handle case where the run extends to the end
                if in_run:
                    run_length = len(hot_series) - run_start_idx
                    if run_length >= 5:
                        run_lengths.append(run_length)
                        run_starts.append(run_start_idx)
                        run_ends.append(len(hot_series) - 1)
                
                # Mark the runs in the MHW array
                for start, end in zip(run_starts, run_ends):
                    mhw[start:end+1, i, j] = 1
                    
    return mhw

def join_gaps(mhw, max_gap=2):
    """Join MHWs separated by 1 or 2 non-hot days"""
    # This is more complex - we need to analyze each cell independently
    mhw_joined = np.copy(mhw)
    
    for i in range(mhw.shape[1]):  # Loop through latitude
        for j in range(mhw.shape[2]):  # Loop through longitude
            # Process each cell's time series
            cell_mhw = mhw[:, i, j]
            
            # Find gaps and join them if they're small enough
            if np.any(cell_mhw):
                # Identify segments of consecutive MHW days
                segments = []
                in_segment = False
                segment_start = 0
                
                for k, is_mhw in enumerate(cell_mhw):
                    if is_mhw and not in_segment:
                        # Start of a new segment
                        in_segment = True
                        segment_start = k
                    elif not is_mhw and in_segment:
                        # End of a segment
                        in_segment = False
                        segments.append((segment_start, k-1))
                
                # Handle case where segment goes to the end
                if in_segment:
                    segments.append((segment_start, len(cell_mhw)-1))
                
                # Now join adjacent segments if the gap is small
                if len(segments) > 1:
                    merged_segments = [segments[0]]
                    
                    for seg in segments[1:]:
                        prev_end = merged_segments[-1][1]
                        gap = seg[0] - prev_end - 1
                        
                        if gap <= max_gap:
                            # Join segments
                            merged_segments[-1] = (merged_segments[-1][0], seg[1])
                        else:
                            # Keep separate
                            merged_segments.append(seg)
                    
                    # Update the MHW array with merged segments
                    mhw_joined[:, i, j] = 0  # Reset
                    for start, end in merged_segments:
                        mhw_joined[start:end+1, i, j] = 1
                        
    return mhw_joined

def main():
    # Define region and periods
    region = {
        "lat_min": 64.51,
        "lat_max": 65.71,
        "lon_min": 21.97,
        "lon_max": 23.17
    }
    
    baseline_start = datetime(1992, 1, 1)
    baseline_end = datetime(2002, 12, 31)
    
    target_start = datetime(2016, 6, 1)
    target_end = datetime(2016, 8, 31)
    
    base_dir = "/data/icsa2027_data_20261101T090944Z/s1z"
    
    print("Starting analysis...")
    
    # Step 1: Load baseline data to compute thresholds and climatology
    print("Loading baseline data...")
    
    # Create pools for each day of year
    pools = [[] for _ in range(367)]  # Index 0 unused, 1-366 for days
    
    # Collect all baseline files
    baseline_files = []
    for filename in sorted(os.listdir(base_dir)):
        if filename.startswith('sst_') and filename.endswith('.nc'):
            # Extract date from filename
            date_str = filename[4:-3]  # Remove 'sst_' prefix and '.nc' suffix
            try:
                file_date = datetime.strptime(date_str, '%Y%m%d')
                if baseline_start <= file_date <= baseline_end:
                    baseline_files.append((file_date, filename))
            except ValueError:
                continue
    
    print(f"Found {len(baseline_files)} baseline files")
    
    # Process baseline files to build pools
    for file_date, filename in baseline_files[:5]:  # Just test with first 5 files
        file_path = os.path.join(base_dir, filename)
        ds = xr.open_dataset(file_path, engine="h5netcdf")
        
        # Convert to doy
        doy = date_to_doy(file_date)
        
        # Get SST data and flatten
        sst_vals = ds.analysed_sst.values[0]  # First time step
        flat_sst = sst_vals.flatten()
        
        # Add to appropriate pools
        if doy == 60:
            # For Feb 29, add to both neighbors
            pools[59].extend(flat_sst[~np.isnan(flat_sst)])
            pools[61].extend(flat_sst[~np.isnan(flat_sst)])
        else:
            # Add to corresponding day of year
            pools[doy].extend(flat_sst[~np.isnan(flat_sst)])
        
        ds.close()
        print(f"Processed {filename}, DOY {doy}")
    
    # Calculate thresholds and climatology
    print("Calculating thresholds and climatology...")
    thresholds = np.full(367, np.nan)
    climatology = np.full(367, np.nan)
    
    for doy in range(1, 367):
        if len(pools[doy]) > 0:
            # Compute climatology (mean)
            climatology[doy] = np.nanmean(pools[doy])
            
            # Compute 90th percentile threshold
            thresholds[doy] = np.quantile(pools[doy], 0.9, method='hazen')
        elif doy == 60:
            # Special handling for Feb 29 - use average of neighbors
            if len(pools[59]) > 0 and len(pools[61]) > 0:
                climatology[doy] = (np.nanmean(pools[59]) + np.nanmean(pools[61])) / 2
                # For threshold, combine pools and compute 90th percentile
                combined_pool = pools[59] + pools[61]
                if len(combined_pool) > 0:
                    thresholds[doy] = np.quantile(combined_pool, 0.9, method='hazen')
    
    # Smooth both arrays
    print("Smoothing arrays...")
    smoothed_thresholds = smooth_with_wrapping(thresholds, 31)
    smoothed_climatology = smooth_with_wrapping(climatology, 31)
    
    # Step 2: Load target data for the specific region
    print("Loading target data...")
    
    # Collect target files
    target_files = []
    target_dates = []
    target_doys = []
    
    for filename in sorted(os.listdir(base_dir)):
        if filename.startswith('sst_') and filename.endswith('.nc'):
            date_str = filename[4:-3]
            try:
                file_date = datetime.strptime(date_str, '%Y%m%d')
                if target_start <= file_date <= target_end:
                    target_files.append(filename)
                    target_dates.append(file_date)
                    target_doys.append(date_to_doy(file_date))
            except ValueError:
                continue
    
    print(f"Found {len(target_files)} target files")
    
    # Load first few target files to test
    test_files = target_files[:3]  # Just test with first 3 files
    
    # Load and process first file to get spatial dimensions
    first_file_path = os.path.join(base_dir, test_files[0])
    ds_first = xr.open_dataset(first_file_path, engine="h5netcdf")
    
    # Subset to our region
    lat_indices = np.where((ds_first.latitude >= region['lat_min']) & 
                          (ds_first.latitude <= region['lat_max']))[0]
    lon_indices = np.where((ds_first.longitude >= region['lon_min']) & 
                          (ds_first.longitude <= region['lon_max']))[0]
    
    subset_first = ds_first.isel(latitude=lat_indices, longitude=lon_indices)
    
    print(f"Region subset shape: {subset_first.analysed_sst.shape}")
    print(f"Latitudes: {subset_first.latitude.values}")
    print(f"Longitudes: {subset_first.longitude.values}")
    
    ds_first.close()
    
    # Process all target files
    all_sst_data = []
    
    for filename in test_files:
        file_path = os.path.join(base_dir, filename)
        ds = xr.open_dataset(file_path, engine="h5netcdf")
        
        # Subset to our region
        lat_indices = np.where((ds.latitude >= region['lat_min']) & 
                              (ds.latitude <= region['lat_max']))[0]
        lon_indices = np.where((ds.longitude >= region['lon_min']) & 
                              (ds.longitude <= region['lon_max']))[0]
        
        subset = ds.isel(latitude=lat_indices, longitude=lon_indices)
        all_sst_data.append(subset.analysed_sst.values[0])
        
        ds.close()
    
    # Combine all SST data
    if all_sst_data:
        sst_array = np.stack(all_sst_data, axis=0)
        print(f"Combined SST data shape: {sst_array.shape}")
        
        # Create MHW mask
        mhw_mask = np.zeros((len(target_dates), sst_array.shape[1], sst_array.shape[2]), dtype=np.uint8)
        
        # For each day, compare to threshold and mark hot days
        hot_days = np.zeros((len(target_dates), sst_array.shape[1], sst_array.shape[2]), dtype=bool)
        
        for t in range(len(target_dates)):
            doy = target_doys[t]
            # For each cell, check if SST is above threshold
            hot_days[t] = sst_array[t] >= smoothed_thresholds[doy]
        
        # Find MHW runs
        print("Finding MHW runs...")
        mhw_runs = find_mhw_runs(hot_days)
        
        # Join gaps
        print("Joining gaps...")
        mhw_final = join_gaps(mhw_runs)
        
        # Save results
        print("Saving results...")
        os.makedirs("output", exist_ok=True)
        
        # Create dataset for netcdf output
        coords = {
            'time': target_dates,
            'lat': subset_first.latitude.values,
            'lon': subset_first.longitude.values
        }
        
        # Save to NetCDF
        mhw_da = xr.DataArray(mhw_final, 
                             dims=['time', 'lat', 'lon'],
                             coords=coords,
                             name='mhw',
                             attrs={'units': 'binary', 'long_name': 'Marine Heatwave'})
        
        mhw_da.to_netcdf('output/mhw_mask.nc')
        
        # Generate report
        report = {
            "region": region,
            "baseline_analysed": {
                "start": baseline_start.strftime("%Y-%m-%d"),
                "end": baseline_end.strftime("%Y-%m-%d")
            },
            "target_analysed": {
                "start": target_start.strftime("%Y-%m-%d"),
                "end": target_end.strftime("%Y-%m-%d")
            },
            "events": [],
            "complete": True,
            "caveats": ""
        }
        
        # Find regional events
        # A day is active if at least one sea cell is in an MHW
        active_days = np.any(mhw_final, axis=(1, 2))
        
        # Find maximal runs of consecutive active days
        if np.any(active_days):
            events = []
            in_event = False
            event_start = None
            
            for i, is_active in enumerate(active_days):
                if is_active and not in_event:
                    # Start of new event
                    in_event = True
                    event_start = i
                elif not is_active and in_event:
                    # End of event
                    in_event = False
                    event_end = i - 1
                    events.append({
                        "onset": target_dates[event_start].strftime("%Y-%m-%d"),
                        "end": target_dates[event_end].strftime("%Y-%m-%d")
                    })
            
            # Handle case where event continues to the end
            if in_event:
                event_end = len(active_days) - 1
                events.append({
                    "onset": target_dates[event_start].strftime("%Y-%m-%d"),
                    "end": target_dates[event_end].strftime("%Y-%m-%d")
                })
            
            report["events"] = events
        
        with open('output/report.json', 'w') as f:
            json.dump(report, f, indent=2)
        
        print("Analysis complete!")
        return report
    else:
        print("No target data found")
        return None

# Run the main function
report = main()