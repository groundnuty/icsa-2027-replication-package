import xarray as xr
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import json
import os

# Constants
LAT_MIN, LAT_MAX = 56.63, 57.83
LON_MIN, LON_MAX = 20.23, 21.43
TARGET_START = "2010-06-01"
TARGET_END = "2010-08-31"
BASELINE_START_YEAR = 1992
BASELINE_END_YEAR = 2002
FILE_PATH = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"

def get_custom_doy(dt):
    """Map date to DOY 1-366, where 29 Feb = 60 and 1 Mar = 61."""
    return datetime(2000, dt.month, dt.day).timetuple().tm_yday

def solve():
    ds = xr.open_dataset(FILE_PATH, engine="h5netcdf")
    
    lat_coords = ds.latitude.values
    lon_coords = ds.longitude.values
    
    if lat_coords[0] > lat_coords[-1]:
        lat_slice = slice(LAT_MAX, LAT_MIN)
    else:
        lat_slice = slice(LAT_MIN, LAT_MAX)
        
    if lon_coords[0] > lon_coords[-1]:
        lon_slice = slice(LON_MAX, LON_MIN)
    else:
        lon_slice = slice(LON_MIN, LON_MAX)
        
    ds_reg = ds.sel(latitude=lat_slice, longitude=lon_slice)
    
    b_start_ts = pd.Timestamp("1991-12-27")
    b_end_ts = pd.Timestamp("2003-01-05")
    t_start_ts = pd.Timestamp(TARGET_START)
    t_end_ts = pd.Timestamp(TARGET_END)
    
    sst_baseline = ds_reg.analysed_sst.sel(time=slice(b_start_ts, b_end_ts)).load()
    sst_target = ds_reg.analysed_sst.sel(time=slice(t_start_ts, t_end_ts)).load()
    
    is_finite = np.isfinite(sst_target.values).all(axis=0)
    sea_cells_mask = is_finite
    
    baseline_years = range(BASELINE_START_YEAR, BASELINE_END_YEAR + 1)
    baseline_times = pd.to_datetime(sst_baseline.time.values)
    baseline_doy = np.array([get_custom_doy(t) for t in baseline_times])
    
    n_lat = sst_baseline.shape[1]
    n_lon = sst_baseline.shape[2]
    
    thresholds = np.full((366, n_lat, n_lon), np.nan, dtype=np.float64)
    climatology = np.full((366, n_lat, n_lon), np.nan, dtype=np.float64)
    
    for d in range(1, 367):
        if d == 60:
            continue
        
        center_dates_indices = np.where(
            (baseline_doy == d) & 
            (baseline_times >= pd.Timestamp(f"{BASELINE_START_YEAR}-01-01")) & 
            (baseline_times <= pd.Timestamp(f"{BASELINE_END_YEAR}-12-31"))
        )[0]
        
        if len(center_dates_indices) == 0:
            continue
            
        all_window_indices = set()
        for idx in center_dates_indices:
            center_date = baseline_times[idx]
            window_start = center_date - timedelta(days=5)
            window_end = center_date + timedelta(days=5)
            
            idx_start = np.searchsorted(baseline_times, window_start)
            idx_end = np.searchsorted(baseline_times, window_end, side='right')
            for i in range(idx_start, idx_end):
                all_window_indices.add(i)
                
        pool_indices = np.array(list(all_window_indices))
        if len(pool_indices) == 0:
            continue
            
        pool = sst_baseline.values[pool_indices, :, :].astype(np.float64)
        thresholds[d-1, :, :] = np.nanpercentile(pool, 90, axis=0, method='hazen')
        climatology[d-1, :, :] = np.nanmean(pool, axis=0)
        
    thresholds[59, :, :] = (thresholds[58, :, :] + thresholds[60, :, :]) / 2
    climatology[59, :, :] = (climatology[58, :, :] + climatology[60, :, :]) / 2
    
    def smooth_366(arr):
        smoothed = np.zeros_like(arr)
        for d in range(366):
            window_indices = [(d + k) % 366 for k in range(-15, 16)]
            smoothed[d, :, :] = np.nanmean(arr[window_indices, :, :], axis=0)
        return smoothed

    thresholds = smooth_366(thresholds)
    climatology = smooth_366(climatology)
    
    target_times = pd.to_datetime(sst_target.time.values)
    target_doy = np.array([get_custom_doy(t) for t in target_times])
    
    hot_mask = np.zeros(sst_target.shape, dtype=bool)
    for t_idx, d in enumerate(target_doy):
        hot_mask[t_idx, :, :] = sst_target.values[t_idx, :, :] >= thresholds[d-1, :, :]
        
    mhw_mask = np.zeros(sst_target.shape, dtype=np.uint8)
    
    for i in range(n_lat):
        for j in range(n_lon):
            if not sea_cells_mask[i, j]:
                continue
            
            cell_hot = hot_mask[:, i, j]
            n_days = len(cell_hot)
            is_mhw = np.zeros(n_days, dtype=bool)
            
            run_start = None
            for t in range(n_days):
                if cell_hot[t]:
                    if run_start is None:
                        run_start = t
                else:
                    if run_start is not None:
                        if t - run_start >= 5:
                            is_mhw[run_start:t] = True
                        run_start = None
            if run_start is not None and n_days - run_start >= 5:
                is_mhw[run_start:n_days] = True
            
            changed = True
            while changed:
                changed = False
                for t in range(n_days):
                    if not is_mhw[t]:
                        if 0 < t < n_days - 1 and is_mhw[t-1] and is_mhw[t+1]:
                            is_mhw[t] = True
                            changed = True
                        elif 0 < t < n_days - 2 and is_mhw[t-1] and not is_mhw[t+1] and is_mhw[t+2]:
                            is_mhw[t] = True
                            is_mhw[t+1] = True
                            changed = True
            
            mhw_mask[:, i, j] = is_mhw.astype(np.uint8)
            
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
                    "onset": target_times[run_start].strftime("%Y-%m-%d"),
                    "end": target_times[t-1].strftime("%Y-%m-%d")
                })
                run_start = None
    if run_start is not None:
        events.append({
            "onset": target_times[run_start].strftime("%Y-%m-%d"),
            "end": target_times[-1].strftime("%Y-%m-%d")
        })
        
    out_ds = xr.Dataset(
        {"mhw": (("time", "lat", "lon"), mhw_mask)},
        coords={
            "time": sst_target.time,
            "lat": sst_target.latitude,
            "lon": sst_target.longitude
        }
    )
    os.makedirs("output", exist_ok=True)
    out_ds.to_netcdf("output/mhw_mask.nc")
    
    report = {
        "region": {
            "lat_min": float(LAT_MIN),
            "lat_max": float(LAT_MAX),
            "lon_min": float(LON_MIN),
            "lon_max": float(LON_MAX)
        },
        "baseline_analysed": {
            "start": b_start_ts.strftime("%Y-%m-%d"),
            "end": b_end_ts.strftime("%Y-%m-%d")
        },
        "target_analysed": {
            "start": t_start_ts.strftime("%Y-%m-%d"),
            "end": t_end_ts.strftime("%Y-%m-%d")
        },
        "events": events,
        "complete": True,
        "caveats": ""
    }
    with open("output/report.json", "w") as f:
        json.dump(report, f, indent=2)

solve()
