import fsspec
import xarray as xr
import numpy as np
from datetime import datetime, timedelta
import netCDF4 as nc
import os
from scipy import stats

# Create output directory
os.makedirs('output', exist_ok=True)

# Create filesystem
fs = fsspec.filesystem('onedata')

# Download the file
remote_path = '/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
local_path = '/work/sst_s2.nc'
fs.get(remote_path, local_path)

# Open with xarray
ds = xr.open_dataset(local_path, engine='h5netcdf')

# Define the region
lat_min, lat_max = 56.13, 57.33
lon_min, lon_max = 17.71, 18.91

# Find indices for the region
lat_indices = np.where((ds['latitude'] >= lat_min) & (ds['latitude'] <= lat_max))[0]
lon_indices = np.where((ds['longitude'] >= lon_min) & (ds['longitude'] <= lon_max))[0]

# Get the subset of data for our region
subset_ds = ds.sel(latitude=ds['latitude'][lat_indices], longitude=ds['longitude'][lon_indices])

# Define target period
target_start = datetime(2015, 6, 1)
target_end = datetime(2015, 8, 31)

# Convert dates to time indices
time_values = ds['time'].values
target_start_idx = np.where(time_values >= np.datetime64(target_start))[0][0]
target_end_idx = np.where(time_values <= np.datetime64(target_end))[0][-1]

# Define baseline period (1992-2002)
baseline_start = datetime(1992, 1, 1)
baseline_end = datetime(2002, 12, 31)

baseline_start_idx = np.where(time_values >= np.datetime64(baseline_start))[0][0]
baseline_end_idx = np.where(time_values <= np.datetime64(baseline_end))[0][-1]

print(f"Target period: {target_start} to {target_end}")
print(f"Baseline period: {baseline_start} to {baseline_end}")

# Create helper function to convert datetime to day-of-year
def get_doy(dt):
    """Convert datetime to day-of-year (1-366)"""
    # Create a date object without time component
    d = dt.date()
    # Get the day of year
    doy = d.timetuple().tm_yday
    
    # Special handling for Feb 29 in leap years
    if dt.month == 2 and dt.day == 29:
        return 60
    elif dt.month > 2 and (dt.year % 4 == 0 and dt.year != 1900):
        # For leap years, adjust day numbers after Feb 29
        if doy > 59:  # After Feb 29
            doy -= 1
    
    return doy

# Create time arrays
baseline_times = time_values[baseline_start_idx:baseline_end_idx+1]
target_times = time_values[target_start_idx:target_end_idx+1]

baseline_doy = np.array([get_doy(datetime.fromisoformat(str(t)[:10])) for t in baseline_times])
target_doy = np.array([get_doy(datetime.fromisoformat(str(t)[:10])) for t in target_times])

# Function to compute quantiles with numpy's hazen method
def quantile_hazen(data, q):
    """Compute quantile using Hazen method (numpy method='hazen')"""
    if len(data) == 0:
        return np.nan
    return np.quantile(data, q, method='hazen')

# Step 1: Identify sea cells (cells with finite SST on every day)
def identify_sea_cells():
    """Identify sea cells (those with finite SST on every day of baseline period)"""
    # Load baseline data for the region only
    baseline_sst = ds['analysed_sst'].values[baseline_start_idx:baseline_end_idx+1, :, :]
    # Subset to our region
    baseline_sst_region = baseline_sst[:, lat_indices, :][:, :, lon_indices]
    
    # Check if each cell has finite values for all times
    finite_mask = np.isfinite(baseline_sst_region)
    sea_cell_mask = np.all(finite_mask, axis=0)
    
    # Clean up memory
    del baseline_sst
    del baseline_sst_region
    
    return sea_cell_mask

