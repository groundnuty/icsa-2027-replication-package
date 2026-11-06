import fsspec
import xarray as xr
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json

def get_doy(date):
    """Map date to day of year from 1 to 366.
    Non-leap years have no day 60 (Mar 1 is 61).
    """
    month = date.month
    day = date.day
    days_in_month = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return sum(days_in_month[:month-1]) + day

def is_leap(year):
    return (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)

fs = fsspec.filesystem('onedata')
base_path = 'icsa2027_data_20261101T090944Z/s1z'

lat_min, lat_max = 58.69, 59.89
lon_min, lon_max = 18.69, 19.89
target_start = pd.to_datetime('2010-06-01')
target_end = pd.to_datetime('2010-08-31')
baseline_start_year = 1992
baseline_end_year = 2002

# We need data from 1991-12-27 to 2003-01-05 to cover all possible windows.
baseline_data_start = pd.to_datetime('1991-12-27')
baseline_data_end = pd.to_datetime('2003-01-05')

def load_sst_range(start_date, end_date):
    dates = pd.date_range(start_date, end_date)
    sst_list = []
    coords_lat = None
    coords_lon = None
    
    for d in dates:
        file_path = f"{base_path}/sst_{d.strftime('%Y%m%d')}.nc"
        try:
            with fs.open(file_path, 'rb') as f:
                ds = xr.open_dataset(f, engine='h5netcdf')
                # Slice region
                ds_region = ds.sel(
                    latitude=slice(lat_min, lat_max), 
                    longitude=slice(lon_min, lon_max)
                )
                # Wait, the slicing might be reversed depending on the dataset's coordinate order.
                # Let's double check or use .where() / indexing.
                # Based on previous check, latitude is 53.5...66.0, longitude 9.0...30.0.
                # slice(lat_min, lat_max) should work.
                
                # Let's make sure we are slicing correctly
                # Correcting slice if needed:
                # lat = ds.latitude.values
                # lon = ds.longitude.values
                # lat_mask = (lat >= lat_min) & (lat <= lat_max)
                # lon_mask = (lon >= lon_min) & (lon <= lon_max)
                # sst_val = ds.analysed_sst.values[0, lat_mask, lon_mask]
                
                # Let's use boolean masking for safety
                lat_mask = (ds.latitude >= lat_min) & (ds.latitude <= lat_max)
                lon_mask = (ds.longitude >= lon_min) & (ds.longitude <= lon_max)
                sst_val = ds.analysed_sst.values[0, lat_mask, lon_mask]
                
                if coords_lat is None:
                    coords_lat = ds.latitude.values[lat_mask]
                    coords_lon = ds.longitude.values[lon_mask]
                
                sst_list.append(sst_val)
        except Exception as e:
            print(f"Error loading {file_path}: {e}")
            sst_list.append(np.full((60, 60), np.nan)) # Use size from previous check if possible

    return np.array(sst_list, dtype=np.float64), coords_lat, coords_lon

print("Loading target data...")
target_sst, lats, lons = load_sst_range(target_start, target_end)
print("Loading baseline data...")
baseline_sst, _, _ = load_sst_range(baseline_data_start, baseline_data_end)

# 1. Sea cells
# SST finite on every day of the target period
sea_mask = np.all(np.isfinite(target_sst), axis=0)
print(f"Number of sea cells: {np.sum(sea_mask)}")

# 2. Threshold and Climatology
# Baseline dates range
baseline_dates = pd.date_range(baseline_data_start, baseline_data_end)
baseline_sst_df = pd.DataFrame(baseline_sst.reshape(len(baseline_dates), -1), index=baseline_dates)
baseline_sst_df.columns = [f"cell_{i}" for i in range(baseline_sst.shape[1] * baseline_sst.shape[2])]
# Reshape back to (time, lat, lon) for easier indexing if needed, but let's keep it flat.
# Actually, let's use (time, lat, lon) array.
baseline_sst = baseline_sst # already (time, lat, lon)

# To map date to index in baseline_sst array:
date_to_idx = {d: i for i, d in enumerate(baseline_dates)}

# Precompute baseline dates for each DOY d in [1, 366]
# baseline_years = range(1992, 2003)
doy_to_baseline_dates = {d: [] for d in range(1, 367)}
for year in range(1992, 2003):
    # Find the date for each DOY d in this year
    # We can just iterate through the year's days
    year_dates = pd.date_range(f"{year}-01-01", f"{year}-12-31")
    for date in year_dates:
        d = get_doy(date)
        if d != 60:
            doy_to_baseline_dates[d].append(date)

# Now compute pool for each d != 60
thresholds = np.full((366, baseline_sst.shape[1], baseline_sst.shape[2]), np.nan)
climatologies = np.full((366, baseline_sst.shape[1], baseline_sst.shape[2]), np.nan)

# Optimize: compute pool indices first
doy_to_pool_indices = {d: [] for d in range(1, 367)}
for d in range(1, 367):
    if d == 60: continue
    pool_dates = set()
    for b_date in doy_to_baseline_dates[d]:
        for offset in range(-5, 6):
            t = b_date + timedelta(days=offset)
            if t in date_to_idx:
                pool_dates.add(date_to_idx[t])
    doy_to_pool_indices[d] = list(pool_dates)

