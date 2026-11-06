
import numpy as np

threshold_raw = np.load('/tmp/threshold_raw.npy')
threshold_smoothed = np.load('/tmp/threshold_smoothed.npy')

# For doy 153 (index 152), the smoothing window is indices 137-167
# doy 153 corresponds to index 152
# Window: indices 152-15=137 to 152+15=167
indices = [(152 + k) % 366 for k in range(-15, 16)]
print(f"Indices: {indices}")

raw_vals = [threshold_raw[idx, 30, 30] for idx in indices]
print(f"Mean of raw: {np.mean(raw_vals)}")
print(f"Smoothed: {threshold_smoothed[152, 30, 30]}")

# Check if they match
print(f"Match: {abs(np.mean(raw_vals) - threshold_smoothed[152, 30, 30]) < 1e-10}")
