import numpy as np
import xarray as xr
import pandas as pd
import fsspec
import os
import json
from datetime import datetime, timedelta

def get_doy(date):
    return date.day_of_year

# Dataset and Region
root_dir = 'icsa2027_data_20261101T090944Z/s1z'
lat_min, lat_max = 59.05, 60.25
lon_min, lon_max = 21.25, 22.45
target_start = pd.to_datetime('2005-06-01')
target_end = pd.to_datetime('2005-08-31')
baseline_start_year = 1992
baseline_end_year = 2002

fs = fsspec.filesystem('onedata')

# 1. Target Data and Sea Cells
target_dates = pd.date_range(target_start, target_end)
target_sst_list = []
coords = None

for d in target_dates:
    f_remote = f"{root_dir}/sst_{d.strftime('%Y%m%d')}.nc"
    f_local = f"/work/{os.path.basename(f_remote)}"
    fs.get(f_remote, f_local)
    with xr.open_dataset(f_local, engine="h5netcdf") as ds:
        ds_region = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))
        if coords is None:
            coords = {'lat': ds_region.latitude.values, 'lon': ds_region.longitude.values}
        # Squeeze time dimension (it's always 1)
        target_sst_list.append(ds_region.analysed_sst.values.squeeze())
    os.remove(f_local)

target_sst = np.array(target_sst_list, dtype=np.float64) # (time, lat, lon)
sea_mask = np.all(np.isfinite(target_sst), axis=0)

# 2. Thresholds and Climatology
# We need to build pools for each doy d in [1, 366], d != 60
# The pool for d is all SST values within +/- 5 days of any baseline date with doy d.
# Baseline dates are in [1992-01-01, 2002-12-31].

# To avoid reading files many times, we identify all needed baseline files
# Baseline range: [1992-01-01 - 5 days, 2002-12-31 + 5 days]
all_baseline_dates = pd.date_range(pd.to_datetime('1992-01-01') - pd.Timedelta(days=5),
                                   pd.to_datetime('2002-12-31') + pd.Timedelta(days=5))

# Map each baseline date to the DOYs it contributes to.
# A date t contributes to DOY d if there exists a baseline date B in [1992-01-01, 2002-12-31]
# such that B.day_of_year == d and |t - B| <= 5.
date_to_doys = {t: [] for t in all_baseline_dates}
for y in range(baseline_start_year, baseline_end_year + 1):
    # For each day of year d in year y
    year_start = pd.to_datetime(f"{y}-01-01")
    year_end = pd.to_datetime(f"{y}-12-31")
    for b_date in pd.date_range(year_start, year_end):
        d = b_date.day_of_year
        if d == 60: continue
        # This date b_date contributes to DOY d. 
        # All t within [b_date - 5, b_date + 5] also contribute.
        for t in pd.date_range(b_date - pd.Timedelta(days=5), b_date + pd.Timedelta(days=5)):
            if t in date_to_doys:
                date_to_doys[t].append(d)

# Now collect SSTs
pools = {d: [] for d in range(1, 367) if d != 60}
for t in all_baseline_dates:
    f_remote = f"{root_dir}/sst_{t.strftime('%Y%m%d')}.nc"
    f_local = f"/work/{os.path.basename(f_remote)}"
    try:
        fs.get(f_remote, f_local)
        with xr.open_dataset(f_local, engine="h5netcdf") as ds:
            ds_region = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))
            sst_vals = ds_region.analysed_sst.values.squeeze()
            for d in date_to_doys[t]:
                pools[d].append(sst_vals)
    except Exception as e:
        print(f"Error with {f_remote}: {e}")
    finally:
        if os.path.exists(f_local):
            os.remove(f_local)

# Compute thresholds and climatology
lat_len, lon_len = target_sst.shape[1:]
thresholds = np.full((lat_len, lon_len, 366), np.nan, dtype=np.float64)
climatology = np.full((lat_len, lon_len, 366), np.nan, dtype=np.float64)

for d in range(1, 367):
    if d == 60: continue
    pool_d = np.array(pools[d]) # (num_days, lat, lon)
    thresholds[:, :, d-1] = np.nanpercentile(pool_d, 90, axis=0, method='hazen')
    climatology[:, :, d-1] = np.nanmean(pool_d, axis=0)

# Day 60
thresholds[:, :, 59] = (thresholds[:, :, 58] + thresholds[:, :, 60]) / 2
climatology[:, :, 59] = (climatology[:, :, 58] + climatology[:, :, 60]) / 2

# Smoothing
def smooth_array(arr):
    smoothed = np.full_like(arr, np.nan)
    for d in range(366):
        indices = [(d + i) % 366 for i in range(-15, 16)]
        window = arr[:, :, indices]
        smoothed[:, :, d] = np.nanmean(window, axis=2)
    return smoothed

thresholds = smooth_array(thresholds)
climatology = smooth_array(climatology)

# 3. Per-cell MHWs
mhw_mask = np.zeros(target_sst.shape, dtype=np.uint8)
target_doys = [get_doy(t) for t in target_dates]

for lat_idx in range(lat_len):
    for lon_idx in range(lon_len):
        if not sea_mask[lat_idx, lon_idx]:
            continue
        
        sst_cell = target_sst[:, lat_idx, lon_idx]
        thresh_cell = np.array([thresholds[lat_idx, lon_idx, d-1] for d in target_doys])
        
        hot = sst_cell >= thresh_cell
        
        # Run detection
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
            continue
            
        # Join gaps of 1 or 2
        merged = []
        curr_start, curr_end = runs[0]
        for next_start, next_end in runs[1:]:
            if next_start - curr_end <= 3: # gap = next_start - curr_end - 1 <= 2
                curr_end = next_end
            else:
                merged.append((curr_start, curr_end))
                curr_start, curr_end = next_start, next_end
        merged.append((curr_start, curr_end))
        
        for s, e in merged:
            is_mhw[s:e] = True
        
        mhw_mask[:, lat_idx, lon_idx] = is_mhw.astype(np.uint8)

# 4. Regional Events
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

# 5. Save Results
ds_out = xr.Dataset(
    {"mhw": (("time", "lat", "lon"), mhw_mask)},
    coords={"time": target_dates, "lat": coords['lat'], "lon": coords['lon']}
)
os.makedirs('output', exist_ok=True)
ds_out.to_netcdf('output/mhw_mask.nc')

report = {
    "region": {"lat_min": lat_min, "lat_max": lat_max, "lon_min": lon_min, "lon_max": lon_max},
    "baseline_analysed": {
        "start": all_baseline_dates[0].strftime('%Y-%m-%d'),
        "end": all_baseline_dates[-1].strftime('%Y-%m-%d')
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
