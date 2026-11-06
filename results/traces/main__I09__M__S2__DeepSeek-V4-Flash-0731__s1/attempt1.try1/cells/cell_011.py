
import numpy as np
import pandas as pd

# Load saved data
sst_data = np.load('/tmp/sst_data.npy')
time_int = np.load('/tmp/time_sub.npy')
time_sub = time_int.astype('datetime64[s]')
lat_vals = np.load('/tmp/lat_vals.npy')
lon_vals = np.load('/tmp/lon_vals.npy')

def date_to_doy(date):
    ts = pd.Timestamp(date)
    month, day = ts.month, ts.day
    cum_days = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum_days[month-1] + day

dates = pd.to_datetime(time_sub)
n_time = len(dates)

# Baseline dates
baseline_start = pd.Timestamp('1992-01-01')
baseline_end = pd.Timestamp('2002-12-31')
baseline_dates = pd.date_range(baseline_start, baseline_end, freq='D')

# Build pool masks
pool_masks = {}
for d in range(1, 367):
    if d == 60:
        continue
    pool_masks[d] = np.zeros(n_time, dtype=bool)

for B in baseline_dates:
    d = date_to_doy(B)
    if d == 60:
        continue
    B_start = B - pd.Timedelta(days=5)
    B_end = B + pd.Timedelta(days=5)
    mask = (dates >= B_start) & (dates <= B_end)
    pool_masks[d] |= mask

# Compute thresholds and climatology for each DOY and cell
n_lat = sst_data.shape[1]
n_lon = sst_data.shape[2]

# Arrays indexed by DOY-1 (0-365)
thresholds = np.full((366, n_lat, n_lon), np.nan)
climatology = np.full((366, n_lat, n_lon), np.nan)

for d in range(1, 367):
    if d == 60:
        continue
    mask = pool_masks[d]
    pool_idx = np.where(mask)[0]
    if len(pool_idx) == 0:
        continue
    pool_data = sst_data[pool_idx]  # (n_pool, n_lat, n_lon)
    
    with np.errstate(invalid='ignore', all='ignore'):
        climatology[d-1] = np.nanmean(pool_data, axis=0)
        thresholds[d-1] = np.nanquantile(pool_data, 0.9, axis=0, method='hazen')

print("Computed thresholds and climatology for all DOYs")

# Check some values
print("Thresholds[152, 30, 30] (DOY 153):", thresholds[152, 30, 30])
print("Climatology[152, 30, 30] (DOY 153):", climatology[152, 30, 30])
print("Thresholds[243, 30, 30] (DOY 244):", thresholds[243, 30, 30])
print("Climatology[243, 30, 30] (DOY 244):", climatology[243, 30, 30])

# Check NaN counts
nan_thresh = np.isnan(thresholds).sum()
nan_clim = np.isnan(climatology).sum()
print(f"NaN in thresholds: {nan_thresh}")
print(f"NaN in climatology: {nan_clim}")

# Save intermediate results
np.save('/tmp/thresholds_raw.npy', thresholds)
np.save('/tmp/climatology_raw.npy', climatology)
print("Saved raw thresholds and climatology")
