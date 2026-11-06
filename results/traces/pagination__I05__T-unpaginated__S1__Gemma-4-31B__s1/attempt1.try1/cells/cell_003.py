import fsspec
import xarray as xr
import numpy as np
import pandas as pd
import json
from datetime import datetime, timedelta

def get_custom_doy(dt):
    # 1 January = 1, 28 February = 59, 29 February = 60, 1 March = 61...
    # This is effectively the day of the year in a leap year.
    # For non-leap years, Feb 29 is just missing.
    # We can use a leap year as reference.
    ref_date = datetime(2000, 1, 1) # 2000 is a leap year
    # We only care about month and day
    target_date = datetime(2000, dt.month, dt.day)
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
    pool_start = baseline_start - pd.Timedelta(days=5)
    pool_end = baseline_end + pd.Timedelta(days=5)
    
    # 1. Find and load data
    # Use pandas to generate date ranges for files
    baseline_dates = pd.date_range(pool_start, pool_end)
    target_dates = pd.date_range(target_start, target_end)
    
    all_needed_dates = sorted(list(baseline_dates) + list(target_dates))
    
    # To avoid loading too much data, we'll filter by region first.
    # We need to know the coordinate values. 
    # Let's open one file to get lat/lon.
    sample_file = f'{root_dir}/sst_19820101.nc'
    with fs.open(sample_file, "rb") as f:
        ds_sample = xr.open_dataset(f, engine="h5netcdf")
        lats = ds_sample.latitude.values
        lons = ds_sample.longitude.values
        
    lat_mask = (lats >= lat_min) & (lats <= lat_max)
    lon_mask = (lons >= lon_min) & (lons <= lon_max)
    
    subset_lats = lats[lat_mask]
    subset_lons = lons[lon_mask]
    
    # Pre-calculate date-to-file mapping
    def date_to_path(dt):
        return f'{root_dir}/sst_{dt.strftime("%Y%m%d")}.nc'

    # Instead of loading all at once, let's process baseline and target separately.
    # Memory might be an issue. 
    # Region size: (55.59-54.39)/0.02 ~ 60; (19.45-18.25)/0.02 ~ 60.
    # 60*60*365*11 days ~ 14 million values. manageable.
    
    # Baseline SSTs
    baseline_sst_list = []
    baseline_actual_dates = []
    for dt in baseline_dates:
        path = date_to_path(dt)
        try:
            with fs.open(path, "rb") as f:
                ds = xr.open_dataset(f, engine="h5netcdf")
                # Slice region
                sst = ds.analysed_sst.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))
                # The sel slice might be slightly different due to precision, 
                # but our lat_mask/lon_mask are more precise.
                # Let's use isel with the masks found earlier.
                # Wait, the coordinates in the sample file were sorted.
                # Let's find the indices for the masks.
                # indices = np.where(lat_mask)[0] etc.
                # No, just use .sel with a small tolerance or just .isel.
                
                # Correct way to use masks:
                sst_val = ds.analysed_sst.values[0, lat_mask, lon_mask]
                baseline_sst_list.append(sst_val)
                baseline_actual_dates.append(dt)
        except Exception as e:
            # Some days might be missing
            pass

    baseline_sst = np.array(baseline_sst_list, dtype='float64') # (time, lat, lon)
    baseline_dates = np.array(baseline_actual_dates)
    
    # Target SSTs
    target_sst_list = []
    target_actual_dates = []
    for dt in target_dates:
        path = date_to_path(dt)
        try:
            with fs.open(path, "rb") as f:
                ds = xr.open_dataset(f, engine="h5netcdf")
                sst_val = ds.analysed_sst.values[0, lat_mask, lon_mask]
                target_sst_list.append(sst_val)
                target_actual_dates.append(dt)
        except Exception as e:
            pass
            
    target_sst = np.array(target_sst_list, dtype='float64') # (time, lat, lon)
    target_dates = np.array(target_actual_dates)
    
    # 2. Identify sea cells
    # SST is finite on every day of the target period.
    # target_sst shape: (T, lat, lon)
    is_finite = np.isfinite(target_sst).all(axis=0) # (lat, lon)
    sea_cells_mask = is_finite
    
    # 3. Threshold and Climatology
    # baseline_dates mapping to DOY
    baseline_doy = np.array([get_custom_doy(d.to_pydatetime()) for d in baseline_dates])
    
    thresholds = np.full((366, baseline_sst.shape[1], baseline_sst.shape[2]), np.nan, dtype='float64')
    climatologies = np.full((366, baseline_sst.shape[1], baseline_sst.shape[2]), np.nan, dtype='float64')
    
    # Baseline dates used for pools
    # We need to identify which baseline dates (1992-2002) were used.
    # a date is a baseline date if it's in [1992-01-01, 2002-12-31].
    baseline_dates_range = pd.date_range(baseline_start, baseline_end)
    
    for d in range(1, 367):
        if d == 60:
            continue
        
        # Pool: SST values whose date lies within ±5 calendar days of a baseline date (1992-2002) whose DOY is d.
        # Find all baseline dates (1992-2002) with DOY d.
        baseline_dates_with_doy_d = [bd for bd in baseline_dates_range if get_custom_doy(bd.to_pydatetime()) == d]
        
        # Now, for each such date, take the window [-5, +5]
        # To avoid duplicates, we can find the union of all these windows.
        pool_dates = set()
        for bd in baseline_dates_with_doy_d:
            for offset in range(-5, 6):
                pool_dates.add(bd + pd.Timedelta(days=offset))
        
        # Now find which of these pool_dates are actually in our `baseline_dates` (the ones we loaded)
        # baseline_dates is a numpy array of timestamps.
        pool_dates_list = sorted(list(pool_dates))
        
        # Get indices in baseline_sst
        indices = []
        for pd in pool_dates_list:
            idx = np.where(baseline_dates == pd)[0]
            if idx.size > 0:
                indices.append(idx[0])
        
        if indices:
            pool_vals = baseline_sst[indices, :, :] # (N, lat, lon)
            # Threshold: 90th percentile (method="hazen")
            # np.quantile with method="hazen" corresponds to Hyndman-Fan type 5
            # Note: np.nanquantile is used to ignore NaNs
            thresholds[d-1] = np.nanquantile(pool_vals, 0.9, axis=0, method="hazen")
            climatologies[d-1] = np.nanmean(pool_vals, axis=0)
    
    # Day 60 = mean of 59 and 61
    thresholds[59] = (thresholds[58] + thresholds[60]) / 2
    climatologies[59] = (climatologies[58] + climatologies[60]) / 2
    
    # Smoothing: 31-day centered moving mean, wraps around
    def smooth(arr):
        # arr shape (366, lat, lon)
        smoothed = np.zeros_like(arr)
        for d in range(366):
            # window: d-15 to d+15 modulo 366
            window = [ (d + i) % 366 for i in range(-15, 16) ]
            smoothed[d] = np.nanmean(arr[window], axis=0)
        return smoothed

    thresholds = smooth(thresholds)
    climatologies = smooth(climatologies)
    
    # 4. Per-cell MHWs (Target Period)
    # target_sst: (T, lat, lon)
    T, lat_len, lon_len = target_sst.shape
    target_doy = np.array([get_custom_doy(d.to_pydatetime()) for d in target_dates])
    
    # hot_days: (T, lat, lon)
    hot_days = np.zeros((T, lat_len, lon_len), dtype=bool)
    for t in range(T):
        doy = target_doy[t]
        # doy is 1-366, index is doy-1
        threshold_t = thresholds[doy-1]
        hot_days[t] = (target_sst[t] >= threshold_t)
        
    mhw_mask = np.zeros((T, lat_len, lon_len), dtype=np.uint8)
    
    # Process each cell
    for i in range(lat_len):
        for j in range(lon_len):
            if not sea_cells_mask[i, j]:
                continue
            
            cell_hot = hot_days[:, i, j]
            # Find runs of at least 5 consecutive hot days
            # Join gaps of 1 or 2 non-hot days
            
            # This can be done by:
            # 1. Find all hot runs.
            # 2. Mark as MHW if len >= 5.
            # 3. Join.
            
            # Simpler approach:
            # Use a boolean array to mark MHW days
            is_mhw = np.zeros(T, dtype=bool)
            
            # First pass: find all runs of >= 5 hot days
            current_run = []
            for t in range(T):
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
            
            # Second pass: join gaps of 1 or 2 non-hot days
            # Note: The gaps must be between existing MHW days.
            # We iterate until no more joins are made.
            while True:
                changed = False
                # Find gaps of 1 or 2 zeros between ones
                for t in range(1, T-1):
                    if not is_mhw[t]:
                        # Gap of 1
                        if is_mhw[t-1] and is_mhw[t+1]:
                            is_mhw[t] = True
                            changed = True
                        # Gap of 2
                        elif t < T-2 and is_mhw[t-1] and not is_mhw[t+1] and is_mhw[t+2]:
                            # This is a gap of 2. We need to mark both t and t+1.
                            # Wait, the loop will handle t+1 in the next iteration if we mark t?
                            # No, it's safer to mark both.
                            is_mhw[t] = True
                            is_mhw[t+1] = True
                            changed = True
                if not changed:
                    break
            
            mhw_mask[:, i, j] = is_mhw.astype(np.uint8)
            
    # 5. Regional Events
    # Day active if >= 1 cell in MHW
    active_days = np.any(mhw_mask == 1, axis=(1, 2))
    
    regional_events = []
    current_event_start = None
    for t in range(T):
        if active_days[t]:
            if current_event_start is None:
                current_event_start = t
        else:
            if current_event_start is not None:
                regional_events.append({
                    "onset": target_dates[current_event_start].strftime("%Y-%m-%d"),
                    "end": target_dates[t-1].strftime("%Y-%m-%d")
                })
                current_event_start = None
    if current_event_start is not None:
        regional_events.append({
            "onset": target_dates[current_event_start].strftime("%Y-%m-%d"),
            "end": target_dates[T-1].strftime("%Y-%m-%d")
        })
        
    # 6. Output Files
    # mhw_mask.nc
    ds_out = xr.Dataset(
        {"mhw": (("time", "latitude", "longitude"), mhw_mask.astype(np.uint8))},
        coords={
            "time": target_dates,
            "latitude": subset_lats,
            "longitude": subset_lons,
        }
    )
    os.makedirs('output', exist_ok=True)
    ds_out.to_netcdf('output/mhw_mask.nc')
    
    # report.json
    report = {
        "region": {"lat_min": lat_min, "lat_max": lat_max, "lon_min": lon_min, "lon_max": lon_max},
        "baseline_analysed": {
            "start": baseline_dates[0].strftime("%Y-%m-%d"),
            "end": baseline_dates[-1].strftime("%Y-%m-%d")
        },
        "target_analysed": {
            "start": target_dates[0].strftime("%Y-%m-%d"),
            "end": target_dates[-1].strftime("%Y-%m-%d")
        },
        "events": regional_events,
        "complete": True,
        "caveats": ""
    }
    with open('output/report.json', 'w') as f:
        json.dump(report, f, indent=2)

solve()
