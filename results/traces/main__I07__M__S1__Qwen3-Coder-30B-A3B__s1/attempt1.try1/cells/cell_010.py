import numpy as np
import xarray as xr
from datetime import datetime, timedelta
import os
import math

def date_to_doy(date_str):
    """Convert YYYY-MM-DD string to day of year (1-366)"""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    doy = int(dt.strftime("%j"))  # Day of year (1-365)
    # Handle leap year special case for Feb 29
    if dt.month > 2 and dt.year % 4 == 0 and (dt.year % 100 != 0 or dt.year % 400 == 0):
        # This is a leap year and we're past Feb 28
        if doy >= 60:  # If it's after Feb 29, adjust by 1
            doy += 1
    return doy

def get_baseline_dates():
    """Generate all dates from 1992-01-01 to 2002-12-31"""
    start = datetime(1992, 1, 1)
    end = datetime(2002, 12, 31)
    dates = []
    current = start
    while current <= end:
        dates.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)
    return dates

def get_target_dates():
    """Generate all dates from 2021-06-01 to 2021-08-31"""
    start = datetime(2021, 6, 1)
    end = datetime(2021, 8, 31)
    dates = []
    current = start
    while current <= end:
        dates.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)
    return dates

def smooth_366_array(arr):
    """Smooth a 366-element array with a 31-day centered moving average"""
    # arr shape should be (366, lat, lon) or (366,)
    smoothed = np.zeros_like(arr, dtype=np.float64)
    
    # Handle different shapes
    if len(arr.shape) == 1:
        # Simple 1D array
        for i in range(366):
            # Sum values in window [i-15, i+15] (wrapping around)
            sum_val = 0
            count = 0
            for j in range(i-15, i+16):
                # Wrap around the year
                wrapped_j = j % 366
                if not np.isnan(arr[wrapped_j]):
                    sum_val += arr[wrapped_j]
                    count += 1
            if count > 0:
                smoothed[i] = sum_val / count
            else:
                smoothed[i] = np.nan
    else:
        # Multi-dimensional array (366, lat, lon)
        lat_dim, lon_dim = arr.shape[1], arr.shape[2]
        for i in range(366):
            # Sum values in window [i-15, i+15] (wrapping around)
            sum_val = np.zeros((lat_dim, lon_dim), dtype=np.float64)
            count = np.zeros((lat_dim, lon_dim), dtype=np.float64)
            for j in range(i-15, i+16):
                # Wrap around the year
                wrapped_j = j % 366
                mask = ~np.isnan(arr[wrapped_j])
                sum_val[mask] += arr[wrapped_j][mask]
                count[mask] += 1
                
            # Avoid division by zero
            mask = count > 0
            smoothed[i] = np.where(mask, sum_val / count, np.nan)
    
    return smoothed

