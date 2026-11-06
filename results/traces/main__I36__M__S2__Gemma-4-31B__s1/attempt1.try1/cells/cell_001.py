import xarray as xr
import numpy as np
import pandas as pd
import json
from datetime import datetime, timedelta

def get_doy(dt):
    # dt is a pandas timestamp
    # Jan 1 = 1, ..., Feb 28 = 59, Feb 29 = 60, Mar 1 = 61, ..., Dec 31 = 366
    # Non-leap years have no day 60.
    is_leap = (dt.year % 4 == 0 and (dt.year % 100 != 0 or dt.year % 400 == 0))
    doy = dt.timetuple().tm_yday
    if not is_leap and dt.month >= 3:
        return doy + 1
    return doy

def get_date_from_doy(year, doy):
    # Given year and doy (1-366), return the date.
    # This is the inverse of get_doy.
    is_leap = (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0))
    if doy == 60 and not is_leap:
        return None # Day 60 doesn't exist in non-leap years
    
    if doy <= 59:
        # Standard day of year
        return pd.Timestamp(year, 1, 1) + pd.Timedelta(days=doy-1)
    else:
        # doy >= 61
        # If leap, doy is standard. If non-leap, doy is standard + 1.
        standard_doy = doy if is_leap else doy - 1
        return pd.Timestamp(year, 1, 1) + pd.Timedelta(days=standard_doy-1)

# Define constants
LAT_MIN, LAT_MAX = 60.09, 61.29
LON_MIN, LON_MAX = 20.01, 21.21
TARGET_START = "2003-06-01"
TARGET_END = "2003-08-31"
BASELINE_START_YEAR = 1992
BASELINE_END_YEAR = 2002
FILE_PATH = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"

# 1. Load data and subset
ds = xr.open_dataset(FILE_PATH, engine="h5netcdf")
# We need baseline window (1991-12-27 to 2003-01-05) and target period (2003-06-01 to 2003-08-31)
# To be safe, just load 1991-12-27 to 2003-08-31.
ds_subset = ds.sel(
    lat=slice(LAT_MIN, LAT_MAX),
    lon=slice(LON_MIN, LON_MAX),
    time=slice("1991-12-27", "2003-08-31")
).load()

# Ensure float64
sst = ds_subset.sst.astype(np.float64)
lat = ds_subset.lat.values
lon = ds_subset.lon.values
time = pd.to_datetime(ds_subset.time.values)

# Target period indices
target_mask = (time >= pd.Timestamp(TARGET_START)) & (time <= pd.Timestamp(TARGET_END))
target_times = time[target_mask]
target_sst = sst.sel(time=slice(TARGET_START, TARGET_END))

# 2. Sea cells
# Cells whose SST is finite on every day of the target period.
# Target SST is (time, lat, lon)
# Sea cells: all time indices for target period must be finite.
finite_mask = np.isfinite(target_sst.values)
sea_cells_mask = np.all(finite_mask, axis=0) # (lat, lon)

sea_lat_idx, sea_lon_idx = np.where(sea_cells_mask)
num_sea_cells = len(sea_lat_idx)

# 3. Threshold and Climatology
# baseline years 1992-2002
baseline_years = range(BASELINE_START_YEAR, BASELINE_END_YEAR + 1)
doy_range = [d for d in range(1, 367) if d != 60]

# Pre-calculate windows for each d
# windows[d] = list of (start_date, end_date)
windows = {}
for d in doy_range:
    win_list = []
    for y in baseline_years:
        b_date = get_date_from_doy(y, d)
        if b_date:
            win_list.append((b_date - pd.Timedelta(days=5), b_date + pd.Timedelta(days=5)))
    windows[d] = win_list

# For each sea cell, compute threshold and climatology
# This could be slow. Let's try to vectorize if possible.
# We can pre-slice the SST for all baseline-relevant dates.
all_baseline_dates = pd.to_datetime(ds_subset.time.values)
# Only dates from 1991-12-27 to 2003-01-05 are used for baseline pools.
baseline_relevant_mask = (all_baseline_dates >= pd.Timestamp("1991-12-27")) & (all_baseline_dates <= pd.Timestamp("2003-01-05"))
baseline_sst = sst.sel(time=slice("1991-12-27", "2003-01-05"))
baseline_times = pd.to_datetime(baseline_sst.time.values)

# Initialize arrays
# thresholds: (lat, lon, 366)
# climatology: (lat, lon, 366)
thresholds = np.full((len(lat), len(lon), 366), np.nan, dtype=np.float64)
climatologies = np.full((len(lat), len(lon), 366), np.nan, dtype=np.float64)

# We only need to compute for sea cells.
for i in range(num_sea_cells):
    slat, slon = sea_lat_idx[i], sea_lon_idx[i]
    
    # SST for this cell over the baseline period
    cell_sst_baseline = baseline_sst.isel(lat=slat, lon=slon).values
    
    for d in doy_range:
        pool = []
        for start_win, end_win in windows[d]:
            # Find indices of dates in the window
            win_mask = (baseline_times >= start_win) & (baseline_times <= end_win)
            pool.extend(cell_sst_baseline[win_mask])
        
        pool = np.array(pool)
        pool = pool[np.isfinite(pool)]
        
        if len(pool) > 0:
            thresholds[slat, slon, d-1] = np.nanpercentile(pool, 90, method='hazen')
            climatologies[slat, slon, d-1] = np.nanmean(pool)

