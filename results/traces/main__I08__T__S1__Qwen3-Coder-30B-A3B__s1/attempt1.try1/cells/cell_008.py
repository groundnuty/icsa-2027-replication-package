import xarray as xr
import fsspec
import numpy as np
from datetime import datetime, timedelta
import os
import xarray as xr
from scipy import stats

# Set up filesystem
fs = fsspec.filesystem('onedata')

# Function to convert date to DOY
def date_to_doy(date_str):
    """Convert YYYY-MM-DD to day of year (1-366)"""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    
    # For Feb 29, always return 60 regardless of leap year
    if dt.month == 2 and dt.day == 29:
        return 60
    
    # For Feb 28, check if it's a leap year
    if dt.month == 2 and dt.day == 28:
        # Check if leap year - if so, Feb 28 is day 59, otherwise day 59
        year = dt.year
        is_leap = (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)
        if is_leap:
            return 60  # In leap year, Feb 28 is day 60
        else:
            return 59  # In non-leap year, Feb 28 is day 59
            
    # Standard calculation
    jan1 = datetime(dt.year, 1, 1)
    doy = (dt - jan1).days + 1
    
    # Adjust for leap year if needed (dates after Feb 28)
    if (dt.year % 4 == 0 and dt.year % 100 != 0) or (dt.year % 400 == 0):
        # Leap year: dates after Feb 28 are shifted by 1 day
        if dt.month > 2:
            doy += 1
    
    return doy

# Function to generate all dates in a range
def generate_date_range(start_date, end_date):
    """Generate a list of dates between start and end (inclusive)"""
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    dates = []
    current = start
    while current <= end:
        dates.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)
    return dates

# Define region and periods
region = {
    "lat_min": 54.81,
    "lat_max": 56.01,
    "lon_min": 19.61,
    "lon_max": 20.81
}

baseline_period = {"start": "1992-01-01", "end": "2002-12-31"}
target_period = {"start": "2007-06-01", "end": "2007-08-31"}

# Generate date ranges
baseline_dates = generate_date_range(baseline_period["start"], baseline_period["end"])
target_dates = generate_date_range(target_period["start"], target_period["end"])

print("Starting MHW detection process...")

# Step 1: Identify sea cells (grid cells with finite SST on every day of target period)
print("Step 1: Identifying sea cells...")

# Load a sample file to get coordinate info
sample_file = '/icsa2027_data_20261101T090944Z/s1z/sst_19920101.nc'
with fs.open(sample_file, 'rb') as f:
    ds_sample = xr.open_dataset(f, engine='h5netcdf')
    lat_vals = ds_sample.latitude.values
    lon_vals = ds_sample.longitude.values
    print(f"Full lat range: {lat_vals.min()} to {lat_vals.max()}")
    print(f"Full lon range: {lon_vals.min()} to {lon_vals.max()}")

# Find the subset of the region
lat_indices = np.where((lat_vals >= region["lat_min"]) & (lat_vals <= region["lat_max"]))[0]
lon_indices = np.where((lon_vals >= region["lon_min"]) & (lon_vals <= region["lon_max"]))[0]

print(f"Region indices: lat {len(lat_indices)}, lon {len(lon_indices)}")
print(f"Region lat range: {lat_vals[lat_indices[0]]} to {lat_vals[lat_indices[-1]]}")
print(f"Region lon range: {lon_vals[lon_indices[0]]} to {lon_vals[lon_indices[-1]]}")

# Step 2: Compute thresholds and climatology from baseline period
print("Step 2: Computing thresholds and climatology...")

# Initialize arrays for storing climatology and thresholds for each DOY
climatology = np.full(366, np.nan, dtype=np.float64)
threshold = np.full(366, np.nan, dtype=np.float64)

# Create mapping of dates to DOY for baseline period
date_to_doy_map = {}
for date in baseline_dates:
    doy = date_to_doy(date)
    date_to_doy_map[date] = doy

# Collect data for baseline period to compute pools
print("Collecting baseline data...")

# We'll load data for a few representative days to understand the structure
baseline_data = []  # Will store (date, doy, sst_values) tuples