# Step 2: Compute thresholds and climatology
def compute_thresholds_and_climatology():
    """Compute thresholds and climatology for each day of year"""
    n_days = 366
    thresholds = np.full(n_days, np.nan, dtype=np.float64)
    climatologies = np.full(n_days, np.nan, dtype=np.float64)
    
    # Load baseline data for the region only
    baseline_sst = ds['analysed_sst'].values[baseline_start_idx:baseline_end_idx+1, :, :]
    baseline_sst_region = baseline_sst[:, lat_indices, :][:, :, lon_indices]
    
    # Process each day of year
    for doy in range(1, n_days + 1):
        if doy == 60:  # Special case for Feb 29
            continue
            
        # Find all baseline dates with matching day of year
        matching_indices = np.where(baseline_doy == doy)[0]
        
        if len(matching_indices) == 0:
            continue
            
        # Get the SST values for these dates for all cells in region
        pool_sst = baseline_sst_region[matching_indices, :, :]
        
        # Flatten to get all valid SST values for this day of year
        flat_pool = pool_sst.flatten()
        # Remove NaN values
        valid_pool = flat_pool[np.isfinite(flat_pool)]
        
        if len(valid_pool) > 0:
            # Compute 90th percentile threshold
            thresholds[doy-1] = quantile_hazen(valid_pool, 0.9)
            # Compute mean climatology  
            climatologies[doy-1] = np.mean(valid_pool)
    
    # Handle day 60 (Feb 29) - set to mean of days 59 and 61
    if not np.isnan(thresholds[58]) and not np.isnan(thresholds[59]) and not np.isnan(thresholds[60]):
        thresholds[59] = (thresholds[58] + thresholds[60]) / 2
        climatologies[59] = (climatologies[58] + climatologies[60]) / 2
    
    # Smooth with 31-day centered moving average (wrapping around year)
    def smooth_with_moving_average(data):
        """Smooth data with 31-day centered moving average, wrapping around year"""
        smoothed = np.zeros_like(data, dtype=np.float64)
        window_size = 31
        half_window = window_size // 2
        
        for i in range(len(data)):
            # Get indices for the window
            indices = [(i + j - half_window) % len(data) for j in range(window_size)]
            # Calculate mean ignoring NaN values
            window_data = data[indices]
            valid_data = window_data[np.isfinite(window_data)]
            if len(valid_data) > 0:
                smoothed[i] = np.mean(valid_data)
            else:
                smoothed[i] = np.nan
        return smoothed
    
    # Apply smoothing to both thresholds and climatologies
    smoothed_thresholds = smooth_with_moving_average(thresholds)
    smoothed_climatologies = smooth_with_moving_average(climatologies)
    
    # Clean up memory
    del baseline_sst
    del baseline_sst_region
    
    return smoothed_thresholds, smoothed_climatologies

# Step 3: Find MHWs for each cell
def find_mhws_per_cell():
    """Find MHWs for each cell efficiently"""
    # Load target data for the region only
    target_sst = ds['analysed_sst'].values[target_start_idx:target_end_idx+1, :, :]
    target_sst_region = target_sst[:, lat_indices, :][:, :, lon_indices]
    
    n_time, n_lat, n_lon = target_sst_region.shape
    
    # Initialize MHW mask
    mhw_mask = np.zeros((n_time, n_lat, n_lon), dtype=np.uint8)
    
    # For each cell, process one at a time to save memory
    for i in range(n_lat):
        # Process each column of the region
        if i % 10 == 0:
            print(f"Processing row {i}/{n_lat}")
            
        for j in range(n_lon):
            # Get SST for this cell across all time
            cell_sst = target_sst_region[:, i, j]
            
            # Identify hot days for this cell
            hot_days = np.zeros(n_time, dtype=bool)
            for t in range(n_time):
                doy = target_doy[t]
                if not np.isnan(cell_sst[t]):
                    hot_days[t] = cell_sst[t] >= thresholds[doy-1]
            
            # Find runs of at least 5 consecutive hot days
            # Then join gaps of 1 or 2 days
            mhw_runs = []
            k = 0
            while k < n_time:
                if hot_days[k]:
                    start = k
                    # Extend the run
                    while k < n_time and hot_days[k]:
                        k += 1
                    end = k - 1
                    
                    # Check if this is at least 5 days
                    if end - start + 1 >= 5:
                        mhw_runs.append((start, end))
                    else:
                        # If less than 5 days, don't count as MHW
                        pass
                else:
                    k += 1
            
            # Join gaps of 1 or 2 days
            if len(mhw_runs) > 1:
                merged_runs = [mhw_runs[0]]
                for start, end in mhw_runs[1:]:
                    prev_start, prev_end = merged_runs[-1]
                    # If gap is 1 or 2 days, merge
                    if start - prev_end <= 2:
                        merged_runs[-1] = (prev_start, end)
                    else:
                        merged_runs.append((start, end))
                mhw_runs = merged_runs
                
            # Mark MHW days in the mask
            for start, end in mhw_runs:
                mhw_mask[start:end+1, i, j] = 1
    
    # Clean up memory
    del target_sst
    del target_sst_region
    
    return mhw_mask

