
import numpy as np
import pandas as pd
import xarray as xr

# I need to recompute the full pipeline to check hot days for cell (54,20)
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')

lat = ds.latitude.values
lon = ds.longitude.values
time = pd.to_datetime(ds.time.values)

lat_idx = np.where((lat >= 56.09) & (lat <= 57.29))[0]
lon_idx = np.where((lon >= 10.55) & (lon <= 11.75))[0]

mask = (time >= pd.Timestamp('1991-12-27')) & (time <= pd.Timestamp('2003-01-05'))
idx_base = np.where(mask)[0]
mask_t = (time >= pd.Timestamp('2009-06-01')) & (time <= pd.Timestamp('2009-08-31'))
idx_target = np.where(mask_t)[0]

base_time = time[idx_base]
target_time = time[idx_target]
base_sst = ds['analysed_sst'].isel(time=idx_base, latitude=lat_idx, longitude=lon_idx).values.astype(np.float64)
target_sst = ds['analysed_sst'].isel(time=idx_target, latitude=lat_idx, longitude=lon_idx).values.astype(np.float64)

n_lat, n_lon = 60, 60
sea_cells = np.zeros((n_lat, n_lon), dtype=bool)
for a in range(n_lat):
    for b in range(n_lon):
        sea_cells[a,b] = np.all(np.isfinite(target_sst[:, a, b]))

def date_to_doy(dt):
    month = dt.month
    day = dt.day
    days_before = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return days_before[month-1] + day

# Build pools and thresholds (quick version for one cell)
full_base_time = base_time
base_dates_mask = (full_base_time >= pd.Timestamp('1992-01-01')) & (full_base_time <= pd.Timestamp('2002-12-31'))
base_dates = full_base_time[base_dates_mask]
base_doys = np.array([date_to_doy(d) for d in base_dates])

# For cell (54, 20)
i, j = 54, 20

threshold = np.full(367, np.nan)
for d in range(1, 367):
    if d == 60:
        continue
    bd_mask = (base_doys == d)
    bd_dates = base_dates[bd_mask]
    if len(bd_dates) == 0:
        continue
    pool_date_set = set()
    for B in bd_dates:
        for delta in range(-5, 6):
            pool_date_set.add(B + pd.Timedelta(days=delta))
    pool_mask = np.array([t in pool_date_set for t in full_base_time])
    pool_vals = base_sst[pool_mask, i, j]
    valid = pool_vals[np.isfinite(pool_vals)]
    if len(valid) > 0:
        threshold[d] = np.quantile(valid, 0.9, method='hazen')

threshold[60] = (threshold[59] + threshold[61]) / 2.0

# Smooth
def smooth_31day(arr):
    result = np.zeros_like(arr)
    for d in range(366):
        result[d] = np.mean(arr[(np.arange(d-15, d+16) % 366)])
    return result

smoothed_threshold = np.full(367, np.nan)
smoothed_threshold[1:367] = smooth_31day(threshold[1:367])

# Check hot days for target period
target_doys = np.array([date_to_doy(t) for t in target_time])
hot = np.zeros(len(target_doys), dtype=bool)

print(f"Cell ({i},{j}): Hot day pattern for first 45 days:")
for t in range(45):
    d = target_doys[t]
    sst_val = target_sst[t, i, j]
    thr = smoothed_threshold[d]
    is_hot = np.isfinite(sst_val) and sst_val >= thr
    hot[t] = is_hot
    date_str = target_time[t].strftime('%Y-%m-%d')
    marker = "HOT" if is_hot else "   "
    print(f"  {date_str} (doy {d}): SST={sst_val:.2f}, Thresh={thr:.2f} {marker}")
