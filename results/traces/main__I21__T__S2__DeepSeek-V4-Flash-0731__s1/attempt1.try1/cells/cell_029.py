
import numpy as np
import xarray as xr
import pandas as pd
from datetime import datetime, timedelta
import json
import os

# ============================================================
# 1. Load data
# ============================================================

# Load the previously saved intermediate data
baseline_data = xr.open_dataset('baseline_data.nc')
target_data = xr.open_dataset('target_data.nc')

baseline_sst = baseline_data.analysed_sst.values  # (4028, 60, 60) - 1991-12-27 to 2003-01-05
baseline_time = baseline_data.time.values
target_sst = target_data.analysed_sst.values  # (92, 60, 60) - 2021-06-01 to 2021-08-31
target_time = target_data.time.values

# Original dataset coordinates for the region
# Get the original coordinate values
orig_lat = baseline_data.latitude.values
orig_lon = baseline_data.longitude.values
orig_time = target_data.time.values

print(f"Baseline: {pd.Timestamp(baseline_time[0])} to {pd.Timestamp(baseline_time[-1])}, shape={baseline_sst.shape}")
print(f"Target: {pd.Timestamp(target_time[0])} to {pd.Timestamp(target_time[-1])}, shape={target_sst.shape}")
print(f"Lat range: {orig_lat[0]} to {orig_lat[-1]}, count={len(orig_lat)}")
print(f"Lon range: {orig_lon[0]} to {orig_lon[-1]}, count={len(orig_lon)}")

# ============================================================
# 2. Day-of-year mapping
# ============================================================

