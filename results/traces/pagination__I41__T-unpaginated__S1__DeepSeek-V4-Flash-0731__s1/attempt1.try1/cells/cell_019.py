
import fsspec
import xarray as xr
import numpy as np
import datetime
import time
import os
import json
import warnings

fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'

# ========================
# Setup and definitions
# ========================

# Region
lat_min, lat_max = 61.57, 62.77
lon_min, lon_max = 20.17, 21.37

# Get region indices and coordinates
f = fs.open(f'{base}/sst_20210601.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')
lat_all = ds.latitude.values
lon_all = ds.longitude.values
lat_idx = np.where((lat_all >= lat_min) & (lat_all <= lat_max))[0]
lon_idx = np.where((lon_all >= lon_min) & (lon_all <= lon_max))[0]
lat_min_i, lat_max_i = lat_idx.min(), lat_idx.max()
lon_min_i, lon_max_i = lon_idx.min(), lon_idx.max()
region_lat = lat_all[lat_min_i:lat_max_i+1]
region_lon = lon_all[lon_min_i:lon_max_i+1]
nlat, nlon = len(region_lat), len(region_lon)
ds.close()

def day_of_year(d):
    """Day of year 1-366. Jan 1=1, Feb 28=59, Feb 29=60, Mar 1=61, Dec 31=366."""
    doy = (d - datetime.date(d.year, 1, 1)).days + 1
    is_leap = (d.year % 4 == 0 and (d.year % 100 != 0 or d.year % 400 == 0))
    if not is_leap and d.month >= 3:
        doy += 1
    return doy

# ========================
# Load baseline data
# ========================
baseline_start = datetime.date(1991, 12, 27)
baseline_end = datetime.date(2003, 1, 5)

all_baseline_dates = []
d = baseline_start
while d <= baseline_end:
    all_baseline_dates.append(d)
    d += datetime.timedelta(days=1)
n_baseline = len(all_baseline_dates)

print(f"Loading {n_baseline} baseline files...", flush=True)
t0 = time.time()

baseline_data = np.zeros((n_baseline, nlat, nlon), dtype=np.float32)
baseline_doy = np.zeros(n_baseline, dtype=np.int32)

for i, date in enumerate(all_baseline_dates):
    fpath = f'{base}/sst_{date.strftime("%Y%m%d")}.nc'
    f = fs.open(fpath, 'rb')
    ds = xr.open_dataset(f, engine='h5netcdf')
    baseline_data[i] = ds.analysed_sst.values[0, lat_min_i:lat_max_i+1, lon_min_i:lon_max_i+1]
    ds.close()
    f.close()
    baseline_doy[i] = day_of_year(date)

print(f"Baseline loaded in {time.time()-t0:.1f}s", flush=True)

# ========================
# Build pool masks for each day of year
# ========================
date_to_idx = {date: i for i, date in enumerate(all_baseline_dates)}

# Proper baseline: 1992-01-01 to 2002-12-31 (indices 5 to 4022)
proper_start_idx = 5
proper_end_idx = 4022  # inclusive

# Find proper baseline dates by day of year (only indices in proper range)
doy_to_idxs = {}
for i in range(proper_start_idx, proper_end_idx + 1):
    doy = baseline_doy[i]
    if doy not in doy_to_idxs:
        doy_to_idxs[doy] = []
    doy_to_idxs[doy].append(i)

print(f"Proper baseline dates: {proper_end_idx - proper_start_idx + 1} days", flush=True)

# Build pool masks
pool_masks = {}
for d in range(1, 367):
    if d == 60:
        continue
    mask = np.zeros(n_baseline, dtype=bool)
    if d in doy_to_idxs:
        for idx in doy_to_idxs[d]:
            date_y = all_baseline_dates[idx]
            for offset in range(-5, 6):
                date_x = date_y + datetime.timedelta(days=offset)
                if date_x in date_to_idx:
                    mask[date_to_idx[date_x]] = True
    pool_masks[d] = mask

print("Pool masks built", flush=True)

# Check pool sizes for days near boundaries
for d_check in [1, 2, 5, 6, 10, 59, 61, 360, 361, 365, 366]:
    if d_check in pool_masks:
        print(f"  Day {d_check}: pool size = {pool_masks[d_check].sum()}", flush=True)

# ========================
# Compute threshold and climatology
# ========================
baseline_data_f64 = baseline_data.astype(np.float64)

threshold = np.zeros((366, nlat, nlon), dtype=np.float64)
climatology = np.zeros((366, nlat, nlon), dtype=np.float64)