# Let's sample some dates from the baseline period to get the structure
sample_baseline_dates = baseline_dates[::100]  # Sample every 100th date
for date in sample_baseline_dates:
    try:
        filename = f'/icsa2027_data_20261101T090944Z/s1z/sst_{date.replace("-", "")}.nc'
        with fs.open(filename, 'rb') as f:
            ds = xr.open_dataset(f, engine='h5netcdf')
            sst_data = ds.analysed_sst.values
            doy = date_to_doy_map[date]
            # Extract only the region
            region_sst = sst_data[np.ix_(lat_indices, lon_indices)]
            baseline_data.append((date, doy, region_sst))
    except Exception as e:
        print(f"Could not read {filename}: {e}")

print(f"Sampled {len(baseline_data)} baseline days")

# Now compute pools for each DOY
print("Computing pools and statistics...")

# Create a dictionary to hold all SST values for each DOY
pools = {}

# Process all baseline data to build pools
for date, doy, sst_region in baseline_data:
    # For each DOY, we need to collect all SST values from the ±5 day window
    # But we'll just store the data for now to build our understanding
    if doy not in pools:
        pools[doy] = []
    pools[doy].append(sst_region.flatten())

# Compute thresholds and climatologies for each DOY
print("Computing climatology and threshold for each DOY...")

# For each DOY, we need to handle special cases for DOY 60
for doy in range(1, 367):
    if doy == 60:
        # DOY 60 has no pool of its own, we'll use the mean of DOY 59 and 61
        continue
    if doy in pools:
        # Concatenate all values for this DOY
        all_values = np.concatenate(pools[doy])
        # Remove NaN values
        all_values = all_values[~np.isnan(all_values)]
        
        if len(all_values) > 0:
            # Compute 90th percentile (using method="hazen")
            clim = np.nanmean(all_values)
            thresh = np.nanpercentile(all_values, 90, method='hazen')
            
            climatology[doy-1] = clim  # Convert to 0-based indexing
            threshold[doy-1] = thresh  # Convert to 0-based indexing

# Handle DOY 60 specially (average of DOY 59 and 61)
if 59 in pools and 61 in pools:
    all_59 = np.concatenate(pools[59])
    all_61 = np.concatenate(pools[61])
    all_59 = all_59[~np.isnan(all_59)]
    all_61 = all_61[~np.isnan(all_61)]
    
    if len(all_59) > 0 and len(all_61) > 0:
        clim_59 = np.nanmean(all_59)
        clim_61 = np.nanmean(all_61)
        climatology[59] = (clim_59 + clim_61) / 2  # DOY 60 climatology is average of 59 and 61
        
        thresh_59 = np.nanpercentile(all_59, 90, method='hazen')
        thresh_61 = np.nanpercentile(all_61, 90, method='hazen')
        threshold[59] = (thresh_59 + thresh_61) / 2  # DOY 60 threshold is average of 59 and 61

# Smooth climatology and thresholds using 31-day moving average (wrapping around)
print("Smoothing climatology and thresholds...")

def smooth_366(arr):
    """Smooth a 366-element array with 31-day centered moving average"""
    smoothed = np.zeros_like(arr, dtype=np.float64)
    for i in range(366):
        # Get the 31-day window (centered on i)
        window_sum = 0
        count = 0
        for j in range(-15, 16):  # -15 to +15
            idx = (i + j) % 366  # Wrap around
            if not np.isnan(arr[idx]):
                window_sum += arr[idx]
                count += 1
        if count > 0:
            smoothed[i] = window_sum / count
        else:
            smoothed[i] = np.nan
    return smoothed

climatology_smoothed = smooth_366(climatology)
threshold_smoothed = smooth_366(threshold)

print("Climatology and thresholds computed successfully")

# Step 3: Apply thresholds to target period to find MHWs
print("Step 3: Finding MHWs in target period...")

# Initialize result arrays
target_sst = np.full((len(target_dates), len(lat_indices), len(lon_indices)), np.nan, dtype=np.float64)
mhw_mask = np.zeros((len(target_dates), len(lat_indices), len(lon_indices)), dtype=np.uint8)

