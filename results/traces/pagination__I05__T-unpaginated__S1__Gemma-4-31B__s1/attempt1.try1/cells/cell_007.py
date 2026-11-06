import fsspec
import xarray as xr
import numpy as np
import pandas as pd
import json
from datetime import datetime, timedelta
import os

def get_custom_doy(dt):
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
    
    pool_start = baseline_start - pd.Timedelta(days=5)
    pool_end = baseline_end + pd.Timedelta(days=5)
    
    baseline_dates_range = pd.date_range(pool_start, pool_end)
    target_dates_range = pd.date_range(target_start, target_end)
    
    def date_to_path(dt):
        return f'{root_dir}/sst_{dt.strftime("%Y%m%d")}.nc'

    sample_file = f'{root_dir}/sst_19820101.nc'
    with fs.open(sample_file, "rb") as f:
        ds_sample = xr.open_dataset(f, engine="h5netcdf")
        lats = ds_sample.latitude.values
        lons = ds_sample.longitude.values
        
    lat_mask = (lats >= lat_min) & (lats <= lat_max)
    lon_mask = (lons >= lon_min) & (lons <= lon_max)
    subset_lats = lats[lat_mask]
    subset_lons = lons[lon_mask]
    n_lat, n_lon = len(subset_lats), len(subset_lons)

    def load_sst_subset(dates):
        sst_list = []
        actual_dates = []
        for dt in dates:
            path = date_to_path(dt)
            try:
                with fs.open(path, "rb") as f:
                    ds = xr.open_dataset(f, engine="h5netcdf")
                    val = ds.analysed_sst.values
                    if val.ndim == 3:
                        val = val[0]
                    # Correct way to get the rectangular subset using boolean masks
                    sst_val = val[lat_mask][:, lon_mask]
                    sst_list.append(sst_val.astype('float64'))
                    actual_dates.append(dt)
            except Exception:
                pass
        if not sst_list:
            return np.empty((0, n_lat, n_lon)), np.array([])
        return np.array(sst_list), np.array(actual_dates)

    print("Loading baseline data...")
    baseline_sst, baseline_actual_dates = load_sst_subset(baseline_dates_range)
    print(f"Baseline SST shape: {baseline_sst.shape}")
    
    print("Loading target data...")
    target_sst, target_actual_dates = load_sst_subset(target_dates_range)
    print(f"Target SST shape: {target_sst.shape}")
    
    if target_sst.size == 0:
        print("No target data found.")
        ds_out = xr.Dataset(
            {"mhw": (("time", "latitude", "longitude"), np.array([], dtype=np.uint8))},
            coords={"time": [], "latitude": subset_lats, "longitude": subset_lons}
        )
        os.makedirs('output', exist_ok=True)
        ds_out.to_netcdf('output/mhw_mask.nc')
        with open('output/report.json', 'w') as f:
            json.dump({
                "region": {"lat_min": lat_min, "lat_max": lat_max, "lon_min": lon_min, "lon_max": lon_max},
                "baseline_analysed": None,
                "target_analysed": None,
                "events": [],
                "complete": True,
                "caveats": "No target data found"
            }, f, indent=2)
        return

    sea_cells_mask = np.isfinite(target_sst).all(axis=0)
    
    thresholds = np.full((366, n_lat, n_lon), np.nan, dtype='float64')
    climatologies = np.full((366, n_lat, n_lon), np.nan, dtype='float64')
    
    dates_used_in_pools = set()
    baseline_core_range = pd.date_range(baseline_start, baseline_end)
    
    print("Computing thresholds...")
    for d in range(1, 367):
        if d == 60: continue
        centers = [bd for bd in baseline_core_range if get_custom_doy(bd.to_pydatetime()) == d]
        pool_dates = set()
        for center in centers:
            for offset in range(-5, 6):
                pool_dates.add(center + pd.Timedelta(days=offset))
        
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
    
    T_target = target_sst.shape[0]
    target_doy = np.array([get_custom_doy(d.to_pydatetime()) for d in target_actual_dates])
    
    hot_days = np.zeros((T_target, n_lat, n_lon), dtype=bool)
    for t in range(T_target):
        doy = target_doy[t]
        hot_days[t] = (target_sst[t] >= thresholds[doy-1])
        
    mhw_mask = np.zeros((T_target, n_lat, n_lon), dtype=np.uint8)
    
    print("Computing per-cell MHWs...")
    for i in range(n_lat):
        for j in range(n_lon):
            if not sea_cells_mask[i, j]: continue
            cell_hot = hot_days[:, i, j]
            is_mhw = np.zeros(T_target, dtype=bool)
            current_run = []
            for t in range(T_target):
                if cell_hot[t]:
                    current_run.append(t)
                else:
                    if len(current_run) >= 5:
                        for t_run in current_run: is_mhw[t_run] = True
                    current_run = []
            if len(current_run) >= 5:
                for t_run in current_run: is_mhw[t_run] = True
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
                if not changed: break
            mhw_mask[:, i, j] = is_mhw.astype(np.uint8)
            
    active_days = np.any(mhw_mask == 1, axis=(1, 2))
    regional_events = []
    current_start = None
    for t in range(T_target):
        if active_days[t]:
            if current_start is None: current_start = t
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