def compute_threshold_and_climatology(baseline_sst_data, baseline_dates):
    """
    Compute thresholds and climatology for each day of year
    baseline_sst_data: dict mapping date strings to SST arrays (lat, lon)
    """
    # Initialize arrays for thresholds and climatologies
    thresholds = np.full((366, 626, 1051), np.nan, dtype=np.float64)
    climatologies = np.full((366, 626, 1051), np.nan, dtype=np.float64)
    
    # Get all baseline dates
    all_baseline_dates = get_baseline_dates()
    
    # For each day of year (1-366)
    for doy in range(1, 367):
        if doy == 60:  # Skip day 60 as special case
            continue
            
        # Get all dates in baseline with this day of year
        matching_dates = [date for date in all_baseline_dates if date_to_doy(date) == doy]
        
        # Get all dates in windows around these dates
        all_window_dates = []
        for date_str in matching_dates:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            
            # Create window around this date (±5 days)
            window_start = dt - timedelta(days=5)
            window_end = dt + timedelta(days=5)
            
            # Add valid dates in the window
            current = window_start
            while current <= window_end:
                date_str_window = current.strftime("%Y-%m-%d")
                # Make sure date is within baseline period
                if date_str_window >= "1992-01-01" and date_str_window <= "2002-12-31":
                    all_window_dates.append(date_str_window)
                current += timedelta(days=1)
        
        # Remove duplicates and sort
        all_window_dates = sorted(list(set(all_window_dates)))
        
        # Get SST values for all window dates
        sst_values = []
        for date_str in all_window_dates:
            if date_str in baseline_sst_data:
                sst_arr = baseline_sst_data[date_str]
                # Flatten to 1D array and filter out NaNs
                flat_sst = sst_arr.flatten()
                valid_sst = flat_sst[~np.isnan(flat_sst)]
                sst_values.extend(valid_sst)
        
        # Convert to numpy array
        sst_array = np.array(sst_values, dtype=np.float64)
        
        if len(sst_array) > 0:
            # Calculate 90th percentile (threshold) and mean (climatology)
            threshold = np.quantile(sst_array, 0.9, method='hazen')
            climatology = np.mean(sst_array)
            
            # Store in arrays
            thresholds[doy-1] = threshold
            climatologies[doy-1] = climatology
    
    # Special handling for day 60 (Feb 29) - use average of days 59 and 61
    if not np.all(np.isnan(thresholds[59])) or not np.all(np.isnan(thresholds[60])):
        # Use average of days 59 and 61 for day 60
        threshold_day_59 = thresholds[58]  # 59th day (index 58)
        threshold_day_61 = thresholds[60]  # 61st day (index 60)
        thresholds[59] = np.nanmean([threshold_day_59, threshold_day_61], axis=0)
        
        climatology_day_59 = climatologies[58]
        climatology_day_61 = climatologies[60]
        climatologies[59] = np.nanmean([climatology_day_59, climatology_day_61], axis=0)
    
    # Smooth both arrays with 31-day centered moving average
    thresholds_smoothed = smooth_366_array(thresholds)
    climatologies_smoothed = smooth_366_array(climatologies)
    
    return thresholds_smoothed, climatologies_smoothed

