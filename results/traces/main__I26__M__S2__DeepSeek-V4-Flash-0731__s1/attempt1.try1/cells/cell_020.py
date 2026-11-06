
import numpy as np

# Load the unsmoothed and smoothed data
threshold_raw = np.load('/tmp/threshold_raw.npy')
climatology_raw = np.load('/tmp/climatology_raw.npy')
threshold_smooth = np.load('/tmp/threshold_smoothed.npy')
climatology_smooth = np.load('/tmp/climatology_smoothed.npy')

# Verify smoothing for a specific cell
cell = (0, 0)
raw = threshold_raw[:, cell[0], cell[1]]
sm = threshold_smooth[:, cell[0], cell[1]]

# Day 0 should average days 349, 350, ..., 364, 0, 1, ..., 14
# That's indices (0-15+366) % 366 ... (0+15) % 366
# = 351, 352, ..., 365, 0, 1, ..., 14
# = 15 days from 351-365 + 16 days from 0-14 = 31 days

indices = [(0 + j) % 366 for j in range(-15, 16)]
manual_mean = np.mean(raw[indices])
print(f"Day 0: manual mean = {manual_mean:.6f}, smoothed = {sm[0]:.6f}")
print(f"Match: {abs(manual_mean - sm[0]) < 1e-10}")

# Check day 100
indices = [(100 + j) % 366 for j in range(-15, 16)]
manual_mean = np.mean(raw[indices])
print(f"Day 100: manual mean = {manual_mean:.6f}, smoothed = {sm[100]:.6f}")
print(f"Match: {abs(manual_mean - sm[100]) < 1e-10}")

# Check day 365 (last)
indices = [(365 + j) % 366 for j in range(-15, 16)]
manual_mean = np.mean(raw[indices])
print(f"Day 365: manual mean = {manual_mean:.6f}, smoothed = {sm[365]:.6f}")
print(f"Match: {abs(manual_mean - sm[365]) < 1e-10}")

# Also verify day 60 handling
print(f"\nDay 59 (index 58) raw: {raw[58]:.6f}")
print(f"Day 60 (index 59) raw: {raw[59]:.6f}")
print(f"Day 61 (index 60) raw: {raw[60]:.6f}")
print(f"Day 60 should be (day59 + day61)/2 = {(raw[58] + raw[60]) / 2:.6f}")
