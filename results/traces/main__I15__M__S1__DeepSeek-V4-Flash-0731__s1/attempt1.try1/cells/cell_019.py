import numpy as np

# Load raw threshold and climatology
threshold_raw = np.load('/tmp/threshold_raw.npy')  # (366, n_sea)
clim_raw = np.load('/tmp/clim_raw.npy')  # (366, n_sea)

print(f"Shapes: threshold_raw={threshold_raw.shape}, clim_raw={clim_raw.shape}")

# Check for any remaining NaNs
print(f"NaN in threshold: {np.isnan(threshold_raw).sum()}")
print(f"NaN in climatology: {np.isnan(clim_raw).sum()}")

# Check some values
print(f"Threshold DOY 1, cell 0: {threshold_raw[0, 0]}")
print(f"Threshold DOY 60, cell 0: {threshold_raw[59, 0]}")
print(f"Clim DOY 1, cell 0: {clim_raw[0, 0]}")
print(f"Clim DOY 60, cell 0: {clim_raw[59, 0]}")
