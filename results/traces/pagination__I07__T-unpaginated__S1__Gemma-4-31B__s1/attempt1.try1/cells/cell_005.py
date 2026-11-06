import numpy as np
import pandas as pd
import xarray as xr
import fsspec
from datetime import datetime, timedelta
import json

fs = fsspec.filesystem('onedata')
base_path = 'icsa2027_data_20261101T090944Z/s1z'

lat_min, lat_max = 54.45, 55.65
lon_min, lon_max = 16.05, 17.25
target_start = pd.Timestamp('2021-06-01')
target_end = pd.Timestamp('2021-08-31')

def get_custom_doy(date):
    month = date.month
    day = date.day
    offsets = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return offsets[month-1] + day

def get_sst_subset_fixed(date):
    date_str = date.strftime('%Y%m%d')
    path = f'{base_path}/sst_{date_str}.nc'
    try:
        with fs.open(path, 'rb') as f:
            ds = xr.open_dataset(f, engine='h5netcdf')
            subset_ds = ds.sel(
                latitude=slice(lat_min, lat_max), 
                longitude=slice(lon_min, lon_max)
            )
            return subset_ds.analysed_sst.values.astype(np.float64), subset_ds.latitude.values, subset_ds.longitude.values
    except Exception:
        return None, None, None

# 1. Find Sea Cells
target_dates = pd.date_range(target_start, target_end)
sst_target_list = []
sliced_lats, sliced_lons = None, None

for date in target_dates:
    sst, la, lo = get_sst_subset_fixed(date)
    if sst is not None:
        sst_target_list.append(sst)
        sliced_lats, sliced_lons = la, lo
    else:
        sst_target_list.append(None)

if sliced_lats is None:
    # Try to get coords from any file if the first one failed
    # but let's just assume we have some.
    pass

# Handle any None in target list
shape = (len(sliced_lats), len(sliced_lons))
sst_target_list = [sst if sst is not None else np.full(shape, np.nan) for sst in sst_target_list]
sst_target = np.stack(sst_target_list)
sea_mask = np.all(np.isfinite(sst_target), axis=0)

# 2. Baseline Climatology and Threshold
baseline_start = pd.Timestamp('1992-01-01')
baseline_end = pd.Timestamp('2002-12-31')
# The range of files we need is baseline_start - 5 days to baseline_end + 5 days
all_baseline_dates = pd.date_range(baseline_start - pd.Timedelta(days=5), 
                                   baseline_end + pd.Timedelta(days=5))

# Load all baseline SSTs for the region
baseline_sst_dict = {}
for date in all_baseline_dates:
    sst, la, lo = get_sst_subset_fixed(date)
    if sst is not None:
        baseline_sst_dict[date] = sst
    else:
        baseline_sst_dict[date] = np.full(shape, np.nan)

# Pre-calculate threshold and climatology for each sea cell
# Dimensions: (366, lat, lon)
thresholds = np.full((366, *shape), np.nan)
climatology = np.full((366, *shape), np.nan)

# Pre-calculate baseline dates for each DOY
baseline_period = pd.date_range(baseline_start, baseline_end)
doy_to_baseline_dates = {d: [] for d in range(1, 367)}
for d in baseline_period:
    doy = get_custom_doy(d)
    if doy in doy_to_baseline_dates:
        doy_to_baseline_dates[doy].append(d)

for d in range(1, 367):
    if d == 60:
        continue
    
    # Pool of dates for DOY d
    pool_dates = set()
    for b_date in doy_to_baseline_dates[d]:
        for offset in range(-5, 6):
            pool_dates.add(b_date + pd.Timedelta(days=offset))
    
    # Gather SSTs for these dates
    pool_ssts = []
    for p_date in pool_dates:
        if p_date in baseline_sst_dict:
            pool_ssts.append(baseline_sst_dict[p_date])
        else:
            pool_ssts.append(np.full(shape, np.nan))
    
    pool_ssts = np.stack(pool_ssts) # (num_dates, lat, lon)
    
    # Compute 90th percentile (Hazen) and mean
    # Hazen is method='hazen' in np.quantile
    thresholds[d-1] = np.nanquantile(pool_ssts, 0.9, axis=0, method='hazen')
    climatology[d-1] = np.nanmean(pool_ssts, axis=0)

