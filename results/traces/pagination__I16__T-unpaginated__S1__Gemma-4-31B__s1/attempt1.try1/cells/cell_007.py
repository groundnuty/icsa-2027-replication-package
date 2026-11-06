import numpy as np
import pandas as pd
import xarray as xr
import fsspec
import json
import os
from datetime import datetime, timedelta

def solve():
    # Setup
    fs = fsspec.filesystem('onedata')
    base_path = 'icsa2027_data_20261101T090944Z/s1z'
    
    lat_min, lat_max = 56.63, 57.83
    lon_min, lon_max = 20.23, 21.43
    target_start = pd.to_datetime('2008-06-01')
    target_end = pd.to_datetime('2008-08-31')
    baseline_start = pd.to_datetime('1992-01-01')
    baseline_end = pd.to_datetime('2002-12-31')

    # Determine all dates needed
    min_baseline_date = baseline_start - timedelta(days=5)
    max_baseline_date = baseline_end + timedelta(days=5)
    
    needed_dates = set()
    needed_dates.update(pd.date_range(min_baseline_date, max_baseline_date))
    needed_dates.update(pd.date_range(target_start, target_end))
    
    all_files_set = set(fs.ls(base_path))
    final_needed_dates = []
    for dt in sorted(list(needed_dates)):
        filename = f"sst_{dt.strftime('%Y%m%d')}.nc"
        path = f"{base_path}/{filename}"
        if path in all_files_set:
            final_needed_dates.append(dt)
    
    # Load coordinate indices from first available file
    first_file = sorted(list(all_files_set))[0]
    with fs.open(first_file, 'rb') as f:
        ds_sample = xr.open_dataset(f, engine='h5netcdf')
        lat_idx = np.where((ds_sample.latitude >= lat_min) & (ds_sample.latitude <= lat_max))[0]
        lon_idx = np.where((ds_sample.longitude >= lon_min) & (ds_sample.longitude <= lon_max))[0]
        lats = ds_sample.latitude.values[lat_idx]
        lons = ds_sample.longitude.values[lon_idx]
        
    # Load data
    sst_data = []
    loaded_dates = []
    for dt in final_needed_dates:
        filename = f"sst_{dt.strftime('%Y%m%d')}.nc"
        path = f"{base_path}/{filename}"
        with fs.open(path, 'rb') as f:
            ds = xr.open_dataset(f, engine='h5netcdf')
            sst_slice = ds.analysed_sst.isel(latitude=slice(lat_idx[0], lat_idx[-1]+1), 
                                             longitude=slice(lon_idx[0], lon_idx[-1]+1))
            sst_data.append(sst_slice.values[0])
            loaded_dates.append(dt)
            
    sst_array = np.array(sst_data, dtype='float64') 
    loaded_dates = np.array(loaded_dates)
    
    # 1. Sea cells
    target_mask = (loaded_dates >= target_start) & (loaded_dates <= target_end)
    sst_target = sst_array[target_mask]
    is_finite = np.isfinite(sst_target)
    sea_cells_mask = np.all(is_finite, axis=0) 
    
    # 2. Threshold and Climatology
    # Use extended baseline range for the pool
    extended_baseline_mask = (loaded_dates >= min_baseline_date) & (loaded_dates <= max_baseline_date)
    sst_ext = sst_array[extended_baseline_mask]
    dates_ext = loaded_dates[extended_baseline_mask]
    
    date_to_idx = {dt: i for i, dt in enumerate(dates_ext)}
    
    thresholds = np.full((366, sst_array.shape[1], sst_array.shape[2]), np.nan, dtype='float64')
    climatologies = np.full((366, sst_array.shape[1], sst_array.shape[2]), np.nan, dtype='float64')
    
    baseline_years = range(1992, 2003)
    
    for d in range(1, 367):
        if d == 60:
            continue
        
        pool_indices = []
        for year in baseline_years:
            try:
                # Date T in year with doy=d
                T = pd.Timestamp(year=year, month=1, day=1) + pd.Timedelta(days=d-1)
                if T.dayofyear == d:
                    for offset in range(-5, 6):
                        T_prime = T + pd.Timedelta(days=offset)
                        if T_prime in date_to_idx:
                            pool_indices.append(date_to_idx[T_prime])
            except Exception:
                continue
        
        if pool_indices:
            pool_vals = sst_ext[pool_indices] 
            thresholds[d-1] = np.nanpercentile(pool_vals, 90, axis=0, method='hazen')
            climatologies[d-1] = np.nanmean(pool_vals, axis=0)

    # Day 60 mean of 59 and 61
    thresholds[59] = (thresholds[58] + thresholds[60]) / 2
    climatologies[59] = (climatologies[58] + climatologies[60]) / 2
    
    def smooth_366(arr):
        smoothed = np.zeros_like(arr)
        for d in range(366):
            indices = [(d + offset) % 366 for offset in range(-15, 16)]
            smoothed[d] = np.nanmean(arr[indices], axis=0)
        return smoothed
    
    thresholds_smooth = smooth_366(thresholds)
    climatologies_smooth = smooth_366(climatologies)
    
    # 3. Per-cell MHWs
    sst_target = sst_array[target_mask] 
    target_dates = loaded_dates[target_mask]
    target_doys = np.array([dt.dayofyear for dt in target_dates])
    target_thresholds = thresholds_smooth[target_doys - 1]
    
    hot_mask = (sst_target >= target_thresholds)
    hot_mask = hot_mask & sea_cells_mask[np.newaxis, :, :]
    
    mhw_mask = np.zeros_like(hot_mask, dtype='uint8')
    
    for i in range(sst_array.shape[1]):
        for j in range(sst_array.shape[2]):
            if not sea_cells_mask[i, j]:
                continue
            
            cell_hot = hot_mask[:, i, j]
            is_mhw = np.zeros(len(cell_hot), dtype=bool)
            
            # Run of at least 5
            run_start = None
            for t in range(len(cell_hot)):
                if cell_hot[t]:
                    if run_start is None:
                        run_start = t
                else:
                    if run_start is not None:
                        if t - run_start >= 5:
                            is_mhw[run_start:t] = True
                        run_start = None
            if run_start is not None:
                if len(cell_hot) - run_start >= 5:
                    is_mhw[run_start:] = True
            
            # Join gaps
            changed = True
            while changed:
                changed = False
                for t in range(1, len(is_mhw) - 1):
                    if not is_mhw[t]:
                        if is_mhw[t-1] and is_mhw[t+1]:
                            is_mhw[t] = True
                            changed = True
                        elif t < len(is_mhw) - 2 and is_mhw[t-1] and not is_mhw[t+1] and is_mhw[t+2]:
                            is_mhw[t] = True
                            is_mhw[t+1] = True
                            changed = True
            mhw_mask[:, i, j] = is_mhw.astype('uint8')
            
    # 4. Regional Events
    active_days = np.any(mhw_mask == 1, axis=(1, 2))
    events = []
    run_start = None
    for t in range(len(active_days)):
        if active_days[t]:
            if run_start is None:
                run_start = t
        else:
            if run_start is not None:
                events.append({
                    "onset": target_dates[run_start].strftime('%Y-%m-%d'),
                    "end": target_dates[t-1].strftime('%Y-%m-%d')
                })
                run_start = None
    if run_start is not None:
        events.append({
            "onset": target_dates[run_start].strftime('%Y-%m-%d'),
            "end": target_dates[-1].strftime('%Y-%m-%d')
        })
    
    os.makedirs('output', exist_ok=True)
    mask_ds = xr.Dataset(
        {"mhw": (("time", "latitude", "longitude"), mhw_mask)},
        coords={"time": target_dates, "latitude": lats, "longitude": lons}
    )
    mask_ds.to_netcdf('output/mhw_mask.nc')
    
    baseline_used_dates = [dt for dt in final_needed_dates if dt <= max_baseline_date]
    report = {
        "region": {"lat_min": lat_min, "lat_max": lat_max, "lon_min": lon_min, "lon_max": lon_max},
        "baseline_analysed": {
            "start": baseline_used_dates[0].strftime('%Y-%m-%d') if baseline_used_dates else None,
            "end": baseline_used_dates[-1].strftime('%Y-%m-%d') if baseline_used_dates else None
        } if baseline_used_dates else None,
        "target_analysed": {
            "start": target_dates[0].strftime('%Y-%m-%d') if len(target_dates) > 0 else None,
            "end": target_dates[-1].strftime('%Y-%m-%d') if len(target_dates) > 0 else None
        },
        "events": events,
        "complete": True,
        "caveats": ""
    }
    with open('output/report.json', 'w') as f:
        json.dump(report, f, indent=2)

solve()
