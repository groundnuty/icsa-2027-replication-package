
import numpy as np
from datetime import datetime, timedelta
from collections import defaultdict
import xarray as xr
import json
import os

# ========== Load data ==========
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
lat_sel = ds.latitude.values
lon_sel = ds.longitude.values
lat_idx = np.where((lat_sel >= 54.13) & (lat_sel <= 55.33))[0]
lon_idx = np.where((lon_sel >= 14.67) & (lon_sel <= 15.87))[0]

region = {"lat_min": 54.13, "lat_max": 55.33, "lon_min": 14.67, "lon_max": 15.87}

base_start = np.datetime64('1991-12-27')
base_end = np.datetime64('2003-01-05')
t_idx_base = np.where((ds.time.values >= base_start) & (ds.time.values <= base_end))[0]
base_dates_np = ds.time.values[t_idx_base]
base_sst = ds.analysed_sst.isel(time=t_idx_base, latitude=lat_idx, longitude=lon_idx).values.astype(np.float64)

tgt_start = np.datetime64('2008-06-01')
tgt_end = np.datetime64('2008-08-31')
t_idx_tgt = np.where((ds.time.values >= tgt_start) & (ds.time.values <= tgt_end))[0]
tgt_dates_np = ds.time.values[t_idx_tgt]
tgt_sst = ds.analysed_sst.isel(time=t_idx_tgt, latitude=lat_idx, longitude=lon_idx).values.astype(np.float64)

base_dates_py = [datetime.utcfromtimestamp(int(d.astype('datetime64[ns]').astype(np.int64)) / 1e9) for d in base_dates_np]
tgt_dates_py = [datetime.utcfromtimestamp(int(d.astype('datetime64[ns]').astype(np.int64)) / 1e9) for d in tgt_dates_np]

# ========== Sea cells ==========
n_tgt = len(tgt_dates_py)
sea_cells = np.all(~np.isnan(tgt_sst), axis=0)
sea_lat_idx, sea_lon_idx = np.where(sea_cells)

# ========== Day of year mapping ==========
days_before_month = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
def doy_from_date(dt):
    return days_before_month[dt.month - 1] + dt.day

# ========== Build doy -> date indices ==========
baseline_date_indices = [i for i, d in enumerate(base_dates_py) 
                         if datetime(1992,1,1) <= d <= datetime(2002,12,31)]
baseline_doy = {i: doy_from_date(base_dates_py[i]) for i in baseline_date_indices}

date_to_pools = defaultdict(list)
for i in range(len(base_dates_py)):
    t = base_dates_py[i]
    for j in baseline_date_indices:
        b = base_dates_py[j]
        if abs((t - b).days) <= 5:
            d = baseline_doy[j]
            if d != 60:
                date_to_pools[i].append(d)

doy_to_dates = defaultdict(list)
for i, pools in date_to_pools.items():
    for d in pools:
        doy_to_dates[d].append(i)

# ========== Compute threshold and climatology ==========
n_doy = 366
threshold = np.full((n_doy, 60, 60), np.nan)
climatology = np.full((n_doy, 60, 60), np.nan)

for d in range(1, n_doy+1):
    if d == 60:
        continue
    dates_in_pool = doy_to_dates[d]
    if len(dates_in_pool) == 0:
        continue
    pool_vals = base_sst[dates_in_pool, :, :]
    idx = d - 1
    
    for i, (li, lo) in enumerate(zip(sea_lat_idx, sea_lon_idx)):
        vals = pool_vals[:, li, lo]
        valid = ~np.isnan(vals)
        if valid.sum() == 0:
            continue
        threshold[idx, li, lo] = np.quantile(vals[valid], 0.9, method='hazen')
        climatology[idx, li, lo] = np.mean(vals[valid])

# Day 60 = mean of days 59 and 61
threshold[59, :, :] = (threshold[58, :, :] + threshold[60, :, :]) / 2.0
climatology[59, :, :] = (climatology[58, :, :] + climatology[60, :, :]) / 2.0

# ========== Smooth ==========
def smooth_wrap(arr):
    """Smooth 366-element array with unweighted centred 31-day moving mean wrapping around."""
    n = 366
    result = np.zeros(n)
    for i in range(n):
        vals = []
        for j in range(i-15, i+16):
            k = j % n
            if not np.isnan(arr[k]):
                vals.append(arr[k])
        if vals:
            result[i] = np.mean(vals)
        else:
            result[i] = np.nan
    return result

