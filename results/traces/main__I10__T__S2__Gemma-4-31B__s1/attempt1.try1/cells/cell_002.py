import xarray as xr
import numpy as np
import pandas as pd
import fsspec
import json
from datetime import datetime, timedelta

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
    
    # Handle latitude potentially being reversed
    if ds.latitude[0] > ds.latitude[-1]:
        ds_region = ds.sel(latitude=slice(lat_max, lat_min), longitude=slice(lon_min, lon_max))
    else:
        ds_region = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))
    
    sst_target = ds_region.sel(time=slice(target_start, target_end)).sst.astype('float64')
    
    # 1. Sea cells: SST finite on every day of target period
    sea_mask = np.isfinite(sst_target).all(dim='time')
    
    # 2. Threshold and Climatology
    # Baseline date range for the windows
    b_start_dt = pd.to_datetime(baseline_start)
    b_end_dt = pd.to_datetime(baseline_end)
    # Data needed to cover windows
    data_start = b_start_dt - timedelta(days=5)
    data_end = b_end_dt + timedelta(days=5)
    
    sst_baseline_full = ds_region.sel(time=slice(data_start.strftime('%Y-%m-%d'), data_end.strftime('%Y-%m-%d'))).sst.astype('float64')
    
    times_baseline = pd.to_datetime(sst_baseline_full.time.values)
    
    # dayofyear from 1 to 366.
    # Note: pd.Timestamp.dayofyear gives 1-366. 
    # In non-leap years, 28 Feb is 59 and 1 Mar is 60. 
    # But the prompt says 28 Feb = 59, 29 Feb = 60, 1 Mar = 61.
    # This means the prompt defines day of year based on a leap year calendar.
    def get_doy(dt):
        # Prompt: 1 Jan=1, 28 Feb=59, 29 Feb=60, 1 Mar=61
        # This is standard for leap years. For non-leap years, it skips 60.
        # pd.Timestamp.dayofyear:
        # Leap year: Feb 28=59, Feb 29=60, Mar 1=61
        # Non-leap: Feb 28=59, Mar 1=60
        # So if it's a non-leap year and dayofyear >= 60, it's actually dayofyear + 1.
        y = dt.year
        doy = dt.dayofyear
        is_leap = (y % 4 == 0 and (y % 100 != 0 or y % 400 == 0))
        if not is_leap and doy >= 60:
            return doy + 1
        return doy

    # Precompute DOY for all baseline dates
    doy_baseline = np.array([get_doy(t) for t in times_baseline])
    
    # We need thresholds and climatology for doy = 1 to 366
    # Baseline range (1992-01-01 to 2002-12-31)
    baseline_dates = pd.date_range(b_start_dt, b_end_dt)
    
    # Create arrays for thresholds and climatology (shape: 367, lat, lon)
    # index 0 unused
    thresh_raw = np.full((367, len(ds_region.latitude), len(ds_region.longitude)), np.nan, dtype='float64')
    clim_raw = np.full((367, len(ds_region.latitude), len(ds_region.longitude)), np.nan, dtype='float64')
    
    # Iterate doy from 1 to 366, excluding 60
    for d in range(1, 367):
        if d == 60:
            continue
        
        # Baseline dates that have doy == d
        # Only check dates in 1992-01-01 to 2002-12-31
        relevant_baseline_dates = [dt for dt in baseline_dates if get_doy(dt) == d]
        
        if not relevant_baseline_dates:
            continue
            
        # Find all dates within +/- 5 days of these dates
        pool_dates = set()
        for dt in relevant_baseline_dates:
            for offset in range(-5, 6):
                pool_dates.add(dt + timedelta(days=offset))
        
        # Map pool_dates to indices in sst_baseline_full
        # Use a dictionary for fast lookup
        date_to_idx = {t: i for i, t in enumerate(times_baseline)}
        pool_indices = [date_to_idx[t] for t in pool_dates if t in date_to_idx]
        
        if not pool_indices:
            continue
            
        # Extract SST pool
        # shape: (len(pool_indices), lat, lon)
        pool = sst_baseline_full.values[pool_indices, :, :]
        
        # 90th percentile (method="hazen") and mean
        # numpy.nanquantile(pool, 0.9, axis=0, method='hazen')
        thresh_raw[d] = np.nanquantile(pool, 0.9, axis=0, method='hazen')
        clim_raw[d] = np.nanmean(pool, axis=0)
    
    # Day 60: mean of 59 and 61
    thresh_raw[60] = (thresh_raw[59] + thresh_raw[61]) / 2
    clim_raw[60] = (clim_raw[59] + clim_raw[61]) / 2
    
    # Smooth with 31-day moving mean, wrapping around (day 1..366)
    # We'll use 0-indexed arrays of length 366
    thresh_smooth = np.zeros((366, len(ds_region.latitude), len(ds_region.longitude)), dtype='float64')
    clim_smooth = np.zeros((366, len(ds_region.latitude), len(ds_region.longitude)), dtype='float64')
    
    # Original arrays (1-366) shifted to (0-365)
    t_vals = thresh_raw[1:]
    c_vals = clim_raw[1:]
    
    for d in range(366):
        # window: d-15 to d+15 (modulo 366)
        window_indices = [(d + k) % 366 for k in range(-15, 16)]
        thresh_smooth[d] = np.mean(t_vals[window_indices], axis=0)
        clim_smooth[d] = np.mean(c_vals[window_indices], axis=0)
    
    # 3. Per-cell MHWs
    # Target period days
    times_target = pd.to_datetime(sst_target.time.values)
    doy_target = np.array([get_doy(t) for t in times_target])
    
    # SST for target period
    sst_vals = sst_target.values # (time, lat, lon)
    
    # Thresholds for target days
    # doy_target is 1-366, map to 0-365 for thresh_smooth
    target_thresh = thresh_smooth[doy_target - 1] # (time, lat, lon)
    
    # A day is hot if SST >= threshold
    hot_mask = sst_vals >= target_thresh
    
    # Sea cells are the only ones that can have MHWs
    # Land cells (not sea cells) are always 0 in the output mask
    hot_mask = hot_mask & sea_mask.values
    
    # Find runs of at least 5 consecutive hot days, join gaps of 1-2 days
    # Dimensions: (time, lat, lon)
    mhw_mask = np.zeros_like(hot_mask, dtype='uint8')
    
    n_time = len(times_target)
    n_lat = len(ds_region.latitude)
    n_lon = len(ds_region.longitude)
    
    for i in range(n_lat):
        for j in range(n_lon):
            if not sea_mask.values[i, j]:
                continue
            
            cell_hot = hot_mask[:, i, j]
            # Find runs
            mhw_cell = np.zeros(n_time, dtype='uint8')
            
            # Identify segments of hot days
            # Using a simple loop to find runs
            start = -1
            for t in range(n_time):
                if cell_hot[t]:
                    if start == -1:
                        start = t
                else:
                    if start != -1:
                        length = t - start
                        if length >= 5:
                            mhw_cell[start:t] = 1
                        start = -1
            if start != -1:
                length = n_time - start
                if length >= 5:
                    mhw_cell[start:n_time] = 1
            
            # Join gaps of 1 or 2 non-hot days
            # We iterate until no more gaps are joined
            changed = True
            while changed:
                changed = False
                # Find gaps of 1 or 2 zeros between ones
                for t in range(1, n_time - 1):
                    if mhw_cell[t] == 0:
                        # Check gap of 1
                        if mhw_cell[t-1] == 1 and mhw_cell[t+1] == 1:
                            mhw_cell[t] = 1
                            changed = True
                        # Check gap of 2
                        elif t < n_time - 2 and mhw_cell[t-1] == 1 and mhw_cell[t+1] == 0 and mhw_cell[t+2] == 1:
                            mhw_cell[t] = 1
                            mhw_cell[t+1] = 1
                            changed = True
            
            mhw_mask[:, i, j] = mhw_cell
            
    # 4. Regional Events
    # a day is active if at least one sea cell is in a per-cell MHW
    active_days = np.any(mhw_mask == 1, axis=(1, 2))
    
    regional_events = []
    start = -1
    for t in range(n_time):
        if active_days[t]:
            if start == -1:
                start = t
        else:
            if start != -1:
                regional_events.append({
                    "onset": times_target[start].strftime('%Y-%m-%d'),
                    "end": times_target[t-1].strftime('%Y-%m-%d')
                })
                start = -1
    if start != -1:
        regional_events.append({
            "onset": times_target[start].strftime('%Y-%m-%d'),
            "end": times_target[n_time-1].strftime('%Y-%m-%d')
        })
    
    # Write output files
    os.makedirs('output', exist_ok=True)
    
    # NetCDF output
    mhw_ds = xr.Dataset(
        {"mhw": (("time", "latitude", "longitude"), mhw_mask)},
        coords={
            "time": sst_target.time,
            "latitude": ds_region.latitude,
            "longitude": ds_region.longitude,
        }
    )
    mhw_ds.to_netcdf('output/mhw_mask.nc')
    
    # JSON report
    report = {
        "region": {
            "lat_min": float(lat_min),
            "lat_max": float(lat_max),
            "lon_min": float(lon_min),
            "lon_max": float(lon_max),
        },
        "baseline_analysed": {
            "start": baseline_start,
            "end": baseline_end
        },
        "target_analysed": {
            "start": target_start,
            "end": target_end
        },
        "events": regional_events,
        "complete": True,
        "caveats": ""
    }
    with open('output/report.json', 'w') as f:
        json.dump(report, f, indent=2)

solve()