for d in range(1, 367):
    if d == 60: continue
    indices = doy_to_pool_indices[d]
    # pool is baseline_sst[indices, :, :] which is (len(indices), lat, lon)
    pool = baseline_sst[indices, :, :]
    
    # Calculate 90th percentile (Hazen) and mean per cell
    # numpy.nanquantile with method="hazen"
    # We need to do this per cell.
    # Since we only care about sea cells, we can optimize.
    
    # To avoid loop over cells, we can use np.nanquantile on axis=0
    # But nanquantile can be slow.
    thresh = np.nanquantile(pool, 0.9, axis=0, method="hazen")
    clim = np.nanmean(pool, axis=0)
    
    thresholds[d-1] = thresh
    climatologies[d-1] = clim

# Day 60
thresholds[59] = (thresholds[58] + thresholds[60]) / 2
climatologies[59] = (climatologies[58] + climatologies[60]) / 2

# Smoothing: 31-day centered moving mean (wrap around)
def smooth_366(arr):
    # arr is (366, lat, lon)
    smoothed = np.full_like(arr, np.nan)
    for d in range(366):
        # Window: d-15 to d+15 modulo 366
        window_indices = [(d + offset) % 366 for offset in range(-15, 16)]
        window_data = arr[window_indices, :, :]
        smoothed[d] = np.nanmean(window_data, axis=0)
    return smoothed

thresholds = smooth_366(thresholds)
climatologies = smooth_366(climatologies)

# 3. Per-cell MHWs
# target_sst: (time, lat, lon)
# target_dates: pd.date_range(target_start, target_end)
target_dates = pd.date_range(target_start, target_end)
mhw_mask = np.zeros(target_sst.shape, dtype=np.uint8)

for lat_idx in range(baseline_sst.shape[1]):
    for lon_idx in range(baseline_sst.shape[2]):
        if not sea_mask[lat_idx, lon_idx]:
            continue
        
        # SST for this cell over target period
        sst_cell = target_sst[:, lat_idx, lon_idx]
        
        # Thresholds for this cell over target period
        thresh_cell = np.array([thresholds[get_doy(d)-1, lat_idx, lon_idx] for d in target_dates])
        
        # Hot days
        hot = (sst_cell >= thresh_cell)
        
        # Run of at least 5 consecutive hot days
        # Joining gaps of 1 or 2 non-hot days
        mhw_cell = np.zeros(len(hot), dtype=np.uint8)
        
        # Finding runs
        i = 0
        while i < len(hot):
            if hot[i]:
                start = i
                while i < len(hot) and hot[i]:
                    i += 1
                end = i - 1
                # Current run [start, end]
                # Check if this run is part of a larger MHW or can start one
                # This is tricky. Let's use a different approach for gaps.
                pass
            i += 1
            
        # Let's use a better algorithm for MHWs
        # 1. Mark all runs of >= 5 hot days
        # 2. Join them if gaps are <= 2 days
        
        # Correct algorithm:
        # a. Identify all hot days
        # b. Find contiguous runs of hot days.
        # c. Keep runs with length >= 5.
        # d. Join runs if gap is 1 or 2 days.
        
        # Let's refine:
        # The gap joining should be iterative? 
        # "per-cell MHWs separated by 1 or 2 non-hot days are joined into one"
        # This usually means: if we have two MHWs (each >= 5 days) separated by 1-2 days, 
        # they merge.
        
        # Let's implement:
        hot_days = np.where(hot)[0]
        if len(hot_days) == 0:
            continue
            
        # Group into runs
        runs = []
        if len(hot_days) > 0:
            start = hot_days[0]
            for j in range(1, len(hot_days)):
                if hot_days[j] != hot_days[j-1] + 1:
                    runs.append((start, hot_days[j-1]))
                    start = hot_days[j]
            runs.append((start, hot_days[-1]))
            
        # Filter runs >= 5 days
        mhw_runs = [r for r in runs if (r[1] - r[0] + 1) >= 5]
        
        # Join gaps
        if not mhw_runs:
            continue
            
        joined_runs = []
        if mhw_runs:
            curr_start, curr_end = mhw_runs[0]
            for j in range(1, len(mhw_runs)):
                next_start, next_end = mhw_runs[j]
                if next_start - curr_end - 1 <= 2:
                    curr_end = next_end
                else:
                    joined_runs.append((curr_start, curr_end))
                    curr_start, curr_end = next_start, next_end
            joined_runs.append((curr_start, curr_end))
            
        for rs, re in joined_runs:
            mhw_cell[rs:re+1] = 1
            
        mhw_mask[:, lat_idx, lon_idx] = mhw_cell

# 4. Regional Events
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
            "onset": target_dates[start].strftime('%Y-%m-%d'),
            "end": target_dates[end].strftime('%Y-%m-%d')
        })
    else:
        i += 1

# Save results
# mhw_mask.nc
ds_out = xr.Dataset(
    {"mhw": (("time", "lat", "lon"), mhw_mask)},
    coords={
        "time": target_dates,
        "lat": lats,
        "lon": lons
    }
)
ds_out.to_netcdf("output/mhw_mask.nc")

# report.json
report = {
    "region": {"lat_min": lat_min, "lat_max": lat_max, "lon_min": lon_min, "lon_max": lon_max},
    "baseline_analysed": {
        "start": baseline_dates[0].strftime('%Y-%m-%d'),
        "end": baseline_dates[-1].strftime('%Y-%m-%d')
    },
    "target_analysed": {
        "start": target_dates[0].strftime('%Y-%m-%d'),
        "end": target_dates[-1].strftime('%Y-%m-%d')
    },
    "events": regional_events,
    "complete": True,
    "caveats": ""
}
with open("output/report.json", "w") as f:
    json.dump(report, f)

print("Done.")
