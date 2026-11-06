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
    return pd.Timestamp(2000, dt.month, dt.day).dayofyear

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
                sst_list.append(np.full(coords['latitude'].shape[0] * coords['longitude'].shape[0], np.nan).reshape(coords['latitude'].shape[0], coords['longitude'].shape[0]))
    
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
    # sst_target shape: (time, lat, lon)
    is_sea = np.all(np.isfinite(sst_target), axis=0)
    
    # 2. Threshold and climatology
    # Baseline dates
    baseline_dates = pd.date_range(BASELINE_START, BASELINE_END)
    # pool_search_dates
    pool_dates = pd.date_range(pool_search_start, pool_search_end)
    pool_doy = np.array([get_doy(d) for d in pool_dates])
    
    # Baseline pool: +/- 5 calendar days of a baseline date
    # For each DOY d (1..366, except 60)
    # Pool is every SST value whose date lies within +/- 5 calendar days of a baseline date with DOY d.
    # Wait, let's re-read: "the pool is every SST value whose date lies within ±5 calendar days of a baseline date... whose day of year is d."
    # This means for a fixed d, we find all baseline dates B with get_doy(B) == d.
    # Then we find all pool_dates P such that dist(P, B) <= 5 for at least one such B.
    
    # Precompute indices for pool dates
    pool_sst = sst_baseline # (time, lat, lon)
    
    thresholds = np.full((367, lats.shape[0], lons.shape[0]), np.nan, dtype=np.float64)
    climatologies = np.full((367, lats.shape[0], lons.shape[0]), np.nan, dtype=np.float64)
    
    # Optimization: map pool dates to their distance from any baseline date of DOY d
    # Actually, a simpler way: for each pool date P, it contributes to the pool of DOY d if 
    # there exists a baseline date B with get_doy(B) == d and |P-B| <= 5.
    
    # Let's pre-calculate which pool dates belong to which DOY pool.
    doy_to_pool_indices = {d: [] for d in range(1, 367)}
    for d in range(1, 367):
        if d == 60: continue
        # Find all baseline dates B with DOY d
        baseline_indices = np.where(np.array([get_doy(b) for b in baseline_dates]) == d)[0]
        # Baseline dates are indexed 0 to len(baseline_dates)-1. 
        # Pool dates start 5 days before.
        # A pool date P (index p) is within 5 days of B (index b) if |p - (b + 5)| <= 5.
        # Wait, pool_dates[0] is BASELINE_START - 5 days. baseline_dates[0] is BASELINE_START.
        # So pool_dates[5] == baseline_dates[0].
        # Offset is 5.
        pool_indices = []
        for b_idx in baseline_indices:
            p_start = max(0, b_idx + 5 - 5)
            p_end = min(len(pool_dates) - 1, b_idx + 5 + 5)
            pool_indices.extend(range(p_start, p_end + 1))
        doy_to_pool_indices[d] = sorted(list(set(pool_indices)))

    print("Computing thresholds and climatology...")
    for d in range(1, 367):
        if d == 60: continue
        indices = doy_to_pool_indices[d]
        if not indices: continue
        
        # Extract data for this DOY pool: (len(indices), lat, lon)
        pool_data = pool_sst[indices]
        
        # Compute 90th percentile and mean along the time axis
        # Use nanquantile and nanmean
        thresholds[d] = np.nanquantile(pool_data, 0.9, axis=0, method='hazen')
        climatologies[d] = np.nanmean(pool_data, axis=0)
        
    # Day 60 handling
    thresholds[60] = (thresholds[59] + thresholds[61]) / 2
    climatologies[60] = (climatologies[59] + climatologies[61]) / 2
    
    # Smoothing: 31-day moving mean (centered, wrap around)
    def smooth(arr):
        # arr: (367, lat, lon)
        # We only care about 1..366
        data = arr[1:] # (366, lat, lon)
        smoothed = np.full_like(data)
        for d in range(366):
            # Days d-15 to d+15 modulo 366
            # d is 0-indexed here, so it corresponds to DOY d+1.
            # The range is [d-15, d+15]
            indices = [(d + i) % 366 for i in range(-15, 16)]
            smoothed[d] = np.nanmean(data[indices], axis=0)
        return smoothed

    thresholds_smooth = smooth(thresholds)
    climatologies_smooth = smooth(climatologies)
    
    # 3. Per-cell MHWs
    # sst_target: (time, lat, lon)
    # target_doy: (time,)
    target_dates = pd.date_range(TARGET_START, TARGET_END)
    target_doys = np.array([get_doy(d) for d in target_dates])
    
    # Hot days: SST >= threshold
    # thresholds_smooth is indexed 0..365 (corresponding to DOY 1..366)
    hot_mask = np.zeros(sst_target.shape, dtype=bool)
    for t in range(len(target_dates)):
        doy = target_doys[t]
        hot_mask[t] = sst_target[t] >= thresholds_smooth[doy - 1]
        
    # MHW mask for each cell
    mhw_mask = np.zeros(sst_target.shape, dtype=np.uint8)
    
    # Process each sea cell
    lat_size, lon_size = lats.shape[0], lons.shape[0]
    for i in range(lat_size):
        for j in range(lon_size):
            if not is_sea[i, j]:
                continue
            
            cell_hot = hot_mask[:, i, j]
            # Find runs of >= 5 hot days
            # Joining gaps of 1 or 2 non-hot days
            # Logic: 
            # 1. Identify hot runs
            # 2. If two hot runs are separated by 1 or 2 days, merge them.
            
            # a simple way to implement this:
            # - Use a boolean array 'mhw_cell'
            # - First pass: identify all runs of 5+
            # - Second pass: merge runs with gaps <= 2
            
            # Wait, the rule is: "a per-cell MHW is a run of at least 5 consecutive hot days; per-cell MHWs separated by 1 or 2 non-hot days are joined into one"
            # This implies:
            # 1. Initial MHWs are blocks of 5+ hot days.
            # 2. Then we merge these blocks if the gap between them is <= 2.
            # 3. The gap days also become part of the MHW.
            
            cell_mhw = np.zeros(len(cell_hot), dtype=bool)
            
            # Find all runs of 5+
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
            
            # Merge runs with gaps <= 2
            merged_runs = []
            if runs:
                curr_start, curr_end = runs[0]
                for i in range(1, len(runs)):
                    next_start, next_end = runs[i]
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
    # a day is active if at least one sea cell is inside a per-cell MHW
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
        
    # Output NetCDF
    ds_out = xr.Dataset(
        {"mhw": (("time", "latitude", "longitude"), mhw_mask)},
        coords={"time": target_dates, "latitude": lats, "longitude": lons}
    )
    ds_out.to_netcdf("output/mhw_mask.nc")
    
    # Output JSON
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
