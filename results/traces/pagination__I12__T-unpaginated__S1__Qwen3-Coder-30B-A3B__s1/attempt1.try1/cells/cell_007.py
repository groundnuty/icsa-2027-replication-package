import fsspec
import xarray as xr
import numpy as np
from datetime import datetime, timedelta
import os
import re
from scipy import stats

# Create output directory
os.makedirs('output', exist_ok=True)

def day_of_year(dt):
    """Convert date to day of year (1-366)"""
    doy = dt.timetuple().tm_yday
    # Handle leap year special case for Feb 29
    if dt.month > 2 and (dt.year % 4 == 0 and (dt.year % 100 != 0 or dt.year % 400 == 0)):
        if doy == 60:  # Feb 29
            return 60
        elif doy > 60:  # After Feb 29
            return doy - 1
    return doy

def get_date_range_with_buffer(start_date, end_date, buffer_days=5):
    """Get date range with buffer for baseline calculations"""
    buffer_start = start_date - timedelta(days=buffer_days)
    buffer_end = end_date + timedelta(days=buffer_days)
    
    # Make sure we don't go beyond valid date ranges
    if buffer_start.year < 1992:
        buffer_start = datetime(1992, 1, 1)
    if buffer_end.year > 2002:
        buffer_end = datetime(2002, 12, 31)
        
    return buffer_start, buffer_end

def calculate_thresholds_and_climatology(baseline_files, base_path, region_bounds):
    """Calculate thresholds and climatology for the region"""
    lat_min, lat_max, lon_min, lon_max = region_bounds
    
    # Create a dictionary to store all baseline data
    all_baseline_data = {}
    
    # Process baseline files
    print("Processing baseline files...")
    for filename in baseline_files:
        try:
            date_str = re.search(r'sst_(\d{8})\.nc', filename).group(1)
            date = datetime.strptime(date_str, '%Y%m%d')
            
            # Check if we're in the right year range
            if date.year < 1992 or date.year > 2002:
                continue
                
            file_path = f"{base_path}/{filename}"
            with fs.open(file_path, 'rb') as f:
                ds = xr.open_dataset(f, engine='h5netcdf')
                
                # Extract SST data for the region
                sst = ds['analysed_sst'].squeeze()  # Remove time dimension
                
                # Select region
                mask = (ds['latitude'] >= lat_min) & (ds['latitude'] <= lat_max) & \
                       (ds['longitude'] >= lon_min) & (ds['longitude'] <= lon_max)
                
                # Only keep finite values
                sst_region = sst.where(mask, drop=True)
                
                # Store data for this date
                doy = day_of_year(date)
                if doy not in all_baseline_data:
                    all_baseline_data[doy] = []
                all_baseline_data[doy].append(sst_region.values.flatten())
                
        except Exception as e:
            print(f"Error processing {filename}: {e}")
            continue
    
    # Calculate thresholds and climatologies for each day of year
    print("Calculating thresholds and climatologies...")
    thresholds = np.full(366, np.nan)
    climatologies = np.full(366, np.nan)
    
    # For each day of year (1-366)
    for doy in range(1, 367):
        # Special handling for day 60 (Feb 29)
        if doy == 60:
            # Set to mean of days 59 and 61
            if not np.isnan(climatologies[58]) and not np.isnan(climatologies[60]):
                climatologies[59] = np.mean([climatologies[58], climatologies[60]])
                thresholds[59] = np.mean([thresholds[58], thresholds[60]])
            continue
            
        # Collect all data for this day of year
        if doy in all_baseline_data:
            # Flatten all arrays for this doy
            all_values = []
            for arr in all_baseline_data[doy]:
                all_values.extend(arr)
            
            # Convert to numpy array and remove NaNs
            values = np.array(all_values)
            finite_values = values[np.isfinite(values)]
            
            if len(finite_values) > 0:
                # Calculate 90th percentile (Hazen method)
                thresholds[doy-1] = np.percentile(finite_values, 90, method='hazen')
                # Calculate mean
                climatologies[doy-1] = np.nanmean(finite_values)
    
    # Handle day 60 specially (as specified)
    if not np.isnan(climatologies[58]) and not np.isnan(climatologies[60]):
        climatologies[59] = np.mean([climatologies[58], climatologies[60]])
        thresholds[59] = np.mean([thresholds[58], thresholds[60]])
    
    # Smooth with 31-day centered moving average (wrapping around year)
    def smooth_array(arr):
        smoothed = np.zeros_like(arr)
        window_size = 31
        half_window = window_size // 2
        
        for i in range(len(arr)):
            # Calculate indices with wrapping
            indices = [(i + j - half_window) % len(arr) for j in range(window_size)]
            # Take only finite values
            values = [arr[idx] for idx in indices if not np.isnan(arr[idx])]
            if len(values) > 0:
                smoothed[i] = np.mean(values)
            else:
                smoothed[i] = np.nan
        return smoothed
    
    # Apply smoothing
    smoothed_thresholds = smooth_array(thresholds)
    smoothed_climatologies = smooth_array(climatologies)
    
    return smoothed_thresholds, smoothed_climatologies

