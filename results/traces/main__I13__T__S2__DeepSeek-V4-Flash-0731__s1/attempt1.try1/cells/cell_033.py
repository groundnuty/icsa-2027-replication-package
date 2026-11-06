
import numpy as np

# Load thresholds
thresholds_raw = np.load('thresholds_raw.npy')
thresholds_smooth = np.load('thresholds_smooth.npy')

# Check smoothing for a sea cell (cell 0,0 has no NaN)
print("=== Smoothing verification for cell (0,0) ===")
print(f"Raw threshold NaN count for cell (0,0): {np.isnan(thresholds_raw[:, 0, 0]).sum()}")
print(f"Smoothed threshold NaN count for cell (0,0): {np.isnan(thresholds_smooth[:, 0, 0]).sum()}")

# Verify smoothing manually
# Day 1 (index 0): mean of indices 351-365 and 0-15
expected = np.mean(np.concatenate([thresholds_raw[351:366, 0, 0], thresholds_raw[0:16, 0, 0]]))
actual = thresholds_smooth[0, 0, 0]
print(f"Day 1: expected={expected:.6f}, actual={actual:.6f}, diff={abs(expected-actual):.2e}")

# Day 153 (index 152): mean of indices 137-167
expected = np.mean(thresholds_raw[137:168, 0, 0])
actual = thresholds_smooth[152, 0, 0]
print(f"Day 153: expected={expected:.6f}, actual={actual:.6f}, diff={abs(expected-actual):.2e}")

# Day 366 (index 365): mean of indices 350-365 and 0-14
expected = np.mean(np.concatenate([thresholds_raw[350:366, 0, 0], thresholds_raw[0:15, 0, 0]]))
actual = thresholds_smooth[365, 0, 0]
print(f"Day 366: expected={expected:.6f}, actual={actual:.6f}, diff={abs(expected-actual):.2e}")

# Verify day 60 (index 59) is correctly set
print(f"\nDay 59 raw: {thresholds_raw[58, 0, 0]:.6f}")
print(f"Day 60 raw: {thresholds_raw[59, 0, 0]:.6f}")
print(f"Day 61 raw: {thresholds_raw[60, 0, 0]:.6f}")
print(f"Day 60 should be: {(thresholds_raw[58, 0, 0] + thresholds_raw[60, 0, 0]) / 2:.6f}")

# Verify all sea cells have finite smoothed thresholds
sst_target = np.load('sst_target.npy')
sea_cells = np.all(np.isfinite(sst_target), axis=0)
all_finite = np.all(np.isfinite(thresholds_smooth[:, sea_cells]))
print(f"\nAll smoothed thresholds finite for sea cells: {all_finite}")
