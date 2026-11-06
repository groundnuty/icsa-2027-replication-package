import numpy as np
import pandas as pd
import xarray as xr
import fsspec
import json
from datetime import datetime, timedelta

# Constants
LAT_MIN, LAT_MAX = 57.13, 58.33
LON_MIN, LON_MAX = 22.79, 23.99
TARGET_START = pd.to_datetime("2014-06-01")
TARGET_END = pd.to_datetime("2014-08-31")
BASELINE_START = pd.to_datetime("1992-01-01")
BASELINE_END = pd.to_datetime("2002-12-31")

def get_doy(dt):
    """Custom day of year mapping: 1 Jan = 1, 28 Feb = 59, 29 Feb = 60, 1 Mar = 61"""
    return pd.Timestamp(2000, dt.month, dt.day).day_of_year

def load_region_sst(start_date, end_date, fs):
    dates = pd.date_range(start_date, end_date)
    sst_list = []
    coords = None
    
    for d in dates:
        filename = f'icsa2027_data_20261101T090944Z/s1z/sst_{d.strftime("%Y%m%d")}.nc'
        try:
            with fs.open(filename, 'rb') as f:
                ds = xr.open_dataset(f, engine='h5netcdf')
                subset = ds.analysed_sst.sel(latitude=slice(LAT_MIN, LAT_MAX), longitude=slice(LON_MIN, LON_MAX))
                if coords is None:
                    coords = {'latitude': ds.latitude.sel(latitude=slice(LAT_MIN, LAT_MAX)),
                              'longitude': ds.longitude.sel(longitude=slice(LON_MIN, LON_MAX))}
                sst_list.append(subset.values.squeeze())
        except Exception as e:
            if coords is None:
                sst_list.append(None)
            else:
                sst_list.append(np.full((coords['latitude'].shape[0], coords['longitude'].shape[0]), np.nan))
    
    if coords is None:
        return None, None, None
    
    sst_array = np.stack(sst_list, axis=0).astype(np.float64)
    return sst_array, coords['latitude'], coords['longitude']

