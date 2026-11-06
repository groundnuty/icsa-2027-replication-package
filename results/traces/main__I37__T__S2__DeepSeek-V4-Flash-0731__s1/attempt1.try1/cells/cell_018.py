
import pandas as pd
import numpy as np
import json
import os

# ====== Parameters ======
LAT_MIN, LAT_MAX = 60.09, 61.29
LON_MIN, LON_MAX = 20.01, 21.21

# ====== Fixed day-of-year mapping ======
def fixed_doy(ts):
    cum = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum[ts.month - 1] + ts.day

# ====== Build pool time indices ======
ext_dates = pd.date_range('1991-12-27', '2003-01-05', freq='D')
base_dates = pd.date_range('1992-01-01', '2002-12-31', freq='D')
base_doy = np.array([fixed_doy(d) for d in base_dates])

# Map extended dates to indices in baseline_sst
# ext_dates[0] corresponds to index 0 in baseline_sst
ext_date_to_idx = {d: i for i, d in enumerate(ext_dates)}

pool_time_indices = {}  # doy -> list of indices into baseline_sst
for d in range(1, 367):
    if d == 60:
        continue
    b_mask = (base_doy == d)
    b_dates_for_d = base_dates[b_mask]
    pool_date_set = set()
    for b in b_dates_for_d:
        for t in ext_dates:
            if abs((t - b).days) <= 5:
                pool_date_set.add(t)
    pool_time_indices[d] = sorted([ext_date_to_idx[t] for t in pool_date_set])

# ====== Sea cells ======
n_lat, n_lon = target_sst.shape[1], target_sst.shape[2]
sea_cells = ~np.isnan(target_sst).any(axis=0)
print(f"Sea cells: {sea_cells.sum()} out of {n_lat*n_lon}")

# ====== Compute threshold and climatology for each cell and doy ======
# For each doy d, compute threshold[cell] and climatology[cell]
threshold_raw = np.full((366, n_lat, n_lon), np.nan)  # raw threshold before smoothing
climatology_raw = np.full((366, n_lat, n_lon), np.nan)  # raw climatology before smoothing

for d in range(1, 367):
    if d == 60:
        continue
    pool_idx = pool_time_indices[d]
    # Extract pool values for all cells: (n_pool, n_lat, n_lon)
    pool_vals = baseline_sst[pool_idx]  # shape (n_pool, n_lat, n_lon)
    
    # For each cell, compute percentile and mean ignoring NaN
    # Use np.percentile with method='hazen' and nan-aware computation
    # We need to handle this per-cell since NaN positions differ
    
    for i in range(n_lat):
        for j in range(n_lon):
            vals = pool_vals[:, i, j]
            valid = vals[~np.isnan(vals)]
            if len(valid) > 0:
                threshold_raw[d-1, i, j] = np.percentile(valid, 90, method='hazen')
                climatology_raw[d-1, i, j] = np.mean(valid)
            # else stays NaN

print("Threshold computation done")

# Set day 60 to mean of days 59 and 61
threshold_raw[59] = (threshold_raw[58] + threshold_raw[60]) / 2
climatology_raw[59] = (climatology_raw[58] + climatology_raw[60]) / 2

print("Day 60 set to mean of 59 and 61")
print("NaN in threshold:", np.isnan(threshold_raw).sum())
print("NaN in climatology:", np.isnan(climatology_raw).sum())
