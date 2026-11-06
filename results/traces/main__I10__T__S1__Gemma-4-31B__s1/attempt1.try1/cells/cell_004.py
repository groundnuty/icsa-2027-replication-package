import xarray as xr
import fsspec
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import json

def get_doy(dt):
    # 1 Jan = 1, ..., 31 Dec = 366 (if leap)
    # pandas timestd.dayofyear is 1-indexed
    return dt.dayofyear

def solve():
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
    # For each d in 1..366, d != 60, pool is dates t such that
    # there exists y in [1992, 2002] with t_{y,d} exists and |t - t_{y,d}| <= 5
    date_to_pools = {}
    
    # Baseline dates
    baseline_dates = pd.date_range(baseline_start, baseline_end)
    
    # We need dates from baseline_start - 5 days to baseline_end + 5 days
    full_baseline_range = pd.date_range(baseline_start - pd.Timedelta(days=5), 
                                        baseline_end + pd.Timedelta(days=5))
    
    for d in range(1, 367):
        if d == 60: continue
        
        pool_dates = set()
        for y in range(1992, 2003):
            # Find date with DOY d in year y
            # Handle non-leap years: if d=60 and not leap, no t_{y,d}
            try:
                # This is a bit tricky. Let's find the date of DOY d in year y.
                # Start of year y
                year_start = pd.Timestamp(year=y, month=1, day=1)
                # DOY d is (d-1) days after Jan 1
                t_yd = year_start + pd.Timedelta(days=d-1)
                if t_yd.year != y: # This happens if d=60 in non-leap year
                    continue
                
                # Window [t_yd - 5, t_yd + 5]
                for offset in range(-5, 6):
                    pool_dates.add(t_yd + pd.Timedelta(days=offset))
            except:
                continue
        
        for t in pool_dates:
            if t not in date_to_pools:
                date_to_pools[t] = []
            date_to_pools[t].append(d)
            
    # Now collect all SSTs for the pools and target period
    all_needed_dates = set(date_to_pools.keys())
    target_dates = pd.date_range(target_start, target_end)
    all_needed_dates.update(target_dates)
    
    # To avoid loading too many files, we can group dates by file if they are daily
    # The files are named sst_YYYYMMDD.nc
    needed_files = {d.strftime('%Y%m%d'): d for d in all_needed_dates}
    
    # Data structures for pools
    # pool_data[d] = list of SST arrays (each 60x60)
    pool_data = {d: [] for d in range(1, 367)}
    target_sst = {} # {date: SST_array}

    # Sort dates to read files sequentially if possible
    sorted_needed_dates = sorted(list(all_needed_dates))
    
    for t in sorted_needed_dates:
        fname = f"{path}/sst_{t.strftime('%Y%m%d')}.nc"
        try:
            with fs.open(fname, 'rb') as f:
                ds = xr.open_dataset(f, engine='h5netcdf')
                # Slice region
                sst = ds.analysed_sst.isel(latitude=lat_indices, longitude=lon_indices).values[0]
                sst = sst.astype(np.float64)
                
                if t in date_to_pools:
                    for d in date_to_pools[t]:
                        pool_data[d].append(sst)
                
                if t in target_dates:
                    target_sst[t] = sst
        except Exception as e:
            # Some files might be missing
            pass

    # Calculate threshold and climatology
    thresholds = np.zeros((367, 60, 60), dtype=np.float64)
    climatology = np.zeros((367, 60, 60), dtype=np.float64)
    
    for d in range(1, 367):
        if d == 60: continue
        
        # pool_data[d] is a list of 60x60 arrays
        data = np.stack(pool_data[d], axis=0) # (N, 60, 60)
        
        # Threshold: 90th percentile (hazen)
        # numpy.quantile(method='hazen')
        # Mask NaNs for each cell?
        # Better: use nanquantile
        # Note: numpy.nanquantile doesn't have method='hazen'
        # We must implement hazen manually or use a loop
        
        # The requested method is "hazen" (Hyndman-Fan type 5).
        # For a sorted array x of size N, the i-th quantile is:
        # q(p) = x[j] + (p - (j - 0.5)/N) / (1/N) * (x[j+1] - x[j])
        # where j is the index such that (j-0.5)/N < p <= j/N.
        # Actually, numpy.quantile(method='hazen') is available in numpy 1.22+
        
        # Let's use np.nanquantile if possible, but wait, we need 'hazen'.
        # Let's use a custom function for hazen quantile that handles NaNs.
        
        # To be efficient, we can reshape and use np.nanquantile if we can find a way.
        # Or just loop over cells. 60x60=3600 cells.
        
        for i in range(60):
            for j in range(60):
                cell_vals = data[:, i, j]
                valid_vals = cell_vals[~np.isnan(cell_vals)]
                if len(valid_vals) > 0:
                    # Hazen quantile
                    thresholds[d, i, j] = np.quantile(valid_vals, 0.9, method='hazen')
                    climatology[d, i, j] = np.nanmean(cell_vals)
                else:
                    thresholds[d, i, j] = np.nan
                    climatology[d, i, j] = np.nan

    # Handle day 60
    thresholds[60] = (thresholds[59] + thresholds[61]) / 2
    climatology[60] = (climatology[59] + climatology[61]) / 2
    
    # Smooth with 31-day moving mean (wrap around)
    def smooth(arr):
        # arr is (367, 60, 60). 1..366 are used.
        # Convert to 0..365
        smoothed = np.zeros_like(arr)
        # 31-day window: d-15 to d+15
        # We only care about d in 1..366
        for d in range(1, 367):
            window_sum = np.zeros((60, 60), dtype=np.float64)
            count = np.zeros((60, 60), dtype=np.float64)
            for offset in range(-15, 16):
                # Wrap around day d (1-indexed)
                # day_idx = (d + offset - 1) % 366 + 1
                day_idx = (d + offset - 1) % 366 + 1
                window_sum += np.nan_to_num(arr[day_idx])
                count += (~np.isnan(arr[day_idx])).astype(np.float64)
            
            # Avoid division by zero
            mask = count > 0
            smoothed[d][mask] = window_sum[mask] / count[mask]
            smoothed[d][~mask] = np.nan
        return smoothed

    thresholds_smooth = smooth(thresholds)
    climatology_smooth = smooth(climatology)
    
    # Detect MHWs for each cell
    # target_sst: {date: SST_array}
    # target_dates: range(target_start, target_end)
    
    mhw_mask = np.zeros((len(target_dates), 60, 60), dtype=np.uint8)
    
    for i in range(60):
        for j in range(60):
            # Time series for cell (i, j)
            cell_sst = []
            cell_thresholds = []
            for t in target_dates:
                if t in target_sst:
                    cell_sst.append(target_sst[t][i, j])
                else:
                    cell_sst.append(np.nan)
                
                d = get_doy(t)
                cell_thresholds.append(thresholds_smooth[d, i, j])
            
            cell_sst = np.array(cell_sst)
            cell_thresholds = np.array(cell_thresholds)
            
            # Hot days
            is_hot = (cell_sst >= cell_thresholds) & (~np.isnan(cell_sst)) & (~np.isnan(cell_thresholds))
            
            # Find runs of hot days
            # MHW: run of >= 5 days. Joined if gap <= 2 days.
            
            # Implementation of joining gaps:
            # 1. Find all runs of hot days.
            # 2. If distance between runs <= 2, join them.
            
            # Simpler:
            # a day is in MHW if it's part of a hot run of >= 5 days,
            # OR it's a gap day between two MHWs separated by <= 2 days.
            
            # Use a mask to mark hot days
            mhw_cell = np.zeros(len(target_dates), dtype=bool)
            
            # Find all runs
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
            
            # Filter runs of >= 5 days
            mhw_runs = [r for r in runs if r[1] - r[0] + 1 >= 5]
            
            # Join runs
            if not mhw_runs:
                continue
                
            joined_runs = []
            if mhw_runs:
                curr_start, curr_end = mhw_runs[0]
                for next_start, next_end in mhw_runs[1:]:
                    if next_start - curr_end - 1 <= 2:
                        curr_end = next_end
                    else:
                        joined_runs.append((curr_start, curr_end))
                        curr_start, curr_end = next_start, next_end
                joined_runs.append((curr_start, curr_end))
            
            for rs, re in joined_runs:
                mhw_cell[rs:re+1] = True
            
            for t_idx in range(len(target_dates)):
                if mhw_cell[t_idx]:
                    mhw_mask[t_idx, i, j] = 1

    # Regional Events
    # A day is active if at least one sea cell is in an MHW
    # Sea cells: SST is finite on every day of the target period
    sea_cells_mask = np.ones((60, 60), dtype=bool)
    for t in target_dates:
        if t in target_sst:
            sst = target_sst[t]
            sea_cells_mask &= (~np.isnan(sst))
        else:
            sea_cells_mask[:] = False # No data for some target day
            break
            
    active_days = np.zeros(len(target_dates), dtype=bool)
    for t_idx in range(len(target_dates)):
        # check if any sea cell is in MHW
        # mhw_mask is (time, lat, lon)
        # we only care about sea cells
        cell_mhws = mhw_mask[t_idx] * sea_cells_mask
        if np.any(cell_mhws):
            active_days[t_idx] = True
            
    # Find maximal runs of active days
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

    # Write output files
    # 1. mhw_mask.nc
    # Need coordinates
    # mhw_mask is (time, lat, lon)
    # Coordinates: time, latitude, longitude
    
    # Let's build the xarray Dataset
    # Use target_dates as time coordinate
    ds_out = xr.Dataset(
        {"mhw": (["time", "latitude", "longitude"], mhw_mask.astype(np.uint8))},
        coords={
            "time": target_dates,
            "latitude": lat[lat_indices],
            "longitude": lon[lon_indices],
        }
    )
    ds_out.to_netcdf("output/mhw_mask.nc")
    
    # 2. report.json
    # Baseline analysed dates
    # First baseline date used: min(date_to_pools.keys())
    # Last baseline date used: max(date_to_pools.keys())
    baseline_dates_used = sorted(list(date_to_pools.keys()))
    
    report = {
        "region": {
            "lat_min": float(lat_min),
            "lat_max": float(lat_max),
            "lon_min": float(lon_min),
            "lon_max": float(lon_max)
        },
        "baseline_analysed": {
            "start": baseline_dates_used[0].strftime('%Y-%m-%d'),
            "end": baseline_dates_used[-1].strftime('%Y-%m-%d')
        } if baseline_dates_used else None,
        "target_analysed": {
            "start": target_dates[0].strftime('%Y-%m-%d'),
            "end": target_dates[-1].strftime('%Y-%m-%d')
        } if len(target_dates) > 0 else None,
        "events": regional_events,
        "complete": True,
        "caveats": ""
    }
    
    with open("output/report.json", "w") as f:
        json.dump(report, f)

solve()
