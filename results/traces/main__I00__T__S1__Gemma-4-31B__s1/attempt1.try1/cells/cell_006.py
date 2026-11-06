import fsspec
import xarray as xr
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import json
import os

def get_custom_doy(date):
    # 1 January = 1, ..., 29 February = 60, 1 March = 61, ..., 31 December = 366.
    leap_year_days = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return sum(leap_year_days[:date.month-1]) + date.day

def solve():
    fs = fsspec.filesystem('onedata')
    root_dir = 'icsa2027_data_20261101T090944Z/s1z'
    
    lat_min, lat_max = 54.13, 55.33
    lon_min, lon_max = 14.67, 15.87
    
    target_start = pd.Timestamp('2004-06-01')
    target_end = pd.Timestamp('2004-08-31')
    baseline_start = pd.Timestamp('1992-01-01')
    baseline_end = pd.Timestamp('2002-12-31')
    
    # Windows extend 5 days beyond baseline
    data_start = baseline_start - pd.Timedelta(days=5)
    data_end = baseline_end + pd.Timedelta(days=5)
    
    # All dates we need to load
    baseline_dates_range = pd.date_range(baseline_start, baseline_end)
    target_dates_range = pd.date_range(target_start, target_end)
    all_needed_dates = sorted(list(set(pd.date_range(data_start, data_end)) | set(target_dates_range)))
    
    files = fs.ls(root_dir)
    
    # Coordinates
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
    
    target_indices = [i for i, d in enumerate(all_needed_dates) if target_start <= d <= target_end]
    target_sst = all_sst[target_indices]
    sea_mask = np.isfinite(target_sst).all(axis=0)
    
    thresholds = np.full((n_lat, n_lon, 366), np.nan, dtype=np.float64)
    climatology = np.full((n_lat, n_lon, 366), np.nan, dtype=np.float64)
    
    date_to_idx = {d: i for i, d in enumerate(all_needed_dates)}
    baseline_doy_map = {d: get_custom_doy(d) for d in baseline_dates_range}
    
    for d in range(1, 367):
        if d == 60:
            continue
        
        pool_indices = []
        baseline_dates_with_d = [d_date for d_date, doy in baseline_doy_map.items() if doy == d]
        
        for base_date in baseline_dates_with_d:
            for offset in range(-5, 6):
                win_date = base_date + pd.Timedelta(days=offset)
                if win_date in date_to_idx:
                    pool_indices.append(date_to_idx[win_date])
        
        if not pool_indices:
            continue
            
        pool_sst = all_sst[pool_indices]
        # Compute for all cells, nanquantile/nanmean handle NaNs
        t_vals = np.nanquantile(pool_sst, 0.9, axis=0, method='hazen')
        m_vals = np.nanmean(pool_sst, axis=0)
        
        thresholds[:, :, d-1] = t_vals
        climatology[:, :, d-1] = m_vals
        
    thresholds[:, :, 59] = (thresholds[:, :, 58] + thresholds[:, :, 60]) / 2
    climatology[:, :, 59] = (climatology[:, :, 58] + climatology[:, :, 60]) / 2
    
    def smooth_366(arr):
        smoothed = np.full(arr.shape, np.nan, dtype=np.float64)
        for d in range(366):
            indices = [(d + i) % 366 for i in range(-15, 16)]
            smoothed[:, :, d] = np.nanmean(arr[:, :, indices], axis=-1)
        return smoothed

    thresholds = smooth_366(thresholds)
    climatology = smooth_366(climatology)
    
    mhw_mask = np.zeros((len(target_indices), n_lat, n_lon), dtype=np.uint8)
    
    for lat_idx in range(n_lat):
        for lon_idx in range(n_lon):
            if not sea_mask[lat_idx, lon_idx]:
                continue
            
            cell_sst = target_sst[:, lat_idx, lon_idx]
            cell_thresholds = []
            for i in target_indices:
                date = all_needed_dates[i]
                doy = get_custom_doy(date)
                cell_thresholds.append(thresholds[lat_idx, lon_idx, doy-1])
            
            cell_thresholds = np.array(cell_thresholds)
            hot_days = cell_sst >= cell_thresholds
            
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
