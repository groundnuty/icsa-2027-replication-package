
import numpy as np

thresholds_raw = np.load('/tmp/thresholds_raw.npy')
climatology_raw = np.load('/tmp/climatology_raw.npy')

# Step 1: Set DOY 60 (index 59) = mean of DOY 59 (index 58) and DOY 61 (index 60)
thresholds_raw[59] = (thresholds_raw[58] + thresholds_raw[60]) / 2.0
climatology_raw[59] = (climatology_raw[58] + climatology_raw[60]) / 2.0

# Verify
print("Thresholds[59] NaN count:", np.isnan(thresholds_raw[59]).sum())
print("Climatology[59] NaN count:", np.isnan(climatology_raw[59]).sum())

# Step 2: Smooth with 31-day centered moving mean wrapping around the year
# For day d (1-indexed, index d-1 in array), average days d-15 to d+15 (modulo 366)

def smooth_wrap(arr):
    """Smooth a (366, n_lat, n_lon) array with a 31-day centered moving mean that wraps."""
    # arr shape: (366, n_lat, n_lon)
    # For each day index i (0-365), average indices (i-15)%366 to (i+15)%366
    n = arr.shape[0]  # should be 366
    
    # We'll tile the array 3 times and use rolling window
    # Actually, let's build it directly
    result = np.zeros_like(arr)
    
    # For each day, collect the 31 values
    for i in range(n):
        indices = [(i + j) % n for j in range(-15, 16)]
        result[i] = np.mean(arr[indices], axis=0)
    
    return result

thresholds_smoothed = smooth_wrap(thresholds_raw)
climatology_smoothed = smooth_wrap(climatology_raw)

print("Smoothed thresholds shape:", thresholds_smoothed.shape)
print("Smoothed climatology shape:", climatology_smoothed.shape)

# Check for NaN
print("NaN in smoothed thresholds:", np.isnan(thresholds_smoothed).sum())
print("NaN in smoothed climatology:", np.isnan(climatology_smoothed).sum())

# Save
np.save('/tmp/thresholds_smoothed.npy', thresholds_smoothed)
np.save('/tmp/climatology_smoothed.npy', climatology_smoothed)
print("Saved smoothed thresholds and climatology")
