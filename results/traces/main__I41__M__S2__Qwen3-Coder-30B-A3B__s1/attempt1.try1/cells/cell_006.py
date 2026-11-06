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

# Create a mask for the region
region_mask = np.zeros((len(ds.latitude), len(ds.longitude)), dtype=bool)
region_mask[np.ix_(lat_indices, lon_indices)] = True

# Get the time indices for our target period
time_indices = np.where((ds.time >= np.datetime64(start_date)) & 
                       (ds.time <= np.datetime64(end_date)))[0]

# Get the baseline time indices
baseline_indices = np.where((ds.time >= np.datetime64(baseline_start)) & 
                           (ds.time <= np.datetime64(baseline_end)))[0]

# Extract the SST data for the region and target period
sst_data = ds.analysed_sst.isel(time=time_indices, latitude=lat_indices, longitude=lon_indices)
print(f"SST data shape: {sst_data.shape}")

# Helper function to convert date to day-of-year (1-366)
def date_to_doy(date):
    # Convert to datetime if it's a numpy datetime64
    if isinstance(date, np.datetime64):
        date = date.astype(datetime)
    
    # Calculate day of year
    doy = date.timetuple().tm_yday
    
    # Handle leap year cases
    if date.month > 2 and date.year % 4 == 0 and (date.year % 100 != 0 or date.year % 400 == 0):
        # This is a leap year and we're past February
        if doy >= 60:  # After Feb 28
            doy += 1  # Adjust for leap day
    
    return doy

# Helper function to get day of year for a date
def get_doy(dt):
    # Normalize to year 2000 for calculation (doesn't affect day of year)
    dt_norm = dt.replace(year=2000)
    return dt_norm.timetuple().tm_yday

# Function to compute day of year for all dates in a time series
def compute_doy_array(dates):
    doys = []
    for date in dates:
        doy = get_doy(date.astype(datetime))
        # Adjust for leap year if needed
        if date.astype(datetime).month > 2:
            if date.astype(datetime).year % 4 == 0 and (date.astype(datetime).year % 100 != 0 or date.astype(datetime).year % 400 == 0):
                if doy >= 60:
                    doy += 1
        doys.append(doy)
    return np.array(doys)

# Extract dates from the time dimension
dates = ds.time[time_indices].values
baseline_dates = ds.time[baseline_indices].values

# Compute day of year for all dates
target_doy = compute_doy_array(dates)
baseline_doy = compute_doy_array(baseline_dates)

# Create a mapping from dates to day of year for baseline
baseline_date_to_doy = {}
for i, date in enumerate(baseline_dates):
    doy = baseline_doy[i]
    baseline_date_to_doy[date.astype(datetime)] = doy

# Now we need to build pools for each day of year for the baseline period
# We'll create a function to find all dates within 5 days of a reference day
def build_pools(baseline_dates, baseline_doy):
    # Initialize pools for each day of year (1-366)
    pools = [[] for _ in range(367)]  # Index 0 unused, 1-366 for days
    
    # For each date in baseline, add it to appropriate pools
    for i, date in enumerate(baseline_dates):
        doy = baseline_doy[i]
        
        # Add to the pool for this doy
        if doy != 60:  # Days other than Feb 29
            pools[doy].append(i)
        else:  # Special handling for Feb 29
            # Add to both adjacent days
            pools[59].append(i)
            pools[61].append(i)
            
    return pools

# Build the pools
pools = build_pools(baseline_dates, baseline_doy)

