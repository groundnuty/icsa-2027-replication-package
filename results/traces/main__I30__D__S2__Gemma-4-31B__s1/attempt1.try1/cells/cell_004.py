import xarray as xr
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import json
import os

# Create output directory
os.makedirs('output', exist_ok=True)

# Load data
ds = xr.open_dataset('/work/sst_s2.nc', engine="h5netcdf")
lat_min, lat_max = 58.69, 59.89
lon_min, lon_max = 18.69, 19.89
ds_reg = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))

# Baseline and target ranges
baseline_range = pd.date_range('1992-01-01', '2002-12-31')
# Buffer for +/- 5 days
baseline_data_range = pd.date_range('1991-12-27', '2003-01-05')
target_range = pd.date_range('2010-06-01', '2010-08-31')

# Slice and load
ds_baseline_full = ds_reg.sel(time=slice('1991-12-27', '2003-01-05')).load()
ds_target = ds_reg.sel(time=slice('2010-06-01', '2010-08-31')).load()

# Identify sea cells: SST is finite on every day of target period
sst_target = ds_target.analysed_sst.values.astype(np.float64)
sea_mask = np.all(np.isfinite(sst_target), axis=0)

# Climatology and threshold calculation
baseline_full_dates = pd.DatetimeIndex(ds_baseline_full.time.values)

thresholds = np.full((366, ds_reg.latitude.size, ds_reg.longitude.size), np.nan, dtype=np.float64)
climatology = np.full((366, ds_reg.latitude.size, ds_reg.longitude.size), np.nan, dtype=np.float64)

# Pre-calculate the indices for each DOY in the baseline range (1992-2002)
# and then find the union of +/- 5 day windows.
for d in range(1, 367):
    if d == 60:
        continue
    
    # Dates in the official baseline range (1992-2002) that have DOY d
    dates_with_doy = [dt for dt in baseline_range if dt.day_of_year == d]
    
    pool_indices = set()
    for dt_base in dates_with_doy:
        start = dt_base - timedelta(days=5)
        end = dt_base + timedelta(days=5)
        
        idx_start = np.searchsorted(baseline_full_dates, start)
        idx_end = np.searchsorted(baseline_full_dates, end + timedelta(days=1))
        for i in range(idx_start, idx_end):
            pool_indices.add(i)
    
    if not pool_indices:
        continue
        
    pool_indices = sorted(list(pool_indices))
    sst_pool = ds_baseline_full.analysed_sst.values[pool_indices, :, :].astype(np.float64)
    
    # Threshold: 90th percentile (hazen)
    thresholds[d-1] = np.nanquantile(sst_pool, 0.9, axis=0, method="hazen")
    # Climatology: mean
    climatology[d-1] = np.nanmean(sst_pool, axis=0)

# Set day 60 (Feb 29) as mean of 59 and 61
thresholds[59] = (thresholds[58] + thresholds[60]) / 2
climatology[59] = (climatology[58] + climatology[60]) / 2

# Smoothing: 31-day centred moving mean (wraps around)
def smooth_366(arr):
    smoothed = np.zeros_like(arr)
    for d in range(366):
        indices = [(d + i) % 366 for i in range(-15, 16)]
        window_data = arr[indices, :, :]
        smoothed[d] = np.nanmean(window_data, axis=0)
    return smoothed

thresholds_smooth = smooth_366(thresholds)
climatology_smooth = smooth_366(climatology)

# Per-cell MHWs
mhw_mask = np.zeros(sst_target.shape, dtype=np.uint8)
target_doys = [dt.day_of_year for dt in target_range]

for lat_idx in range(ds_reg.latitude.size):
    for lon_idx in range(ds_reg.longitude.size):
        if not sea_mask[lat_idx, lon_idx]:
            continue
            
        sst_cell = sst_target[:, lat_idx, lon_idx]
        thresh_cell = np.array([thresholds_smooth[d-1, lat_idx, lon_idx] for d in target_doys])
        
        is_hot = sst_cell >= thresh_cell
        in_mhw = np.zeros(len(is_hot), dtype=bool)
        
        # Find runs of >= 5 hot days
        i = 0
        while i < len(is_hot):
            if is_hot[i]:
                start = i
                while i < len(is_hot) and is_hot[i]:
                    i += 1
                end = i - 1
                if (end - start + 1) >= 5:
                    in_mhw[start:end+1] = True
            else:
                i += 1
        
        # Join gaps of 1 or 2 non-hot days
        changed = True
        while changed:
            changed = False
            # Gap of 1
            for j in range(1, len(in_mhw)-1):
                if not in_mhw[j] and in_mhw[j-1] and in_mhw[j+1]:
                    in_mhw[j] = True
                    changed = True
            # Gap of 2
            for j in range(1, len(in_mhw)-2):
                if not in_mhw[j] and not in_mhw[j+1] and in_mhw[j-1] and in_mhw[j+2]:
                    in_mhw[j] = True
                    in_mhw[j+1] = True
                    changed = True
        
        mhw_mask[:, lat_idx, lon_idx] = in_mhw.astype(np.uint8)

# Regional events
active_days = np.any(mhw_mask == 1, axis=(1, 2))
regional_events = []
i = 0
while i < len(active_days):
    if active_days[i]:
        start = i
        while i < len(active_days) and active_days[i]:
            i += 1
        end = i - 1
        regional_events.append({
            "onset": target_range[start].strftime('%Y-%m-%d'),
            "end": target_range[end].strftime('%Y-%m-%d')
        })
    else:
        i += 1

# Output mask
ds_out = xr.Dataset(
    {"mhw": (("time", "latitude", "longitude"), mhw_mask)},
    coords={
        "time": ds_target.time,
        "latitude": ds_reg.latitude,
        "longitude": ds_reg.longitude,
    }
)
ds_out.to_netcdf("output/mhw_mask.nc")

# Output report
report = {
    "region": {
        "lat_min": float(lat_min),
        "lat_max": float(lat_max),
        "lon_min": float(lon_min),
        "lon_max": float(lon_max),
    },
    "baseline_analysed": {
        "start": "1992-01-01",
        "end": "2002-12-31"
    },
    "target_analysed": {
        "start": target_range[0].strftime('%Y-%m-%d'),
        "end": target_range[-1].strftime('%Y-%m-%d')
    },
    "events": regional_events,
    "complete": True,
    "caveats": ""
}

with open("output/report.json", "w") as f:
    json.dump(report, f)

print("Analysis complete. Files written.")
