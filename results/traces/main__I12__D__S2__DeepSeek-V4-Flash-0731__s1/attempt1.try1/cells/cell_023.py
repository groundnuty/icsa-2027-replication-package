
import numpy as np
import pandas as pd
import xarray as xr

# Reload and recompute everything to verify cell-level results
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
for i in range(n_lat):
    for j in range(n_lon):
        sea_cells[i,j] = np.all(np.isfinite(target_sst[:, i, j]))

def date_to_doy(dt):
    month = dt.month
    day = dt.day
    days_before = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return days_before[month-1] + day

# Rebuild pools
full_base_time = base_time
base_dates_mask = (full_base_time >= pd.Timestamp('1992-01-01')) & (full_base_time <= pd.Timestamp('2002-12-31'))
base_dates = full_base_time[base_dates_mask]
base_doys = np.array([date_to_doy(d) for d in base_dates])

pool_indices = {}
for d in range(1, 367):
    if d == 60:
        continue
    bd_mask = (base_doys == d)
    bd_dates = base_dates[bd_mask]
    if len(bd_dates) == 0:
        pool_indices[d] = np.array([], dtype=int)
        continue
    pool_date_set = set()
    for B in bd_dates:
        for delta in range(-5, 6):
            pool_date_set.add(B + pd.Timedelta(days=delta))
    indices = np.array([i for i, t in enumerate(full_base_time) if t in pool_date_set], dtype=int)
    pool_indices[d] = indices

# Compute threshold and climatology
threshold = np.full((367, n_lat, n_lon), np.nan)
climatology = np.full((367, n_lat, n_lon), np.nan)

for d in range(1, 367):
    if d == 60:
        continue
    idx = pool_indices[d]
    if len(idx) == 0:
        continue
    pool = base_sst[idx]
    for i in range(n_lat):
        for j in range(n_lon):
            if not sea_cells[i, j]:
                continue
            vals = pool[:, i, j]
            valid = vals[np.isfinite(vals)]
            if len(valid) == 0:
                continue
            threshold[d, i, j] = np.quantile(valid, 0.9, method='hazen')
            climatology[d, i, j] = np.mean(valid)

threshold[60] = (threshold[59] + threshold[61]) / 2.0
climatology[60] = (climatology[59] + climatology[61]) / 2.0

def smooth_31day(arr):
    result = np.zeros_like(arr)
    for d in range(366):
        result[d] = np.mean(arr[(np.arange(d-15, d+16) % 366)])
    return result

thresh_smoothed = np.full_like(threshold, np.nan)
clim_smoothed = np.full_like(climatology, np.nan)

for i in range(n_lat):
    for j in range(n_lon):
        if not sea_cells[i, j]:
            continue
        thresh_smoothed[1:367, i, j] = smooth_31day(threshold[1:367, i, j])
        clim_smoothed[1:367, i, j] = smooth_31day(climatology[1:367, i, j])

# Now examine a specific cell in detail
# Let's look at cell (0,0)
i, j = 0, 0
n_target = len(idx_target)
target_doys = np.array([date_to_doy(t) for t in target_time])

print(f"Cell ({i},{j}) - checking per-cell MHW detection")
print(f"SST values and thresholds:")
print(f"{'Date':<12} {'Doy':<5} {'SST':<8} {'Thresh':<8} {'Hot':<5} {'In MHW':<7}")
hot = np.zeros(n_target, dtype=bool)
for t in range(n_target):
    d = target_doys[t]
    sst_val = target_sst[t, i, j]
    thr = thresh_smoothed[d, i, j]
    is_hot = np.isfinite(sst_val) and sst_val >= thr
    hot[t] = is_hot
    if is_hot or t >= 50:  # print all or just from some point
        print(f"{target_time[t].strftime('%Y-%m-%d'):<12} {d:<5} {sst_val:.2f} {thr:.2f} {'Y' if is_hot else 'N':<5}")
