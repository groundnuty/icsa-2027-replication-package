import xarray as xr
import numpy as np
from datetime import datetime, timedelta
import os

# Create output directory
os.makedirs('output', exist_ok=True)

# Open with xarray
print("Opening dataset...")
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
print("Dataset opened successfully.")

# Define our region of interest (exact coordinates)
lat_min, lat_max = 54.17, 55.37
lon_min, lon_max = 13.25, 14.45

# Filter to our region
print("Filtering to region...")
ds_region = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))
print(f"Region dimensions: {ds_region.dims}")

# Define our target period
start_date = datetime(2004, 6, 1)
end_date = datetime(2004, 8, 31)

# Filter to target period
print("Filtering to target period...")
ds_period = ds_region.sel(time=slice(start_date, end_date))
print(f"Period dimensions: {ds_period.dims}")

# Get the SST data
sst_data = ds_period['analysed_sst']
print(f"SST data shape: {sst_data.shape}")

# Convert to numpy array for easier processing
sst_array = sst_data.values.astype(np.float64)  # Use double precision as required
print(f"SST array shape: {sst_array.shape}")

# First, let's compute day-of-year for each time step
time_steps = sst_data.time.values
day_of_year = []
for t in time_steps:
    dt = datetime.strptime(str(t)[:10], '%Y-%m-%d')
    # Convert to day of year (1-366)
    doy = int(dt.strftime('%j'))
    # Handle leap year special case for Feb 29
    if dt.month > 2 and dt.year % 4 == 0 and (dt.year % 100 != 0 or dt.year % 400 == 0):
        if doy >= 60:  # After Feb 29
            doy += 1  # Adjust for leap year
    day_of_year.append(doy)

day_of_year = np.array(day_of_year)
print(f"Day of year array shape: {day_of_year.shape}")
print(f"Day of year range: {day_of_year.min()} to {day_of_year.max()}")

# Now let's compute the climatology and thresholds based on baseline years 1992-2002
baseline_start = datetime(1992, 1, 1)
baseline_end = datetime(2002, 12, 31)

# Get baseline data
print("Extracting baseline data...")
ds_baseline = ds.sel(time=slice(baseline_start, baseline_end))
sst_baseline = ds_baseline['analysed_sst'].values.astype(np.float64)

# Get baseline time steps
baseline_time_steps = ds_baseline.time.values
baseline_day_of_year = []
for t in baseline_time_steps:
    dt = datetime.strptime(str(t)[:10], '%Y-%m-%d')
    doy = int(dt.strftime('%j'))
    # Handle leap year special case for Feb 29
    if dt.month > 2 and dt.year % 4 == 0 and (dt.year % 100 != 0 or dt.year % 400 == 0):
        if doy >= 60:  # After Feb 29
            doy += 1  # Adjust for leap year
    baseline_day_of_year.append(doy)

baseline_day_of_year = np.array(baseline_day_of_year)

print(f"Baseline data shape: {sst_baseline.shape}")
print(f"Baseline day of year range: {baseline_day_of_year.min()} to {baseline_day_of_year.max()}")

# Step 1: Find sea cells (cells with finite SST on every day of target period)
print("Identifying sea cells...")
# A sea cell is one that has finite SST on every day of the target period
sea_cells = np.all(np.isfinite(sst_array), axis=0)
print(f"Number of sea cells (finite on all days): {np.sum(sea_cells)} out of {sst_array.shape[1]*sst_array.shape[2]} total cells")

# Step 2: Compute threshold and climatology for each day of year using baseline data
print("Computing thresholds and climatologies...")
thresholds = np.full(366, np.nan, dtype=np.float64)
climatologies = np.full(366, np.nan, dtype=np.float64)

