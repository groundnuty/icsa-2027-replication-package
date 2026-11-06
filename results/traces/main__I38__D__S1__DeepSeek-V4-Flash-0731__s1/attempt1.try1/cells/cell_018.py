import numpy as np
from datetime import date, timedelta
import xarray as xr
import json
import os

# ============================================================
# Day-of-year mapping (1-366)
# ============================================================
month_days = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

def day_of_year(month, day):
    doy = day
    for m in range(month - 1):
        doy += month_days[m]
    return doy

def date_to_doy(d):
    return day_of_year(d.month, d.day)

# ============================================================
# Load data
# ============================================================
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')

lat = ds.latitude.values
lon = ds.longitude.values
lat_idx = np.where((lat >= 60.49) & (lat <= 61.69))[0]
lon_idx = np.where((lon >= 17.25) & (lon <= 18.45))[0]
lat_region = lat[lat_idx].astype(float)
lon_region = lon[lon_idx].astype(float)

# Baseline: 1991-12-27 to 2003-01-05
time = ds.time.values
baseline_start_idx = np.where(time == np.datetime64('1991-12-27'))[0][0]
baseline_end_idx = np.where(time == np.datetime64('2003-01-05'))[0][0]

# Target: 2003-06-01 to 2003-08-31
target_start_idx = np.where(time == np.datetime64('2003-06-01'))[0][0]
target_end_idx = np.where(time == np.datetime64('2003-08-31'))[0][0]

# Read data
baseline_data = ds.analysed_sst[baseline_start_idx:baseline_end_idx+1, lat_idx[0]:lat_idx[-1]+1, lon_idx[0]:lon_idx[-1]+1].values.astype(np.float64)
target_data = ds.analysed_sst[target_start_idx:target_end_idx+1, lat_idx[0]:lat_idx[-1]+1, lon_idx[0]:lon_idx[-1]+1].values.astype(np.float64)

n_baseline_days = baseline_data.shape[0]
n_target_days = target_data.shape[0]
n_lat = baseline_data.shape[1]
n_lon = baseline_data.shape[2]

print(f"Baseline data shape: {baseline_data.shape}")
print(f"Target data shape: {target_data.shape}")

# Generate dates
baseline_dates = []
d = date(1991, 12, 27)
end_d = date(2003, 1, 5)
while d <= end_d:
    baseline_dates.append(d)
    d += timedelta(days=1)
assert len(baseline_dates) == n_baseline_days

target_dates = []
d = date(2003, 6, 1)
end_d = date(2003, 8, 31)
while d <= end_d:
    target_dates.append(d)
    d += timedelta(days=1)
assert len(target_dates) == n_target_days

# ============================================================
# Identify sea cells: finite on every day of target period
# ============================================================
sea_cells = np.all(np.isfinite(target_data), axis=0)
print(f"Sea cells: {sea_cells.sum()} out of {sea_cells.size}")

# ============================================================
# Build pool dates for each day-of-year
# ============================================================
baseline_years = range(1992, 2003)

# Map baseline date indices to positions in baseline_dates
baseline_date_index = {d: i for i, d in enumerate(baseline_dates)}

# For each day-of-year, find the pool dates (indices in baseline_dates)
pool_date_indices_by_doy = {}

for doy in range(1, 367):
    if doy == 60:
        continue
    pool_indices = set()
    for y in baseline_years:
        # Find the date in year y with this day-of-year
        # Need to handle Feb 29 (doy=60) separately
        # For doy != 60, the date is well-defined in all years
        # Let me compute the month and day from the doy
        month = 1
        remaining = doy
        while remaining > month_days[month-1]:
            remaining -= month_days[month-1]
            month += 1
        day = remaining
        
        # Skip Feb 29 (day 60)
        if month == 2 and day == 29:
            continue
        
        # Create the date in year y
        try:
            b = date(y, month, day)
        except ValueError:
            continue  # Skip invalid dates like Feb 29 in non-leap years
        
        # ±5 days around b
        for offset in range(-5, 6):
            t = b + timedelta(days=offset)
            if t in baseline_date_index:
                pool_indices.add(baseline_date_index[t])
    
    pool_date_indices_by_doy[doy] = sorted(pool_indices)

print(f"Pools built for {len(pool_date_indices_by_doy)} day-of-years")
print(f"Day 1 pool size: {len(pool_date_indices_by_doy[1])}")
print(f"Day 366 pool size: {len(pool_date_indices_by_doy[366])}")
print(f"Day 100 pool size: {len(pool_date_indices_by_doy[100])}")

# ============================================================
# Compute thresholds and climatology for each sea cell and day-of-year
# ============================================================
# We need to compute for each day-of-year, for each sea cell:
# - threshold: 90th percentile of pool (numpy method="hazen"), ignoring NaN
# - climatology: mean of pool, ignoring NaN

thresholds = np.full((366, n_lat, n_lon), np.nan)
climatology = np.full((366, n_lat, n_lon), np.nan)

for doy in range(1, 367):
    if doy == 60:
        continue
    pool_indices = pool_date_indices_by_doy[doy]
    if not pool_indices:
        continue
    # Extract SST values for pool dates for all cells
    pool_data = baseline_data[pool_indices, :, :]  # (n_pool, n_lat, n_lon)
    
    # For each sea cell, compute threshold and climatology
    for li in range(n_lat):
        for loi in range(n_lon):
            if not sea_cells[li, loi]:
                continue
            values = pool_data[:, li, loi]
            valid = np.isfinite(values)
            if valid.sum() == 0:
                continue
            vals = values[valid]
            thresholds[doy, li, loi] = np.quantile(vals, 0.9, method='hazen')
            climatology[doy, li, loi] = np.mean(vals)

print("Thresholds and climatology computed")

# ============================================================
# Set day 60 to mean of days 59 and 61
# ============================================================
for li in range(n_lat):
    for loi in range(n_lon):
        if sea_cells[li, loi]:
            thresholds[59, li, loi] = (thresholds[58, li, loi] + thresholds[60, li, loi]) / 2.0
            climatology[59, li, loi] = (climatology[58, li, loi] + climatology[60, li, loi]) / 2.0

print("Day 60 set to mean of days 59 and 61")