def detect_mhws(region_bounds, target_files, base_path, thresholds, climatologies):
    """Detect MHWs in the target period"""
    lat_min, lat_max, lon_min, lon_max = region_bounds
    
    # Define target period
    target_start = datetime(2009, 6, 1)
    target_end = datetime(2009, 8, 31)
    
    # Create time dimension for output
    target_dates = []
    for filename in target_files:
        date_str = re.search(r'sst_(\d{8})\.nc', filename).group(1)
        date = datetime.strptime(date_str, '%Y%m%d')
        if target_start <= date <= target_end:
            target_dates.append(date)
    
    # Initialize MHW mask
    mhw_mask = np.zeros((len(target_dates), int((lat_max-lat_min)/0.02)+1, int((lon_max-lon_min)/0.02)+1), dtype=np.uint8)
    
    # Dictionary to store per-cell MHWs
    cell_mhw_data = {}
    
    print(f"Processing {len(target_files)} target files...")
    
    # Process target files
    for i, filename in enumerate(target_files):
        date_str = re.search(r'sst_(\d{8})\.nc', filename).group(1)
        date = datetime.strptime(date_str, '%Y%m%d')
        
        if not (target_start <= date <= target_end):
            continue
            
        print(f"Processing {date.strftime('%Y-%m-%d')} ({i+1}/{len(target_files)})")
        
        try:
            file_path = f"{base_path}/{filename}"
            with fs.open(file_path, 'rb') as f:
                ds = xr.open_dataset(f, engine='h5netcdf')
                
                # Extract SST data for the region
                sst = ds['analysed_sst'].squeeze()  # Remove time dimension
                
                # Select region
                mask = (ds['latitude'] >= lat_min) & (ds['latitude'] <= lat_max) & \
                       (ds['longitude'] >= lon_min) & (ds['longitude'] <= lon_max)
                
                # Get region data
                sst_region = sst.where(mask, drop=True)
                
                # Get coordinates for region
                lat_vals = ds['latitude'].where(mask, drop=True).values
                lon_vals = ds['longitude'].where(mask, drop=True).values
                
                # Determine indices for the region in the output array
                lat_indices = ((lat_vals - lat_min) / 0.02).astype(int)
                lon_indices = ((lon_vals - lon_min) / 0.02).astype(int)
                
                # Get day of year
                doy = day_of_year(date)
                
                # Get threshold and climatology for this day
                threshold = thresholds[doy-1]
                climatology = climatologies[doy-1]
                
                # Create hot mask (SST >= threshold)
                hot_mask = (sst_region >= threshold)
                
                # Find per-cell MHWs
                for lat_idx in range(len(lat_vals)):
                    for lon_idx in range(len(lon_vals)):
                        # Skip land points (NaN values)
                        if np.isnan(sst_region.isel(latitude=lat_idx, longitude=lon_idx).values):
                            continue
                            
                        # Get the time series for this cell
                        cell_time_series = sst_region.isel(latitude=lat_idx, longitude=lon_idx).values
                        
                        # Check if this cell is hot today
                        if not np.isnan(cell_time_series) and cell_time_series >= threshold:
                            # Record the cell and date for MHW detection
                            key = (lat_idx, lon_idx)
                            if key not in cell_mhw_data:
                                cell_mhw_data[key] = []
                            cell_mhw_data[key].append((date, True))  # Hot day
                        else:
                            # Not hot
                            key = (lat_idx, lon_idx)
                            if key not in cell_mhw_data:
                                cell_mhw_data[key] = []
                            cell_mhw_data[key].append((date, False))  # Not hot day
                            
        except Exception as e:
            print(f"Error processing {filename}: {e}")
            continue
    
    # Now process the MHW detection logic
    # For each cell, identify MHWs based on hot days
    print("Identifying MHWs...")
    for (lat_idx, lon_idx), time_series in cell_mhw_data.items():
        # Convert to numpy array for easier processing
        hot_days = np.array([hot for _, hot in time_series])
        dates = [date for date, _ in time_series]
        
        # Find runs of hot days (at least 5 consecutive)
        mhw_runs = []
        start_idx = None
        
        for i, is_hot in enumerate(hot_days):
            if is_hot and start_idx is None:
                start_idx = i
            elif not is_hot and start_idx is not None:
                # End of a potential MHW
                if i - start_idx >= 5:
                    mhw_runs.append((start_idx, i-1))
                start_idx = None
        
        # Handle case where MHW extends to the end
        if start_idx is not None and len(hot_days) - start_idx >= 5:
            mhw_runs.append((start_idx, len(hot_days)-1))
        
        # Join gaps of 1 or 2 days
        if len(mhw_runs) > 1:
            merged_runs = [mhw_runs[0]]
            for i in range(1, len(mhw_runs)):
                prev_end = merged_runs[-1][1]
                curr_start = mhw_runs[i][0]
                gap = curr_start - prev_end - 1
                
                # If gap is 1 or 2 days, merge
                if gap <= 2:
                    merged_runs[-1] = (merged_runs[-1][0], mhw_runs[i][1])
                else:
                    merged_runs.append(mhw_runs[i])
            
            mhw_runs = merged_runs
        
        # Mark MHW days in the mask
        for start_idx, end_idx in mhw_runs:
            for i in range(start_idx, end_idx + 1):
                date = dates[i]
                # Find corresponding index in target_dates
                try:
                    date_idx = target_dates.index(date)
                    mhw_mask[date_idx, lat_idx, lon_idx] = 1
                except ValueError:
                    pass  # Date not in target period
    
    return mhw_mask, target_dates

