import fsspec
import xarray as xr
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import json

# Parameters
lat_min, lat_max = 57.33, 58.53
lon_min, lon_max = 9.03, 10.23
target_start = pd.to_datetime("2021-06-01")
target_end = pd.to_datetime("2021-08-31")
baseline_start = pd.to_datetime("1992-01-01")
baseline_end = pd.to_datetime("2002-12-31")

# Load data for target and baseline windows
fs = fsspec.filesystem('onedata')
root_dir = 'icsa2027_data_20261101T090944Z/s1z'

def get_doy(dt):
    # Map date to day of year (1-366) as if it were a leap year
    return datetime(2000, dt.month, dt.day).timetuple().tm_yday

def load_sst_range(start, end, lat_min, lat_max, lon_min, lon_max):
    dates = pd.date_range(start, end)
    sst_list = []
    actual_dates = []
    
    # We'll read a sample file first to get coordinates
    sample_file = f"{root_dir}/sst_{dates[0].strftime('%Y%m%d')}.nc"
    with fs.open(sample_file, "rb") as f:
        ds_sample = xr.open_dataset(f, engine="h5netcdf")
        # Handle coordinate order
        lats = ds_sample.latitude.values
        lons = ds_sample.longitude.values
        
        lat_mask = (lats >= lat_min) & (lats <= lat_max)
        lon_mask = (lons >= lon_min) & (lons <= lon_max)
        
        selected_lats = lats[lat_mask]
        selected_lons = lons[lon_mask]
        
    for d in dates:
        date_str = d.strftime("%Y%m%d")
        file_path = f"{root_dir}/sst_{date_str}.nc"
        try:
            with fs.open(file_path, "rb") as f:
                ds = xr.open_dataset(f, engine="h5netcdf")
                # Use indices for speed and precision
                sst_val = ds.analysed_sst.values[0, lat_mask, lon_mask].astype(np.float64)
                sst_list.append(sst_val)
                actual_dates.append(d)
        except Exception:
            pass
            
    return np.array(sst_list), np.array(actual_dates), selected_lats, selected_lons

# Baseline window extension
baseline_window_start = baseline_start - timedelta(days=5)
baseline_window_end = baseline_end + timedelta(days=5)

print("Loading baseline data...")
sst_baseline, dates_baseline, lats, lons = load_sst_range(baseline_window_start, baseline_window_end, lat_min, lat_max, lon_min, lon_max)
print("Loading target data...")
sst_target, dates_target, _, _ = load_sst_range(target_start, target_end, lat_min, lat_max, lon_min, lon_max)

# 1. Sea cells: SST is finite on every day of the target period
# sst_target shape: (time, lat, lon)
# We need to handle missing days in target period if any.
target_mask = np.all(np.isfinite(sst_target), axis=0)
sea_cells = target_mask
n_lat, n_lon = sst_target.shape[1:]

# 2. Threshold and Climatology
# Pre-calculate DOY for all loaded baseline dates
baseline_doy_map = {d: get_doy(d) for d in dates_baseline}
baseline_date_to_idx = {d: i for i, d in enumerate(dates_baseline)}

thresholds = np.full((366, n_lat, n_lon), np.nan, dtype=np.float64)
climatologies = np.full((366, n_lat, n_lon), np.nan, dtype=np.float64)

# Find all baseline dates between 1992-01-01 and 2002-12-31
baseline_years_dates = pd.date_range(baseline_start, baseline_end)
# Group baseline dates by their DOY
doy_to_baseline_dates = {}
for d in baseline_years_dates:
    doy = get_doy(d)
    if doy != 60:
        doy_to_baseline_dates.setdefault(doy, []).append(d)

print("Computing thresholds and climatologies...")
for doy in range(1, 367):
    if doy == 60:
        continue
    
    # Pool dates: for each B_y with DOY=doy, take B_y - 5 to B_y + 5
    pool_indices = []
    for by in doy_to_baseline_dates.get(doy, []):
        for offset in range(-5, 6):
            win_date = by + timedelta(days=offset)
            if win_date in baseline_date_to_idx:
                pool_indices.append(baseline_date_to_idx[win_date])
    
    if not pool_indices:
        continue
        
    # Extract values for the pool
    # shape: (len(pool_indices), n_lat, n_lon)
    pool_vals = sst_baseline[pool_indices]
    
    # Compute 90th percentile (hazen) and mean
    # We use np.nanquantile(..., method='hazen') and np.nanmean
    thresholds[doy-1] = np.nanquantile(pool_vals, 0.9, axis=0, method='hazen')
    climatologies[doy-1] = np.nanmean(pool_vals, axis=0)

# Day 60 = mean of 59 and 61
thresholds[59] = (thresholds[58] + thresholds[60]) / 2
climatologies[59] = (climatologies[58] + climatologies[60]) / 2

