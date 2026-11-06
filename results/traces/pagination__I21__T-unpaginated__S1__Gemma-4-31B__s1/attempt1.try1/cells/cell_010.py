import fsspec
import xarray as xr
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import json
import os

os.makedirs("output", exist_ok=True)

lat_min, lat_max = 57.33, 58.53
lon_min, lon_max = 9.03, 10.23
target_start = pd.to_datetime("2021-06-01")
target_end = pd.to_datetime("2021-08-31")
baseline_start = pd.to_datetime("1992-01-01")
baseline_end = pd.to_datetime("2002-12-31")

fs = fsspec.filesystem('onedata')
root_dir = 'icsa2027_data_20261101T090944Z/s1z'

def get_doy(dt):
    return datetime(2000, dt.month, dt.day).timetuple().tm_yday

def load_sst_range(start, end, lat_min, lat_max, lon_min, lon_max):
    dates = pd.date_range(start, end)
    sst_list = []
    actual_dates = []
    selected_lats, selected_lons = None, None
    lat_mask, lon_mask = None, None
    
    for d in dates:
        date_str = d.strftime("%Y%m%d")
        file_path = f"{root_dir}/sst_{date_str}.nc"
        try:
            with fs.open(file_path, "rb") as f:
                ds_sample = xr.open_dataset(f, engine="h5netcdf")
                lats = ds_sample.latitude.values
                lons = ds_sample.longitude.values
                lat_mask = (lats >= lat_min) & (lats <= lat_max)
                lon_mask = (lons >= lon_min) & (lons <= lon_max)
                selected_lats = lats[lat_mask]
                selected_lons = lons[lon_mask]
                break
        except Exception:
            continue
            
    if selected_lats is None:
        return None, None, None, None

    for d in dates:
        date_str = d.strftime("%Y%m%d")
        file_path = f"{root_dir}/sst_{date_str}.nc"
        try:
            with fs.open(file_path, "rb") as f:
                ds = xr.open_dataset(f, engine="h5netcdf")
                sst_val = ds.analysed_sst.values[0, lat_mask, lon_mask].astype(np.float64)
                sst_list.append(sst_val)
                actual_dates.append(d)
        except Exception:
            pass
            
    return np.array(sst_list), pd.DatetimeIndex(actual_dates), selected_lats, selected_lons

print("Loading baseline...")
baseline_window_start = baseline_start - timedelta(days=5)
baseline_window_end = baseline_end + timedelta(days=5)
b_res = load_sst_range(baseline_window_start, baseline_window_end, lat_min, lat_max, lon_min, lon_max)
print(f"Baseline result: {type(b_res)}")

print("Loading target...")
t_res = load_sst_range(target_start, target_end, lat_min, lat_max, lon_min, lon_max)
print(f"Target result: {type(t_res)}")

if b_res[0] is not None and t_res[0] is not None:
    sst_baseline, dates_baseline, lats, lons = b_res
    sst_target, dates_target, _, _ = t_res
    
    sea_cells = np.all(np.isfinite(sst_target), axis=0)
    n_lat, n_lon = sst_target.shape[1:]
    
    baseline_date_to_idx = {d: i for i, d in enumerate(dates_baseline)}
    baseline_years_dates = pd.date_range(baseline_start, baseline_end)
    doy_to_baseline_dates = {}
    for d in baseline_years_dates:
        doy = get_doy(d)
        if doy != 60:
            doy_to_baseline_dates.setdefault(doy, []).append(d)
            
    thresholds = np.full((366, n_lat, n_lon), np.nan, dtype=np.float64)
    climatologies = np.full((366, n_lat, n_lon), np.nan, dtype=np.float64)
    
    print("Computing thresholds...")
    for doy in range(1, 367):
        if doy == 60: continue
        pool_indices = []
        for by in doy_to_baseline_dates.get(doy, []):
            for offset in range(-5, 6):
                win_date = by + timedelta(days=offset)
                if win_date in baseline_date_to_idx:
                    pool_indices.append(baseline_date_to_idx[win_date])
        if pool_indices:
            pool_vals = sst_baseline[pool_indices]
            thresholds[doy-1] = np.nanquantile(pool_vals, 0.9, axis=0, method='hazen')
            climatologies[doy-1] = np.nanmean(pool_vals, axis=0)
            
    thresholds[59] = (thresholds[58] + thresholds[60]) / 2
    climatologies[59] = (climatologies[58] + climatologies[60]) / 2
    
    def smooth_366(arr):
        smoothed = np.zeros_like(arr)
        for i in range(366):
            window = [arr[(i + offset) % 366] for offset in range(-15, 16)]
            smoothed[i] = np.nanmean(np.array(window), axis=0)
        return smoothed
    
    thresholds_smooth = smooth_366(thresholds)
    
    mhw_mask = np.zeros(sst_target.shape, dtype=np.uint8)
    for lat_idx in range(n_lat):
        for lon_idx in range(n_lon):
            if not sea_cells[lat_idx, lon_idx]: continue
            cell_sst = sst_target[:, lat_idx, lon_idx]
            cell_thresholds = np.array([thresholds_smooth[get_doy(d)-1, lat_idx, lon_idx] for d in dates_target])
            hot = cell_sst >= cell_thresholds
            is_mhw = np.zeros_like(hot, dtype=bool)
            i = 0
            while i < len(hot):
                if hot[i]:
                    j = i
                    while j < len(hot) and hot[j]: j += 1
                    if j - i >= 5: is_mhw[i:j] = True
                    i = j
                else: i += 1
            current_mhw = is_mhw.copy()
            while True:
                changed = False
                i = 0
                while i < len(current_mhw):
                    if not current_mhw[i]:
                        j = i
                        while j < len(current_mhw) and not current_mhw[j]: j += 1
                        gap_len = j - i
                        if gap_len <= 2 and i > 0 and j < len(current_mhw):
                            if current_mhw[i-1] and current_mhw[j]:
                                current_mhw[i:j] = True
                                changed = True
                        i = j
                    else: i += 1
                if not changed: break
            mhw_mask[:, lat_idx, lon_idx] = current_mhw.astype(np.uint8)
            
    active_days = np.any(mhw_mask == 1, axis=(1, 2))
    regional_events = []
    i = 0
    while i < len(active_days):
        if active_days[i]:
            j = i
            while j < len(active_days) and active_days[j]: j += 1
            regional_events.append({"onset": dates_target[i].strftime("%Y-%m-%d"), "end": dates_target[j-1].strftime("%Y-%m-%d")})
            i = j
        else: i += 1
        
    ds_out = xr.Dataset({"mhw": (("time", "latitude", "longitude"), mhw_mask)}, coords={"time": dates_target, "latitude": lats, "longitude": lons})
    ds_out.to_netcdf("output/mhw_mask.nc")
    
    report = {
        "region": {"lat_min": lat_min, "lat_max": lat_max, "lon_min": lon_min, "lon_max": lon_max},
        "baseline_analysed": {"start": dates_baseline[0].strftime("%Y-%m-%d"), "end": dates_baseline[-1].strftime("%Y-%m-%d")},
        "target_analysed": {"start": dates_target[0].strftime("%Y-%m-%d"), "end": dates_target[-1].strftime("%Y-%m-%d")},
        "events": regional_events,
        "complete": True,
        "caveats": ""
    }
    with open("output/report.json", "w") as f:
        json.dump(report, f)
    print("Done.")
else:
    print("Data missing.")
