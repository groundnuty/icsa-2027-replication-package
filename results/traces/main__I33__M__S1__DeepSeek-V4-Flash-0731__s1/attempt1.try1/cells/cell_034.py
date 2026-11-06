
import numpy as np

# Verify smoothing manually
threshold_raw = np.load('output/threshold_raw.npy')
climatology_raw = np.load('output/climatology_raw.npy')
threshold_smooth = np.load('output/threshold_smooth.npy')
climatology_smooth = np.load('output/climatology_smooth.npy')

# Set day 60 (index 59) to mean of days 59 and 61
threshold_d60 = threshold_raw.copy()
threshold_d60[59] = (threshold_raw[58] + threshold_raw[60]) / 2.0

clim_d60 = climatology_raw.copy()
clim_d60[59] = (climatology_raw[58] + climatology_raw[60]) / 2.0

# Verify smoothing for cell (0,0) at day 153 (index 152)
# Window: days 138-168 (indices 137-167)
i = 152  # day 153
indices = [(i + j) % 366 for j in range(-15, 16)]
print(f"Smoothing indices for day 153: {indices}")

# Manual mean for cell (0,0)
manual_mean = np.mean(threshold_d60[indices, 0, 0])
stored_mean = threshold_smooth[152, 0, 0]
print(f"Manual mean: {manual_mean:.6f}")
print(f"Stored smoothed: {stored_mean:.6f}")
print(f"Match: {np.isclose(manual_mean, stored_mean)}")

# Also verify climatology smoothing
manual_clim = np.mean(clim_d60[indices, 0, 0])
stored_clim = climatology_smooth[152, 0, 0]
print(f"\nManual clim mean: {manual_clim:.6f}")
print(f"Stored smoothed clim: {stored_clim:.6f}")
print(f"Match: {np.isclose(manual_clim, stored_clim)}")

# Check raw vs smoothed for a few days
print(f"\nThreshold raw [153,0,0]: {threshold_raw[152, 0, 0]:.6f}")
print(f"Threshold smooth [153,0,0]: {threshold_smooth[152, 0, 0]:.6f}")
print(f"Clim raw [153,0,0]: {climatology_raw[152, 0, 0]:.6f}")
print(f"Clim smooth [153,0,0]: {climatology_smooth[152, 0, 0]:.6f}")