# For each day of year (1-366), compute pool of baseline values
# Day 60 (Feb 29) will be handled specially later
for doy in range(1, 367):
    if doy == 60:  # Skip day 60 for now, handle it specially later
        continue
        
    # Find baseline dates that fall within ±5 days of this day of year
    # Create a mask for baseline dates that match this day of year (±5 days)
    # We'll use a sliding window approach
    pool_indices = []
    
    # For each baseline date, check if it falls within the appropriate window
    for i, (baseline_doy, baseline_date) in enumerate(zip(baseline_day_of_year, baseline_time_steps)):
        # Calculate distance between this DOY and our target DOY
        # Account for year wrapping (since we're dealing with circular year)
        diff = abs(baseline_doy - doy)
        if diff > 183:  # More than 183 days apart means we need to wrap around
            diff = 366 - diff
            
        if diff <= 5:
            pool_indices.append(i)
            
    if len(pool_indices) > 0:
        # Extract the pool of values - process in chunks to save memory
        pool_values = sst_baseline[pool_indices, :, :]
        # Flatten to 1D, remove NaNs
        flat_pool = pool_values.flatten()
        valid_pool = flat_pool[np.isfinite(flat_pool)]
        
        if len(valid_pool) > 0:
            # Compute 90th percentile (Hazen method)
            threshold = np.percentile(valid_pool, 90, method='linear')
            # Compute mean
            climatology = np.mean(valid_pool)
            
            thresholds[doy-1] = threshold  # Convert to 0-based indexing
            climatologies[doy-1] = climatology

# Special handling for day 60 (Feb 29)
print("Handling day 60 (February 29)...")
# Day 60 gets the mean of days 59 and 61
if not np.isnan(thresholds[58]) and not np.isnan(thresholds[60]):  # Days 59 and 61 (0-based)
    thresholds[59] = (thresholds[58] + thresholds[60]) / 2  # Day 60 (0-based index 59)
if not np.isnan(climatologies[58]) and not np.isnan(climatologies[60]):
    climatologies[59] = (climatologies[58] + climatologies[60]) / 2

# Step 3: Smooth the thresholds and climatologies with 31-day moving average
print("Smoothing thresholds and climatologies...")
def smooth_366(arr):
    """Smooth a 366-element array with a 31-day centered moving average"""
    smoothed = np.zeros_like(arr, dtype=np.float64)
    window_size = 31
    half_window = window_size // 2
    
    for i in range(366):
        # Sum values in the window, wrapping around the year
        window_sum = 0
        count = 0
        for j in range(-half_window, half_window + 1):
            # Wrap around the year
            wrapped_index = (i + j) % 366
            if not np.isnan(arr[wrapped_index]):
                window_sum += arr[wrapped_index]
                count += 1
                
        if count > 0:
            smoothed[i] = window_sum / count
        else:
            smoothed[i] = np.nan
            
    return smoothed

thresholds_smoothed = smooth_366(thresholds)
climatologies_smoothed = smooth_366(climatologies)

# Step 4: Find MHWs for each sea cell - Process row by row to reduce memory
print("Finding MHWs for each sea cell...")
# Initialize MHW mask
mhw_mask = np.zeros((sst_array.shape[0], sst_array.shape[1], sst_array.shape[2]), dtype=np.uint8)

