
import numpy as np
import pandas as pd
import xarray as xr
import os
import json

# Create output directory
os.makedirs('output', exist_ok=True)

# ============ 1. Load data ============
print("Loading data...")
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')

# Region: lat 58.69-59.89, lon 18.69-19.89
# From the dataset: lat indices 260-319, lon indices 485-544
base_data = ds['analysed_sst'].isel(time=slice(3647, 7675), latitude=slice(260, 320), longitude=slice(485, 545)).load()
target_data = ds['analysed_sst'].isel(time=slice(12935, 13027), latitude=slice(260, 320), longitude=slice(485, 545)).load()

base_times = base_data.time.values
target_times = target_data.time.values

# Convert to float64
base_data64 = base_data.values.astype(np.float64)
target_data64 = target_data.values.astype(np.float64)

print(f"Base data: {base_data64.shape}, Target data: {target_data64.shape}")
print(f"Base time range: {pd.Timestamp(base_times[0]).date()} to {pd.Timestamp(base_times[-1]).date()}")
print(f"Target time range: {pd.Timestamp(target_times[0]).date()} to {pd.Timestamp(target_times[-1]).date()}")

# ============ 2. Day of year mapping ============
def doy_from_datetime64(t):
    dt = pd.Timestamp(t).to_pydatetime()
    year = dt.year
    month = dt.month
    day = dt.day
    is_leap = (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0))
    days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    if is_leap:
        days_in_month[1] = 29
    std_doy = sum(days_in_month[:month-1]) + day
    if not is_leap and month >= 3:
        return std_doy + 1
    else:
        return std_doy

base_doy = np.array([doy_from_datetime64(t) for t in base_times])
target_doy = np.array([doy_from_datetime64(t) for t in target_times])

# ============ 3. Identify sea cells ============
sea_cells = np.all(np.isfinite(target_data64), axis=0)  # (60, 60)
print(f"Sea cells: {sea_cells.sum()} out of {60*60}")

# ============ 4. Compute thresholds and climatology ============
print("Computing thresholds and climatology...")
in_baseline = (base_times >= np.datetime64('1992-01-01')) & (base_times <= np.datetime64('2002-12-31'))

# Build pool masks for each DOY
pool_masks = {}
for d in range(1, 367):
    if d == 60:
        continue
    baseline_indices = np.where(in_baseline & (base_doy == d))[0]
    pool_mask = np.zeros(len(base_times), dtype=bool)
    for bi in baseline_indices:
        lo = max(0, bi - 5)
        hi = min(len(base_times) - 1, bi + 5)
        pool_mask[lo:hi+1] = True
    pool_masks[d] = pool_mask

# Compute raw thresholds and climatology
thresholds = np.zeros((366, 60, 60), dtype=np.float64)
climatology = np.zeros((366, 60, 60), dtype=np.float64)

for d in range(1, 367):
    if d == 60:
        continue
    mask = pool_masks[d]
    pool = base_data64[mask, :, :]
    with np.errstate(all='ignore'):
        p90 = np.nanpercentile(pool, 90, axis=0, method='hazen')
        mean_val = np.nanmean(pool, axis=0)
    thresholds[d-1, :, :] = p90
    climatology[d-1, :, :] = mean_val

# Day 60: mean of days 59 and 61
thresholds[59, :, :] = (thresholds[58, :, :] + thresholds[60, :, :]) / 2.0
climatology[59, :, :] = (climatology[58, :, :] + climatology[60, :, :]) / 2.0

print("Smoothing...")
# Smooth: 31-day centered moving mean wrapping around the year
def smooth_wrap(arr):
    result = np.zeros_like(arr)
    for d in range(366):
        indices = [(d - 15 + i) % 366 for i in range(31)]
        result[d] = np.mean(arr[indices], axis=0)
    return result

thresholds_smooth = smooth_wrap(thresholds)
climatology_smooth = smooth_wrap(climatology)

print("Thresholds/climatology computed and smoothed")

