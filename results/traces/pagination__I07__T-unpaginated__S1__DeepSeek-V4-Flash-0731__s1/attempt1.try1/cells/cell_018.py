
import numpy as np

# Check for NaN in raw and smoothed thresholds
threshold_raw = np.load('/tmp/threshold_raw.npy')
threshold_smooth = np.load('/tmp/threshold_smooth.npy')
climatology_raw = np.load('/tmp/climatology_raw.npy')
climatology_smooth = np.load('/tmp/climatology_smooth.npy')
sea_cells = np.load('/tmp/sea_cells.npy')

# Check NaN counts for sea cells only
n_sea_lat, n_sea_lon = sea_cells.shape
for cell_idx in range(n_sea_lat * n_sea_lon):
    li, loi = cell_idx // n_sea_lon, cell_idx % n_sea_lon
    if not sea_cells[li, loi]:
        continue
    thr_raw = threshold_raw[:, li, loi]
    thr_smooth = threshold_smooth[:, li, loi]
    if np.isnan(thr_raw).any():
        print(f"Cell ({li},{loi}): raw threshold has {np.isnan(thr_raw).sum()} NaN")
    if np.isnan(thr_smooth).any():
        print(f"Cell ({li},{loi}): smoothed threshold has {np.isnan(thr_smooth).sum()} NaN")

# Just check overall
print(f"Raw threshold NaN count: {np.isnan(threshold_raw).sum()}")
print(f"Smooth threshold NaN count: {np.isnan(threshold_smooth).sum()}")
print(f"Raw climatology NaN count: {np.isnan(climatology_raw).sum()}")
print(f"Smooth climatology NaN count: {np.isnan(climatology_smooth).sum()}")

# Check which cells have NaN in threshold
nan_mask_raw = np.isnan(threshold_raw).any(axis=0)
nan_mask_smooth = np.isnan(threshold_smooth).any(axis=0)
print(f"Cells with NaN in raw threshold: {nan_mask_raw.sum()}")
print(f"Cells with NaN in smoothed threshold: {nan_mask_smooth.sum()}")
print(f"Sea cells with NaN in smoothed threshold: {(nan_mask_smooth & sea_cells).sum()}")
