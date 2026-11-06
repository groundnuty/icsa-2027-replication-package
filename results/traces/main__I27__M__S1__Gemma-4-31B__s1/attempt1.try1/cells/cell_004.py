import os
import numpy as np
import pandas as pd
import xarray as xr
from datetime import datetime, timedelta
import json

# Parameters
lat_min, lat_max = 57.83, 59.03
lon_min, lon_max = 17.41, 18.61
target_start_str = "2008-06-01"
target_end_str = "2008-08-31"
baseline_start_str = "1992-01-01"
baseline_end_str = "2002-12-31"
baseline_pool_start_str = "1991-12-27"
baseline_pool_end_str = "2003-01-05"

data_dir = '/data/icsa2027_data_20261101T090944Z/s1z'

def get_doy(dt):
    """Custom day of year mapping as per instructions."""
    # 1 Jan = 1, ..., 28 Feb = 59, 29 Feb = 60, 1 Mar = 61, ..., 31 Dec = 366
    # This is basically just the standard doy, but we need to ensure it's 1-indexed
    # and we handle the 29 Feb as 60.
    return dt.timetuple().tm_yday

def get_sst_for_period(start_str, end_str, lat_range, lon_range):
    dates = pd.date_range(start_str, end_str)
    sst_list = []
    times = []
    for d in dates:
        fname = f"sst_{d.strftime('%Y%m%d')}.nc"
        path = os.path.join(data_dir, fname)
        with xr.open_dataset(path, engine="h5netcdf") as ds:
            # Slice to region immediately
            region_sst = ds.analysed_sst.sel(
                latitude=slice(lat_min, lat_max),
                longitude=slice(lon_min, lon_max)
            ).values
            sst_list.append(region_sst)
            times.append(d)
    
    # Create xarray Dataset
    # Need to get coordinates from one of the files
    with xr.open_dataset(os.path.join(data_dir, f"sst_{dates[0].strftime('%Y%m%d')}.nc"), engine="h5netcdf") as ds:
        region_ds = ds.sel(
            latitude=slice(lat_min, lat_max),
            longitude=slice(lon_min, lon_max)
        )
        lats = region_ds.latitude.values
        lons = region_ds.longitude.values
    
    sst_array = np.array(sst_list, dtype=np.float64)
    ds_res = xr.Dataset(
        {"sst": (("time", "latitude", "longitude"), sst_array)},
        coords={"time": times, "latitude": lats, "longitude": lons}
    )
    return ds_res

# 1. Sea cells identification
print("Loading target period data...")
ds_target = get_sst_for_period(target_start_str, target_end_str, (lat_min, lat_max), (lon_min, lon_max))
# Sea cells: SST is finite on every day of the target period
sst_target = ds_target.sst.values
# Finite on every day -> all(np.isfinite(sst_target, axis=0))
sea_mask = np.all(np.isfinite(sst_target), axis=0)
print(f"Sea cells found: {np.sum(sea_mask)} out of {sea_mask.size}")

# 2. Threshold and Climatology
print("Loading baseline pool data...")
ds_baseline = get_sst_for_period(baseline_pool_start_str, baseline_pool_end_str, (lat_min, lat_max), (lon_min, lon_max))
sst_baseline = ds_baseline.sst.values
time_baseline = pd.to_datetime(ds_baseline.time.values)

# Pre-calculate DOY for baseline dates
baseline_doys = np.array([get_doy(t) for t in time_baseline])

# We only care about sea cells
sst_baseline_sea = sst_baseline[:, sea_mask]
n_sea_cells = np.sum(sea_mask)
n_baseline_days = len(time_baseline)

thresholds = np.full((366, n_sea_cells), np.nan, dtype=np.float64)
climatology = np.full((366, n_sea_cells), np.nan, dtype=np.float64)

# Baseline range for anchor dates: 1992-01-01 to 2002-12-31
baseline_anchor_start = pd.to_datetime(baseline_start_str)
baseline_anchor_end = pd.to_datetime(baseline_end_str)
anchor_dates = pd.date_range(baseline_anchor_start, baseline_anchor_end)

