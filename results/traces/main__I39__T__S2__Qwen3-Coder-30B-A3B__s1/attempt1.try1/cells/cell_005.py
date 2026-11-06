import fsspec
import xarray as xr
import numpy as np
from datetime import datetime, timedelta
import os

# Create output directory
os.makedirs('output', exist_ok=True)

# Create the filesystem
fs = fsspec.filesystem('onedata')

# Open the dataset and extract all required data at once
with fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    
    # Define our region and time period
    lat_min, lat_max = 60.49, 61.69
    lon_min, lon_max = 17.25, 18.45
    start_date = datetime(2010, 6, 1)
    end_date = datetime(2010, 8, 31)
    baseline_start = datetime(1992, 1, 1)
    baseline_end = datetime(2002, 12, 31)

    # Find indices for our region
    lat_indices = np.where((ds['latitude'] >= lat_min) & (ds['latitude'] <= lat_max))[0]
    lon_indices = np.where((ds['longitude'] >= lon_min) & (ds['longitude'] <= lon_max))[0]

    # Filter data for our region
    subset_ds = ds.isel(latitude=lat_indices, longitude=lon_indices)

    # Get the actual coordinate values for our region
    lat_vals = subset_ds['latitude'].values
    lon_vals = subset_ds['longitude'].values

    # Find time indices for our periods
    target_indices = np.where((subset_ds['time'] >= np.datetime64(start_date)) & 
                             (subset_ds['time'] <= np.datetime64(end_date)))[0]

    baseline_indices = np.where((subset_ds['time'] >= np.datetime64(baseline_start)) & 
                               (subset_ds['time'] <= np.datetime64(baseline_end)))[0]

    # Extract SST data for the full dataset (we'll slice it as needed)
    sst_full = subset_ds['analysed_sst'].values  # Shape: (time, lat, lon)

    # Extract data for baseline and target periods
    sst_baseline = sst_full[baseline_indices]  # Shape: (baseline_days, lat, lon)
    sst_target = sst_full[target_indices]      # Shape: (target_days, lat, lon)

    # Get time values for target period
    target_times = subset_ds['time'].values[target_indices]

    # Get time values for baseline period
    baseline_times = subset_ds['time'].values[baseline_indices]

print(f"Target period: {len(target_indices)} days")
print(f"Baseline period: {len(baseline_indices)} days")
print(f"Region dimensions: {len(lat_indices)} x {len(lon_indices)}")

# Helper function to get day-of-year for a date
def get_day_of_year(date):
    """Convert datetime to day-of-year (1-366)"""
    # Handle leap year special case for Feb 29
    if date.month == 2 and date.day == 29:
        return 60
    # Create a date for Jan 1 of the same year
    jan1 = datetime(date.year, 1, 1)
    # Calculate the difference in days
    delta = date - jan1
    day_of_year = delta.days + 1
    
    # Adjust for leap year - if it's a leap year and we're past Feb 28, add 1
    if (date.year % 4 == 0 and date.year % 100 != 0) or (date.year % 400 == 0):
        if date.month > 2:
            day_of_year += 1
    return day_of_year

# Get day-of-year for all dates in baseline period
baseline_dates = [datetime.strptime(str(d), '%Y-%m-%dT%H:%M:%S.%f') for d in baseline_times]
baseline_doy = [get_day_of_year(d) for d in baseline_dates]

# Get day-of-year for all dates in target period  
target_dates = [datetime.strptime(str(d), '%Y-%m-%dT%H:%M:%S.%f') for d in target_times]
target_doy = [get_day_of_year(d) for d in target_dates]

print(f"Day-of-year range in baseline: {min(baseline_doy)} to {max(baseline_doy)}")
print(f"Day-of-year range in target: {min(target_doy)} to {max(target_doy)}")

# Step 2: Calculate thresholds and climatology for each day of year
def build_pools_and_compute_stats(sst_data, doy_list):
    """
    Build pools for each day of year based on ±5 day windows and compute stats
    """
    # Initialize arrays for thresholds and climatologies
    threshold = np.full(367, np.nan)  # 1-366 + 1 extra for indexing
    climatology = np.full(367, np.nan)
    
    # For each day of year, collect data from ±5 days around it in baseline period
    for doy in range(1, 367):
        if doy == 60:  # Feb 29 - special case handled later
            continue
            
        # Collect values for this day of year within ±5 days window
        pool_values = []
        
        # Go through all baseline data
        for i, base_doy in enumerate(doy_list):
            # Check if this baseline date should contribute to our doy pool
            if abs(base_doy - doy) <= 5:
                # Add all valid SST values from this day
                valid_values = sst_data[i][~np.isnan(sst_data[i])]
                pool_values.extend(valid_values)
        
        if len(pool_values) > 0:
            pool_array = np.array(pool_values)
            threshold[doy] = np.percentile(pool_array, 90, method='hazen')
            climatology[doy] = np.mean(pool_array)
    
    # Handle special case for day 60 (Feb 29)
    # Take average of days 59 and 61
    if not np.isnan(climatology[59]) and not np.isnan(climatology[61]):
        climatology[60] = (climatology[59] + climatology[61]) / 2
    if not np.isnan(threshold[59]) and not np.isnan(threshold[61]):
        threshold[60] = (threshold[59] + threshold[61]) / 2
    
    # Smooth with 31-day centered moving average (wrapping around year)
    def smooth_with_moving_average(data):
        smoothed = np.zeros_like(data)
        window_size = 31
        half_window = window_size // 2
        
        for i in range(1, 367):  # Days 1-366
            # Sum values in the window
            window_sum = 0
            count = 0
            for j in range(-half_window, half_window + 1):
                # Wrap around the year
                wrapped_day = ((i + j - 1) % 366) + 1
                if not np.isnan(data[wrapped_day]):
                    window_sum += data[wrapped_day]
                    count += 1
            
            if count > 0:
                smoothed[i] = window_sum / count
            else:
                smoothed[i] = data[i]
                
        return smoothed
    
    # Apply smoothing
    threshold_smoothed = smooth_with_moving_average(threshold)
    climatology_smoothed = smooth_with_moving_average(climatology)
    
    return threshold_smoothed, climatology_smoothed