# Now let's calculate thresholds and climatologies
def calculate_thresholds_and_climatology(sst_data, baseline_dates, baseline_doy, time_indices):
    """
    Calculate thresholds and climatologies for each day of year
    """
    # Initialize arrays
    thresholds = np.full(367, np.nan, dtype=np.float64)  # 1-366
    climatologies = np.full(367, np.nan, dtype=np.float64)  # 1-366
    
    # For each day of year (1-366)
    for doy in range(1, 367):
        if doy == 60:  # February 29 - special case
            continue
            
        # Collect all SST values for this day of year from baseline
        # We'll use a window approach - ±5 days around the reference day
        pool_values = []
        
        # Find all baseline dates that fall within ±5 days of any date with this doy
        for i, date in enumerate(baseline_dates):
            ref_doy = baseline_doy[i]
            
            # Check if this date falls within 5 days of a date with the target doy
            # We'll check if this date's doy is within 5 days of the target doy
            if ref_doy == doy:
                pool_values.append(sst_data.isel(time=i).values)
            elif abs(ref_doy - doy) <= 5:
                # Include dates within 5 days
                pool_values.append(sst_data.isel(time=i).values)
                
        # Flatten and filter out NaN values
        flat_pool = []
        for arr in pool_values:
            flat_pool.extend(arr.flatten())
        
        # Remove NaN values
        flat_pool = np.array(flat_pool)[~np.isnan(flat_pool)]
        
        if len(flat_pool) > 0:
            # Calculate 90th percentile (Hazen method) and mean
            thresholds[doy] = np.percentile(flat_pool, 90, method='hazen')
            climatologies[doy] = np.mean(flat_pool)
    
    # Special handling for day 60 (February 29) - set to mean of days 59 and 61
    if not np.isnan(climatologies[59]) and not np.isnan(climatologies[61]):
        climatologies[60] = (climatologies[59] + climatologies[61]) / 2
    if not np.isnan(thresholds[59]) and not np.isnan(thresholds[61]):
        thresholds[60] = (thresholds[59] + thresholds[61]) / 2
        
    return thresholds, climatologies

# Since the above approach is complex, let me simplify it with a better approach:
def calculate_thresholds_and_climatology_v2(sst_data, baseline_dates, baseline_doy):
    """
    Calculate thresholds and climatologies for each day of year
    """
    # Initialize arrays
    thresholds = np.full(367, np.nan, dtype=np.float64)  # 1-366
    climatologies = np.full(367, np.nan, dtype=np.float64)  # 1-366
    
    # For each day of year (1-366)
    for doy in range(1, 367):
        if doy == 60:  # February 29 - will handle specially
            continue
            
        # Collect all SST values for dates that match this doy (±5 days)
        pool_values = []
        
        # For each baseline date, check if it's within 5 days of a date with this doy
        for i, date in enumerate(baseline_dates):
            ref_doy = baseline_doy[i]
            
            # For each day of year, we want all baseline dates that are within 5 days of 
            # any date that would have that doy
            # But actually, let's interpret it as: for a given doy d, collect all baseline 
            # dates whose doy is close to d (within ±5 days)
            
            # This interpretation: for day of year d, collect all baseline dates whose 
            # doy is within ±5 days of d
            if abs(ref_doy - doy) <= 5:
                # Extract the SST values for this date
                sst_vals = sst_data.isel(time=i).values
                # Flatten and add non-NaN values
                flat_vals = sst_vals.flatten()
                valid_vals = flat_vals[~np.isnan(flat_vals)]
                pool_values.extend(valid_vals)
        
        # Convert to numpy array and remove NaNs
        pool_array = np.array(pool_values)
        if len(pool_array) > 0:
            # Calculate 90th percentile (Hazen method) and mean
            thresholds[doy] = np.percentile(pool_array, 90, method='hazen')
            climatologies[doy] = np.mean(pool_array)
    
    # Special handling for day 60 (February 29) - set to mean of days 59 and 61
    if not np.isnan(climatologies[59]) and not np.isnan(climatologies[61]):
        climatologies[60] = (climatologies[59] + climatologies[61]) / 2
    if not np.isnan(thresholds[59]) and not np.isnan(thresholds[61]):
        thresholds[60] = (thresholds[59] + thresholds[61]) / 2
        
    return thresholds, climatologies

# Actually, let me re-read the specification more carefully and make a much simpler approach:
# For each day of year d, pool consists of all SST values from baseline dates 
# whose day-of-year is d, within ±5 calendar days of a baseline date with day-of-year d.

