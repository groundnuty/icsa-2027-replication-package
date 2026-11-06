import numpy as np

# Load intermediate results
threshold = np.load('/work/threshold_raw.npy')
climatology = np.load('/work/climatology_raw.npy')

def smooth_366(arr):
    n = 366
    half = 15
    pad = np.concatenate([arr[..., -half:], arr, arr[..., :half]], axis=-1)
    csum = np.concatenate([np.zeros(arr.shape[:-1] + (1,)), np.cumsum(pad, axis=-1)], axis=-1)
    window_sum = csum[..., 31:] - csum[..., :-31]
    return window_sum / 31.0

# Apply smoothing
threshold_smooth = smooth_366(threshold)
climatology_smooth = smooth_366(climatology)

print("Threshold smoothed shape:", threshold_smooth.shape)
print("Climatology smoothed shape:", climatology_smooth.shape)

# Verify shapes
assert threshold_smooth.shape == (60, 60, 366)
assert climatology_smooth.shape == (60, 60, 366)

# Save smoothed results
np.save('/work/threshold_smooth.npy', threshold_smooth)
np.save('/work/climatology_smooth.npy', climatology_smooth)

print("Smoothed results saved")
print(f"Sample smoothed threshold (cell 0,0, DOY 180): {threshold_smooth[0, 0, 179]}")
print(f"Sample smoothed climatology (cell 0,0, DOY 180): {climatology_smooth[0, 0, 179]}")
