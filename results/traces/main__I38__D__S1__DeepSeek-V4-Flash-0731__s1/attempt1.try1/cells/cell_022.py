
import numpy as np
from datetime import date, timedelta
import xarray as xr
import json
import os

# ============================================================
# Day-of-year mapping (1-366)
# ============================================================
month_days = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

def day_of_year(month, day):
    doy = day
    for m in range(month - 1):
        doy += month_days[m]
    return doy

def date_to_doy(d):
    return day_of_year(d.month, d.day)

# ============================================================
# Load data
# ============================================================
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')

lat = ds.latitude.values
lon = ds.longitude.values
lat_idx = np.where((lat >= 60.49) & (lat <= 61.69))[0]
lon_idx = np.where((lon >= 17.25) & (lon <= 18.45))[0]
lat_region = lat[lat_idx].astype(float)
lon_region = lon[lon_idx].astype(float)

# Baseline: 1991-12-27 to 2003-01-05
time = ds.time.values
baseline_start_idx = np.where(time == np.datetime64('1991-12-27'))[0][0]
baseline_end_idx = np.where(time == np.datetime64('2003-01-05'))[0][0]

# Target: 2003-06-01 to 2003-08-31
target_start_idx = np.where(time == np.datetime64('2003-06-01'))[0][0]
target_end_idx = np.where(time == np.datetime64('2003-08-31'))[0][0]

# Read data
baseline_data = ds.analysed_sst[baseline_start_idx:baseline_end_idx+1, 
                                lat_idx[0]:lat_idx[-1]+1, 
                                lon_idx[0]:lon_idx[-1]+1].values.astype(np.float64)
target_data = ds.analysed_sst[target_start_idx:target_end_idx+1, 
                              lat_idx[0]:lat_idx[-1]+1, 
                              lon_idx[0]:lon_idx[-1]+1].values.astype(np.float64)

n_baseline_days = baseline_data.shape[0]
n_target_days = target_data.shape[0]
n_lat = baseline_data.shape[1]
n_lon = baseline_data.shape[2]

print(f"Baseline data shape: {baseline_data.shape}")
print(f"Target data shape: {target_data.shape}")

# Generate dates
baseline_dates = []
d = date(1991, 12, 27)
end_d = date(2003, 1, 5)
while d <= end_d:
    baseline_dates.append(d)
    d += timedelta(days=1)
assert len(baseline_dates) == n_baseline_days

target_dates = []
d = date(2003, 6, 1)
end_d = date(2003, 8, 31)
while d <= end_d:
    target_dates.append(d)
    d += timedelta(days=1)
assert len(target_dates) == n_target_days

print(f"Baseline: {baseline_dates[0]} to {baseline_dates[-1]}, {len(baseline_dates)} days")
print(f"Target: {target_dates[0]} to {target_dates[-1]}, {len(target_dates)} days")

# ============================================================
# Identify sea cells: finite on every day of target period
# ============================================================
sea_cells = np.all(np.isfinite(target_data), axis=0)
print(f"Sea cells: {sea_cells.sum()} out of {sea_cells.size}")

# ============================================================
# Build pool dates for each day-of-year
# ============================================================
baseline_years = range(1992, 2003)
baseline_date_index = {d: i for i, d in enumerate(baseline_dates)}

# pool_date_indices_by_doy[doy] for doy in 1..366
pool_date_indices_by_doy = {}

for doy in range(1, 367):
    if doy == 60:
        continue
    pool_indices = set()
    for y in baseline_years:
        # Determine month and day from doy
        month = 1
        remaining = doy
        while remaining > month_days[month-1]:
            remaining -= month_days[month-1]
            month += 1
        day = remaining
        
        # Skip Feb 29 in non-leap years
        try:
            b = date(y, month, day)
        except ValueError:
            continue
        
        for offset in range(-5, 6):
            t = b + timedelta(days=offset)
            if t in baseline_date_index:
                pool_indices.add(baseline_date_index[t])
    
    pool_date_indices_by_doy[doy] = sorted(pool_indices)

print(f"Pools built for {len(pool_date_indices_by_doy)} day-of-years")

# ============================================================
# Compute thresholds and climatology
# Index 0 corresponds to day-of-year 1, index 365 to day 366
# ============================================================
thresholds = np.full((366, n_lat, n_lon), np.nan)
climatology = np.full((366, n_lat, n_lon), np.nan)

for doy in range(1, 367):
    if doy == 60:
        continue
    pool_indices = pool_date_indices_by_doy[doy]
    if not pool_indices:
        continue
    pool_data = baseline_data[pool_indices, :, :]
    
    idx = doy - 1
    
    for li in range(n_lat):
        for loi in range(n_lon):
            if not sea_cells[li, loi]:
                continue
            values = pool_data[:, li, loi]
            valid = np.isfinite(values)
            if valid.sum() == 0:
                continue
            vals = values[valid]
            thresholds[idx, li, loi] = np.quantile(vals, 0.9, method='hazen')
            climatology[idx, li, loi] = np.mean(vals)

print("Thresholds and climatology computed")

# Set day 60 (index 59) to mean of days 59 (index 58) and 61 (index 60)
thresholds[59] = (thresholds[58] + thresholds[60]) / 2.0
climatology[59] = (climatology[58] + climatology[60]) / 2.0

print("Day 60 set to mean of days 59 and 61")

