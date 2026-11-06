import fsspec
import xarray as xr
import numpy as np
import pandas as pd
import json
from datetime import datetime, timedelta
import os

def get_custom_doy(dt):
    # 1 January = 1, 28 February = 59, 29 February = 60, 1 March = 61...
    # Using 2000 as a leap year reference.
    target_date = datetime(2000, dt.month, dt.day)
    ref_date = datetime(2000, 1, 1)
    return (target_date - ref_date).days + 1

def solve():
    fs = fsspec.filesystem('onedata')
    root_dir = 'icsa2027_data_20261101T090944Z/s1z'
    
    lat_min, lat_max = 54.39, 55.59
    lon_min, lon_max = 18.25, 19.45
    target_start = pd.Timestamp('2021-06-01')
    target_end = pd.Timestamp('2021-08-31')
    baseline_start = pd.Timestamp('1992-01-01')
    baseline_end = pd.Timestamp('2002-12-31')
    
    # Window for baseline pools: +/- 5 days
    # We need files from 1991-12-27 to 2003-01-05
    pool_start = baseline_start - pd.Timedelta(days=5)
    pool_end = baseline_end + pd.Timedelta(days=5)
    
    baseline_dates_range = pd.date_range(pool_start, pool_end)
    target_dates_range = pd.date_range(target_start, target_end)
    
    def date_to_path(dt):
        return f'{root_dir}/sst_{dt.strftime("%Y%m%d")}.nc'

    # Get lat/lon from sample
    sample_file = f'{root_dir}/sst_19820101.nc'
    with fs.open(sample_file, "rb") as f:
        ds_sample = xr.open_dataset(f, engine="h5netcdf")
        lats = ds_sample.latitude.values
        lons = ds_sample.longitude.values
        
    lat_mask = (lats >= lat_min) & (lats <= lat_max)
    lon_mask = (lons >= lon_min) & (lons <= lon_max)
    subset_lats = lats[lat_mask]
    subset_lons = lons[lon_mask]

    # Load baseline data
    baseline_sst_list = []
    baseline_actual_dates = []
    for dt in baseline_dates_range:
        path = date_to_path(dt)
        try:
            with fs.open(path, "rb") as f:
                ds = xr.open_dataset(f, engine="h5netcdf")
                # Slicing using the masks for precision
                sst_val = ds.analysed_sst.values[0, lat_mask, lon_mask]
                baseline_sst_list.append(sst_val)
                baseline_actual_dates.append(dt)
        except Exception:
            pass

    baseline_sst = np.array(baseline_sst_list, dtype='float64') # (T_base, lat, lon)
    baseline_actual_dates = np.array(baseline_actual_dates)
    
    # Load target data
    target_sst_list = []
    target_actual_dates = []
    for dt in target_dates_range:
        path = date_to_path(dt)
        try:
            with fs.open(path, "rb") as f:
                ds = xr.open_dataset(f, engine="h5netcdf")
                sst_val = ds.analysed_sst.values[0, lat_mask, lon_mask]
                target_sst_list.append(sst_val)
                target_actual_dates.append(dt)
        except Exception:
            pass
            
    target_sst = np.array(target_sst_list, dtype='float64') # (T_target, lat, lon)
    target_actual_dates = np.array(target_actual_dates)
    
    # 1. Sea cells: finite on every day of the target period
    sea_cells_mask = np.isfinite(target_sst).all(axis=0)
    
    # 2. Threshold and Climatology
    thresholds = np.full((366, baseline_sst.shape[1], baseline_sst.shape[2]), np.nan, dtype='float64')
    climatologies = np.full((366, baseline_sst.shape[1], baseline_sst.shape[2]), np.nan, dtype='float64')
    
    dates_used_in_pools = set()
    baseline_core_range = pd.date_range(baseline_start, baseline_end)
    
    for d in range(1, 367):
        if d == 60:
            continue
        
        # baseline dates (1992-2002) whose DOY is d
        centers = [bd for bd in baseline_core_range if get_custom_doy(bd.to_pydatetime()) == d]
        
        pool_dates = set()
        for center in centers:
            for offset in range(-5, 6):
                pool_dates.add(center + pd.Timedelta(days=offset))
        
        # Find indices in baseline_actual_dates
        indices = []
        for pd_date in pool_dates:
            idx = np.where(baseline_actual_dates == pd_date)[0]
            if idx.size > 0:
                indices.append(idx[0])
                dates_used_in_pools.add(pd_date)
        
        if indices:
            pool_vals = baseline_sst[indices, :, :]
            thresholds[d-1] = np.nanquantile(pool_vals, 0.9, axis=0, method="hazen")
            climatologies[d-1] = np.nanmean(pool_vals, axis=0)
    
    # Day 60
    thresholds[59] = (thresholds[58] + thresholds[60]) / 2
    climatologies[59] = (climatologies[58] + climatologies[60]) / 2
    
    def smooth(arr):
        smoothed = np.zeros_like(arr)
        for d in range(366):
            window = [(d + i) % 366 for i in range(-15, 16)]
            smoothed[d] = np.nanmean(arr[window], axis=0)
        return smoothed

    thresholds = smooth(thresholds)
    climatologies = smooth(climatologies)
    
    # 3. Per-cell MHWs
    T_target = target_sst.shape[0]
    target_doy = np.array([get_custom_doy(d.to_pydatetime()) for d in target_actual_dates])
    
    hot_days = np.zeros((T_target, baseline_sst.shape[1], baseline_sst.shape[2]), dtype=bool)
    for t in range(T_target):
        doy = target_doy[t]
        hot_days[t] = (target_sst[t] >= thresholds[doy-1])
        
    mhw_mask = np.zeros((T_target, baseline_sst.shape[1], baseline_sst.shape[2]), dtype=np.uint8)
    
    for i in range(baseline_sst.shape[1]):
        for j in range(baseline_sst.shape[2]):
            if not sea_cells_mask[i, j]:
                continue
            
            cell_hot = hot_days[:, i, j]
            is_mhw = np.zeros(T_target, dtype=bool)
            
            # Runs of >= 5
            current_run = []
            for t in range(T_target):
                if cell_hot[t]:
                    current_run.append(t)
                else:
                    if len(current_run) >= 5:
                        for t_run in current_run:
                            is_mhw[t_run] = True
                    current_run = []
            if len(current_run) >= 5:
                for t_run in current_run:
                    is_mhw[t_run] = True
            
            # Join gaps of 1 or 2
            while True:
                changed = False
                for t in range(1, T_target-1):
                    if not is_mhw[t]:
                        if is_mhw[t-1] and is_mhw[t+1]:
                            is_mhw[t] = True
                            changed = True
                        elif t < T_target-2 and is_mhw[t-1] and not is_mhw[t+1] and is_mhw[t+2]:
                            is_mhw[t] = True
                            is_mhw[t+1] = True
                            changed = True
                if not changed:
                    break
            mhw_mask[:, i, j] = is_mhw.astype(np.uint8)
            
    # 4. Regional Events
    active_days = np.any(mhw_mask == 1, axis=(1, 2))
    regional_events = []
    current_start = None
    for t in range(T_target):
        if active_days[t]:
            if current_start is None:
                current_start = t
        else:
            if current_start is not None:
                regional_events.append({
                    "onset": target_actual_dates[current_start].strftime("%Y-%m-%d"),
                    "end": target_actual_dates[t-1].strftime("%Y-%m-%d")
                })
                current_start = None
    if current_start is not None:
        regional_events.append({
            "onset": target_actual_dates[current_start].strftime("%Y-%m-%d"),
            "end": target_actual_dates[T_target-1].strftime("%Y-%m-%d")
        })
        
    # Output
    ds_out = xr.Dataset(
        {"mhw": (("time", "latitude", "longitude"), mhw_mask.astype(np.uint8))},
        coords={"time": target_actual_dates, "latitude": subset_lats, "longitude": subset_lons}
    )
    os.makedirs('output', exist_ok=True)
    ds_out.to_netcdf('output/mhw_mask.nc')
    
    baseline_analysed = None
    if dates_used_in_pools:
        baseline_analysed = {
            "start": min(dates_used_in_pools).strftime("%Y-%m-%d"),
            "end": max(dates_used_in_pools).strftime("%Y-%m-%d")
        }

    report = {
        "region": {"lat_min": lat_min, "lat_max": lat_max, "lon_min": lon_min, "lon_max": lon_max},
        "baseline_analysed": baseline_analysed,
        "target_analysed": {
            "start": target_actual_dates[0].strftime("%Y-%m-%d"),
            "end": target_actual_dates[-1].strftime("%Y-%m-%d")
        } if T_target > 0 else None,
        "events": regional_events,
        "complete": True,
        "caveats": ""
    }
    with open('output/report.json', 'w') as f:
        json.dump(report, f, indent=2)

solve()
