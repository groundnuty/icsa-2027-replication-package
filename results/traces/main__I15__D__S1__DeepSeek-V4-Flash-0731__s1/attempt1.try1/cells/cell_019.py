
import xarray as xr
import numpy as np
import datetime
import pandas as pd

def date_to_doy(dt):
    days_in_month = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    doy = sum(days_in_month[:dt.month-1]) + dt.day
    return doy

# Load data
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
lat = ds.latitude.values
lon = ds.longitude.values
time_vals = ds.time.values

lat_idx = np.where((lat >= 56.13) & (lat <= 57.33))[0]
lon_idx = np.where((lon >= 17.71) & (lon <= 18.91))[0]

# Target period
target_start = np.datetime64('2019-06-01')
target_end = np.datetime64('2019-08-31')
target_mask = (time_vals >= target_start) & (time_vals <= target_end)
target_time_idx = np.where(target_mask)[0]
target_dates = [pd.Timestamp(t).date() for t in time_vals[target_time_idx]]

# Baseline period
baseline_start = np.datetime64('1991-12-27')
baseline_end = np.datetime64('2003-01-05')
baseline_mask = (time_vals >= baseline_start) & (time_vals <= baseline_end)
baseline_time_idx = np.where(baseline_mask)[0]
baseline_dates = [pd.Timestamp(t).date() for t in time_vals[baseline_time_idx]]

# Extract data
baseline_sst = ds.analysed_sst[baseline_time_idx, lat_idx[0]:lat_idx[-1]+1, lon_idx[0]:lon_idx[-1]+1].values.astype(np.float64)
target_sst = ds.analysed_sst[target_time_idx, lat_idx[0]:lat_idx[-1]+1, lon_idx[0]:lon_idx[-1]+1].values.astype(np.float64)

# Identify sea cells
sea_mask = np.all(np.isfinite(target_sst), axis=0)
sea_y, sea_x = np.where(sea_mask)
print("Sea cells:", len(sea_y))

# Build pool date indices for each doy
date_to_idx = {dt: i for i, dt in enumerate(baseline_dates)}

pools_idx = {}
for d_val in range(1, 367):
    if d_val == 60:
        continue
    bdt_with_doy = []
    for dt in baseline_dates:
        if datetime.date(1992,1,1) <= dt <= datetime.date(2002,12,31) and date_to_doy(dt) == d_val:
            bdt_with_doy.append(dt)
    pool_idx_set = set()
    for bdt in bdt_with_doy:
        for i in range(-5, 6):
            dt2 = bdt + datetime.timedelta(days=i)
            if dt2 in date_to_idx:
                pool_idx_set.add(date_to_idx[dt2])
    pools_idx[d_val] = sorted(pool_idx_set)

# Compute threshold and climatology (index 0 = doy 1, index 365 = doy 366)
threshold = np.full((366, 60, 60), np.nan, dtype=np.float64)
climatology = np.full((366, 60, 60), np.nan, dtype=np.float64)

for d_val in range(1, 367):
    if d_val == 60:
        continue
    pool_idx = pools_idx[d_val]
    pool_data = baseline_sst[pool_idx]  # (n_dates, 60, 60)
    for ci in range(len(sea_y)):
        y, x = sea_y[ci], sea_x[ci]
        vals = pool_data[:, y, x]
        finite_vals = vals[np.isfinite(vals)]
        if len(finite_vals) > 0:
            threshold[d_val-1, y, x] = np.quantile(finite_vals, 0.9, method='hazen')
            climatology[d_val-1, y, x] = np.mean(finite_vals)

# Set day 60 (index 59) to mean of days 59 (index 58) and 61 (index 60)
threshold[59] = (threshold[58] + threshold[60]) / 2.0
climatology[59] = (climatology[58] + climatology[60]) / 2.0

print("Computed threshold and climatology")

# Now smooth with 31-day centered moving average wrapping around
def smooth_circular(arr):
    """Smooth a 366-element array with unweighted centered 31-day moving average wrapping around."""
    n = 366
    # Pad the array
    padded = np.concatenate([arr[-15:], arr, arr[:15]])
    # Compute moving average
    result = np.zeros(n)
    for i in range(n):
        result[i] = np.mean(padded[i:i+31])
    return result

# Apply smoothing per cell
smooth_threshold = np.zeros_like(threshold)
smooth_climatology = np.zeros_like(climatology)
for ci in range(len(sea_y)):
    y, x = sea_y[ci], sea_x[ci]
    smooth_threshold[:, y, x] = smooth_circular(threshold[:, y, x])
    smooth_climatology[:, y, x] = smooth_circular(climatology[:, y, x])

print("Smoothed")
# Verify some values
y, x = sea_y[0], sea_x[0]
for d in [1, 153, 183, 213, 214, 244, 245, 366]:
    print(f"doy {d}: thresh={smooth_threshold[d-1,y,x]:.4f}, clim={smooth_climatology[d-1,y,x]:.4f}")
