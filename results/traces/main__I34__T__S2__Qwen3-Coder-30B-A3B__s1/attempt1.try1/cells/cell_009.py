import fsspec
import xarray as xr
import numpy as np
from datetime import datetime, timedelta
import os

# Set up the filesystem
fs = fsspec.filesystem('onedata')

# Open the dataset
file_path = '/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
with fs.open(file_path, 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')

# Define the region of interest
lat_min, lat_max = 59.93, 61.13
lon_min, lon_max = 18.69, 19.89

# Get indices for the region
lat_indices = np.where((ds.latitude >= lat_min) & (ds.latitude <= lat_max))[0]
lon_indices = np.where((ds.longitude >= lon_min) & (ds.longitude <= lon_max))[0]

# Define the target period
start_date = np.datetime64('2007-06-01')
end_date = np.datetime64('2007-08-31')

# Get indices for the target period
time_indices = np.where((ds.time >= start_date) & (ds.time <= end_date))[0]

# Extract the subset
ds_subset = ds.isel(latitude=lat_indices, longitude=lon_indices, time=time_indices)

print("Extracted subset dimensions:", ds_subset.dims)
print("Subset time range:", ds_subset.time.min().values, "to", ds_subset.time.max().values)

# Now we need to work with the full dataset for baseline period (1992-2002)
# Let's extract the baseline period data
baseline_start = np.datetime64('1992-01-01')
baseline_end = np.datetime64('2002-12-31')

# Get indices for the baseline period
baseline_time_indices = np.where((ds.time >= baseline_start) & (ds.time <= baseline_end))[0]

# Extract baseline data for the region
ds_baseline = ds.isel(latitude=lat_indices, longitude=lon_indices, time=baseline_time_indices)

print("Baseline data shape:", ds_baseline.analysed_sst.shape)
print("Baseline time range:", ds_baseline.time.min().values, "to", ds_baseline.time.max().values)

# Let's now create a more robust approach to compute thresholds and climatology
def get_doy_from_date(date):
    """Convert date to day of year (1-366)"""
    dt = date.astype(datetime)
    doy = dt.timetuple().tm_yday
    # Adjust for leap years - if it's a leap year and day > 60, subtract 1
    if is_leap_year(dt.year) and doy > 60:
        doy -= 1
    return doy

def is_leap_year(year):
    """Check if a year is a leap year"""
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)

def compute_climatology_and_thresholds(sst_data, time_dim, doy_map):
    """
    Compute climatology and thresholds for each day of year using the baseline data
    """
    # Initialize storage for all pools
    pools = [[] for _ in range(367)]  # Index 0 unused, days 1-366
    
    # Process each time step in baseline data
    for t in range(len(sst_data[time_dim])):
        date = sst_data[time_dim][t].values
        doy = doy_map[date]
        
        # Skip day 60 (February 29) as specified
        if doy == 60:
            continue
            
        # Get SST data for this time step and add to pool
        sst_slice = sst_data.analysed_sst[t, :, :]
        # Flatten and filter out NaN values
        sst_values = sst_slice.values.flatten()
        valid_values = sst_values[~np.isnan(sst_values)]
        
        # Add to the appropriate pool
        pools[doy].extend(valid_values)
    
    # Handle special case for day 60 (combine from neighboring days)
    if len(pools[59]) > 0 and len(pools[61]) > 0:
        pools[60] = pools[59] + pools[61]
    elif len(pools[59]) > 0:
        pools[60] = pools[59]
    elif len(pools[61]) > 0:
        pools[60] = pools[61]
    
    # Compute thresholds and climatologies
    threshold = np.full(367, np.nan)
    climatology = np.full(367, np.nan)
    
    for doy in range(1, 367):
        if len(pools[doy]) > 0:
            # Using numpy's quantile with linear interpolation (equivalent to MATLAB's quantile default)
            threshold[doy] = np.quantile(pools[doy], 0.9, method='linear')
            climatology[doy] = np.mean(pools[doy])
    
    # Apply smoothing (31-day centered moving average that wraps around)
    threshold_smoothed = smooth_366_array(threshold)
    climatology_smoothed = smooth_366_array(climatology)
    
    return threshold_smoothed, climatology_smoothed