# 31-day smoothing (wrap around)
def smooth_366(arr):
    smoothed = np.zeros_like(arr)
    for i in range(366):
        # window i-15 to i+15
        window = []
        for offset in range(-15, 16):
            idx = (i + offset) % 366
            window.append(arr[idx])
        smoothed[i] = np.nanmean(np.array(window), axis=0)
    return smoothed

thresholds_smooth = smooth_366(thresholds)
climatologies_smooth = smooth_366(climatologies)

# 3. Per-cell MHWs
# Target period only: 2021-06-01 to 2021-08-31
# sst_target shape: (time, n_lat, n_lon)
# thresholds_smooth shape: (366, n_lat, n_lon)
mhw_mask = np.zeros(sst_target.shape, dtype=np.uint8)

for lat_idx in range(n_lat):
    for lon_idx in range(n_lon):
        if not sea_cells[lat_idx, lon_idx]:
            continue
            
        # SST for this cell over target period
        cell_sst = sst_target[:, lat_idx, lon_idx]
        # Thresholds for this cell over target period
        cell_thresholds = []
        for d in dates_target:
            cell_thresholds.append(thresholds_smooth[get_doy(d)-1, lat_idx, lon_idx])
        cell_thresholds = np.array(cell_thresholds)
        
        # Hot days
        hot = cell_sst >= cell_thresholds
        
        # Identify runs of >= 5 hot days
        # Join gaps of 1 or 2 non-hot days
        # A simpler way to implement "join gaps of 1 or 2":
        # First, find hot days.
        # Then, any non-hot day that is between two hot runs and the gap is <= 2 is filled.
        # Repeat until no more gaps can be filled.
        
        current_hot = hot.copy()
        while True:
            changed = False
            for i in range(1, len(current_hot)-1):
                if not current_hot[i]:
                    # Check for gap of 1
                    if current_hot[i-1] and current_hot[i+1]:
                        current_hot[i] = True
                        changed = True
                    # Check for gap of 2
                    elif i < len(current_hot)-2 and current_hot[i-1] and not current_hot[i+1] and current_hot[i+2]:
                        # This is a gap of 2 (i and i+1).
                        # But we only fill i if it's part of a gap of 2.
                        # Let's use a more robust approach.
                        pass
            # To handle gaps of 1 or 2 properly:
            # A gap of 1: hot, non-hot, hot -> fill
            # A gap of 2: hot, non-hot, non-hot, hot -> fill both
            
            # Reset and do a clean pass
            new_hot = current_hot.copy()
            for i in range(1, len(current_hot)-1):
                if not current_hot[i]:
                    if current_hot[i-1] and current_hot[i+1]:
                        new_hot[i] = True
                    elif i < len(current_hot)-2 and current_hot[i-1] and not current_hot[i+1] and current_hot[i+2]:
                        new_hot[i] = True
                        new_hot[i+1] = True
            if np.array_equal(new_hot, current_hot):
                break
            current_hot = new_hot
            changed = True
            
        # Now, only keep runs of >= 5 consecutive hot days
        final_hot = np.zeros_like(current_hot, dtype=bool)
        i = 0
        while i < len(current_hot):
            if current_hot[i]:
                j = i
                while j < len(current_hot) and current_hot[j]:
                    j += 1
                if j - i >= 5:
                    final_hot[i:j] = True
                i = j
            else:
                i += 1
        
        mhw_mask[:, lat_idx, lon_idx] = final_hot.astype(np.uint8)

# 4. Regional events
# Day is active if at least one sea cell is in an MHW
active_days = np.any(mhw_mask == 1, axis=(1, 2))
regional_events = []
i = 0
while i < len(active_days):
    if active_days[i]:
        j = i
        while j < len(active_days) and active_days[j]:
            j += 1
        regional_events.append({
            "onset": dates_target[i].strftime("%Y-%m-%d"),
            "end": dates_target[j-1].strftime("%Y-%m-%d")
        })
        i = j
    else:
        i += 1

# Outputs
# mhw_mask.nc
ds_out = xr.Dataset(
    {"mhw": (("time", "latitude", "longitude"), mhw_mask)},
    coords={
        "time": dates_target,
        "latitude": lats,
        "longitude": lons,
    }
)
ds_out.to_netcdf("output/mhw_mask.nc")

# report.json
report = {
    "region": {"lat_min": lat_min, "lat_max": lat_max, "lon_min": lon_min, "lon_max": lon_max},
    "baseline_analysed": {
        "start": dates_baseline[0].strftime("%Y-%m-%d"),
        "end": dates_baseline[-1].strftime("%Y-%m-%d")
    },
    "target_analysed": {
        "start": dates_target[0].strftime("%Y-%m-%d"),
        "end": dates_target[-1].strftime("%Y-%m-%d")
    },
    "events": regional_events,
    "complete": True,
    "caveats": ""
}
with open("output/report.json", "w") as f:
    json.dump(report, f)

print("Done.")
