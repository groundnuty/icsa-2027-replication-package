import os
import xarray as xr
import numpy as np
from datetime import datetime, timedelta

os.makedirs('output', exist_ok=True)

# Define region and time period
lat_min, lat_max = 61.57, 62.77
lon_min, lon_max = 20.17, 21.37
start_date = datetime(2021, 6, 1)
end_date = datetime(2021, 8, 31)
baseline_start = datetime(1992, 1, 1)
baseline_end = datetime(2002, 12, 31)

# Open the dataset
ds = xr.open_dataset('/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', engine='h5netcdf')

# Select the region
lat_indices = np.where((ds.latitude >= lat_min) & (ds.latitude <= lat_max))[0]
lon_indices = np.where((ds.longitude >= lon_min) & (ds.longitude <= lon_max))[0]

# Get the time indices for our target period
time_indices = np.where((ds.time >= np.datetime64(start_date)) & 
                       (ds.time <= np.datetime64(end_date)))[0]

# Get the baseline time indices
baseline_indices = np.where((ds.time >= np.datetime64(baseline_start)) & 
                           (ds.time <= np.datetime64(baseline_end)))[0]

# Extract the SST data for the region and target period
sst_data = ds.analysed_sst.isel(time=time_indices, latitude=lat_indices, longitude=lon_indices)

# Helper function to convert datetime64 to day-of-year
def datetime_to_doy(dt64):
    """Convert numpy datetime64 to day of year (1-366)"""
    # Convert to datetime object
    if isinstance(dt64, np.datetime64):
        dt_obj = dt64.astype(datetime)
    else:
        dt_obj = dt64
    
    # Calculate day of year
    doy = dt_obj.timetuple().tm_yday
    
    # For leap years, adjust dates after Feb 28
    if dt_obj.month > 2:
        # Check if it's a leap year
        if dt_obj.year % 4 == 0 and (dt_obj.year % 100 != 0 or dt_obj.year % 400 == 0):
            doy += 1
    
    return doy

# Extract dates
dates = ds.time[time_indices].values
baseline_dates = ds.time[baseline_indices].values

# Compute day of year for all dates
target_doy = np.array([datetime_to_doy(dt) for dt in dates])
baseline_doy = np.array([datetime_to_doy(dt) for dt in baseline_dates])

print("Computing thresholds and climatologies...")
# Calculate thresholds and climatologies for each day of year
thresholds = np.full(367, np.nan, dtype=np.float64)  # 1-366
climatologies = np.full(367, np.nan, dtype=np.float64)  # 1-366

# For each day of year, find all baseline dates with that day of year
# and collect their SST values
for doy in range(1, 367):
    if doy == 60:  # February 29 - special case handled later
        continue
        
    # Find all baseline indices with this day of year
    matching_indices = np.where(baseline_doy == doy)[0]
    
    if len(matching_indices) > 0:
        # Collect all SST values for these dates
        pool_values = []
        for idx in matching_indices:
            sst_vals = sst_data.isel(time=idx).values
            flat_vals = sst_vals.flatten()
            valid_vals = flat_vals[~np.isnan(flat_vals)]
            pool_values.extend(valid_vals)
        
        if len(pool_values) > 0:
            pool_array = np.array(pool_values)
            thresholds[doy] = np.percentile(pool_array, 90, method='hazen')
            climatologies[doy] = np.mean(pool_array)

# Special handling for day 60 (February 29) - set to mean of days 59 and 61
if not np.isnan(climatologies[59]) and not np.isnan(climatologies[61]):
    climatologies[60] = (climatologies[59] + climatologies[61]) / 2
if not np.isnan(thresholds[59]) and not np.isnan(thresholds[61]):
    thresholds[60] = (thresholds[59] + thresholds[61]) / 2

print("Smoothing thresholds and climatologies...")
# Smooth with 31-day moving average that wraps around
def smooth_with_moving_average(data, window_size=31):
    smoothed = np.copy(data)
    half_window = window_size // 2
    
    for i in range(1, 367):  # 1 to 366
        # Calculate the window boundaries (wrapping around)
        start_idx = (i - half_window) % 366
        end_idx = (i + half_window) % 366
        
        if start_idx <= end_idx:
            # No wraparound
            window_data = data[start_idx:end_idx+1]
        else:
            # Wraparound case
            window_data = np.concatenate([data[start_idx:], data[:end_idx+1]])
        
        # Calculate mean of the window
        if len(window_data) > 0:
            smoothed[i] = np.mean(window_data)
    
    return smoothed

smoothed_thresholds = smooth_with_moving_average(thresholds)
smoothed_climatologies = smooth_with_moving_average(climatologies)

