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
    
    # 1. Slice region
    # Check coordinate directions
    lat_coords = ds.lat.values
    lon_coords = ds.lon.values
    
    if lat_coords[0] > lat_coords[-1]:
        lat_slice = slice(LAT_MAX, LAT_MIN)
    else:
        lat_slice = slice(LAT_MIN, LAT_MAX)
        
    if lon_coords[0] > lon_coords[-1]:
        lon_slice = slice(LON_MAX, LON_MIN)
    else:
        lon_slice = slice(LON_MIN, LON_MAX)
        
    ds_reg = ds.sel(lat=lat_slice, lon=lon_slice)
    
    # Define time ranges
    # Baseline windows: 1992-01-01 to 2002-12-31, each +/- 5 days
    # Total baseline window: 1991-12-27 to 2003-01-05
    b_start = pd.Timestamp("1991-12-27")
    b_end = pd.Timestamp("2003-01-05")
    t_start = pd.Timestamp(TARGET_START)
    t_end = pd.Timestamp(TARGET_END)
    
    # Load SST for both periods
    sst_baseline = ds_reg.sst.sel(time=slice(b_start, b_end)).load()
    sst_target = ds_reg.sst.sel(time=slice(t_start, t_end)).load()
    
    # Identify sea cells (finite on every day of target period)
    # sst_target is (time, lat, lon)
    is_finite = np.isfinite(sst_target.values).all(axis=0)
    sea_cells_mask = is_finite
    
    # 2. Threshold and Climatology
    #Baseline years: 1992-2002
    baseline_years = range(BASELINE_START_YEAR, BASELINE_END_YEAR + 1)
    
    # Pre-calculate DOY for all dates in sst_baseline
    baseline_times = pd.to_datetime(sst_baseline.time.values)
    baseline_doy = np.array([get_custom_doy(t) for t in baseline_times])
    
    # We need thresholds and climatology for each sea cell and day of year (1-366)
    n_lat = sst_baseline.shape[1]
    n_lon = sst_baseline.shape[2]
    
    thresholds = np.full((366, n_lat, n_lon), np.nan, dtype=np.float64)
    climatology = np.full((366, n_lat, n_lon), np.nan, dtype=np.float64)
    
    # To optimize, we'll iterate over DOY d
    for d in range(1, 367):
        if d == 60:
            continue
        
        # Find all baseline dates with DOY d
        # Baseline dates must be within [1992-01-01, 2002-12-31]
        pool_indices = []
        for y in baseline_years:
            try:
                # Find the date in year y with DOY d
                # Using the same 2000-leap-year mapping:
                # Date with DOY d in year y is:
                # datetime(y, 1, 1) + timedelta(days=d-1) ? 
                # No, that's not quite right because of leap years.
                # Let's find the date in year y that maps to d.
                # We can just check all dates in that year.
                pass
            except:
                pass
        
        # Better way:
        # Find all dates in baseline_times that map to d.
        # Then for each such date, find dates within +/- 5 days.
        
        # Baseline dates (1992-01-01 to 2002-12-31) with DOY d
        # Note: baseline_times includes the extensions 1991-12-27 and 2003-01-05.
        # We only center windows on dates WITHIN the actual baseline range.
        
        center_dates_indices = np.where(
            (baseline_doy == d) & 
            (baseline_times >= pd.Timestamp(f"{BASELINE_START_YEAR}-01-01")) & 
            (baseline_times <= pd.Timestamp(f"{BASELINE_END_YEAR}-12-31"))
        )[0]
        
        if len(center_dates_indices) == 0:
            continue
            
        # For each center date, the window is +/- 5 days.
        # We can collect all indices in sst_baseline that fall into any of these windows.
        all_window_indices = set()
        for idx in center_dates_indices:
            center_date = baseline_times[idx]
            window_start = center_date - timedelta(days=5)
            window_end = center_date + timedelta(days=5)
            
            # Find indices in baseline_times that are within [window_start, window_end]
            # Since baseline_times is sorted, we can use searchsorted
            idx_start = np.searchsorted(baseline_times, window_start)
            idx_end = np.searchsorted(baseline_times, window_end, side='right')
            for i in range(idx_start, idx_end):
                all_window_indices.add(i)
                
        pool_indices = np.array(list(all_window_indices))
        if len(pool_indices) == 0:
            continue
            
        # Extract pool for all cells: (len(pool), n_lat, n_lon)
        pool = sst_baseline.values[pool_indices, :, :]
        
        # Calculate 90th percentile (Hazen) and mean
        # numpy.nanpercentile with method='hazen' is used
        # We calculate per cell.
        thresholds[d-1, :, :] = np.nanpercentile(pool, 90, axis=0, method='hazen')
        climatology[d-1, :, :] = np.nanmean(pool, axis=0)
        
    # Handle day 60
    thresholds[59, :, :] = (thresholds[58, :, :] + thresholds[60, :, :]) / 2
    climatology[59, :, :] = (climatology[58, :, :] + climatology[60, :, :]) / 2
    
    # Smoothing: 31-day centered moving mean (wrapped)
    def smooth_366(arr):
        # arr is (366, n_lat, n_lon)
        smoothed = np.zeros_like(arr)
        for d in range(366):
            # Days d-15 to d+15 (modulo 366)
            window_indices = [(d + k) % 366 for k in range(-15, 16)]
            smoothed[d, :, :] = np.nanmean(arr[window_indices, :, :], axis=0)
        return smoothed

    thresholds = smooth_366(thresholds)
    climatology = smooth_366(climatology)
    
    # 3. Per-cell MHWs
    target_times = pd.to_datetime(sst_target.time.values)
    target_doy = np.array([get_custom_doy(t) for t in target_times])
    
    # Hot days mask
    # SST is (time, lat, lon), thresholds is (366, lat, lon)
    # We need to index thresholds by target_doy
    # target_doy is 1-366
    hot_mask = np.zeros(sst_target.shape, dtype=bool)
    for t_idx, d in enumerate(target_doy):
        hot_mask[t_idx, :, :] = sst_target.values[t_idx, :, :] >= thresholds[d-1, :, :]
        
    # Per-cell MHW logic
    # For each cell, find runs of >= 5 hot days, then join gaps of 1-2 days.
    mhw_mask = np.zeros(sst_target.shape, dtype=np.uint8)
    
    for i in range(n_lat):
        for j in range(n_lon):
            if not sea_cells_mask[i, j]:
                continue
            
            cell_hot = hot_mask[:, i, j]
            n_days = len(cell_hot)
            is_mhw = np.zeros(n_days, dtype=bool)
            
            # Find initial runs of >= 5
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
            
            # Join gaps of 1-2 days
            # Keep repeating until no more merges
            changed = True
            while changed:
                changed = False
                # Find blocks of is_mhw
                # A gap of 1-2 days is a sequence of 1 or 2 False between True
                for t in range(1, n_days - 1):
                    if not is_mhw[t] and is_mhw[t-1] and ( (t+1 < n_days and is_mhw[t+1]) or (t+2 < n_days and is_mhw[t+2]) ):
                        # Gap of 1 day (t) between is_mhw[t-1] and is_mhw[t+1] or is_mhw[t+2]
                        # Actually, if is_mhw[t-1] and is_mhw[t+1], gap is 1.
                        # If is_mhw[t-1] and is_mhw[t+2] and not is_mhw[t+1], gap is 2.
                        pass
                
                # Simpler gap filling:
                # If we have True, then 1 or 2 False, then True, fill the False.
                for t in range(n_days):
                    if not is_mhw[t]:
                        # Check for gap of 1
                        if t > 0 and t < n_days - 1 and is_mhw[t-1] and is_mhw[t+1]:
                            is_mhw[t] = True
                            changed = True
                        # Check for gap of 2
                        elif t > 0 and t < n_days - 2 and is_mhw[t-1] and not is_mhw[t+1] and is_mhw[t+2]:
                            is_mhw[t] = True
                            is_mhw[t+1] = True
                            changed = True
                        elif t > 1 and t < n_days - 1 and is_mhw[t-2] and not is_mhw[t-1] and is_mhw[t]:
                            # This case is covered by the gap of 2 logic when t was t-1
                            pass
            
            mhw_mask[:, i, j] = is_mhw.astype(np.uint8)
            
    # 4. Regional Events
    # active_days: (time,)
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
        
    # Write output NC
    # Coordinates for output
    out_ds = xr.Dataset(
        {"mhw": (("time", "lat", "lon"), mhw_mask)},
        coords={
            "time": sst_target.time,
            "lat": sst_target.lat,
            "lon": sst_target.lon
        }
    )
    os.makedirs("output", exist_ok=True)
    out_ds.to_netcdf("output/mhw_mask.nc")
    
    # Write report JSON
    report = {
        "region": {
            "lat_min": float(LAT_MIN),
            "lat_max": float(LAT_MAX),
            "lon_min": float(LON_MIN),
            "lon_max": float(LON_MAX)
        },
        "baseline_analysed": {
            "start": b_start.strftime("%Y-%m-%d"),
            "end": b_end.strftime("%Y-%m-%d")
        },
        "target_analysed": {
            "start": t_start.strftime("%Y-%m-%d"),
            "end": t_end.strftime("%Y-%m-%d")
        },
        "events": events,
        "complete": True,
        "caveats": ""
    }
    with open("output/report.json", "w") as f:
        json.dump(report, f, indent=2)

solve()
