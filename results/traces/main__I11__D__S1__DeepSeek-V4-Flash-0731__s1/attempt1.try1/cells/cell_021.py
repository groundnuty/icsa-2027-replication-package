
import numpy as np
import pandas as pd
from datetime import date, timedelta

# Load saved data
baseline_sst = np.load('/work/baseline_sst.npy')  # (4028, 60, 60)
target_sst = np.load('/work/target_sst.npy')  # (92, 60, 60)

# Reload time data
import xarray as xr
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
time_vals = ds.time.values
baseline_idx = np.where((time_vals >= np.datetime64('1991-12-27')) & (time_vals <= np.datetime64('2003-01-05')))[0]
baseline_time = time_vals[baseline_idx]
baseline_dates = [pd.Timestamp(t).date() for t in baseline_time]

# Day of year mapping (always Feb=29)
def day_of_year_366(d):
    m, day = d.month, d.day
    days_in_month = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return sum(days_in_month[:m-1]) + day

# Build mapping from date to index
baseline_date_to_idx = {d: i for i, d in enumerate(baseline_dates)}

# Identify sea cells
sea_mask = np.all(~np.isnan(target_sst), axis=0)  # (60, 60)
n_sea = np.sum(sea_mask)
print(f"Sea cells: {n_sea}")

# Build doy_to_date_indices mapping
doy_to_date_indices = {}
for i, D in enumerate(baseline_dates):
    for offset in range(-5, 6):
        E = D + timedelta(days=offset)
        if date(1992, 1, 1) <= E <= date(2002, 12, 31):
            doy_E = day_of_year_366(E)
            if doy_E != 60:
                if doy_E not in doy_to_date_indices:
                    doy_to_date_indices[doy_E] = []
                doy_to_date_indices[doy_E].append(i)

# Now compute thresholds and climatology for each day-of-year and cell
# For each doy, the pool is the SST values from the dates in doy_to_date_indices[doy]
# for each sea cell.

# thresholds[doy-1, i, j] and climatology[doy-1, i, j] for doy 1-366
# Shape: (366, 60, 60)
thresholds = np.full((366, 60, 60), np.nan)
climatology = np.full((366, 60, 60), np.nan)

print("Computing thresholds and climatology...")
for doy in range(1, 367):
    if doy == 60:
        continue  # Day 60 gets no pool
    if doy not in doy_to_date_indices:
        continue
    indices = doy_to_date_indices[doy]
    # Pool: (n_dates, 60, 60)
    pool = baseline_sst[indices]  # (121, 60, 60)
    
    # For each cell, compute threshold and climatology ignoring NaN
    # We need to compute per-cell, so let's iterate over the sea cells
    for i in range(60):
        for j in range(60):
            if sea_mask[i, j]:
                values = pool[:, i, j]
                valid = ~np.isnan(values)
                if np.sum(valid) > 0:
                    v = values[valid]
                    thresholds[doy-1, i, j] = np.quantile(v, 0.9, method='hazen')
                    climatology[doy-1, i, j] = np.mean(v)

print("Done computing base thresholds and climatology")

# Set day 60 (index 59) to mean of days 59 and 61 (indices 58 and 60)
thresholds[59, :, :] = (thresholds[58, :, :] + thresholds[60, :, :]) / 2
climatology[59, :, :] = (climatology[58, :, :] + climatology[60, :, :]) / 2

print("Set day 60 values")
print(f"Thresholds shape: {thresholds.shape}")
print(f"Climatology shape: {climatology.shape}")

# Check some values
print(f"Sample threshold at (0, 0): {thresholds[0, 0, 0]}")
print(f"Sample climatology at (0, 0): {climatology[0, 0, 0]}")
print(f"Sample threshold at (152, 0, 0): {thresholds[152, 0, 0]}")  # June 1
print(f"Sample climatology at (152, 0, 0): {climatology[152, 0, 0]}")

# Save
np.save('/work/thresholds.npy', thresholds)
np.save('/work/climatology.npy', climatology)
np.save('/work/sea_mask.npy', sea_mask)
print("Saved.")
