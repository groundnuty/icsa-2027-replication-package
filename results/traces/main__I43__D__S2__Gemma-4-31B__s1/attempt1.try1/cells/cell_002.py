import xarray as xr
import numpy as np
import pandas as pd
import datetime
import json
import os

# Constants
REGION = {"lat_min": 62.25, "lat_max": 63.45, "lon_min": 18.73, "lon_max": 19.93}
TARGET_START = "2017-06-01"
TARGET_END = "2017-08-31"
BASELINE_START = "1992-01-01"
BASELINE_END = "2002-12-31"
REMOTE_PATH = "icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
LOCAL_PATH = "/work/sst_s2.nc"

def get_doy_fixed(dt):
    """Map date to DOY 1-366 based on month and day."""
    yday = (dt - datetime.date(dt.year, 1, 1)).days + 1
    is_leap = (dt.year % 4 == 0 and (dt.year % 100 != 0 or dt.year % 400 == 0))
    if not is_leap and yday > 59:
        return yday + 1
    return yday

# Load dataset
import fsspec
fs = fsspec.filesystem('onedata')
if not os.path.exists(LOCAL_PATH):
    fs.get(REMOTE_PATH, LOCAL_PATH)

ds = xr.open_dataset(LOCAL_PATH, engine="h5netcdf")

# Slice to region
ds_reg = ds.sel(
    latitude=slice(REGION["lat_min"], REGION["lat_max"]),
    longitude=slice(REGION["lon_min"], REGION["lon_max"])
)

# Target period
target_start_dt = pd.to_datetime(TARGET_START)
target_end_dt = pd.to_datetime(TARGET_END)
ds_target = ds_reg.sel(time=slice(target_start_dt, target_end_dt))

# Identify sea cells: SST finite on every day of target period
sst_target = ds_target['analysed_sst'].astype(np.float64)
# Finite check: not NaN and not Inf
sea_mask = np.all(np.isfinite(sst_target), dim='time')

# Baseline period and window extensions
baseline_start_dt = pd.to_datetime(BASELINE_START).date()
baseline_end_dt = pd.to_datetime(BASELINE_END).date()
# Needed dates for baseline pools: [baseline_start - 5, baseline_end + 5]
pool_start_dt = pd.to_datetime(baseline_start_dt - datetime.timedelta(days=5))
pool_end_dt = pd.to_datetime(baseline_end_dt + datetime.timedelta(days=5))
ds_pool = ds_reg.sel(time=slice(pool_start_dt, pool_end_dt))
sst_pool = ds_pool['analysed_sst'].astype(np.float64)

# Prepare DOY pools
all_dates = pd.to_datetime(ds_pool.time.values)
doy_to_dates = {}
for dt in all_dates:
    d = get_doy_fixed(dt.date())
    if d not in doy_to_dates:
        doy_to_dates[d] = []
    doy_to_dates[d].append(dt)

#- Map every date to a day of year from 1 to 366
#- For each day of year d other than 60, the pool is every SST value whose date lies within ±5 calendar days of a baseline date whose day of year is d.
baseline_dates = pd.date_range(baseline_start_dt, baseline_end_dt)
doy_baseline_dates = {}
for dt in baseline_dates:
    d = get_doy_fixed(dt)
    if d not in doy_baseline_dates:
        doy_baseline_dates[d] = []
    doy_baseline_dates[d].append(pd.to_datetime(dt))

# We need to find all dates in the dataset that are within 5 days of any baseline date with DOY d.
dataset_dates = pd.to_datetime(ds_pool.time.values)

doy_pools_indices = {} # DOY -> list of indices in ds_pool.time
for d in range(1, 367):
    if d == 60:
        continue
    
    # Baseline dates with DOY d
    b_dates = doy_baseline_dates.get(d, [])
    
    # Find dates in dataset within 5 days of any b_date
    pool_dates = []
    for b_date in b_dates:
        # Dates in range [b_date - 5, b_date + 5]
        # Since dataset_dates is sorted, we can use searchsorted or just filter
        # For simplicity and correctness:
        mask = (dataset_dates >= b_date - pd.Timedelta(days=5)) & \
               (dataset_dates <= b_date + pd.Timedelta(days=5))
        pool_dates.extend(np.where(mask)[0])
    
    # Remove duplicates
    doy_pools_indices[d] = np.unique(pool_dates)

# Now compute Threshold and Climatology for each sea cell
# Dimensions: (latitude, longitude)
# We only care about sea cells
lats = ds_reg.latitude.values
lons = ds_reg.longitude.values
n_lat = len(lats)
n_lon = len(lons)

thresholds = np.full((367, n_lat, n_lon), np.nan, dtype=np.float64)
climatology = np.full((367, n_lat, n_lon), np.nan, dtype=np.float64)

# Convert SST to numpy for faster access
# sst_pool is (time, lat, lon)
sst_pool_vals = sst_pool.values

for d in range(1, 367):
    if d == 60:
        continue
    
    indices = doy_pools_indices[d]
    if len(indices) == 0:
        continue
    
    # pool_data: (len(indices), n_lat, n_lon)
    pool_data = sst_pool_vals[indices]
    
    # 90th percentile (hazen / Hyndman-Fan type 5)
    # numpy.quantile(..., method='hazen')
    # We need to do this per cell. This is the expensive part.
    # To optimize, we can reshape pool_data to (len(indices), n_lat * n_lon)
    reshaped_pool = pool_data.reshape(len(indices), -1)
    
    # Compute quantiles and means along the time axis (axis 0)
    # NaN-aware quantile and mean
    # np.nanquantile is available. method='hazen' is available in recent numpy.
    q90 = np.nanquantile(reshaped_pool, 0.9, axis=0, method='hazen')
    mean_val = np.nanmean(reshaped_pool, axis=0)
    
    thresholds[d] = q90.reshape(n_lat, n_lon)
    climatology[d] = mean_val.reshape(n_lat, n_lon)