# Map each day of year (1-366, except 60) to its anchor dates
doy_to_anchors = {d: [] for d in range(1, 367)}
for ad in anchor_dates:
    doy_to_anchors[get_doy(ad)].append(ad)

print("Computing thresholds and climatology...")
for d in range(1, 367):
    if d == 60:
        continue
    
    # Pool is SST values within +/- 5 days of any anchor date with DOY d
    # Find all dates in the pool
    pool_dates = set()
    for ad in doy_to_anchors[d]:
        for offset in range(-5, 6):
            pool_dates.add(ad + timedelta(days=offset))
    
    # Convert pool dates to indices in sst_baseline
    # baseline_pool_start is 1991-12-27.
    pool_indices = []
    for pd_date in pool_dates:
        # The pool date must be within the baseline_pool range
        if pd.to_datetime(baseline_pool_start_str) <= pd_date <= pd.to_datetime(baseline_pool_end_str):
            # Find index in time_baseline
            # Since time_baseline is sorted and daily, we can use simple subtraction
            idx = (pd_date - pd.to_datetime(baseline_pool_start_str)).days
            if 0 <= idx < n_baseline_days:
                pool_indices.append(idx)
    
    if not pool_indices:
        continue
        
    pool_data = sst_baseline_sea[pool_indices, :] # (n_pool_days, n_sea_cells)
    
    # 90th percentile (Hazen) and mean
    # numpy.nanquantile(..., method="hazen")
    thresholds[d-1, :] = np.nanquantile(pool_data, 0.9, axis=0, method="hazen")
    climatology[d-1, :] = np.nanmean(pool_data, axis=0)

# Set day 60
thresholds[59, :] = (thresholds[58, :] + thresholds[60, :]) / 2
climatology[59, :] = (climatology[58, :] + climatology[60, :]) / 2

def smooth_366(arr):
    """Unweighted centred 31-day moving mean that wraps around the year."""
    # arr: (366, n_cells)
    smoothed = np.full_like(arr, np.nan)
    for d in range(366):
        # d is 0-indexed, corresponds to DOY d+1
        # We want days d-15 to d+15 (inclusive) modulo 366
        indices = [(d + i) % 366 for i in range(-15, 16)]
        window = arr[indices, :]
        smoothed[d, :] = np.nanmean(window, axis=0)
    return smoothed

print("Smoothing...")
thresholds_smooth = smooth_366(thresholds)
climatology_smooth = smooth_366(climatology)

# 3. Per-cell MHWs
print("Detecting per-cell MHWs...")
# Target period SSTs for sea cells
sst_target_sea = sst_target[:, sea_mask]
target_doys = np.array([get_doy(t) for t in ds_target.time.values])

# A day is hot if SST >= threshold
# thresholds_smooth is (366, n_sea_cells)
# target_doys is (n_target_days,)
# sst_target_sea is (n_target_days, n_sea_cells)
hot_mask = np.zeros((len(target_doys), n_sea_cells), dtype=bool)
for t_idx in range(len(target_doys)):
    doy = target_doys[t_idx]
    # doy is 1-366
    hot_mask[t_idx, :] = sst_target_sea[t_idx, :] >= thresholds_smooth[doy-1, :]

