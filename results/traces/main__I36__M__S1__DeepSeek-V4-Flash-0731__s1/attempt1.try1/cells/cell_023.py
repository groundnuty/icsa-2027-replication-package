
import numpy as np

threshold_raw = np.load('/tmp/threshold_raw.npy')
threshold_smoothed = np.load('/tmp/threshold_smoothed.npy')

# Check cell (30,30) for doy 138-168
print("Raw threshold values for doy 138-168, cell (30,30):")
for k in range(31):
    idx = (153-15+k) % 366
    val = threshold_raw[idx, 30, 30]
    print(f"  doy {idx+1}: {val}")

print(f"\nNaN count in these: {sum(1 for k in range(31) if np.isnan(threshold_raw[(153-15+k)%366, 30, 30]))}")

# Compute mean manually, ignoring NaN
raw_vals = [threshold_raw[(153-15+k) % 366, 30, 30] for k in range(31)]
valid = [v for v in raw_vals if not np.isnan(v)]
print(f"Valid values: {len(valid)}")
print(f"Mean of valid: {np.mean(valid)}")
print(f"Smoothed: {threshold_smoothed[152, 30, 30]}")