# Handle day 60: mean of days 59 and 61
thresholds[60] = (thresholds[59] + thresholds[61]) / 2
climatology[60] = (climatology[59] + climatology[61]) / 2

# Smoothing: 31-day centred moving mean, wrapping around the year
def smooth_array(arr):
    # arr shape: (367, n_lat, n_lon)
    # arr[0] is unused. Let's work with arr[1:] which is 366
    data = arr[1:] # (366, n_lat, n_lon)
    smoothed = np.full_like(data, np.nan)
    for d in range(366):
        # window: d-15 to d+15 modulo 366
        # indices: (d - 15 + i) % 366 for i in 0..30
        # Wait, centred 31-day: d-15, ..., d, ..., d+15. Total 31.
        # Let's use indexing.
        window_indices = [(d - 15 + i) % 366 for i in range(31)]
        window_data = data[window_indices] # (31, n_lat, n_lon)
        smoothed[d] = np.nanmean(window_data, axis=0)
    return smoothed

thresholds_smooth = smooth_array(thresholds)
climatology_smooth = smooth_array(climatology)

# Now detect MHWs in the target period
# Target SST: (time, lat, lon)
sst_target_vals = sst_target.values
target_dates = pd.to_datetime(ds_target.time.values)
n_target_days = len(target_dates)

# For each day, get the threshold for its DOY
target_doys = [get_doy_fixed(dt.date()) for dt in target_dates]
# target_doys are 1-366. Map to 0-365 for thresholds_smooth.
target_doys_idx = [d - 1 for d in target_doys]

mhw_mask = np.zeros((n_target_days, n_lat, n_lon), dtype=np.uint8)

for i in range(n_lat):
    for j in range(n_lon):
        if not sea_mask[i, j]:
            continue
        
        # Cell SST over target period
        cell_sst = sst_target_vals[:, i, j]
        
        # Thresholds for target days
        cell_thresholds = np.array([thresholds_smooth[d][i, j] for d in target_doys_idx])
        
        # Hot days: SST >= threshold
        hot = cell_sst >= cell_thresholds
        
        # Find runs of at least 5 consecutive hot days
        # Join gaps of 1-2 non-hot days
        # We can use a simple loop or group-by
        is_mhw = np.zeros(n_target_days, dtype=bool)
        
        # First pass: find runs of 5+
        # We'll use a simple algorithm:
        # 1. Find all hot runs
        # 2. If run length >= 5, mark as MHW
        # 3. Join MHW runs separated by 1 or 2 non-hot days
        
        # Step 1 & 2
        runs = []
        start = None
        for t in range(n_target_days):
            if hot[t]:
                if start is None:
                    start = t
            else:
                if start is not None:
                    if t - start >= 5:
                        runs.append((start, t - 1))
                    start = None
        if start is not None:
            if n_target_days - start >= 5:
                runs.append((start, n_target_days - 1))
        
        # Step 3: Join gaps of 1 or 2 non-hot days
        if not runs:
            continue
            
        # Merge overlapping or close runs
        merged = []
        if runs:
            curr_start, curr_end = runs[0]
            for next_start, next_end in runs[1:]:
                if next_start - curr_end <= 3: # Gap of 1, 2 or 0 days
                    # Wait, "separated by 1 or 2 non-hot days"
                    # If curr_end is t, and next_start is t+2, there is 1 non-hot day (t+1).
                    # If next_start is t+3, there are 2 non-hot days (t+1, t+2).
                    # If next_start is t+1, there are 0 non-hot days.
                    # So gap is next_start - curr_end - 1.
                    # Gap <= 2 means next_start - curr_end <= 3.
                    curr_end = next_end
                else:
                    merged.append((curr_start, curr_end))
                    curr_start, curr_end = next_start, next_end
            merged.append((curr_start, curr_end))
        
        # Mark MHW days in mask
        for start, end in merged:
            is_mhw[start : end + 1] = True
        
        mhw_mask[:, i, j] = is_mhw.astype(np.uint8)

# Regional Events
# a day is active if at least one sea cell is inside a per-cell MHW
active_days = np.any(mhw_mask == 1, axis=(1, 2))

regional_events = []
start = None
for t in range(n_target_days):
    if active_days[t]:
        if start is None:
            start = t
    else:
        if start is not None:
            regional_events.append((target_dates[start], target_dates[t-1]))
            start = None
if start is not None:
    regional_events.append((target_dates[start], target_dates[n_target_days-1]))

# Save mhw_mask.nc
# Use xarray to save
mask_ds = xr.Dataset(
    {"mhw": (("time", "latitude", "longitude"), mhw_mask)},
    coords={
        "time": ds_target.time,
        "latitude": ds_reg.latitude,
        "longitude": ds_reg.longitude,
    }
)
os.makedirs("output", exist_ok=True)
mask_ds.to_netcdf("output/mhw_mask.nc")

# Prepare report
report = {
    "region": REGION,
    "baseline_analysed": {
        "start": BASELINE_START,
        "end": BASELINE_END
    },
    "target_analysed": {
        "start": TARGET_START,
        "end": TARGET_END
    },
    "events": [
        {"onset": e[0].strftime("%Y-%m-%d"), "end": e[1].strftime("%Y-%m-%d")}
        for e in regional_events
    ],
    "complete": True,
    "caveats": ""
}

with open("output/report.json", "w") as f:
    json.dump(report, f)

print("Success")
