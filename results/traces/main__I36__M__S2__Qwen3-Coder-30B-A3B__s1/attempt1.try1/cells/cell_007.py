import xarray as xr
import numpy as np
from datetime import datetime, timedelta
import os

# Create output directory
os.makedirs('output', exist_ok=True)

# Open the dataset
ds = xr.open_dataset('/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', engine='h5netcdf')

# Define region of interest
lat_min, lat_max = 60.09, 61.29
lon_min, lon_max = 20.01, 21.21

# Find indices for the region
lat_indices = np.where((ds.latitude >= lat_min) & (ds.latitude <= lat_max))[0]
lon_indices = np.where((ds.longitude >= lon_min) & (ds.longitude <= lon_max))[0]

print(f"Region indices - Latitude: {lat_indices[0]} to {lat_indices[-1]}, Longitude: {lon_indices[0]} to {lon_indices[-1]}")

# Get the subset of data for our region
subset = ds.analysed_sst.isel(latitude=lat_indices, longitude=lon_indices)
print(f"Subset shape: {subset.shape}")

# Define periods
target_start = np.datetime64('2003-06-01')
target_end = np.datetime64('2003-08-31')
baseline_start = np.datetime64('1992-01-01')
baseline_end = np.datetime64('2002-12-31')

# Filter for baseline period
baseline_mask = (ds.time >= baseline_start) & (ds.time <= baseline_end)
baseline_times = ds.time[baseline_mask]
print(f"Baseline period: {baseline_times[0].values} to {baseline_times[-1].values}")
print(f"Number of baseline days: {len(baseline_times)}")

# Filter for target period  
target_mask = (ds.time >= target_start) & (ds.time <= target_end)
target_times = ds.time[target_mask]
print(f"Target period: {target_times[0].values} to {target_times[-1].values}")
print(f"Number of target days: {len(target_times)}")

# Create mapping from date to day of year
doy_map = {}
for date in baseline_times:
    dt = datetime.strptime(str(date), '%Y-%m-%dT%H:%M:%S.%f')
    doy = dt.timetuple().tm_yday
    doy_map[date.values] = doy

# Extract SST data for baseline and target periods
baseline_sst = ds.analysed_sst.sel(time=baseline_times).values
target_sst = ds.analysed_sst.sel(time=target_times).values

print(f"Baseline SST shape: {baseline_sst.shape}")
print(f"Target SST shape: {target_sst.shape}")

# Close the original dataset
ds.close()

# Now perform the MHW analysis
print("Starting MHW analysis...")

# Step 1: Identify sea cells (cells with finite SST on every day of target period)
sea_cells = detect_sea_cells(target_sst, target_times.values)
print(f"Number of sea cells: {np.sum(sea_cells)}")

# Step 2: Compute thresholds and climatology using baseline period
print("Computing thresholds and climatology...")
thresholds, climatologies = compute_threshold_and_climatology(
    baseline_sst, baseline_times.values, doy_map
)

# Step 3: Find hot days in target period
print("Finding hot days...")
hot_days = find_hot_days(target_sst, thresholds, climatologies, target_times.values, doy_map)

# Step 4: Identify MHWs
print("Identifying MHWs...")
mhw_mask = identify_mhws(hot_days)

# Step 5: Create regional events
print("Creating regional events...")
# A day is active if at least one sea cell is inside an MHW
active_days = np.any(mhw_mask, axis=(1,2))  # Shape: (n_target_days,)

# Find regional MHW events (maximal runs of consecutive active days)
events = []
start_event = None
for i, is_active in enumerate(active_days):
    if is_active and start_event is None:
        start_event = i
    elif not is_active and start_event is not None:
        # End of an event
        events.append((start_event, i-1))
        start_event = None

# Don't forget a possible ongoing event at the end
if start_event is not None:
    events.append((start_event, len(active_days)-1))

# Convert to proper date format for reporting
event_list = []
for start_idx, end_idx in events:
    start_date = str(target_times[start_idx].values)[:10]
    end_date = str(target_times[end_idx].values)[:10]
    event_list.append({"onset": start_date, "end": end_date})

# Prepare report
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
        "start": str(target_start)[:10],
        "end": str(target_end)[:10]
    },
    "events": event_list,
    "complete": True,
    "caveats": ""
}

# Save the report
import json
with open('output/report.json', 'w') as f:
    json.dump(report, f, indent=2)

# Save the NetCDF file
# We need to create the proper NetCDF with correct coordinates
lat_vals = ds.latitude.isel(latitude=lat_indices).values
lon_vals = ds.longitude.isel(longitude=lon_indices).values

# Reopen dataset to get the proper coordinates
ds_full = xr.open_dataset('/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', engine='h5netcdf')
lat_vals = ds_full.latitude.isel(latitude=lat_indices).values
lon_vals = ds_full.longitude.isel(longitude=lon_indices).values
time_vals = target_times.values

# Create the dataset
mhw_ds = xr.Dataset(
    {
        'mhw': (['time', 'lat', 'lon'], mhw_mask)
    },
    coords={
        'time': time_vals,
        'lat': lat_vals,
        'lon': lon_vals
    }
)

# Set attributes
mhw_ds['mhw'].attrs['units'] = 'binary'
mhw_ds['mhw'].attrs['long_name'] = 'Marine Heatwave indicator'

# Save to NetCDF
mhw_ds.to_netcdf('output/mhw_mask.nc')

print("Analysis complete!")
print(f"Events detected: {len(event_list)}")
print(f"Report saved to output/report.json")
print(f"MHW mask saved to output/mhw_mask.nc")

# Close datasets
ds_full.close()