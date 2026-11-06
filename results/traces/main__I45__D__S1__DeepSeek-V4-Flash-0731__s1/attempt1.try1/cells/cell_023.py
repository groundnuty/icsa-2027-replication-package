
import numpy as np

# Load raw threshold and climatology
threshold_raw = np.load('/work/threshold_raw.npy')  # (n_sea, 366)
climatology_raw = np.load('/work/climatology_raw.npy')

n_sea, nd = threshold_raw.shape
print(f"Shape: ({n_sea}, {nd})")

# Apply 31-day centered moving mean wrapping around (day d averages days d-15..d+15 modulo 366)
# This is equivalent to a convolution with a box filter of width 31, with circular padding

def circular_moving_mean(arr, window=31):
    """Apply unweighted centered moving mean with wrap-around."""
    n = arr.shape[-1]
    half = window // 2  # 15
    
    # Use convolution with 'wrap' boundary
    kernel = np.ones(window) / window
    
    # Apply along the last axis (the day-of-year axis)
    result = np.empty_like(arr, dtype=np.float64)
    for i in range(arr.shape[0]):
        # Pad circularly
        padded = np.concatenate([arr[i, -half:], arr[i], arr[i, :half]])
        result[i] = np.convolve(padded, kernel, mode='valid')
    
    return result

# Convert to float64 for precision
threshold_raw64 = threshold_raw.astype(np.float64)
climatology_raw64 = climatology_raw.astype(np.float64)

threshold_smooth = circular_moving_mean(threshold_raw64, 31)
climatology_smooth = circular_moving_mean(climatology_raw64, 31)

print("Threshold shape:", threshold_smooth.shape)
print("Climatology shape:", climatology_smooth.shape)
print("Any NaN in threshold_smooth:", np.isnan(threshold_smooth).any())
print("Any NaN in climatology_smooth:", np.isnan(climatology_smooth).any())

# Check some values
print("\nSample threshold values (cell 0):")
print("  Day 1:", threshold_smooth[0, 0])
print("  Day 153 (Jun 1):", threshold_smooth[0, 152])
print("  Day 244 (Aug 31):", threshold_smooth[0, 243])
print("  Day 366:", threshold_smooth[0, 365])

np.save('/work/threshold_smooth.npy', threshold_smooth)
np.save('/work/climatology_smooth.npy', climatology_smooth)
print("\nSaved smoothed threshold and climatology")
