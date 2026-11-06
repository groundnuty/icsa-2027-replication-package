import xarray as xr
import numpy as np
import pandas as pd
import fsspec
import json
import os
from datetime import datetime, timedelta

def get_doy(dt):
    # Prompt: 1 Jan=1, 28 Feb=59, 29 Feb=60, 1 Mar=61
    # Non-leap years have no day 60.
    # pd.Timestamp.dayofyear:
    # Leap year: Feb 28=59, Feb 29=60, Mar 1=61
    # Non-leap: Feb 28=59, Mar 1=60
    y = dt.year
    doy = dt.dayofyear
    is_leap = (y % 4 == 0 and (y % 100 != 0 or y % 400 == 0))
    if not is_leap and doy >= 60:
        return doy + 1
    return doy

def solve():
    fs = fsspec.filesystem('onedata')
    file_path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
    
    # Region and target period
    lat_min, lat_max = 55.67, 56.87
    lon_min, lon_max = 16.45, 17.65
    target_start = '2005-06-01'
    target_end = '2005-08-31'
    baseline_start = '1992-01-01'
    baseline_end = '2002-12-31'
    
    with fs.open(file_path, "rb") as f:
        ds = xr.open_dataset(f, engine="h5netcdf")
    
    # Coordinate check
    lat_coords = ds.latitude.values
    lon_coords = ds.longitude.values
    
    # Subset region
    # Since lat is 53.5 to 66.0, it's increasing.
    ds_region = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))
    
    # Target period SST (variable name is analysed_sst)
    sst_target_ds = ds_region.sel(time=slice(target_start, target_end))
    sst_target = sst_target_ds.analysed_sst.astype('float64')
    
    # 1. Sea cells: SST finite on every day of target period
    sea_mask = np.isfinite(sst_target).all(dim='time')
    
    # 2. Threshold and Climatology
    b_start_dt = pd.to_datetime(baseline_start)
    b_end_dt = pd.to_datetime(baseline_end)
    data_start = b_start_dt - timedelta(days=5)
    data_end = b_end_dt + timedelta(days=5)
    
    sst_baseline_full = ds_region.sel(time=slice(data_start.strftime('%Y-%m-%d'), data_end.strftime('%Y-%m-%d'))).analysed_sst.astype('float64')
    times_baseline = pd.to_datetime(sst_baseline_full.time.values)
    
    # Precompute DOY for all baseline dates
    doy_baseline = np.array([get_doy(t) for t in times_baseline])
    
    baseline_dates = pd.date_range(b_start_dt, b_end_dt)
    
    n_lat = len(ds_region.latitude)
    n_lon = len(ds_region.longitude)
    
    thresh_raw = np.full((367, n_lat, n_lon), np.nan, dtype='float64')
    clim_raw = np.full((367, n_lat, n_lon), np.nan, dtype='float64')
    
    # Map date to index in sst_baseline_full
    date_to_idx = {t: i for i, t in enumerate(times_baseline)}
    
    for d in range(1, 367):
        if d == 60:
            continue
        
        relevant_baseline_dates = [dt for dt in baseline_dates if get_doy(dt) == d]
        if not relevant_baseline_dates:
            continue
            
        pool_dates = set()
        for dt in relevant_baseline_dates:
            for offset in range(-5, 6):
                pool_dates.add(dt + timedelta(days=offset))
        
        pool_indices = [date_to_idx[t] for t in pool_dates if t in date_to_idx]
        if not pool_indices:
            continue
            
        pool = sst_baseline_full.values[pool_indices, :, :]
        thresh_raw[d] = np.nanquantile(pool, 0.9, axis=0, method='hazen')
        clim_raw[d] = np.nanmean(pool, axis=0)
    
    # Day 60: mean of 59 and 61
    thresh_raw[60] = (thresh_raw[59] + thresh_raw[61]) / 2
    clim_raw[60] = (clim_raw[59] + clim_raw[61]) / 2
    
    # Smooth with 31-day moving mean, wrap around (1..366)
    thresh_smooth = np.zeros((366, n_lat, n_lon), dtype='float64')
    clim_smooth = np.zeros((366, n_lat, n_lon), dtype='float64')
    
    t_vals = thresh_raw[1:] # 0-365
    c_vals = clim_raw[1:]
    
    for d in range(366):
        window_indices = [(d + k) % 366 for k in range(-15, 16)]
        thresh_smooth[d] = np.nanmean(t_vals[window_indices], axis=0)
        clim_smooth[d] = np.nanmean(c_vals[window_indices], axis=0)
    
    # 3. Per-cell MHWs
    times_target = pd.to_datetime(sst_target.time.values)
    doy_target = np.array([get_doy(t) for t in times_target])
    sst_vals = sst_target.values
    target_thresh = thresh_smooth[doy_target - 1]
    
    hot_mask = sst_vals >= target_thresh
    hot_mask = hot_mask & sea_mask.values
    
    mhw_mask = np.zeros_like(hot_mask, dtype='uint8')
    n_time = len(times_target)
    
    for i in range(n_lat):
        for j in range(n_lon):
            if not sea_mask.values[i, j]:
                continue
            
            cell_hot = hot_mask[:, i, j]
            mhw_cell = np.zeros(n_time, dtype='uint8')
            
            # Find runs >= 5
            start = -1
            for t in range(n_time):
                if cell_hot[t]:
                    if start == -1: start = t
                else:
                    if start != -1:
                        if (t - start) >= 5: mhw_cell[start:t] = 1
                        start = -1
            if start != -1 and (n_time - start) >= 5:
                mhw_cell[start:n_time] = 1
            
            # Join gaps of 1 or 2
            changed = True
            while changed:
                changed = False
                for t in range(1, n_time - 1):
                    if mhw_cell[t] == 0:
                        if mhw_cell[t-1] == 1 and mhw_cell[t+1] == 1:
                            mhw_cell[t] = 1
                            changed = True
                        elif t < n_time - 2 and mhw_cell[t-1] == 1 and mhw_cell[t+1] == 0 and mhw_cell[t+2] == 1:
                            mhw_cell[t] = 1
                            mhw_cell[t+1] = 1
                            changed = True
            mhw_mask[:, i, j] = mhw_cell
            
    # 4. Regional Events
    active_days = np.any(mhw_mask == 1, axis=(1, 2))
    regional_events = []
    start = -1
    for t in range(n_time):
        if active_days[t]:
            if start == -1: start = t
        else:
            if start != -1:
                regional_events.append({"onset": times_target[start].strftime('%Y-%m-%d'), "end": times_target[t-1].strftime('%Y-%m-%d')})
                start = -1
    if start != -1:
        regional_events.append({"onset": times_target[start].strftime('%Y-%m-%d'), "end": times_target[n_time-1].strftime('%Y-%m-%d')})
    
    # Outputs
    os.makedirs('output', exist_ok=True)
    mhw_ds = xr.Dataset(
        {"mhw": (("time", "latitude", "longitude"), mhw_mask)},
        coords={"time": sst_target.time, "latitude": ds_region.latitude, "longitude": ds_region.longitude}
    )
    mhw_ds.to_netcdf('output/mhw_mask.nc')
    
    report = {
        "region": {"lat_min": float(lat_min), "lat_max": float(lat_max), "lon_min": float(lon_min), "lon_max": float(lon_max)},
        "baseline_analysed": {"start": baseline_start, "end": baseline_end},
        "target_analysed": {"start": target_start, "end": target_end},
        "events": regional_events,
        "complete": True,
        "caveats": ""
    }
    with open('output/report.json', 'w') as f:
        json.dump(report, f, indent=2)

solve()
