import numpy as np

# Load raw threshold and climatology
threshold_raw = np.load('/tmp/threshold_raw.npy')  # (366, n_sea)
clim_raw = np.load('/tmp/clim_raw.npy')  # (366, n_sea)

n_doy = 366
n_sea = threshold_raw.shape[1]

# 31-day centered moving average wrapping around
def smooth_wrap(arr, window=31):
    """Smooth a (366, n) array with a centered moving average that wraps around.
    Day d averages days d-15 to d+15, counted modulo 366."""
    n = arr.shape[0]
    half = window // 2  # 15
    result = np.zeros_like(arr)
    for d in range(n):
        indices = [(d + offset) % n for offset in range(-half, half + 1)]
        result[d] = np.mean(arr[indices], axis=0)
    return result

threshold_smooth = smooth_wrap(threshold_raw)
clim_smooth = smooth_wrap(clim_raw)

print(f"Smoothed shapes: threshold_smooth={threshold_smooth.shape}, clim_smooth={clim_smooth.shape}")
print(f"NaN in smoothed threshold: {np.isnan(threshold_smooth).sum()}")
print(f"NaN in smoothed clim: {np.isnan(clim_smooth).sum()}")

# Check some values
print(f"Threshold DOY 1, cell 0: {threshold_smooth[0, 0]}")
print(f"Threshold DOY 60, cell 0: {threshold_smooth[59, 0]}")
print(f"Clim DOY 1, cell 0: {clim_smooth[0, 0]}")
print(f"Clim DOY 60, cell 0: {clim_smooth[59, 0]}")

np.save('/tmp/threshold_smooth.npy', threshold_smooth)
np.save('/tmp/clim_smooth.npy', clim_smooth)
print("Saved smoothed threshold and climatology")
