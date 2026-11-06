
import numpy as np

threshold_raw = np.load('/tmp/threshold_raw.npy')
climatology_raw = np.load('/tmp/climatology_raw.npy')

# Set day 60 (index 59) to mean of days 59 (index 58) and 61 (index 60)
threshold_raw[59] = (threshold_raw[58] + threshold_raw[60]) / 2.0
climatology_raw[59] = (climatology_raw[58] + climatology_raw[60]) / 2.0

# Apply 31-day centered moving average with wrap-around
def smooth_31(data):
    """Smooth a (366, n_lat, n_lon) array with unweighted centred 31-day moving mean wrapping around."""
    result = np.zeros_like(data)
    n = 366
    for d in range(n):
        # Days d-15 to d+15, modulo 366
        indices = [(d + k) % n for k in range(-15, 16)]
        result[d] = np.nanmean(data[indices], axis=0)
    return result

# Check which cells are all-NaN (land cells)
# For land cells, the threshold and climatology will remain NaN
print(f"Before smoothing - NaN in threshold doy 100: {np.isnan(threshold_raw[99]).sum()}")
print(f"Before smoothing - NaN in climatology doy 100: {np.isnan(climatology_raw[99]).sum()}")

# For NaN cells, the nanmean will still produce NaN if all values are NaN
# But we need to be careful: if some days have NaN and others don't, nanmean gives the mean of non-NaN values

threshold_smoothed = smooth_31(threshold_raw)
climatology_smoothed = smooth_31(climatology_raw)

print(f"After smoothing - NaN in threshold doy 100: {np.isnan(threshold_smoothed[99]).sum()}")
print(f"After smoothing - NaN in climatology doy 100: {np.isnan(climatology_smoothed[99]).sum()}")

# Save smoothed arrays
np.save('/tmp/threshold_smoothed.npy', threshold_smoothed)
np.save('/tmp/climatology_smoothed.npy', climatology_smoothed)

# Check some values
print(f"\nSmoothed threshold doy 153, cell (30,30): {threshold_smoothed[152, 30, 30]}")
print(f"Smoothed climatology doy 153, cell (30,30): {climatology_smoothed[152, 30, 30]}")
print(f"Smoothed threshold doy 60, cell (30,30): {threshold_smoothed[59, 30, 30]}")
print(f"Smoothed climatology doy 60, cell (30,30): {climatology_smoothed[59, 30, 30]}")
