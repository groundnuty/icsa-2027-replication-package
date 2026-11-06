import fsspec
import xarray as xr
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import json
import os

def get_custom_doy(date):
    year = date.year
    month = date.month
    day = date.day
    month_days = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    is_leap = (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)
    doy = sum(month_days[:month-1]) + day
    if is_leap and month > 2:
        doy += 1
    if not is_leap and month > 2:
        return doy + 1
    return doy

def solve():
    fs = fsspec.filesystem('onedata')
    root_dir = 'icsa2027_data_20261101T090944Z/s1z'
    
    lat_min, lat_max = 54.13, 55.33
    lon_min, lon_max = 14.67, 15.87
    
    target_start = pd.Timestamp('2004-06-01')
    target_end = pd.Timestamp('2004-08-31')
    baseline_start = pd.Timestamp('1992-01-01')
    baseline_end = pd.Timestamp('2002-12-31')
    
    data_start = baseline_start - pd.Timedelta(days=5)
    data_end = baseline_end + pd.Timedelta(days=5)
    
    baseline_dates_range = pd.date_range(baseline_start, baseline_end)
    target_dates_range = pd.date_range(target_start, target_end)
    
    # All dates we need to load from files
    # We need the baseline range extended by 5 days, and the target range
    all_needed_dates = sorted(list(set(pd.date_range(data_start, data_end)) | set(target_dates_range)))
    
    # Find existing files
    files = fs.ls(root_dir)
    
    # Load data
    # First, get coordinates
    sample_fpath = f"{root_dir}/sst_{all_needed_dates[0].strftime('%Y%m%d')}.nc"
    with fs.open(sample_fpath, "rb") as f:
        ds_sample = xr.open_dataset(f, engine="h5netcdf")
        subset_sample = ds_sample.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))
        lats = subset_sample.latitude.values
        lons = subset_sample.longitude.values
    
    n_lat = len(lats)
    n_lon = len(lons)
    
    all_sst = np.full((len(all_needed_dates), n_lat, n_lon), np.nan, dtype=np.float64)
    
    for i, date in enumerate(all_needed_dates):
        fname = f"sst_{date.strftime('%Y%m%d')}.nc"
        fpath = f"{root_dir}/{fname}"
        if fpath in files:
            with fs.open(fpath, "rb") as f:
                ds = xr.open_dataset(f, engine="h5netcdf")
                subset = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))
                all_sst[i] = subset.analysed_sst.values[0]
    
    # Identify sea cells (finite SST on every day of target period)
    target_indices = [i for i, d in enumerate(all_needed_dates) if target_start <= d <= target_end]
    target_sst = all_sst[target_indices]
    sea_mask = np.isfinite(target_sst).all(axis=0)
    
    # Thresholds and Climatology
    thresholds = np.full((n_lat, n_lon, 366), np.nan, dtype=np.float64)
    climatology = np.full((n_lat, n_lon, 366), np.nan, dtype=np.float64)
    
    date_to_idx = {d: i for i, d in enumerate(all_needed_dates)}
    
    # Mapping baseline dates to their custom DOY
    baseline_doy_map = {d: get_custom_doy(d) for d in baseline_dates_range}
    
    for d in range(1, 367):
        if d == 60:
            continue
        
        pool_indices = []
        # Find all dates in the baseline with custom DOY d
        baseline_dates_with_d = [d_date for d_date, doy in baseline_doy_map.items() if doy == d]
        
        for base_date in baseline_dates_with_d:
            for offset in range(-5, 6):
                win_date = base_date + pd.Timedelta(days=offset)
                if win_date in date_to_idx:
                    pool_indices.append(date_to_idx[win_date])
        
        if not pool_indices:
            continue
            
        pool_sst = all_sst[pool_indices] # (len(pool), lat, lon)
        
        # Quantile (hazen) and Mean
        # np.nanquantile handles NaNs
        t_vals = np.nanquantile(pool_sst, 0.9, axis=0, method='hazen')
        m_vals = np.nanmean(pool_sst, axis=0)
        
        thresholds[:, :, d-1] = t_vals
        climatology[:, :, d-1] = m_vals
        
    # Day 60 is mean of 59 and 61
    thresholds[:, :, 59] = (thresholds[:, :, 58] + thresholds[:, :, 60]) / 2
    climatology[:, :, 59] = (climatology[:, :, 58] + climatology[:, :, 60]) / 2
    
    # Smoothing: 31-day centered moving mean, wrap around
    def smooth_366(arr):
        smoothed = np.full_like(arr)
        for d in range(366):
            indices = [(d + i) % 366 for i in range(-15, 16)]
            smoothed[:, :, d] = np.nanmean(arr[:, :, indices], axis=-1)
        return smoothed

    thresholds = smooth_366(thresholds)
    climatology = smooth_366(climatology)
    
    # Per-cell MHWs
    mhw_mask = np.zeros((len(target_indices), n_lat, n_lon), dtype=np.uint8)
    
    for lat_idx in range(n_lat):
        for lon_idx in range(n_lon):
            if not sea_mask[lat_idx, lon_idx]:
                continue
            
            cell_sst = target_sst[:, lat_idx, lon_idx]
            
            # Get threshold for each day of the target period
            cell_thresholds = []
            for i in target_indices:
                date = all_needed_dates[i]
                doy = get_custom_doy(date)
                cell_thresholds.append(thresholds[lat_idx, lon_idx, doy-1])
            
            cell_thresholds = np.array(cell_thresholds)
            hot_days = cell_sst >= cell_thresholds
            
            # Find runs of at least 5 consecutive hot days
            is_mhw = np.zeros(len(hot_days), dtype=bool)
            i = 0
            while i < len(hot_days):
                if hot_days[i]:
                    start = i
                    while i < len(hot_days) and hot_days[i]:
                        i += 1
                    if i - start >= 5:
                        is_mhw[start:i] = True
                else:
                    i += 1
            
            # Join gaps of 1 or 2 non-hot days
            while True:
                intervals = []
                i = 0
                while i < len(is_mhw):
                    if is_mhw[i]:
                        start = i
                        while i < len(is_mhw) and is_mhw[i]:
                            i += 1
                        intervals.append([start, i-1])
                    else:
                        i += 1
                
                merged = False
                i = 0
                while i < len(intervals) - 1:
                    # Gap is intervals[i+1][0] - intervals[i][1] - 1
                    if intervals[i+1][0] - intervals[i][1] - 1 <= 2:
                        intervals[i][1] = intervals[i+1][1]
                        intervals.pop(i+1)
                        merged = True
                    else:
                        i += 1
                
                if not merged:
                    break
                
                is_mhw = np.zeros(len(hot_days), dtype=bool)
                for start, end in intervals:
                    is_mhw[start:end+1] = True
            
            mhw_mask[:, lat_idx, lon_idx] = is_mhw.astype(np.uint8)
            
    # Regional events
    active_days = np.any(mhw_mask == 1, axis=(1, 2))
    regional_events = []
    i = 0
    while i < len(active_days):
        if active_days[i]:
            start = i
            while i < len(active_days) and active_days[i]:
                i += 1
            regional_events.append({
                "onset": all_needed_dates[target_indices[start]].strftime('%Y-%m-%d'),
                "end": all_needed_dates[target_indices[i-1]].strftime('%Y-%m-%d')
            })
        else:
            i += 1
            
    # Save results
    os.makedirs('output', exist_ok=True)
    ds_out = xr.Dataset(
        {"mhw": (["time", "latitude", "longitude"], mhw_mask)},
        coords={
            "time": [all_needed_dates[i] for i in target_indices],
            "latitude": lats,
            "longitude": lons
        }
    )
    ds_out.to_netcdf('output/mhw_mask.nc')
    
    report = {
        "region": {"lat_min": lat_min, "lat_max": lat_max, "lon_min": lon_min, "lon_max": lon_max},
        "baseline_analysed": {
            "start": data_start.strftime('%Y-%m-%d'),
            "end": data_end.strftime('%Y-%m-%d')
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
        json.dump(report, f)

solve()
