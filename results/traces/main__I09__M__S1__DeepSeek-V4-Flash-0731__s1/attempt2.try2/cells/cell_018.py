
import numpy as np
import time

# Load data
baseline_sst = np.load('/tmp/baseline_sst.npy')
sea_cells = np.load('/tmp/sea_cells.npy')
doy_pool_indices = np.load('/tmp/doy_pool_indices.npy', allow_pickle=True)

n_lat, n_lon = sea_cells.shape

# Compute thresholds and climatology for all cells and doys (1-366)
thresholds = np.full((366, n_lat, n_lon), np.nan)
climatology = np.full((366, n_lat, n_lon), np.nan)

start = time.time()
for d in range(1, 367):
    if d == 60:
        continue
    pool_idx = doy_pool_indices[d-1]  # index 0 corresponds to doy 1
    if len(pool_idx) == 0:
        continue
    pool = baseline_sst[pool_idx]  # (n_pool, n_lat, n_lon)
    
    # Compute 90th percentile and mean along axis 0, ignoring NaN
    thresholds[d-1] = np.nanquantile(pool, 0.9, axis=0, method='hazen')
    climatology[d-1] = np.nanmean(pool, axis=0)
    
    if d % 50 == 0:
        print(f"Processed doy {d}, elapsed: {time.time()-start:.1f}s")

# Set doy 60 (index 59) to mean of doys 59 and 61 (indices 58 and 60)
thresholds[59] = (thresholds[58] + thresholds[60]) / 2
climatology[59] = (climatology[58] + climatology[60]) / 2

print(f"Total time: {time.time()-start:.1f}s")
print(f"Thresholds shape: {thresholds.shape}")
print(f"NaN count in thresholds: {np.isnan(thresholds).sum()}")
print(f"NaN count in climatology: {np.isnan(climatology).sum()}")

# Check some values for a sea cell
si, sj = np.where(sea_cells)
si, sj = si[0], sj[0]
print(f"Sea cell at ({si}, {sj}):")
print(f"  Threshold doy 180: {thresholds[179, si, sj]}")
print(f"  Climatology doy 180: {climatology[179, si, sj]}")

np.save('/tmp/thresholds.npy', thresholds)
np.save('/tmp/climatology.npy', climatology)
print("Saved")