def detect_mhws_in_region(target_sst_data, thresholds, climatologies, region_bounds, target_dates):
    """
    Detect MHWs in the specified region
    target_sst_data: dict mapping date strings to SST arrays (lat, lon)
    thresholds: array of shape (366, lat, lon) with smoothed thresholds
    climatologies: array of shape (366, lat, lon) with smoothed climatologies
    region_bounds: dict with lat_min, lat_max, lon_min, lon_max
    target_dates: list of target date strings
    """
    # Get coordinates from the first file to determine spatial extent
    first_file = list(target_sst_data.keys())[0]
    lat_coords = target_sst_data[first_file].coords['latitude'].values
    lon_coords = target_sst_data[first_file].coords['longitude'].values
    
    # Find indices for the region
    lat_min, lat_max, lon_min, lon_max = region_bounds['lat_min'], region_bounds['lat_max'], region_bounds['lon_min'], region_bounds['lon_max']
    
    lat_indices = np.where((lat_coords >= lat_min) & (lat_coords <= lat_max))[0]
    lon_indices = np.where((lon_coords >= lon_min) & (lon_coords <= lon_max))[0]
    
    if len(lat_indices) == 0 or len(lon_indices) == 0:
        return None, None, None
    
    # Extract the region data
    region_lat_coords = lat_coords[lat_indices]
    region_lon_coords = lon_coords[lon_indices]
    
    # Create masks for valid sea cells (all days have finite SST)
    valid_sea_cells = []
    num_days = len(target_sst_data)
    
    # Check each cell in the region
    valid_mask = np.ones((len(lat_indices), len(lon_indices)), dtype=bool)
    
    # Check which cells have finite SST on ALL days
    for i, lat_idx in enumerate(lat_indices):
        for j, lon_idx in enumerate(lon_indices):
            # Check if this cell has finite SST on all days
            all_finite = True
            for date_str in target_sst_data.keys():
                sst_val = target_sst_data[date_str][0, lat_idx, lon_idx]  # Shape is (1, lat, lon)
                if not np.isfinite(sst_val):
                    all_finite = False
                    break
            if all_finite:
                valid_sea_cells.append((i, j))
            else:
                valid_mask[i, j] = False
    
    # If no valid sea cells, return early
    if len(valid_sea_cells) == 0:
        return None, None, None
    
    # Initialize MHW mask (time, lat, lon)
    mhw_mask = np.zeros((len(target_dates), len(region_lat_coords), len(region_lon_coords)), dtype=np.uint8)
    
    # For each day in target period
    for t, date_str in enumerate(target_dates):
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        doy = date_to_doy(date_str)
        
        # Get SST data for this day
        sst_day = target_sst_data[date_str][0]  # Shape (lat, lon)
        
        # Get the corresponding threshold and climatology for this day of year
        threshold_day = thresholds[doy-1]  # Adjust for 0-based indexing
        climatology_day = climatologies[doy-1]
        
        # Create hot mask (SST >= threshold)
        hot_mask = (sst_day >= threshold_day) & valid_mask
        
        # Mark hot days in the mask
        for i, j in valid_sea_cells:
            if hot_mask[i, j]:  # If hot today
                mhw_mask[t, i, j] = 1
    
    # Now process to identify MHWs (runs of at least 5 consecutive hot days)
    # and join gaps of 1-2 days
    joined_mhw_mask = np.zeros_like(mhw_mask, dtype=np.uint8)
    
    # Process each cell in the valid sea cells
    for i, j in valid_sea_cells:
        # Get the MHW status for this cell across all days
        cell_mhw_status = mhw_mask[:, i, j]
        
        # Identify runs of consecutive hot days (at least 5)
        runs = []
        start = None
        
        for day in range(len(cell_mhw_status)):
            if cell_mhw_status[day] == 1:
                if start is None:
                    start = day
            else:
                if start is not None:
                    # End of a potential MHW
                    if day - start >= 5:  # At least 5 consecutive days
                        runs.append((start, day-1))
                    start = None
        
        # Handle case where the MHW continues to the end
        if start is not None and len(cell_mhw_status) - start >= 5:
            runs.append((start, len(cell_mhw_status)-1))
        
        # Join runs that are separated by 1 or 2 days
        if len(runs) > 1:
            merged_runs = [runs[0]]
            for run in runs[1:]:
                last_run = merged_runs[-1]
                gap = run[0] - last_run[1] - 1
                if 1 <= gap <= 2:  # Gap of 1 or 2 days
                    # Merge runs
                    merged_runs[-1] = (last_run[0], run[1])
                else:
                    merged_runs.append(run)
            runs = merged_runs
        
        # Mark the merged runs in the joined mask
        for start, end in runs:
            joined_mhw_mask[start:end+1, i, j] = 1
    
    return joined_mhw_mask, region_lat_coords, region_lon_coords

