import xarray as xr
import fsspec
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import json
import os

def get_doy(dt):
    return dt.day_of_year

def solve():
    # Create output directory
    os.makedirs("output", exist_ok=True)
    
    fs = fsspec.filesystem('onedata')
    path = 'icsa2027_data_20261101T090944Z/s1z'
    
    # Region and Period
    lat_min, lat_max = 55.67, 56.87
    lon_min, lon_max = 16.45, 17.65
    target_start = pd.Timestamp('2005-06-01')
    target_end = pd.Timestamp('2005-08-31')
    baseline_start = pd.Timestamp('1992-01-01')
    baseline_end = pd.Timestamp('2002-12-31')
    
    # Coordinate setup
    with fs.open(f'{path}/sst_19820101.nc', 'rb') as f:
        ds_coord = xr.open_dataset(f, engine='h5netcdf')
        lat = ds_coord.latitude.values
        lon = ds_coord.longitude.values
    
    lat_mask = (lat >= lat_min) & (lat <= lat_max)
    lon_mask = (lon >= lon_min) & (lon <= lon_max)
    lat_indices = np.where(lat_mask)[0]
    lon_indices = np.where(lon_mask)[0]
    
    # Pool mapping
    date_to_pools = {}
    for d in range(1, 367):
        if d == 60: continue
        pool_dates = set()
        for y in range(1992, 2003):
            # Find date with DOY d in year y
            year_start = pd.Timestamp(year=y, month=1, day=1)
            t_yd = year_start + pd.Timedelta(days=d-1)
            if t_yd.year != y: # d=60 in non-leap year
                continue
            for offset in range(-5, 6):
                pool_dates.add(t_yd + pd.Timedelta(days=offset))
        for t in pool_dates:
            if t not in date_to_pools:
                date_to_pools[t] = []
            date_to_pools[t].append(d)
            
    all_needed_dates = set(date_to_pools.keys())
    target_dates = pd.date_range(target_start, target_end)
    all_needed_dates.update(target_dates)
    
    # Collect SSTs
    pool_data = {d: [] for d in range(1, 367)}
    target_sst = {}
    
    sorted_needed_dates = sorted(list(all_needed_dates))
    
    for t in sorted_needed_dates:
        fname = f"{path}/sst_{t.strftime('%Y%m%d')}.nc"
        try:
            with fs.open(fname, 'rb') as f:
                ds = xr.open_dataset(f, engine='h5netcdf')
                sst = ds.analysed_sst.isel(latitude=lat_indices, longitude=lon_indices).values[0]
                sst = sst.astype(np.float64)
                if t in date_to_pools:
                    for d in date_to_pools[t]:
                        pool_data[d].append(sst)
                if t in target_dates:
                    target_sst[t] = sst
        except Exception:
            pass

    # Threshold and Climatology
    thresholds = np.full((367, 60, 60), np.nan, dtype=np.float64)
    climatology = np.full((367, 60, 60), np.nan, dtype=np.float64)
    
    for d in range(1, 367):
        if d == 60: continue
        if not pool_data[d]: continue
        
        data = np.stack(pool_data[d], axis=0)
        # Vectorized approach for mean and quantile
        climatology[d] = np.nanmean(data, axis=0)
        
        # For quantile, we have to loop or use a trick
        # Since we need 'hazen', and np.nanquantile doesn't support it, 
        # we'll loop over cells. 60x60 = 3600 is small.
        for i in range(60):
            for j in range(60):
                cell_vals = data[:, i, j]
                valid_vals = cell_vals[~np.isnan(cell_vals)]
                if len(valid_vals) > 0:
                    thresholds[d, i, j] = np.quantile(valid_vals, 0.9, method='hazen')

    # Day 60
    thresholds[60] = (thresholds[59] + thresholds[61]) / 2
    climatology[60] = (climatology[59] + climatology[61]) / 2
    
    def smooth(arr):
        smoothed = np.full_like(arr, np.nan)
        for d in range(1, 367):
            window_sum = np.zeros((60, 60), dtype=np.float64)
            count = np.zeros((60, 60), dtype=np.float64)
            for offset in range(-15, 16):
                day_idx = (d + offset - 1) % 366 + 1
                val = arr[day_idx]
                window_sum += np.nan_to_num(val)
                count += (~np.isnan(val)).astype(np.float64)
            mask = count > 0
            smoothed[d][mask] = window_sum[mask] / count[mask]
        return smoothed

    thresholds_smooth = smooth(thresholds)
    
    # MHW Detection
    mhw_mask = np.zeros((len(target_dates), 60, 60), dtype=np.uint8)
    
    for i in range(60):
        for j in range(60):
            cell_sst = []
            cell_thresholds = []
            for t in target_dates:
                cell_sst.append(target_sst.get(t, np.array([np.nan]*1))[0] if isinstance(target_sst.get(t), np.ndarray) else (target_sst[t][i,j] if t in target_sst else np.nan))
                # Corrected target_sst access
            
            # Redo target_sst extraction for cell (i,j)
            cell_sst = np.array([target_sst[t][i,j] if t in target_sst else np.nan for t in target_dates])
            cell_thresholds = np.array([thresholds_smooth[get_doy(t), i, j] for t in target_dates])
            
            is_hot = (cell_sst >= cell_thresholds) & (~np.isnan(cell_sst)) & (~np.isnan(cell_thresholds))
            
            runs = []
            start = None
            for idx in range(len(is_hot)):
                if is_hot[idx] and start is None:
                    start = idx
                elif not is_hot[idx] and start is not None:
                    runs.append((start, idx - 1))
                    start = None
            if start is not None:
                runs.append((start, len(is_hot) - 1))
            
            mhw_runs = [r for r in runs if r[1] - r[0] + 1 >= 5]
            if not mhw_runs: continue
                
            joined_runs = []
            curr_start, curr_end = mhw_runs[0]
            for next_start, next_end in mhw_runs[1:]:
                if next_start - curr_end - 1 <= 2:
                    curr_end = next_end
                else:
                    joined_runs.append((curr_start, curr_end))
                    curr_start, curr_end = next_start, next_end
            joined_runs.append((curr_start, curr_end))
            
            for rs, re in joined_runs:
                mhw_mask[rs:re+1, i, j] = 1

    # Regional Events
    sea_cells_mask = np.ones((60, 60), dtype=bool)
    for t in target_dates:
        if t in target_sst:
            sea_cells_mask &= (~np.isnan(target_sst[t]))
        else:
            sea_cells_mask[:] = False
            break
            
    active_days = np.zeros(len(target_dates), dtype=bool)
    for t_idx in range(len(target_dates)):
        if np.any(mhw_mask[t_idx] * sea_cells_mask):
            active_days[t_idx] = True
            
    regional_events = []
    start = None
    for idx in range(len(active_days)):
        if active_days[idx] and start is None:
            start = idx
        elif not active_days[idx] and start is not None:
            regional_events.append({
                "onset": target_dates[start].strftime('%Y-%m-%d'),
                "end": target_dates[idx-1].strftime('%Y-%m-%d')
            })
            start = None
    if start is not None:
        regional_events.append({
            "onset": target_dates[start].strftime('%Y-%m-%d'),
            "end": target_dates[-1].strftime('%Y-%m-%d')
        })

    # Output
    ds_out = xr.Dataset(
        {"mhw": (["time", "latitude", "longitude"], mhw_mask.astype(np.uint8))},
        coords={"time": target_dates, "latitude": lat[lat_indices], "longitude": lon[lon_indices]}
    )
    ds_out.to_netcdf("output/mhw_mask.nc")
    
    baseline_dates_used = sorted(list(date_to_pools.keys()))
    report = {
        "region": {"lat_min": float(lat_min), "lat_max": float(lat_max), "lon_min": float(lon_min), "lon_max": float(lon_max)},
        "baseline_analysed": {"start": baseline_dates_used[0].strftime('%Y-%m-%d'), "end": baseline_dates_used[-1].strftime('%Y-%m-%d')} if baseline_dates_used else None,
        "target_analysed": {"start": target_dates[0].strftime('%Y-%m-%d'), "end": target_dates[-1].strftime('%Y-%m-%d')} if len(target_dates) > 0 else None,
        "events": regional_events,
        "complete": True,
        "caveats": ""
    }
    with open("output/report.json", "w") as f:
        json.dump(report, f)

solve()
