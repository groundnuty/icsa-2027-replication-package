
import numpy as np

# threshold and climatology are (366, n_sea)
# Smooth with unweighted centred 31-day moving mean that wraps
# Day d averages days d-15 to d+15 (modulo 366)

def smooth_wrap(data, window=31):
    """Smooth a (366, ...) array with a centred moving mean that wraps around."""
    n = data.shape[0]
    half = window // 2  # 15
    result = np.empty_like(data)
    
    # Pad the data by wrapping around
    # For each day d (0-indexed), average days d-15 to d+15 (mod 366)
    for i in range(n):
        # Get indices i-15 to i+15 (mod n)
        idx = [(i + j) % n for j in range(-half, half + 1)]
        result[i] = np.mean(data[idx], axis=0)
    
    return result

threshold_smoothed = smooth_wrap(threshold)
climatology_smoothed = smooth_wrap(climatology)

print(f"Threshold smoothed shape: {threshold_smoothed.shape}")
print(f"Climatology smoothed shape: {climatology_smoothed.shape}")
print(f"Check: threshold[0] = {threshold_smoothed[0,:5]}")
print(f"Check: threshold[60] = {threshold_smoothed[60,:5]}")
print(f"Any NaN: {np.isnan(threshold_smoothed).any()}, {np.isnan(climatology_smoothed).any()}")