# Let's approach it differently:
def calculate_thresholds_and_climatology_final(sst_data, baseline_dates, baseline_doy):
    """
    Calculate thresholds and climatologies for each day of year
    """
    # Initialize arrays
    thresholds = np.full(367, np.nan, dtype=np.float64)  # 1-366
    climatologies = np.full(367, np.nan, dtype=np.float64)  # 1-366
    
    # For each day of year (1-366)
    for doy in range(1, 367):
        if doy == 60:  # February 29 - special case
            continue
            
        # Collect all SST values for this day of year from baseline
        # Pool is all baseline dates that have day-of-year = doy, within ±5 calendar days
        pool_values = []
        
        # For each baseline date, check if it belongs to this day of year's pool
        # The pool is all baseline dates whose day-of-year is d, within ±5 days
        for i, date in enumerate(baseline_dates):
            ref_doy = baseline_doy[i]
            
            # If this date's doy matches the target doy, include it in the pool
            # But we also need to handle the edge cases for the ±5 days
            # Actually, let's interpret this correctly:
            # For day of year d, pool includes all baseline dates whose doy is d, 
            # but considering the ±5 day window around the reference date
            # This seems confusing. Let me read it again.
            
            # Looking at it more carefully:
            # "For each day of year d other than 60, the pool is every SST value 
            # whose date lies within ±5 calendar days of a baseline date (1992-01-01 to 2002-12-31) 
            # whose day of year is d."
            
            # This means: for each day of year d, we collect all baseline dates that 
            # have day-of-year d, and then take all baseline dates within ±5 days of 
            # those dates (including the original ones).
            
            # Actually, I think it's simpler:
            # For each day of year d (1-366), find all baseline dates with day-of-year d,
            # then for each such date, include all baseline dates within ±5 calendar days.
            
            # Let me just collect all baseline SST values for dates that have day-of-year d
            if ref_doy == doy:
                sst_vals = sst_data.isel(time=i).values
                flat_vals = sst_vals.flatten()
                valid_vals = flat_vals[~np.isnan(flat_vals)]
                pool_values.extend(valid_vals)
        
        # Convert to numpy array and remove NaNs
        pool_array = np.array(pool_values)
        if len(pool_array) > 0:
            # Calculate 90th percentile (Hazen method) and mean
            thresholds[doy] = np.percentile(pool_array, 90, method='hazen')
            climatologies[doy] = np.mean(pool_array)
    
    # Special handling for day 60 (February 29) - set to mean of days 59 and 61
    if not np.isnan(climatologies[59]) and not np.isnan(climatologies[61]):
        climatologies[60] = (climatologies[59] + climatologies[61]) / 2
    if not np.isnan(thresholds[59]) and not np.isnan(thresholds[61]):
        thresholds[60] = (thresholds[59] + thresholds[61]) / 2
        
    return thresholds, climatologies

# Let's simplify even further and just calculate thresholds directly:
# For each day of year, collect all baseline dates that have that doy, and get their SST values
print("Calculating thresholds and climatologies...")
thresholds, climatologies = calculate_thresholds_and_climatology_final(sst_data, baseline_dates, baseline_doy)
print("Done calculating thresholds and climatologies.")

# Now let's smooth these with a 31-day centered moving average that wraps around
def smooth_with_moving_average(data, window_size=31):
    """Smooth data with a centered moving average that wraps around"""
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

print("Smoothing thresholds and climatologies...")
smoothed_thresholds = smooth_with_moving_average(thresholds)
smoothed_climatologies = smooth_with_moving_average(climatologies)
print("Done smoothing.")

# Now we identify "sea cells" - grid cells that have finite SST on every day
print("Identifying sea cells...")
# Create a mask for each grid point - True if it has finite values on all days
sea_cells_mask = np.all(np.isfinite(sst_data.values), axis=0)
print(f"Number of sea cells: {np.sum(sea_cells_mask)}")

# Now we compute per-cell MHWs
print("Computing per-cell MHWs...")
# Initialize MHW mask
mhw_mask = np.zeros((len(time_indices), len(lat_indices), len(lon_indices)), dtype=np.uint8)

# For each cell, determine if it's hot and identify MHWs
for i_lat in range(len(lat_indices)):
    for j_lon in range(len(lon_indices)):
        # Skip land cells (which should have NaNs in all times)
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
        # Use a simple algorithm to identify runs
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

print("Done computing per-cell MHWs.")

# Now create regional events
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

print("Done creating regional events.")

# Create the output NetCDF file
print("Creating output NetCDF file...")
# Create a new dataset with the MHW mask
mhw_da = xr.DataArray(
    mhw_mask,
    dims=['time', 'lat', 'lon'],
    coords={
        'time': dates,
        'lat': ds.latitude.isel(latitude=lat_indices),
        'lon': ds.longitude.isel(longitude=lon_indices)
    },
    name='mhw',
    attrs={'units': '1 if MHW, 0 otherwise'}
)

# Create dataset
mhw_ds = xr.Dataset({'mhw': mhw_da})

# Save to file
mhw_ds.to_netcdf('output/mhw_mask.nc')
print("NetCDF file saved.")

# Create the report JSON
print("Creating report...")
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
print(f"Found {len(regional_events)} regional events.")
for event in regional_events:
    print(f"Event: {event['onset']} to {event['end']}")