# ============================================================
# Smooth with 31-day moving average wrapping around 366 days
# ============================================================
def smooth_wrap(arr):
    """Smooth a 366-element array with 31-day moving avg wrapping around."""
    result = np.zeros_like(arr)
    for d in range(366):
        total = 0.0
        count = 0
        for offset in range(-15, 16):
            idx = (d + offset) % 366
            if np.isfinite(arr[idx]):
                total += arr[idx]
                count += 1
        if count > 0:
            result[d] = total / count
        else:
            result[d] = np.nan
    return result

# Apply smoothing per cell
for li in range(n_lat):
    for loi in range(n_lon):
        if not sea_cells[li, loi]:
            continue
        thresholds[:, li, loi] = smooth_wrap(thresholds[:, li, loi])
        climatology[:, li, loi] = smooth_wrap(climatology[:, li, loi])

print("Smoothing done")

# ============================================================
# Detect per-cell MHWs in target period
# ============================================================
# Day-of-year for each target date
target_doy = np.array([date_to_doy(d) for d in target_dates])

# Hot day check
hot = np.zeros((n_lat, n_lon, n_target_days), dtype=bool)
for t in range(n_target_days):
    doy = target_doy[t]
    idx = doy - 1
    hot[:, :, t] = (target_data[t, :, :] >= thresholds[idx, :, :]) & sea_cells

print(f"Hot cell-days: {hot.sum()} out of {sea_cells.sum() * n_target_days}")

# Find per-cell MHWs
mhw_mask = np.zeros((n_target_days, n_lat, n_lon), dtype=bool)

for li in range(n_lat):
    for loi in range(n_lon):
        if not sea_cells[li, loi]:
            continue
        
        hot_days = hot[li, loi, :]
        
        # Find runs of consecutive hot days
        runs = []
        in_run = False
        run_start = 0
        for t in range(n_target_days):
            if hot_days[t]:
                if not in_run:
                    run_start = t
                    in_run = True
            else:
                if in_run:
                    runs.append((run_start, t - 1))
                    in_run = False
        if in_run:
            runs.append((run_start, n_target_days - 1))
        
        if not runs:
            continue
        
        # Keep runs of length >= 5
        mhw_runs = [(s, e) for s, e in runs if (e - s + 1) >= 5]
        
        if not mhw_runs:
            continue
        
        # Join runs separated by 1 or 2 non-hot days
        joined_runs = []
        current = [mhw_runs[0][0], mhw_runs[0][1]]
        for i in range(1, len(mhw_runs)):
            prev_end = current[1]
            next_start = mhw_runs[i][0]
            gap = next_start - prev_end - 1
            if gap <= 2:
                current[1] = mhw_runs[i][1]
            else:
                joined_runs.append(tuple(current))
                current = [mhw_runs[i][0], mhw_runs[i][1]]
        joined_runs.append(tuple(current))
        
        # Mark days in per-cell MHWs
        for s, e in joined_runs:
            mhw_mask[s:e+1, li, loi] = True

print(f"Per-cell MHW cell-days: {mhw_mask.sum()}")

# ============================================================
# Regional events
# ============================================================
active = np.any(mhw_mask, axis=(1, 2))
print(f"Active days: {active.sum()}")

events = []
in_event = False
event_start = 0
for t in range(n_target_days):
    if active[t]:
        if not in_event:
            event_start = t
            in_event = True
    else:
        if in_event:
            events.append((event_start, t - 1))
            in_event = False
if in_event:
    events.append((event_start, n_target_days - 1))

print(f"Regional events: {len(events)}")
for s, e in events:
    print(f"  {target_dates[s]} to {target_dates[e]}")

# ============================================================
# Write output files
# ============================================================
os.makedirs('output', exist_ok=True)

# mhw_mask.nc
target_time = time[target_start_idx:target_end_idx+1]

mhw_da = xr.DataArray(
    mhw_mask.astype(np.uint8),
    dims=['time', 'lat', 'lon'],
    coords={
        'time': target_time,
        'lat': lat_region,
        'lon': lon_region
    },
    name='mhw'
)

mhw_ds = mhw_da.to_dataset()
mhw_ds.to_netcdf('output/mhw_mask.nc', engine='h5netcdf')
print("Wrote output/mhw_mask.nc")

# report.json
report = {
    'region': {
        'lat_min': 60.49,
        'lat_max': 61.69,
        'lon_min': 17.25,
        'lon_max': 18.45
    },
    'baseline_analysed': {
        'start': '1991-12-27',
        'end': '2003-01-05'
    },
    'target_analysed': {
        'start': '2003-06-01',
        'end': '2003-08-31'
    },
    'events': [
        {'onset': target_dates[s].strftime('%Y-%m-%d'),
         'end': target_dates[e].strftime('%Y-%m-%d')}
        for s, e in events
    ],
    'complete': True,
    'caveats': ''
}

with open('output/report.json', 'w') as f:
    json.dump(report, f, indent=2)

print("Wrote output/report.json")
print(json.dumps(report, indent=2))

# Verify output
print("\nVerification:")
print("mhw_mask shape:", mhw_mask.shape)
print("mhw_mask dtype:", mhw_mask.dtype)
print("mhw_mask sum:", mhw_mask.sum())
print("mhw_mask unique values:", np.unique(mhw_mask))
