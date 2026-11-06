
import numpy as np
from datetime import date, timedelta
import time

# We need to reconstruct some things since the sandbox state persists
# The baseline_sst and target_sst arrays should still be in memory

# Let me check what's available
print("baseline_sst shape:", baseline_sst.shape)
print("target_sst shape:", target_sst.shape)
print("sea_cells shape:", sea_cells.shape, "sum:", sea_cells.sum())

# ===== STEP 4: Compute thresholds and climatology =====
# For each doy (1-366, excluding 60), compute pool, threshold, climatology for each sea cell
# Threshold = 90th percentile (hazen method), Climatology = mean

n_doy = 366
n_lat, n_lon = len(lat_idx), len(lon_idx)

# We'll compute for all cells, not just sea cells (sea cells will use their data, 
# land cells will be NaN anyway)
# Initialize threshold and climatology arrays
threshold = np.full((n_doy, n_lat, n_lon), np.nan, dtype=np.float64)
climatology = np.full((n_doy, n_lat, n_lon), np.nan, dtype=np.float64)

# For each doy, find pool dates and compute
t0 = time.time()
for doy in range(1, 367):
    if doy == 60:
        continue
    
    pool_dates = doy_to_pool_dates[doy]
    pool_indices = [baseline_date_to_idx[d] for d in pool_dates]
    
    # Extract pool values for all cells
    pool = baseline_sst[pool_indices]  # shape: (n_pool_dates, n_lat, n_lon)
    pool_f64 = pool.astype(np.float64)
    
    # Compute threshold (90th percentile, hazen) and climatology (mean) for each cell
    # Ignoring NaN
    for la in range(n_lat):
        for lo in range(n_lon):
            if not sea_cells[la, lo]:
                continue
            vals = pool_f64[:, la, lo]
            valid = ~np.isnan(vals)
            if valid.sum() > 0:
                # threshold
                threshold[doy-1, la, lo] = np.quantile(vals[valid], 0.9, method='hazen')
                # climatology
                climatology[doy-1, la, lo] = np.mean(vals[valid])
    
    if doy % 50 == 0:
        print(f"  Processed doy {doy}, elapsed: {time.time()-t0:.1f}s")

print(f"Threshold/climatology computation took {time.time()-t0:.1f}s")

# ===== STEP 5: Set day 60 = mean of days 59 and 61 =====
threshold[59] = (threshold[58] + threshold[60]) / 2.0
climatology[59] = (climatology[58] + climatology[60]) / 2.0
print("Day 60 set")

# ===== STEP 6: Smooth with 31-day centered moving average (wrapping) =====
def smooth_wrap(arr, window=31):
    """Smooth a 366-element array with an unweighted centered 31-day moving average that wraps."""
    # arr shape: (366, n_lat, n_lon)
    half = window // 2  # 15
    result = np.zeros_like(arr)
    for d in range(366):
        # Days d-15 to d+15, modulo 366
        indices = [(d + i) % 366 for i in range(-half, half+1)]
        result[d] = np.mean(arr[indices], axis=0)
    return result

print("Smoothing...")
t0 = time.time()
threshold_smooth = smooth_wrap(threshold)
climatology_smooth = smooth_wrap(climatology)
print(f"Smoothing took {time.time()-t0:.1f}s")
print("Done smoothing")