def day_of_year(dt):
    """Map a date to day of year 1-366 by month and day."""
    month = dt.month
    day = dt.day
    cum_days = [0, 0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum_days[month] + day

baseline_dates = [pd.Timestamp(t).to_pydatetime() for t in baseline_time]
target_dates = [pd.Timestamp(t).to_pydatetime() for t in target_time]
target_doy = [day_of_year(dt) for dt in target_dates]

# ============================================================
# 3. Sea cells: finite SST on every target day
# ============================================================

n_lat = target_sst.shape[1]
n_lon = target_sst.shape[2]

sea_cells = np.zeros((n_lat, n_lon), dtype=bool)
for la in range(n_lat):
    for lo in range(n_lon):
        if np.all(np.isfinite(target_sst[:, la, lo])):
            sea_cells[la, lo] = True

sea_indices = np.argwhere(sea_cells)
print(f"Sea cells: {np.sum(sea_cells)} out of {n_lat * n_lon}")

# ============================================================
# 4. Build day-of-year pools and compute thresholds/climatology
# ============================================================

# Build day-of-year to pool indices mapping
base_start = datetime(1992, 1, 1)
base_end = datetime(2002, 12, 31)

doy_to_indices = {}
for d in range(1, 367):
    if d == 60:
        continue
    pool_indices = set()
    for i, dt in enumerate(baseline_dates):
        if base_start <= dt <= base_end and day_of_year(dt) == d:
            for j in range(max(0, i-5), min(len(baseline_dates), i+6)):
                pool_indices.add(j)
    doy_to_indices[d] = sorted(pool_indices)

# Compute threshold and climatology per sea cell per day-of-year (float64)
baseline_sst_f64 = baseline_sst.astype(np.float64)
target_sst_f64 = target_sst.astype(np.float64)

threshold_raw = np.full((366, n_lat, n_lon), np.nan, dtype=np.float64)
climatology_raw = np.full((366, n_lat, n_lon), np.nan, dtype=np.float64)

print("Computing thresholds and climatology...")

for d in range(1, 367):
    if d == 60:
        continue
    idx = doy_to_indices[d]
    pool_values = baseline_sst_f64[idx, :, :]  # (n_pool, n_lat, n_lon)
    
    for la, lo in sea_indices:
        vals = pool_values[:, la, lo]
        vals_clean = vals[np.isfinite(vals)]
        if len(vals_clean) == 0:
            continue
        threshold_raw[d-1, la, lo] = np.percentile(vals_clean, 90, method='hazen')
        climatology_raw[d-1, la, lo] = np.mean(vals_clean)

print("Setting day 60...")
# Set day 60 (index 59) to mean of days 59 (index 58) and 61 (index 60)
for la, lo in sea_indices:
    threshold_raw[59, la, lo] = (threshold_raw[58, la, lo] + threshold_raw[60, la, lo]) / 2.0
    climatology_raw[59, la, lo] = (climatology_raw[58, la, lo] + climatology_raw[60, la, lo]) / 2.0

# Apply 31-day centered moving mean with wrap-around
print("Smoothing...")
threshold_smooth = np.full_like(threshold_raw, np.nan)
climatology_smooth = np.full_like(climatology_raw, np.nan)

for d in range(1, 367):
    d_idx = d - 1
    window = [(d + k - 1) % 366 for k in range(-15, 16)]
    for la, lo in sea_indices:
        vals_t = threshold_raw[window, la, lo]
        vals_c = climatology_raw[window, la, lo]
        threshold_smooth[d_idx, la, lo] = np.mean(vals_t[np.isfinite(vals_t)])
        climatology_smooth[d_idx, la, lo] = np.mean(vals_c[np.isfinite(vals_c)])

print("Done smoothing.")

# ============================================================
# 5. Detect per-cell MHWs over target period
# ============================================================

print("Detecting hot days...")
hot = np.zeros((len(target_time), n_lat, n_lon), dtype=bool)

for t in range(len(target_time)):
    doy = target_doy[t]
    doy_idx = doy - 1
    for la in range(n_lat):
        for lo in range(n_lon):
            if sea_cells[la, lo]:
                sst_val = target_sst_f64[t, la, lo]
                if np.isfinite(sst_val):
                    thr = threshold_smooth[doy_idx, la, lo]
                    if sst_val >= thr:
                        hot[t, la, lo] = True

print("Detecting per-cell MHWs...")
mhw_mask = np.zeros((len(target_time), n_lat, n_lon), dtype=np.uint8)

for la, lo in sea_indices:
    hot_series = hot[:, la, lo]
    
    # Find all runs of consecutive hot days
    all_runs = []
    i = 0
    while i < len(target_time):
        if hot_series[i]:
            start = i
            while i < len(target_time) and hot_series[i]:
                i += 1
            all_runs.append((start, i-1))
        else:
            i += 1
    
    # MHWs are runs of >= 5 hot days
    mhws = [(s, e) for s, e in all_runs if (e - s + 1) >= 5]
    
    # Join MHWs separated by 1-2 non-hot days
    if len(mhws) <= 1:
        final_mhws = mhws
    else:
        final_mhws = [mhws[0]]
        for m in mhws[1:]:
            prev_end = final_mhws[-1][1]
            gap = m[0] - prev_end - 1
            if gap <= 2:
                final_mhws[-1] = (final_mhws[-1][0], m[1])
            else:
                final_mhws.append(m)
    
    # Mark the mask
    for s, e in final_mhws:
        mhw_mask[s:e+1, la, lo] = 1

print(f"Total MHW day-cell entries: {np.sum(mhw_mask)}")

# ============================================================
# 6. Detect regional events
# ============================================================

print("Detecting regional events...")
active = np.any(mhw_mask > 0, axis=(1, 2))

events = []
i = 0
while i < len(target_time):
    if active[i]:
        start = i
        while i < len(target_time) and active[i]:
            i += 1
        end = i - 1
        events.append((start, end))
    else:
        i += 1

print(f"Regional events: {len(events)}")
event_list = []
for s, e in events:
    onset = target_dates[s].strftime('%Y-%m-%d')
    end = target_dates[e].strftime('%Y-%m-%d')
    event_list.append({"onset": onset, "end": end})
    print(f"  {onset} to {end} ({e-s+1} days)")

# ============================================================
# 7. Write output files
# ============================================================

os.makedirs('output', exist_ok=True)

# Write mhw_mask.nc
print("Writing mhw_mask.nc...")

# Create the output dataset
out_ds = xr.Dataset(
    {
        'mhw': (('time', 'lat', 'lon'), mhw_mask)
    },
    coords={
        'time': orig_time,
        'lat': orig_lat,
        'lon': orig_lon
    }
)
out_ds['mhw'].attrs['units'] = '1'
out_ds['mhw'].attrs['long_name'] = 'Marine heatwave mask'
out_ds['mhw'].attrs['description'] = '1 if cell is inside a per-cell MHW on that day, 0 otherwise'

out_ds.to_netcdf('output/mhw_mask.nc')
print("Written output/mhw_mask.nc")

# Write report.json
report = {
    "region": {
        "lat_min": 57.33,
        "lat_max": 58.53,
        "lon_min": 9.03,
        "lon_max": 10.23
    },
    "baseline_analysed": {
        "start": "1991-12-27",
        "end": "2003-01-05"
    },
    "target_analysed": {
        "start": "2021-06-01",
        "end": "2021-08-31"
    },
    "events": event_list,
    "complete": True,
    "caveats": ""
}

with open('output/report.json', 'w') as f:
    json.dump(report, f, indent=2)

print("Written output/report.json")
print("\nDone!")
print(f"Report: {json.dumps(report, indent=2)}")