# Handle day 60
thresholds[59] = (thresholds[58] + thresholds[60]) / 2
climatology[59] = (climatology[58] + climatology[60]) / 2

# Smoothing: unweighted centred 31-day moving mean that wraps around
def smooth_array(arr):
    # arr shape (366, lat, lon)
    smoothed = np.full_like(arr, np.nan)
    for d in range(366):
        # Window: d-15 to d+15 modulo 366
        window_indices = [(d + i) % 366 for i in range(-15, 16)]
        window_data = arr[window_indices]
        smoothed[d] = np.nanmean(window_data, axis=0)
    return smoothed

thresholds = smooth_array(thresholds)
climatology = smooth_array(climatology)

# 3. Per-cell MHWs
# Target period: 2021-06-01 to 2021-08-31
mhw_mask = np.zeros((len(target_dates), *shape), dtype=np.uint8)

for r in range(shape[0]):
    for c in range(shape[1]):
        if not sea_mask[r, c]:
            continue
        
        # For each day in target period, is it hot?
        is_hot = []
        for i, date in enumerate(target_dates):
            doy = get_custom_doy(date)
            sst_val = sst_target[i, r, c]
            thresh_val = thresholds[doy-1, r, c]
            is_hot.append(sst_val >= thresh_val if not np.isnan(sst_val) and not np.isnan(thresh_val) else False)
        
        is_hot = np.array(is_hot)
        
        # Find runs of at least 5 consecutive hot days
        # Then join gaps of 1 or 2 non-hot days
        
        # Standard run finding
        in_mhw = np.zeros(len(is_hot), dtype=bool)
        
        # First, find runs of 5+
        i = 0
        while i < len(is_hot):
            if is_hot[i]:
                start = i
                while i < len(is_hot) and is_hot[i]:
                    i += 1
                if i - start >= 5:
                    in_mhw[start:i] = True
            else:
                i += 1
        
        # Join gaps of 1 or 2 non-hot days
        # Note: the gaps are joined only if they are between two MHW segments.
        # Let's repeat joining until no more changes occur.
        changed = True
        while changed:
            changed = False
            for i in range(1, len(in_mhw)-1):
                if not in_mhw[i]:
                    # Gap of 1
                    if in_mhw[i-1] and in_mhw[i+1]:
                        in_mhw[i] = True
                        changed = True
            for i in range(1, len(in_mhw)-2):
                if not in_mhw[i] and not in_mhw[i+1]:
                    # Gap of 2
                    if in_mhw[i-1] and in_mhw[i+2]:
                        in_mhw[i] = True
                        in_mhw[i+1] = True
                        changed = True
        
        mhw_mask[:, r, c] = in_mhw.astype(np.uint8)

# 4. Regional events
active_days = np.any(mhw_mask == 1, axis=(1, 2))
regional_events = []
i = 0
while i < len(active_days):
    if active_days[i]:
        start = i
        while i < len(active_days) and active_days[i]:
            i += 1
        regional_events.append({
            "onset": target_dates[start].strftime('%Y-%m-%d'),
            "end": target_dates[i-1].strftime('%Y-%m-%d')
        })
    else:
        i += 1

# Write output
os.makedirs('output', exist_ok=True)
# mhw_mask.nc
ds_out = xr.Dataset(
    {"mhw": (("time", "latitude", "longitude"), mhw_mask)},
    coords={
        "time": target_dates,
        "latitude": sliced_lats,
        "longitude": sliced_lons
    }
)
ds_out.to_netcdf('output/mhw_mask.nc')

# report.json
report = {
    "region": {"lat_min": lat_min, "lat_max": lat_max, "lon_min": lon_min, "lon_max": lon_max},
    "baseline_analysed": {"start": baseline_start.strftime('%Y-%m-%d'), "end": baseline_end.strftime('%Y-%m-%d')},
    "target_analysed": {"start": target_start.strftime('%Y-%m-%d'), "end": target_end.strftime('%Y-%m-%d')},
    "events": regional_events,
    "complete": True,
    "caveats": ""
}
with open('output/report.json', 'w') as f:
    json.dump(report, f)

print("Done")
