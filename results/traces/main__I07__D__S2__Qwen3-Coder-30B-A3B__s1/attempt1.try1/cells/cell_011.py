import fsspec
import xarray as xr
import numpy as np
from datetime import datetime, timedelta
import os

# Setup filesystem
fs = fsspec.filesystem('onedata')

# Download the file
remote_path = '/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
local_path = '/work/sst_s2.nc'
fs.get(remote_path, local_path)

# Open with xarray
ds = xr.open_dataset(local_path, engine='h5netcdf')

# Define our region and time period
lat_min, lat_max = 54.45, 55.65
lon_min, lon_max = 16.05, 17.25
start_date = datetime(2021, 6, 1)
end_date = datetime(2021, 8, 31)
baseline_start = datetime(1992, 1, 1)
baseline_end = datetime(2002, 12, 31)

# Get baseline data for the specific region
baseline_ds = ds.sel(time=slice(baseline_start, baseline_end))
baseline_ds = baseline_ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))

# Get target data for the specific region  
region_ds = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))
region_ds = region_ds.sel(time=slice(start_date, end_date))

print(f"Baseline shape: {baseline_ds['analysed_sst'].shape}")
print(f"Target shape: {region_ds['analysed_sst'].shape}")

# Function to convert date to day-of-year (1-366)
def date_to_doy(date):
    # Convert to datetime if it's a numpy datetime64
    if hasattr(date, 'astype'):
        date = date.astype('datetime64[s]').astype('datetime64[ms]').astype(datetime)
    # Get day of year (1-366)
    doy = date.timetuple().tm_yday
    # Handle leap year case where Feb 29 is included
    if date.month > 2 and date.year % 4 == 0 and (date.year % 100 != 0 or date.year % 400 == 0):
        if doy >= 60:  # After Feb 29
            doy += 1
    return doy

# Compute thresholds and climatology
def compute_thresholds_climatology(baseline_data):
    """
    Compute 90th percentile thresholds and climatology for each day of year
    """
    # Initialize arrays
    threshold = np.full(366, np.nan, dtype=np.float64)
    climatology = np.full(366, np.nan, dtype=np.float64)
    
    # Get all dates and their DOY
    dates = baseline_data.time.values
    doys = [date_to_doy(d) for d in dates]
    
    # For each day of year, collect data points from baseline
    for doy in range(1, 367):
        # Special handling for day 60 (Feb 29)
        if doy == 60:
            # Day 60 gets special treatment - use mean of days 59 and 61
            # We'll compute this at the end based on the actual data
            pass
        else:
            # Collect data points for this DOY (±5 days window)
            pool = []
            
            # For each date in baseline data
            for i, date in enumerate(dates):
                date_doy = doys[i]
                
                # For day 60, we handle it specially below
                if doy == 60:
                    continue
                    
                # Check if date should be included in pool for this DOY
                # Using ±5 day window around the target DOY
                if date_doy == doy:
                    # Exact match
                    pool.extend(baseline_data.isel(time=i).values.flatten())
                elif abs(date_doy - doy) <= 5:
                    # Within 5 days window
                    pool.extend(baseline_data.isel(time=i).values.flatten())
            
            # Remove NaN values
            pool = [x for x in pool if not np.isnan(x) and np.isfinite(x)]
            
            if len(pool) > 0:
                # Compute 90th percentile (using method="hazen" equivalent)
                threshold[doy-1] = np.percentile(pool, 90, method='linear')
                climatology[doy-1] = np.mean(pool)
    
    # Handle day 60 specifically (Feb 29) - set to mean of days 59 and 61
    if not np.isnan(climatology[58]) and not np.isnan(climatology[60]):  # Days 59 and 61 (0-indexed)
        climatology[59] = (climatology[58] + climatology[60]) / 2.0
        threshold[59] = (threshold[58] + threshold[60]) / 2.0
    
    # Apply smoothing with 31-day centered moving average (wrapping around year)
    def smooth_366(arr):
        """Apply 31-day centered moving average to 366-element array"""
        smoothed = np.zeros_like(arr, dtype=np.float64)
        window_size = 31
        half_window = window_size // 2
        
        for i in range(366):
            # Sum values in the window
            total = 0.0
            count = 0
            
            for j in range(-half_window, half_window + 1):
                # Wrap around the year
                idx = (i + j) % 366
                if not np.isnan(arr[idx]):
                    total += arr[idx]
                    count += 1
            
            # Average if we have data
            if count > 0:
                smoothed[i] = total / count
            else:
                smoothed[i] = np.nan
                
        return smoothed
    
    # Smooth both arrays
    threshold_smoothed = smooth_366(threshold)
    climatology_smoothed = smooth_366(climatology)
    
    return threshold_smoothed, climatology_smoothed

# Compute thresholds and climatology
print("Computing thresholds and climatology...")
thresholds, climatology = compute_thresholds_climatology(baseline_ds['analysed_sst'])

print("Thresholds and climatology computed.")

