
import numpy as np

threshold_raw = np.load('/tmp/threshold_raw.npy')
threshold_smooth = np.load('/tmp/threshold_smooth.npy')
climatology_raw = np.load('/tmp/climatology_raw.npy')
climatology_smooth = np.load('/tmp/climatology_smooth.npy')

# Verify smoothing for a specific cell and day
i, j = 0, 0  # cell (0,0)
d = 153

# Manually compute the smoothed threshold for day 153
# Days 138-168 (153-15 to 153+15)
raw_values = threshold_raw[138:169, i, j]
manual_mean = np.mean(raw_values)
print(f"Manual smooth threshold day 153 cell (0,0): {manual_mean:.6f}")
print(f"Computed smooth threshold day 153 cell (0,0): {threshold_smooth[153, i, j]:.6f}")
print(f"Match: {abs(manual_mean - threshold_smooth[153, i, j]) < 1e-10}")

# Verify wrap-around for day 1
d = 1
# Days 352-366 and 1-16
indices = list(range(352, 367)) + list(range(1, 17))
raw_values = threshold_raw[indices, i, j]
manual_mean = np.mean(raw_values)
print(f"\nManual smooth threshold day 1 cell (0,0): {manual_mean:.6f}")
print(f"Computed smooth threshold day 1 cell (0,0): {threshold_smooth[1, i, j]:.6f}")
print(f"Match: {abs(manual_mean - threshold_smooth[1, i, j]) < 1e-10}")

# Verify day 60 smoothing
d = 60
# Days 45-75
raw_values = threshold_raw[45:76, i, j]
manual_mean = np.mean(raw_values)
print(f"\nManual smooth threshold day 60 cell (0,0): {manual_mean:.6f}")
print(f"Computed smooth threshold day 60 cell (0,0): {threshold_smooth[60, i, j]:.6f}")
print(f"Match: {abs(manual_mean - threshold_smooth[60, i, j]) < 1e-10}")
