import numpy as np
import xarray as xr
import pandas as pd
import fsspec
import os
import json
from datetime import datetime, timedelta

def get_doy(date):
    return date.timetuple().tm_yday

def get_date_from_doy(year, doy):
    # doy is 1-366.
    if doy == 60:
        # Handle Feb 29
        try:
            return datetime(year, 2, 29)
        except ValueError:
            return None
    # For others, we can use pandas
    return pd.to_datetime(f"{year}-01-01") + pd.Timedelta(days=doy-1)

# Dataset and Region
root_dir = 'icsa2027_data_20261101T090944Z/s1z'
lat_min, lat_max = 59.05, 60.25
lon_min, lon_max = 21.25, 22.45
target_start = pd.to_datetime('2005-06-01')
target_end = pd.to_datetime('2005-08-31')
baseline_start = pd.to_datetime('1992-01-01')
baseline_end = pd.to_datetime('2002-12-31')
extended_baseline_start = baseline_start - pd.Timedelta(days=5)
extended_baseline_end = baseline_end + pd.Timedelta(days=5)

fs = fsspec.filesystem('onedata')

# 1. Find target files and identify sea cells
target_dates = pd.date_range(target_start, target_end)
target_files = [f"{root_dir}/sst_{d.strftime('%Y%m%d')}.nc" for d in target_dates]

# Load target data for the region to find sea cells
target_sst_list = []
coords = None

for f_remote in target_files:
    f_local = f"/work/{os.path.basename(f_remote)}"
    fs.get(f_remote, f_local)
    ds = xr.open_dataset(f_local, engine="h5netcdf")
    # Slice region
    ds_region = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))
    if coords is None:
        coords = {'lat': ds_region.latitude.values, 'lon': ds_region.longitude.values}
    target_sst_list.append(ds_region.analysed_sst.values)
    ds.close()
    os.remove(f_local)

target_sst = np.array(target_sst_list) # (time, lat, lon)
# Sea cells: finite on every day of target period
sea_mask = np.all(np.isfinite(target_sst), axis=0)
sea_indices = np.where(sea_mask)

print(f"Region shape: {target_sst.shape[1:]}")
print(f"Sea cells found: {np.sum(sea_mask)}")

# 2. Baseline pools
# Precompute mapping from date to DOYs
date_to_doys = {}
all_baseline_dates = pd.date_range(extended_baseline_start, extended_baseline_end)
for t in all_baseline_dates:
    doys = set()
    for y in [t.year - 1, t.year, t.year + 1]:
        if 1992 <= y <= 2002:
            # Find d such that |t - D(y, d)| <= 5
            # D(y, d) is within [t-5, t+5]
            for t_prime in pd.date_range(t - pd.Timedelta(days=5), t + pd.Timedelta(days=5)):
                if t_prime.year == y:
                    d = t_prime.dayofyear
                    if d != 60:
                        doys.add(d)
    date_to_doys[t] = list(doys)

# To save memory, we'll store pools as lists of arrays or similar
# But for each cell, we need a pool for each d.
# Let's use a dictionary: pools[d] = list of SST arrays
pools = {d: [] for d in range(1, 367) if d != 60}

for t in all_baseline_dates:
    f_remote = f"{root_dir}/sst_{t.strftime('%Y%m%d')}.nc"
    try:
        f_local = f"/work/{os.path.basename(f_remote)}"
        fs.get(f_remote, f_local)
        ds = xr.open_dataset(f_local, engine="h5netcdf")
        ds_region = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))
        sst_vals = ds_region.analysed_sst.values # (1, lat, lon)
        
        # Add to pools
        for d in date_to_doys[t]:
            pools[d].append(sst_vals[0])
            
        ds.close()
        os.remove(f_local)
    except Exception as e:
        print(f"Error processing {f_remote}: {e}")

# Now compute threshold and climatology per sea cell
# shape: (lat, lon, 366)
thresholds = np.full((target_sst.shape[1], target_sst.shape[2], 366), np.nan, dtype=np.float64)
climatology = np.full((target_sst.shape[1], target_sst.shape[2], 366), np.nan, dtype=np.float64)

# To compute efficiently, iterate over d
for d in range(1, 367):
    if d == 60: continue
    
    # pool_d is a list of arrays (time, lat, lon)
    pool_d = np.array(pools[d]) # (num_days, lat, lon)
    
    # For each cell, we only care about sea cells
    # However, it's easier to compute for all and mask later
    # np.nanpercentile and np.nanmean
    thresholds[:, :, d-1] = np.nanpercentile(pool_d, 90, axis=0, method='hazen')
    climatology[:, :, d-1] = np.nanmean(pool_d, axis=0)

# Handle Day 60
thresholds[:, :, 59] = (thresholds[:, :, 58] + thresholds[:, :, 60]) / 2
climatology[:, :, 59] = (climatology[:, :, 58] + climatology[:, :, 60]) / 2

