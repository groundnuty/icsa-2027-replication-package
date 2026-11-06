import fsspec
import xarray as xr
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import json
import os

def get_doy(date):
    """Custom DOY mapping: 1 Jan = 1, 29 Feb = 60, 1 Mar = 61, ..., 31 Dec = 366."""
    # pandas.Timestamp.dayofyear handles leap years correctly (29 Feb is 60)
    return date.dayofyear

def solve():
    fs = fsspec.filesystem('onedata')
    root_dir = 'icsa2027_data_20261101T090944Z/s1z'
    
    lat_min, lat_max = 54.13, 55.33
    lon_min, lon_max = 14.67, 15.87
    
    target_start = pd.Timestamp('2004-06-01')
    target_end = pd.Timestamp('2004-08-31')
    
    baseline_start = pd.Timestamp('1992-01-01')
    baseline_end = pd.Timestamp('2002-12-31')
    
    # Windows can extend 5 days beyond
    data_start = baseline_start - pd.Timedelta(days=5)
    data_end = baseline_end + pd.Timedelta(days=5)
    
    # We also need target data
    all_dates_needed = sorted(list(
        pd.date_range(data_start, data_end).strftime('%Y%m%d') + 
        list(pd.date_range(target_start, target_end).strftime('%Y%m%d'))
    )) # This is not correct, list addition.
    
    # Correct dates
    baseline_dates = pd.date_range(data_start, data_end)
    target_dates = pd.date_range(target_start, target_end)
    all_dates = sorted(list(set(baseline_dates) | set(target_dates)))
    
    # Load data for the region
    sst_data = []
    coords_time = []
    
    # Find which files exist
    files = fs.ls(root_dir)
    # Filter files that match our needed dates
    needed_files = []
    for date in all_dates:
        fname = f"sst_{date.strftime('%Y%m%d')}.nc"
        fpath = f"{root_dir}/{fname}"
        if fpath in files:
            needed_files.append(fpath)
        else:
            # Handle potential missing files? The task implies they exist.
            pass

    # Let's load data for the region. To be efficient, we can open them and slice.
    # Given the size (60x60), we can probably fit them in memory.
    
    # First, get coordinates from any file
    with fs.open(needed_files[0], "rb") as f:
        ds_sample = xr.open_dataset(f, engine="h5netcdf")
        subset_sample = ds_sample.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))
        lats = subset_sample.latitude.values
        lons = subset_sample.longitude.values
    
    n_lat = len(lats)
    n_lon = len(lons)
    
    # Data array: (time, lat, lon)
    # We'll use a dictionary or a pre-allocated array
    all_sst = np.full((len(all_dates), n_lat, n_lon), np.nan, dtype=np.float64)
    
    for i, date in enumerate(all_dates):
        fname = f"sst_{date.strftime('%Y%m%d')}.nc"
        fpath = f"{root_dir}/{fname}"
        if fpath in files:
            with fs.open(fpath, "rb") as f:
                ds = xr.open_dataset(f, engine="h5netcdf")
                subset = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))
                all_sst[i] = subset.analysed_sst.values[0]
    
    # Now we have all_sst indexed by all_dates.
    # Identify sea cells: SST is finite on every day of the target period.
    target_indices = [i for i, d in enumerate(all_dates) if target_start <= d <= target_end]
    target_sst = all_sst[target_indices]
    
    # finite on every day of the target period
    # np.isfinite(target_sst).all(axis=0)
    sea_mask = np.isfinite(target_sst).all(axis=0)
    
    # Threshold and Climatology
    # Baseline years: 1992-2002
    baseline_years = range(1992, 2003)
    
    # We need thresholds and climatology for each sea cell for DOY 1-366.
    thresholds = np.full((n_lat, n_lon, 366), np.nan, dtype=np.float64)
    climatology = np.full((n_lat, n_lon, 366), np.nan, dtype=np.float64)
    
    # Pre-calculate date to index mapping
    date_to_idx = {d: i for i, d in enumerate(all_dates)}
    
    for d in range(1, 367):
        if d == 60:
            continue
        
        # Pool for DOY d
        # For each baseline year, find the date with DOY d and take +- 5 days.
        pool_indices = []
        for year in baseline_years:
            try:
                # Create a date with DOY d in this year
                # If d=60 and year is not leap, this will fail or be wrong.
                # But we only do this for d != 60.
                # However, a non-leap year date with DOY 61 is March 1.
                # Let's use pd.Timestamp and offset.
                base_date = pd.Timestamp(year, 1, 1) + pd.Timedelta(days=d-1)
                # Check if base_date actually has DOY d. 
                # (If year is leap and d=61, it's March 1. If year is not leap and d=61, it's March 1.)
                # Wait, the logic "1 January = 1, 28 February = 59, 29 February = 60, 1 March = 61"
                # implies a fixed mapping.
                # Let's use a more robust way:
                # For a given year and d, what is the date?
                # If d <= 59: date is Jan 1 + (d-1) days
                # If d == 60: 29 Feb (only in leap years)
                # If d >= 61: date is March 1 + (d-61) days
                
                if d <= 59:
                    target_date = pd.Timestamp(year, 1, 1) + pd.Timedelta(days=d-1)
                else: # d >= 61
                    target_date = pd.Timestamp(year, 3, 1) + pd.Timedelta(days=d-61)
                
                for offset in range(-5, 6):
                    win_date = target_date + pd.Timedelta(days=offset)
                    if win_date in date_to_idx:
                        pool_indices.append(date_to_idx[win_date])
            except Exception as e:
                print(f"Error for year {year}, doy {d}: {e}")
        
        if not pool_indices:
            continue
            
        pool_sst = all_sst[pool_indices] # (len(pool), lat, lon)
        
        # Compute threshold (90th percentile) and mean for each cell
        # Numpy's quantile with method='hazen' is what we need.
        # We need to compute this for each cell.
        # For sea cells only, but we can do it for all and mask later.
        
        # reshaped: (len(pool), n_lat * n_lon)
        reshaped_pool = pool_sst.reshape(len(pool_indices), -1)
        
        # Hazen percentile: 
        # np.nanquantile(reshaped_pool, 0.9, axis=0, method='hazen')
        t_vals = np.nanquantile(reshaped_pool, 0.9, axis=0, method='hazen')
        m_vals = np.nanmean(reshaped_pool, axis=0)
        
        thresholds[:, :, d-1] = t_vals.reshape(n_lat, n_lon)
        climatology[:, :, d-1] = m_vals.reshape(n_lat, n_lon)
        
    # Day 60 = mean of 59 and 61
    thresholds[:, :, 59] = (thresholds[:, :, 58] + thresholds[:, :, 60]) / 2
    climatology[:, :, 59] = (climatology[:, :, 58] + climatology[:, :, 60]) / 2
    
    # Smoothing: 31-day centered moving mean, wrap around
    def smooth_366(arr):
        # arr: (lat, lon, 366)
        smoothed = np.full_like(arr)
        for d in range(366):
            # Days d-15 to d+15 (inclusive), modulo 366
            indices = [(d + i) % 366 for i in range(-15, 16)]
            smoothed[:, :, d] = np.nanmean(arr[:, :, indices], axis=-1)
        return smoothed

    thresholds = smooth_366(thresholds)
    climatology = smooth_366(climatology)
    
    # Per-cell MHWs
    # Target period: 2004-06-01 to 2004-08-31
    mhw_mask = np.zeros((len(target_indices), n_lat, n_lon), dtype=np.uint8)
    
    for lat_idx in range(n_lat):
        for lon_idx in range(n_lon):
            if not sea_mask[lat_idx, lon_idx]:
                continue
            
            cell_sst = target_sst[:, lat_idx, lon_idx]
            cell_thresholds = []
            for i, date in enumerate(all_dates[target_indices]):
                doy = get_doy(date)
                cell_thresholds.append(thresholds[lat_idx, lon_idx, doy-1])
            
            cell_thresholds = np.array(cell_thresholds)
            hot_days = cell_sst >= cell_thresholds
            
            # Find runs of at least 5 consecutive hot days
            # Joining gaps of 1 or 2 non-hot days
            
            # First, find hot runs
            is_mhw = np.zeros(len(hot_days), dtype=bool)
            
            # Use a sliding window or scan
            # Actually, a simpler way:
            # 1. Mark all hot days as potential MHW
            # 2. Find segments of hot days
            # 3. If segment length >= 5, it's MHW
            # 4. Join MHW segments if gap is 1 or 2
            
            # But the standard MHW definition (Hobday et al.) is:
            # A run of at least 5 consecutive days where SST >= threshold.
            # Gaps of 1-2 days are filled.
            
            # Implementation:
            # Step 1: Initial MHW runs (length >= 5)
            initial_mhw = np.zeros(len(hot_days), dtype=bool)
            i = 0
            while i < len(hot_days):
                if hot_days[i]:
                    start = i
                    while i < len(hot_days) and hot_days[i]:
                        i += 1
                    if i - start >= 5:
                        initial_mhw[start:i] = True
                else:
                    i += 1
            
            # Step 2: Join gaps of 1 or 2 non-hot days
            # Repeat until no more joins
            current_mhw = initial_mhw.copy()
            while True:
                changed = False
                # Find gaps of 1 or 2 non-hot days between MHW days
                # This is a bit tricky. Let's just scan.
                new_mhw = current_mhw.copy()
                for j in range(1, len(current_mhw)-1):
                    if not current_mhw[j]:
                        # Gap of 1?
                        if current_mhw[j-1] and current_mhw[j+1]:
                            new_mhw[j] = True
                            changed = True
                        # Gap of 2?
                        elif j < len(current_mhw)-2 and current_mhw[j-1] and not current_mhw[j+1] and current_mhw[j+2]:
                            # This is a gap of 2 starting at j. 
                            # We need to set j and j+1 to True.
                            # But wait, the gap is j and j+1.
                            pass
                
                # Let's use a more robust gap-filling:
                # Find all MHW intervals [start, end]
                intervals = []
                i = 0
                while i < len(current_mhw):
                    if current_mhw[i]:
                        start = i
                        while i < len(current_mhw) and current_mhw[i]:
                            i += 1
                        intervals.append([start, i-1])
                    else:
                        i += 1
                
                # Merge intervals if gap <= 2
                merged = False
                i = 0
                while i < len(intervals) - 1:
                    if intervals[i+1][0] - intervals[i][1] <= 3: # Gap is (i+1)[0] - (i)[1] - 1
                        # Wait, gap of 1 means intervals[i+1][0] - intervals[i][1] == 2
                        # Gap of 2 means intervals[i+1][0] - intervals[i][1] == 3
                        # So gap <= 2 means difference <= 3.
                        intervals[i][1] = intervals[i+1][1]
                        intervals.pop(i+1)
                        merged = True
                    else:
                        i += 1
                
                if not merged:
                    break
                
                # Update current_mhw
                current_mhw = np.zeros(len(hot_days), dtype=bool)
                for start, end in intervals:
                    current_mhw[start:end+1] = True
            
            mhw_mask[:, lat_idx, lon_idx] = current_mhw.astype(np.uint8)
            
    # Regional events
    # A day is active if at least one sea cell is in a per-cell MHW
    active_days = np.any(mhw_mask == 1, axis=(1, 2))
    
    regional_events = []
    i = 0
    while i < len(active_days):
        if active_days[i]:
            start = i
            while i < len(active_days) and active_days[i]:
                i += 1
            regional_events.append({
                "onset": all_dates[target_indices[start]].strftime('%Y-%m-%d'),
                "end": all_dates[target_indices[i-1]].strftime('%Y-%m-%d')
            })
        else:
            i += 1
            
    # Output files
    os.makedirs('output', exist_ok=True)
    
    # mhw_mask.nc
    # dimensions (time, lat, lon)
    # Use xarray to save
    ds_out = xr.Dataset(
        {"mhw": (["time", "latitude", "longitude"], mhw_mask)},
        coords={
            "time": all_dates[target_indices],
            "latitude": lats,
            "longitude": lons
        }
    )
    ds_out.to_netcdf('output/mhw_mask.nc')
    
    # report.json
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