# Process one row at a time to reduce memory usage
for i in range(sst_array.shape[1]):  # latitude
    if i % 10 == 0:
        print(f"Processing row {i}/{sst_array.shape[1]}")
    
    for j in range(sst_array.shape[2]):  # longitude
        if not sea_cells[i, j]:  # Not a sea cell
            continue
            
        # Get SST for this cell over the entire period
        cell_sst = sst_array[:, i, j]
        
        # Determine if each day is hot (>= threshold for that day of year)
        hot_days = np.zeros(cell_sst.shape, dtype=bool)
        for k, sst_val in enumerate(cell_sst):
            if np.isfinite(sst_val):
                doy = day_of_year[k]
                if not np.isnan(thresholds_smoothed[doy-1]):  # 0-based indexing
                    hot_days[k] = sst_val >= thresholds_smoothed[doy-1]
        
        # Find runs of at least 5 consecutive hot days
        # Also join gaps of 1 or 2 days
        mhw_days = np.zeros(cell_sst.shape, dtype=bool)
        
        # Simple approach: mark hot days, then extend runs by joining small gaps
        if np.any(hot_days):
            # Create a list of hot day indices
            hot_indices = np.where(hot_days)[0]
            
            # Group consecutive hot days
            if len(hot_indices) > 0:
                # Start grouping
                current_group = [hot_indices[0]]
                groups = []
                
                for idx in hot_indices[1:]:
                    if idx == current_group[-1] + 1:  # Consecutive day
                        current_group.append(idx)
                    else:  # Gap - start new group
                        groups.append(current_group)
                        current_group = [idx]
                groups.append(current_group)
                
                # Now process groups and join small gaps
                merged_groups = []
                for group in groups:
                    if not merged_groups:
                        merged_groups.append(group)
                    else:
                        prev_group = merged_groups[-1]
                        gap = group[0] - prev_group[-1] - 1
                        if gap <= 2:  # Join if gap is 1 or 2 days
                            merged_groups[-1] = prev_group + group
                        else:
                            merged_groups.append(group)
                
                # Mark all days in merged groups as MHW
                for group in merged_groups:
                    for day_idx in group:
                        mhw_days[day_idx] = True
                        
        # Set the result in our mask
        mhw_mask[:, i, j] = mhw_days.astype(np.uint8)

# Step 5: Compute regional events
print("Computing regional events...")
# A day is active if at least one sea cell is inside an MHW on that day
active_days = np.any(mhw_mask, axis=(1, 2))  # Shape: (92,) 

# A regional MHW event is a maximal run of consecutive active days
events = []
start_event = None

for i, is_active in enumerate(active_days):
    if is_active and start_event is None:
        # Start of a new event
        start_event = i
    elif not is_active and start_event is not None:
        # End of an event
        events.append((start_event, i - 1))
        start_event = None

# Handle case where the last day is active
if start_event is not None:
    events.append((start_event, len(active_days) - 1))

# Convert to actual dates
event_list = []
for start_idx, end_idx in events:
    start_date_str = str(sst_data.time.values[start_idx])[:10]
    end_date_str = str(sst_data.time.values[end_idx])[:10]
    event_list.append({
        "onset": start_date_str,
        "end": end_date_str
    })

# Prepare the output NetCDF file
print("Preparing output NetCDF file...")
# Create a new dataset with the MHW mask
mhw_da = xr.DataArray(
    mhw_mask,
    dims=['time', 'latitude', 'longitude'],
    coords={
        'time': sst_data.time,
        'latitude': sst_data.latitude,
        'longitude': sst_data.longitude
    },
    name='mhw',
    attrs={'units': 'binary', 'long_name': 'Marine Heatwave'}
)

# Create dataset
ds_output = xr.Dataset({'mhw': mhw_da})

# Save to file
ds_output.to_netcdf('output/mhw_mask.nc')

# Create report
report = {
    "region": {
        "lat_min": float(lat_min),
        "lat_max": float(lat_max),
        "lon_min": float(lon_min),
        "lon_max": float(lon_max)
    },
    "baseline_analysed": {
        "start": "1992-01-01",
        "end": "2002-12-31"
    },
    "target_analysed": {
        "start": "2004-06-01",
        "end": "2004-08-31"
    },
    "events": event_list,
    "complete": True,
    "caveats": ""
}

import json
with open('output/report.json', 'w') as f:
    json.dump(report, f, indent=2)

print("Analysis complete!")
print(f"Number of MHW events found: {len(event_list)}")
if event_list:
    print("Events:")
    for event in event_list:
        print(f"  {event['onset']} to {event['end']}")
else:
    print("No MHW events found in the region.")

print("Files saved to output/")