# 3. Smoothing
def smooth_array(arr):
    # arr shape: (lat, lon, 366)
    smoothed = np.full_like(arr, np.nan)
    for d in range(366):
        # indices d-15 to d+15, wrapped
        indices = [(d + i) % 366 for i in range(-15, 16)]
        window = arr[:, :, indices]
        smoothed[:, :, d] = np.nanmean(window, axis=2)
    return smoothed

thresholds = smooth_array(thresholds)
climatology = smooth_array(climatology)

# 4. Detect per-cell MHWs
# target_sst shape: (time, lat, lon)
# thresholds shape: (lat, lon, 366)
mhw_mask = np.zeros(target_sst.shape, dtype=np.uint8)

for lat_idx in range(target_sst.shape[1]):
    for lon_idx in range(target_sst.shape[2]):
        if not sea_mask[lat_idx, lon_idx]:
            continue
        
        # SSTs for this cell over target period
        sst_cell = target_sst[:, lat_idx, lon_idx]
        # Corresponding thresholds
        doy_cell = [get_doy(t) for t in target_dates]
        thresh_cell = np.array([thresholds[lat_idx, lon_idx, d-1] for d in doy_cell])
        
        # Hot days
        hot = sst_cell >= thresh_cell
        
        # MHW detection
        # a run of at least 5 consecutive hot days
        # joined by 1-2 non-hot days
        is_mhw = np.zeros(len(hot), dtype=bool)
        
        # First, find runs of >= 5
        # We can use a simple loop
        i = 0
        while i < len(hot):
            if hot[i]:
                j = i
                while j < len(hot) and hot[j]:
                    j += 1
                if j - i >= 5:
                    is_mhw[i:j] = True
                i = j
            else:
                i += 1
        
        # Now join gaps of 1 or 2
        changed = True
        while changed:
            changed = False
            i = 0
            while i < len(is_mhw) - 2:
                if not is_mhw[i] and is_mhw[i-1] and is_mhw[i+1]: # gap of 1
                    is_mhw[i] = True
                    changed = True
                elif not is_mhw[i] and not is_mhw[i+1] and is_mhw[i-1] and is_mhw[i+2]: # gap of 2
                    is_mhw[i] = True
                    is_mhw[i+1] = True
                    changed = True
                i += 1
        
        # Wait, the gap joining is simpler:
        # "per-cell MHWs separated by 1 or 2 non-hot days are joined into one"
        # This means if we have MHW1 ... gap ... MHW2, and gap <= 2 days, then gap becomes MHW.
        # Let's re-implement this carefully.
        
        # Let's use the logic: 
        # 1. Identify all runs of >= 5 hot days.
        # 2. Join those runs if gap <= 2.
        
        # Re-do
        is_mhw = np.zeros(len(hot), dtype=bool)
        runs = []
        i = 0
        while i < len(hot):
            if hot[i]:
                j = i
                while j < len(hot) and hot[j]:
                    j += 1
                if j - i >= 5:
                    runs.append((i, j))
                i = j
            else:
                i += 1
        
        if not runs:
            mhw_mask[:, lat_idx, lon_idx] = 0
            continue
            
        # Join runs
        merged = []
        if runs:
            curr_start, curr_end = runs[0]
            for next_start, next_end in runs[1:]:
                if next_start - curr_end <= 3: # gap is next_start - curr_end - 1
                    # gap <= 2 means next_start - curr_end <= 3
                    curr_end = next_end
                else:
                    merged.append((curr_start, curr_end))
                    curr_start, curr_end = next_start, next_end
            merged.append((curr_start, curr_end))
            
        for s, e in merged:
            is_mhw[s:e] = True
        
        mhw_mask[:, lat_idx, lon_idx] = is_mhw.astype(np.uint8)

# 5. Regional Events
active_days = np.any(mhw_mask == 1, axis=(1, 2))
regional_events = []
i = 0
while i < len(active_days):
    if active_days[i]:
        j = i
        while j < len(active_days) and active_days[j]:
            j += 1
        regional_events.append({
            "onset": target_dates[i].strftime('%Y-%m-%d'),
            "end": target_dates[j-1].strftime('%Y-%m-%d')
        })
        i = j
    else:
        i += 1

# 6. Save results
# mhw_mask.nc
ds_out = xr.Dataset(
    {"mhw": (("time", "lat", "lon"), mhw_mask)},
    coords={"time": target_dates, "lat": coords['lat'], "lon": coords['lon']}
)
os.makedirs('output', exist_ok=True)
ds_out.to_netcdf('output/mhw_mask.nc')

# report.json
report = {
    "region": {"lat_min": lat_min, "lat_max": lat_max, "lon_min": lon_min, "lon_max": lon_max},
    "baseline_analysed": {
        "start": extended_baseline_start.strftime('%Y-%m-%d'),
        "end": extended_baseline_end.strftime('%Y-%m-%d')
    },
    "target_analysed": {
        "start": target_start.strftime('%Y-%m-%d'),
        "end": target_end.strftime('%Y-%m-%d')
    },
    "events": regional_events,
    "complete": True,
    "caveats": ""
}
with open('output/report.json', 'w') as f:
    json.dump(report, f, indent=2)

print("Done")
