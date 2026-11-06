
import numpy as np

thresholds_raw = np.load('/tmp/thresholds_raw.npy')
climatology_raw = np.load('/tmp/climatology_raw.npy')
sea_mask = np.load('/tmp/sea_mask.npy')

# Check index 59 (DOY 60)
print("Thresholds[59] NaN count:", np.isnan(thresholds_raw[59]).sum())
print("Climatology[59] NaN count:", np.isnan(climatology_raw[59]).sum())

# Check all other indices for sea cells
non60_nan_thresh = 0
non60_nan_clim = 0
for d in range(1, 367):
    if d == 60:
        continue
    non60_nan_thresh += np.isnan(thresholds_raw[d-1][sea_mask]).sum()
    non60_nan_clim += np.isnan(climatology_raw[d-1][sea_mask]).sum()

print(f"NaN in thresholds for sea cells excluding DOY 60: {non60_nan_thresh}")
print(f"NaN in climatology for sea cells excluding DOY 60: {non60_nan_clim}")
