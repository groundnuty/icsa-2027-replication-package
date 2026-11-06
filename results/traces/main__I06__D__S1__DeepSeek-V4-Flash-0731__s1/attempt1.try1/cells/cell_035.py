
import numpy as np
import xarray as xr
import datetime
import pandas as pd
import json
import os

# ====== 1. Load data ======
baseline_sst = np.load('/work/baseline_sst.npy')  # (4028, 60, 60) float32
target_sst = np.load('/work/target_sst.npy')      # (92, 60, 60) float32
baseline_time_idx = np.load('/work/baseline_time_idx.npy')
target_time_idx = np.load('/work/target_time_idx.npy')
lat_idx = np.load('/work/lat_idx.npy')
lon_idx = np.load('/work/lon_idx.npy')

# Read coordinate values from s2 file
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
lat_vals = ds.latitude.values[lat_idx]
lon_vals = ds.longitude.values[lon_idx]
time_vals = ds.time.values
baseline_dates_arr = time_vals[baseline_time_idx]
target_dates_arr = time_vals[target_time_idx]
ds.close()

# Convert to Python dates
baseline_dates_list = [pd.Timestamp(t).to_pydatetime().date() for t in baseline_dates_arr]
target_dates_list = [pd.Timestamp(t).to_pydatetime().date() for t in target_dates_arr]

print(f"Baseline: {baseline_dates_list[0]} to {baseline_dates_list[-1]} ({len(baseline_dates_list)} days)")
print(f"Target: {target_dates_list[0]} to {target_dates_list[-1]} ({len(target_dates_list)} days)")
print(f"Region: {lat_vals[0]:.4f}-{lat_vals[-1]:.4f} N, {lon_vals[0]:.4f}-{lon_vals[-1]:.4f} E, {len(lat_vals)}x{len(lon_vals)} cells")

# ====== 2. Day of year function ======
def doy_from_date(date):
    m = date.month; d = date.day
    if m == 1: return d
    elif m == 2: return 31 + d
    elif m == 3: return 60 + d
    elif m == 4: return 91 + d
    elif m == 5: return 121 + d
    elif m == 6: return 152 + d
    elif m == 7: return 182 + d
    elif m == 8: return 213 + d
    elif m == 9: return 244 + d
    elif m == 10: return 274 + d
    elif m == 11: return 305 + d
    elif m == 12: return 335 + d
    return -1

# ====== 3. Build pools ======
print("\nBuilding pools...")
date_to_idx = {d: i for i, d in enumerate(baseline_dates_list)}
core_dates = [d for d in baseline_dates_list 
              if datetime.date(1992,1,1) <= d <= datetime.date(2002,12,31)]
core_doy = {d: doy_from_date(d) for d in core_dates}

pools = {}
for doy in range(1, 367):
    if doy == 60:
        continue
    matching_dates = [d for d, dd in core_doy.items() if dd == doy]
    pool_dates = set()
    for t0 in matching_dates:
        for delta in range(-5, 6):
            t = t0 + datetime.timedelta(days=delta)
            if t in date_to_idx:
                pool_dates.add(t)
    pools[doy] = sorted(pool_dates)

print(f"Pools built for {len(pools)} day-of-year values")

# ====== 4. Compute thresholds and climatologies ======
print("Computing thresholds and climatologies...")
baseline_sst64 = baseline_sst.astype(np.float64)
n_lat, n_lon = 60, 60

thresholds = np.full((366, n_lat, n_lon), np.nan)
climatologies = np.full((366, n_lat, n_lon), np.nan)

for doy in range(1, 367):
    if doy == 60:
        continue
    pool_dates = pools[doy]
    pool_indices = [date_to_idx[d] for d in pool_dates]
    pool_sst = baseline_sst64[pool_indices, :, :]
    
    thresholds[doy-1] = np.nanquantile(pool_sst, 0.9, axis=0, method='hazen')
    climatologies[doy-1] = np.nanmean(pool_sst, axis=0)

# Set day 60 (index 59) as mean of days 59 and 61
thresholds[59] = (thresholds[58] + thresholds[60]) / 2
climatologies[59] = (climatologies[58] + climatologies[60]) / 2

print("Thresholds and climatologies computed.")

# ====== 5. Smooth ======
print("Smoothing...")
def smooth_wrap(arr):
    n = arr.shape[0]
    result = np.zeros_like(arr)
    padded = np.concatenate([arr[-15:], arr, arr[:15]], axis=0)
    for d in range(n):
        result[d] = np.mean(padded[d:d+31], axis=0)
    return result