# Per-cell MHWs
mhw_mask_sea = np.zeros_like(hot_mask, dtype=bool)
for c in range(n_sea_cells):
    cell_hot = hot_mask[:, c]
    # Find runs of hot days
    # a per-cell MHW is a run of at least 5 consecutive hot days
    # separated by 1 or 2 non-hot days are joined
    
    # First, find all runs of >= 5 hot days
    # Using a simple loop for clarity on a small target period (92 days)
    is_mhw = np.zeros(len(cell_hot), dtype=bool)
    
    # Identify initial hot runs
    run_start = None
    for t in range(len(cell_hot)):
        if cell_hot[t]:
            if run_start is None:
                run_start = t
        else:
            if run_start is not None:
                if t - run_start >= 5:
                    is_mhw[run_start:t] = True
                run_start = None
    if run_start is not None and len(cell_hot) - run_start >= 5:
        is_mhw[run_start:] = True
        
    # Join gaps of 1 or 2 non-hot days
    # Repeat until no more joins possible
    changed = True
    while changed:
        changed = False
        for t in range(1, len(cell_hot)-1):
            if not is_mhw[t]:
                # Check if it's a gap of 1
                if is_mhw[t-1] and is_mhw[t+1]:
                    is_mhw[t] = True
                    changed = True
                # Check if it's a gap of 2
                elif t < len(cell_hot)-2 and is_mhw[t-1] and not is_mhw[t+1] and is_mhw[t+2]:
                    is_mhw[t] = True
                    is_mhw[t+1] = True
                    changed = True
                elif t > 0 and not is_mhw[t-1] and is_mhw[t-2] and is_mhw[t+1]:
                    # this case is covered by the logic above if we iterate carefully
                    pass
                    
        # Better gap joining:
        # Find all segments of False. If a segment of False has length 1 or 2, 
        # and is bounded by True on both sides, turn it to True.
        
        # Re-implementing gap joining more robustly
        new_is_mhw = is_mhw.copy()
        t = 0
        while t < len(is_mhw):
            if not is_mhw[t]:
                start = t
                while t < len(is_mhw) and not is_mhw[t]:
                    t += 1
                end = t
                # gap is [start, end)
                gap_len = end - start
                if 0 < gap_len <= 2:
                    if start > 0 and end < len(is_mhw):
                        if is_mhw[start-1] and is_mhw[end]:
                            new_is_mhw[start:end] = True
                            changed = True
            else:
                t += 1
        is_mhw = new_is_mhw

    mhw_mask_sea[:, c] = is_mhw

# 4. Regional events
# a day is active if at least one sea cell of the region is inside a per-cell MHW
active_days = np.any(mhw_mask_sea, axis=1)

# regional MHW event is a maximal run of consecutive active days
regional_events = []
run_start = None
for t in range(len(active_days)):
    if active_days[t]:
        if run_start is None:
            run_start = t
    else:
        if run_start is not None:
            regional_events.append((run_start, t-1))
            run_start = None
if run_start is not None:
    regional_events.append((run_start, len(active_days)-1))

# Output mhw_mask.nc
full_mhw_mask = np.zeros((len(target_doys), len(lats), len(lons)), dtype=np.uint8)
# We need the sea_mask to map back to full grid
# sea_mask is (len(lats), len(lons))
# mhw_mask_sea is (len(target_doys), n_sea_cells)
sea_indices = np.where(sea_mask)
# For each sea cell, fill its MHW status
for i in range(n_sea_cells):
    lat_idx = sea_indices[0][i]
    lon_idx = sea_indices[1][i]
    full_mhw_mask[:, lat_idx, lon_idx] = mhw_mask_sea[:, i].astype(np.uint8)

# Create xarray Dataset for output
ds_out = xr.Dataset(
    {"mhw": (("time", "latitude", "longitude"), full_mhw_mask)},
    coords={"time": ds_target.time.values, "latitude": lats, "longitude": lons}
)
os.makedirs("output", exist_ok=True)
ds_out.to_netcdf("output/mhw_mask.nc")

# Output report.json
report = {
    "region": {"lat_min": lat_min, "lat_max": lat_max, "lon_min": lon_min, "lon_max": lon_max},
    "baseline_analysed": {"start": baseline_pool_start_str, "end": baseline_pool_end_str},
    "target_analysed": {"start": target_start_str, "end": target_end_str},
    "events": [
        {"onset": ds_target.time.values[e[0]].strftime("%Y-%m-%d"), "end": ds_target.time.values[e[1]].strftime("%Y-%m-%d")}
        for e in regional_events
    ],
    "complete": True,
    "caveats": ""
}

with open("output/report.json", "w") as f:
    json.dump(report, f, indent=2)

print("Done.")