# Step 4: Regional events
def find_regional_events(mhw_mask):
    """Find regional MHW events based on the MHW mask"""
    n_time, n_lat, n_lon = mhw_mask.shape
    
    # A day is active if at least one sea cell is inside an MHW
    active_days = np.any(mhw_mask, axis=(1, 2))  # Shape: (n_time,)
    
    # Find maximal runs of consecutive active days
    events = []
    i = 0
    while i < n_time:
        if active_days[i]:
            start = i
            # Extend until inactive day
            while i < n_time and active_days[i]:
                i += 1
            end = i - 1
            # Add event
            events.append((start, end))
        else:
            i += 1
    
    return events, active_days

# Execute the algorithm step by step
print("Step 1: Identifying sea cells...")
sea_cell_mask = identify_sea_cells()
print(f"Number of sea cells: {np.sum(sea_cell_mask)} out of {sea_cell_mask.size}")

print("Step 2: Computing thresholds and climatology...")
thresholds, climatologies = compute_thresholds_and_climatology()
print("Thresholds and climatologies computed")

print("Step 3: Finding MHWs per cell...")
mhw_mask = find_mhws_per_cell()
print("MHWs found per cell")

print("Step 4: Finding regional events...")
regional_events, active_days = find_regional_events(mhw_mask)
print(f"Found {len(regional_events)} regional events")

# Format events for output
formatted_events = []
for start_idx, end_idx in regional_events:
    start_date = datetime.fromisoformat(str(target_times[start_idx])[:10])
    end_date = datetime.fromisoformat(str(target_times[end_idx])[:10])
    formatted_events.append({
        "onset": start_date.strftime("%Y-%m-%d"),
        "end": end_date.strftime("%Y-%m-%d")
    })

# Prepare report
report = {
    "region": {
        "lat_min": lat_min,
        "lat_max": lat_max,
        "lon_min": lon_min,
        "lon_max": lon_max
    },
    "baseline_analysed": {
        "start": baseline_start.strftime("%Y-%m-%d"),
        "end": baseline_end.strftime("%Y-%m-%d")
    },
    "target_analysed": {
        "start": target_start.strftime("%Y-%m-%d"),
        "end": target_end.strftime("%Y-%m-%d")
    },
    "events": formatted_events,
    "complete": True,
    "caveats": ""
}

# Write report
import json
with open('output/report.json', 'w') as f:
    json.dump(report, f, indent=2)

print("Report saved to output/report.json")

# Create NetCDF file for mhw_mask
print("Creating NetCDF file...")
lat_vals = ds['latitude'].values[lat_indices]
lon_vals = ds['longitude'].values[lon_indices]
time_vals = target_times

# Create the NetCDF file
nc_file = nc.Dataset('output/mhw_mask.nc', 'w', format='NETCDF4')

# Create dimensions
nc_file.createDimension('time', None)
nc_file.createDimension('lat', len(lat_vals))
nc_file.createDimension('lon', len(lon_vals))

# Create variables
time_var = nc_file.createVariable('time', 'i8', ('time',))
lat_var = nc_file.createVariable('lat', 'f4', ('lat',))
lon_var = nc_file.createVariable('lon', 'f4', ('lon',))
mhw_var = nc_file.createVariable('mhw', 'u1', ('time', 'lat', 'lon'), zlib=True)

# Fill in the data
time_var[:] = time_vals
lat_var[:] = lat_vals
lon_var[:] = lon_vals
mhw_var[:] = mhw_mask

# Add attributes
time_var.units = 'days since 1970-01-01 00:00:00'
time_var.calendar = 'standard'
mhw_var.units = '1'
mhw_var.long_name = 'Marine Heat Wave flag'

nc_file.close()

print("NetCDF file created: output/mhw_mask.nc")
print("Analysis complete!")