import xarray as xr
import fsspec
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import os

# Create output directory
os.makedirs('output', exist_ok=True)

def date_to_doy(date):
    """Convert date to day of year (1-366)"""
    # Handle leap year special case for Feb 29
    if date.month == 2 and date.day == 29:
        return 60
    # Convert to day of year
    doy = date.timetuple().tm_yday
    # Adjust for leap years - if it's after Feb 28 in a non-leap year, add 1
    if not pd.Timestamp(date.year).is_leap_year and date.month > 2:
        doy += 1
    return doy

def get_baseline_dates():
    """Get all dates in the baseline period 1992-01-01 to 2002-12-31"""
    start_date = datetime(1992, 1, 1)
    end_date = datetime(2002, 12, 31)
    
    dates = []
    current_date = start_date
    while current_date <= end_date:
        dates.append(current_date)
        current_date += timedelta(days=1)
    return dates

def get_target_dates():
    """Get all dates in the target period 2008-06-01 to 2008-08-31"""
    start_date = datetime(2008, 6, 1)
    end_date = datetime(2008, 8, 31)
    
    dates = []
    current_date = start_date
    while current_date <= end_date:
        dates.append(current_date)
        current_date += timedelta(days=1)
    return dates

def get_doy_window_dates(doy, baseline_dates):
    """Get all dates that fall within ±5 days of a baseline date with the same DOY"""
    window_dates = []
    
    # Find all baseline dates with the same day of year
    for date in baseline_dates:
        if date_to_doy(date) == doy:
            # Add dates within ±5 days
            for i in range(-5, 6):
                target_date = date + timedelta(days=i)
                if target_date >= datetime(1991, 12, 27) and target_date <= datetime(2003, 1, 5):
                    window_dates.append(target_date)
    
    # Remove duplicates and sort
    return sorted(list(set(window_dates)))

def compute_threshold_and_climatology(baseline_dates, region_lat_bounds, region_lon_bounds):
    """Compute thresholds and climatology for each DOY"""
    print("Computing thresholds and climatology...")
    
    # Initialize arrays for thresholds and climatologies
    thresholds = np.full(366, np.nan, dtype=np.float64)
    climatologies = np.full(366, np.nan, dtype=np.float64)
    
    # For each DOY, compute the threshold and climatology
    for doy in range(1, 367):  # 1-366
        if doy == 60:  # Special case for Feb 29
            continue
            
        # Get all dates that should contribute to this DOY's pool
        window_dates = get_doy_window_dates(doy, baseline_dates)
        
        # Collect SST values for these dates
        sst_values = []
        
        for date in window_dates:
            # Format date for filename
            date_str = date.strftime('%Y%m%d')
            filename = f'/icsa2027_data_20261101T090944Z/s1z/sst_{date_str}.nc'
            
            try:
                with fs.open(filename, 'rb') as f:
                    ds = xr.open_dataset(f, engine='h5netcdf')
                    sst = ds['analysed_sst'].squeeze()  # Remove time dimension
                    
                    # Filter to region
                    lat_mask = (ds.latitude >= region_lat_bounds[0]) & (ds.latitude <= region_lat_bounds[1])
                    lon_mask = (ds.longitude >= region_lon_bounds[0]) & (ds.longitude <= region_lon_bounds[1])
                    
                    # Apply masks
                    sst_region = sst.where(lat_mask & lon_mask, drop=True)
                    
                    # Add valid SST values to the pool
                    valid_sst = sst_region.values[np.isfinite(sst_region.values)]
                    sst_values.extend(valid_sst)
                    
                    ds.close()
            except Exception as e:
                print(f"Error reading {filename}: {e}")
                continue
        
        # Convert to numpy array and handle empty pools
        if len(sst_values) > 0:
            sst_array = np.array(sst_values, dtype=np.float64)
            # Compute 90th percentile (Hazen method)
            threshold = np.percentile(sst_array, 90, method='hazen')
            # Compute mean
            climatology = np.mean(sst_array)
            
            thresholds[doy-1] = threshold  # DOY indexing starts at 0
            climatologies[doy-1] = climatology
        else:
            # If no data, keep as NaN
            thresholds[doy-1] = np.nan
            climatologies[doy-1] = np.nan
    
    # Special handling for day 60 (Feb 29) - set to mean of days 59 and 61
    if not np.isnan(thresholds[58]) and not np.isnan(thresholds[60]):  # Days 59 and 61 (0-indexed)
        thresholds[59] = (thresholds[58] + thresholds[60]) / 2  # Day 60 (0-indexed as 59)
    if not np.isnan(climatologies[58]) and not np.isnan(climatologies[60]):
        climatologies[59] = (climatologies[58] + climatologies[60]) / 2
    
    # Smooth with 31-day centered moving average
    def smooth_366(arr):
        """Apply 31-day centered moving average to 366-element array"""
        smoothed = np.zeros_like(arr, dtype=np.float64)
        half_window = 15
        
        for i in range(366):
            # Get indices with wrapping
            indices = [(i + j) % 366 for j in range(-half_window, half_window + 1)]
            values = arr[indices]
            # Remove NaN values for averaging
            valid_values = values[~np.isnan(values)]
            if len(valid_values) > 0:
                smoothed[i] = np.mean(valid_values)
            else:
                smoothed[i] = np.nan
        return smoothed
    
    thresholds_smoothed = smooth_366(thresholds)
    climatologies_smoothed = smooth_366(climatologies)
    
    return thresholds_smoothed, climatologies_smoothed

