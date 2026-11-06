
import numpy as np

threshold_raw = np.load('/tmp/threshold_raw.npy')  # (367, 60, 60)
threshold_smooth = np.load('/tmp/threshold_smooth.npy')

# Verify smoothing for doy 153, cell (0,0)
d = 153
i, j = 0, 0

# After filling day 60
threshold_filled = threshold_raw.copy()
threshold_filled[60] = (threshold_filled[59] + threshold_filled[61]) / 2

# Smoothing window: days 138-168 (d-15 to d+15)
window = range(d-15, d+16)  # 138 to 168
vals = [threshold_filled[k, i, j] for k in window]
print(f"Window days: {list(window)}")
print(f"Values: {vals}")
print(f"Manual mean: {np.mean(vals):.6f}")
print(f"Stored smoothed: {threshold_smooth[d, i, j]:.6f}")
print(f"Match: {abs(np.mean(vals) - threshold_smooth[d, i, j]) < 1e-10}")

# Verify wrapping: doy 1
d = 1
# Window: days 1-15 and 352-366
window = list(range(367-15, 367)) + list(range(1, 16+1))
print(f"\nDay 1 window: {window}")
vals = [threshold_filled[k, i, j] for k in window]
print(f"Manual mean: {np.mean(vals):.6f}")
print(f"Stored smoothed: {threshold_smooth[d, i, j]:.6f}")
print(f"Match: {abs(np.mean(vals) - threshold_smooth[d, i, j]) < 1e-10}")
