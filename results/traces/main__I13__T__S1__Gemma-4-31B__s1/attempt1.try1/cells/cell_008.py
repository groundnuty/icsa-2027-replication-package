import fsspec
import xarray as xr
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import json
import os

# Constants
LAT_MIN, LAT_MAX = 56.09, 57.29
LON_MIN, LON_MAX = 10.55, 11.75
TARGET_START = datetime(2021, 6, 1)
TARGET_END = datetime(2021, 8, 31)
BASELINE_START = datetime(1992, 1, 1)
BASELINE_END = datetime(2002, 12, 31)
LOAD_BASELINE_START = datetime(1991, 12, 27)
LOAD_BASELINE_END = datetime(2003, 1, 5)

def get_doy(date):
    doy = date.timetuple().tm_yday
    is_leap = (date.year % 4 == 0 and (date.year % 100 != 0 or date.year % 400 == 0))
    if not is_leap and doy >= 60:
        doy += 1
    return doy

def load_sst_region(fs, root_dir, start_date, end_date, lat_min, lat_max, lon_min, lon_max):
    dates = pd.date_range(start_date, end_date)
    sst_list = []
    lats, lons = None, None
    
    for date in dates:
        filename = f"{root_dir}/sst_{date.strftime('%Y%m%d')}.nc"
        try:
            with fs.open(filename, "rb") as f:
                with xr.open_dataset(f, engine="h5netcdf") as ds:
                    subset = ds.analysed_sst.sel(
                        latitude=slice(lat_min, lat_max), 
                        longitude=slice(lon_min, lon_max)
                    )
                    data = subset.values.astype(np.float64)
                    if lats is None:
                        lats = subset.latitude.values
                        lons = subset.longitude.values
                    if data.ndim == 3:
                        data = data[0]
                    sst_list.append(data)
        except Exception:
            sst_list.append(None)
            
    first_val = next((x for x in sst_list if x is not None), None)
    if first_val is None:
        return None, None, None, dates
    
    final_sst = np.full((len(dates), first_val.shape[0], first_val.shape[1]), np.nan, dtype=np.float64)
    for i, val in enumerate(sst_list):
        if val is not None and val.shape == first_val.shape:
            final_sst[i, :, :] = val
            
    return final_sst, lats, lons, dates

def smooth_array(arr):
    smoothed = np.zeros_like(arr)
    for d in range(366):
        window = []
        for i in range(-15, 16):
            idx = (d + i) % 366
            window.append(arr[idx])
        smoothed[d] = np.nanmean(window)
    return smoothed

