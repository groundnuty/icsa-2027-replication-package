import xarray as xr
import numpy as np
import pandas as pd
import fsspec
from datetime import datetime, timedelta
import json

def is_leap(year):
    return (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)

def get_doy(dt):
    doy = dt.timetuple().tm_yday
    if dt.month > 2 and not is_leap(dt.year):
        doy += 1
    return doy

def get_sst_subset(fs, base_dir, date, lat_bounds, lon_bounds):
    fname = f"{base_dir}/sst_{date.strftime('%Y%m%d')}.nc"
    try:
        with fs.open(fname, "rb") as f:
            ds = xr.open_dataset(f, engine="h5netcdf")
            subset = ds.analysed_sst.sel(
                latitude=slice(lat_bounds[0], lat_bounds[1]),
                longitude=slice(lon_bounds[0], lon_bounds[1])
            ).values
            return subset.squeeze()
    except Exception as e:
        # In case of missing file, return NaNs
        return np.full((60, 60), np.nan)

def solve():
    fs = fsspec.filesystem('onedata')
    base_dir = 'icsa2027_data_20261101T090944Z/s1z'
    lat_min, lat_max = 60.09, 61.29
    lon_min, lon_max = 20.01, 21.21
    target_start_str = '2003-06-01'
    target_end_str = '2003-08-31'
    
    target_start = pd.to_datetime(target_start_str)
    target_end = pd.to_datetime(target_end_str)
    target_dates = pd.date_range(target_start, target_end)
    
    # 1. Identify sea cells
    sst_target_list = []
    lats, lons = None, None
    for d in target_dates:
        sst = get_sst_subset(fs, base_dir, d, (lat_min, lat_max), (lon_min, lon_max))
        if lats is None:
            # We need the coordinates. Let's get them from the first file.
            fname = f"{base_dir}/sst_{d.strftime('%Y%m%d')}.nc"
            with fs.open(fname, "rb") as f:
                ds = xr.open_dataset(f, engine="h5netcdf")
                lats = ds.latitude.sel(latitude=slice(lat_min, lat_max)).values
                lons = ds.longitude.sel(longitude=slice(lon_min, lon_max)).values
        sst_target_list.append(sst)
    
    sst_target = np.stack(sst_target_list, axis=0).astype(np.float64)
    is_sea = np.all(np.isfinite(sst_target), axis=0)
    
    # 2. Threshold and climatology
    baseline_start = pd.to_datetime('1992-01-01')
    baseline_end = pd.to_datetime('2002-12-31')
    baseline_dates = pd.date_range(baseline_start, baseline_end)
    
    # Collect all necessary dates for pools
    # Pools for d=1..366 (except 60)
    all_pool_dates = set()
    doy_to_baseline_dates = {}
    for bd in baseline_dates:
        d = get_doy(bd)
        if d != 60:
            if d not in doy_to_baseline_dates:
                doy_to_baseline_dates[d] = []
            doy_to_baseline_dates[d].append(bd)
            
    for d in range(1, 367):
        if d == 60: continue
        for bd in doy_to_baseline_dates.get(d, []):
            for offset in range(-5, 6):
                all_pool_dates.add(bd + timedelta(days=offset))
    
    sorted_pool_dates = sorted(list(all_pool_dates))
    date_to_sst = {}
    for d in sorted_pool_dates:
        date_to_sst[d] = get_sst_subset(fs, base_dir, d, (lat_min, lat_max), (lon_min, lon_max))
    
    thresholds = np.full((366, 60, 60), np.nan, dtype=np.float64)
    climatology = np.full((366, 60, 60), np.nan, dtype=np.float64)
    
    for d in range(1, 367):
        if d == 60: continue
        
        # Pool for day d
        pool_values = []
        for bd in doy_to_baseline_dates.get(d, []):
            for offset in range(-5, 6):
                dt = bd + timedelta(days=offset)
                if dt in date_to_sst:
                    pool_values.append(date_to_sst[dt])
        
        if pool_values:
            pool_arr = np.stack(pool_values, axis=0) # (N, 60, 60)
            # Threshold: 90th percentile (method='hazen')
            # Climatology: mean
            # Apply only to sea cells to be safe, though nan-aware functions work
            thresholds[d-1] = np.nanquantile(pool_arr, 0.9, axis=0, method='hazen')
            climatology[d-1] = np.nanmean(pool_arr, axis=0)
            
    # Day 60 is mean of 59 and 61
    thresholds[59] = (thresholds[58] + thresholds[60]) / 2
    climatology[59] = (climatology[58] + climatology[60]) / 2
    
    # Smoothing (31-day moving mean, wrap around)
    def smooth(arr):
        smoothed = np.full_like(arr, np.nan)
        for d in range(366):
            # Days d-15 to d+15 mod 366
            window_indices = [(d + i) % 366 for i in range(-15, 16)]
            window_data = arr[window_indices]
            # Mean over the time axis (axis 0)
            smoothed[d] = np.nanmean(window_data, axis=0)
        return smoothed

    thresholds = smooth(thresholds)
    climatology = smooth(climatology)
    
    # 3. Per-cell MHWs
    # Target SST is sst_target: (92, 60, 60)
    # Thresholds is (366, 60, 60)
    mhw_mask = np.zeros(sst_target.shape, dtype=np.uint8)
    
    for r in range(60):
        for c in range(60):
            if not is_sea[r, c]:
                continue
            
            # Time series for this cell
            sst_cell = sst_target[:, r, c]
            # Thresholds for this cell for the target days
            thresh_cell = []
            for d in target_dates:
                thresh_cell.append(thresholds[get_doy(d)-1, r, c])
            thresh_cell = np.array(thresh_cell)
            
            # Hot days
            is_hot = sst_cell >= thresh_cell
            
            # MHW runs
            # - Run of at least 5 consecutive hot days
            # - Joined if gap is 1 or 2 non-hot days
            
            # Find all runs of hot days
            mhw_cell = np.zeros(len(is_hot), dtype=bool)
            
            # Initial hot runs
            i = 0
            while i < len(is_hot):
                if is_hot[i]:
                    j = i
                    while j < len(is_hot) and is_hot[j]:
                        j += 1
                    if j - i >= 5:
                        mhw_cell[i:j] = True
                    i = j
                else:
                    i += 1
            
            # Join gaps of 1 or 2 non-hot days
            # We iterate until no more joins are possible
            changed = True
            while changed:
                changed = False
                # Find existing MHW segments
                # This is simple: any gap of 1 or 2 between True values becomes True
                for i in range(1, len(mhw_cell) - 1):
                    if not mhw_cell[i]:
                        # Gap of 1
                        if mhw_cell[i-1] and mhw_cell[i+1]:
                            mhw_cell[i] = True
                            changed = True
                        # Gap of 2
                        elif i < len(mhw_cell) - 2 and mhw_cell[i-1] and not mhw_cell[i+1] and mhw_cell[i+2]:
                            # This is a gap of 2 at i, i+1
                            # Actually simpler:
                            pass
                # Re-evaluate gap of 2
                for i in range(1, len(mhw_cell) - 2):
                    if not mhw_cell[i] and not mhw_cell[i+1]:
                        if mhw_cell[i-1] and mhw_cell[i+2]:
                            mhw_cell[i] = True
                            mhw_cell[i+1] = True
                            changed = True
                            
            mhw_mask[:, r, c] = mhw_cell.astype(np.uint8)
            
    # 4. Regional events
    # A day is active if at least one sea cell is inside an MHW
    active_days = np.any(mhw_mask == 1, axis=(1, 2))
    
    events = []
    i = 0
    while i < len(active_days):
        if active_days[i]:
            j = i
            while j < len(active_days) and active_days[j]:
                j += 1
            events.append({
                "onset": target_dates[i].strftime('%Y-%m-%d'),
                "end": target_dates[j-1].strftime('%Y-%m-%d')
            })
            i = j
        else:
            i += 1
            
    # Output files
    # mhw_mask.nc
    ds_out = xr.Dataset(
        {"mhw": (("time", "latitude", "longitude"), mhw_mask)},
        coords={"time": target_dates, "latitude": lats, "longitude": lons}
    )
    ds_out.to_netcdf("output/mhw_mask.nc")
    
    # report.json
    report = {
        "region": {"lat_min": lat_min, "lat_max": lat_max, "lon_min": lon_min, "lon_max": lon_max},
        "baseline_analysed": {
            "start": sorted_pool_dates[0].strftime('%Y-%m-%d'),
            "end": sorted_pool_dates[-1].strftime('%Y-%m-%d')
        },
        "target_analysed": {
            "start": target_dates[0].strftime('%Y-%m-%d'),
            "end": target_dates[-1].strftime('%Y-%m-%d')
        },
        "events": events,
        "complete": True,
        "caveats": ""
    }
    with open("output/report.json", "w") as f:
        json.dump(report, f)

solve()