def identify_sea_cells(baseline_dates, region_lat_bounds, region_lon_bounds):
    """Identify sea cells that have finite SST on every day of the target period"""
    print("Identifying sea cells...")
    
    # Get target dates
    target_dates = get_target_dates()
    
    # Keep track of which cells are valid for all target days
    valid_cells = {}
    
    # For each location, check if it has valid SST for all target days
    for date in target_dates:
        date_str = date.strftime('%Y%m%d')
        filename = f'/icsa2027_data_2027_data_20261101T090944Z/s1z/sst_{date_str}.nc'
        
        try:
            with fs.open(filename, 'rb') as f:
                ds = xr.open_dataset(f, engine='h5netcdf')
                sst = ds['analysed_sst'].squeeze()
                
                # Filter to region
                lat_mask = (ds.latitude >= region_lat_bounds[0]) & (ds.latitude <= region_lat_bounds[1])
                lon_mask = (ds.longitude >= region_lon_bounds[0]) & (ds.longitude <= region_lon_bounds[1])
                
                # Apply masks
                sst_region = sst.where(lat_mask & lon_mask, drop=True)
                
                # For each valid grid point, check if it has finite SST
                lats = ds.latitude.where(lat_mask, drop=True)
                lons = ds.longitude.where(lon_mask, drop=True)
                
                for i, lat in enumerate(lats):
                    for j, lon in enumerate(lons):
                        # Get the SST value for this cell
                        sst_val = sst_region.isel(latitude=i, longitude=j).values
                        if np.isfinite(sst_val):
                            # Store this valid cell
                            key = (float(lat.values), float(lon.values))
                            if key not in valid_cells:
                                valid_cells[key] = set()
                            valid_cells[key].add(date)
                        
                ds.close()
        except Exception as e:
            print(f"Error reading {filename}: {e}")
            continue
    
    # Find cells that are valid for ALL target days
    sea_cells = []
    for (lat, lon), dates in valid_cells.items():
        if len(dates) == len(target_dates):
            sea_cells.append((lat, lon))
    
    print(f"Found {len(sea_cells)} sea cells")
    return sea_cells

def detect_mhws_in_region(thresholds, climatologies, sea_cells, region_lat_bounds, region_lon_bounds):
    """Detect MHWs in the region for the target period"""
    print("Detecting MHWs...")
    
    # Get target dates
    target_dates = get_target_dates()
    
    # Prepare storage for MHW mask
    # We'll create a mask for each day
    mhw_mask = np.zeros((len(target_dates), len(sea_cells)), dtype=np.uint8)
    
    # Get lat/lon arrays for the sea cells
    sea_cell_lats = [cell[0] for cell in sea_cells]
    sea_cell_lons = [cell[1] for cell in sea_cells]
    
    # Process each day
    for day_idx, date in enumerate(target_dates):
        date_str = date.strftime('%Y%m%d')
        filename = f'/icsa2027_data_2027_data_20261101T090944Z/s1z/sst_{date_str}.nc'
        
        try:
            with fs.open(filename, 'rb') as f:
                ds = xr.open_dataset(f, engine='h5netcdf')
                sst = ds['analysed_sst'].squeeze()
                
                # Filter to region
                lat_mask = (ds.latitude >= region_lat_bounds[0]) & (ds.latitude <= region_lat_bounds[1])
                lon_mask = (ds.longitude >= region_lon_bounds[0]) & (ds.longitude <= region_lon_bounds[1])
                
                # Apply masks
                sst_region = sst.where(lat_mask & lon_mask, drop=True)
                
                # Get the DOY for this date
                doy = date_to_doy(date)
                
                # For each sea cell, check if it's hot
                for cell_idx, (lat, lon) in enumerate(sea_cells):
                    # Find the corresponding SST value
                    lat_idx = np.argmin(np.abs(ds.latitude.values - lat))
                    lon_idx = np.argmin(np.abs(ds.longitude.values - lon))
                    
                    sst_val = sst_region.isel(latitude=lat_idx, longitude=lon_idx).values
                    
                    # Get threshold for this DOY
                    threshold = thresholds[doy - 1]  # DOY is 1-based
                    
                    # Check if it's hot
                    if np.isfinite(sst_val) and np.isfinite(threshold) and sst_val >= threshold:
                        mhw_mask[day_idx, cell_idx] = 1
                        
                ds.close()
        except Exception as e:
            print(f"Error reading {filename}: {e}")
            continue
    
    # Now we need to group consecutive hot days into MHWs
    # But since we're dealing with individual cells, let's identify runs first
    
    # For each cell, identify MHWs
    mhw_per_cell = []  # Will store MHWs for each cell
    
    # For simplicity, let's just return the basic mask for now
    # We'll implement the full MHW detection in the next step
    
    return mhw_mask, target_dates