thresholds_smooth = smooth_wrap(thresholds)
climatologies_smooth = smooth_wrap(climatologies)

print("Smoothing done.")

# ====== 6. Target analysis ======
print("\nTarget analysis...")
target_sst64 = target_sst.astype(np.float64)
sea_cells = ~np.isnan(target_sst64).any(axis=0)
print(f"Sea cells: {sea_cells.sum()} out of {sea_cells.size}")

target_doy = [doy_from_date(d) for d in target_dates_list]

# Get thresholds for target days
n_target = len(target_dates_list)
target_thresholds = np.zeros((n_target, n_lat, n_lon), dtype=np.float64)
for t, doy in enumerate(target_doy):
    target_thresholds[t] = thresholds_smooth[doy-1]

# Hot days: SST >= threshold
hot = target_sst64 >= target_thresholds

# Per-cell MHW detection
mhw_mask = np.zeros((n_target, n_lat, n_lon), dtype=np.uint8)

for i in range(n_lat):
    for j in range(n_lon):
        if not sea_cells[i, j]:
            continue
        
        hot_series = hot[:, i, j].astype(int)
        
        # Find runs of consecutive hot days
        runs = []
        start = None
        for t in range(n_target):
            if hot_series[t]:
                if start is None:
                    start = t
            else:
                if start is not None:
                    runs.append((start, t-1))
                    start = None
        if start is not None:
            runs.append((start, n_target-1))
        
        # Filter for >= 5 consecutive days
        mhw_runs = [(s, e) for s, e in runs if e - s + 1 >= 5]
        
        # Join runs separated by 1-2 non-hot days
        if mhw_runs:
            joined = [mhw_runs[0]]
            for s, e in mhw_runs[1:]:
                last_s, last_e = joined[-1]
                gap = s - last_e - 1
                if gap <= 2:
                    joined[-1] = (last_s, e)
                else:
                    joined.append((s, e))
            
            for s, e in joined:
                mhw_mask[s:e+1, i, j] = 1

print(f"MHW cell-days: {mhw_mask.sum()}")

# ====== 7. Regional events ======
active = mhw_mask.any(axis=(1, 2))
print(f"Active days: {active.sum()}")

events = []
start = None
for t in range(n_target):
    if active[t]:
        if start is None:
            start = t
    else:
        if start is not None:
            events.append((start, t-1))
            start = None
if start is not None:
    events.append((start, n_target-1))

print(f"Regional events: {len(events)}")
for s, e in events:
    print(f"  {target_dates_list[s]} to {target_dates_list[e]} ({e-s+1} days)")

# ====== 8. Write output ======
print("\nWriting output files...")
os.makedirs('output', exist_ok=True)

# Write mhw_mask.nc
ds_out = xr.Dataset(
    {'mhw': (('time', 'lat', 'lon'), mhw_mask)},
    coords={
        'time': target_dates_arr,
        'lat': lat_vals,
        'lon': lon_vals
    }
)
ds_out.to_netcdf('output/mhw_mask.nc', engine='h5netcdf')

# Write report.json
report = {
    'region': {'lat_min': 54.45, 'lat_max': 55.65, 'lon_min': 16.05, 'lon_max': 17.25},
    'baseline_analysed': {'start': str(baseline_dates_list[0]), 'end': str(baseline_dates_list[-1])},
    'target_analysed': {'start': str(target_dates_list[0]), 'end': str(target_dates_list[-1])},
    'events': [{'onset': str(target_dates_list[s]), 'end': str(target_dates_list[e])} for s, e in events],
    'complete': True,
    'caveats': ''
}

with open('output/report.json', 'w') as f:
    json.dump(report, f, indent=2)

print("\nDone! Output files written:")
print(f"  output/mhw_mask.nc")
print(f"  output/report.json")

# Print report summary
print(f"\nReport:")
print(f"  Region: lat {54.45}-{55.65}, lon {16.05}-{17.25}")
print(f"  Baseline: {baseline_dates_list[0]} to {baseline_dates_list[-1]}")
print(f"  Target: {target_dates_list[0]} to {target_dates_list[-1]}")
print(f"  Events: {len(events)}")
for s, e in events:
    print(f"    {target_dates_list[s]} to {target_dates_list[e]}")
