
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
print(f"Baseline dates: {baseline_dates[0]} to {baseline_dates[-1]}, count={len(baseline_dates)}")

# Extract data
baseline_sst = ds.analysed_sst[baseline_time_idx, lat_idx[0]:lat_idx[-1]+1, lon_idx[0]:lon_idx[-1]+1].values.astype(np.float64)
target_sst = ds.analysed_sst[target_time_idx, lat_idx[0]:lat_idx[-1]+1, lon_idx[0]:lon_idx[-1]+1].values.astype(np.float64)

print("Baseline SST shape:", baseline_sst.shape)
print("Target SST shape:", target_sst.shape)

# Identify sea cells
sea_mask = np.all(np.isfinite(target_sst), axis=0)
print("Sea cells:", sea_mask.sum())

# Build pool date indices for each doy
# Pool dates for each doy d (1-366, excluding 60)
# Map from date to index in baseline array
date_to_idx = {dt: i for i, dt in enumerate(baseline_dates)}

# For each doy, get list of pool indices into baseline_sst
pools_idx = {}
for d_val in range(1, 367):
    if d_val == 60:
        continue
    # Baseline dates with this doy (1992-2002)
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
    
print("Pool sizes:", {d: len(pools_idx[d]) for d in [1, 58, 59, 61, 62, 366]})

# Now compute threshold and climatology for each sea cell and each doy
# We'll iterate over doys and cells

# Initialize arrays
threshold = np.full((366, 60, 60), np.nan, dtype=np.float64)
climatology = np.full((366, 60, 60), np.nan, dtype=np.float64)

# Get sea cell indices
sea_y, sea_x = np.where(sea_mask)
print("Sea cell count:", len(sea_y))

# For each doy, compute threshold and climatology
for d_val in range(1, 367):
    if d_val == 60:
        continue
    pool_idx = pools_idx[d_val]
    pool_data = baseline_sst[pool_idx]  # (n_dates, 60, 60)
    # Mask only sea cells
    # For sea cells, compute quantile and mean ignoring NaN
    # For each sea cell
    for ci in range(len(sea_y)):
        y, x = sea_y[ci], sea_x[ci]
        vals = pool_data[:, y, x]
        finite_vals = vals[np.isfinite(vals)]
        if len(finite_vals) > 0:
            # Quantile using numpy method='hazen' (Hyndman-Fan type 5)
            threshold[d_val, y, x] = np.quantile(finite_vals, 0.9, method='hazen')
            climatology[d_val, y, x] = np.mean(finite_vals)

print("Computed threshold and climatology for all doys")
# Check some values
for d in [1, 150, 200, 213, 214, 244, 245, 366]:
    y = sea_y[0]
    x = sea_x[0]
    print(f"doy {d}: threshold={threshold[d,y,x]:.4f}, climatology={climatology[d,y,x]:.4f}")
