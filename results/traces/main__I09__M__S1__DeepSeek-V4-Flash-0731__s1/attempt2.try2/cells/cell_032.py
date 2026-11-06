
import numpy as np

# Load data
thresholds = np.load('/tmp/thresholds.npy')
thr_smooth = np.load('/tmp/thr_smooth.npy')

# Verify smoothing for cell (0,0), doy 200
# doy 200 is index 199 (0-indexed)
# Smoothing window: doys 185-215 (mod 366)

si, sj = 0, 0
raw_values = thresholds[:, si, sj]

# Compute smoothing for doy 200 manually
d = 199  # 0-indexed for doy 200
window_indices = [(d + offset) % 366 for offset in range(-15, 16)]
window_values = [raw_values[i] for i in window_indices]
manual_smooth = np.mean(window_values)

print(f"Raw threshold for doy 185-215 (cell 0,0):")
for i in range(184, 216):
    print(f"  doy {i+1}: {raw_values[i]:.6f}")

print(f"\nManual smoothed threshold for doy 200: {manual_smooth:.6f}")
print(f"Stored smoothed threshold: {thr_smooth[199, 0, 0]:.6f}")
print(f"Match: {np.isclose(manual_smooth, thr_smooth[199, 0, 0])}")

# Verify wrap-around for doy 1
d = 0  # doy 1
window_indices = [(d + offset) % 366 for offset in range(-15, 16)]
window_values = [raw_values[i] for i in window_indices]
manual_smooth_d1 = np.mean(window_values)
print(f"\nManual smoothed threshold for doy 1: {manual_smooth_d1:.6f}")
print(f"Stored smoothed threshold: {thr_smooth[0, 0, 0]:.6f}")
print(f"Match: {np.isclose(manual_smooth_d1, thr_smooth[0, 0, 0])}")

# Verify wrap-around for doy 366
d = 365  # doy 366
window_indices = [(d + offset) % 366 for offset in range(-15, 16)]
window_values = [raw_values[i] for i in window_indices]
manual_smooth_d366 = np.mean(window_values)
print(f"\nManual smoothed threshold for doy 366: {manual_smooth_d366:.6f}")
print(f"Stored smoothed threshold: {thr_smooth[365, 0, 0]:.6f}")
print(f"Match: {np.isclose(manual_smooth_d366, thr_smooth[365, 0, 0])}")
