
import numpy as np

# Load the raw threshold (before smoothing)
threshold = np.load('/tmp/threshold.npy')
climatology = np.load('/tmp/climatology.npy')
sea_mask = np.load('/tmp/sea_mask.npy')

# Check day 60 (index 59) vs days 59 and 61 (indices 58 and 60)
# For the first sea cell
sea_indices = np.where(sea_mask)
lat_i, lon_j = sea_indices[0][0], sea_indices[1][0]

print("Raw threshold values for first sea cell:")
print(f"  Day 59 (idx 58): {threshold[58, lat_i, lon_j]}")
print(f"  Day 60 (idx 59): {threshold[59, lat_i, lon_j]}")
print(f"  Day 61 (idx 60): {threshold[60, lat_i, lon_j]}")
print(f"  Day 60 should = (day 59 + day 61) / 2: {(threshold[58, lat_i, lon_j] + threshold[60, lat_i, lon_j]) / 2}")
print(f"  Actual day 60: {threshold[59, lat_i, lon_j]}")

# Verify the smoothing
threshold_smooth = np.load('/tmp/threshold_smooth.npy')

# Check that smoothing for day 60 (index 59) averages days 44-74 (mod 366)
# i.e., indices 44 to 74
raw_values = threshold[44:75, lat_i, lon_j]
smoothed_val = np.mean(raw_values)
print(f"\nSmoothing check for day 60 (idx 59):")
print(f"  Manual smoothing: {smoothed_val}")
print(f"  Actual smoothing: {threshold_smooth[59, lat_i, lon_j]}")

# Check smoothing wraps correctly for day 1 (index 0)
# Should average days 351-365 and 0-15
indices = list(range(351, 366)) + list(range(0, 16))
raw_values = threshold[indices, lat_i, lon_j]
smoothed_val = np.mean(raw_values)
print(f"\nSmoothing check for day 1 (idx 0):")
print(f"  Manual smoothing: {smoothed_val}")
print(f"  Actual smoothing: {threshold_smooth[0, lat_i, lon_j]}")