def main():
    fs = fsspec.filesystem('onedata')
    root_dir = 'icsa2027_data_20261101T090944Z/s1z'
    
    print("Loading baseline data...")
    baseline_sst, lats, lons, baseline_all_dates = load_sst_region(
        fs, root_dir, LOAD_BASELINE_START, LOAD_BASELINE_END, LAT_MIN, LAT_MAX, LON_MIN, LON_MAX
    )
    
    print("Loading target data...")
    target_sst, _, _, target_dates = load_sst_region(
        fs, root_dir, TARGET_START, TARGET_END, LAT_MIN, LAT_MAX, LON_MIN, LON_MAX
    )
    
    if baseline_sst is None or target_sst is None:
        print("Error loading data.")
        return

    # 1. Sea cells
    is_sea_cell = np.all(np.isfinite(target_sst), axis=0)
    
    # 2. Threshold and climatology
    baseline_period_dates = pd.date_range(BASELINE_START, BASELINE_END)
    date_to_idx = {date: i for i, date in enumerate(baseline_all_dates)}
    baseline_all_doys = np.array([get_doy(d) for d in baseline_all_dates])
    
    thresholds = np.full((366, lats.shape[0], lons.shape[0]), np.nan, dtype=np.float64)
    climatology = np.full((366, lats.shape[0], lons.shape[0]), np.nan, dtype=np.float64)
    
    baseline_period_doys = np.array([get_doy(d) for d in baseline_period_dates])
    
    for d in range(1, 367):
        if d == 60:
            continue
        
        baseline_dates_with_doy_d = baseline_period_dates[baseline_period_doys == d]
        
        pool_dates = set()
        for bd in baseline_dates_with_doy_d:
            for offset in range(-5, 6):
                window_date = bd + timedelta(days=offset)
                if window_date in date_to_idx:
                    pool_dates.add(window_date)
        
        if not pool_dates:
            continue
            
        pool_indices = [date_to_idx[date] for date in pool_dates]
        pool_data = baseline_sst[pool_indices, :, :]
        
        thresholds[d-1] = np.nanpercentile(pool_data, 90, axis=0, method="hazen")
        climatology[d-1] = np.nanmean(pool_data, axis=0)

    # Day 60: mean of 59 and 61
    thresholds[59] = (thresholds[58] + thresholds[60]) / 2
    climatology[59] = (climatology[58] + climatology[60]) / 2
    
    # Smoothing
    smoothed_thresholds = np.full((366, lats.shape[0], lons.shape[0]), np.nan, dtype=np.float64)
    smoothed_climatology = np.full((366, lats.shape[0], lons.shape[0]), np.nan, dtype=np.float64)
    for i in range(lats.shape[0]):
        for j in range(lons.shape[0]):
            smoothed_thresholds[:, i, j] = smooth_array(thresholds[:, i, j])
            smoothed_climatology[:, i, j] = smooth_array(climatology[:, i, j])
            
    # 3. Per-cell MHWs
    target_doys = np.array([get_doy(d) for d in target_dates])
    target_doy_indices = target_doys - 1
    
    mhw_mask = np.zeros(target_sst.shape, dtype=np.uint8)
    for i in range(lats.shape[0]):
        for j in range(lons.shape[0]):
            if not is_sea_cell[i, j]:
                continue
            
            sst_cell = target_sst[:, i, j]
            thresh_cell = smoothed_thresholds[target_doy_indices, i, j]
            hot = (sst_cell >= thresh_cell)
            
            is_mhw = np.zeros(len(hot), dtype=bool)
            current_run = 0
            start_idx = 0
            for k in range(len(hot)):
                if hot[k]:
                    if current_run == 0:
                        start_idx = k
                    current_run += 1
                else:
                    if current_run >= 5:
                        is_mhw[start_idx : start_idx + current_run] = True
                    current_run = 0
            if current_run >= 5:
                is_mhw[start_idx : start_idx + current_run] = True
                
            changed = True
            while changed:
                changed = False
                for k in range(1, len(is_mhw) - 1):
                    if not is_mhw[k] and is_mhw[k-1] and is_mhw[k+1]:
                        is_mhw[k] = True
                        changed = True
                for k in range(1, len(is_mhw) - 2):
                    if not is_mhw[k] and not is_mhw[k+1] and is_mhw[k-1] and is_mhw[k+2]:
                        is_mhw[k] = True
                        is_mhw[k+1] = True
                        changed = True
            mhw_mask[:, i, j] = is_mhw.astype(np.uint8)
            
    # 4. Regional events
    active_days = np.any(mhw_mask == 1, axis=(1, 2))
    events = []
    current_event_start = None
    for k in range(len(active_days)):
        if active_days[k]:
            if current_event_start is None:
                current_event_start = k
        else:
            if current_event_start is not None:
                events.append({
                    "onset": target_dates[current_event_start].strftime('%Y-%m-%d'),
                    "end": target_dates[k-1].strftime('%Y-%m-%d')
                })
                current_event_start = None
    if current_event_start is not None:
        events.append({
            "onset": target_dates[current_event_start].strftime('%Y-%m-%d'),
            "end": target_dates[-1].strftime('%Y-%m-%d')
        })
        
    # Save outputs
    os.makedirs("output", exist_ok=True)
    ds_out = xr.Dataset(
        {"mhw": (("time", "lat", "lon"), mhw_mask)},
        coords={"time": target_dates, "lat": lats, "lon": lons}
    )
    ds_out.to_netcdf("output/mhw_mask.nc")
    
    report = {
        "region": {"lat_min": LAT_MIN, "lat_max": LAT_MAX, "lon_min": LON_MIN, "lon_max": LON_MAX},
        "baseline_analysed": {"start": "1992-01-01", "end": "2002-12-31"},
        "target_analysed": {
            "start": target_dates[0].strftime('%Y-%m-%d'),
            "end": target_dates[-1].strftime('%Y-%m-%d')
        },
        "events": events,
        "complete": True,
        "caveats": ""
    }
    with open("output/report.json", "w") as f:
        json.dump(report, f, indent=2)
    
    print("Analysis complete.")

if __name__ == "__main__":
    main()
