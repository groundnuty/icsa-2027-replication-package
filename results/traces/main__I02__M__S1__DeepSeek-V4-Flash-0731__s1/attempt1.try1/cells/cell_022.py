
import numpy as np

threshold = np.load('/tmp/threshold_unsmoothed.npy')
climatology = np.load('/tmp/climatology_unsmoothed.npy')

def smooth_wrap(arr):
    """Smooth a 366-element array with a 31-day centered moving mean that wraps around.
    arr shape: (lat, lon, 366) or (366,)
    """
    n = 366
    window = 31
    half = window // 2  # 15
    
    # For each cell
    if arr.ndim == 3:
        n_lat, n_lon, n_doy = arr.shape
        result = np.zeros_like(arr)
        for i in range(n_lat):
            for j in range(n_lon):
                result[i, j, :] = smooth_wrap(arr[i, j, :])
        return result
    elif arr.ndim == 1:
        result = np.zeros_like(arr)
        for d in range(n):
            # Sum from d-15 to d+15, wrapping around
            vals = []
            for k in range(-15, 16):
                idx = (d + k) % n
                vals.append(arr[idx])
            result[d] = np.mean(vals)
        return result
    else:
        raise ValueError(f"Unsupported shape: {arr.shape}")

# Actually, this is too slow with the loop. Let me use a more efficient approach.
# For each day d, smoothed[d] = mean of arr[(d-15)%366] ... arr[(d+15)%366]
# This is a circular moving average

def smooth_wrap_fast(arr):
    """arr shape: (lat, lon, 366)"""
    n_lat, n_lon, n_doy = arr.shape
    result = np.zeros_like(arr)
    
    # Create extended array with circular padding
    # For window size 31, we need 15 extra on each side
    ext = np.concatenate([arr[:, :, -15:], arr, arr[:, :, :15]], axis=2)
    # ext shape: (n_lat, n_lon, 366+30)
    
    # Use cumulative sum for efficient computation
    cumsum = np.cumsum(ext, axis=2)
    
    for d in range(n_doy):
        start = d  # in the extended array, this corresponds to d in original (since ext starts with -15 offset)
        # Actually let me think again. 
        # ext = arr[-15:] + arr + arr[:15], so ext[:,:,i] = arr[:,:,(i-15)%366]
        # For day d (0-indexed in arr), we want arr[(d-15)%366] to arr[(d+15)%366]
        # In ext, arr[(d-15)%366] is at index (d-15+15) = d (since ext[0] = arr[-15])
        # and arr[(d+15)%366] is at index (d+15+15) = d+30
        # So we want ext[:,:,d] to ext[:,:,d+30], which is 31 values
        if d == 0:
            result[:, :, d] = np.sum(ext[:, :, 0:31], axis=2) / 31.0
        else:
            result[:, :, d] = (cumsum[:, :, d+30] - cumsum[:, :, d-1]) / 31.0
    
    return result

print("Smoothing threshold...")
threshold_smoothed = smooth_wrap_fast(threshold)
print("Smoothing climatology...")
climatology_smoothed = smooth_wrap_fast(climatology)

# Verify
print(f"Threshold smoothed shape: {threshold_smoothed.shape}")
print(f"Climatology smoothed shape: {climatology_smoothed.shape}")
print(f"Threshold smoothed NaN count: {np.isnan(threshold_smoothed).sum()}")
print(f"Climatology smoothed NaN count: {np.isnan(climatology_smoothed).sum()}")

# Verify the smoothing for a specific cell
i, j = 34, 213  # First sea cell
# Check smoothing manually for a few days
for day_idx in [0, 1, 59, 60, 100, 365]:
    start = (day_idx - 15) % 366
    manual = np.mean([threshold[i,j,(day_idx+k)%366] for k in range(-15,16)])
    print(f"Day {day_idx+1}: smoothed={threshold_smoothed[i,j,day_idx]:.6f}, manual={manual:.6f}")

# Save smoothed
np.save('/tmp/threshold.npy', threshold_smoothed)
np.save('/tmp/climatology.npy', climatology_smoothed)
print("Saved smoothed thresholds and climatologies")
