
import numpy as np

thresholds = np.load('/tmp/thresholds.npy')
thresholds_smoothed = np.load('/tmp/thresholds_smoothed.npy')

# Verify smoothing for doy 153, cell (0,0)
# Day 153 in 1-indexed = index 152 in 0-indexed
# Window: days 138-168 (1-indexed) = indices 137-167 (0-indexed)
# Mod 366

idx_153 = [(153 - 1 + i) % 366 for i in range(-15, 16)]
# 0-indexed
idx_153_0 = [i % 366 for i in range(153-1-15, 153+15)]
# This should be indices 137-167 (0-indexed)
print("Indices for doy 153 smoothing:", idx_153_0[0], "to", idx_153_0[-1])
print("Expected: 137 to 167")

vals = thresholds[idx_153_0, 0, 0]
manual_smooth = np.mean(vals)
print("Manual smoothed:", manual_smooth)
print("Computed smoothed:", thresholds_smoothed[152, 0, 0])

# Also verify wrap-around for doy 1 (index 0)
# Days d-15 to d+15 mod 366
# Days 1-15+366 to 1+15 = days 352-366 and 1-16 (1-indexed)
# Indices: (1-1-15) to (1-1+15) mod 366 = -15 to 15 mod 366
# = 351 to 365 (from -15 to -1) and 0 to 15
idx_1 = [i % 366 for i in range(-15, 16)]
print("\nIndices for doy 1 smoothing:", idx_1)
vals_1 = thresholds[idx_1, 0, 0]
manual_smooth_1 = np.mean(vals_1)
print("Manual smoothed day 1:", manual_smooth_1)
print("Computed smoothed day 1:", thresholds_smoothed[0, 0, 0])