# Set day 60 (index 59)
thresholds[:, :, 59] = (thresholds[:, :, 58] + thresholds[:, :, 60]) / 2
climatologies[:, :, 59] = (climatologies[:, :, 58] + climatologies[:, :, 60]) / 2

# Smoothing: 31-day moving mean
def smooth_array(arr):
    # arr shape: (lat, lon, 366)
    smoothed = np.full_like(arr)
    for i in range(366):
        # Window: i-15 to i+15 modulo 366
        indices = [(i + k) % 366 for k in range(-15, 16)]
        smoothed[:, :, i] = np.nanmean(arr[:, :, indices], axis=-1)
    return smoothed

smoothed_thresholds = smooth_array(thresholds)
smoothed_climatologies = smooth_array(climatologies)

# 4. Per-cell MHWs
# Target period SST: (time, lat, lon)
target_sst_vals = target_sst.values
target_doy = np.array([get_doy(t) for t in target_times])

# mhw_mask: (time, lat, lon)
mhw_mask = np.zeros(target_sst_vals.shape, dtype=np.uint8)

for i in range(num_sea_cells):
    slat, slon = sea_lat_idx[i], sea_lon_idx[i]
    
    # SST for this cell in target period
    cell_sst_target = target_sst_vals[:, slat, slon]
    # Thresholds for this cell for the target doys
    cell_thresh_target = smoothed_thresholds[slat, slon, target_doy - 1]
    
    # Hot days
    is_hot = cell_sst_target >= cell_thresh_target
    
    # Identify MHWs
    # 1. Find runs of True
    runs = []
    start = None
    for t in range(len(is_hot)):
        if is_hot[t] and start is None:
            start = t
        elif not is_hot[t] and start is not None:
            runs.append([start, t - 1])
            start = None
    if start is not None:
        runs.append([start, len(is_hot) - 1])
        
    # 2. Filter for runs length >= 5
    mhw_runs = [run for run in runs if run[1] - run[0] + 1 >= 5]
    
    # 3. Join gaps of 1 or 2 non-hot days
    if not mhw_runs:
        continue
        
    mhw_runs.sort()
    joined = False
    while not joined:
        joined = True
        new_runs = []
        if not mhw_runs:
            break
        
        curr_start, curr_end = mhw_runs[0]
        for next_start, next_end in mhw_runs[1:]:
            gap = next_start - curr_end - 1
            if gap <= 2:
                curr_end = next_end
                joined = False
            else:
                new_runs.append([curr_start, curr_end])
                curr_start, curr_end = next_start, next_end
        new_runs.append([curr_start, curr_end])
        mhw_runs = new_runs
        if joined: break
    
    # Set mask
    for start, end in mhw_runs:
        mhw_mask[start:end+1, slat, slon] = 1

# 5. Regional Events
# Active days: at least one sea cell is in an MHW
active_days = np.any(mhw_mask[:, sea_lat_idx, :][:, :, sea_lon_idx], axis=(1, 2)) # This is not quite right
# Let's do it properly:
active_days = np.zeros(len(target_times), dtype=bool)
for t in range(len(target_times)):
    # Check if any sea cell is 1 at time t
    # We can use the mhw_mask indexed by sea cells
    # mhw_mask shape: (time, lat, lon)
    # We want to know if any (slat, slon) in sea_cells has mhw_mask[t, slat, slon] == 1
    # Let's use the sea_cells_mask
    active_days[t] = np.any(mhw_mask[t] & sea_cells_mask)

# Regional MHW events: maximal runs of active days
regional_events = []
start = None
for t in range(len(active_days)):
    if active_days[t] and start is None:
        start = t
    elif not active_days[t] and start is not None:
        regional_events.append({
            "onset": target_times[start].strftime('%Y-%m-%d'),
            "end": target_times[t-1].strftime('%Y-%m-%d')
        })
        start = None
if start is not None:
    regional_events.append({
        "onset": target_times[start].strftime('%Y-%m-%d'),
        "end": target_times[-1].strftime('%Y-%m-%d')
    })

# Write outputs
# mhw_mask.nc
out_ds = xr.Dataset(
    {"mhw": (["time", "lat", "lon"], mhw_mask.astype(np.uint8))},
    coords={"time": target_times, "lat": lat, "lon": lon}
)
out_ds.to_netcdf("output/mhw_mask.nc")

# report.json
report = {
    "region": {"lat_min": LAT_MIN, "lat_max": LAT_MAX, "lon_min": LON_MIN, "lon_max": LON_MAX},
    "baseline_analysed": {
        "start": "1991-12-27",
        "end": "2003-01-05"
    },
    "target_analysed": {
        "start": TARGET_START,
        "end": TARGET_END
    },
    "events": regional_events,
    "complete": True,
    "caveats": ""
}

with open("output/report.json", "w") as f:
    json.dump(report, f, indent=2)

print("Success")