def smooth_366_array(arr):
    """Apply 31-day centered moving average that wraps around the year"""
    smoothed = np.zeros_like(arr)
    window_size = 31
    half_window = window_size // 2
    
    for i in range(1, 367):  # Days 1-366 (1-indexed)
        # Sum values in the window
        window_sum = 0
        count = 0
        
        for j in range(-half_window, half_window + 1):
            # Wrap around the year (1-366)
            wrapped_idx = ((i + j - 1) % 366) + 1  # Convert to 1-based indexing
            if not np.isnan(arr[wrapped_idx]):
                window_sum += arr[wrapped_idx]
                count += 1
                
        if count > 0:
            smoothed[i] = window_sum / count
        else:
            smoothed[i] = np.nan
            
    return smoothed

# Create mapping from date to day of year for baseline period
doy_map = {}
for t in range(len(ds_baseline.time)):
    date = ds_baseline.time[t].values
    dt = date.astype(datetime)
    doy = dt.timetuple().tm_yday
    # Adjust for leap years
    if is_leap_year(dt.year) and doy > 60:
        doy -= 1
    doy_map[date] = doy

print("Created DOY mapping for", len(doy_map), "dates")

# Compute climatology and thresholds
thresholds, climatologies = compute_climatology_and_thresholds(ds_baseline, 'time', doy_map)

print("Computed thresholds and climatologies")
print("Thresholds shape:", thresholds.shape)
print("Climatologies shape:", climatologies.shape)
print("Sample thresholds:", thresholds[1:10])
print("Sample climatologies:", climatologies[1:10])

# Now perform MHW detection on target period data
def detect_mhw_events(sst_data, thresholds, climatologies, min_duration=5, gap_threshold=2):
    """
    Detect MHW events in the target period data
    """
    # Create mask for MHWs
    mhw_mask = np.zeros((len(sst_data.time), len(sst_data.latitude), len(sst_data.longitude)), dtype=np.uint8)
    
    # For each location (lat, lon), detect MHWs
    for i_lat in range(len(sst_data.latitude)):
        for i_lon in range(len(sst_data.longitude)):
            # Get SST timeseries for this location
            sst_ts = sst_data.analysed_sst[:, i_lat, i_lon]
            
            # Check if all values are valid (finite) for the entire period
            if np.all(np.isfinite(sst_ts.values)):
                # Determine which days are hot (SST >= threshold for that day of year)
                hot_days = np.zeros(len(sst_ts), dtype=bool)
                
                # Get the day of year for each date
                for i_time in range(len(sst_ts)):
                    date = sst_data.time[i_time].values
                    dt = date.astype(datetime)
                    doy = dt.timetuple().tm_yday
                    # Adjust for leap years
                    if is_leap_year(dt.year) and doy > 60:
                        doy -= 1
                    
                    # Compare to threshold
                    if not np.isnan(thresholds[doy]) and sst_ts[i_time] >= thresholds[doy]:
                        hot_days[i_time] = True
                        
                # Find runs of hot days (at least min_duration consecutive)
                # Simple approach: find connected components of hot days
                mhw_runs = find_hot_runs(hot_days, min_duration, gap_threshold)
                
                # Mark MHW days in the mask
                for start, end in mhw_runs:
                    mhw_mask[start:end+1, i_lat, i_lon] = 1
            else:
                # If any values are invalid, this cell is not considered a "sea cell"
                # So we don't mark any MHWs for this cell
                pass
                
    return mhw_mask

