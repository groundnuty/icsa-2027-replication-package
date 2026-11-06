
import numpy as np
import datetime

# We have baseline_sst (4028, 60, 60) and baseline_dates

# Compute per-doy thresholds and climatology
n_cells = 60 * 60
# Flatten cells
baseline_flat = baseline_sst.reshape(4028, -1)  # (4028, 3600)

# For each doy, compute threshold and mean
print("Computing per-doy thresholds and climatology...")
start = datetime.datetime.now()

threshold = np.full((366, 3600), np.nan, dtype=np.float64)
climatology = np.full((366, 3600), np.nan, dtype=np.float64)

for d in range(1, 367):
    if d == 60:
        continue
    pool_dates = doy_to_pool_dates[d]
    pool_idx = [date_to_idx[date] for date in pool_dates]
    pool_data = baseline_flat[pool_idx, :]  # (n_pool, 3600)
    
    # Compute 90th percentile (Hazen) and mean, ignoring NaN
    for c in range(n_cells):
        col = pool_data[:, c]
        valid = col[~np.isnan(col)]
        if len(valid) > 0:
            # Hazen method (type 5)
            # MATLAB quantile default: p*(n+1) position, interpolate
            n = len(valid)
            q = 0.9
            pos = q * (n + 1) - 1  # 0-indexed position
            idx_floor = int(np.floor(pos))
            idx_ceil = int(np.ceil(pos))
            if idx_floor < 0:
                threshold[d-1, c] = valid[0]
            elif idx_ceil >= n:
                threshold[d-1, c] = valid[-1]
            elif idx_floor == idx_ceil:
                threshold[d-1, c] = valid[idx_floor]
            else:
                frac = pos - idx_floor
                threshold[d-1, c] = valid[idx_floor] * (1 - frac) + valid[idx_ceil] * frac
            climatology[d-1, c] = np.mean(valid)
    
    if d % 50 == 0:
        print(f"  Processed doy {d}")

print(f"Done computing in {(datetime.datetime.now()-start).total_seconds():.1f}s")
print(f"Threshold NaN count: {np.isnan(threshold).sum()}")
print(f"Climatology NaN count: {np.isnan(climatology).sum()}")