# ============ 5. Per-cell MHWs ============
print("Identifying per-cell MHWs...")
threshold_for_target = thresholds_smooth[target_doy - 1, :, :]  # (92, 60, 60)

hot = target_data64 >= threshold_for_target
hot = hot & np.broadcast_to(sea_cells, hot.shape)
hot = hot & np.isfinite(target_data64)

n_time, n_lat, n_lon = hot.shape
per_cell_mhw = np.zeros_like(hot, dtype=bool)

sea_indices = np.where(sea_cells)
for idx in range(len(sea_indices[0])):
    i, j = sea_indices[0][idx], sea_indices[1][idx]
    hot_cell = hot[:, i, j]
    
    # Find runs of consecutive hot days
    runs = []
    start = None
    for t in range(n_time):
        if hot_cell[t]:
            if start is None:
                start = t
        else:
            if start is not None:
                runs.append((start, t - 1))
                start = None
    if start is not None:
        runs.append((start, n_time - 1))
    
    # Keep runs with length >= 5
    mhw_runs = [(s, e) for s, e in runs if e - s + 1 >= 5]
    
    if not mhw_runs:
        continue
    
    # Join MHWs separated by 1-2 non-hot days
    merged = [mhw_runs[0]]
    for s, e in mhw_runs[1:]:
        prev_s, prev_e = merged[-1]
        gap = s - prev_e - 1
        if gap <= 2:
            merged[-1] = (prev_s, e)
        else:
            merged.append((s, e))
    
    for s, e in merged:
        per_cell_mhw[s:e+1, i, j] = True

print(f"Per-cell MHW days: {per_cell_mhw.sum()}")

# ============ 6. Regional events ============
active_days = np.any(per_cell_mhw, axis=(1, 2))  # (92,)

events = []
start = None
for t in range(n_time):
    if active_days[t]:
        if start is None:
            start = t
    else:
        if start is not None:
            events.append((start, t - 1))
            start = None
if start is not None:
    events.append((start, n_time - 1))

event_list = []
for s, e in events:
    onset = pd.Timestamp(target_times[s]).strftime('%Y-%m-%d')
    end = pd.Timestamp(target_times[e]).strftime('%Y-%m-%d')
    event_list.append({"onset": onset, "end": end})

print(f"Regional events: {event_list}")
print(f"Active days: {active_days.sum()}")

# ============ 7. Write output ============
print("Writing output files...")

# mhw_mask.nc
mhw = per_cell_mhw.astype(np.uint8)  # (92, 60, 60)

# Get coordinate values from the dataset
lat_region = ds.latitude.values[260:320]
lon_region = ds.longitude.values[485:545]
time_target = ds.time.values[12935:13027]

ds_out = xr.Dataset(
    {
        'mhw': (('time', 'lat', 'lon'), mhw)
    },
    coords={
        'time': time_target,
        'lat': lat_region,
        'lon': lon_region,
    }
)
ds_out.to_netcdf('output/mhw_mask.nc', engine='h5netcdf')
print("Wrote output/mhw_mask.nc")

# report.json
report = {
    "region": {
        "lat_min": 58.69,
        "lat_max": 59.89,
        "lon_min": 18.69,
        "lon_max": 19.89
    },
    "baseline_analysed": {
        "start": "1991-12-27",
        "end": "2003-01-05"
    },
    "target_analysed": {
        "start": "2017-06-01",
        "end": "2017-08-31"
    },
    "events": event_list,
    "complete": True,
    "caveats": ""
}
with open('output/report.json', 'w') as f:
    json.dump(report, f, indent=2)
print("Wrote output/report.json")

print("\n=== SUMMARY ===")
print(f"Region: lat {58.69}-{59.89}, lon {18.69}-{19.89}")
print(f"Baseline analysed: 1991-12-27 to 2003-01-05")
print(f"Target analysed: 2017-06-01 to 2017-08-31")
print(f"Sea cells: {sea_cells.sum()}")
print(f"Events: {event_list}")
print(f"Complete: True")