for i, (li, lo) in enumerate(zip(sea_lat_idx, sea_lon_idx)):
    threshold[:, li, lo] = smooth_wrap(threshold[:, li, lo])
    climatology[:, li, lo] = smooth_wrap(climatology[:, li, lo])

print("Threshold/climatology computed and smoothed")

# ========== Per-cell MHW detection ==========
tgt_doys = np.array([doy_from_date(d) for d in tgt_dates_py])

# Hot days: SST >= threshold
hot = np.zeros((n_tgt, 60, 60), dtype=bool)
for i, (li, lo) in enumerate(zip(sea_lat_idx, sea_lon_idx)):
    thresh_cell = threshold[tgt_doys - 1, li, lo]
    hot[:, li, lo] = tgt_sst[:, li, lo] >= thresh_cell

print("Hot days computed")

# Find per-cell MHW runs
def find_mhw_runs(hot_days):
    n = len(hot_days)
    runs = []
    i = 0
    while i < n:
        if hot_days[i]:
            start = i
            while i < n and hot_days[i]:
                i += 1
            end = i - 1
            runs.append([start, end])
        else:
            i += 1
    
    if len(runs) == 0:
        return []
    
    merged = [runs[0].copy()]
    for r in runs[1:]:
        prev = merged[-1]
        gap = r[0] - prev[1] - 1
        if 1 <= gap <= 2:
            merged[-1][1] = r[1]
        else:
            merged.append(r.copy())
    
    mhw_runs = [(s, e) for s, e in merged if (e - s + 1) >= 5]
    return mhw_runs

# Create per-cell MHW mask: shape (n_tgt, 60, 60), 1 where cell is in MHW
mhw_mask = np.zeros((n_tgt, 60, 60), dtype=np.uint8)
per_cell_mhw_cells = []
for i, (li, lo) in enumerate(zip(sea_lat_idx, sea_lon_idx)):
    runs = find_mhw_runs(hot[:, li, lo])
    if runs:
        per_cell_mhw_cells.append((li, lo, runs))
        for s, e in runs:
            mhw_mask[s:e+1, li, lo] = 1

print(f"Cells with MHWs: {len(per_cell_mhw_cells)} out of {len(sea_lat_idx)} sea cells")

# ========== Regional events ==========
active = np.zeros(n_tgt, dtype=bool)
for li, lo, runs in per_cell_mhw_cells:
    for s, e in runs:
        active[s:e+1] = True

events = []
i = 0
while i < n_tgt:
    if active[i]:
        start = i
        while i < n_tgt and active[i]:
            i += 1
        end = i - 1
        events.append((start, end))
    else:
        i += 1

print(f"Regional events: {len(events)}")
event_list = []
for s, e in events:
    onset = tgt_dates_py[s].date().isoformat()
    end = tgt_dates_py[e].date().isoformat()
    print(f"  {onset} to {end}")
    event_list.append({"onset": onset, "end": end})

# ========== Write output files ==========
os.makedirs('output', exist_ok=True)

# Create mhw_mask.nc
# Dimensions: (time, lat, lon) where time is the target days, lat/lon are the region's grid cells
# Use dataset's coordinate values
lat_coords = lat_sel[lat_idx]
lon_coords = lon_sel[lon_idx]
time_coords = tgt_dates_np

mhw_ds = xr.Dataset(
    {
        'mhw': (('time', 'lat', 'lon'), mhw_mask)
    },
    coords={
        'time': time_coords,
        'lat': lat_coords,
        'lon': lon_coords
    }
)

# Check dimension names match what's expected
print("mhw_ds dims:", dict(mhw_ds.sizes))
print("mhw_ds vars:", list(mhw_ds.data_vars))
print("mhw_ds coords:", list(mhw_ds.coords))

mhw_ds.to_netcdf('output/mhw_mask.nc', engine='h5netcdf')
print("Wrote output/mhw_mask.nc")

# Write report.json
report = {
    "region": region,
    "baseline_analysed": {"start": "1991-12-27", "end": "2003-01-05"},
    "target_analysed": {"start": "2008-06-01", "end": "2008-08-31"},
    "events": event_list,
    "complete": True,
    "caveats": ""
}

with open('output/report.json', 'w') as f:
    json.dump(report, f, indent=2)
print("Wrote output/report.json")
print(json.dumps(report, indent=2))
