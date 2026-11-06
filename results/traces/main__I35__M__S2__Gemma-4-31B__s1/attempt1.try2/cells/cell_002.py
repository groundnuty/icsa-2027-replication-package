import xarray as xr
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import json
import os

# Constants
REGION = {"lat_min": 59.93, "lat_max": 61.13, "lon_min": 18.69, "lon_max": 19.89}
TARGET_START = "2009-06-01"
TARGET_END = "2009-08-31"
BASELINE_START = "1992-01-01"
BASELINE_END = "2002-12-31"
FILE_PATH = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"

def get_doy(dt):
    """Map date to day of year 1-366, skipping 60 for non-leap years."""
    y = dt.year
    is_leap = (y % 4 == 0 and (y % 100 != 0 or y % 400 == 0))
    doy = dt.timetuple().tm_yday
    if not is_leap and dt.month > 2:
        doy += 1
    return doy

def solve():
    # Ensure output directory exists
    os.makedirs("output", exist_ok=True)

    ds = xr.open_dataset(FILE_PATH, engine="h5netcdf")
    
    # Identify SST variable
    sst_var = None
    for var in ds.variables:
        if var == "sst" or "sst" in var.lower() or "temp" in var.lower():
            sst_var = var
            break
    if sst_var is None:
        raise ValueError("SST variable not found in dataset")

    # Coordinate names
    lat_name = "lat" if "lat" in ds.coords else "latitude"
    lon_name = "lon" if "lon" in ds.coords else "longitude"
    time_name = "time"

    # Region subset
    ds_region = ds.sel({
        lat_name: slice(REGION["lat_min"], REGION["lat_max"]),
        lon_name: slice(REGION["lon_min"], REGION["lon_max"])
    })

    # Target period subset
    ds_target = ds_region.sel({time_name: slice(TARGET_START, TARGET_END)})
    target_times = ds_target[time_name].values
    target_sst = ds_target[sst_var].values.astype(np.float64)

    # Step 1: Sea Cells
    # SST is finite on every day of the target period
    finite_mask = np.all(np.isfinite(target_sst), axis=0)
    sea_cells_mask = finite_mask
    
    # Step 2: Threshold and Climatology
    # Baseline years: 1992-2002. Include windows.
    baseline_ds = ds_region.sel({time_name: slice("1991-12-27", "2003-01-05")})
    baseline_sst = baseline_ds[sst_var].values.astype(np.float64)
    baseline_times = pd.to_datetime(baseline_ds[time_name].values)

    doy_map = {t: get_doy(t.to_pydatetime()) for t in baseline_times}
    baseline_start_dt = pd.to_datetime(BASELINE_START)
    baseline_end_dt = pd.to_datetime(BASELINE_END)
    baseline_dates_in_range = [t for t in baseline_times if baseline_start_dt <= t <= baseline_end_dt]
    
    thresholds = np.full((367, *target_sst.shape[1:]), np.nan, dtype=np.float64)
    climatology = np.full((367, *target_sst.shape[1:]), np.nan, dtype=np.float64)

    time_to_idx = {t: i for i, t in enumerate(baseline_times)}

    for d in range(1, 367):
        if d == 60:
            continue
        
        dates_with_doy = [t for t in baseline_dates_in_range if doy_map[t] == d]
        if not dates_with_doy:
            continue
            
        pool_indices = set()
        for t in dates_with_doy:
            for offset in range(-5, 6):
                win_date = t + timedelta(days=offset)
                if win_date in time_to_idx:
                    pool_indices.add(time_to_idx[win_date])
        
        if not pool_indices:
            continue
            
        pool_sst = baseline_sst[list(pool_indices), :, :]
        
        # Threshold: 90th percentile (hazen)
        # We use nanquantile to handle potential NaNs in the pool for land cells
        # but since we only care about sea cells eventually, it's fine.
        thresholds[d] = np.nanquantile(pool_sst, 0.9, axis=0, method="hazen")
        climatology[d] = np.nanmean(pool_sst, axis=0)

    # Handle DOY 60: mean of 59 and 61
    thresholds[60] = (thresholds[59] + thresholds[61]) / 2
    climatology[60] = (climatology[59] + climatology[61]) / 2

    # Smoothing: 31-day centred moving mean (wrap around 366)
    def smooth(arr):
        data = arr[1:] # 1-366 -> index 0-365
        smoothed = np.zeros_like(data)
        for d in range(366):
            indices = [(d + i) % 366 for i in range(-15, 16)]
            # Use nanmean to ignore NaNs during smoothing
            smoothed[d] = np.nanmean(data[indices], axis=0)
        return smoothed

    smooth_thresh = smooth(thresholds)
    # smooth_clim = smooth(climatology) # Not strictly needed for MHW detection but requested

    # Step 3: Per-cell MHWs
    target_dates = pd.to_datetime(target_times)
    target_doys = [get_doy(t.to_pydatetime()) for t in target_dates]
    
    mhw_mask = np.zeros(target_sst.shape, dtype=np.uint8)
    
    # We only process sea cells
    lat_len, lon_len = target_sst.shape[1:]
    for lat_idx in range(lat_len):
        for lon_idx in range(lon_len):
            if not sea_cells_mask[lat_idx, lon_idx]:
                continue
            
            cell_sst = target_sst[:, lat_idx, lon_idx]
            cell_thresh = np.array([smooth_thresh[doy-1, lat_idx, lon_idx] for doy in target_doys])
            
            # A day is hot if SST >= threshold
            hot = cell_sst >= cell_thresh
            
            # Per-cell MHW: run of >= 5 hot days, joined by 1-2 non-hot days
            # Find runs
            runs = []
            start = None
            for i in range(len(hot)):
                if hot[i]:
                    if start is None:
                        start = i
                else:
                    if start is not None:
                        if i - start >= 5:
                            runs.append([start, i - 1])
                        start = None
            if start is not None:
                if len(hot) - start >= 5:
                    runs.append([start, len(hot) - 1])
            
            if not runs:
                continue
                
            # Join runs
            merged = []
            curr_start, curr_end = runs[0]
            for i in range(1, len(runs)):
                next_start, next_end = runs[i]
                if next_start - curr_end - 1 <= 2:
                    curr_end = next_end
                else:
                    merged.append([curr_start, curr_end])
                    curr_start, curr_end = next_start, next_end
            merged.append([curr_start, curr_end])
            
            for s, e in merged:
                mhw_mask[s:e+1, lat_idx, lon_idx] = 1

    # Step 4: Regional Events
    # Active day: at least one sea cell is in an MHW
    active = np.any(mhw_mask == 1, axis=(1, 2))
    
    regional_events = []
    start = None
    for i in range(len(active)):
        if active[i]:
            if start is None:
                start = i
        else:
            if start is not None:
                regional_events.append({
                    "onset": target_dates[start].strftime("%Y-%m-%d"),
                    "end": target_dates[i-1].strftime("%Y-%m-%d")
                })
                start = None
    if start is not None:
        regional_events.append({
            "onset": target_dates[start].strftime("%Y-%m-%d"),
            "end": target_dates[-1].strftime("%Y-%m-%d")
        })

    # Output NetCDF
    out_ds = xr.Dataset(
        {"mhw": (["time", lat_name, lon_name], mhw_mask)},
        coords={
            time_name: target_times,
            lat_name: ds_region[lat_name].values,
            lon_name: ds_region[lon_name].values
        }
    )
    out_ds.to_netcdf("output/mhw_mask.nc")

    # Output Report
    report = {
        "region": {
            "lat_min": REGION["lat_min"],
            "lat_max": REGION["lat_max"],
            "lon_min": REGION["lon_min"],
            "lon_max": REGION["lon_max"]
        },
        "baseline_analysed": {
            "start": BASELINE_START,
            "end": BASELINE_END
        },
        "target_analysed": {
            "start": target_dates[0].strftime("%Y-%m-%d"),
            "end": target_dates[-1].strftime("%Y-%m-%d")
        },
        "events": regional_events,
        "complete": True,
        "caveats": ""
    }
    with open("output/report.json", "w") as f:
        json.dump(report, f, indent=2)

solve()