def solve():
    fs = fsspec.filesystem('onedata')
    
    pool_search_start = BASELINE_START - timedelta(days=5)
    pool_search_end = BASELINE_END + timedelta(days=5)
    
    print("Loading baseline data...")
    sst_baseline, lats, lons = load_region_sst(pool_search_start, pool_search_end, fs)
    print("Loading target data...")
    sst_target, _, _ = load_region_sst(TARGET_START, TARGET_END, fs)
    
    if sst_baseline is None or sst_target is None:
        print("Error loading data")
        return

    # 1. Sea cells: finite SST on every day of target period
    is_sea = np.all(np.isfinite(sst_target), axis=0)
    
    # 2. Threshold and climatology
    baseline_dates = pd.date_range(BASELINE_START, BASELINE_END)
    pool_dates = pd.date_range(pool_search_start, pool_search_end)
    
    # Precompute indices for pool dates for each DOY
    doy_to_pool_indices = {d: [] for d in range(1, 367)}
    
    # Optimized mapping: for each pool date P, find which DOY pools it belongs to.
    # P belongs to pool d if |P - B| <= 5 for some baseline date B with DOY(B) == d.
    # Let's stick to the original logic for clarity, but make it efficient.
    baseline_doys = np.array([get_doy(b) for b in baseline_dates])
    
    for d in range(1, 367):
        if d == 60: continue
        # Indices of baseline dates with DOY d
        b_indices = np.where(baseline_doys == d)[0]
        pool_indices = set()
        for b_idx in b_indices:
            # Offset by 5 days (since pool_dates start 5 days before baseline_dates)
            p_center = b_idx + 5
            for offset in range(-5, 6):
                p_idx = p_center + offset
                if 0 <= p_idx < len(pool_dates):
                    pool_indices.add(p_idx)
        doy_to_pool_indices[d] = sorted(list(pool_indices))

    print("Computing thresholds and climatology...")
    thresholds = np.full((367, lats.shape[0], lons.shape[0]), np.nan, dtype=np.float64)
    climatologies = np.full((367, lats.shape[0], lons.shape[0]), np.nan, dtype=np.float64)
    
    for d in range(1, 367):
        if d == 60: continue
        indices = doy_to_pool_indices[d]
        if not indices: continue
        
        pool_data = sst_baseline[indices]
        thresholds[d] = np.nanquantile(pool_data, 0.9, axis=0, method='hazen')
        climatologies[d] = np.nanmean(pool_data, axis=0)
        
    # Day 60 handling
    thresholds[60] = (thresholds[59] + thresholds[61]) / 2
    climatologies[60] = (climatologies[59] + climatologies[61]) / 2
    
    # Smoothing
    def smooth(arr):
        # arr: (367, lat, lon), only indices 1..366 are used
        data = arr[1:] # (366, lat, lon)
        smoothed = np.full((366, lats.shape[0], lons.shape[0]), np.nan, dtype=np.float64)
        for d in range(366):
            indices = [(d + i) % 366 for i in range(-15, 16)]
            smoothed[d] = np.nanmean(data[indices], axis=0)
        return smoothed

    thresholds_smooth = smooth(thresholds)
    
    # 3. Per-cell MHWs
    target_dates = pd.date_range(TARGET_START, TARGET_END)
    target_doys = np.array([get_doy(d) for d in target_dates])
    
    hot_mask = np.zeros(sst_target.shape, dtype=bool)
    for t in range(len(target_dates)):
        doy = target_doys[t]
        hot_mask[t] = sst_target[t] >= thresholds_smooth[doy - 1]
        
    mhw_mask = np.zeros(sst_target.shape, dtype=np.uint8)
    lat_size, lon_size = lats.shape[0], lons.shape[0]
    
    for i in range(lat_size):
        for j in range(lon_size):
            if not is_sea[i, j]:
                continue
            
            cell_hot = hot_mask[:, i, j]
            cell_mhw = np.zeros(len(cell_hot), dtype=bool)
            
            runs = []
            start = None
            for t in range(len(cell_hot)):
                if cell_hot[t]:
                    if start is None: start = t
                else:
                    if start is not None:
                        if t - start >= 5:
                            runs.append((start, t - 1))
                        start = None
            if start is not None:
                if len(cell_hot) - start >= 5:
                    runs.append((start, len(cell_hot) - 1))
            
            if not runs:
                continue
            
            merged_runs = []
            curr_start, curr_end = runs[0]
            for next_start, next_end in runs[1:]:
                if next_start - curr_end - 1 <= 2:
                    curr_end = next_end
                else:
                    merged_runs.append((curr_start, curr_end))
                    curr_start, curr_end = next_start, next_end
            merged_runs.append((curr_start, curr_end))
            
            for start, end in merged_runs:
                cell_mhw[start : end + 1] = True
                
            mhw_mask[:, i, j] = cell_mhw.astype(np.uint8)
            
    # 4. Regional events
    active_days = np.any(mhw_mask == 1, axis=(1, 2))
    regional_events = []
    start = None
    for t in range(len(active_days)):
        if active_days[t]:
            if start is None: start = t
        else:
            if start is not None:
                regional_events.append({"onset": target_dates[start].strftime("%Y-%m-%d"), 
                                        "end": target_dates[t-1].strftime("%Y-%m-%d")})
                start = None
    if start is not None:
        regional_events.append({"onset": target_dates[start].strftime("%Y-%m-%d"), 
                                "end": target_dates[-1].strftime("%Y-%m-%d")})
        
    # Output
    ds_out = xr.Dataset(
        {"mhw": (("time", "latitude", "longitude"), mhw_mask)},
        coords={"time": target_dates, "latitude": lats, "longitude": lons}
    )
    ds_out.to_netcdf("output/mhw_mask.nc")
    
    report = {
        "region": {"lat_min": LAT_MIN, "lat_max": LAT_MAX, "lon_min": LON_MIN, "lon_max": LON_MAX},
        "baseline_analysed": {"start": BASELINE_START.strftime("%Y-%m-%d"), "end": BASELINE_END.strftime("%Y-%m-%d")},
        "target_analysed": {"start": TARGET_START.strftime("%Y-%m-%d"), "end": TARGET_END.strftime("%Y-%m-%d")},
        "events": regional_events,
        "complete": True,
        "caveats": ""
    }
    with open("output/report.json", "w") as f:
        json.dump(report, f)

solve()
