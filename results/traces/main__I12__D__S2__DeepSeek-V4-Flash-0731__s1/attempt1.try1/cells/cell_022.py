
import numpy as np
import pandas as pd
import xarray as xr

# Check the smoothed threshold for cell (0,0) across all doys
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')

# Let me just verify by recomputing the full thing but checking a specific cell
# Actually, let me just check the threshold for a target day and compare

# Recompute the full pipeline for cell (0,0)
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

# Cell (0,0) - it's a sea cell
i, j = 0, 0

def date_to_doy(dt):
    month = dt.month
    day = dt.day
    days_before = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return days_before[month-1] + day

# Build pools for cell (0,0)
full_base_time = base_time
base_dates_mask = (full_base_time >= pd.Timestamp('1992-01-01')) & (full_base_time <= pd.Timestamp('2002-12-31'))
base_dates = full_base_time[base_dates_mask]
base_doys = np.array([date_to_doy(d) for d in base_dates])

# Compute raw threshold and climatology for all doys
raw_threshold = np.full(367, np.nan)  # index 1-366
raw_climatology = np.full(367, np.nan)

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
        raw_threshold[d] = np.quantile(valid, 0.9, method='hazen')
        raw_climatology[d] = np.mean(valid)

# Set doy 60
raw_threshold[60] = (raw_threshold[59] + raw_threshold[61]) / 2.0
raw_climatology[60] = (raw_climatology[59] + raw_climatology[61]) / 2.0

# Smooth
def smooth_31day(arr):
    result = np.zeros_like(arr)
    for d in range(366):
        result[d] = np.mean(arr[(np.arange(d-15, d+16) % 366)])
    return result

smoothed_threshold = smooth_31day(raw_threshold[1:367])
smoothed_climatology = smooth_31day(raw_climatology[1:367])

# Check for a few doys
print("Raw vs smoothed threshold for cell (0,0):")
for d in [1, 59, 60, 61, 100, 153, 154, 155, 200, 244, 366]:
    print(f"  doy {d}: raw={raw_threshold[d]:.2f}, smoothed={smoothed_threshold[d-1]:.2f}")

# Check if smoothing preserves reasonable values
print(f"\nSmoothed threshold range: {np.nanmin(smoothed_threshold):.2f} to {np.nanmax(smoothed_threshold):.2f}")
print(f"Smoothed climatology range: {np.nanmin(smoothed_climatology):.2f} to {np.nanmax(smoothed_climatology):.2f}")