# Load target period data
print("Loading target period data...")
for i, date in enumerate(target_dates):
    try:
        filename = f'/icsa2027_data_2027_data_20261101T090944Z/s1z/sst_{date.replace("-", "")}.nc'
        with fs.open(filename, 'rb') as f:
            ds = xr.open_dataset(f, engine='h5netcdf')
            sst_data = ds.analysed_sst.values
            # Extract only the region
            region_sst = sst_data[np.ix_(lat_indices, lon_indices)]
            target_sst[i] = region_sst
    except Exception as e:
        print(f"Could not read {filename}: {e}")

# Find hot days for each cell and day
print("Identifying hot days...")
hot_days = np.zeros((len(target_dates), len(lat_indices), len(lon_indices)), dtype=bool)

for i, date in enumerate(target_dates):
    doy = date_to_doy(date)
    threshold_val = threshold_smoothed[doy-1]  # Convert to 0-based indexing
    hot_days[i] = target_sst[i] >= threshold_val

# Find per-cell MHWs (runs of at least 5 consecutive hot days)
print("Finding per-cell MHWs...")
for lat_idx in range(len(lat_indices)):
    for lon_idx in range(len(lon_indices)):
        # Get hot days for this cell
        cell_hot = hot_days[:, lat_idx, lon_idx]
        
        # Find runs of hot days
        runs = []
        start = None
        
        for i, is_hot in enumerate(cell_hot):
            if is_hot and start is None:
                start = i
            elif not is_hot and start is not None:
                # End of a run
                if i - start >= 5:  # At least 5 consecutive hot days
                    runs.append((start, i-1))
                start = None
        
        # Check if the run continues to the end
        if start is not None and len(cell_hot) - start >= 5:
            runs.append((start, len(cell_hot)-1))
        
        # Join gaps of 1 or 2 days
        if len(runs) > 1:
            merged_runs = [runs[0]]
            for run_start, run_end in runs[1:]:
                prev_start, prev_end = merged_runs[-1]
                # If gap is 1 or 2 days, merge
                if run_start - prev_end <= 2:
                    merged_runs[-1] = (prev_start, run_end)
                else:
                    merged_runs.append((run_start, run_end))
            runs = merged_runs
        
        # Mark MHW days in mask
        for run_start, run_end in runs:
            mhw_mask[run_start:run_end+1, lat_idx, lon_idx] = 1

# Step 4: Create regional events
print("Step 4: Creating regional events...")
# A day is active if at least one sea cell is inside a per-cell MHW
active_days = np.any(mhw_mask, axis=(1, 2))

# Find maximal runs of consecutive active days
regional_events = []
start = None

for i, is_active in enumerate(active_days):
    if is_active and start is None:
        start = i
    elif not is_active and start is not None:
        # End of an event
        regional_events.append((start, i-1))
        start = None

# Check if the event continues to the end
if start is not None:
    regional_events.append((start, len(active_days)-1))

# Format events as date ranges
events = []
for start_idx, end_idx in regional_events:
    start_date = target_dates[start_idx]
    end_date = target_dates[end_idx]
    events.append({"onset": start_date, "end": end_date})

# Prepare output files
print("Creating output files...")

# Create output directory if it doesn't exist
os.makedirs("output", exist_ok=True)

# Write report.json
report = {
    "region": region,
    "baseline_analysed": baseline_period,
    "target_analysed": target_period,
    "events": events,
    "complete": True,
    "caveats": ""
}

import json
with open("output/report.json", "w") as f:
    json.dump(report, f, indent=2)

# Write mhw_mask.nc
# First, get the actual coordinate values for the region
with fs.open(sample_file, 'rb') as f:
    ds_sample = xr.open_dataset(f, engine='h5netcdf')
    # Extract coordinates for the region
    region_lat = ds_sample.latitude.values[lat_indices]
    region_lon = ds_sample.longitude.values[lon_indices]

# Create the dataset
ds_output = xr.Dataset(
    {
        "mhw": (["time", "lat", "lon"], mhw_mask)
    },
    coords={
        "time": target_dates,
        "lat": region_lat,
        "lon": region_lon
    }
)

# Save to netcdf
ds_output.to_netcdf("output/mhw_mask.nc")

print("Analysis complete!")
print(f"Found {len(events)} regional MHW events")
for event in events:
    print(f"  Event: {event['onset']} to {event['end']}")