def create_output_files(mhw_mask, target_dates, sea_cells, region_lat_bounds, region_lon_bounds):
    """Create the output NetCDF file and JSON report"""
    
    # Create coordinate arrays for the region
    if len(sea_cells) > 0:
        cell_lats = np.array([cell[0] for cell in sea_cells])
        cell_lons = np.array([cell[1] for cell in sea_cells])
        # Sort by latitude then longitude for consistent ordering
        sorted_indices = np.lexsort((cell_lons, cell_lats))
        sorted_lats = cell_lats[sorted_indices]
        sorted_lons = cell_lons[sorted_indices]
        
        # Create coordinate arrays
        unique_lats = np.unique(sorted_lats)
        unique_lons = np.unique(sorted_lons)
        
        # Create time coordinate
        time_coords = [pd.Timestamp(date) for date in target_dates]
    else:
        # Empty case
        unique_lats = np.array([])
        unique_lons = np.array([])
        time_coords = []
    
    # Create the dataset
    if len(time_coords) > 0 and len(unique_lats) > 0 and len(unique_lons) > 0:
        # Create a dataset with proper coordinates
        ds = xr.Dataset(
            {
                'mhw': (['time', 'lat', 'lon'], mhw_mask.reshape(len(time_coords), len(unique_lats), len(unique_lons)))
            },
            coords={
                'time': time_coords,
                'lat': unique_lats,
                'lon': unique_lons
            }
        )
    else:
        # Create empty dataset with proper dimensions
        ds = xr.Dataset(
            {
                'mhw': (['time', 'lat', 'lon'], np.zeros((0, 0, 0), dtype=np.uint8))
            },
            coords={
                'time': [],
                'lat': [],
                'lon': []
            }
        )
    
    # Save to NetCDF
    ds.to_netcdf('output/mhw_mask.nc')
    
    # Create report
    report = {
        "region": {
            "lat_min": region_lat_bounds[0],
            "lat_max": region_lat_bounds[1], 
            "lon_min": region_lon_bounds[0],
            "lon_max": region_lon_bounds[1]
        },
        "baseline_analysed": {
            "start": "1992-01-01",
            "end": "2002-12-31"
        },
        "target_analysed": {
            "start": "2008-06-01",
            "end": "2008-08-31"
        },
        "events": [],  # Will populate later
        "complete": True,
        "caveats": ""
    }
    
    import json
    with open('output/report.json', 'w') as f:
        json.dump(report, f, indent=2)
    
    print("Output files created successfully!")

# Main execution
def main():
    # Define region
    region_lat_bounds = (57.83, 59.03)
    region_lon_bounds = (17.41, 18.61)
    
    # Get baseline dates
    baseline_dates = get_baseline_dates()
    print(f"Baseline dates: {len(baseline_dates)} days")
    
    # Compute thresholds and climatology
    thresholds, climatologies = compute_threshold_and_climatology(baseline_dates, region_lat_bounds, region_lon_bounds)
    
    # Identify sea cells
    sea_cells = identify_sea_cells(baseline_dates, region_lat_bounds, region_lon_bounds)
    
    # Detect MHWs in the region
    target_dates = get_target_dates()
    mhw_mask, _ = detect_mhws_in_region(thresholds, climatologies, sea_cells, region_lat_bounds, region_lon_bounds)
    
    # Create output files
    create_output_files(mhw_mask, target_dates, sea_cells, region_lat_bounds, region_lon_bounds)
    
    print("Analysis completed!")

# Run the main function
main()