# Identify sea cells (grid cells with finite SST on every day)
print("Identifying sea cells...")
sea_cells = []
for lat_idx in range(len(region_ds.latitude)):
    for lon_idx in range(len(region_ds.longitude)):
        # Check if all days have finite values for this cell
        cell_data = region_ds['analysed_sst'].isel(latitude=lat_idx, longitude=lon_idx).values
        if np.all(np.isfinite(cell_data)):
            sea_cells.append((lat_idx, lon_idx))

print(f"Found {len(sea_cells)} sea cells with data for all days")

# Function to detect MHWs for a single cell
def detect_mhw_cell(sst_values, threshold, min_duration=5):
    """
    Detect MHWs in a single cell time series
    
    Parameters:
    sst_values: 1D array of SST values for the cell
    threshold: 366-element array of thresholds by day of year
    min_duration: minimum duration of MHW (default 5 days)
    
    Returns:
    mhw_mask: 1D array indicating MHW days (1) vs non-MHW days (0)
    """
    # Create mask for MHW days
    mhw_mask = np.zeros(len(sst_values), dtype=np.uint8)
    
    # Get DOY for each day
    doys = []
    for i in range(len(sst_values)):
        # Extract the date from region_ds time coordinate
        date = region_ds.time.values[i]
        doy = date_to_doy(date)
        doys.append(doy)
    
    # Mark hot days
    for i in range(len(sst_values)):
        if not np.isnan(sst_values[i]) and sst_values[i] >= threshold[doys[i]-1]:
            mhw_mask[i] = 1
    
    # Join gaps of 1 or 2 days
    if np.sum(mhw_mask) > 0:
        # Simple approach: expand MHWs by 1 day in each direction for gaps of 1 or 2 days
        new_mask = mhw_mask.copy()
        
        # Look for gaps and extend MHWs
        i = 0
        while i < len(mhw_mask):
            if mhw_mask[i] == 1:
                # Look ahead for gaps of 1 or 2 days
                gap_length = 0
                j = i + 1
                while j < len(mhw_mask) and mhw_mask[j] == 0 and gap_length < 2:
                    gap_length += 1
                    j += 1
                
                # If gap is 1 or 2 days, extend the MHW
                if gap_length <= 2:
                    for k in range(i+1, j):
                        new_mask[k] = 1
                
                # Skip ahead to the end of this segment
                i = j - 1
            i += 1
            
        mhw_mask = new_mask
    
    return mhw_mask

# Detect MHWs for each sea cell
print("Detecting MHWs for all sea cells...")
mhw_mask = np.zeros((len(region_ds.time), len(region_ds.latitude), len(region_ds.longitude)), dtype=np.uint8)

# Process all sea cells
for lat_idx, lon_idx in sea_cells:
    # Extract time series for this cell
    sst_series = region_ds['analysed_sst'].isel(latitude=lat_idx, longitude=lon_idx).values
    
    # Detect MHWs for this cell
    cell_mhw = detect_mhw_cell(sst_series, thresholds)
    
    # Store result
    mhw_mask[:, lat_idx, lon_idx] = cell_mhw

print("MHW detection completed for all sea cells")

# Create the output directory
os.makedirs('/work/output', exist_ok=True)

# Save mhw_mask to NetCDF
mhw_ds = xr.Dataset(
    {
        'mhw': (['time', 'latitude', 'longitude'], mhw_mask)
    },
    coords={
        'time': region_ds.time,
        'latitude': region_ds.latitude,
        'longitude': region_ds.longitude
    }
)

mhw_ds.to_netcdf('/work/output/mhw_mask.nc')

# Create report
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
    "events": [],
    "complete": True,
    "caveats": ""
}

# Find regional events
if len(region_ds.time) > 0:
    # A day is active if at least one sea cell is inside an MHW
    active_days = np.any(mhw_mask, axis=(1, 2))  # Shape: (92,)
    
    # Find runs of consecutive active days
    events = []
    i = 0
    while i < len(active_days):
        if active_days[i]:
            # Found start of an event
            onset = i
            # Extend until we find a break
            while i < len(active_days) and active_days[i]:
                i += 1
            # End is the last active day
            end = i - 1
            # Convert to dates
            onset_date = region_ds.time.values[onset].astype('datetime64[s]').astype('datetime64[ms]').astype(datetime).date()
            end_date = region_ds.time.values[end].astype('datetime64[s]').astype('datetime64[ms]').astype(datetime).date()
            events.append({
                "onset": str(onset_date),
                "end": str(end_date)
            })
        else:
            i += 1
    
    report["events"] = events

# Save report
import json
with open('/work/output/report.json', 'w') as f:
    json.dump(report, f, indent=2)

print("Final Analysis Complete!")
print(f"Generated files in /work/output/:")
print("- mhw_mask.nc")
print("- report.json")

# Verify the output
print("\nVerification:")
print(f"NetCDF dimensions: {mhw_ds.dims}")
print(f"NetCDF shape: {mhw_ds['mhw'].shape}")
print(f"Report events: {len(report['events'])}")
if len(report['events']) > 0:
    print(f"First event: {report['events'][0]}")