print("Identifying sea cells...")
# Create a mask for each grid point - True if it has finite values on all days
sea_cells_mask = np.all(np.isfinite(sst_data.values), axis=0)
print(f"Number of sea cells: {np.sum(sea_cells_mask)}")

print("Computing per-cell MHWs...")
# Initialize MHW mask
mhw_mask = np.zeros((len(time_indices), len(lat_indices), len(lon_indices)), dtype=np.uint8)

# For each cell, determine if it's hot and identify MHWs
for i_lat in range(len(lat_indices)):
    for j_lon in range(len(lon_indices)):
        # Skip land cells
        if not sea_cells_mask[i_lat, j_lon]:
            continue
            
        # Get SST time series for this cell
        cell_sst = sst_data.isel(latitude=i_lat, longitude=j_lon).values
        
        # Determine hot days for this cell
        hot_days = np.zeros(len(time_indices), dtype=bool)
        for t in range(len(time_indices)):
            doy = target_doy[t]
            if not np.isnan(cell_sst[t]) and not np.isnan(smoothed_thresholds[doy]):
                hot_days[t] = cell_sst[t] >= smoothed_thresholds[doy]
        
        # Find runs of hot days (at least 5 consecutive)
        mhw_runs = []
        in_run = False
        run_start = 0
        
        for t in range(len(time_indices)):
            if hot_days[t]:
                if not in_run:
                    in_run = True
                    run_start = t
            else:
                if in_run:
                    # End of a run
                    run_length = t - run_start
                    if run_length >= 5:
                        mhw_runs.append((run_start, t-1))
                    in_run = False
                    
        # Handle case where run extends to the end
        if in_run:
            run_length = len(time_indices) - run_start
            if run_length >= 5:
                mhw_runs.append((run_start, len(time_indices)-1))
        
        # Join gaps of 1 or 2 days
        if len(mhw_runs) > 1:
            merged_runs = [mhw_runs[0]]
            for i in range(1, len(mhw_runs)):
                prev_end = merged_runs[-1][1]
                curr_start = mhw_runs[i][0]
                gap = curr_start - prev_end
                
                # If gap is 1 or 2 days, merge
                if 1 <= gap <= 2:
                    merged_runs[-1] = (merged_runs[-1][0], mhw_runs[i][1])
                else:
                    merged_runs.append(mhw_runs[i])
                    
            mhw_runs = merged_runs
        
        # Mark MHW days in the mask
        for start, end in mhw_runs:
            mhw_mask[start:end+1, i_lat, j_lon] = 1

print("Creating regional events...")
# A day is active if at least one sea cell is inside a per-cell MHW
active_days = np.any(mhw_mask, axis=(1, 2))  # Shape: (time_steps,)

# Identify regional MHW events (maximal runs of consecutive active days)
regional_events = []
in_event = False
event_start = 0

for t in range(len(active_days)):
    if active_days[t] and not in_event:
        # Start of new event
        in_event = True
        event_start = t
    elif not active_days[t] and in_event:
        # End of event
        in_event = False
        # Record the event (inclusive start and end)
        regional_events.append({
            'onset': str(dates[event_start].astype(datetime))[:10],
            'end': str(dates[t-1].astype(datetime))[:10]
        })

if in_event:
    # Handle case where the last day is part of an event
    regional_events.append({
        'onset': str(dates[event_start].astype(datetime))[:10],
        'end': str(dates[len(active_days)-1].astype(datetime))[:10]
    })

print(f"Found {len(regional_events)} regional events.")

# Create the output NetCDF file
print("Creating output NetCDF file...")
# Create the DataArray with proper coordinates
mhw_da = xr.DataArray(
    mhw_mask,
    dims=['time', 'latitude', 'longitude'],
    coords={
        'time': dates,
        'latitude': ds.latitude.isel(latitude=lat_indices),
        'longitude': ds.longitude.isel(longitude=lon_indices)
    },
    name='mhw',
    attrs={'units': '1 if MHW, 0 otherwise'}
)

mhw_ds = xr.Dataset({'mhw': mhw_da})
mhw_ds.to_netcdf('output/mhw_mask.nc')
print("NetCDF file saved.")

# Create the report JSON
report = {
    "region": {
        "lat_min": lat_min,
        "lat_max": lat_max,
        "lon_min": lon_min,
        "lon_max": lon_max
    },
    "baseline_analysed": {
        "start": str(baseline_start)[:10],
        "end": str(baseline_end)[:10]
    },
    "target_analysed": {
        "start": str(start_date)[:10],
        "end": str(end_date)[:10]
    },
    "events": regional_events,
    "complete": True,
    "caveats": ""
}

import json
with open('output/report.json', 'w') as f:
    json.dump(report, f, indent=2)

print("Report saved.")
for event in regional_events:
    print(f"Event: {event['onset']} to {event['end']}")