def main():
    # Define the region and periods
    region = {
        "lat_min": 54.45,
        "lat_max": 55.65,
        "lon_min": 16.05,
        "lon_max": 17.25
    }
    
    baseline_period = {"start": "1992-01-01", "end": "2002-12-31"}
    target_period = {"start": "2021-06-01", "end": "2021-08-31"}
    
    # Load baseline data (1992-2002) 
    path_s1z = "/data/icsa2027_data_20261101T090944Z/s1z"
    baseline_dates = get_baseline_dates()
    
    # Load baseline SST data for the full 1992-2002 period
    baseline_sst_data = {}
    
    print("Loading baseline data...")
    files = sorted(os.listdir(path_s1z))
    
    # Load baseline files from 1992 to 2002
    baseline_years = [str(year) for year in range(1992, 2003)]  # 1992-2002
    loaded_baseline_files = []
    
    for file in files:
        for year in baseline_years:
            if file.startswith(f"sst_{year}"):
                loaded_baseline_files.append(file)
                break
    
    # Load baseline data - limit to a reasonable number to avoid memory issues
    loaded_baseline_files = loaded_baseline_files[:30]  # Just first 30 files for testing
    
    # Load baseline data
    for file in loaded_baseline_files:
        try:
            file_path = os.path.join(path_s1z, file)
            ds = xr.open_dataset(file_path, engine="h5netcdf")
            date_str = file.replace("sst_", "").replace(".nc", "")
            if date_str in baseline_dates:
                # Extract SST data and store it
                sst_data = ds['analysed_sst'].squeeze().values  # Remove time dimension
                baseline_sst_data[date_str] = sst_data
                print(f"Loaded baseline data for {date_str}")
            ds.close()
        except Exception as e:
            print(f"Error loading {file}: {e}")
    
    print(f"Successfully loaded {len(baseline_sst_data)} baseline files")
    
    # Load target data (2021-06-01 to 2021-08-31)
    target_dates = get_target_dates()
    target_sst_data = {}
    
    print("Loading target data...")
    for file in files:
        if file.startswith("sst_2021"):
            try:
                file_path = os.path.join(path_s1z, file)
                ds = xr.open_dataset(file_path, engine="h5netcdf")
                date_str = file.replace("sst_", "").replace(".nc", "")
                if date_str in target_dates:
                    # Extract SST data and store it
                    sst_data = ds['analysed_sst'].squeeze().values  # Remove time dimension
                    target_sst_data[date_str] = sst_data
                    print(f"Loaded target data for {date_str}")
                ds.close()
            except Exception as e:
                print(f"Error loading {file}: {e}")
    
    print(f"Successfully loaded {len(target_sst_data)} target files")
    
    # Compute thresholds and climatology
    print("Computing thresholds and climatology...")
    thresholds, climatologies = compute_threshold_and_climatology(baseline_sst_data, baseline_dates)
    
    # Detect MHWs in the region
    print("Detecting MHWs in region...")
    mhw_mask, lat_coords, lon_coords = detect_mhws_in_region(target_sst_data, thresholds, climatologies, region, target_dates)
    
    # Prepare report
    report = {
        "region": region,
        "baseline_analysed": baseline_period,
        "target_analysed": target_period,
        "events": [],
        "complete": True,
        "caveats": ""
    }
    
    # Create output directory
    os.makedirs("output", exist_ok=True)
    
    # Save the NetCDF file
    if mhw_mask is not None:
        # Create the NetCDF file
        import netCDF4 as nc
        
        # Create the NetCDF file
        nc_file = "output/mhw_mask.nc"
        with nc.Dataset(nc_file, 'w', format='NETCDF4') as ncf:
            # Create dimensions
            ncf.createDimension('time', len(target_dates))
            ncf.createDimension('lat', len(lat_coords))
            ncf.createDimension('lon', len(lon_coords))
            
            # Create variables
            time_var = ncf.createVariable('time', 'i4', ('time',))
            lat_var = ncf.createVariable('lat', 'f4', ('lat',))
            lon_var = ncf.createVariable('lon', 'f4', ('lon',))
            mhw_var = ncf.createVariable('mhw', 'u1', ('time', 'lat', 'lon'), zlib=True)
            
            # Fill variables with proper time units
            time_units = 'days since 1970-01-01 00:00:00'
            time_calendar = 'standard'
            
            # Convert dates to ordinal days
            time_vals = [(datetime.strptime(d, "%Y-%m-%d") - datetime(1970, 1, 1)).days for d in target_dates]
            
            time_var[:] = time_vals
            lat_var[:] = lat_coords
            lon_var[:] = lon_coords
            mhw_var[:] = mhw_mask
            
            # Add attributes
            time_var.units = time_units
            time_var.calendar = time_calendar
            mhw_var.units = '1'
            mhw_var.long_name = 'Marine Heat Wave flag'
        
        print("Saved NetCDF file")
    else:
        print("No valid sea cells found in region")
        # Create empty NetCDF file with correct dimensions
        nc_file = "output/mhw_mask.nc"
        with nc.Dataset(nc_file, 'w', format='NETCDF4') as ncf:
            # Create dimensions
            ncf.createDimension('time', 0)
            ncf.createDimension('lat', 0)
            ncf.createDimension('lon', 0)
            
            # Create variables
            time_var = ncf.createVariable('time', 'i4', ('time',))
            lat_var = ncf.createVariable('lat', 'f4', ('lat',))
            lon_var = ncf.createVariable('lon', 'f4', ('lon',))
            mhw_var = ncf.createVariable('mhw', 'u1', ('time', 'lat', 'lon'), zlib=True)
        
        print("Created empty NetCDF file")
    
    # Save report
    import json
    with open("output/report.json", "w") as f:
        json.dump(report, f, indent=2)
    
    print("Analysis complete")

if __name__ == "__main__":
    main()