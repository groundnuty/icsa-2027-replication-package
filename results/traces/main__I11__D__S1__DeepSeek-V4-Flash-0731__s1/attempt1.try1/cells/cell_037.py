
import numpy as np
import pandas as pd
from datetime import date, timedelta

# Reload all the raw data
import xarray as xr
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
time_vals = ds.time.values

baseline_idx = np.where((time_vals >= np.datetime64('1991-12-27')) & (time_vals <= np.datetime64('2003-01-05')))[0]
baseline_time = time_vals[baseline_idx]
baseline_dates = [pd.Timestamp(t).date() for t in baseline_time]

baseline_sst = ds['analysed_sst'].isel(time=baseline_idx, latitude=slice(109,169), longitude=slice(373,433)).load().values.astype(np.float64)

def day_of_year_366(d):
    m, day = d.month, d.day
    days_in_month = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return sum(days_in_month[:m-1]) + day

# Independent check: compute the pool for doy=153 (June 1) for a specific sea cell
# Baseline dates with doy=153: June 1 of each year 1992-2002
# Pool: all dates within ±5 days of these

# Find all baseline dates that contribute to doy 153's pool
# A date D contributes if it's within ±5 days of some baseline date E with doy(E)=153

pool_dates = []
for i, D in enumerate(baseline_dates):
    for offset in range(-5, 6):
        E = D + timedelta(days=offset)
        if date(1992, 1, 1) <= E <= date(2002, 12, 31):
            if day_of_year_366(E) == 153:
                pool_dates.append(D)
                break

print(f"Pool for doy 153 has {len(pool_dates)} dates")

# Check a specific sea cell (30, 30)
cell_i, cell_j = 30, 30

# Collect SST values for this cell from the pool dates
pool_values = []
for i, D in enumerate(baseline_dates):
    for offset in range(-5, 6):
        E = D + timedelta(days=offset)
        if date(1992, 1, 1) <= E <= date(2002, 12, 31):
            if day_of_year_366(E) == 153:
                pool_values.append(baseline_sst[i, cell_i, cell_j])
                break

pool_values = np.array(pool_values)
valid = ~np.isnan(pool_values)
v = pool_values[valid]
print(f"Valid values: {len(v)}")
print(f"Independent threshold (hazen): {np.quantile(v, 0.9, method='hazen')}")
print(f"Independent climatology: {np.mean(v)}")

# Compare with my computed values
smooth_thresholds = np.load('/work/smooth_thresholds.npy')
thresholds_raw = np.load('/work/thresholds.npy')
climatology_raw = np.load('/work/climatology.npy')

print(f"My raw threshold for doy 153: {thresholds_raw[152, cell_i, cell_j]}")
print(f"My raw climatology for doy 153: {climatology_raw[152, cell_i, cell_j]}")
print(f"My smoothed threshold for doy 153: {smooth_thresholds[152, cell_i, cell_j]}")

# Verify the smoothed value
# Compute smoothed: mean of raw thresholds for days 138-168 (doy 153 ± 15)
raw_thresholds_cell = thresholds_raw[:, cell_i, cell_j]
smoothed_manual = np.mean([raw_thresholds_cell[(152 - 15 + k) % 366] for k in range(31)])
print(f"Manual smoothed threshold: {smoothed_manual}")