def find_hot_runs(hot_days, min_duration, gap_threshold):
    """
    Find runs of hot days that meet minimum duration requirements,
    and join runs separated by small gaps
    """
    runs = []
    i = 0
    while i < len(hot_days):
        if hot_days[i]:
            # Found start of a potential run
            start = i
            # Extend the run as long as days are hot
            while i < len(hot_days) and hot_days[i]:
                i += 1
            end = i - 1
            
            # If run is long enough, add it
            if (end - start + 1) >= min_duration:
                runs.append((start, end))
            else:
                # Check if we should join with nearby runs
                # This is a simplified version - in practice we'd want to be more sophisticated
                pass
        else:
            i += 1
            
    # Now join runs separated by gaps of 1 or 2 days
    if len(runs) > 1:
        merged_runs = [runs[0]]
        for i in range(1, len(runs)):
            prev_end = merged_runs[-1][1]
            curr_start = runs[i][0]
            # If gap is 1 or 2 days, merge
            if curr_start - prev_end <= gap_threshold + 1:
                # Merge runs
                merged_runs[-1] = (merged_runs[-1][0], runs[i][1])
            else:
                merged_runs.append(runs[i])
        runs = merged_runs
        
    return runs

# Run MHW detection
print("Starting MHW detection...")
mhw_mask = detect_mhw_events(ds_subset, thresholds, climatologies)

print("MHW detection complete")
print("MHW mask shape:", mhw_mask.shape)
print("Number of MHW days:", np.sum(mhw_mask))

# Create regional MHW events
def create_regional_events(mhw_mask, time_dim):
    """
    Create regional MHW events based on whether any cell is in an MHW
    """
    # Determine which days are active (at least one cell is in MHW)
    active_days = np.any(mhw_mask, axis=(1, 2))  # Shape: (time,)
    
    # Find maximal runs of consecutive active days
    events = []
    i = 0
    while i < len(active_days):
        if active_days[i]:
            # Found start of an event
            start = i
            # Extend until inactive
            while i < len(active_days) and active_days[i]:
                i += 1
            end = i - 1
            # Record event
            events.append((start, end))
        else:
            i += 1
            
    return events

regional_events = create_regional_events(mhw_mask, 'time')
print("Found", len(regional_events), "regional events")

# Convert event indices to dates
event_dates = []
for start_idx, end_idx in regional_events:
    start_date = ds_subset.time[start_idx].values.astype(datetime)
    end_date = ds_subset.time[end_idx].values.astype(datetime)
    event_dates.append({
        "onset": start_date.strftime("%Y-%m-%d"),
        "end": end_date.strftime("%Y-%m-%d")
    })

print("Events:", event_dates)

# Prepare report
report = {
    "region": {
        "lat_min": lat_min,
        "lat_max": lat_max,
        "lon_min": lon_min,
        "lon_max": lon_max
    },
    "baseline_analysed": {
        "start": "1992-01-01",
        "end": "2002-12-31"
    },
    "target_analysed": {
        "start": "2007-06-01",
        "end": "2007-08-31"
    },
    "events": event_dates,
    "complete": True,
    "caveats": ""
}

# Write report to JSON
import json
with open('output/report.json', 'w') as f:
    json.dump(report, f, indent=2)

print("Report written to output/report.json")

# Create NetCDF file with mhw mask
import xarray as xr

# Create DataArray with the mask
mhw_da = xr.DataArray(
    mhw_mask,
    dims=['time', 'latitude', 'longitude'],
    coords={
        'time': ds_subset.time,
        'latitude': ds_subset.latitude,
        'longitude': ds_subset.longitude
    },
    name='mhw',
    attrs={'units': 'boolean', 'long_name': 'Marine Heatwave'}
)

# Create Dataset
ds_output = xr.Dataset({'mhw': mhw_da})

# Save to NetCDF
ds_output.to_netcdf('output/mhw_mask.nc')
print("NetCDF file written to output/mhw_mask.nc")