# Compute thresholds and climatology
print("Computing thresholds and climatology...")
thresholds, climatologies = build_pools_and_compute_stats(sst_baseline, baseline_doy)

print("Done computing thresholds and climatology.")

# Step 3: Identify sea cells (grid cells with finite SST on every day of target period)
# A sea cell is one where SST is finite on every day of target period
sea_cells = np.all(np.isfinite(sst_target), axis=0)  # Shape: (lat, lon)

print(f"Number of sea cells: {np.sum(sea_cells)} out of {sea_cells.shape[0]*sea_cells.shape[1]}")

# Step 4: Per-cell MHW detection
# For each sea cell, determine if it experiences MHWs during target period

# Initialize MHW mask
mhw_mask = np.zeros((len(target_indices), len(lat_vals), len(lon_vals)), dtype=np.uint8)

# For each cell, check if it's a sea cell and then compute MHWs
for i_lat in range(len(lat_vals)):
    for i_lon in range(len(lon_vals)):
        if sea_cells[i_lat, i_lon]:  # Only process sea cells
            # Get SST time series for this cell
            sst_series = sst_target[:, i_lat, i_lon]
            
            # Get corresponding day-of-year for each day
            doy_series = [target_doy[j] for j in range(len(target_doy))]
            
            # Determine which days are hot (SST >= threshold for that day of year)
            hot_days = np.zeros(len(sst_series), dtype=bool)
            for j in range(len(sst_series)):
                if not np.isnan(sst_series[j]):
                    # Use the smoothed threshold for that day of year
                    threshold_for_day = thresholds[doy_series[j]]
                    if not np.isnan(threshold_for_day) and sst_series[j] >= threshold_for_day:
                        hot_days[j] = True
            
            # Find runs of at least 5 consecutive hot days
            # And join gaps of 1-2 days
            # First, find all runs of hot days
            runs = []
            start_idx = None
            
            for j in range(len(hot_days)):
                if hot_days[j]:
                    if start_idx is None:
                        start_idx = j
                else:
                    if start_idx is not None:
                        # End of a run
                        runs.append((start_idx, j-1))
                        start_idx = None
            
            # Don't forget the last run if it extends to the end
            if start_idx is not None:
                runs.append((start_idx, len(hot_days)-1))
            
            # Join runs separated by 1-2 non-hot days
            merged_runs = []
            if len(runs) > 0:
                current_run = list(runs[0])
                for i in range(1, len(runs)):
                    prev_end = runs[i-1][1]
                    curr_start = runs[i][0]
                    
                    # Gap between runs
                    gap = curr_start - prev_end - 1
                    
                    if gap <= 2:  # Join if gap is 1 or 2 days
                        current_run[1] = runs[i][1]  # Extend current run
                    else:
                        merged_runs.append(tuple(current_run))
                        current_run = list(runs[i])
                
                merged_runs.append(tuple(current_run))
            
            # Mark MHW days in the mask
            for start, end in merged_runs:
                mhw_mask[start:end+1, i_lat, i_lon] = 1

# Step 5: Regional events
# A day is active if at least one sea cell is inside a per-cell MHW
active_days = np.any(mhw_mask, axis=(1, 2))  # Shape: (target_days,)

# Find maximal runs of consecutive active days
regional_events = []
start_idx = None

for i in range(len(active_days)):
    if active_days[i]:
        if start_idx is None:
            start_idx = i
    else:
        if start_idx is not None:
            # End of an event
            regional_events.append((start_idx, i-1))
            start_idx = None

# Don't forget the last event if it extends to the end
if start_idx is not None:
    regional_events.append((start_idx, len(active_days)-1))

# Convert to proper date strings
event_list = []
for start_idx, end_idx in regional_events:
    start_date_str = str(target_times[start_idx]).split('T')[0]
    end_date_str = str(target_times[end_idx]).split('T')[0]
    event_list.append({"onset": start_date_str, "end": end_date_str})

# Prepare report
report = {
    "region": {
        "lat_min": lat_min,
        "lat_max": lat_max,
        "lon_min": lon_min,
        "lon_max": lon_max
    },
    "baseline_analysed": {
        "start": str(baseline_start.date()),
        "end": str(baseline_end.date())
    },
    "target_analysed": {
        "start": str(start_date.date()),
        "end": str(end_date.date())
    },
    "events": event_list,
    "complete": True,
    "caveats": ""
}

# Write the report
import json
with open('output/report.json', 'w') as f:
    json.dump(report, f, indent=2)

# Write the NetCDF file
try:
    import xarray as xr
    
    # Create the DataArray for the MHW mask
    mhw_da = xr.DataArray(
        mhw_mask,
        dims=['time', 'lat', 'lon'],
        coords={
            'time': target_times,
            'lat': lat_vals,
            'lon': lon_vals
        },
        name='mhw',
        attrs={'units': 'binary', 'long_name': 'Marine Heatwave'}
    )
    
    # Create dataset
    ds_out = xr.Dataset({'mhw': mhw_da})
    
    # Save to netcdf
    ds_out.to_netcdf('output/mhw_mask.nc')
    
    print("Files successfully written.")
except Exception as e:
    print(f"Error writing files: {e}")

print(f"Analysis completed. Found {len(event_list)} regional events.")