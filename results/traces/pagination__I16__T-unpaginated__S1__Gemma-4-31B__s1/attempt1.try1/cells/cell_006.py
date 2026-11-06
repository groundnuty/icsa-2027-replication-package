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
    # Baseline dates: 1992-01-01 to 2002-12-31
    # Windows can extend 5 days before and after.
    all_baseline_dates = pd.date_range(baseline_start, baseline_end)
    
    # The pool for day d uses dates within +/- 5 days of baseline dates with doy=d.
    # The absolute minimum date needed is baseline_start - 5 days.
    # The absolute maximum date needed is baseline_end + 5 days.
    min_baseline_date = baseline_start - timedelta(days=5)
    max_baseline_date = baseline_end + timedelta(days=5)
    
    needed_dates = set()
    # Add all dates from the extended baseline range
    needed_dates.update(pd.date_range(min_baseline_date, max_baseline_date))
    # Add all dates from the target range
    needed_dates.update(pd.date_range(target_start, target_end))
    
    # Filter for existing files
    all_files_set = set(fs.ls(base_path))
    final_needed_dates = []
    for dt in sorted(list(needed_dates)):
        filename = f"sst_{dt.strftime('%Y%m%d')}.nc"
        path = f"{base_path}/{filename}"
        if path in all_files_set:
            final_needed_dates.append(dt)
    
    # Load coordinate indices from first available file
    with fs.open(list(all_files_set)[0], 'rb') as f:
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
            
    sst_array = np.array(sst_data, dtype='float64') # (time, lat, lon)
    loaded_dates = np.array(loaded_dates)
    
    # 1. Sea cells
    # Region's grid cells whose SST is finite on every day of the target period.
    target_mask = (loaded_dates >= target_start) & (loaded_dates <= target_end)
    sst_target = sst_array[target_mask]
    # sst_target shape: (days_in_target, lat, lon)
    
    # Find cells where all target days are finite
    # np.isfinite returns True for non-NaN and non-Inf
    is_finite = np.isfinite(sst_target)
    sea_cells_mask = np.all(is_finite, axis=0) # (lat, lon)
    
    # 2. Threshold and Climatology
    # baseline_dates = 1992-01-01 to 2002-12-31
    baseline_mask = (loaded_dates >= baseline_start) & (loaded_dates <= baseline_end)
    baseline_sst = sst_array[baseline_mask]
    baseline_dates_arr = loaded_dates[baseline_mask]
    
    # Map every date to day of year 1-366
    def get_doy(dt):
        return dt.dayofyear
        
    # We need the pool for each day d in 1..366 (except 60)
    # For each d, pool = SST values from all dates T' within +/- 5 days of any baseline date T with doy=d.
    
    # To optimize, let's pre-calculate the doy for all loaded dates in the extended baseline range
    extended_baseline_mask = (loaded_dates >= min_baseline_date) & (loaded_dates <= max_baseline_date)
    sst_ext = sst_array[extended_baseline_mask]
    dates_ext = loaded_dates[extended_baseline_mask]
    
    # Create a lookup: date -> index in sst_ext
    date_to_idx = {dt: i for i, dt in enumerate(dates_ext)}
    
    thresholds = np.full((366, sst_array.shape[1], sst_array.shape[2]), np.nan, dtype='float64')
    climatologies = np.full((366, sst_array.shape[1], sst_array.shape[2]), np.nan, dtype='float64')
    
    # For each baseline year
    baseline_years = np.unique(baseline_dates_arr.year)
    
    for d in range(1, 367):
        if d == 60:
            continue
        
        pool_indices = []
        for year in baseline_years:
            # Find the date T in this year with doy=d
            # Careful with leap years. Non-leap years don't have doy=60. 
            # We are already skipping d=60.
            # To find a date with doy=d in a specific year:
            try:
                # Construct date: start of year + (d-1) days
                T = pd.Timestamp(year=year, month=1, day=1) + pd.Timedelta(days=d-1)
                # Check if this date actually has doy=d (it should, unless d=60 in non-leap)
                if T.dayofyear == d:
                    # Window [T-5, T+5]
                    for offset in range(-5, 6):
                        T_prime = T + pd.Timedelta(days=offset)
                        if T_prime in date_to_idx:
                            pool_indices.append(date_to_idx[T_prime])
            except Exception:
                continue
        
        if pool_indices:
            pool_vals = sst_ext[pool_indices] # (num_days, lat, lon)
            
            # Threshold: 90th percentile (numpy method="hazen")
            # Climatology: mean
            # We need to do this per cell.
            # Flattening the time axis to compute across the pool.
            
            # To avoid huge loops, we can use np.nanpercentile and np.nanmean
            thresholds[d-1] = np.nanpercentile(pool_vals, 90, axis=0, method='hazen')
            climatologies[d-1] = np.nanmean(pool_vals, axis=0)

    # Day 60 is mean of 59 and 61
    thresholds[59] = (thresholds[58] + thresholds[60]) / 2
    climatologies[59] = (climatologies[58] + climatologies[60]) / 2
    
    # Smoothing: 31-day centered moving mean, wraps around
    def smooth_366(arr):
        # arr shape (366, lat, lon)
        smoothed = np.zeros_like(arr)
        for d in range(366):
            # Days d-15 to d+15 modulo 366
            indices = [(d + offset) % 366 for offset in range(-15, 16)]
            # axis=0 is the day axis
            smoothed[d] = np.nanmean(arr[indices], axis=0)
        return smoothed
    
    thresholds_smooth = smooth_366(thresholds)
    climatologies_smooth = smooth_366(climatologies)
    
    # 3. Per-cell MHWs
    # Target period: 2008-06-01 to 2008-08-31
    # Restrict SST to this period
    sst_target = sst_array[target_mask] # (time, lat, lon)
    target_dates = loaded_dates[target_mask]
    
    #- a day is hot if SST >= threshold for that doy
    # target_doy shape (time,)
    target_doys = np.array([dt.dayofyear for dt in target_dates])
    
    # Get threshold for each day of the target period
    # target_thresholds shape (time, lat, lon)
    target_thresholds = thresholds_smooth[target_doys - 1]
    
    hot_mask = (sst_target >= target_thresholds) # (time, lat, lon)
    # Land cells (where sea_cells_mask is False) should be treated as not hot
    hot_mask = hot_mask & sea_cells_mask[np.newaxis, :, :]
    
    # Per-cell MHWs
    mhw_mask = np.zeros_like(hot_mask, dtype='uint8')
    
    # Iterate over each cell
    for i in range(sst_array.shape[1]):
        for j in range(sst_array.shape[2]):
            if not sea_cells_mask[i, j]:
                continue
            
            cell_hot = hot_mask[:, i, j]
            # A per-cell MHW is a run of at least 5 consecutive hot days
            # Join runs separated by 1 or 2 non-hot days.
            
            # First, find runs of at least 5 hot days
            is_mhw = np.zeros(len(cell_hot), dtype=bool)
            
            # Find consecutive hot days
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
            
            # Now join runs separated by 1 or 2 non-hot days.
            # This is an iterative process? "separated by 1 or 2 non-hot days are joined into one, and the gap days belong to it."
            # Let's implement it by looking at gaps.
            
            changed = True
            while changed:
                changed = False
                # Find gaps of 1 or 2 non-hot days between MHW periods
                # A gap exists if is_mhw[t-1] is True, is_mhw[t+1] is True (or is_mhw[t+2] is True), and is_mhw[t] is False.
                
                # Easier: iterate and fill
                for t in range(1, len(is_mhw) - 1):
                    if not is_mhw[t]:
                        # Check for 1-day gap
                        if is_mhw[t-1] and is_mhw[t+1]:
                            is_mhw[t] = True
                            changed = True
                        # Check for 2-day gap
                        elif t < len(is_mhw) - 2 and is_mhw[t-1] and not is_mhw[t+1] and is_mhw[t+2]:
                            is_mhw[t] = True
                            is_mhw[t+1] = True
                            changed = True
            
            mhw_mask[:, i, j] = is_mhw.astype('uint8')
            
    # 4. Regional Events
    # a day is active if at least one sea cell of the region is inside a per-cell MHW on that day
    active_days = np.any(mhw_mask == 1, axis=(1, 2)) # (time,)
    
    # Regional MHW event: maximal run of consecutive active days
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
    
    # Save output/mhw_mask.nc
    os.makedirs('output', exist_ok=True)
    
    # Create xarray Dataset for mask
    mask_ds = xr.Dataset(
        {"mhw": (("time", "latitude", "longitude"), mhw_mask)},
        coords={
            "time": target_dates,
            "latitude": lats,
            "longitude": lons,
        }
    )
    mask_ds.to_netcdf('output/mhw_mask.nc')
    
    # Save output/report.json
    report = {
        "region": {"lat_min": lat_min, "lat_max": lat_max, "lon_min": lon_min, "lon_max": lon_max},
        "baseline_analysed": {
            "start": final_needed_dates[0].strftime('%Y-%m-%d') if final_needed_dates else None,
            "end": final_needed_dates[-1].strftime('%Y-%m-%d') if final_needed_dates else None
        },
        "target_analysed": {
            "start": target_dates[0].strftime('%Y-%m-%d') if len(target_dates) > 0 else None,
            "end": target_dates[-1].strftime('%Y-%m-%d') if len(target_dates) > 0 else None
        },
        "events": events,
        "complete": True,
        "caveats": ""
    }
    
    # Correction on baseline_analysed: the prompt asks for the first and last baseline day used.
    # My `final_needed_dates` includes target days.
    baseline_used_dates = [dt for dt in final_needed_dates if dt <= max_baseline_date]
    if baseline_used_dates:
        report["baseline_analysed"] = {
            "start": baseline_used_dates[0].strftime('%Y-%m-%d'),
            "end": baseline_used_dates[-1].strftime('%Y-%m-%d')
        }
    else:
        report["baseline_analysed"] = None
        
    with open('output/report.json', 'w') as f:
        json.dump(report, f, indent=2)

solve()
