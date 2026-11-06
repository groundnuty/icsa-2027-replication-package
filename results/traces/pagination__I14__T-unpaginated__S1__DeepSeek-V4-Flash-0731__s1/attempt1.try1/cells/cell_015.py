
import numpy as np

# Load raw thresholds and climatologies
threshold = np.load('threshold_raw.npy')  # (366, 60, 60)
climatology = np.load('climatology_raw.npy')  # (366, 60, 60)

# Apply 31-day centered moving average that wraps around (mod 366)
# For day index i (0-based), average over days (i-15) mod 366 to (i+15) mod 366

def smooth_366(arr):
    """Smooth a (366, ...) array with an unweighted centred 31-day moving mean that wraps."""
    n = 366
    # Create a padded array
    # For wrapping, we need to access indices modulo 366
    # Use np.take with mode='wrap'
    result = np.zeros_like(arr)
    for i in range(n):
        # Get indices i-15 to i+15, modulo 366
        indices = [(i + j) % n for j in range(-15, 16)]
        result[i] = np.mean(arr[indices], axis=0)
    return result

print("Applying smoothing...")
threshold_smooth = smooth_366(threshold)
climatology_smooth = smooth_366(climatology)
print("Smoothing complete")

np.save('threshold_smooth.npy', threshold_smooth)
np.save('climatology_smooth.npy', climatology_smooth)
print("Saved smoothed thresholds and climatologies")

# Verify a few values
print(f"\nThreshold[180] (day 181) sample: {threshold_smooth[180, 150, 460]}")
print(f"Climatology[180] (day 181) sample: {climatology_smooth[180, 150, 460]}")