for d in range(1, 367):
    if d == 60:
        continue
    mask = pool_masks[d]
    if mask.sum() == 0:
        continue
    pool = baseline_data_f64[mask]
    pool_flat = pool.reshape(pool.shape[0], -1)
    
    for c in range(nlat * nlon):
        vals = pool_flat[:, c]
        if np.isnan(vals).all():
            threshold[d-1, c // nlon, c % nlon] = np.nan
            climatology[d-1, c // nlon, c % nlon] = np.nan
        else:
            threshold[d-1, c // nlon, c % nlon] = np.nanpercentile(vals, 90, method='hazen')
            climatology[d-1, c // nlon, c % nlon] = np.nanmean(vals)

# Set day 60 to mean of days 59 and 61
threshold[59] = (threshold[58] + threshold[60]) / 2.0
climatology[59] = (climatology[58] + climatology[60]) / 2.0

print("Threshold and climatology computed", flush=True)

# ========================
# Smooth with 31-day centered moving average (wrapping)
# ========================
def smooth_wrapping(arr):
    """Smooth a 366-element array with unweighted centred 31-day moving mean, wrapping."""
    result = np.zeros_like(arr)
    for d in range(366):
        idxs = [(d + k) % 366 for k in range(-15, 16)]
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=RuntimeWarning)
            result[d] = np.nanmean(arr[idxs], axis=0)
    return result

threshold_smooth = smooth_wrapping(threshold)
climatology_smooth = smooth_wrapping(climatology)

print("Smoothing done", flush=True)

# ========================
# Load target data
# ========================
target_start = datetime.date(2021, 6, 1)
target_end = datetime.date(2021, 8, 31)
target_dates = []
d = target_start
while d <= target_end:
    target_dates.append(d)
    d += datetime.timedelta(days=1)
n_target = len(target_dates)

print(f"Loading {n_target} target files...", flush=True)
target_data = np.zeros((n_target, nlat, nlon), dtype=np.float32)
for i, date in enumerate(target_dates):
    fpath = f'{base}/sst_{date.strftime("%Y%m%d")}.nc'
    f = fs.open(fpath, 'rb')
    ds = xr.open_dataset(f, engine='h5netcdf')
    target_data[i] = ds.analysed_sst.values[0, lat_min_i:lat_max_i+1, lon_min_i:lon_max_i+1]
    ds.close()
    f.close()

target_data_f64 = target_data.astype(np.float64)
print("Target data loaded", flush=True)

# ========================
# Sea cells: cells with finite SST on every target day
# ========================
sea_cells = np.all(~np.isnan(target_data_f64), axis=0)

print(f"Sea cells: {sea_cells.sum()} out of {nlat*nlon}", flush=True)

# ========================
# Determine per-cell MHWs
# ========================
target_doy = np.array([day_of_year(d) for d in target_dates])

target_threshold = np.zeros((n_target, nlat, nlon), dtype=np.float64)
for i, doy in enumerate(target_doy):
    target_threshold[i] = threshold_smooth[doy - 1]

# Hot days
hot = np.zeros((n_target, nlat, nlon), dtype=bool)
for i in range(n_target):
    for la in range(nlat):
        for lo in range(nlon):
            if sea_cells[la, lo] and not np.isnan(target_data_f64[i, la, lo]):
                hot[i, la, lo] = target_data_f64[i, la, lo] >= target_threshold[i, la, lo]

print("Hot days computed", flush=True)

# Find per-cell MHWs
per_cell_mhw = np.zeros((n_target, nlat, nlon), dtype=bool)

for la in range(nlat):
    for lo in range(nlon):
        if not sea_cells[la, lo]:
            continue
        hot_seq = hot[:, la, lo]
        
        # Find runs of hot days
        runs = []
        i = 0
        while i < n_target:
            if hot_seq[i]:
                j = i
                while j < n_target and hot_seq[j]:
                    j += 1
                runs.append((i, j-1))
                i = j
            else:
                i += 1
        
        # Filter runs >= 5 days
        long_runs = [r for r in runs if (r[1] - r[0] + 1) >= 5]
        
        # Join runs separated by 1 or 2 non-hot days
        if long_runs:
            joined = [long_runs[0]]
            for r in long_runs[1:]:
                prev = joined[-1]
                gap = r[0] - prev[1] - 1
                if gap <= 2:
                    joined[-1] = (prev[0], r[1])
                else:
                    joined.append(r)
            
            for start, end in joined:
                per_cell_mhw[start:end+1, la, lo] = True

print("Per-cell MHWs computed", flush=True)

# ========================
# Regional events
# ========================
active = np.any(per_cell_mhw, axis=(1, 2))

events = []
i = 0
while i < n_target:
    if active[i]:
        j = i
        while j < n_target and active[j]:
            j += 1
        events.append((i, j-1))
        i = j
    else:
        i += 1

print(f"Regional events: {len(events)}", flush=True)
for start, end in events:
    print(f"  {target_dates[start]} to {target_dates[end]}", flush=True)

# ========================
# Write output files
# ========================
os.makedirs('output', exist_ok=True)

# Write mhw_mask.nc using xarray
time_vals = np.array([np.datetime64(d) for d in target_dates], dtype='datetime64[ns]')

mhw_da = xr.DataArray(
    per_cell_mhw.astype(np.uint8),
    dims=('time', 'lat', 'lon'),
    coords={
        'time': time_vals,
        'lat': region_lat,
        'lon': region_lon
    },
    name='mhw'
)

mhw_da.to_netcdf('output/mhw_mask.nc', engine='h5netcdf')
print("mhw_mask.nc written", flush=True)

# Write report.json
report = {
    "region": {
        "lat_min": lat_min,
        "lat_max": lat_max,
        "lon_min": lon_min,
        "lon_max": lon_max
    },
    "baseline_analysed": {
        "start": baseline_start.strftime("%Y-%m-%d"),
        "end": baseline_end.strftime("%Y-%m-%d")
    },
    "target_analysed": {
        "start": target_start.strftime("%Y-%m-%d"),
        "end": target_end.strftime("%Y-%m-%d")
    },
    "events": [
        {"onset": target_dates[s].strftime("%Y-%m-%d"), "end": target_dates[e].strftime("%Y-%m-%d")}
        for s, e in events
    ],
    "complete": True,
    "caveats": ""
}

with open('output/report.json', 'w') as f:
    json.dump(report, f, indent=2)

print("report.json written", flush=True)
print("Done!", flush=True)