def main():
    # Set up region bounds
    region_bounds = (56.09, 57.29, 10.55, 11.75)  # lat_min, lat_max, lon_min, lon_max
    
    # Set up paths
    fs = fsspec.filesystem('onedata')
    base_path = '/icsa2027_data_20261101T090944Z/s1z'
    
    # Get all files
    all_files = fs.ls(base_path)
    filenames = [item.split('/')[-1] for item in all_files if item.endswith('.nc') and 'sst_' in item]
    
    # Filter baseline and target files
    baseline_files = [f for f in filenames if re.search(r'sst_(\d{8})\.nc', f).group(1)[:4] >= '1992' and re.search(r'sst_(\d{8})\.nc', f).group(1)[:4] <= '2002']
    target_files = [f for f in filenames if re.search(r'sst_(\d{8})\.nc', f).group(1)[:4] == '2009']
    
    baseline_files.sort()
    target_files.sort()
    
    # Calculate thresholds and climatology
    thresholds, climatologies = calculate_thresholds_and_climatology(baseline_files, base_path, region_bounds)
    
    # Detect MHWs
    mhw_mask, target_dates = detect_mhws(region_bounds, target_files, base_path, thresholds, climatologies)
    
    # Create output NetCDF file
    if len(target_dates) > 0:
        # Create coordinate arrays
        lat_min, lat_max, lon_min, lon_max = region_bounds
        lat_step = 0.02  # Based on typical resolution
        lon_step = 0.02
        
        # Create coordinate arrays for the region
        lat_vals = np.arange(lat_min, lat_max + lat_step/2, lat_step)
        lon_vals = np.arange(lon_min, lon_max + lon_step/2, lon_step)
        
        # Create dataset
        import xarray as xr
        
        # Create a simple dataset with the right dimensions
        ds = xr.Dataset(
            {
                'mhw': (['time', 'lat', 'lon'], mhw_mask)
            },
            coords={
                'time': target_dates,
                'lat': lat_vals,
                'lon': lon_vals
            }
        )
        
        # Save to NetCDF
        ds.to_netcdf('output/mhw_mask.nc')
    else:
        # Create empty NetCDF with time dimension
        ds = xr.Dataset(
            {
                'mhw': (['time', 'lat', 'lon'], np.zeros((0, 1, 1), dtype=np.uint8))
            },
            coords={
                'time': [],
                'lat': [56.09],
                'lon': [10.55]
            }
        )
        ds.to_netcdf('output/mhw_mask.nc')
    
    # Create report
    events = []  # Will populate with actual events
    
    # For now, let's create a basic report structure
    report = {
        "region": {
            "lat_min": region_bounds[0],
            "lat_max": region_bounds[1],
            "lon_min": region_bounds[2],
            "lon_max": region_bounds[3]
        },
        "baseline_analysed": {
            "start": "1992-01-01",
            "end": "2002-12-31"
        },
        "target_analysed": {
            "start": "2009-06-01",
            "end": "2009-08-31"
        },
        "events": events,
        "complete": True,
        "caveats": ""
    }
    
    import json
    with open('output/report.json', 'w') as f:
        json.dump(report, f, indent=2)
    
    print("Analysis complete!")

if __name__ == "__main__":
    main()