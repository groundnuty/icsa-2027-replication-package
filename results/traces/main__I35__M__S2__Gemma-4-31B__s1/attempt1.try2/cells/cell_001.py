import xarray as xr
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import json

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
    ds = xr.open_dataset(FILE_PATH, engine="h5netcdf")
    sst_var = "sst" # Assuming the variable name is sst based on common CMEMS naming
    # Check variable names
    if sst_var not in ds.variables:
        # Try to find a variable that looks like SST
        for var in ds.variables:
            if "sst" in var.lower() or "temp" in var.lower():
                sst_var = var
                break

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
    # Target_sst shape: (time, lat, lon)
    finite_mask = np.all(np.isfinite(target_sst), axis=0)
    sea_cells = np.where(finite_mask)
    
    # Step 2: Threshold and Climatology
    # Baseline years: 1992-2002
    # Need dates from 1991-12-27 to 2003-01-05 to cover windows
    baseline_ds = ds_region.sel({time_name: slice("1991-12-27", "2003-01-05")})
    baseline_sst = baseline_ds[sst_var].values.astype(np.float64)
    baseline_times = pd.to_datetime(baseline_ds[time_name].values)

    # Map each date to its DOY
    doy_map = {t: get_doy(t.to_pydatetime()) for t in baseline_times}
    
    # Create pools for each DOY 1-366 (excluding 60)
    # Pool for DOY d: union of [T-5, T+5] for all T in 1992-2002 with DOY d.
    baseline_start_dt = pd.to_datetime(BASELINE_START)
    baseline_end_dt = pd.to_datetime(BASELINE_END)
    
    # Fixed dates in 1992-2002
    baseline_dates_in_range = [t for t in baseline_times if baseline_start_dt <= t <= baseline_end_dt]
    
    thresholds = np.full((367, *target_sst.shape[1:]), np.nan, dtype=np.float64)
    climatology = np.full((367, *target_sst.shape[1:]), np.nan, dtype=np.float64)

    # Pre-calculate date indices for faster access
    time_to_idx = {t: i for i, t in enumerate(baseline_times)}

    for d in range(1, 367):
        if d == 60:
            continue
        
        # Find all baseline dates T with DOY d
        dates_with_doy = [t for t in baseline_dates_in_range if doy_map[t] == d]
        
        if not dates_with_doy:
            continue
            
        # Find union of [T-5, T+5]
        pool_dates = set()
        for t in dates_with_doy:
            for offset in range(-5, 6):
                win_date = t + timedelta(days=offset)
                if win_date in time_to_idx:
                    pool_dates.add(time_to_idx[win_date])
        
        if not pool_dates:
            continue
            
        # Get SST values for these dates
        # indices = list(pool_dates)
        # pool_sst = baseline_sst[indices, :, :] # shape (num_dates, lat, lon)
        
        # To be memory efficient, process the pool
        pool_sst = baseline_sst[list(pool_dates), :, :]
        
        # Threshold: 90th percentile (hazen)
        # numpy.quantile(..., method="hazen")
        thresholds[d] = np.nanquantile(pool_sst, 0.9, axis=0, method="hazen")
        # Climatology: Mean
        climatology[d] = np.nanmean(pool_sst, axis=0)

    # Handle DOY 60
    thresholds[60] = (thresholds[59] + thresholds[61]) / 2
    climatology[60] = (climatology[59] + climatology[61]) / 2

    # Smoothing: 31-day centred moving mean (wrap around 366)
    def smooth(arr):
        # arr shape (367, lat, lon). We only care about 1-366.
        # Let's use a 0-indexed array of size 366.
        data = arr[1:] # 0 to 365
        smoothed = np.zeros_like(data)
        for d in range(366):
            # Window: d-15 to d+15
            indices = [(d + i) % 366 for i in range(-15, 16)]
            smoothed[d] = np.mean(data[indices], axis=0)
        return smoothed

    smooth_thresh = smooth(thresholds)
    smooth_clim = smooth(climatology)

    # Step 3: Per-cell MHWs
    # Target period dates and DOYs
    target_dates = pd.to_datetime(target_times)
    target_doys = [get_doy(t.to_pydatetime()) for t in target_dates]
    
    # Map target_doys to indices for smooth_thresh (1-366 -> 0-365)
    # If doy is 60, it's index 59.
    # We need to handle non-leap years carefully. 
    # In 2009 (non-leap), DOY 60 doesn't exist.
    # target_doys already uses get_doy.
    
    mhw_mask = np.zeros(target_sst.shape, dtype=np.uint8)
    
    # We only care about sea cells
    lat_indices, lon_indices = sea_cells
    for lat_idx, lon_idx in zip(lat_indices, lon_indices):
        # SST for this cell
        cell_sst = target_sst[:, lat_idx, lon_idx]
        
        # Thresholds for this cell on target days
        cell_thresh = np.array([smooth_thresh[doy-1, lat_idx, lon_idx] for doy in target_doys])
        
        # Hot days
        hot = cell_sst >= cell_thresh
        
        # Find runs of at least 5 consecutive hot days
        # Use a simple run-length encoding or loop
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
        
        # Join runs separated by 1 or 2 non-hot days
        if not runs:
            continue
            
        merged_runs = []
        if runs:
            curr_start, curr_end = runs[0]
            for i in range(1, len(runs)):
                next_start, next_end = runs[i]
                if next_start - curr_end - 1 <= 2:
                    curr_end = next_end
                else:
                    merged_runs.append([curr_start, curr_end])
                    curr_start, curr_end = next_start, next_end
            merged_runs.append([curr_start, curr_end])
        
        # Mark MHW in mask
        for start, end in merged_runs:
            mhw_mask[start:end+1, lat_idx, lon_idx] = 1

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

    # Save output/mhw_mask.nc
    # Create xarray dataset
    out_ds = xr.Dataset(
        {"mhw": (["time", lat_name, lon_name], mhw_mask)},
        coords={
            time_name: target_times,
            lat_name: ds_region[lat_name].values,
            lon_name: ds_region[lon_name].values
        }
    )
    out_ds.to_netcdf("output/mhw_mask.nc")

    # Save output/report.json
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
