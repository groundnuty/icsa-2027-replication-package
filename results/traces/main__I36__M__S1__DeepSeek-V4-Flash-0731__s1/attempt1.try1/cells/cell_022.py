
import numpy as np

# Verify smoothing
threshold_raw = np.load('/tmp/threshold_raw.npy')
threshold_smoothed = np.load('/tmp/threshold_smoothed.npy')

# For a simple test, create a constant array and check smoothing
test = np.ones((366, 3, 3))
# Manually compute smoothed for doy 0
n = 366
d = 0
indices = [(d + k) % n for k in range(-15, 16)]
print(f"Indices for day 0: {indices}")

# Check: day 0 should average days 351-365 and 0-15 (modulo 366)
print(f"Indices: {len(indices)} values from {min(indices)} to {max(indices)}")
print(f"Should include: {list(range(351,366)) + list(range(0,16))}")

# Verify with actual data
# Check cell (30,30), doy 153 (June 1) 
# The smoothed value should be the mean of days 138-168 (153-15 to 153+15)
print(f"\nRaw threshold doy 138-168, cell (30,30):")
raw_vals = [threshold_raw[(153-15+k) % 366, 30, 30] for k in range(31)]
print(f"Mean of raw: {np.mean(raw_vals)}")
print(f"Smoothed value: {threshold_smoothed[152, 30, 30]}")
